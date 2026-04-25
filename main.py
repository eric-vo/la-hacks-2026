import os
import time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import cv2
import mediapipe as mp
import pyautogui
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from features.cursor_control import CursorControlFeature
from features.media_control import MediaControlFeature
from features.common_gestures import CommonGesturesFeature
from logger import log_event


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
    if index == WRIST:
        return (255, 255, 255)  # wrist
    if 1 <= index <= THUMB_TIP:
        return (0, 165, 255)  # thumb
    if 5 <= index <= INDEX_PIP:
        return (0, 255, 255)  # index
    if 9 <= index <= MIDDLE_TIP:
        return (0, 255, 0)  # middle
    if 13 <= index <= RING_TIP:
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


def draw_status_overlay(frame, cursor_status, media_status, common_status):
    mode_text = "Mouse Control: ON" if cursor_status.active else "Mouse Control: OFF"
    color = (40, 220, 40) if cursor_status.active else (50, 50, 220)
    cv2.putText(frame, mode_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    if cursor_status.pinch_ratio is not None:
        cv2.putText(
            frame,
            f"Pinch ratio: {cursor_status.pinch_ratio:.2f}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

    if media_status.cooldown_active:
        media_label = "Media hand: cooldown"
        media_color = (180, 180, 50)
    elif media_status.gesture_detected:
        media_label = "Media hand: holding..."
        media_color = (50, 200, 255)
    else:
        media_label = "Media hand: ready"
        media_color = (130, 130, 130)
    cv2.putText(frame, media_label, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, media_color, 2)

    gesture_label = f"Common Gesture: {common_status.gesture or 'none'}"
    cv2.putText(frame, gesture_label, (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    cv2.putText(
        frame,
        "Press 'q' to quit",
        (10, frame.shape[0] - 12),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (220, 220, 220),
        1,
    )

    # Draw click indicator if mouse is down
    if cursor_status.mouse_down:
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        cv2.circle(frame, (cx, cy), 40, (0, 0, 255), 4)
        cv2.putText(
            frame,
            "CLICK",
            (cx - 35, cy + 7),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 0, 255),
            3,
            cv2.LINE_AA,
        )

    # Draw double-click flash indicator
    if cursor_status.double_click:
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        cv2.circle(frame, (cx, cy), 58, (255, 120, 0), 4)
        cv2.putText(
            frame,
            "DOUBLE CLICK",
            (cx - 90, cy + 7),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (255, 120, 0),
            3,
            cv2.LINE_AA,
        )

    # Draw triple-click flash indicator
    if cursor_status.triple_click:
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        cv2.circle(frame, (cx, cy), 74, (0, 200, 0), 4)
        cv2.putText(
            frame,
            "TRIPLE CLICK",
            (cx - 88, cy + 7),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 200, 0),
            3,
            cv2.LINE_AA,
        )

    # Flash "PLAY/PAUSE" when the gesture fires
    if media_status.triggered:
        h, w = frame.shape[:2]
        cv2.putText(
            frame,
            "PLAY/PAUSE",
            (w // 2 - 100, h // 2 - 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.4,
            (50, 200, 255),
            3,
            cv2.LINE_AA,
        )

    # Flash "YES" or "NO" when a common gesture triggers.
    if common_status.triggered == "thumbs_up":
        h, w = frame.shape[:2]
        cv2.putText(
            frame,
            "YES",
            (w // 2 - 45, h // 2 + 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.6,
            (40, 220, 40),
            3,
            cv2.LINE_AA,
        )
    elif common_status.triggered == "thumbs_down":
        h, w = frame.shape[:2]
        cv2.putText(
            frame,
            "NO",
            (w // 2 - 30, h // 2 + 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.6,
            (50, 50, 220),
            3,
            cv2.LINE_AA,
        )


def main():
    model_path = resolve_model_path()
    hand_landmarker = create_hand_landmarker(model_path)
    cursor_feature = CursorControlFeature()
    media_feature = MediaControlFeature()
    common_feature = CommonGesturesFeature()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera.")

    win_name = "Hand Mouse Control"
    screen_w, screen_h = pyautogui.size()
    win_w, win_h = int(screen_w * 0.7), int(screen_h * 0.7)
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, win_w, win_h)
    win_x = (screen_w - win_w) // 2
    win_y = int(screen_h * 0.40) - win_h // 2
    cv2.moveWindow(win_name, win_x, win_y)

    prev_cursor_active = False
    prev_mouse_down = False
    prev_double_click = False
    prev_triple_click = False
    prev_media_triggered = False
    prev_common_triggered = None

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

            landmarks = (
                hand_result.hand_landmarks[0] if hand_result.hand_landmarks else None
            )
            if landmarks:
                draw_hand_landmarks(frame, landmarks)

            cursor_status = cursor_feature.process_landmarks(landmarks)
            media_status = media_feature.process_landmarks(landmarks)
            common_status = common_feature.process_landmarks(landmarks)
            draw_status_overlay(frame, cursor_status, media_status, common_status)

            # Log gesture events on state transitions (once per event, not every frame).
            if cursor_status.active != prev_cursor_active:
                log_event("cursor_on" if cursor_status.active else "cursor_off",
                          "Cursor Mode ON" if cursor_status.active else "Cursor Mode OFF")
            if cursor_status.mouse_down and not prev_mouse_down:
                log_event("single_click", "Single Click")
            if cursor_status.double_click and not prev_double_click:
                log_event("double_click", "Double Click")
            if cursor_status.triple_click and not prev_triple_click:
                log_event("triple_click", "Triple Click")
            if media_status.triggered and not prev_media_triggered:
                log_event("media_play_pause", "Play / Pause")
            if common_status.triggered and common_status.triggered != prev_common_triggered:
                if common_status.triggered == "thumbs_up":
                    log_event("thumbs_up", "Thumbs Up")
                elif common_status.triggered == "thumbs_down":
                    log_event("thumbs_down", "Thumbs Down")

            prev_cursor_active = cursor_status.active
            prev_mouse_down = cursor_status.mouse_down
            prev_double_click = cursor_status.double_click
            prev_triple_click = cursor_status.triple_click
            prev_media_triggered = media_status.triggered
            prev_common_triggered = common_status.triggered

            cv2.imshow(win_name, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            if cv2.getWindowProperty(win_name, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        cursor_feature.release()
        cap.release()
        hand_landmarker.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
