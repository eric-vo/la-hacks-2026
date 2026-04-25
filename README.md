# Hand Bridge
## Hand Gesture Computer Control (TBA)

Control your mouse and media playback using only your hand and a webcam; no hardware required. The app uses MediaPipe to track 21 hand landmarks in real time and maps gestures to system actions. A "lobster grip" (thumb and index finger extended, others folded) activates cursor mode, where your hand position drives the mouse and a pinch registers as a click. Holding an open palm for half a second triggers play/pause on whatever media is playing.

## Media Controls

Play/Pause video/music = stop hand (🤚)

## Common Gestures

| Message | Gesture |
|---------|---------|
| Yes | thumbs up |
| No |thumbs down |

## Run the Program

**Terminal 1 -- Gesture Backend:**
```
python3 main.py
```

**Terminal 2 -- React Frontend:**
```
cd frontend
npm install
npm fund
npm run dev
```

- npm install     # first time
- npm fund     # first time
- npm run dev     # opens http://localhost:5173
