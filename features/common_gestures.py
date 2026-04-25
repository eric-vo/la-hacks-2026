from dataclasses import dataclass

# Landmark indices used for gesture detection.
THUMB_TIP = 4
THUMB_MCP = 2
INDEX_TIP = 8
INDEX_PIP = 6
MIDDLE_TIP = 12
MIDDLE_PIP = 10
RING_TIP = 16
RING_PIP = 14
PINKY_TIP = 20
PINKY_PIP = 18

# Fingers must be this far below their PIP joint to count as folded.
FOLDED_MARGIN = 0.02

# Thumb tip must be this far above/below THUMB_MCP (in image y) to confirm direction.
THUMB_DIRECTION_MARGIN = 0.06

# Frames the gesture must be held before firing (~0.4 s at 30 fps).
HOLD_FRAMES_REQUIRED = 12

# Frames to suppress new triggers after one fires (~1.5 s at 30 fps).
COOLDOWN_FRAMES = 45

# Frames the triggered label stays visible (~0.67 s at 30 fps).
FLASH_FRAMES = 20


def _fingers_folded(landmarks) -> bool:
    def folded(tip_idx, pip_idx):
        return landmarks[tip_idx].y > landmarks[pip_idx].y + FOLDED_MARGIN

    return (
        folded(INDEX_TIP, INDEX_PIP)
        and folded(MIDDLE_TIP, MIDDLE_PIP)
        and folded(RING_TIP, RING_PIP)
        and folded(PINKY_TIP, PINKY_PIP)
    )


def _detect_gesture(landmarks) -> str | None:
    if landmarks is None:
        return None
    if not _fingers_folded(landmarks):
        return None
    # Thumb direction is determined by how far the tip is above/below its MCP joint.
    dy = landmarks[THUMB_TIP].y - landmarks[THUMB_MCP].y
    if dy < -THUMB_DIRECTION_MARGIN:
        return "thumbs_up"
    if dy > THUMB_DIRECTION_MARGIN:
        return "thumbs_down"
    return None


@dataclass
class CommonGesturesState:
    candidate: str | None = None
    gesture_frames: int = 0
    cooldown_frames: int = 0
    flash_frames: int = 0
    flash_gesture: str | None = None


@dataclass
class CommonGesturesStatus:
    gesture: str | None = None    # currently detected gesture label
    triggered: str | None = None  # non-None for FLASH_FRAMES after a trigger fires


class CommonGesturesFeature:
    def __init__(self):
        self.state = CommonGesturesState()

    def process_landmarks(self, landmarks) -> CommonGesturesStatus:
        state = self.state
        detected = _detect_gesture(landmarks)

        if state.flash_frames > 0:
            state.flash_frames -= 1
            if state.flash_frames == 0:
                state.flash_gesture = None

        if state.cooldown_frames > 0:
            state.cooldown_frames -= 1
            if detected != state.candidate:
                state.candidate = None
                state.gesture_frames = 0
            return CommonGesturesStatus(gesture=detected, triggered=state.flash_gesture)

        if detected and detected == state.candidate:
            state.gesture_frames += 1
        else:
            state.candidate = detected
            state.gesture_frames = 1 if detected else 0

        if state.gesture_frames >= HOLD_FRAMES_REQUIRED and detected:
            state.flash_gesture = detected
            state.flash_frames = FLASH_FRAMES
            state.gesture_frames = 0
            state.cooldown_frames = COOLDOWN_FRAMES
            state.candidate = None

        return CommonGesturesStatus(gesture=detected, triggered=state.flash_gesture)
