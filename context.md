ASLPC Plan
Below is a clean, copy-pastable full hackathon plan for ASLPC, updated with:
* Proper phase structure
* KNN (including hierarchical grouping) in Phase 3
* Wrist normalization + scale invariance
* PyAutoGUI integration
* ElevenLabs Phase 4
* Clear pain points + focus areas

🧠 ASLPC — Full Hackathon Implementation Plan
🎯 Core Idea
ASLPC is a real-time hand interaction system that enables:
* Mouse control via hand tracking
* Gesture-based OS shortcuts
* ML-based ASL-inspired typing (KNN)
* Phrase-based speech output for communication
Powered by:
* MediaPipe Hands (landmarks)
* KNN classification (scikit-learn)
* PyAutoGUI (system automation)
* ElevenLabs (text-to-speech)

🏗️ SYSTEM ARCHITECTURE
Camera Input
   ↓
MediaPipe Hands (21 landmarks)
   ↓
Normalization Layer (wrist centering + scaling)
   ↓
Feature Extraction
   ↓
Decision Layer:
   ├── Phase 1: Cursor Control (rules)
   ├── Phase 2: Gesture Shortcuts (rules)
   ├── Phase 3: KNN Typing System (ML)
   └── Phase 4: Phrase Speech System
   ↓
Action Layer:
   ├── PyAutoGUI (OS control)
   └── ElevenLabs (voice output)

🥇 PHASE 1 — CURSOR + CLICK SYSTEM (RULE-BASED)
🎯 Goal
Enable full mouse control using hand tracking.
🔧 Implementation
* Index fingertip → cursor position
* Thumb + index pinch → click
Cursor mapping:
* Normalize hand coordinates
* Map to screen resolution
Click detection:
if distance(thumb_tip, index_tip) < threshold:
    trigger_click()
⚠️ Pain points
* Cursor jitter → requires smoothing
* Accidental clicks → require hold (200–300ms confirmation)
* Hand loss in frame → add fallback state
🎯 Focus
* Smooth movement > accuracy
* Stable click behavior > features

🥈 PHASE 2 — GESTURE SHORTCUT SYSTEM (RULE-BASED)
🎯 Goal
Trigger OS-level actions using gestures.
Example gestures:
* ✊ → play/pause
* ✌️ → switch tab
* 👍 → enter
* 👎 → backspace
* 🤟 → toggle mode
Implementation:
pyautogui.press("space")
pyautogui.hotkey("ctrl", "tab")
⚠️ Pain points
* Gesture overlap → reduce to 5–7 max gestures
* False triggers → require hold or stability window
* Mode confusion → introduce explicit system modes
🎯 Focus
* Reliability > variety
* Clear gesture definitions

🥉 PHASE 3 — KNN ASL TYPING SYSTEM (ML CORE)
🎯 Goal
Translate hand gestures into letters using KNN classification.

🧠 STEP 1 — LANDMARK NORMALIZATION (CRITICAL)
Using MediaPipe:
1. Wrist centering
Make wrist the origin:
for point in landmarks:
    point.x -= wrist.x
    point.y -= wrist.y
    point.z -= wrist.z

2. Scale normalization (fix hand size differences)
Compute hand scale:
scale = distance(wrist, middle_mcp)
Normalize:
for point in landmarks:
    point /= scale
✔ Fixes:
* Different hand sizes
* Distance from camera
* User variability

🧠 STEP 2 — FEATURE EXTRACTION
Base features:
* 21 landmarks × (x, y, z) = 63 features
Optional enhancements:
* Finger extended states (binary)
* Key fingertip distances
* Finger curl approximations

🧠 STEP 3 — HIERARCHICAL KNN (RECOMMENDED DESIGN)
Instead of one 26-class model:

Stage 1 — Shape Group Classifier
Groups based on hand geometry:
* G1: A, S, E, T (fist-like)
* G2: B, C, D, O (flat/open)
* G3: V, U, R (two fingers)
* G4: W, F (three fingers)
* G5: I, L, Y (single-finger variants)
* G6: K, P, Q, X, Z (special shapes)
Output → group ID

Stage 2 — Group-specific KNN
Each group has its own classifier:
G3 → KNN(V, U, R)
G1 → KNN(A, S, E, T)
Using:
KNeighborsClassifier(n_neighbors=3)

Why this works better:
* Reduces confusion space
* Improves accuracy on similar letters
* Requires fewer samples per model

🧠 STEP 4 — TRAINING PIPELINE
Dataset:
* 20–30 samples per letter
* ~500–700 total samples (if full 26 letters)
Tool:
* Custom recorder:
    * press key → label gesture
    * store normalized feature vector

🧠 STEP 5 — REAL-TIME INFERENCE LOOP
frame →
  MediaPipe →
  normalization →
  feature extraction →
  group classifier →
  letter KNN →
  smoothing →
  output

🧠 STEP 6 — TEMPORAL SMOOTHING (MANDATORY)
Prevent flickering outputs:
if same_prediction_for_5_to_10_frames:
    confirm_letter()
Add:
* cooldown per letter (300–500ms)
* neutral/no-hand class (optional but useful)

⚠️ PHASE 3 PAIN POINTS
❌ Similar letters collapse
* A/S/E, M/N/T, U/V/R
Fix:
* grouping system
* add distance-based features

❌ Dataset bias (single user)
Fix:
* multiple users OR calibration step

❌ Noisy outputs → typing spam
Fix:
* smoothing + cooldown

❌ Bad normalization breaks everything
Fix:
* wrist centering + scale normalization is non-negotiable

🎯 Focus for Phase 3
* stable pipeline > full alphabet
* correctness > completeness
* clean feature engineering > model complexity

🏁 PHASE 4 — PHRASE-BASED SPEECH OUTPUT
Powered by ElevenLabs:
* ElevenLabs

🎯 Goal
Convert gestures into spoken phrases for real-time communication.

Instead of letters → speech
Use direct mapping:
Gesture	Phrase
✊	“Hello”
☝️	“I need help”
✌️	“Thank you”
🤟	“One moment please”
👌	“Yes”
👎	“No”
Pipeline:
gesture →
  phrase buffer →
  confirm →
  ElevenLabs TTS →
  audio output

⚠️ Pain points
❌ Over-speaking
Fix:
* cooldown between speech events
❌ API latency
Fix:
* batch phrases, not single words
❌ accidental triggers
Fix:
* hold gesture or explicit "send"

🧭 GLOBAL SYSTEM RISKS
1. Mode confusion (major risk)
Fix:
* explicit modes:
    * cursor
    * shortcuts
    * typing

2. Latency stacking
Fix:
* async speech calls
* keep inference local

3. Debug complexity
Fix:
* strict build order:
    1. cursor
    2. shortcuts
    3. KNN
    4. speech

🗓️ BUILD ORDER (CRITICAL)
Day 1
1. Cursor + click (perfect it)
2. smoothing
3. gesture shortcuts
Day 2
1. normalization system
2. hierarchical KNN system
3. typing output
Stretch
1. ElevenLabs speech layer

🧭 FINAL SUMMARY
ASLPC is NOT just an ML project.
It is a:
real-time hand-driven computer interface with layered intelligence
Core design principle:
* Rules for control (reliable)
* KNN for recognition (flexible)
* Phrase mapping for speech (usable)
