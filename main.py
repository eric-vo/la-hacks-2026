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

from features.asl_typing import AslTypingFeature
from features.cursor_control import CursorControlFeature, CursorStatus
from features.media_control import MediaControlFeature, MediaStatus
from logger import log_event


# Landmark indices in MediaPipe Hands.
THUMB_TIP = 4
THUMB_IP = 3
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

# Gesture mode switch: index + thumb extended, middle/ring/pinky folded.
MODE_SWITCH_EXTEND_MARGIN_RATIO = 0.08
MODE_SWITCH_FOLD_MARGIN_RATIO = 0.02
MODE_SWITCH_THUMB_INDEX_SEPARATION_RATIO = 1.5
MODE_SWITCH_HOLD_FRAMES = 7
MODE_SWITCH_COOLDOWN_FRAMES = 20


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


def _euclidean_2d(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def is_mode_switch_gesture(landmarks):
    if not landmarks:
        return False

    wrist = landmarks[WRIST]
    palm = max(
        _euclidean_2d(wrist, landmarks[INDEX_MCP]),
        _euclidean_2d(wrist, landmarks[PINKY_MCP]),
        1e-6,
    )

    def finger_extended(tip_idx, pip_idx):
        tip_dist = _euclidean_2d(wrist, landmarks[tip_idx])
        pip_dist = _euclidean_2d(wrist, landmarks[pip_idx])
        return tip_dist > pip_dist + MODE_SWITCH_EXTEND_MARGIN_RATIO * palm

    def finger_folded(tip_idx, pip_idx):
        tip_dist = _euclidean_2d(wrist, landmarks[tip_idx])
        pip_dist = _euclidean_2d(wrist, landmarks[pip_idx])
        return tip_dist < pip_dist + MODE_SWITCH_FOLD_MARGIN_RATIO * palm

    index_extended = finger_extended(INDEX_TIP, INDEX_PIP)
    thumb_extended = finger_extended(THUMB_TIP, THUMB_IP)
    middle_folded = finger_folded(MIDDLE_TIP, MIDDLE_PIP)
    ring_folded = finger_folded(RING_TIP, RING_PIP)
    pinky_folded = finger_folded(PINKY_TIP, PINKY_PIP)

    thumb_index_separation = (
        _euclidean_2d(landmarks[THUMB_TIP], landmarks[INDEX_TIP]) / palm
    )
    thumb_index_apart = (
        thumb_index_separation >= MODE_SWITCH_THUMB_INDEX_SEPARATION_RATIO
    )

    return (
        index_extended
        and thumb_extended
        and middle_folded
        and ring_folded
        and pinky_folded
        and thumb_index_apart
    )


def resolve_model_path():
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
    if index == WRIST:
        return (255, 255, 255)
    if 1 <= index <= THUMB_TIP:
        return (0, 165, 255)
    if 5 <= index <= INDEX_PIP:
        return (0, 255, 255)
    if 9 <= index <= MIDDLE_TIP:
        return (0, 255, 0)
    if 13 <= index <= RING_TIP:
        return (255, 140, 0)
    return (255, 0, 255)


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


def draw_status_overlay(
    frame,
    active_mode,
    cursor_status,
    media_status,
    typing_status,
    switch_hold_frames,
):
    mode_text = f"Mode: {active_mode.upper()}"
    mode_color = (40, 220, 40) if active_mode == "cursor" else (220, 180, 60)
    cv2.putText(
        frame, mode_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, mode_color, 2
    )

    cursor_text = "Mouse Control: ON" if cursor_status.active else "Mouse Control: OFF"
    cursor_color = (40, 220, 40) if cursor_status.active else (50, 50, 220)
    cv2.putText(
        frame,
        cursor_text,
        (10, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        cursor_color,
        2,
    )

    if cursor_status.pinch_ratio is not None:
        cv2.putText(
            frame,
            f"Pinch ratio: {cursor_status.pinch_ratio:.2f}",
            (10, 90),
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
    cv2.putText(
        frame,
        media_label,
        (10, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        media_color,
        2,
    )

    model_text = "loaded" if typing_status.model_loaded else "missing"
    if typing_status.confidence is not None:
        typing_line = (
            f"Typing: {typing_status.candidate_letter or '-'}"
            f" | conf: {typing_status.confidence:.2f}"
        )
    else:
        typing_line = "Typing: - | conf: -"
    cv2.putText(
        frame,
        f"ASL model: {model_text}",
        (10, 180),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (210, 210, 210),
        2,
    )
    cv2.putText(
        frame,
        typing_line,
        (10, 210),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (210, 210, 210),
        2,
    )
    cv2.putText(
        frame,
        f"Typed: {typing_status.typed_text or ''}",
        (10, 240),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (180, 255, 180),
        2,
    )
    cv2.putText(
        frame,
        "Keys: 1=cursor, 2=media, 3=common, 4=typing",
        (10, 270),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (180, 180, 180),
        1,
    )
    cv2.putText(
        frame,
        "Gesture switch: index+thumb extended, others folded",
        (10, 295),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (180, 180, 180),
        1,
    )

    if switch_hold_frames > 0:
        cv2.putText(
            frame,
            f"Switch hold: {switch_hold_frames}/{MODE_SWITCH_HOLD_FRAMES}",
            (10, 320),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (60, 220, 255),
            2,
        )

    cv2.putText(
        frame,
        "Press 'q' to quit",
        (10, frame.shape[0] - 12),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (220, 220, 220),
        1,
    )

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


def main():
    model_path = resolve_model_path()
    hand_landmarker = create_hand_landmarker(model_path)
    cursor_feature = CursorControlFeature()
    media_feature = MediaControlFeature()
    typing_feature = AslTypingFeature()

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
    prev_media_triggered = False
    prev_typed_letter = None

    active_mode = "cursor"
    mode_switch_hold_frames = 0
    mode_switch_cooldown_frames = 0
    mode_switch_armed = True

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

            if mode_switch_cooldown_frames > 0:
                mode_switch_cooldown_frames -= 1

            switch_gesture_active = bool(landmarks) and is_mode_switch_gesture(
                landmarks
            )

            # Rearm only after the gesture is released once.
            if not switch_gesture_active:
                mode_switch_armed = True

            if (
                mode_switch_armed
                and switch_gesture_active
                and mode_switch_cooldown_frames == 0
            ):
                mode_switch_hold_frames += 1
                if mode_switch_hold_frames >= MODE_SWITCH_HOLD_FRAMES:
                    active_mode = "cursor" if active_mode == "typing" else "typing"
                    log_event("mode_switch", f"Switched mode to: {active_mode}")
                    mode_switch_hold_frames = 0
                    mode_switch_cooldown_frames = MODE_SWITCH_COOLDOWN_FRAMES
                    mode_switch_armed = False
            else:
                mode_switch_hold_frames = 0

            if active_mode == "cursor":
                cursor_status = cursor_feature.process_landmarks(landmarks)
            else:
                cursor_feature.release()
                cursor_status = CursorStatus()

            if active_mode == "media":
                media_status = media_feature.process_landmarks(landmarks)
            else:
                media_status = MediaStatus()

            typing_status = typing_feature.process_landmarks(
                landmarks, enabled=(active_mode == "typing")
            )

            draw_status_overlay(
                frame,
                active_mode,
                cursor_status,
                media_status,
                typing_status,
                mode_switch_hold_frames,
            )

            if cursor_status.active != prev_cursor_active:
                log_event(
                    "cursor_on" if cursor_status.active else "cursor_off",
                    "Cursor Mode ON" if cursor_status.active else "Cursor Mode OFF",
                )
            if cursor_status.mouse_down and not prev_mouse_down:
                log_event("single_click", "Single Click")
            if cursor_status.double_click and not prev_double_click:
                log_event("double_click", "Double Click")
            if media_status.triggered and not prev_media_triggered:
                log_event("media_play_pause", "Play / Pause")
            if (
                typing_status.committed_letter
                and typing_status.committed_letter != prev_typed_letter
            ):
                log_event(
                    "typed_letter", f"Typed letter: {typing_status.committed_letter}"
                )

            prev_cursor_active = cursor_status.active
            prev_mouse_down = cursor_status.mouse_down
            prev_double_click = cursor_status.double_click
            prev_media_triggered = media_status.triggered
            prev_typed_letter = typing_status.committed_letter

            cv2.imshow(win_name, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("1"):
                active_mode = "cursor"
            elif key == ord("2"):
                active_mode = "media"
            elif key == ord("3"):
                active_mode = "common"
            elif key == ord("4"):
                active_mode = "typing"
            elif key == ord("r"):
                typing_feature.reload_models()
            elif key == ord("q"):
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
