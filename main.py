import math
import os
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import pyautogui
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision


# Landmark indices in MediaPipe Hands.
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


# MediaPipe hand landmark graph (21 points) connections.
HAND_CONNECTIONS = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17),
]


def resolve_model_path():
    # Prefer an explicit env var, then fall back to local model file.
    env_path = os.environ.get("MEDIAPIPE_HAND_MODEL")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return Path(__file__).with_name("hand_landmarker.task")


def create_hand_landmarker(model_path):
    if not model_path.exists():
        raise RuntimeError(
            "Hand Landmarker model not found. Place 'hand_landmarker.task' next to "
            "main.py or set MEDIAPIPE_HAND_MODEL to the model path."
        )

    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    return vision.HandLandmarker.create_from_options(options)


def landmark_color(index):
    # BGR colors by anatomical group for easier visual debugging.
    if index == 0:
        return (255, 255, 255)  # wrist
    if 1 <= index <= 4:
        return (0, 165, 255)  # thumb
    if 5 <= index <= 8:
        return (0, 255, 255)  # index
    if 9 <= index <= 12:
        return (0, 255, 0)  # middle
    if 13 <= index <= 16:
        return (255, 140, 0)  # ring
    return (255, 0, 255)  # pinky (17-20)


def draw_hand_landmarks(frame, landmarks):
    height, width = frame.shape[:2]

    for start_idx, end_idx in HAND_CONNECTIONS:
        p1 = landmarks[start_idx]
        p2 = landmarks[end_idx]
        x1, y1 = int(p1.x * width), int(p1.y * height)
        x2, y2 = int(p2.x * width), int(p2.y * height)
        cv2.line(frame, (x1, y1), (x2, y2), (90, 180, 255), 2)

    for idx, lm in enumerate(landmarks):
        x, y = int(lm.x * width), int(lm.y * height)
        color = landmark_color(idx)
        cv2.circle(frame, (x, y), 4, color, -1)
        cv2.putText(
            frame,
            str(idx),
            (x + 6, y - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            color,
            1,
            cv2.LINE_AA,
        )


@dataclass
class MouseState:
    active: bool = False
    activation_frames: int = 0
    deactivation_frames: int = 0
    pinch_down_frames: int = 0
    pinch_up_frames: int = 0
    mouse_down: bool = False
    smooth_x: float | None = None
    smooth_y: float | None = None


def euclidean(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def palm_size(landmarks):
    # A scale reference used to make thresholds hand-size agnostic.
    wrist = landmarks[WRIST]
    index_mcp = landmarks[INDEX_MCP]
    pinky_mcp = landmarks[PINKY_MCP]
    return max(euclidean(wrist, index_mcp), euclidean(wrist, pinky_mcp), 1e-6)


def is_folded(tip, pip, margin=0.02):
    # In image coordinates, larger y is lower on screen.
    return tip.y > (pip.y + margin)


def map_to_screen(x_norm, y_norm, screen_w, screen_h, edge_padding=0.15):
    # Ignore edge regions to reduce jumpiness and accidental edge hits.
    x_clamped = min(max(x_norm, edge_padding), 1.0 - edge_padding)
    y_clamped = min(max(y_norm, edge_padding), 1.0 - edge_padding)

    xr = (x_clamped - edge_padding) / (1.0 - 2.0 * edge_padding)
    yr = (y_clamped - edge_padding) / (1.0 - 2.0 * edge_padding)

    return xr * screen_w, yr * screen_h


@dataclass
class GestureData:
    lobster_pose: bool = False
    pinch_ratio: float | None = None
    weighted_x: float | None = None
    weighted_y: float | None = None


def extract_gesture_data(hand_result, frame):
    data = GestureData()
    if not hand_result.hand_landmarks:
        return data

    lm = hand_result.hand_landmarks[0]
    draw_hand_landmarks(frame, lm)

    psize = palm_size(lm)
    thumb_tip = lm[THUMB_TIP]
    index_tip = lm[INDEX_TIP]

    middle_folded = is_folded(lm[MIDDLE_TIP], lm[MIDDLE_PIP])
    ring_folded = is_folded(lm[RING_TIP], lm[RING_PIP])
    pinky_folded = is_folded(lm[PINKY_TIP], lm[PINKY_PIP])
    others_folded = middle_folded and ring_folded and pinky_folded

    thumb_index_dist = euclidean(thumb_tip, index_tip)
    grip_ratio = thumb_index_dist / psize

    data.pinch_ratio = grip_ratio
    data.lobster_pose = others_folded and (grip_ratio < 0.45)
    data.weighted_x = 0.60 * index_tip.x + 0.40 * thumb_tip.x
    data.weighted_y = 0.60 * index_tip.y + 0.40 * thumb_tip.y
    return data


def update_activation_state(
    state, lobster_pose, activate_required_frames, deactivate_required_frames
):
    if lobster_pose:
        state.activation_frames += 1
        state.deactivation_frames = 0
        if state.activation_frames >= activate_required_frames:
            state.active = True
        return

    state.deactivation_frames += 1
    state.activation_frames = 0
    if state.deactivation_frames >= deactivate_required_frames:
        state.active = False


def update_cursor_position(
    state, weighted_x, weighted_y, screen_w, screen_h, smooth_alpha
):
    if not state.active or (weighted_x is None) or (weighted_y is None):
        return

    tx, ty = map_to_screen(weighted_x, weighted_y, screen_w, screen_h)
    if state.smooth_x is None:
        state.smooth_x, state.smooth_y = tx, ty
    else:
        state.smooth_x = smooth_alpha * tx + (1.0 - smooth_alpha) * state.smooth_x
        state.smooth_y = smooth_alpha * ty + (1.0 - smooth_alpha) * state.smooth_y

    pyautogui.moveTo(state.smooth_x, state.smooth_y)


def update_mouse_button(
    state, pinch_ratio, pinch_down_th, pinch_up_th, pinch_required_frames
):
    # Pinch down/up with hysteresis and debounce to avoid noise.
    if state.active and (pinch_ratio is not None):
        if pinch_ratio < pinch_down_th:
            state.pinch_down_frames += 1
            state.pinch_up_frames = 0
            if (not state.mouse_down) and (
                state.pinch_down_frames >= pinch_required_frames
            ):
                pyautogui.mouseDown()
                state.mouse_down = True
            return

        if pinch_ratio > pinch_up_th:
            state.pinch_up_frames += 1
            state.pinch_down_frames = 0
            if state.mouse_down and (state.pinch_up_frames >= pinch_required_frames):
                pyautogui.mouseUp()
                state.mouse_down = False
            return

        state.pinch_down_frames = 0
        state.pinch_up_frames = 0
        return

    state.pinch_down_frames = 0
    state.pinch_up_frames = 0
    if state.mouse_down:
        pyautogui.mouseUp()
        state.mouse_down = False


def draw_status_overlay(frame, state, pinch_ratio):
    mode_text = "Mouse Control: ON" if state.active else "Mouse Control: OFF"
    color = (40, 220, 40) if state.active else (50, 50, 220)
    cv2.putText(frame, mode_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    if pinch_ratio is not None:
        cv2.putText(
            frame,
            f"Pinch ratio: {pinch_ratio:.2f}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

    cv2.putText(
        frame,
        "Press q to quit",
        (10, frame.shape[0] - 12),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (220, 220, 220),
        1,
    )


def main():
    pyautogui.PAUSE = 0.0
    pyautogui.FAILSAFE = False

    screen_w, screen_h = pyautogui.size()

    model_path = resolve_model_path()
    hand_landmarker = create_hand_landmarker(model_path)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera.")

    state = MouseState()

    # Gesture thresholds in units normalized by palm size.
    pinch_down_th = 0.20
    pinch_up_th = 0.28

    # Debounce/hysteresis to avoid accidental triggers.
    activate_required_frames = 7
    deactivate_required_frames = 5
    pinch_required_frames = 2

    # Smoothed cursor update.
    smooth_alpha = 0.30

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int(time.monotonic() * 1000)
            hand_result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)

            gesture = extract_gesture_data(hand_result, frame)

            update_activation_state(
                state,
                gesture.lobster_pose,
                activate_required_frames,
                deactivate_required_frames,
            )

            update_cursor_position(
                state,
                gesture.weighted_x,
                gesture.weighted_y,
                screen_w,
                screen_h,
                smooth_alpha,
            )

            update_mouse_button(
                state,
                gesture.pinch_ratio,
                pinch_down_th,
                pinch_up_th,
                pinch_required_frames,
            )

            draw_status_overlay(frame, state, gesture.pinch_ratio)

            cv2.imshow("Hand Mouse Control", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        if state.mouse_down:
            pyautogui.mouseUp()
        cap.release()
        hand_landmarker.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
