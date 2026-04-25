import math

from constants import INDEX_MCP, MIDDLE_MCP, PINKY_MCP, WRIST


def _distance(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def normalize_landmarks(landmarks):
    """Return a 63-length wrist-centered, scale-normalized feature vector."""
    if not landmarks:
        return None

    wrist = landmarks[WRIST]
    centered = []
    for point in landmarks:
        centered.append((point.x - wrist.x, point.y - wrist.y, point.z - wrist.z))

    scale = max(
        _distance(landmarks[WRIST], landmarks[MIDDLE_MCP]),
        _distance(landmarks[WRIST], landmarks[INDEX_MCP]),
        _distance(landmarks[WRIST], landmarks[PINKY_MCP]),
        1e-6,
    )

    features = []
    for x, y, z in centered:
        features.extend((x / scale, y / scale, z / scale))

    return features
