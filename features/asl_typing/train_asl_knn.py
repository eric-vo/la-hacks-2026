import argparse
import csv
import json
from collections import defaultdict

import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier

from features.asl_typing.constants import (
    ASL_LETTERS,
    FEATURE_VECTOR_SIZE,
    LANDMARKS_CSV,
    LETTER_TO_GROUP,
    MODEL_METADATA_PATH,
    MODELS_DIR,
    STAGE1_MODEL_PATH,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Train hierarchical KNN models for ASL letter classification."
    )
    parser.add_argument("--k", type=int, default=5, help="Number of neighbors")
    parser.add_argument(
        "--test-size", type=float, default=0.2, help="Validation split ratio"
    )
    return parser.parse_args()


def load_dataset(csv_path):
    if not csv_path.exists():
        raise FileNotFoundError(f"Training CSV not found: {csv_path}")

    labels = []
    vectors = []
    with csv_path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = row["label"].strip().upper()
            if label not in ASL_LETTERS:
                continue
            vector = [float(row[f"f{i}"]) for i in range(FEATURE_VECTOR_SIZE)]
            labels.append(label)
            vectors.append(vector)

    if not labels:
        raise RuntimeError("No valid samples found in dataset.")

    return np.asarray(vectors, dtype=float), np.asarray(labels)


def train_and_report(model, x, y, test_size):
    if len(np.unique(y)) < 2 or len(y) < 10:
        model.fit(x, y)
        return None

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=test_size, random_state=42, stratify=y
    )
    model.fit(x_train, y_train)
    return model.score(x_test, y_test)


def main():
    args = parse_args()

    x, letters = load_dataset(LANDMARKS_CSV)
    groups = np.asarray([LETTER_TO_GROUP[label] for label in letters])

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    stage1 = KNeighborsClassifier(n_neighbors=args.k)
    stage1_acc = train_and_report(stage1, x, groups, args.test_size)
    joblib.dump(stage1, STAGE1_MODEL_PATH)

    group_to_letters = defaultdict(set)
    for letter, group in zip(letters, groups):
        group_to_letters[group].add(letter)

    group_reports = {}
    for group_name in sorted(set(groups)):
        idx = np.nonzero(groups == group_name)[0]
        x_group = x[idx]
        y_group = letters[idx]
        model = KNeighborsClassifier(n_neighbors=args.k)
        acc = train_and_report(model, x_group, y_group, args.test_size)
        joblib.dump(model, MODELS_DIR / f"group_{group_name}.joblib")
        group_reports[group_name] = {
            "sample_count": int(len(idx)),
            "letters": sorted(group_to_letters[group_name]),
            "accuracy": None if acc is None else float(acc),
        }

    metadata = {
        "k": args.k,
        "feature_size": FEATURE_VECTOR_SIZE,
        "dataset_path": str(LANDMARKS_CSV),
        "stage1_accuracy": None if stage1_acc is None else float(stage1_acc),
        "group_to_letters": {
            group: sorted(letters_set)
            for group, letters_set in sorted(group_to_letters.items())
        },
        "group_reports": group_reports,
    }
    MODEL_METADATA_PATH.write_text(json.dumps(metadata, indent=2))

    print("Saved models to:", MODELS_DIR)
    if stage1_acc is not None:
        print(f"Stage-1 group accuracy: {stage1_acc:.3f}")
    print("Group reports:")
    for group_name, report in group_reports.items():
        acc = report["accuracy"]
        acc_text = "n/a" if acc is None else f"{acc:.3f}"
        print(
            f"- {group_name}: samples={report['sample_count']}, accuracy={acc_text}, letters={','.join(report['letters'])}"
        )


if __name__ == "__main__":
    main()
