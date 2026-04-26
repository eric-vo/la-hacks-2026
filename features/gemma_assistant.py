"""Thin wrapper around the local Ollama Gemma model.

Runs inference in a daemon thread so it never blocks the camera loop.
The latest prediction is stored in a shared dict and broadcast via WebSocket.
"""
import threading

import httpx
from ollama import chat

MODEL = "gemma3:1b"
OLLAMA_BASE = "http://localhost:11434"

_lock = threading.Lock()
_state: dict = {"prediction": "", "thinking": False, "error": ""}
_last_submitted: str = ""


def _ollama_reachable() -> bool:
    try:
        r = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=2.0)
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False


def _messages(signed_text: str) -> list[dict]:
    return [
        {
            "role": "user",
            "content": (
                "You are an autocorrect and sentence-completion assistant for someone "
                "communicating via ASL fingerspelling. They sign one letter at a time; "
                "recognition is imperfect so there may be errors or missing letters.\n\n"
                f"Signed letters so far: {signed_text}\n\n"
                "Complete or correct this into the most likely English word or short phrase "
                "the person intends to send. If the phrase is a sentence, capitalize and punctuate it. "
                "Otherwise, reply with ONLY the corrected text — "
                "no explanation, no punctuation unless grammatically required."
            ),
        }
    ]


def _run(text: str) -> None:
    with _lock:
        _state["thinking"] = True
        _state["error"] = ""
    try:
        if not _ollama_reachable():
            with _lock:
                _state["error"] = "Ollama offline — run: ollama serve"
            print("[gemma] Ollama is not running. Start it with: ollama serve")
            return
        resp = chat(model=MODEL, messages=_messages(text))
        with _lock:
            _state["prediction"] = resp.message.content.strip()
            _state["error"] = ""
    except Exception as exc:  # noqa: BLE001
        print(f"[gemma] inference error: {exc}")
        with _lock:
            _state["error"] = f"Error: {exc}"
            _state["prediction"] = ""
    finally:
        with _lock:
            _state["thinking"] = False


def submit(text: str) -> None:
    """Fire a non-blocking Gemma inference for the given typed text.

    Skips if Gemma is already thinking or the text hasn't changed.
    """
    global _last_submitted  # noqa: PLW0603
    with _lock:
        if _state["thinking"] or text == _last_submitted:
            return
        _last_submitted = text

    threading.Thread(target=_run, args=(text,), daemon=True).start()


def get_state() -> dict:
    """Return a snapshot of {prediction, thinking, error} safe to read from any thread."""
    with _lock:
        return dict(_state)
