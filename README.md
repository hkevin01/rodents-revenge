<div align="center">

# 🐭 Rodent Rumble

**A Python/pygame-ce clone of the classic Rodent's Revenge puzzle game**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![pygame-ce](https://img.shields.io/badge/pygame--ce-2.5%2B-orange?logo=pygame)](https://pyga.me/)
[![Tests](https://img.shields.io/badge/tests-40%20passing-brightgreen?logo=pytest)](tests/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows%20%7C%20iPad-lightgrey)](#play-on-ipad--web)

*Push blocks. Trap cats. Collect cheese. Survive.*

</div>

---

## 📋 Table of Contents

- [About](#about)
- [Features](#features)
- [Play on iPad / Web](#play-on-ipad--web)
- [Quick Start](#quick-start)
- [Controls](#controls)
- [How to Play](#how-to-play)
- [Scoring](#scoring)
- [Room Themes](#room-themes)
- [Level Progression](#level-progression)
- [Difficulty Modes](#difficulty-modes)
- [Project Structure](#project-structure)
- [Docker](#docker)
- [Running Tests](#running-tests)
- [Contributing](#contributing)

---

## About

Rodent Rumble is an open-source Python remake of the classic Windows puzzle game *Rodent's Revenge* (Microsoft, 1991). Guide your mouse around a grid, push cardboard boxes to surround and trap orange cats, then collect the cheese they leave behind.

Built with **pygame-ce** and fully playable in a browser on **iPad** via [pygbag](https://pygame-web.github.io/) WebAssembly — no install required.

---

## Features

- [x] **6 hand-crafted room themes** — Kitchen, Dining Room, Living Room, Bedroom, Bathroom, Attic — cycling every 10 levels
- [x] **3 difficulty modes** — Easy, Normal, Hard with adjusted cat speed and count
- [x] **10 hand-designed levels** followed by seeded procedural generation up to level 100+
- [x] **Multi-trap combo scoring** — trap multiple cats in one move for big bonuses
- [x] **Diagonal cat movement** — cats can move diagonally, making trapping more challenging
- [x] **3-2-1-GO countdown** on level start, level-up, and respawn — cats can't move until GO
- [x] **Cat speed acceleration** — ramps up every level, with steeper acceleration past level 20
- [x] **Floating virtual joystick** for iPad / touchscreen play
- [x] **Animated sprites** with graceful fallback to procedural vector art
- [x] **Persistent high scores** — top 10 with 3-letter initials, saved per-browser on web
- [x] **Line-of-sight cat alerts** — orange glow when a cat has a clear shot at you
- [x] **Block-push tweening** — smooth animation when shoving boxes
- [x] **Procedural sound effects** — no external audio files needed
- [x] **Sound toggle** — mute/unmute via the HUD button or `M` key
- [x] **Polished title screen** — animated PLAY button, high scores panel, difficulty selector
- [x] **Docker support** for headless CI testing

---

## Play on iPad / Web

> [!IMPORTANT]
> The game compiles to **WebAssembly** via [pygbag](https://pygame-web.github.io/) and runs directly in Safari on iPad (iOS 15+) or any modern browser — no App Store, no install.

**Live URL (after first GitHub Actions deploy):**
```
https://hkevin01.github.io/rodents-revenge/
```

### Deploy to GitHub Pages yourself

1. Push this repo to GitHub
2. Go to **Settings → Pages** → set source branch to `gh-pages`
3. Go to **Settings → Actions → General** → set Workflow permissions to **Read and write**
4. Trigger the **"Build & Deploy to GitHub Pages"** action from the **Actions** tab

The workflow at [.github/workflows/pygbag.yml](.github/workflows/pygbag.yml) builds and deploys automatically on every push to `main`.

> [!TIP]
> On iPad, tap the **left side of the screen** to spawn the floating virtual joystick. The game detects touch automatically — no special mode needed.

---

## Quick Start

### Prerequisites

- Python 3.10 or newer
- A display (or use Docker for headless testing)

### Install & Run

```bash
# Clone the repo
git clone https://github.com/hkevin01/rodents-revenge.git
cd rodents-revenge

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the game
PYTHONPATH=src python -m rodents_revenge.main
```

> [!NOTE]
> On **Windows**, omit `PYTHONPATH=src` and run from the repo root after installing:
> ```bat
> set PYTHONPATH=src
> python -m rodents_revenge.main
> ```

### Build for Web / iPad

```bash
pip install -r requirements-web.txt
python -m pygbag --build src/rodents_revenge
# Output: build/web/  — open build/web/index.html in a browser
```

---

## Controls

### Keyboard

| Key | Action |
|---|---|
| `Arrow Keys` / `WASD` | Move the mouse |
| `P` | Pause / Resume |
| `H` | Show / hide controls help |
| `M` | Toggle sound on/off |
| `R` | Restart *(game-over screen)* |
| `Enter` | Confirm / start game / back to menu |
| `Esc` | Quit *(goes to menu on web)* |
| `←` / `→` on title screen | Change difficulty |

### Touch / iPad

| Gesture | Action |
|---|---|
| Tap left side of screen | Spawn floating joystick there |
| Drag joystick thumb | Move the mouse (4-way) |
| Tap **PAUSE** button | Pause / Resume |
| Tap **HELP** button | Toggle controls overlay |
| Tap **SND ON / SND OFF** button | Toggle sound |
| Tap **⬅ MENU** / **↺ RESTART** | Game-over navigation |
| Tap **DONE** on initials screen | Submit high score initials |

---

## How to Play

```
┌─────────────────────────────────────┐
│  Walls (fixed)   Blocks (pushable)  │
│  🐭 Mouse        🐱 Cat (orange)    │
│  🧀 Cheese       Empty floor        │
└─────────────────────────────────────┘
```

1. **Move** your mouse with arrow keys or the virtual joystick
2. **Push blocks** — walk into a block to slide it one cell (only if the cell behind it is free)
3. **Trap a cat** — surround it on all **8 sides** (including diagonals) with blocks, walls, or the board edge
4. Trapped cats **turn into cheese** 🧀
5. **Walk over cheese** to collect it for points
6. **Clear the level** by trapping all cats

> [!WARNING]
> Cats move diagonally! A cat can slip past a gap you thought was closed. Each new level and every respawn starts with a **3-2-1-GO** countdown — cats don't move until GO.

---

## Scoring

| Event | Points |
|---|---|
| Each step taken | +1 |
| Collect a cheese tile | +25 |
| Trap a single cat | +100 |
| Multi-trap bonus (per extra cat beyond the first) | +150 |

**Multi-trap example:** Trap 3 cats at once → `3 × 100 + 2 × 150 = 600 pts`

High scores are saved in your **browser (localStorage)** when playing on web, or in `scores.json` locally. Top 10 scores with 3-letter initials are shown on the title screen.

---

## Room Themes

The room changes every **10 levels**, cycling through 6 unique environments. Each theme reskins the floor, walls, and cardboard boxes.

| Levels | Room | Floor Style | Palette |
|---|---|---|---|
| 1–10 | 🍳 Kitchen | Checkerboard tile | Cream & near-black ceramic |
| 11–20 | 🍽️ Dining Room | Wood planks | Warm oak tones |
| 21–30 | 🛋️ Living Room | Burgundy carpet | Deep reds & tans |
| 31–40 | 🛏️ Bedroom | Lavender carpet | Soft lilac & purple |
| 41–50 | 🚿 Bathroom | Checkerboard tile | Sky blue & seafoam |
| 51–60 | 🏚️ Attic | Rough planks | Dusty grey-browns |
| 61+ | 🔄 *Cycles back* | — | — |

---

## Level Progression

<details>
<summary><strong>Click to expand level generation details</strong></summary>

### Levels 1–10 — Hand-crafted Presets

Ten carefully designed layouts with fixed wall structures, predefined cheese locations, and a set number of cats. Great for learning block-pushing patterns.

### Levels 11–100 — Seeded Procedural

Levels beyond 10 use a seeded generator (seed = level number) so the same level always looks the same on every play-through. Difficulty ramps up in **tiers of 10**:

| Tier | Levels | Cats | Blocks |
|---|---|---|---|
| 0 | 11–20 | 3 | 38 |
| 1 | 21–30 | 3 | 42 |
| 2 | 31–40 | 4 | 46 |
| 3 | 41–50 | 4 | 50 |
| 4 | 51–60 | 5 | 54 |
| 5 | 61–70 | 5 | 58 |
| 6 | 71–80 | 6 | 62 |
| 7 | 81–90 | 6 | 66 |
| 8 | 91–100 | 7 | 70 |
| 9 | 101–110 | 8 | 74 |

### Levels 111+ — Fully Procedural

Pure random generation: up to 12 cats and dense block placement. No two runs are the same.

</details>

---

## Difficulty Modes

Selected on the title screen before starting a game. Cat base speed is **2000 ms per step** at level 1.

| Mode | Cat Speed | Cat Count |
|---|---|---|
| Easy | +250 ms slower (2250 ms base) | −1 cat per level |
| Normal | baseline (2000 ms base) | baseline |
| Hard | −125 ms faster (1875 ms base) | +1 cat per level |

### Cat Speed Acceleration

Cat speed increases each level regardless of difficulty:

- **Levels 1–20:** −20 ms per level (e.g. level 10 → 1800 ms)
- **Levels 21+:** an additional −50 ms per level on top of the base ramp
- **Floor:** 150 ms minimum (no slower than ~6 steps/sec)

---

## Project Structure

```
rodents-revenge/
├── src/
│   └── rodents_revenge/
│       ├── game.py          # All game logic, rendering, AI, level gen
│       ├── main.py          # Entry point — asyncio.run(run_game())
│       ├── scores.py        # JSON / localStorage high-score persistence
│       └── __init__.py
├── tests/
│   └── test_game_logic.py   # 40 pytest tests
├── assets/
│   ├── sprites/             # Optional sprite sheets (CC-BY)
│   └── docs/ATTRIBUTION.md  # Asset credits
├── docker/
│   └── docker-compose.yml
├── .github/
│   └── workflows/
│       └── pygbag.yml       # GitHub Pages / iPad deploy workflow
├── requirements.txt         # pygame-ce, pytest
└── requirements-web.txt     # pygbag (web/iPad build)
```

---

## Docker

```bash
# Run the test suite headlessly
docker compose -f docker/docker-compose.yml run --rm test

# Run the game (requires display forwarding on host)
docker compose -f docker/docker-compose.yml run --rm game
```

> [!NOTE]
> The `test` service sets `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` so tests run in CI with no display.

---

## Running Tests

```bash
# Activate venv first
source .venv/bin/activate

PYTHONPATH=src python -m pytest -q
```

Expected output: **40 passed**

---

## Contributing

Contributions are welcome! Here are some ideas:

- [ ] More hand-crafted levels (extend `LEVEL_PRESETS` in `game.py`)
- [ ] Additional room themes
- [ ] Mobile-optimised landscape layout
- [ ] Online leaderboard via a lightweight backend

To contribute:

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes and run `PYTHONPATH=src python -m pytest -q`
4. Open a pull request

---

<div align="center">

*Inspired by Rodent's Revenge (Microsoft, 1991) — unofficial fan remake using CC-BY licensed assets.*

</div>
