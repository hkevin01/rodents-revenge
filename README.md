# Rodent's Revenge (Python + Pygame)

A grid-based puzzle game inspired by Rodent's Revenge.

## Features

- Move the mouse with arrow keys or `WASD`
- Push blocks to trap cats
- Trapped cats turn into cheese
- Collect cheese for score
- Progressive levels with more cats and obstacles
- Animated mouse and cat sprites (when local assets are available)

## Requirements

- Python 3.10+
- Pygame

## Setup

```bash
cd projects/rodents-revenge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
PYTHONPATH=src python -m rodents_revenge.main
```

## Test

```bash
PYTHONPATH=src python -m pytest -q
```

## Docker

Build image and run tests:

```bash
docker compose -f docker/docker-compose.yml run --rm test
```

Run the game container:

```bash
docker compose -f docker/docker-compose.yml run --rm game
```

Notes:

- The `test` service uses dummy SDL drivers for headless execution.
- The `game` service works best with display forwarding configured on your host.

## Controls

- `Arrow keys` or `WASD`: move mouse
- `R`: restart after game over
- `Esc`: quit

## Rules

- You can move onto empty cells and cheese cells.
- You can push one block if the cell behind it is empty.
- Cats move after every player move.
- If a cat is enclosed on all four sides by blocks/walls/boundary, it becomes cheese.
- Level completes when all cats are gone.

## Sprite Assets

The renderer now attempts to load sprite strips from `assets/sprites/raw/cat_sprites/`.
If the files are missing, the game automatically falls back to built-in vector shapes.

Downloaded asset attributions are listed in `assets/docs/ATTRIBUTION.md`.
