from dataclasses import dataclass

from pynput.keyboard import Controller, Key


# Landmark indices used for open-palm detection.
INDEX_TIP = 8
INDEX_PIP = 6
MIDDLE_TIP = 12
MIDDLE_PIP = 10
RING_TIP = 16
RING_PIP = 14
PINKY_TIP = 20
PINKY_PIP = 18

# Open-palm gesture: all four fingers must be extended (tip above pip by this margin).
# A positive margin avoids triggering on a relaxed/near-flat hand.
EXTENDED_MARGIN = 0.03

# Frames the gesture must be held before firing (~0.5 s at 30 fps).
# The hold requirement distinguishes this from a passing ASL handshape.
HOLD_FRAMES_REQUIRED = 15

# Frames to ignore input after a trigger fires (~1.5 s at 30 fps).
COOLDOWN_FRAMES = 45

_keyboard = Controller()


def _press_play_pause():
    _keyboard.press(Key.media_play_pause)
    _keyboard.release(Key.media_play_pause)


def _finger_extended(tip, pip) -> bool:
    # In image coordinates y increases downward, so tip.y < pip.y means extended upward.
    return tip.y < (pip.y - EXTENDED_MARGIN)


def _open_palm(landmarks) -> bool:
    if landmarks is None:
        return False
    return (
        _finger_extended(landmarks[INDEX_TIP], landmarks[INDEX_PIP])
        and _finger_extended(landmarks[MIDDLE_TIP], landmarks[MIDDLE_PIP])
        and _finger_extended(landmarks[RING_TIP], landmarks[RING_PIP])
        and _finger_extended(landmarks[PINKY_TIP], landmarks[PINKY_PIP])
    )


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
        detected = _open_palm(landmarks)

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
