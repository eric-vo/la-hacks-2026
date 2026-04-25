import os
import time
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from features.cursor_control import CursorControlFeature


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


def draw_status_overlay(frame, cursor_status):
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

    cv2.putText(
        frame,
        "Press q to quit",
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


def main():
    model_path = resolve_model_path()
    hand_landmarker = create_hand_landmarker(model_path)
    cursor_feature = CursorControlFeature()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera.")

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

            landmarks = hand_result.hand_landmarks[0] if hand_result.hand_landmarks else None
            if landmarks:
                draw_hand_landmarks(frame, landmarks)

            cursor_status = cursor_feature.process_landmarks(landmarks)
            draw_status_overlay(frame, cursor_status)

            cv2.imshow("Hand Mouse Control", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cursor_feature.release()
        cap.release()
        hand_landmarker.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
