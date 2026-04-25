import math
from dataclasses import dataclass

from pynput.keyboard import Controller, Key


# Landmark indices used for stop-hand detection.
THUMB_TIP = 4
WRIST = 0
INDEX_MCP = 5
PINKY_MCP = 17
INDEX_TIP = 8
INDEX_PIP = 6
MIDDLE_TIP = 12
MIDDLE_PIP = 10
RING_TIP = 16
RING_PIP = 14
PINKY_TIP = 20
PINKY_PIP = 18

# All four fingers must clear their PIP joint by this margin to count as extended.
EXTENDED_MARGIN = 0.03

# Thumb tip distance to index MCP, relative to palm size, must be below this to
# count as tucked — this is what separates a stop hand from an open palm / ASL-5.
THUMB_TUCKED_RATIO = 0.60

# Frames the gesture must be held before firing (~0.5 s at 30 fps).
HOLD_FRAMES_REQUIRED = 15

# Frames to ignore input after a trigger fires (~1.5 s at 30 fps).
COOLDOWN_FRAMES = 45

_keyboard = Controller()


def _press_play_pause():
    _keyboard.press(Key.media_play_pause)
    _keyboard.release(Key.media_play_pause)


def _euclidean(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _palm_size(landmarks) -> float:
    wrist = landmarks[WRIST]
    return max(
        _euclidean(wrist, landmarks[INDEX_MCP]),
        _euclidean(wrist, landmarks[PINKY_MCP]),
        1e-6,
    )


def _finger_extended(tip, pip) -> bool:
    # In image coordinates y increases downward, so tip.y < pip.y means extended upward.
    return tip.y < (pip.y - EXTENDED_MARGIN)


def _stop_hand(landmarks) -> bool:
    if landmarks is None:
        return False
    if not (
        _finger_extended(landmarks[INDEX_TIP], landmarks[INDEX_PIP])
        and _finger_extended(landmarks[MIDDLE_TIP], landmarks[MIDDLE_PIP])
        and _finger_extended(landmarks[RING_TIP], landmarks[RING_PIP])
        and _finger_extended(landmarks[PINKY_TIP], landmarks[PINKY_PIP])
    ):
        return False
    psize = _palm_size(landmarks)
    thumb_to_index_mcp = _euclidean(landmarks[THUMB_TIP], landmarks[INDEX_MCP])
    return (thumb_to_index_mcp / psize) < THUMB_TUCKED_RATIO


@dataclass
class MediaState:
    gesture_frames: int = 0
    cooldown_frames: int = 0


@dataclass
class MediaStatus:
    gesture_detected: bool = False
    triggered: bool = False
    cooldown_active: bool = False


class MediaControlFeature:
    def __init__(self):
        self.state = MediaState()

    def process_landmarks(self, landmarks) -> MediaStatus:
        state = self.state
        detected = _stop_hand(landmarks)

        if state.cooldown_frames > 0:
            state.cooldown_frames -= 1
            if not detected:
                state.gesture_frames = 0
            return MediaStatus(gesture_detected=detected, cooldown_active=True)

        if detected:
            state.gesture_frames += 1
        else:
            state.gesture_frames = 0

        triggered = False
        if state.gesture_frames >= HOLD_FRAMES_REQUIRED:
            _press_play_pause()
            state.gesture_frames = 0
            state.cooldown_frames = COOLDOWN_FRAMES
            triggered = True

        return MediaStatus(gesture_detected=detected, triggered=triggered)
