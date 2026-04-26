# SignPC

[![SignPC Demo](https://ytcards.demolab.com/?id=N3-DQ1GQZJg&title=SignPC+Demo&lang=en&background_color=%230d1117&title_color=%23ffffff&stats_color=%23dedede&max_title_lines=1&width=600&border_radius=8)](https://www.youtube.com/watch?v=N3-DQ1GQZJg)

Control your computer with only your hand and a webcam — no extra hardware required. SignPC uses MediaPipe to track 21 hand landmarks at 30 FPS and maps gestures to system actions.

Two modes are available, toggled with a thumbs-down gesture:

- **Control mode** — move the cursor and trigger media actions
- **Typing mode** — fingerspell ASL letters to compose text, then send to Gemma for autocorrect

---

## Gesture Reference

### Mode Switch

| Gesture | Action |
| --- | --- |
| Thumbs-down — thumb extended downward, all four fingers folded, hold ~0.2 s | **Toggle** between Control and Typing mode |

### Cursor Control *(Control mode only)*

| Gesture | Action |
| --- | --- |
| C-claw grip — index + thumb extended, other three fingers folded, hold ~0.6 s | **Activate** cursor mode |
| Full fist or all fingers open, hold ~0.5 s | **Deactivate** cursor mode |
| Hand position while active | **Move cursor** (80% thumb tip, 20% index tip weighted) |
| Quick pinch — thumb to index, release fast | **Single click** |
| Two quick pinches in a row | **Double click** |
| Pinch and hold (~0.33 s) | **Click and drag** |

### Media Control *(Control mode only)*

| Gesture | Action |
| --- | --- |
| Open palm — all four fingers fully extended, hold ~0.5 s | **Play / Pause** |

A 1.5 s cooldown prevents accidental re-triggers after the gesture fires.

### ASL Fingerspelling *(Typing mode only)*

Letters are recognized by an ML classifier. Hold a letter shape steady for ~0.25 s to commit it. J and Z require motion (they trace the letter in the air) and are not supported.

| Letter | Hand Shape |
| --- | --- |
| **A** | Fist; thumb rests alongside index finger |
| **B** | Four fingers extended straight up together; thumb folded across palm |
| **C** | All fingers curved into a C; thumb mirrors the curve |
| **D** | Index points up; thumb tip touches middle fingertip; ring + pinky folded |
| **E** | All four fingers bent/curled down at knuckles; thumb tucked underneath |
| **F** | Index tip touches thumb tip (circle); middle, ring, pinky extended |
| **G** | Index points horizontally to the side; thumb points same direction; others folded |
| **H** | Index + middle extended together, pointing horizontally |
| **I** | Pinky extended up; all other fingers in fist |
| **J** | Like I, then trace a J with the pinky *(motion — not supported)* |
| **K** | Index points up; middle angled outward; thumb rests between them |
| **L** | Index points up; thumb points sideways (L shape); others folded |
| **M** | Index, middle, and ring fingers folded over the thumb |
| **N** | Index and middle fingers folded over the thumb |
| **O** | All fingers and thumb curved to meet at tips |
| **P** | Like K but hand tilted to point downward |
| **Q** | Index and thumb point downward; other fingers folded |
| **R** | Index and middle extended and crossed |
| **S** | Fist; thumb folded over the front of the fingers |
| **T** | Fist; thumb inserted between index and middle fingers |
| **U** | Index + middle extended up, side by side; others folded |
| **V** | Index + middle extended up and spread apart; others folded |
| **W** | Index, middle, ring extended and spread; pinky + thumb folded |
| **X** | Index finger hooked at first joint; all others folded |
| **Y** | Thumb + pinky extended; index, middle, ring folded |
| **Z** | Index extended; trace a Z in the air *(motion — not supported)* |

### Gemma AI Autocorrect *(Typing mode only)*

| Gesture | Action |
| --- | --- |
| Thumbs-up — thumb tip well above wrist, four fingers folded, hold ~0.4 s | **Send** accumulated typed letters to Gemma for autocorrect |

Gemma corrects recognition errors and completes the intended word or phrase. Output appears in the dashboard. Requires Ollama running locally (see setup below).

---

## Run the Program

### Web interface (browser dashboard + live camera feed)

**Terminal 1 — Python backend:**

```bash
python3 server.py
```

**Terminal 2 — React frontend:**

```bash
cd frontend
npm install    # first time only
npm run dev
```

Open `http://localhost:5173` in your browser. Click **Get Started** for the live dashboard.

### Standalone OpenCV window (no browser needed)

```bash
python3 main.py
```

---

## Setup

**Python dependencies:**

```bash
pip install -r requirements.txt
```

**Environment file:**

```bash
cp .env.example .env
```

**Gemma / Ollama (optional — needed for AI autocorrect):**

1. Download [Ollama](https://ollama.com/download) and install it
2. Pull the model:

   ```bash
   ollama pull gemma3:1b
   ```

3. Ollama runs automatically in the background after installation. If it ever stops, restart it with `ollama serve`.

The Gemma feature is optional — the rest of SignPC works without it.
