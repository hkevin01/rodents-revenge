from __future__ import annotations

import json
from pathlib import Path

_SCORES_FILE = Path(__file__).resolve().parents[2] / "scores.json"
MAX_SCORES = 10


def load_scores() -> list[dict]:
    if not _SCORES_FILE.exists():
        return []
    try:
        data = json.loads(_SCORES_FILE.read_text())
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_score(score: int, level: int) -> None:
    if score <= 0:
        return
    scores = load_scores()
    scores.append({"score": score, "level": level})
    scores.sort(key=lambda s: s["score"], reverse=True)
    try:
        _SCORES_FILE.write_text(json.dumps(scores[:MAX_SCORES], indent=2))
    except OSError:
        pass


def is_high_score(score: int) -> bool:
    if score <= 0:
        return False
    scores = load_scores()
    if len(scores) < MAX_SCORES:
        return True
    return score > scores[-1]["score"]
