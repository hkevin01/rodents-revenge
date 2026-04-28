from __future__ import annotations

import json
import sys
from pathlib import Path

_SCORES_FILE = Path(__file__).resolve().parents[2] / "scores.json"
_LS_KEY = "rodents_revenge_scores"   # localStorage key for web sessions
MAX_SCORES = 10


def _is_web() -> bool:
    return sys.platform == "emscripten"


def _web_load() -> list[dict]:
    """Read scores from browser localStorage."""
    try:
        import platform  # type: ignore[import]
        raw = platform.window.localStorage.getItem(_LS_KEY)
        if raw is None:
            return []
        data = json.loads(raw)
        if isinstance(data, list):
            for entry in data:
                entry.setdefault("initials", "---")
            return data
    except Exception:
        pass
    return []


def _web_save(scores: list[dict]) -> None:
    """Write scores to browser localStorage."""
    try:
        import platform  # type: ignore[import]
        platform.window.localStorage.setItem(_LS_KEY, json.dumps(scores))
    except Exception:
        pass


def load_scores() -> list[dict]:
    if _is_web():
        return _web_load()
    if not _SCORES_FILE.exists():
        return []
    try:
        data = json.loads(_SCORES_FILE.read_text())
        if isinstance(data, list):
            for entry in data:
                entry.setdefault("initials", "---")
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_score(score: int, level: int, initials: str = "---") -> None:
    if score <= 0:
        return
    inits = (initials.strip().upper() or "---")[:3].ljust(3, "-")
    scores = load_scores()
    scores.append({"score": score, "level": level, "initials": inits})
    scores.sort(key=lambda s: s["score"], reverse=True)
    trimmed = scores[:MAX_SCORES]
    if _is_web():
        _web_save(trimmed)
    else:
        try:
            _SCORES_FILE.write_text(json.dumps(trimmed, indent=2))
        except OSError:
            pass


def is_high_score(score: int) -> bool:
    if score <= 0:
        return False
    scores = load_scores()
    if len(scores) < MAX_SCORES:
        return True
    return score > scores[-1]["score"]
