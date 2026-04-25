# HandBridge

Control your computer using only your hand and a webcam — no extra hardware required. HandBridge uses MediaPipe to track 21 hand landmarks in real time and maps gestures to cursor movement, clicks, and media controls.

---

## Gesture Reference

### Cursor Control

| Gesture | Action |
| --- | --- |
| ☝️ Index finger extended up, other three fingers folded | **Activate** cursor mode (hold ~0.6 s) |
| ✊ Open all fingers or make a full fist | **Deactivate** cursor mode (hold ~0.5 s) |
| Hand position while active | **Move cursor** (index + thumb tip weighted average) |
| 🤏 Quick pinch — thumb to index, release fast | **Single click** |
| 🤏🤏 Two quick pinches in a row | **Double click** |
| 🤏🤏🤏 Three quick pinches in a row | **Triple click** |
| 🤏 Pinch and hold (~0.33 s) | **Click and drag** |

### Media Controls

| Gesture | Action |
| --- | --- |
| 🤚 Open palm — all four fingers extended, hold ~0.5 s | **Play / Pause** |

A 1.5 s cooldown prevents accidental re-triggers immediately after the gesture fires.

---

## Run

**Terminal 1 — Python backend:**

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
