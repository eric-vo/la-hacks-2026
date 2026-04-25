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
MIDDLE_MCP = 9
RING_MCP = 13
PINKY_MCP = 17

# Index tip-to-MCP distance must exceed this fraction of palm_size to count as extended.
# 0.5 prevents a loosely-curled fist (e.g. thumbs-up) from falsely triggering cursor mode.
INDEX_EXTENSION_RATIO = 0.5

# Support finger (middle/ring/pinky) tip-to-MCP must be below this fraction of palm_size
# to count as folded — direction-independent.
FINGER_FOLDED_RATIO = 0.6

# Cursor mapping constants.
# 0.60 gives ~4x screen amplification vs the previous 0.45 (~6.7x), reducing jitter.
INPUT_RANGE = 0.60
EDGE_PADDING = 0.05

# C-claw grip: thumb is the stable anchor, index is the guide.
# 80% thumb / 20% index keeps the cursor steady during pinch approach.
INDEX_WEIGHT = 0.20
THUMB_WEIGHT = 0.80

# Smoothing constants.
SMOOTH_ALPHA_BASE = 0.20
ADAPTIVE_ALPHA_MAX = 0.88
ADAPTIVE_ALPHA_GAIN = 0.55
ADAPTIVE_DIST_SCALE = 180.0
JITTER_DEADZONE_PX = 8.0
SEND_THRESHOLD_PX = 1.6

# ~600 ms hold to activate; ~500 ms without gesture to deactivate (at 30 fps).
ACTIVATE_REQUIRED_FRAMES = 18
DEACTIVATE_REQUIRED_FRAMES = 15

# Pinch click: thumb-tip to index-tip distance relative to palm size.
# Wider hysteresis band avoids accidental re-triggers at the boundary.
PINCH_DOWN_THRESHOLD = 0.40
PINCH_UP_THRESHOLD = 0.35
PINCH_REQUIRED_FRAMES = 3
# Cursor freezes as soon as the pinch ratio drops below this, before the click fires,
# so the target doesn't drift during the approach motion.
CURSOR_FREEZE_THRESHOLD = 0.45

# Multi-click: successive pinch-downs within this many frames of the last release.
MULTI_CLICK_WINDOW_FRAMES = 15
DRAG_START_THRESHOLD_FRAMES = 10

# Frames each click label stays visible (~0.83 s at 30 fps).
DOUBLE_CLICK_FLASH_FRAMES = 25
TRIPLE_CLICK_FLASH_FRAMES = 25


@dataclass
class CursorState:
    active: bool = False
    activation_frames: int = 0
    deactivation_frames: int = 0
    pinch_down_frames: int = 0
    pinch_up_frames: int = 0
    mouse_down: bool = False
    frames_since_last_click: int = -1  # -1 = no recent click; ≥0 = frames since last mouseUp
    click_sequence: int = 0            # clicks completed in the current rapid sequence (0-2)
    double_click_flash_frames: int = 0
    triple_click_flash_frames: int = 0
    smooth_x: float | None = None
    smooth_y: float | None = None
    sent_x: float | None = None
    sent_y: float | None = None


@dataclass
class CursorStatus:
    active: bool = False
    pinch_ratio: float | None = None
    mouse_down: bool = False
    double_click: bool = False
    triple_click: bool = False


