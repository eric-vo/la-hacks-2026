import json
import os
from datetime import datetime
from pathlib import Path

_LOG_FILE = Path(__file__).parent / "frontend" / "public" / "events.json"
_MAX_EVENTS = 200

_counter: int = 1
_initialized: bool = False


def _ensure_initialized() -> None:
    global _counter, _initialized
    if _initialized:
        return
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _LOG_FILE.exists():
        try:
            data = json.loads(_LOG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                _counter = data[-1].get("id", 0) + 1
        except (json.JSONDecodeError, OSError):
            pass
    else:
        _LOG_FILE.write_text("[]", encoding="utf-8")
    _initialized = True


def log_event(event_type: str, label: str) -> None:
    global _counter
    _ensure_initialized()

    try:
        events = json.loads(_LOG_FILE.read_text(encoding="utf-8"))
        if not isinstance(events, list):
            events = []
    except (json.JSONDecodeError, OSError):
        events = []

    events.append({
        "id": _counter,
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        "label": label,
    })
    _counter += 1

    if len(events) > _MAX_EVENTS:
        events = events[-_MAX_EVENTS:]

    # Atomic write so the React app never reads a partial file.
    tmp = _LOG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(events, indent=2), encoding="utf-8")
    os.replace(tmp, _LOG_FILE)
