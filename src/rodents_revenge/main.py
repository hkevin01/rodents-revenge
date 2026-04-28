"""
# /// script
# dependencies = [
#   "pygame-ce",
# ]
# ///
"""

import asyncio

# Ensure pygbag resolves and preloads the pygame-ce runtime for web builds.
import pygame  # noqa: F401

# Support both: `python -m rodents_revenge.main` (desktop, PYTHONPATH=src)
# and pygbag: `pygbag src/rodents_revenge`  (flat-package web build)
try:
    from rodents_revenge.game import run_game
except ImportError:
    from game import run_game  # type: ignore[no-redef]


if __name__ == "__main__":
    asyncio.run(run_game())

