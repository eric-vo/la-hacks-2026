import json
from pathlib import Path

import joblib
import numpy as np

from .constants import MODEL_METADATA_PATH, MODELS_DIR, STAGE1_MODEL_PATH


class AslHierarchicalClassifier:
    def __init__(self):
        self.loaded = False
        self.stage1 = None
        self.group_models = {}
        self.group_labels = {}

    def load(self):
        if not STAGE1_MODEL_PATH.exists() or not MODEL_METADATA_PATH.exists():
            self.loaded = False
            return False

        self.stage1 = joblib.load(STAGE1_MODEL_PATH)
        metadata = json.loads(MODEL_METADATA_PATH.read_text())
        self.group_labels = metadata.get("group_to_letters", {})

        group_models = {}
        for model_path in MODELS_DIR.glob("group_*.joblib"):
            group_name = model_path.stem.removeprefix("group_")
            group_models[group_name] = joblib.load(model_path)

        self.group_models = group_models
        self.loaded = True
        return True

    def predict_letter(self, feature_vector):
        """Return (letter, confidence) or (None, None)."""
        if not self.loaded or feature_vector is None:
            return None, None

        x = np.asarray(feature_vector, dtype=float).reshape(1, -1)

        group_name = self.stage1.predict(x)[0]
        group_model = self.group_models.get(group_name)
        if group_model is None:
            return None, None

        letter = group_model.predict(x)[0]

        group_conf = _vote_confidence(self.stage1, x)
        letter_conf = _vote_confidence(group_model, x)
        confidence = group_conf * letter_conf

        return letter, float(confidence)


def _vote_confidence(knn_model, x):
    neighbors = knn_model.kneighbors(x, return_distance=False)[0]
    neighbor_labels = knn_model._y[neighbors]
    _, counts = np.unique(neighbor_labels, return_counts=True)
    if len(counts) == 0:
        return 0.0
    return counts.max() / counts.sum()
