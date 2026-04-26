# ASL Typing Feature (Phase 3)

This feature adds ASL letter typing using hand landmarks and hierarchical KNN models.

## 1) Capture training data

From project root:

python features/asl_typing/capture_train_data.py A --save-images

- Use the target label as the first argument:
  - `A-Z` for letter typing
  - `SPACE` for typing a space
  - `BACKSPACE` for deleting one character
- Press SPACE to capture one sample.
- Press Q to quit.
- Landmark vectors are appended to:
  - features/asl_typing/data/landmarks.csv
- Optional images are saved under:
  - features/asl_typing/data/images/<LETTER>/

Repeat for all labels you want to support.

## 2) Train models

python features/asl_typing/train_asl_knn.py --k 5

Artifacts are written to:
- features/asl_typing/models/stage1_group_knn.joblib
- features/asl_typing/models/group_<GROUP>.joblib
- features/asl_typing/models/model_metadata.json

## 3) Run app and type letters

python main.py

In the camera window:
- Press 4 to switch to typing mode.
- Sign letters to the camera.
- When the prediction is stable, the committed letter is typed to the OS.
- Overlay shows candidate, confidence, and typed text buffer.

Other modes:
- 1 = cursor
- 2 = media
- 3 = common gestures
- r = reload ASL models without restarting