def euclidean(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def palm_size(landmarks):
    wrist = landmarks[WRIST]
    return max(
        euclidean(wrist, landmarks[INDEX_MCP]),
        euclidean(wrist, landmarks[PINKY_MCP]),
        1e-6,
    )


def _index_extended(landmarks) -> bool:
    """Index finger extended in any direction; middle, ring, pinky folded."""
    psize = palm_size(landmarks)
    index_extended = (
        euclidean(landmarks[INDEX_TIP], landmarks[INDEX_MCP]) / psize > INDEX_EXTENSION_RATIO
    )
    support_folded = _support_fingers_folded(landmarks, psize)
    return index_extended and support_folded


def _support_fingers_folded(landmarks, psize=None) -> bool:
    """Middle, ring, pinky folded — direction-independent, allows pinching while active."""
    if psize is None:
        psize = palm_size(landmarks)
    return (
        euclidean(landmarks[MIDDLE_TIP], landmarks[MIDDLE_MCP]) / psize < FINGER_FOLDED_RATIO
        and euclidean(landmarks[RING_TIP], landmarks[RING_MCP]) / psize < FINGER_FOLDED_RATIO
        and euclidean(landmarks[PINKY_TIP], landmarks[PINKY_MCP]) / psize < FINGER_FOLDED_RATIO
    )


def map_to_screen(x_norm, y_norm, screen_w, screen_h):
    # Clamp away from noisy frame edges first.
    x = min(max(x_norm, EDGE_PADDING), 1.0 - EDGE_PADDING)
    y = min(max(y_norm, EDGE_PADDING), 1.0 - EDGE_PADDING)

    # Map the central INPUT_RANGE band (anchored at 0.5) to the full screen.
    # Positions outside that band saturate to the screen edge.
    half = INPUT_RANGE / 2.0
    xr = (x - (0.5 - half)) / INPUT_RANGE
    yr = (y - (0.5 - half)) / INPUT_RANGE

    xr = min(max(xr, 0.0), 1.0)
    yr = min(max(yr, 0.0), 1.0)
    return xr * screen_w, yr * screen_h


def extract_landmark_features(landmarks):
    if not landmarks:
        return False, False, None, None, None

    index_up = _index_extended(landmarks)
    support_folded = _support_fingers_folded(landmarks)
    psize = palm_size(landmarks)
    index_tip = landmarks[INDEX_TIP]
    thumb_tip = landmarks[THUMB_TIP]
    pinch_ratio = euclidean(thumb_tip, index_tip) / psize
    cursor_x = INDEX_WEIGHT * index_tip.x + THUMB_WEIGHT * thumb_tip.x
    cursor_y = INDEX_WEIGHT * index_tip.y + THUMB_WEIGHT * thumb_tip.y
    return index_up, support_folded, pinch_ratio, cursor_x, cursor_y


class CursorControlFeature:
    def __init__(self):
        pyautogui.PAUSE = 0.0
        pyautogui.FAILSAFE = False
        self.screen_w, self.screen_h = pyautogui.size()
        self.state = CursorState()

    def process_landmarks(self, landmarks):
        index_up, support_folded, pinch_ratio, cursor_x, cursor_y = (
            extract_landmark_features(landmarks)
        )

        # Advance multi-click window; expire sequence when gap is too large.
        if self.state.frames_since_last_click >= 0:
            self.state.frames_since_last_click += 1
            if self.state.frames_since_last_click > MULTI_CLICK_WINDOW_FRAMES:
                self.state.frames_since_last_click = -1
                self.state.click_sequence = 0

        if self.state.double_click_flash_frames > 0:
            self.state.double_click_flash_frames -= 1
        if self.state.triple_click_flash_frames > 0:
            self.state.triple_click_flash_frames -= 1

        self._update_activation_state(index_up, support_folded)
        pinch_approaching = pinch_ratio is not None and pinch_ratio < CURSOR_FREEZE_THRESHOLD
        if not self.state.mouse_down and not pinch_approaching:
            self._update_cursor_position(cursor_x, cursor_y)
        self._update_mouse_button(pinch_ratio)

        return CursorStatus(
            active=self.state.active,
            pinch_ratio=pinch_ratio,
            mouse_down=self.state.mouse_down,
            double_click=self.state.double_click_flash_frames > 0,
            triple_click=self.state.triple_click_flash_frames > 0,
        )

    def release(self):
        if self.state.mouse_down:
            pyautogui.mouseUp()
            self.state.mouse_down = False

    def _update_activation_state(self, index_up, support_folded):
        if not self.state.active:
            if index_up:
                self.state.activation_frames += 1
                self.state.deactivation_frames = 0
                if self.state.activation_frames >= ACTIVATE_REQUIRED_FRAMES:
                    self.state.active = True
                    self.state.activation_frames = 0
            else:
                self.state.activation_frames = 0
        else:
            # While active, only check the support fingers so that pinching
            # (which bends the index inward) does not accidentally deactivate.
            if support_folded:
                self.state.deactivation_frames = 0
            else:
                self.state.deactivation_frames += 1
                if self.state.deactivation_frames >= DEACTIVATE_REQUIRED_FRAMES:
                    self.state.active = False
                    self.state.deactivation_frames = 0
                    self.state.smooth_x = None
                    self.state.smooth_y = None

    def _update_cursor_position(self, cursor_x, cursor_y):
        if not self.state.active or cursor_x is None:
            return

        tx, ty = map_to_screen(cursor_x, cursor_y, self.screen_w, self.screen_h)
        if self.state.smooth_x is None:
            self.state.smooth_x, self.state.smooth_y = tx, ty
            pyautogui.moveTo(self.state.smooth_x, self.state.smooth_y)
            self.state.sent_x, self.state.sent_y = self.state.smooth_x, self.state.smooth_y
            return

        dx = tx - self.state.smooth_x
        dy = ty - self.state.smooth_y
        dist = math.hypot(dx, dy)

        if dist < JITTER_DEADZONE_PX:
            return

        adaptive_alpha = min(
            ADAPTIVE_ALPHA_MAX,
            SMOOTH_ALPHA_BASE + ADAPTIVE_ALPHA_GAIN * min(dist / ADAPTIVE_DIST_SCALE, 1.0),
        )
        self.state.smooth_x = adaptive_alpha * tx + (1.0 - adaptive_alpha) * self.state.smooth_x
        self.state.smooth_y = adaptive_alpha * ty + (1.0 - adaptive_alpha) * self.state.smooth_y

        if self.state.sent_x is not None:
            send_dist = math.hypot(
                self.state.smooth_x - self.state.sent_x,
                self.state.smooth_y - self.state.sent_y,
            )
            if send_dist < SEND_THRESHOLD_PX:
                return

        pyautogui.moveTo(self.state.smooth_x, self.state.smooth_y)
        self.state.sent_x, self.state.sent_y = self.state.smooth_x, self.state.smooth_y

    def _update_mouse_button(self, pinch_ratio):
        if not self.state.active or pinch_ratio is None:
            self._reset_click_states()
            return

        # --- PINCH DOWN DETECTED ---
        if pinch_ratio < PINCH_DOWN_THRESHOLD:
            self.state.pinch_down_frames += 1
            self.state.pinch_up_frames = 0
            # If held long enough, treat as drag/normal click.
            if (
                not self.state.mouse_down
                and self.state.pinch_down_frames >= DRAG_START_THRESHOLD_FRAMES
            ):
                if self.state.click_sequence == 0:
                    pyautogui.mouseDown()
                    self.state.mouse_down = True
            return

        # --- PINCH UP (RELEASE) DETECTED ---
        if pinch_ratio > PINCH_UP_THRESHOLD:
            self.state.pinch_up_frames += 1
            if self.state.pinch_down_frames > 0:
                is_quick_tap = self.state.pinch_down_frames < DRAG_START_THRESHOLD_FRAMES
                if is_quick_tap:
                    self.state.click_sequence += 1
                    self.state.frames_since_last_click = 0

                    # Handle the sequence logic
                    if self.state.click_sequence == 2:
                        pyautogui.doubleClick()
                        self.state.double_click_flash_frames = DOUBLE_CLICK_FLASH_FRAMES
                        self._reset_after_action()
                    elif self.state.click_sequence == 3:
                        pyautogui.click(clicks=3, interval=0.05)
                        self.state.triple_click_flash_frames = TRIPLE_CLICK_FLASH_FRAMES
                        self._reset_after_action()
                else:
                    # It was a long hold/drag, just release
                    if self.state.mouse_down:
                        pyautogui.mouseUp()
                        self.state.mouse_down = False
                    self._reset_after_action()

            self.state.pinch_down_frames = 0
            return

    def _reset_after_action(self):
        """Reset sequence trackers after a successful click action."""
        self.state.click_sequence = 0
        self.state.frames_since_last_click = -1

    def _reset_click_states(self):
        """Hard reset when hand is lost or inactive."""
        if self.state.mouse_down:
            pyautogui.mouseUp()
        self.state.mouse_down = False
        self.state.pinch_down_frames = 0
        self.state.pinch_up_frames = 0
        self.state.click_sequence = 0
        self.state.frames_since_last_click = -1
