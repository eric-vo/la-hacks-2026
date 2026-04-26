import asyncio
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import mediapipe as mp
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from features import gemma_assistant
from features.asl_typing import AslTypingFeature
from features.cursor_control import (
    CursorControlFeature,
    THUMB_TIP, INDEX_TIP, INDEX_MCP,
    MIDDLE_TIP, MIDDLE_MCP,
    RING_TIP, RING_MCP,
    PINKY_TIP, PINKY_MCP,
    WRIST,
    euclidean, palm_size,
)
from features.media_control import MediaControlFeature
from logger import log_event

load_dotenv()

# ── Shared state (camera thread writes, FastAPI endpoints read) ───────────────

_frame_lock = threading.Lock()
_latest_jpeg: bytes | None = None

_state_lock = threading.Lock()
_latest_state: dict = {
    "cursor_active": False,
    "pinch_ratio": None,
    "mouse_down": False,
    "double_click": False,
    "triple_click": False,
    "thumb_up": False,
    "media_gesture": False,
    "media_triggered": False,
    "asl_candidate": None,
    "asl_typed": "",
    "gemma_prediction": "",
    "gemma_thinking": False,
}

# ── Hand skeleton drawing ─────────────────────────────────────────────────────

_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),
    (0,17),
]

def _landmark_color(i):
    if i == 0:          return (255, 255, 255)
    if 1  <= i <= 4:    return (0, 165, 255)
    if 5  <= i <= 8:    return (0, 255, 255)
    if 9  <= i <= 12:   return (0, 255, 0)
    if 13 <= i <= 16:   return (255, 140, 0)
    return (255, 0, 255)

def _draw_landmarks(frame, landmarks):
    h, w = frame.shape[:2]
    for a, b in _CONNECTIONS:
        p1, p2 = landmarks[a], landmarks[b]
        cv2.line(frame,
                 (int(p1.x * w), int(p1.y * h)),
                 (int(p2.x * w), int(p2.y * h)),
                 (90, 180, 255), 2)
    for i, lm in enumerate(landmarks):
        cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 4, _landmark_color(i), -1)

# Thumbs-up: thumb tip well above wrist, four fingers folded.
_THUMB_UP_FRAMES_REQUIRED = 12  # ~0.4 s at 30 fps

def _is_thumb_up(landmarks) -> bool:
    if not landmarks:
        return False
    psize = palm_size(landmarks)
    thumb_raised = (landmarks[WRIST].y - landmarks[THUMB_TIP].y) / psize > 0.8
    fingers_folded = all(
        euclidean(landmarks[tip], landmarks[mcp]) / psize < 0.6
        for tip, mcp in [
            (INDEX_TIP, INDEX_MCP),
            (MIDDLE_TIP, MIDDLE_MCP),
            (RING_TIP, RING_MCP),
            (PINKY_TIP, PINKY_MCP),
        ]
    )
    return thumb_raised and fingers_folded

# ── Camera loop (background daemon thread) ────────────────────────────────────

def _camera_loop():
    global _latest_jpeg

    env_path = os.environ.get("MEDIAPIPE_HAND_MODEL")
    model_path = (
        Path(env_path).expanduser().resolve()
        if env_path
        else Path(__file__).with_name("hand_landmarker.task")
    )
    if not model_path.exists():
        raise RuntimeError(f"Model not found: {model_path}")

    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    landmarker = vision.HandLandmarker.create_from_options(options)
    cursor_feature = CursorControlFeature()
    media_feature = MediaControlFeature()
    typing_feature = AslTypingFeature()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera")

    prev_cursor_active = False
    prev_mouse_down = False
    prev_double_click = False
    prev_media_triggered = False
    thumb_up_frames = 0
    thumb_up_fired = False  # prevents re-firing until gesture is released

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            try:
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                ts = int(time.monotonic() * 1000)
                result = landmarker.detect_for_video(mp_image, ts)

                landmarks = result.hand_landmarks[0] if result.hand_landmarks else None
                if landmarks:
                    _draw_landmarks(frame, landmarks)

                cursor_status = cursor_feature.process_landmarks(landmarks)
                media_status  = media_feature.process_landmarks(landmarks)
                typing_status = typing_feature.process_landmarks(landmarks)

                # Thumbs-up gesture triggers Gemma on the accumulated typed text.
                if _is_thumb_up(landmarks):
                    thumb_up_frames += 1
                    if (
                        thumb_up_frames >= _THUMB_UP_FRAMES_REQUIRED
                        and not thumb_up_fired
                        and typing_status.typed_text
                    ):
                        gemma_assistant.submit(typing_status.typed_text)
                        thumb_up_fired = True
                else:
                    thumb_up_frames = 0
                    thumb_up_fired = False

                thumb_up_active = thumb_up_frames >= _THUMB_UP_FRAMES_REQUIRED

                # Log on state transitions only.
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

                prev_cursor_active   = cursor_status.active
                prev_mouse_down      = cursor_status.mouse_down
                prev_double_click    = cursor_status.double_click
                prev_media_triggered = bool(media_status.triggered)

                # Encode and store latest frame.
                _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                with _frame_lock:
                    _latest_jpeg = jpg.tobytes()

                # Update gesture state for WebSocket clients.
                gemma = gemma_assistant.get_state()
                with _state_lock:
                    _latest_state.update({
                        "cursor_active":    cursor_status.active,
                        "pinch_ratio":      cursor_status.pinch_ratio,
                        "mouse_down":       cursor_status.mouse_down,
                        "double_click":     cursor_status.double_click,
                        "triple_click":     False,
                        "thumb_up":         thumb_up_active,
                        "media_gesture":    media_status.gesture_detected,
                        "media_triggered":  bool(media_status.triggered),
                        "asl_candidate":    typing_status.candidate_letter,
                        "asl_typed":        typing_status.typed_text,
                        "gemma_prediction": gemma["prediction"],
                        "gemma_thinking":   gemma["thinking"],
                        "gemma_error":      gemma.get("error", ""),
                    })
            except Exception as exc:  # noqa: BLE001
                print(f"[camera loop] frame error: {exc}")
    finally:
        cursor_feature.release()
        cap.release()
        landmarker.close()

# ── FastAPI app ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_app: FastAPI):
    t = threading.Thread(target=_camera_loop, daemon=True)
    t.start()
    yield

app = FastAPI(lifespan=lifespan)


@app.get("/video")
async def video():
    async def generate():
        while True:
            with _frame_lock:
                jpg = _latest_jpeg
            if jpg:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            await asyncio.sleep(0.033)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace;boundary=frame",
    )


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            with _state_lock:
                state = dict(_latest_state)
            await ws.send_json(state)
            await asyncio.sleep(0.033)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
