import argparse
import csv
import os
import time
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

try:
    from .constants import ASL_LABELS, IMAGES_DIR, LANDMARKS_CSV
    from .normalization import normalize_landmarks
except ImportError:
    from constants import ASL_LABELS, IMAGES_DIR, LANDMARKS_CSV
    from normalization import normalize_landmarks


def resolve_model_path():
    env_path = os.environ.get("MEDIAPIPE_HAND_MODEL")
    if env_path:
        return Path(env_path).expanduser().resolve()
    # Project root is 3 levels up from this file.
    return Path(__file__).resolve().parents[2] / "hand_landmarker.task"


def create_hand_landmarker(model_path):
    if not model_path.exists():
        raise RuntimeError(
            "Hand Landmarker model not found. Set MEDIAPIPE_HAND_MODEL or place hand_landmarker.task at project root."
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


def ensure_csv_header(csv_path):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if csv_path.exists():
        return

    header = ["label"] + [f"f{i}" for i in range(63)]
    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)


def append_sample(csv_path, label, feature_vector):
    with csv_path.open("a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([label] + [f"{value:.8f}" for value in feature_vector])


def parse_args():
    parser = argparse.ArgumentParser(
        description="Capture ASL training samples for one letter by pressing SPACE."
    )
    parser.add_argument(
        "label",
        type=str,
        help="Target label: A-Z, SPACE, or BACKSPACE",
    )
    parser.add_argument(
        "--max-samples", type=int, default=200, help="Stop after this many captures"
    )
    parser.add_argument(
        "--save-images",
        action="store_true",
        help="Save camera frames alongside landmark data",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    label = args.label.strip().upper()
    if label == " ":
        label = "SPACE"
    if label in {"BKSP", "DELETE", "DEL"}:
        label = "BACKSPACE"

    if label not in ASL_LABELS:
        raise ValueError(f"Invalid label '{args.label}'. Use A-Z, SPACE, or BACKSPACE.")

    model_path = resolve_model_path()
    hand_landmarker = create_hand_landmarker(model_path)

    ensure_csv_header(LANDMARKS_CSV)

    image_out_dir = IMAGES_DIR / label
    if args.save_images:
        image_out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera")

    sample_count = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts_ms = int(time.monotonic() * 1000)
            result = hand_landmarker.detect_for_video(mp_image, ts_ms)

            landmarks = result.hand_landmarks[0] if result.hand_landmarks else None
            feature_vector = normalize_landmarks(landmarks)

            status_color = (
                (40, 220, 40) if feature_vector is not None else (50, 50, 220)
            )
            status_text = "Hand detected" if feature_vector is not None else "No hand"
            cv2.putText(
                frame,
                f"Letter: {label}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                f"Samples: {sample_count}/{args.max_samples}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                status_text,
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                status_color,
                2,
            )
            cv2.putText(
                frame,
                "SPACE: capture, Q: quit",
                (10, frame.shape[0] - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (220, 220, 220),
                1,
            )

            cv2.imshow("ASL Data Capture", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

            if key == ord(" "):
                if feature_vector is None:
                    continue
                append_sample(LANDMARKS_CSV, label, feature_vector)
                sample_count += 1

                if args.save_images:
                    image_path = image_out_dir / f"{label}_{sample_count:05d}.jpg"
                    cv2.imwrite(str(image_path), frame)

                if sample_count >= args.max_samples:
                    break
    finally:
        cap.release()
        hand_landmarker.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
