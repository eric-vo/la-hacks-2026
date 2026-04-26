from pathlib import Path

ASL_LETTERS = [chr(code) for code in range(ord("A"), ord("Z") + 1)]
ASL_SPECIAL_TOKENS = ["SPACE", "BACKSPACE"]
ASL_LABELS = ASL_LETTERS + ASL_SPECIAL_TOKENS

# Landmark indices.
WRIST = 0
MIDDLE_MCP = 9
INDEX_MCP = 5
PINKY_MCP = 17

FEATURE_VECTOR_SIZE = 63  # 21 landmarks x (x, y, z)

# Prediction stabilization.
MIN_LETTER_CONFIDENCE = 0.55
STABLE_FRAMES_REQUIRED = 7
COMMIT_COOLDOWN_FRAMES = 9
REARM_NO_HAND_FRAMES = 3
REARM_CHANGE_FRAMES = 4

# Typed text display.
MAX_BUFFER_CHARS = 48
TYPE_UPPERCASE = False

# Model artifact locations.
ASL_TYPING_DIR = Path(__file__).resolve().parent
DATA_DIR = ASL_TYPING_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
LANDMARKS_CSV = DATA_DIR / "landmarks.csv"
MODELS_DIR = ASL_TYPING_DIR / "models"
STAGE1_MODEL_PATH = MODELS_DIR / "stage1_group_knn.joblib"
MODEL_METADATA_PATH = MODELS_DIR / "model_metadata.json"

# Grouping used by the hierarchical KNN setup.
LETTER_TO_GROUP = {
    "A": "G1",
    "S": "G1",
    "E": "G1",
    "T": "G1",
    "B": "G2",
    "C": "G2",
    "D": "G2",
    "O": "G2",
    "R": "G3",
    "W": "G4",
    "F": "G4",
    "I": "G5",
    "L": "G5",
    "Y": "G5",
    "K": "G6",
    "P": "G6",
    "Q": "G6",
    "X": "G6",
    "Z": "G6",
    # Remaining letters grouped as broad bucket to keep full A-Z coverage.
    "G": "G7",
    "H": "G7",
    "J": "G7",
    # Separate M/N into their own group
    "M": "G8",
    "N": "G8",
    # Separate U and V into distinct groups
    "U": "G9",
    "V": "G10",
    # Special typing controls.
    "SPACE": "G11",
    "BACKSPACE": "G12",
}

# Ensure every trainable label has a group assignment.
for label in ASL_LABELS:
    LETTER_TO_GROUP.setdefault(label, "G7")
