import math
from dataclasses import dataclass

import pyautogui


# Landmark indices used by the cursor/click feature.
THUMB_TIP = 4
INDEX_TIP = 8
INDEX_PIP = 6
MIDDLE_TIP = 12
MIDDLE_PIP = 10
RING_TIP = 16
RING_PIP = 14
PINKY_TIP = 20
PINKY_PIP = 18
WRIST = 0
INDEX_MCP = 5
PINKY_MCP = 17

# Gesture interpretation thresholds.
LOBSTER_GRIP_RATIO_THRESHOLD = 0.60
FOLDED_MARGIN = 0.02

# Cursor mapping/smoothing constants.
EDGE_PADDING = 0.15
INDEX_WEIGHT = 0.60
THUMB_WEIGHT = 0.40
SMOOTH_ALPHA_BASE = 0.20
ADAPTIVE_ALPHA_MAX = 0.88
ADAPTIVE_ALPHA_GAIN = 0.55
ADAPTIVE_DIST_SCALE = 180.0
JITTER_DEADZONE_PX = 6.0
SEND_THRESHOLD_PX = 1.6

# Click and mode state constants.
PINCH_DOWN_THRESHOLD = 0.24
PINCH_UP_THRESHOLD = 0.28
ACTIVATE_REQUIRED_FRAMES = 7
DEACTIVATE_REQUIRED_FRAMES = 5
PINCH_REQUIRED_FRAMES = 2


@dataclass
class CursorState:
    active: bool = False
    activation_frames: int = 0
    deactivation_frames: int = 0
    pinch_down_frames: int = 0
    pinch_up_frames: int = 0
    mouse_down: bool = False
    smooth_x: float | None = None
    smooth_y: float | None = None
    sent_x: float | None = None
    sent_y: float | None = None


@dataclass
class CursorStatus:
    active: bool = False
    pinch_ratio: float | None = None
    mouse_down: bool = False


