# HandBridge

Control your mouse and media playback using only your hand and a webcam; no hardware required. The app uses MediaPipe to track 21 hand landmarks in real time and maps gestures to system actions. A C-claw grip (index extended, thumb extended, others folded) activates cursor mode, where your hand position drives the mouse and a pinch registers as a click. Holding an open palm for half a second triggers play/pause on whatever media is playing.

---

## Gesture Reference

### Cursor Control

| Gesture | Action |
| --- | --- |
| C-claw grip — index + thumb extended, other three fingers folded | **Activate** cursor mode (hold ~0.6 s) |
| Full fist or all fingers open | **Deactivate** cursor mode (hold ~0.5 s) |
| Hand position while active | **Move cursor** (80% thumb tip, 20% index tip weighted average) |
| Quick pinch — thumb to index, release fast | **Single click** |
| Two quick pinches in a row | **Double click** |
| Three quick pinches in a row | **Triple click** |
| Pinch and hold (~0.33 s) | **Click and drag** |

### Media Controls

| Gesture | Action |
| --- | --- |
| Open palm — all four fingers extended, hold ~0.5 s | **Play / Pause** |

A 1.5 s cooldown prevents accidental re-triggers immediately after the gesture fires.

### ASL Fingerspelling (A–Z)

> Letters J and Z require motion (they trace the letter shape in air) and are not supported in the static rule-based recognizer.

| Letter | Hand Shape |
| --- | --- |
| **A** | Fist; thumb rests alongside index finger, not over fingers |
| **B** | Four fingers extended straight up and together; thumb folded across palm |
| **C** | All fingers curved into a C shape; thumb mirrors the curve |
| **D** | Index points up; thumb tip touches middle finger tip; ring + pinky folded |
| **E** | All four fingers bent/curled down at knuckles; thumb tucked underneath |
| **F** | Index tip touches thumb tip (circle); middle, ring, pinky extended |
| **G** | Index points horizontally to the side; thumb points same direction; others folded |
| **H** | Index + middle extended together, pointing horizontally to the side |
| **I** | Pinky extended up; all other fingers folded into fist |
| **J** | Like I, then trace a J with the pinky *(motion — not supported)* |
| **K** | Index points up; middle angled outward; thumb rests between them |
| **L** | Index points up; thumb points out sideways forming an L; others folded |
| **M** | Index, middle, and ring fingers folded over the thumb |
| **N** | Index and middle fingers folded over the thumb |
| **O** | All fingers and thumb curved to meet at tips, forming an O |
| **P** | Like K but entire hand tilted to point downward |
| **Q** | Index and thumb point downward; other fingers folded |
| **R** | Index and middle fingers extended and crossed |
| **S** | Fist; thumb folded over the front of the fingers |
| **T** | Fist; thumb inserted between index and middle fingers |
| **U** | Index + middle extended up together (side by side); others folded |
| **V** | Index + middle extended up and spread apart (peace sign); others folded |
| **W** | Index, middle, and ring extended and spread; pinky + thumb folded |
| **X** | Index finger bent/hooked at first joint; all others folded |
| **Y** | Thumb + pinky extended; index, middle, ring folded |
| **Z** | Index extended; trace a Z in the air *(motion — not supported)* |

---

## Run the Program

**Terminal 1 — Python backend (web mode):**

```bash
python3 server.py
```

**Terminal 2 — React frontend:**

```bash
cd frontend
npm install    # first time only
npm run dev    # opens http://localhost:5173
```

Navigate to `http://localhost:5173/live` for the live camera feed and gesture status dashboard.

Alternatively, run the standalone OpenCV window (no web frontend):

```bash
python3 main.py
```

---

## Requirements

```bash
pip install -r requirements.txt
```

Dependencies: `mediapipe`, `opencv-python`, `pyautogui`, `pynput`, `python-dotenv`, `fastapi`, `uvicorn[standard]`

Copy `.env.example` to `.env` before running:

```bash
cp .env.example .env
```
