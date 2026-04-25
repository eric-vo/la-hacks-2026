from dataclasses import dataclass

import pyautogui

from .classifier import AslHierarchicalClassifier
from .constants import (
    COMMIT_COOLDOWN_FRAMES,
    MAX_BUFFER_CHARS,
    MIN_LETTER_CONFIDENCE,
    STABLE_FRAMES_REQUIRED,
    TYPE_UPPERCASE,
)
from .normalization import normalize_landmarks


@dataclass
class AslTypingStatus:
    active: bool = False
    model_loaded: bool = False
    candidate_letter: str | None = None
    committed_letter: str | None = None
    confidence: float | None = None
    typed_text: str = ""
    stable_frames: int = 0
    cooldown_active: bool = False


class AslTypingFeature:
    def __init__(self):
        pyautogui.PAUSE = 0.0
        pyautogui.FAILSAFE = False

        self.classifier = AslHierarchicalClassifier()
        self.model_loaded = self.classifier.load()

        self.current_candidate = None
        self.candidate_frames = 0
        self.cooldown_frames = 0
        self.typed_text = ""

    def reload_models(self):
        self.model_loaded = self.classifier.load()
        return self.model_loaded

    def process_landmarks(self, landmarks, enabled=True):
        status = AslTypingStatus(active=enabled, model_loaded=self.model_loaded)
        if not enabled:
            return status

        if self.cooldown_frames > 0:
            self.cooldown_frames -= 1
            status.cooldown_active = True

        if not self.model_loaded:
            status.typed_text = self.typed_text
            return status

        feature_vector = normalize_landmarks(landmarks)
        letter, confidence = self.classifier.predict_letter(feature_vector)

        status.confidence = confidence

        if letter is None or confidence is None or confidence < MIN_LETTER_CONFIDENCE:
            self.current_candidate = None
            self.candidate_frames = 0
            status.typed_text = self.typed_text
            return status

        if letter == self.current_candidate:
            self.candidate_frames += 1
        else:
            self.current_candidate = letter
            self.candidate_frames = 1

        status.candidate_letter = self.current_candidate
        status.stable_frames = self.candidate_frames

        if (
            self.cooldown_frames == 0
            and self.candidate_frames >= STABLE_FRAMES_REQUIRED
        ):
            committed = (
                self.current_candidate.upper()
                if TYPE_UPPERCASE
                else self.current_candidate.lower()
            )
            pyautogui.write(committed)
            self.typed_text = (self.typed_text + committed)[-MAX_BUFFER_CHARS:]
            status.committed_letter = committed
            self.cooldown_frames = COMMIT_COOLDOWN_FRAMES
            self.candidate_frames = 0
            self.current_candidate = None

        status.typed_text = self.typed_text
        status.cooldown_active = self.cooldown_frames > 0
        return status