def euclidean(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def palm_size(landmarks):
    # A scale reference used to make thresholds hand-size agnostic.
    wrist = landmarks[WRIST]
    index_mcp = landmarks[INDEX_MCP]
    pinky_mcp = landmarks[PINKY_MCP]
    return max(euclidean(wrist, index_mcp), euclidean(wrist, pinky_mcp), 1e-6)


def is_folded(tip, pip, margin=FOLDED_MARGIN):
    # In image coordinates, larger y is lower on screen.
    return tip.y > (pip.y + margin)


def map_to_screen(x_norm, y_norm, screen_w, screen_h, edge_padding=EDGE_PADDING):
    # Ignore edge regions to reduce jumpiness and accidental edge hits.
    x_clamped = min(max(x_norm, edge_padding), 1.0 - edge_padding)
    y_clamped = min(max(y_norm, edge_padding), 1.0 - edge_padding)

    xr = (x_clamped - edge_padding) / (1.0 - 2.0 * edge_padding)
    yr = (y_clamped - edge_padding) / (1.0 - 2.0 * edge_padding)

    return xr * screen_w, yr * screen_h


def extract_landmark_features(landmarks):
    if not landmarks:
        return False, None, None, None

    psize = palm_size(landmarks)
    thumb_tip = landmarks[THUMB_TIP]
    index_tip = landmarks[INDEX_TIP]

    middle_folded = is_folded(landmarks[MIDDLE_TIP], landmarks[MIDDLE_PIP])
    ring_folded = is_folded(landmarks[RING_TIP], landmarks[RING_PIP])
    pinky_folded = is_folded(landmarks[PINKY_TIP], landmarks[PINKY_PIP])
    others_folded = middle_folded and ring_folded and pinky_folded

    thumb_index_dist = euclidean(thumb_tip, index_tip)
    grip_ratio = thumb_index_dist / psize

    lobster_pose = others_folded and (grip_ratio < LOBSTER_GRIP_RATIO_THRESHOLD)
    weighted_x = INDEX_WEIGHT * index_tip.x + THUMB_WEIGHT * thumb_tip.x
    weighted_y = INDEX_WEIGHT * index_tip.y + THUMB_WEIGHT * thumb_tip.y
    return lobster_pose, grip_ratio, weighted_x, weighted_y


class CursorControlFeature:
    def __init__(self):
        pyautogui.PAUSE = 0.0
        pyautogui.FAILSAFE = False
        self.screen_w, self.screen_h = pyautogui.size()
        self.state = CursorState()

    def process_landmarks(self, landmarks):
        lobster_pose, pinch_ratio, weighted_x, weighted_y = extract_landmark_features(
            landmarks
        )

        self._update_activation_state(lobster_pose)
        self._update_cursor_position(weighted_x, weighted_y)
        self._update_mouse_button(pinch_ratio)

        return CursorStatus(
            active=self.state.active,
            pinch_ratio=pinch_ratio,
            mouse_down=self.state.mouse_down,
        )

    def release(self):
        if self.state.mouse_down:
            pyautogui.mouseUp()
            self.state.mouse_down = False

    def _update_activation_state(self, lobster_pose):
        if lobster_pose:
            self.state.activation_frames += 1
            self.state.deactivation_frames = 0
            if self.state.activation_frames >= ACTIVATE_REQUIRED_FRAMES:
                self.state.active = True
            return

        self.state.deactivation_frames += 1
        self.state.activation_frames = 0
        if self.state.deactivation_frames >= DEACTIVATE_REQUIRED_FRAMES:
            self.state.active = False

    def _update_cursor_position(self, weighted_x, weighted_y):
        if not self.state.active or (weighted_x is None) or (weighted_y is None):
            return

        tx, ty = map_to_screen(weighted_x, weighted_y, self.screen_w, self.screen_h)
        if self.state.smooth_x is None:
            self.state.smooth_x, self.state.smooth_y = tx, ty
            pyautogui.moveTo(self.state.smooth_x, self.state.smooth_y)
            self.state.sent_x, self.state.sent_y = (
                self.state.smooth_x,
                self.state.smooth_y,
            )
            return

        dx = tx - self.state.smooth_x
        dy = ty - self.state.smooth_y
        dist = math.hypot(dx, dy)

        # Ignore tiny frame-to-frame motion so a still hand stays still.
        if dist < JITTER_DEADZONE_PX:
            return

        # Move faster for large motions, smoother for small motions.
        adaptive_alpha = min(
            ADAPTIVE_ALPHA_MAX,
            SMOOTH_ALPHA_BASE
            + ADAPTIVE_ALPHA_GAIN * min(dist / ADAPTIVE_DIST_SCALE, 1.0),
        )
        self.state.smooth_x = (
            adaptive_alpha * tx + (1.0 - adaptive_alpha) * self.state.smooth_x
        )
        self.state.smooth_y = (
            adaptive_alpha * ty + (1.0 - adaptive_alpha) * self.state.smooth_y
        )

        if (self.state.sent_x is not None) and (self.state.sent_y is not None):
            send_dist = math.hypot(
                self.state.smooth_x - self.state.sent_x,
                self.state.smooth_y - self.state.sent_y,
            )
            if send_dist < SEND_THRESHOLD_PX:
                return

        pyautogui.moveTo(self.state.smooth_x, self.state.smooth_y)
        self.state.sent_x, self.state.sent_y = self.state.smooth_x, self.state.smooth_y

    def _update_mouse_button(self, pinch_ratio):
        # Pinch down/up with hysteresis and debounce to avoid noise.
        if self.state.active and (pinch_ratio is not None):
            if pinch_ratio < PINCH_DOWN_THRESHOLD:
                self.state.pinch_down_frames += 1
                self.state.pinch_up_frames = 0
                if (not self.state.mouse_down) and (
                    self.state.pinch_down_frames >= PINCH_REQUIRED_FRAMES
                ):
                    pyautogui.mouseDown()
                    self.state.mouse_down = True
                return

            if pinch_ratio > PINCH_UP_THRESHOLD:
                self.state.pinch_up_frames += 1
                self.state.pinch_down_frames = 0
                if self.state.mouse_down and (
                    self.state.pinch_up_frames >= PINCH_REQUIRED_FRAMES
                ):
                    pyautogui.mouseUp()
                    self.state.mouse_down = False
                return

            self.state.pinch_down_frames = 0
            self.state.pinch_up_frames = 0
            return

        self.state.pinch_down_frames = 0
        self.state.pinch_up_frames = 0
        if self.state.mouse_down:
            pyautogui.mouseUp()
            self.state.mouse_down = False
