from __future__ import annotations

import array
import asyncio
import heapq
import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pygame

# On some pygbag runtimes, `import pygame` can resolve to a placeholder module.
# Fall back to pygame-ce module name if needed.
if not hasattr(pygame, "init"):
    try:
        import pygame_ce as pygame  # type: ignore[no-redef]
    except Exception:
        pass


GRID_WIDTH = 20
GRID_HEIGHT = 15
TILE_SIZE = 40
FPS = 60

HUD_HEIGHT = 64
SCREEN_WIDTH = GRID_WIDTH * TILE_SIZE
SCREEN_HEIGHT = GRID_HEIGHT * TILE_SIZE + HUD_HEIGHT

EMPTY = 0
BLOCK = 1
WALL = 2
CHEESE = 3

MOUSE_STEP_SCORE = 0   # original game: no points for movement
CHEESE_SCORE = 25
TRAP_SCORE = 100
MULTI_TRAP_BONUS = 150

CAT_MOVE_DELAY_MS = 2000  # milliseconds between cat steps (device-independent)
COUNTDOWN_STEP_MS  = 800   # ms each of 3, 2, 1 is shown
COUNTDOWN_GO_MS    = 500   # ms "GO!" is shown
COUNTDOWN_TOTAL_MS = 3 * COUNTDOWN_STEP_MS + COUNTDOWN_GO_MS  # 2900 ms total
GAME_TITLE = "Rodent Rumble"

# --- Virtual joystick (touch / iPad) ---
VJOY_RADIUS = 72          # outer ring radius in pixels
VJOY_THUMB_R = 28         # movable thumb circle radius
VJOY_DEADZONE = 18        # pixels inside which input is ignored
VJOY_INITIAL_DELAY = 10   # frames before auto-repeat kicks in
VJOY_REPEAT_EVERY = 5     # frames between repeated moves while held
VJOY_FLOAT = True         # joystick floats to first-touch position

# Keyboard hold repeat (matches virtual joystick feel)
KEY_INITIAL_DELAY = 10
KEY_REPEAT_EVERY = 5

# Touch button layout (bottom-right HUD strip)
TBTN_W = 90   # touch button width
TBTN_H = 50   # touch button height

LEVEL_PRESETS: dict[int, list[str]] = {
    1: [
        "..................",
        "..BBB.............",
        "......##......C...",
        "..M...##..........",
        "......##....BBB...",
        "..................",
        "....C......#......",
        "..........###.....",
        "...........#......",
        "....BBB...........",
        "..............X...",
        "..C...............",
        "..................",
    ],
    2: [
        ".....##...........",
        "..BBB##.....C.....",
        ".....##.....###...",
        "..M.........#.....",
        "....BBBB....#..X..",
        ".................C",
        "..###.............",
        "...#......BBB.....",
        "...#..............",
        "...#....C.....X...",
        "..................",
        "..BBB......##.....",
        "...........##.....",
    ],
    3: [
        "....###...........",
        "..B..#....C..BBB..",
        "..B..#........#...",
        "..M..####.....#...",
        ".....#........#X..",
        "..C..#..BBB...#...",
        ".....#........#...",
        ".....####..####...",
        "..X......C........",
        ".............BBB..",
        "...###............",
        "...#.......C...X..",
        "...###............",
    ],
    4: [
        "........####......",
        "..BBB....##....C..",
        "........###.......",
        "..M...............",
        ".....BBBB......X..",
        "....#.............",
        "..C.#...###.......",
        "....#.....#.......",
        "....###...#..X....",
        "..........#.......",
        "..BBB.....#....C..",
        "..........###.....",
        "...............X..",
    ],
    5: [
        "..###.............",
        "..#....BBB.....X..",
        "..#....B.B........",
        "..M....BBB....C...",
        "..####........##..",
        "......#..BBB..##..",
        "..C...#...#.......",
        "......#...#..X....",
        "......#####.......",
        "..........#....C..",
        "..BBB.....#.......",
        "...........###.X..",
        "..................",
    ],
    6: [
        "...####...........",
        "...#..#.....C.....",
        "...#..#..BBB......",
        "..M#..####....X...",
        "...#..............",
        "...####..###......",
        "......#..#.#...C..",
        "..BBB.#..###......",
        "......#............",
        "..X...#####....X...",
        "...........#.......",
        "..C....BBB..#......",
        "...........###.....",
    ],
    7: [
        "..###.....###.....",
        "..#.#..C..#.#..X..",
        "..###.....###.....",
        "......BBB.........",
        "..M...............",
        "....#######.......",
        "....#.....#...C...",
        "....#.BBB.#.......",
        "....#.....#..X....",
        "....#######.......",
        ".......C........X.",
        "..BBB.............",
        "...............X..",
    ],
    8: [
        "...#####..........",
        "...#...#...C...X..",
        "...#.B.#..........",
        "..M#.B.####.......",
        "...#.B....#.......",
        "...#####..#..BBB..",
        "........#.#.......",
        "..C.....#.#..X....",
        "........#.#.......",
        "..BBB...###.......",
        "............C...X.",
        "..X....####.......",
        ".......#..........",
    ],
    9: [
        "..####........####",
        "..#..#...C....#..#",
        "..#..#######..#..#",
        "..M......#....#..#",
        "..###.BBB#....####",
        "......#...#.......",
        "..X...#...#...X...",
        "......#...#..C....",
        "..###.#####........",
        "......#...#....X..",
        "..BBB.#...#.......",
        "......#...#..C....",
        "..X...#####.......",
    ],
    10: [
        "..#####.....#####.",
        "..#...#..C..#...#.",
        "..#.B.######.B.#X.",
        "..#.B....#....B.#.",
        "..#.B.M..#..BBB.#.",
        "..#####..#..#####.",
        "........##........",
        "..X..C..##..X.....",
        "........##........",
        "..#####..#..#####.",
        "..#...#..#..#...#.",
        "..#.B.######.B.#X.",
        "..#####.....#####.",
    ],
}


@dataclass
class SpritePack:
    mouse_frames: list[pygame.Surface] = field(default_factory=list)
    cat_frames: list[pygame.Surface] = field(default_factory=list)


def _make_mouse_fallback_frames(sprite_size: int) -> list[pygame.Surface]:
    """Build simple sprite-like animated mouse frames for no-asset environments."""
    frames: list[pygame.Surface] = []
    w = max(16, sprite_size)
    h = w
    for i in range(4):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        bob = -1 if i % 2 == 0 else 0
        body = pygame.Rect(w // 4, h // 3 + bob, w // 2, h // 2)
        head = pygame.Rect(w // 3, h // 5 + bob, w // 3, h // 3)

        # Body + head
        pygame.draw.ellipse(s, (201, 230, 150), body)
        pygame.draw.ellipse(s, (211, 238, 160), head)

        # Ears
        ear_l = pygame.Rect(head.x + 1, head.y - 2, w // 7, h // 7)
        ear_r = pygame.Rect(head.right - w // 7 - 1, head.y - 2, w // 7, h // 7)
        pygame.draw.ellipse(s, (220, 245, 172), ear_l)
        pygame.draw.ellipse(s, (220, 245, 172), ear_r)
        pygame.draw.circle(s, (255, 185, 195), ear_l.center, max(1, w // 20))
        pygame.draw.circle(s, (255, 185, 195), ear_r.center, max(1, w // 20))

        # Face
        ey = head.y + head.height // 2
        lx = head.centerx - max(2, w // 10)
        rx = head.centerx + max(2, w // 10)
        pygame.draw.circle(s, (40, 55, 24), (lx, ey), max(1, w // 26))
        pygame.draw.circle(s, (40, 55, 24), (rx, ey), max(1, w // 26))
        nose = (head.centerx, ey + max(2, h // 10))
        pygame.draw.circle(s, (255, 160, 172), nose, max(1, w // 22))

        # Whiskers
        whisk = max(3, w // 7)
        pygame.draw.line(s, (190, 208, 150), (nose[0] - 1, nose[1]), (nose[0] - whisk, nose[1] - 1), 1)
        pygame.draw.line(s, (190, 208, 150), (nose[0] + 1, nose[1]), (nose[0] + whisk, nose[1] - 1), 1)

        # Tail sway + feet
        tail_anchor = (body.x + 2, body.centery)
        sway = -2 if i in (0, 3) else 2
        pygame.draw.line(s, (170, 196, 124), tail_anchor, (tail_anchor[0] - w // 5, tail_anchor[1] + sway), 2)
        paw_y = body.bottom - 1
        paw_shift = -1 if i % 2 == 0 else 1
        pygame.draw.circle(s, (206, 233, 154), (body.centerx - w // 8 + paw_shift, paw_y), max(1, w // 20))
        pygame.draw.circle(s, (206, 233, 154), (body.centerx + w // 8 - paw_shift, paw_y), max(1, w // 20))

        frames.append(s)
    return frames


def _make_cat_fallback_frames(sprite_size: int) -> list[pygame.Surface]:
    """Build simple sprite-like animated cat frames for no-asset environments."""
    frames: list[pygame.Surface] = []
    w = max(16, sprite_size)
    h = w
    for i in range(6):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        bob = -1 if i % 2 == 0 else 0
        body = pygame.Rect(w // 4, h // 3 + bob, w // 2, h // 2)
        head = pygame.Rect(w // 3, h // 5 + bob, w // 3, h // 3)

        # Body + head
        pygame.draw.ellipse(s, (255, 130, 0), body)
        pygame.draw.ellipse(s, (255, 142, 20), head)

        # Ears
        ear_l = [(head.x + 2, head.y + 3), (head.x + w // 10, head.y - h // 10), (head.x + w // 6, head.y + 4)]
        ear_r = [(head.right - 2, head.y + 3), (head.right - w // 10, head.y - h // 10), (head.right - w // 6, head.y + 4)]
        pygame.draw.polygon(s, (255, 138, 8), ear_l)
        pygame.draw.polygon(s, (255, 138, 8), ear_r)
        pygame.draw.polygon(s, (255, 185, 170), [(head.x + 5, head.y + 2), (head.x + 7, head.y - 2), (head.x + 9, head.y + 3)])
        pygame.draw.polygon(s, (255, 185, 170), [(head.right - 5, head.y + 2), (head.right - 7, head.y - 2), (head.right - 9, head.y + 3)])

        # Face/blink
        ey = head.y + head.height // 2
        blink = i == 2
        lx = head.centerx - max(2, w // 10)
        rx = head.centerx + max(2, w // 10)
        if blink:
            pygame.draw.line(s, (60, 35, 20), (lx - 1, ey), (lx + 1, ey), 1)
            pygame.draw.line(s, (60, 35, 20), (rx - 1, ey), (rx + 1, ey), 1)
        else:
            pygame.draw.circle(s, (40, 26, 18), (lx, ey), max(1, w // 26))
            pygame.draw.circle(s, (40, 26, 18), (rx, ey), max(1, w // 26))
        nose = (head.centerx, ey + max(2, h // 10))
        pygame.draw.circle(s, (255, 160, 150), nose, max(1, w // 22))

        # Tail sway + paws
        sway = (-3, -1, 2, 3, 1, -2)[i]
        t0 = (body.right - 1, body.centery)
        t1 = (t0[0] + w // 7, t0[1] + sway)
        t2 = (t1[0] + w // 9, t1[1] - sway // 2)
        pygame.draw.line(s, (238, 120, 20), t0, t1, 3)
        pygame.draw.line(s, (228, 110, 18), t1, t2, 2)
        paw_y = body.bottom - 1
        step = -1 if i % 2 == 0 else 1
        pygame.draw.circle(s, (255, 145, 35), (body.centerx - w // 8 + step, paw_y), max(1, w // 20))
        pygame.draw.circle(s, (255, 145, 35), (body.centerx + w // 8 - step, paw_y), max(1, w // 20))

        frames.append(s)
    return frames


def _load_strip_frames(
    image_path: Path,
    target_size: int,
    frame_size: int = 16,
    gap: int = 1,
    max_frames: int | None = None,
) -> list[pygame.Surface]:
    if not image_path.exists():
        return []

    try:
        sheet = pygame.image.load(str(image_path)).convert_alpha()
    except pygame.error:
        return []

    frame_count = (sheet.get_width() + gap) // (frame_size + gap)
    if max_frames is not None:
        frame_count = min(frame_count, max_frames)

    frames: list[pygame.Surface] = []
    for index in range(frame_count):
        sx = index * (frame_size + gap)
        if sx + frame_size > sheet.get_width():
            break
        frame = pygame.Surface((frame_size, frame_size), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), pygame.Rect(sx, 0, frame_size, frame_size))
        frames.append(pygame.transform.scale(frame, (target_size, target_size)))

    return frames


def _load_sprite_pack(tile_size: int) -> SpritePack:
    root = Path(__file__).resolve().parents[2]
    raw_dir = root / "assets" / "sprites" / "raw" / "cat_sprites"

    sprite_size = int(tile_size * 0.9)
    # Prefer a softer/cuter mouse strip first.
    mouse_frames = _load_strip_frames(raw_dir / "mouse" / "mouse_1_walk.png", sprite_size, max_frames=4)
    cat_frames = _load_strip_frames(raw_dir / "cat_1" / "cat_1_walk.png", sprite_size, max_frames=8)

    if not mouse_frames:
        mouse_frames = _load_strip_frames(raw_dir / "mouse" / "mouse_0_walk.png", sprite_size, max_frames=4)
    if not mouse_frames:
        mouse_frames = _load_strip_frames(raw_dir / "rat" / "rat_0_walk.png", sprite_size, max_frames=4)
    if not cat_frames:
        cat_frames = _load_strip_frames(raw_dir / "cat_0" / "cat_0_walk.png", sprite_size, max_frames=8)

    # Hard fallback: generate sprite-like animation frames in code.
    if not mouse_frames:
        mouse_frames = _make_mouse_fallback_frames(sprite_size)
    if not cat_frames:
        cat_frames = _make_cat_fallback_frames(sprite_size)

    return SpritePack(mouse_frames=mouse_frames, cat_frames=cat_frames)


@dataclass
class GameState:
    width: int = GRID_WIDTH
    height: int = GRID_HEIGHT
    level: int = 1
    score: int = 0
    lives: int = 3
    game_over: bool = False
    win_level_flash: int = 0
    respawn_flash: int = 0
    respawn_pending: bool = False
    level_clear_delay: int = 0
    trap_combo_flash: int = 0
    last_trap_count: int = 0
    paused: bool = False
    cat_delay_bonus: int = 0
    cat_count_offset: int = 0
    last_block_push: tuple[int, int, int, int] | None = None
    near_clear_warned: bool = False
    pending_sounds: list[str] = field(default_factory=list)
    board: list[list[int]] = field(default_factory=list)
    mouse_pos: tuple[int, int] = (1, 1)
    cats: list[tuple[int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.board:
            self.reset_level(self.level)

    def reset_level(self, level: int) -> None:
        self.level = level
        self.game_over = False
        self.paused = False
        self.win_level_flash = 30
        self.respawn_flash = 0
        self.level_clear_delay = 0
        self.trap_combo_flash = 0
        self.last_trap_count = 0
        self.pending_sounds = []
        self.board = [[EMPTY for _ in range(self.width)] for _ in range(self.height)]

        for x in range(self.width):
            self.board[0][x] = WALL
            self.board[self.height - 1][x] = WALL
        for y in range(self.height):
            self.board[y][0] = WALL
            self.board[y][self.width - 1] = WALL

        if self._apply_preset_level(level):
            return

        if self._apply_seeded_level(level):
            return

        # Procedural fallback (extreme levels or seeded generation failed)
        wall_count = min(8 + level * 2, 40)
        block_count = min(50 + level * 8, 200)
        cat_count = max(1, min(2 + level + self.cat_count_offset, 12))
        self.last_block_push = None
        self.near_clear_warned = False

        self._place_random_cells(WALL, wall_count)
        self._place_random_cells(BLOCK, block_count)
        self._place_random_cells(CHEESE, min(3 + level, 15))

        self.mouse_pos = self._find_free_cell(prefer_corner=True)
        self.cats = []
        for _ in range(cat_count):
            self.cats.append(self._find_free_cell(min_distance_from=self.mouse_pos, min_distance=5))

    def _apply_preset_level(self, level: int) -> bool:
        """Use handcrafted early layouts to emulate classic map pacing."""
        if level not in LEVEL_PRESETS or self.width != GRID_WIDTH or self.height != GRID_HEIGHT:
            return False

        layout = LEVEL_PRESETS[level]

        mouse_spawn: tuple[int, int] | None = None
        cat_spawns: list[tuple[int, int]] = []

        # Draw into interior cells (1..width-2, 1..height-2).
        for iy in range(self.height - 2):
            row = layout[iy] if iy < len(layout) else ""
            for ix in range(self.width - 2):
                ch = row[ix] if ix < len(row) else "."
                x, y = ix + 1, iy + 1
                if ch == "#":
                    self.board[y][x] = WALL
                elif ch == "B":
                    self.board[y][x] = BLOCK
                elif ch == "C":
                    self.board[y][x] = CHEESE
                elif ch == "M":
                    mouse_spawn = (x, y)
                elif ch == "X":
                    cat_spawns.append((x, y))

        self.last_block_push = None
        self.near_clear_warned = False

        forbidden: set[tuple[int, int]] = set(cat_spawns)
        if mouse_spawn is not None:
            forbidden.add(mouse_spawn)
        extra_blocks = min(10 + level * 3, 40)
        self._place_random_cells(BLOCK, extra_blocks, forbidden=forbidden)

        self.mouse_pos = mouse_spawn if mouse_spawn else self._find_free_cell(prefer_corner=True)

        base_cat_count = max(1, len(cat_spawns))
        target_cat_count = max(1, base_cat_count + self.cat_count_offset)
        self.cats = cat_spawns[:target_cat_count]
        while len(self.cats) < target_cat_count:
            self.cats.append(self._find_free_cell(min_distance_from=self.mouse_pos, min_distance=5))

        return True

    def restart_game(self) -> None:
        self.score = 0
        self.lives = 3
        self.reset_level(1)

    def handle_player_move(self, dx: int, dy: int) -> bool:
        if self.game_over or self.level_clear_delay > 0 or self.paused:
            return False

        if dx == 0 and dy == 0:
            return False

        mx, my = self.mouse_pos
        nx, ny = mx + dx, my + dy
        if not self.in_bounds(nx, ny):
            return False

        if self._cat_at(nx, ny):
            if not self.respawn_flash:
                self.mouse_pos = (nx, ny)
                self._lose_life(cat_pos=(nx, ny))
            return True

        target = self.board[ny][nx]

        if target in (EMPTY, CHEESE):
            self.mouse_pos = (nx, ny)
            if target == CHEESE:
                self.score += CHEESE_SCORE
                self.board[ny][nx] = EMPTY
                self.pending_sounds.append("cheese")
            else:
                self.pending_sounds.append("move")
            self.score += MOUSE_STEP_SCORE
            # Resolve newly-cornered cats immediately after the player's move.
            if self.cats:
                self._resolve_trapped_cats()
            return True

        if target == BLOCK:
            # Chain-push contiguous blocks if there is empty space at the end.
            chain: list[tuple[int, int]] = []
            cx, cy = nx, ny
            while self.in_bounds(cx, cy) and self.board[cy][cx] == BLOCK:
                chain.append((cx, cy))
                cx += dx
                cy += dy

            if not self.in_bounds(cx, cy):
                return False
            if self.board[cy][cx] != EMPTY or self._cat_at(cx, cy) or (cx, cy) == self.mouse_pos:
                return False

            for bx, by in reversed(chain):
                self.board[by + dy][bx + dx] = BLOCK
                self.board[by][bx] = EMPTY

            self.mouse_pos = (nx, ny)
            self.score += MOUSE_STEP_SCORE
            self.pending_sounds.append("move")
            self.last_block_push = (nx, ny, nx + dx, ny + dy)
            # Pushing blocks can trap cats right away.
            if self.cats:
                self._resolve_trapped_cats()
            return True

        return False

    def step_cats(self) -> None:
        if self.game_over:
            return

        life_lost = False
        new_positions: list[tuple[int, int]] = []
        occupied = set(self.cats)

        for cat in self.cats:
            occupied.discard(cat)
            nx, ny = self._next_cat_position(cat, occupied)
            if (nx, ny) == self.mouse_pos and not self.respawn_flash and not life_lost:
                self._lose_life(cat_pos=cat)
                life_lost = True
            new_positions.append((nx, ny))
            occupied.add((nx, ny))

        self.cats = new_positions
        self._resolve_trapped_cats()

    def _resolve_trapped_cats(self) -> None:
        # First pass: identify all trapped cats against the current board
        # (do NOT modify the board yet, so each cat is evaluated fairly)
        trapped = [cat for cat in self.cats if self.is_cat_trapped(*cat)]
        trap_set = set(trapped)
        # Second pass: convert all trapped cats to cheese at once
        for cx, cy in trapped:
            self.board[cy][cx] = CHEESE
        self.cats = [cat for cat in self.cats if cat not in trap_set]
        trap_count = len(trapped)
        if 0 < len(self.cats) <= 2 and not self.near_clear_warned:
            self.near_clear_warned = True
            self.pending_sounds.append("warn")
        if trap_count > 0:
            combo_bonus = (trap_count - 1) * MULTI_TRAP_BONUS
            self.score += trap_count * TRAP_SCORE + combo_bonus
            self.last_trap_count = trap_count
            self.trap_combo_flash = 60
            self.pending_sounds.append("combo" if trap_count >= 2 else "trap")

        if not self.cats and not self.game_over and self.level_clear_delay == 0:
            self.score += 300
            self.level_clear_delay = 90
            self.pending_sounds.append("clear")

    def is_cat_trapped(self, x: int, y: int) -> bool:
        dirs8 = (
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1),
        )
        for dx, dy in dirs8:
            nx, ny = x + dx, y + dy
            if not self.in_bounds(nx, ny):
                continue
            if self.board[ny][nx] in (BLOCK, WALL, CHEESE):
                continue
            if (nx, ny) == self.mouse_pos:
                return False
            if self._cat_at(nx, ny):
                return False
            # Cell is genuinely reachable and open → not trapped
            return False
        return True

    def _lose_life(self, cat_pos: tuple[int, int] | None = None) -> None:
        self.lives -= 1
        self.pending_sounds.append("death")
        if self.lives <= 0:
            self.game_over = True
        else:
            self.respawn_flash = 90
            self.respawn_pending = True
            # Spawn mouse at least 6 squares away from ALL cats.
            # If no such cell exists, relax to 3, then 1, then any free cell.
            for min_dist in (6, 3, 1, 0):
                pos = self._find_safe_respawn(min_dist, far_from=cat_pos)
                if pos is not None:
                    self.mouse_pos = pos
                    break
            else:
                self.mouse_pos = self._find_free_cell(far_from=cat_pos)

    def _next_cat_position(self, cat: tuple[int, int], occupied: set[tuple[int, int]]) -> tuple[int, int]:
        """Aggressive cat movement: diagonal-capable beeline first, then 8-way BFS fallback."""
        start = cat
        goal = self.mouse_pos
        sx, sy = start

        dirs8 = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1),
        ]

        def can_step(cx: int, cy: int, nx: int, ny: int) -> bool:
            if not self.in_bounds(nx, ny):
                return False
            if self.board[ny][nx] in (BLOCK, WALL, CHEESE):
                return False
            if (nx, ny) in occupied and (nx, ny) != goal:
                return False
            return True

        # Beeline preference: pick adjacent move that minimizes distance to mouse.
        beeline = sorted(
            dirs8,
            key=lambda d: (
                max(abs(goal[0] - (sx + d[0])), abs(goal[1] - (sy + d[1]))),
                abs(goal[0] - (sx + d[0])) + abs(goal[1] - (sy + d[1])),
                0 if d[0] and d[1] else 1,  # prefer diagonal tie-breaks
            ),
        )
        for dx, dy in beeline:
            nx, ny = sx + dx, sy + dy
            if can_step(sx, sy, nx, ny):
                return nx, ny

        # Fallback BFS when immediate beeline is blocked.
        from collections import deque

        queue: deque[tuple[int, int]] = deque([start])
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

        while queue:
            current = queue.popleft()
            if current == goal:
                break
            cx, cy = current
            for dx, dy in dirs8:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in came_from:
                    continue
                if not can_step(cx, cy, nx, ny):
                    continue
                came_from[(nx, ny)] = current
                queue.append((nx, ny))

        if goal not in came_from:
            return start

        step: tuple[int, int] = goal
        while came_from[step] != start:
            prev = came_from[step]
            if prev is None:
                return start
            step = prev
        return step

    def _place_random_cells(
        self,
        kind: int,
        count: int,
        forbidden: set[tuple[int, int]] | None = None,
    ) -> None:
        placed = 0
        attempts = 0
        limit = count * 50
        forbidden = forbidden or set()
        while placed < count and attempts < limit:
            attempts += 1
            x = random.randint(1, self.width - 2)
            y = random.randint(1, self.height - 2)
            if (x, y) in forbidden:
                continue
            if self.board[y][x] == EMPTY:
                self.board[y][x] = kind
                placed += 1

    def _find_safe_respawn(
        self,
        min_cat_dist: int,
        far_from: tuple[int, int] | None = None,
    ) -> tuple[int, int] | None:
        """Return a free cell that is at least min_cat_dist from every cat.
        Picks the farthest qualifying cell from far_from (or any qualifying
        cell if far_from is None).  Returns None if no cell qualifies."""
        candidates: list[tuple[int, int]] = []
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.board[y][x] != EMPTY:
                    continue
                if (x, y) in self.cats:
                    continue
                if min_cat_dist > 0 and any(
                    abs(x - cx) + abs(y - cy) < min_cat_dist
                    for cx, cy in self.cats
                ):
                    continue
                candidates.append((x, y))
        if not candidates:
            return None
        if far_from is not None:
            candidates.sort(
                key=lambda p: abs(p[0] - far_from[0]) + abs(p[1] - far_from[1]),
                reverse=True,
            )
            pool = candidates[: max(1, len(candidates) // 4)]
            return random.choice(pool)
        return random.choice(candidates)

    def _find_free_cell(
        self,
        prefer_corner: bool = False,
        min_distance_from: tuple[int, int] | None = None,
        min_distance: int = 0,
        far_from: tuple[int, int] | None = None,
    ) -> tuple[int, int]:
        candidates: list[tuple[int, int]] = []
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.board[y][x] != EMPTY:
                    continue
                if (x, y) in self.cats:
                    continue
                if min_distance_from:
                    dist = abs(x - min_distance_from[0]) + abs(y - min_distance_from[1])
                    if dist < min_distance:
                        continue
                candidates.append((x, y))

        if not candidates:
            for y in range(1, self.height - 1):
                for x in range(1, self.width - 1):
                    if self.board[y][x] == EMPTY:
                        return x, y
            return 1, 1

        if far_from is not None:
            # Pick from the farthest 25% of cells (Manhattan distance)
            candidates.sort(
                key=lambda p: abs(p[0] - far_from[0]) + abs(p[1] - far_from[1]),
                reverse=True,
            )
            far_pool = candidates[: max(1, len(candidates) // 4)]
            return random.choice(far_pool)

        if prefer_corner:
            candidates.sort(key=lambda p: p[0] + p[1])
            return candidates[0]

        return random.choice(candidates)

    def _validate_solvable(self) -> bool:
        """Basic solvability check used by the seeded level generator."""
        from collections import deque

        mx, my = self.mouse_pos

        # Mouse must have at least 1 free orthogonal neighbour
        has_free = any(
            self.in_bounds(mx + dx, my + dy)
            and self.board[my + dy][mx + dx] in (EMPTY, CHEESE)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        )
        if not has_free:
            return False

        # BFS from mouse through EMPTY/CHEESE — must reach ≥ 12 cells
        visited: set[tuple[int, int]] = {(mx, my)}
        queue: deque[tuple[int, int]] = deque([(mx, my)])
        reachable = 0
        while queue:
            cx, cy = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in visited or not self.in_bounds(nx, ny):
                    continue
                if self.board[ny][nx] in (EMPTY, CHEESE):
                    visited.add((nx, ny))
                    queue.append((nx, ny))
                    reachable += 1

        if reachable < 12:
            return False

        # No cat may start already trapped
        for cat in self.cats:
            if self.is_cat_trapped(*cat):
                return False

        return True

    def _apply_seeded_level(self, level: int) -> bool:
        """Generate a deterministic validated level for levels ≥ 11.

        Uses a fixed seed per level so every playthrough gets the same map.
        Retries up to 400 seeds until solvability constraints are met.
        """
        if level < 11:
            return False

        tier = min((level - 11) // 10, 9)
        tier_wall_segs  = (4, 5, 5, 6, 6, 7, 7, 8, 8, 9)
        tier_block_cnt  = (38, 42, 46, 50, 54, 58, 62, 66, 70, 74)
        tier_cheese_cnt = ( 5,  4,  4,  3,  3,  3,  2,  2,  2,  2)
        tier_cat_cnt    = ( 3,  3,  4,  4,  5,  5,  6,  6,  7,  8)

        wall_segs  = tier_wall_segs[tier]
        block_cnt  = tier_block_cnt[tier]
        cheese_cnt = tier_cheese_cnt[tier]
        cat_cnt    = max(1, tier_cat_cnt[tier] + self.cat_count_offset)

        for attempt in range(400):
            seed = level * 7919 + attempt
            rng = random.Random(seed)

            # Clear interior (perimeter walls already set by reset_level)
            for iy in range(1, self.height - 1):
                for ix in range(1, self.width - 1):
                    self.board[iy][ix] = EMPTY

            # Place wall segments to create corridors / rooms
            for _ in range(wall_segs):
                wx = rng.randint(2, self.width - 4)
                wy = rng.randint(2, self.height - 4)
                horiz = rng.choice((True, False))
                length = rng.randint(3, min(6, self.width // 3))
                for i in range(length):
                    cx = wx + (i if horiz else 0)
                    cy = wy + (0 if horiz else i)
                    if 1 <= cx < self.width - 1 and 1 <= cy < self.height - 1:
                        self.board[cy][cx] = WALL

            # Collect free interior cells
            free = [
                (x, y)
                for y in range(2, self.height - 2)
                for x in range(2, self.width - 2)
                if self.board[y][x] == EMPTY
            ]
            if len(free) < cat_cnt + block_cnt + cheese_cnt + 5:
                continue

            # Mouse: spawn in left third
            left_pool = [(x, y) for x, y in free if x <= self.width // 3]
            if not left_pool:
                left_pool = free[:]
            rng.shuffle(left_pool)
            mouse = left_pool[0]
            self.mouse_pos = mouse

            # Cats: far from mouse, spread across board
            far_pool = sorted(
                [(x, y) for x, y in free if (x, y) != mouse
                 and abs(x - mouse[0]) + abs(y - mouse[1]) >= 8],
                key=lambda c: -(abs(c[0] - mouse[0]) + abs(c[1] - mouse[1])),
            )
            if len(far_pool) < cat_cnt:
                continue
            spread = far_pool[:max(cat_cnt * 3, 12)]
            rng.shuffle(spread)
            self.cats = spread[:cat_cnt]

            forbidden = {mouse} | set(self.cats)

            # Blocks
            block_pool = [c for c in free if c not in forbidden]
            rng.shuffle(block_pool)
            for bx, by in block_pool[:block_cnt]:
                self.board[by][bx] = BLOCK
            remaining = block_pool[block_cnt:]

            # Cheese
            for cx2, cy2 in remaining[:cheese_cnt]:
                self.board[cy2][cx2] = CHEESE

            self.last_block_push = None
            self.near_clear_warned = False

            if self._validate_solvable():
                return True

        return False  # extremely unlikely — fall back to procedural

    def _cat_at(self, x: int, y: int) -> bool:
        return (x, y) in self.cats

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height


# ---------------------------------------------------------------------------
# Room themes — each 10 levels the player moves to a different room
# ---------------------------------------------------------------------------
ROOM_THEMES = [
    {
        "name": "Kitchen",
        "floor_style": "checker",
        "floor_a": (228, 222, 210),   # cream ceramic tile
        "floor_b": (52,  48,  44),    # near-black ceramic tile
        "floor_grout": (190, 185, 175),
        "wall_face": (178, 156, 118),  # terracotta / subway tile
        "wall_dark": (118, 100, 72),
        "block_face": (218, 192, 148),
        "block_edge": (148, 118, 78),
        "grid_col": (185, 178, 162),
    },
    {
        "name": "Dining Room",
        "floor_style": "planks",
        "floor_a": (168, 112, 62),    # warm oak
        "floor_b": (142, 92,  48),    # darker oak
        "floor_grout": (120, 80, 40),
        "wall_face": (188, 148, 102),  # warm cream/tan wainscot
        "wall_dark": (132, 100, 65),
        "block_face": (202, 168, 118),
        "block_edge": (148, 112, 72),
        "grid_col": (148, 104, 58),
    },
    {
        "name": "Living Room",
        "floor_style": "carpet",
        "floor_a": (132, 58,  68),    # burgundy carpet
        "floor_b": (112, 44,  54),
        "floor_grout": (105, 38, 48),
        "wall_face": (168, 132, 98),   # warm sage/tan
        "wall_dark": (118, 92, 62),
        "block_face": (198, 162, 112),
        "block_edge": (142, 108, 68),
        "grid_col": (118, 50, 60),
    },
    {
        "name": "Bedroom",
        "floor_style": "carpet",
        "floor_a": (188, 170, 212),   # soft lavender carpet
        "floor_b": (168, 150, 192),
        "floor_grout": (155, 138, 178),
        "wall_face": (198, 178, 222),  # light lilac
        "wall_dark": (142, 124, 168),
        "block_face": (205, 185, 228),
        "block_edge": (155, 132, 182),
        "grid_col": (172, 155, 198),
    },
    {
        "name": "Bathroom",
        "floor_style": "checker",
        "floor_a": (222, 235, 248),   # pale sky-blue tile
        "floor_b": (178, 212, 232),   # mid-blue tile
        "floor_grout": (155, 188, 212),
        "wall_face": (158, 200, 222),  # seafoam / aqua
        "wall_dark": (108, 158, 185),
        "block_face": (198, 222, 238),
        "block_edge": (122, 172, 202),
        "grid_col": (172, 208, 228),
    },
    {
        "name": "Attic",
        "floor_style": "planks",
        "floor_a": (158, 134, 108),   # dusty rough planks
        "floor_b": (134, 112, 88),
        "floor_grout": (108, 88, 68),
        "wall_face": (108, 92, 72),    # exposed beam / grey
        "wall_dark": (74, 62, 48),
        "block_face": (168, 142, 110),
        "block_edge": (118, 96, 70),
        "grid_col": (138, 116, 92),
    },
]


def get_room_theme(level: int) -> dict:
    """Return the room theme dict for the given level (cycles every 10 levels)."""
    idx = (level - 1) // 10 % len(ROOM_THEMES)
    return ROOM_THEMES[idx]


def _draw_floor_tile(
    surface: pygame.Surface,
    rect: pygame.Rect,
    gx: int,
    gy: int,
    theme: dict,
) -> None:
    """Draw a single floor tile with the room's pattern."""
    style = theme["floor_style"]
    if style == "checker":
        col = theme["floor_a"] if (gx + gy) % 2 == 0 else theme["floor_b"]
        pygame.draw.rect(surface, col, rect)
        # thin grout line
        pygame.draw.rect(surface, theme["floor_grout"], rect, 1)
    elif style == "planks":
        col = theme["floor_a"] if (gy // 2) % 2 == 0 else theme["floor_b"]
        pygame.draw.rect(surface, col, rect)
        # plank seam every 2 rows
        if gy % 2 == 1:
            pygame.draw.line(surface, theme["floor_grout"],
                             rect.bottomleft, (rect.right - 1, rect.bottom), 1)
        pygame.draw.rect(surface, theme["grid_col"], rect, 1)
    else:  # carpet
        # subtle woven texture — alternate tiny brighter/darker diamonds
        col = theme["floor_a"] if (gx + gy * 3) % 5 < 3 else theme["floor_b"]
        pygame.draw.rect(surface, col, rect)
        # faint grid stitch
        pygame.draw.rect(surface, theme["floor_grout"], rect, 1)


def _draw_wall_tile(
    surface: pygame.Surface,
    rect: pygame.Rect,
    face: tuple[int, int, int] = (72, 62, 52),
    dark: tuple[int, int, int] = (42, 35, 28),
) -> None:
    ts = rect.width
    pygame.draw.rect(surface, face, rect.inflate(-2, -2))
    for row in range(1, 3):
        y = rect.y + row * ts // 3
        pygame.draw.line(surface, dark, (rect.x + 2, y), (rect.x + ts - 3, y), 1)
    for row in range(3):
        y0 = rect.y + row * ts // 3 + 1
        y1 = rect.y + (row + 1) * ts // 3 - 1
        if row % 2 == 0:
            x = rect.x + ts // 2
            pygame.draw.line(surface, dark, (x, y0), (x, y1), 1)
        else:
            for x in (rect.x + ts // 4, rect.x + 3 * ts // 4):
                pygame.draw.line(surface, dark, (x, y0), (x, y1), 1)


def _draw_block_tile(
    surface: pygame.Surface,
    rect: pygame.Rect,
    face: tuple[int, int, int] = (210, 185, 140),
    edge: tuple[int, int, int] = (145, 115, 75),
) -> None:
    """Draw a detailed cardboard box tile with top flaps, tape, and small lettering."""
    ts = rect.width
    x, y = rect.x, rect.y

    # Cardboard colour variants from the theme face colour, shifted toward a
    # distinctly darker brown palette.
    r, g, b = face
    base = (
        max(0, min(255, 96 + (r - 170) // 7)),
        max(0, min(255, 67 + (g - 130) // 9)),
        max(0, min(255, 40 + (b - 95) // 12)),
    )
    dark = (max(0, base[0] - 28), max(0, base[1] - 20), max(0, base[2] - 14))
    light = (min(255, base[0] + 14), min(255, base[1] + 10), min(255, base[2] + 7))
    crease = (max(0, base[0] - 12), max(0, base[1] - 9), max(0, base[2] - 7))
    tape = (min(255, base[0] + 7), min(255, base[1] + 6), min(255, base[2] + 4))

    pad = 2

    # --- Main box body (slightly inset) ---
    body = pygame.Rect(x + pad, y + pad, ts - pad * 2, ts - pad * 2)
    pygame.draw.rect(surface, base, body)

    # --- Right shadow strip (3D depth illusion) ---
    shadow_w = max(3, ts // 7)
    shadow = pygame.Rect(body.right - shadow_w, body.y, shadow_w, body.height)
    pygame.draw.rect(surface, dark, shadow)

    # --- Top flap area ---
    flap_h = max(5, ts // 5)
    flap_top = body.y + 3
    flap = pygame.Rect(body.x + 1, flap_top, body.width - shadow_w - 2, flap_h)
    pygame.draw.rect(surface, light, flap)

    flap_y = flap.bottom
    mid_x = body.centerx
    pygame.draw.line(surface, edge, (body.x, flap_y), (body.right - 1, flap_y), 1)
    pygame.draw.line(surface, crease, (mid_x, flap.y + 1), (mid_x, flap_y - 1), 1)

    # --- Tape strip across the middle of the flap (horizontal) ---
    tape_y = flap.y + flap_h // 2 - 1
    tape_w = max(8, flap.width - 8)
    pygame.draw.rect(surface, tape, (flap.x + 3, tape_y, tape_w, 2))

    # --- Vertical centre seam on box body (below flap) ---
    pygame.draw.line(surface, crease, (mid_x, flap_y + 2), (mid_x, body.bottom - 2), 1)

    # --- Small printed letters "BOX" along the lower body ---
    if ts >= 24:
        # Two tiny pixel-art dots suggesting printed text lines
        txt_y = flap_y + (body.bottom - flap_y) // 2 - 2
        for i in range(3):
            dot_x = body.x + 4 + i * (ts // 10 + 2)
            pygame.draw.rect(surface, crease, (dot_x, txt_y, max(2, ts // 12), 1))
            pygame.draw.rect(surface, crease, (dot_x, txt_y + 3, max(2, ts // 14), 1))

    # --- Outer border ---
    pygame.draw.rect(surface, edge, body, 1)


def _draw_cheese_tile(surface: pygame.Surface, rect: pygame.Rect) -> None:
    ts = rect.width
    cx, cy = rect.center
    pts = [
        (cx, rect.y + 6),
        (rect.x + 5, rect.y + ts - 8),
        (rect.x + ts - 5, rect.y + ts - 8),
    ]
    pygame.draw.polygon(surface, (254, 215, 50), pts)
    pygame.draw.polygon(surface, (195, 158, 18), pts, 2)
    pygame.draw.circle(surface, (195, 158, 18), (cx - ts // 7, cy + ts // 10), 3)
    pygame.draw.circle(surface, (195, 158, 18), (cx + ts // 8, cy - ts // 14), 2)


def _gen_tone(freq: float, dur: float, vol: float = 0.25, rate: int = 22050) -> pygame.mixer.Sound:
    n = int(rate * dur)
    buf = array.array("h", [int(32767 * vol * math.sin(2 * math.pi * freq * i / rate)) for i in range(n)])
    return pygame.mixer.Sound(buffer=buf)


def _gen_sweep(f0: float, f1: float, dur: float, vol: float = 0.25, rate: int = 22050) -> pygame.mixer.Sound:
    n = int(rate * dur)
    buf = array.array("h", [
        int(32767 * vol * math.sin(2 * math.pi * (f0 + (f1 - f0) * i / n) * i / rate))
        for i in range(n)
    ])
    return pygame.mixer.Sound(buffer=buf)


def _make_icon() -> pygame.Surface:
    """Procedural 32x32 window icon: cheese wedge on dark background."""
    size = 32
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((18, 16, 13))
    pts = [(size // 2, 4), (4, size - 4), (size - 4, size - 4)]
    pygame.draw.polygon(surf, (254, 215, 50), pts)
    pygame.draw.polygon(surf, (195, 158, 18), pts, 2)
    pygame.draw.circle(surf, (195, 158, 18), (13, 22), 3)
    pygame.draw.circle(surf, (195, 158, 18), (21, 17), 2)
    return surf


async def run_game() -> None:
    try:
        pygame.mixer.pre_init(22050, -16, 1, 512)
    except Exception:
        pass
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(GAME_TITLE)
    # Keep pixel-art look on high-DPI screens (iPad, Retina, etc.)
    if sys.platform == "emscripten":
        import platform  # type: ignore[import]
        platform.window.canvas.style.imageRendering = "pixelated"
    pygame.display.set_icon(_make_icon())
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 24, bold=True)
    small_font = pygame.font.SysFont("monospace", 20)
    tiny_font = pygame.font.SysFont("monospace", 14)
    sprites = _load_sprite_pack(TILE_SIZE)
    title_font = pygame.font.SysFont("monospace", 40, bold=True)
    big_title_font = pygame.font.SysFont("monospace", 64, bold=True)
    snd: dict[str, pygame.mixer.Sound | None] = {}
    try:
        snd["move"]  = _gen_tone(880,  0.04, vol=0.12)
        snd["trap"]  = _gen_tone(523,  0.12, vol=0.30)
        snd["combo"] = _gen_tone(659,  0.18, vol=0.35)
        snd["death"] = _gen_sweep(440, 110, 0.35, vol=0.30)
        snd["clear"] = _gen_sweep(392, 784, 0.40, vol=0.30)
        snd["cheese"]= _gen_tone(1046, 0.07, vol=0.20)
        snd["warn"]  = _gen_sweep(300,  900, 0.15, vol=0.28)
    except Exception:
        snd = {}

    colors = {
        "bg": (18, 16, 13),
        "grid": (38, 34, 30),
        "wall": (85, 72, 60),
        "block": (120, 102, 84),
        "mouse": (210, 200, 190),
        "cat": (255, 130, 0),
        "cheese": (254, 220, 90),
        "hud": (25, 23, 20),
        "text": (235, 226, 206),
        "alert": (255, 130, 130),
        "levelup": (140, 220, 160),
    }

    DIFFICULTIES = ["easy", "normal", "hard"]
    DIFF_SETTINGS: dict[str, dict[str, int]] = {
        "easy":   {"cat_delay_bonus":   250, "cat_count_offset": -1},
        "normal": {"cat_delay_bonus":     0, "cat_count_offset":  0},
        "hard":   {"cat_delay_bonus":  -125, "cat_count_offset":  1},
    }
    diff_idx = 1  # default: normal
    TWEEN_FRAMES = 6
    block_tweens: list[dict] = []
    mouse_facing = 1   # +1 = right (default), -1 = left
    cat_alert: dict[tuple[int, int], int] = {}  # cat pos -> remaining flash frames
    show_help = False
    try:
        from rodents_revenge.scores import load_scores, save_score, is_high_score
    except ImportError:  # flat-package mode inside pygbag / WASM
        from scores import load_scores, save_score, is_high_score  # type: ignore[no-redef]
    state = GameState()
    cat_ms_accum = 0
    countdown_ms = COUNTDOWN_TOTAL_MS
    dt_ms = 0
    animation_frame = 0
    phase = "title"  # "title" | "playing"
    score_saved = False
    new_high_score = False
    scores = load_scores()
    running = True

    entering_initials = False
    entry_initials = ""
    initials_key_rects: list[tuple[str, pygame.Rect]] = []

    # --- Virtual joystick touch state ---
    # Floats to wherever the player first touches (left half of screen)
    _vjoy_default_cx = VJOY_RADIUS + 30
    _vjoy_default_cy = SCREEN_HEIGHT - VJOY_RADIUS - 30
    vjoy_cx = _vjoy_default_cx
    vjoy_cy = _vjoy_default_cy
    vjoy_active = False
    vjoy_finger_id: int | None = None
    vjoy_offset = (0.0, 0.0)   # thumb displacement from center
    vjoy_last_dir = (0, 0)
    vjoy_held_frames = 0
    key_last_dir = (0, 0)
    key_held_frames = 0
    key_left_held = False
    key_right_held = False
    key_up_held = False
    key_down_held = False

    # Touch buttons (Pause, Help) rendered in HUD — rects set in draw_board
    _tbtn_pause_rect = pygame.Rect(0, 0, TBTN_W, TBTN_H)
    _tbtn_help_rect  = pygame.Rect(0, 0, TBTN_W, TBTN_H)
    # Overlay action buttons (Menu / Restart on game-over, Resume on pause)
    _tbtn_menu_rect    = pygame.Rect(0, 0, 160, 64)
    _tbtn_restart_rect = pygame.Rect(0, 0, 160, 64)
    _tbtn_resume_rect  = pygame.Rect(0, 0, 200, 64)

    def _vjoy_dir(offset: tuple[float, float]) -> tuple[int, int]:
        """Map joystick displacement to the nearest 4-way grid direction."""
        ox, oy = offset
        if math.hypot(ox, oy) < VJOY_DEADZONE:
            return (0, 0)
        if abs(ox) >= abs(oy):
            return (1 if ox > 0 else -1, 0)
        return (0, 1 if oy > 0 else -1)

    def _apply_vjoy_move(d: tuple[int, int]) -> bool:
        """Issue one grid step from joystick input; return True if player moved."""
        nonlocal mouse_facing, player_moved
        if state.game_over or state.paused or show_help or countdown_ms > 0:
            return False
        moved = state.handle_player_move(d[0], d[1])
        if moved and d[0] != 0:
            mouse_facing = d[0]
        return moved

    def _draw_touch_btn(
        surf: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        color: tuple[int, int, int] = (70, 65, 50),
        text_color: tuple[int, int, int] = (220, 210, 170),
        active: bool = False,
    ) -> None:
        """Draw a polished rounded button with highlight edge and drop-shadow."""
        bg_col = tuple(min(255, c + 30) for c in color) if active else color  # type: ignore[assignment]
        # Drop-shadow
        shadow_r = rect.move(2, 3)
        shadow_surf = pygame.Surface((shadow_r.width, shadow_r.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 80), shadow_surf.get_rect(), border_radius=10)
        surf.blit(shadow_surf, shadow_r.topleft)
        # Button fill
        pygame.draw.rect(surf, bg_col, rect, border_radius=10)
        # Inner top highlight (1-px lighter strip near top)
        hi_r = pygame.Rect(rect.x + 4, rect.y + 2, rect.width - 8, rect.height // 2)
        hi_surf = pygame.Surface((hi_r.width, hi_r.height), pygame.SRCALPHA)
        pygame.draw.rect(hi_surf, (255, 255, 255, 28), hi_surf.get_rect(), border_radius=8)
        surf.blit(hi_surf, hi_r.topleft)
        # Outer border — bright top-left, dark bottom-right
        pygame.draw.rect(surf, (180, 170, 130), rect, 2, border_radius=10)
        lbl = small_font.render(label, True, text_color)
        surf.blit(lbl, (rect.centerx - lbl.get_width() // 2, rect.centery - lbl.get_height() // 2))

    def draw_board() -> None:
        _tween_dests = {(tw["gx1"], tw["gy1"]) for tw in block_tweens}
        _theme = get_room_theme(state.level)
        # ------ line-of-sight alert: update cat_alert dict ------
        mx, my = state.mouse_pos
        alive_positions = set(state.cats)
        # Remove stale keys (cats that moved/were trapped)
        for key in list(cat_alert):
            if key not in alive_positions:
                del cat_alert[key]
        for cat in state.cats:
            cx, cy = cat
            in_sight = False
            if cx == mx:  # same column
                y0, y1 = (min(cy, my) + 1, max(cy, my))
                if all(
                    state.board[yy][cx] not in (WALL, BLOCK)
                    for yy in range(y0, y1)
                ):
                    in_sight = True
            elif cy == my:  # same row
                x0, x1 = (min(cx, mx) + 1, max(cx, mx))
                if all(
                    state.board[cy][xx] not in (WALL, BLOCK)
                    for xx in range(x0, x1)
                ):
                    in_sight = True
            if in_sight:
                cat_alert[cat] = 20  # sustain glow for 20 frames
            elif cat in cat_alert:
                cat_alert[cat] -= 1
                if cat_alert[cat] <= 0:
                    del cat_alert[cat]
        # ----------------------------------------------------------
        # Fill entire screen with the room's dominant floor color first
        screen.fill(_theme["floor_a"])
        for y in range(state.height):
            for x in range(state.width):
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE)

                tile = state.board[y][x]
                if tile == WALL:
                    _draw_wall_tile(screen, rect, _theme["wall_face"], _theme["wall_dark"])
                elif tile == BLOCK and (x, y) not in _tween_dests:
                    _draw_block_tile(screen, rect, _theme["block_face"], _theme["block_edge"])
                elif tile == CHEESE:
                    _draw_floor_tile(screen, rect, x, y, _theme)
                    _draw_cheese_tile(screen, rect)
                else:
                    _draw_floor_tile(screen, rect, x, y, _theme)

        for cx, cy in state.cats:
            rect = pygame.Rect(cx * TILE_SIZE, cy * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE)
            if (cx, cy) in cat_alert:
                # draw orange glow ring behind sprite
                glow_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                alpha = min(180, 80 + cat_alert[(cx, cy)] * 5)
                pygame.draw.ellipse(glow_surf, (255, 140, 0, alpha),
                                    glow_surf.get_rect().inflate(-4, -4))
                screen.blit(glow_surf, rect.topleft)
            # Side-profile cat — always faces toward the player
            cat_fx = 1 if cx <= mx else -1
            cbx = rect.centerx
            cby = rect.centery + int(math.sin(animation_frame / 9.0))
            cbw, cbh = 28, 14
            body_cx = cbx - cat_fx * 1
            body_cy = cby + 4
            cb_r = pygame.Rect(body_cx - cbw // 2, body_cy - cbh // 2, cbw, cbh)
            ch_cx = cbx + cat_fx * 10
            ch_cy = cby
            ch_r = 9
            # Tail first (body will cover its base)
            ct_x0 = body_cx - cat_fx * (cbw // 2)
            ct_x1 = ct_x0 - cat_fx * 8
            ct_y1 = body_cy - 4
            ct_x2 = ct_x1 - cat_fx * 4
            ct_y2 = ct_y1 - 10
            pygame.draw.line(screen, (220, 140, 55), (ct_x0, body_cy), (ct_x1, ct_y1), 3)
            pygame.draw.line(screen, (210, 130, 50), (ct_x1, ct_y1), (ct_x2, ct_y2), 2)
            # Body + head (covers tail base)
            pygame.draw.ellipse(screen, (235, 158, 65), cb_r)
            pygame.draw.circle(screen, (235, 158, 65), (ch_cx, ch_cy), ch_r)
            # Stripes on body (3 dark arcs/lines across the body)
            stripe_col = (185, 110, 30)
            for si, sx_off in enumerate((-8, -1, 6)):
                sx0 = body_cx + sx_off - 1
                sx1 = body_cx + sx_off + 1
                pygame.draw.line(screen, stripe_col,
                                 (body_cx + sx_off, cb_r.top + 2),
                                 (body_cx + sx_off, cb_r.bottom - 2), 2)
            # Ear: pointy triangle on top of head, toward BACK, fully within head circle
            ear_bx = ch_cx - cat_fx * (ch_r // 2)  # half-radius back from head center
            ear_by = ch_cy - ch_r + 1      # near head top
            ear_tip = (ear_bx, ear_by - 9)
            ear_base_l = (ear_bx - 4, ear_by)
            ear_base_r = (ear_bx + 4, ear_by)
            pygame.draw.polygon(screen, (200, 105, 25), [ear_tip, ear_base_l, ear_base_r])
            pygame.draw.polygon(screen, (255, 175, 165), [
                (ear_bx, ear_by - 5), (ear_bx - 2, ear_by - 1), (ear_bx + 2, ear_by - 1)
            ])
            # Eye: yellow iris + black slit
            eye_x = ch_cx + cat_fx * 3
            eye_y = ch_cy - 2
            pygame.draw.circle(screen, (255, 220, 80), (eye_x, eye_y), 3)
            pygame.draw.circle(screen, (10, 10, 10), (eye_x, eye_y), 1)
            # Nose + whiskers
            nose_x = ch_cx + cat_fx * (ch_r - 1)
            nose_y = ch_cy + 3
            pygame.draw.circle(screen, (255, 160, 150), (nose_x, nose_y), 2)
            pygame.draw.line(screen, (220, 220, 200), (nose_x, nose_y - 1), (nose_x + cat_fx * 10, nose_y - 3), 1)
            pygame.draw.line(screen, (220, 220, 200), (nose_x, nose_y + 1), (nose_x + cat_fx * 10, nose_y + 3), 1)
            # Legs
            pygame.draw.ellipse(screen, (225, 148, 58), pygame.Rect(body_cx - 7, cb_r.bottom - 3, 9, 5))
            pygame.draw.ellipse(screen, (225, 148, 58), pygame.Rect(body_cx + 2, cb_r.bottom - 3, 9, 5))

        mx, my = state.mouse_pos
        mouse_rect = pygame.Rect(mx * TILE_SIZE, my * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE)
        bob = int(math.sin(animation_frame / 7.0) * 2)
        # Side-profile mouse drawing (always procedural)
        fx = 1 if mouse_facing >= 0 else -1
        bx = mouse_rect.centerx
        by = mouse_rect.centery + bob
        # Tail first (body overlaps its base)
        mt_x0 = bx - fx * 11
        mt_x1 = mt_x0 - fx * 8
        mt_x2 = mt_x1 - fx * 5
        pygame.draw.line(screen, (190, 180, 175), (mt_x0, by + 3), (mt_x1, by + 7), 3)
        pygame.draw.line(screen, (178, 168, 163), (mt_x1, by + 7), (mt_x2, by + 1), 2)
        # Body: horizontal oval
        mbw, mbh = 24, 12
        mb_cx = bx - fx * 2
        mb_cy = by + 3
        mb_r = pygame.Rect(mb_cx - mbw // 2, mb_cy - mbh // 2, mbw, mbh)
        pygame.draw.ellipse(screen, (212, 200, 195), mb_r)
        # Head: circle at front, overlaps body edge
        mh_cx = bx + fx * 10
        mh_cy = by - 1
        mh_r = 7
        pygame.draw.circle(screen, (212, 200, 195), (mh_cx, mh_cy), mh_r)
        # Ear: round disc sitting on top of head, toward BACK of head
        # Center placed at head-top so lower half overlaps head (natural mount)
        ear_cx = mh_cx - fx * 3   # back side of head
        ear_cy = mh_cy - mh_r     # at head top surface
        ear_r = 5
        pygame.draw.circle(screen, (215, 205, 200), (ear_cx, ear_cy), ear_r)
        pygame.draw.circle(screen, (245, 180, 185), (ear_cx, ear_cy), 2)   # inner ear
        # Snout nub
        if fx > 0:
            snout_r = pygame.Rect(mh_cx + mh_r - 2, mh_cy + 1, 6, 4)
        else:
            snout_r = pygame.Rect(mh_cx - mh_r - 4, mh_cy + 1, 6, 4)
        pygame.draw.ellipse(screen, (225, 215, 210), snout_r)
        # Nose
        nose_x = mh_cx + fx * (mh_r + 4)
        nose_y = mh_cy + 3
        pygame.draw.circle(screen, (255, 158, 172), (nose_x, nose_y), 2)
        # Eye: dark with highlight
        pygame.draw.circle(screen, (30, 30, 40), (mh_cx + fx * 3, mh_cy - 3), 2)
        pygame.draw.circle(screen, (200, 230, 255), (mh_cx + fx * 3, mh_cy - 3), 1)
        # Whiskers
        pygame.draw.line(screen, (170, 165, 160), (nose_x, nose_y), (nose_x + fx * 9, nose_y - 2), 1)
        pygame.draw.line(screen, (170, 165, 160), (nose_x, nose_y), (nose_x + fx * 9, nose_y + 2), 1)
        # Legs
        pygame.draw.ellipse(screen, (200, 190, 185), pygame.Rect(mb_cx - 6, mb_r.bottom - 3, 8, 5))
        pygame.draw.ellipse(screen, (200, 190, 185), pygame.Rect(mb_cx + 2, mb_r.bottom - 3, 8, 5))

        for tw in block_tweens:
            t = tw["t"]
            px = int(tw["gx0"] * TILE_SIZE + (tw["gx1"] - tw["gx0"]) * TILE_SIZE * t)
            py = int(tw["gy0"] * TILE_SIZE + HUD_HEIGHT + (tw["gy1"] - tw["gy0"]) * TILE_SIZE * t)
            _draw_block_tile(screen, pygame.Rect(px, py, TILE_SIZE, TILE_SIZE), _theme["block_face"], _theme["block_edge"])

        hud_rect = pygame.Rect(0, 0, SCREEN_WIDTH, HUD_HEIGHT)
        pygame.draw.rect(screen, colors["hud"], hud_rect)
        hud_text = font.render(
            f"Score {state.score:05d}   Level {state.level}   Cats {len(state.cats)}",
            True,
            colors["text"],
        )
        screen.blit(hud_text, (16, 18))
        # Room name badge
        room_surf = small_font.render(_theme["name"], True, (200, 188, 148))
        screen.blit(room_surf, (16, HUD_HEIGHT - room_surf.get_height() - 4))
        # HUD touch buttons — Pause and Help, centred in the HUD
        _btn_y = HUD_HEIGHT // 2 - TBTN_H // 2
        pause_x = SCREEN_WIDTH // 2 - TBTN_W - 5
        help_x  = SCREEN_WIDTH // 2 + 5
        _tbtn_pause_rect.topleft = (pause_x, _btn_y)
        _tbtn_help_rect.topleft  = (help_x,  _btn_y)
        _draw_touch_btn(screen, _tbtn_pause_rect, "⏸ PAUSE", active=state.paused)
        _draw_touch_btn(screen, _tbtn_help_rect,  "? HELP",  active=show_help)

        # Lives display — one pip per life
        for i in range(state.lives):
            pygame.draw.circle(
                screen, colors["mouse"],
                (SCREEN_WIDTH - 20 - i * 22, HUD_HEIGHT // 2), 7,
            )

        if state.win_level_flash > 0:
            msg = small_font.render("Level cleared!", True, colors["levelup"])
            screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, 22))
            state.win_level_flash -= 1

        if state.trap_combo_flash > 0:
            if state.last_trap_count >= 2:
                total = state.last_trap_count * TRAP_SCORE + (state.last_trap_count - 1) * MULTI_TRAP_BONUS
                combo_surf = small_font.render(
                    f"{state.last_trap_count}x COMBO!  +{total}", True, (255, 210, 50)
                )
            else:
                combo_surf = small_font.render(f"Trapped!  +{TRAP_SCORE}", True, colors["cheese"])
            screen.blit(combo_surf, (SCREEN_WIDTH // 2 - combo_surf.get_width() // 2, 44))
            state.trap_combo_flash -= 1

        if state.level_clear_delay > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 80))
            screen.blit(overlay, (0, 0))
            next_level = state.level + 1
            lvl_surf = title_font.render(f"Level {next_level}", True, colors["levelup"])
            msg = font.render("Get ready...", True, colors["text"])
            screen.blit(lvl_surf, (SCREEN_WIDTH // 2 - lvl_surf.get_width() // 2, SCREEN_HEIGHT // 2 - 48))
            screen.blit(msg,      (SCREEN_WIDTH // 2 - msg.get_width()      // 2, SCREEN_HEIGHT // 2 + 4))

        if state.respawn_flash > 0 and (state.respawn_flash // 6) % 2 == 0:
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 200, 35))
            screen.blit(flash, (0, 0))

        if state.game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            screen.blit(overlay, (0, 0))
            text1 = font.render("Game Over", True, colors["alert"])
            score_surf = font.render(
                f"Score: {state.score:05d}   Level: {state.level}", True, colors["text"]
            )
            y0 = SCREEN_HEIGHT // 2 - 80
            screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, y0))
            if new_high_score:
                hs_surf = font.render("NEW HIGH SCORE!", True, (255, 220, 50))
                screen.blit(hs_surf,    (SCREEN_WIDTH // 2 - hs_surf.get_width()    // 2, y0 + 40))
                screen.blit(score_surf, (SCREEN_WIDTH // 2 - score_surf.get_width() // 2, y0 + 82))
            else:
                screen.blit(score_surf, (SCREEN_WIDTH // 2 - score_surf.get_width() // 2, y0 + 40))
            if entering_initials:
                init_hint = small_font.render("Enter your initials ↓", True, (255, 220, 80))
                screen.blit(init_hint, (SCREEN_WIDTH // 2 - init_hint.get_width() // 2, y0 + 130))
            else:
                btn_y = SCREEN_HEIGHT // 2 + 20
                _tbtn_menu_rect.center    = (SCREEN_WIDTH // 2 - 100, btn_y)
                _tbtn_restart_rect.center = (SCREEN_WIDTH // 2 + 100, btn_y)
                _draw_touch_btn(screen, _tbtn_menu_rect,    "⬅ MENU",    (55, 50, 38), (200, 190, 150))
                _draw_touch_btn(screen, _tbtn_restart_rect, "↺ RESTART", (55, 50, 38), (200, 190, 150))
                hint_go = tiny_font.render("or ENTER = menu  •  R = restart", True, (100, 95, 75))
                screen.blit(hint_go, (SCREEN_WIDTH // 2 - hint_go.get_width() // 2, btn_y + 48))

    def draw_help_overlay() -> None:
        """Draw the CONTROLS help panel overlay."""
        panel_w, panel_h = 560, 380
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = SCREEN_HEIGHT // 2 - panel_h // 2
        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill((12, 10, 8, 210))
        screen.blit(bg, (panel_x, panel_y))
        pygame.draw.rect(screen, (100, 90, 70), (panel_x, panel_y, panel_w, panel_h), 2)

        heading = font.render("CONTROLS", True, (220, 200, 80))
        screen.blit(heading, (SCREEN_WIDTH // 2 - heading.get_width() // 2, panel_y + 16))

        bindings = [
            ("Arrows / WASD",  "Move the mouse"),
            ("P",              "Pause / resume"),
            ("H",              "Show / hide this help"),
            ("R",              "Restart  (game-over screen)"),
            ("Enter",          "Confirm / back to menu"),
            ("Esc",            "Quit"),
            ("", ""),
            ("Push blocks",    "Trap cats by surrounding them"),
            ("Multi-trap",     f"+{MULTI_TRAP_BONUS} combo bonus per extra cat"),
            ("Cheese tile",    f"+{CHEESE_SCORE} pts each"),
        ]
        key_x  = panel_x + 30
        desc_x = panel_x + 230
        row_y  = panel_y + 58
        for key, desc in bindings:
            if not key:
                row_y += 8
                continue
            k_surf = small_font.render(key,  True, (255, 215, 60))
            d_surf = small_font.render(desc, True, colors["text"])
            screen.blit(k_surf, (key_x,  row_y))
            screen.blit(d_surf, (desc_x, row_y))
            row_y += 26

        close = small_font.render("Tap anywhere or press H to close", True, (110, 105, 80))
        screen.blit(close, (SCREEN_WIDTH // 2 - close.get_width() // 2, panel_y + panel_h - 28))

    def draw_virtual_joystick() -> None:
        """Render the floating on-screen thumbstick (touch input)."""
        sz = (VJOY_RADIUS + 8) * 2
        joy_surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        sc = sz // 2  # centre within the surface

        # Outer filled ring (more visible on iPad)
        pygame.draw.circle(joy_surf, (255, 255, 255, 22), (sc, sc), VJOY_RADIUS)
        pygame.draw.circle(joy_surf, (255, 255, 255, 110), (sc, sc), VJOY_RADIUS, 3)

        # Cardinal direction arrows
        pip_r = VJOY_RADIUS - 16
        arrow_pts = {
            (1,  0): [(sc + pip_r - 6, sc - 6), (sc + pip_r + 6, sc), (sc + pip_r - 6, sc + 6)],
            (-1, 0): [(sc - pip_r + 6, sc - 6), (sc - pip_r - 6, sc), (sc - pip_r + 6, sc + 6)],
            (0,  1): [(sc - 6, sc + pip_r - 6), (sc, sc + pip_r + 6), (sc + 6, sc + pip_r - 6)],
            (0, -1): [(sc - 6, sc - pip_r + 6), (sc, sc - pip_r - 6), (sc + 6, sc - pip_r + 6)],
        }
        cur_dir = _vjoy_dir(vjoy_offset) if vjoy_active else (0, 0)
        for d, pts in arrow_pts.items():
            alpha = 230 if d == cur_dir else 110
            pygame.draw.polygon(joy_surf, (255, 255, 255, alpha), pts)

        # Thumb circle — clamped to ring travel area when active
        if vjoy_active:
            ox, oy = vjoy_offset
            dist = math.hypot(ox, oy)
            max_dist = VJOY_RADIUS - VJOY_THUMB_R - 4
            if dist > max_dist and dist > 0:
                ox = ox * max_dist / dist
                oy = oy * max_dist / dist
            tx, ty = sc + int(ox), sc + int(oy)
            pygame.draw.circle(joy_surf, (255, 255, 255, 190), (tx, ty), VJOY_THUMB_R)
            pygame.draw.circle(joy_surf, (255, 255, 255, 255), (tx, ty), VJOY_THUMB_R, 3)
        else:
            # Resting — semi-transparent centre knob
            pygame.draw.circle(joy_surf, (255, 255, 255, 70),  (sc, sc), VJOY_THUMB_R)
            pygame.draw.circle(joy_surf, (255, 255, 255, 130), (sc, sc), VJOY_THUMB_R, 2)

        screen.blit(joy_surf, (vjoy_cx - sc, vjoy_cy - sc))

    def draw_initials_entry() -> None:
        """Full-screen overlay for entering 3-character initials on a high score."""
        nonlocal initials_key_rects

        # Dark panel
        panel_w, panel_h = 600, 420
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = SCREEN_HEIGHT // 2 - panel_h // 2
        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill((10, 8, 6, 230))
        screen.blit(bg, (panel_x, panel_y))
        pygame.draw.rect(screen, (255, 215, 50), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)

        # Title
        t1 = font.render("NEW HIGH SCORE!", True, (255, 220, 50))
        screen.blit(t1, (SCREEN_WIDTH // 2 - t1.get_width() // 2, panel_y + 14))
        t2 = small_font.render("Enter your initials:", True, (210, 200, 160))
        screen.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, panel_y + 50))

        # Three character boxes
        box_w, box_h = 58, 70
        box_gap = 16
        boxes_total = 3 * box_w + 2 * box_gap
        bx0 = SCREEN_WIDTH // 2 - boxes_total // 2
        by0 = panel_y + 86
        for i in range(3):
            bx = bx0 + i * (box_w + box_gap)
            active = i == len(entry_initials)
            box_col = (80, 70, 50) if not active else (100, 90, 60)
            border_col = (255, 215, 50) if active else (150, 140, 100)
            pygame.draw.rect(screen, box_col, (bx, by0, box_w, box_h), border_radius=6)
            pygame.draw.rect(screen, border_col, (bx, by0, box_w, box_h), 2, border_radius=6)
            if i < len(entry_initials):
                ch_surf = title_font.render(entry_initials[i], True, (255, 230, 80))
                screen.blit(ch_surf, (bx + box_w // 2 - ch_surf.get_width() // 2,
                                      by0 + box_h // 2 - ch_surf.get_height() // 2))
            elif active and (animation_frame // 20) % 2 == 0:
                cx2 = bx + box_w // 2
                pygame.draw.line(screen, (255, 215, 50), (cx2, by0 + 12), (cx2, by0 + box_h - 12), 3)

        # Virtual A-Z keyboard (9 cols x 3 rows)
        keys_layout = [list("ABCDEFGHI"), list("JKLMNOPQR"), list("STUVWXYZ⌫")]
        btn_w2, btn_h2 = 50, 42
        btn_gap = 5
        row_w = 9 * btn_w2 + 8 * btn_gap
        kx0 = SCREEN_WIDTH // 2 - row_w // 2
        ky0 = panel_y + 178
        new_key_rects: list[tuple[str, pygame.Rect]] = []
        for row_i, row in enumerate(keys_layout):
            for col_i, ch in enumerate(row):
                kx = kx0 + col_i * (btn_w2 + btn_gap)
                ky = ky0 + row_i * (btn_h2 + btn_gap)
                r = pygame.Rect(kx, ky, btn_w2, btn_h2)
                is_bksp = ch == "⌫"
                col = (80, 30, 30) if is_bksp else (55, 52, 40)
                pygame.draw.rect(screen, col, r, border_radius=6)
                pygame.draw.rect(screen, (130, 120, 90), r, 1, border_radius=6)
                lbl = small_font.render(ch, True, (240, 230, 180))
                screen.blit(lbl, (r.centerx - lbl.get_width() // 2, r.centery - lbl.get_height() // 2))
                new_key_rects.append((ch, r))

        # DONE button — placed below the last keyboard row with a clear gap
        done_r = pygame.Rect(0, 0, 180, 50)
        done_r.center = (SCREEN_WIDTH // 2, ky0 + 2 * (btn_h2 + btn_gap) + btn_h2 + btn_gap + done_r.height // 2 + 6)
        done_col = (50, 110, 60) if entry_initials else (45, 45, 35)
        pygame.draw.rect(screen, done_col, done_r, border_radius=10)
        pygame.draw.rect(screen, (120, 200, 130) if entry_initials else (80, 80, 60), done_r, 2, border_radius=10)
        done_lbl = small_font.render("✓  DONE", True, (200, 240, 200) if entry_initials else (120, 120, 100))
        screen.blit(done_lbl, (done_r.centerx - done_lbl.get_width() // 2,
                                done_r.centery - done_lbl.get_height() // 2))
        new_key_rects.append(("✓", done_r))
        initials_key_rects = new_key_rects


    def draw_title_screen() -> None:
        # --- Background with subtle grid dot pattern ---
        screen.fill((12, 10, 8))
        dot_col = (24, 21, 17)
        for gx in range(0, SCREEN_WIDTH + 1, 40):
            for gy in range(0, SCREEN_HEIGHT + 1, 40):
                pygame.draw.circle(screen, dot_col, (gx, gy), 1)

        # --- Title: shadow + outline glow + main text ---
        title_text = GAME_TITLE.upper()
        t_shadow = big_title_font.render(title_text, True, (0, 0, 0))
        screen.blit(t_shadow, (SCREEN_WIDTH // 2 - t_shadow.get_width() // 2 + 4, 26))
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            t_outline = big_title_font.render(title_text, True, (90, 72, 14))
            screen.blit(t_outline, (SCREEN_WIDTH // 2 - t_outline.get_width() // 2 + dx, 22 + dy))
        t_main = big_title_font.render(title_text, True, (242, 218, 85))
        screen.blit(t_main, (SCREEN_WIDTH // 2 - t_main.get_width() // 2, 22))

        # --- Tagline ---
        sub_surf = small_font.render("A Cat & Mouse Puzzle Game", True, (158, 146, 100))
        screen.blit(sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 100))

        # Decorative separator
        sep_y, sep_cx = 126, SCREEN_WIDTH // 2
        pygame.draw.line(screen, (55, 52, 38), (sep_cx - 170, sep_y), (sep_cx - 18, sep_y), 1)
        pygame.draw.circle(screen, (120, 108, 62), (sep_cx, sep_y), 4)
        pygame.draw.line(screen, (55, 52, 38), (sep_cx + 18, sep_y), (sep_cx + 170, sep_y), 1)

        # --- HIGH SCORES panel ---
        panel_rect = pygame.Rect(SCREEN_WIDTH // 2 - 250, 138, 500, 232)
        panel_surf = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (0, 0, 0, 135), panel_surf.get_rect(), border_radius=14)
        screen.blit(panel_surf, panel_rect.topleft)
        pygame.draw.rect(screen, (62, 57, 40), panel_rect, 1, border_radius=14)
        hs_label = font.render("*  HIGH SCORES  *", True, (220, 198, 74))
        screen.blit(hs_label, (SCREEN_WIDTH // 2 - hs_label.get_width() // 2, 152))
        if scores:
            for i, entry in enumerate(scores[:5]):
                row_col = (255, 220, 60) if i == 0 else ((205, 188, 155) if i < 3 else (155, 148, 118))
                rank = ["1ST", "2ND", "3RD", "4TH", "5TH"][i]
                line = small_font.render(
                    f"{rank}  {entry.get('initials', '---'):<3}   {entry['score']:>6d}   LVL {entry['level']:02d}",
                    True, row_col,
                )
                screen.blit(line, (SCREEN_WIDTH // 2 - line.get_width() // 2, 186 + i * 30))
        else:
            empty = small_font.render("No scores yet  -  be the first!", True, (128, 122, 98))
            screen.blit(empty, (SCREEN_WIDTH // 2 - empty.get_width() // 2, 218))

        # --- Difficulty selector ---
        dlabel = small_font.render("-  SELECT DIFFICULTY  -", True, (168, 158, 116))
        screen.blit(dlabel, (SCREEN_WIDTH // 2 - dlabel.get_width() // 2, SCREEN_HEIGHT - 248))
        diff_colors     = {"easy": (36, 100, 46), "normal": (38, 40, 100), "hard": (108, 28, 28)}
        diff_text_cols  = {"easy": (130, 240, 148), "normal": (188, 186, 255), "hard": (255, 138, 128)}
        diff_glow_cols  = {"easy": (70, 210, 90),  "normal": (120, 120, 255), "hard": (255, 90, 80)}
        btn_w, btn_h = 158, 62
        x_offsets = [-170, 0, 170]
        for i, d in enumerate(DIFFICULTIES):
            r = pygame.Rect(0, 0, btn_w, btn_h)
            r.center = (SCREEN_WIDTH // 2 + x_offsets[i], SCREEN_HEIGHT - 195)
            active = (i == diff_idx)
            # Shadow
            sh_s = pygame.Surface((r.width + 4, r.height + 6), pygame.SRCALPHA)
            pygame.draw.rect(sh_s, (0, 0, 0, 85), sh_s.get_rect(), border_radius=13)
            screen.blit(sh_s, (r.x - 1, r.y + 4))
            # Glow ring if active
            if active:
                glow_s = pygame.Surface((r.width + 12, r.height + 12), pygame.SRCALPHA)
                pygame.draw.rect(glow_s, (*diff_glow_cols[d], 55), glow_s.get_rect(), border_radius=16)
                screen.blit(glow_s, (r.x - 6, r.y - 6))
            # Fill
            fill_col = tuple(min(255, c + 52) for c in diff_colors[d]) if active else diff_colors[d]
            pygame.draw.rect(screen, fill_col, r, border_radius=12)
            # Inner top sheen
            hi_s = pygame.Surface((r.width - 8, r.height // 2 - 2), pygame.SRCALPHA)
            pygame.draw.rect(hi_s, (255, 255, 255, 38 if active else 16), hi_s.get_rect(), border_radius=9)
            screen.blit(hi_s, (r.x + 4, r.y + 4))
            # Border
            border_col = diff_glow_cols[d] if active else (62, 58, 44)
            pygame.draw.rect(screen, border_col, r, 3 if active else 1, border_radius=12)
            # Label
            txt_col = diff_text_cols[d] if active else (108, 104, 78)
            lbl = small_font.render(d.upper(), True, txt_col)
            lbl_y_off = -4 if active else 0
            screen.blit(lbl, (r.centerx - lbl.get_width() // 2, r.centery + lbl_y_off - lbl.get_height() // 2))
            if active:
                ck = tiny_font.render("selected", True, (*diff_text_cols[d][:3],))
                screen.blit(ck, (r.centerx - ck.get_width() // 2, r.centery + 10))

        # --- PLAY button with smooth pulsing glow ---
        play_rect = pygame.Rect(0, 0, 290, 74)
        play_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 112)
        pulse_v = (math.sin(animation_frame / 60.0 * math.pi * 2) + 1) / 2  # 0..1 smooth
        play_col = (
            int(48 + 28 * pulse_v),
            int(118 + 50 * pulse_v),
            int(58 + 28 * pulse_v),
        )
        # Outer glow ring
        glow_r = play_rect.inflate(int(10 + 8 * pulse_v), int(10 + 8 * pulse_v))
        glow_surf = pygame.Surface((glow_r.width, glow_r.height), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (90, 210, 110, int(35 + 45 * pulse_v)), glow_surf.get_rect(), border_radius=20)
        screen.blit(glow_surf, glow_r.topleft)
        # Shadow
        sh_p = pygame.Surface((play_rect.width + 6, play_rect.height + 6), pygame.SRCALPHA)
        pygame.draw.rect(sh_p, (0, 0, 0, 105), sh_p.get_rect(), border_radius=18)
        screen.blit(sh_p, play_rect.move(3, 5).topleft)
        # Fill
        pygame.draw.rect(screen, play_col, play_rect, border_radius=16)
        # Top inner sheen
        hi_p = pygame.Surface((play_rect.width - 12, play_rect.height // 2 - 4), pygame.SRCALPHA)
        pygame.draw.rect(hi_p, (255, 255, 255, 42), hi_p.get_rect(), border_radius=12)
        screen.blit(hi_p, (play_rect.x + 6, play_rect.y + 5))
        # Border
        border_g = int(130 + 90 * pulse_v)
        pygame.draw.rect(screen, (border_g // 2, border_g, border_g // 2 + 10), play_rect, 3, border_radius=16)
        # Label using title_font for large readable text
        play_lbl = title_font.render("  PLAY  ", True, (215, 255, 220))
        screen.blit(play_lbl, (play_rect.centerx - play_lbl.get_width() // 2,
                                play_rect.centery - play_lbl.get_height() // 2))

        # "Tap or click" hint
        hint = tiny_font.render("Tap  or  Click  PLAY  to  Begin", True, (96, 92, 68))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 66))

        legal1 = tiny_font.render("Inspired by classic Windows-era cat-and-mouse puzzle games", True, (78, 74, 56))
        legal2 = tiny_font.render("Unofficial fan remake  -  open source", True, (78, 74, 56))
        screen.blit(legal1, (SCREEN_WIDTH // 2 - legal1.get_width() // 2, SCREEN_HEIGHT - 46))
        screen.blit(legal2, (SCREEN_WIDTH // 2 - legal2.get_width() // 2, SCREEN_HEIGHT - 30))

    while running:
        animation_frame += 1
        player_moved = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # ---- keyboard quit (skip ESC-to-quit on web) --------------------
            # ---- touch finger events ----------------------------------------
            elif event.type == pygame.FINGERDOWN:
                sx = int(event.x * SCREEN_WIDTH)
                sy = int(event.y * SCREEN_HEIGHT)
                if phase == "title":
                    # Difficulty buttons — three distinct rects in bottom strip
                    btn_w2, btn_h2 = 158, 62
                    x_offsets2 = [-170, 0, 170]
                    for ti, _d in enumerate(DIFFICULTIES):
                        r2 = pygame.Rect(0, 0, btn_w2, btn_h2)
                        r2.center = (SCREEN_WIDTH // 2 + x_offsets2[ti], SCREEN_HEIGHT - 195)
                        if r2.collidepoint(sx, sy):
                            diff_idx = ti
                            break
                    # PLAY button
                    play_r = pygame.Rect(0, 0, 290, 74)
                    play_r.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 112)
                    if play_r.collidepoint(sx, sy):
                        s = DIFF_SETTINGS[DIFFICULTIES[diff_idx]]
                        state = GameState(
                            cat_delay_bonus=s["cat_delay_bonus"],
                            cat_count_offset=s["cat_count_offset"],
                        )
                        cat_ms_accum = 0
                        countdown_ms = COUNTDOWN_TOTAL_MS
                        block_tweens.clear()
                        score_saved = False
                        new_high_score = False
                        phase = "playing"
                elif phase == "playing":
                    # HUD touch buttons
                    if _tbtn_pause_rect.collidepoint(sx, sy):
                        if not state.game_over:
                            state.paused = not state.paused
                    elif _tbtn_help_rect.collidepoint(sx, sy):
                        if not state.game_over and not state.paused:
                            show_help = not show_help
                    # Game-over overlay buttons
                    elif state.game_over:
                        if _tbtn_menu_rect.collidepoint(sx, sy):
                            phase = "title"
                            scores = load_scores()
                        elif _tbtn_restart_rect.collidepoint(sx, sy):
                            state.restart_game()
                            block_tweens.clear()
                            score_saved = False
                            new_high_score = False
                        # Initials virtual keyboard (shown over game-over overlay)
                        elif entering_initials:
                            for key_char, key_rect in initials_key_rects:
                                if key_rect.collidepoint(sx, sy):
                                    if key_char == "⌫":
                                        entry_initials = entry_initials[:-1]
                                    elif key_char == "✓" and entry_initials:
                                        save_score(state.score, state.level, entry_initials)
                                        score_saved = True
                                        entering_initials = False
                                        scores = load_scores()
                                    elif len(entry_initials) < 3 and key_char not in ("⌫", "✓"):
                                        entry_initials += key_char
                                    break
                    # Pause resume button
                    elif state.paused:
                        if _tbtn_resume_rect.collidepoint(sx, sy):
                            state.paused = False
                    # Help close — tap anywhere outside panel closes it
                    elif show_help:
                        show_help = False
                    else:
                        # Floating joystick — spawn at touch point (left 60% of screen)
                        if sx < SCREEN_WIDTH * 3 // 5 and not vjoy_active:
                            # Float to touch position, clamped away from edges
                            vjoy_cx = max(VJOY_RADIUS + 10, min(sx, SCREEN_WIDTH * 3 // 5 - VJOY_RADIUS - 10))
                            vjoy_cy = max(VJOY_RADIUS + HUD_HEIGHT + 10, min(sy, SCREEN_HEIGHT - VJOY_RADIUS - 10))
                            vjoy_active = True
                            vjoy_finger_id = event.finger_id
                            vjoy_offset = (0.0, 0.0)
                            vjoy_last_dir = (0, 0)
                            vjoy_held_frames = 0
            elif event.type == pygame.FINGERMOTION:
                if vjoy_active and event.finger_id == vjoy_finger_id:
                    sx = int(event.x * SCREEN_WIDTH)
                    sy = int(event.y * SCREEN_HEIGHT)
                    vjoy_offset = (float(sx - vjoy_cx), float(sy - vjoy_cy))
            elif event.type == pygame.FINGERUP:
                if vjoy_active and event.finger_id == vjoy_finger_id:
                    vjoy_active = False
                    vjoy_finger_id = None
                    vjoy_offset = (0.0, 0.0)
                    vjoy_last_dir = (0, 0)
                    vjoy_held_frames = 0
                    # Return joystick to default corner position
                    vjoy_cx = _vjoy_default_cx
                    vjoy_cy = _vjoy_default_cy
            # ---- keyboard events --------------------------------------------
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # On web, ESC is intercepted by the browser; go to title instead
                    if sys.platform == "emscripten":
                        phase = "title"
                        scores = load_scores()
                    else:
                        running = False
                elif phase == "title":
                    if event.key == pygame.K_RETURN:
                        s = DIFF_SETTINGS[DIFFICULTIES[diff_idx]]
                        state = GameState(
                            cat_delay_bonus=s["cat_delay_bonus"],
                            cat_count_offset=s["cat_count_offset"],
                        )
                        cat_ms_accum = 0
                        countdown_ms = COUNTDOWN_TOTAL_MS
                        block_tweens.clear()
                        score_saved = False
                        new_high_score = False
                        phase = "playing"
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        diff_idx = (diff_idx - 1) % len(DIFFICULTIES)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        diff_idx = (diff_idx + 1) % len(DIFFICULTIES)
                elif phase == "playing":
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        key_left_held = True
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        key_right_held = True
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        key_up_held = True
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        key_down_held = True
                    if state.game_over:
                        if event.key == pygame.K_RETURN:
                            phase = "title"
                            scores = load_scores()
                        elif event.key == pygame.K_r:
                            state.restart_game()
                            block_tweens.clear()
                            score_saved = False
                            new_high_score = False
                        elif entering_initials:
                            if pygame.K_a <= event.key <= pygame.K_z and len(entry_initials) < 3:
                                entry_initials += chr(event.key - pygame.K_a + ord("A"))
                            elif event.key == pygame.K_BACKSPACE:
                                entry_initials = entry_initials[:-1]
                            elif event.key == pygame.K_RETURN and entry_initials:
                                save_score(state.score, state.level, entry_initials)
                                score_saved = True
                                entering_initials = False
                                scores = load_scores()
                    elif event.key == pygame.K_p:
                        state.paused = not state.paused
                    elif event.key == pygame.K_h:
                        show_help = not show_help
                    elif not state.paused and not show_help and countdown_ms <= 0:
                        if event.key in (pygame.K_LEFT, pygame.K_a):
                            player_moved = state.handle_player_move(-1, 0)
                            if player_moved:
                                mouse_facing = -1
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            player_moved = state.handle_player_move(1, 0)
                            if player_moved:
                                mouse_facing = 1
                        elif event.key in (pygame.K_UP, pygame.K_w):
                            player_moved = state.handle_player_move(0, -1)
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            player_moved = state.handle_player_move(0, 1)

            elif event.type == pygame.KEYUP and phase == "playing":
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    key_left_held = False
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    key_right_held = False
                elif event.key in (pygame.K_UP, pygame.K_w):
                    key_up_held = False
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    key_down_held = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                sx, sy = event.pos
                if phase == "title":
                    # Difficulty buttons
                    btn_w_m, btn_h_m = 158, 62
                    x_offsets_m = [-170, 0, 170]
                    for ti, _d in enumerate(DIFFICULTIES):
                        r_m = pygame.Rect(0, 0, btn_w_m, btn_h_m)
                        r_m.center = (SCREEN_WIDTH // 2 + x_offsets_m[ti], SCREEN_HEIGHT - 195)
                        if r_m.collidepoint(sx, sy):
                            diff_idx = ti
                            break
                    # PLAY button
                    play_r_m = pygame.Rect(0, 0, 290, 74)
                    play_r_m.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 112)
                    if play_r_m.collidepoint(sx, sy):
                        s = DIFF_SETTINGS[DIFFICULTIES[diff_idx]]
                        state = GameState(
                            cat_delay_bonus=s["cat_delay_bonus"],
                            cat_count_offset=s["cat_count_offset"],
                        )
                        cat_ms_accum = 0
                        countdown_ms = COUNTDOWN_TOTAL_MS
                        block_tweens.clear()
                        score_saved = False
                        new_high_score = False
                        phase = "playing"
                elif phase == "playing":
                    if _tbtn_pause_rect.collidepoint(sx, sy):
                        if not state.game_over:
                            state.paused = not state.paused
                    elif _tbtn_help_rect.collidepoint(sx, sy):
                        if not state.game_over and not state.paused:
                            show_help = not show_help
                    elif state.paused and _tbtn_resume_rect.collidepoint(sx, sy):
                        state.paused = False
                    elif state.game_over:
                        if _tbtn_menu_rect.collidepoint(sx, sy):
                            phase = "title"
                            scores = load_scores()
                        elif _tbtn_restart_rect.collidepoint(sx, sy):
                            state.restart_game()
                            block_tweens.clear()
                            score_saved = False

        # ---- keyboard auto-repeat for held arrows/WASD ---------------------
        if phase == "playing" and not state.paused and not show_help and not state.game_over and countdown_ms <= 0:
            # Event-driven held-key tracking is primary; polling is a fallback.
            keys = pygame.key.get_pressed()
            k_left = key_left_held or keys[pygame.K_LEFT] or keys[pygame.K_a]
            k_right = key_right_held or keys[pygame.K_RIGHT] or keys[pygame.K_d]
            k_up = key_up_held or keys[pygame.K_UP] or keys[pygame.K_w]
            k_down = key_down_held or keys[pygame.K_DOWN] or keys[pygame.K_s]

            d = (0, 0)
            if k_left and not k_right:
                d = (-1, 0)
            elif k_right and not k_left:
                d = (1, 0)
            elif k_up and not k_down:
                d = (0, -1)
            elif k_down and not k_up:
                d = (0, 1)

            if d != (0, 0):
                if d != key_last_dir:
                    key_last_dir = d
                    key_held_frames = 0
                else:
                    key_held_frames += 1
                    if key_held_frames == KEY_INITIAL_DELAY or (
                        key_held_frames > KEY_INITIAL_DELAY
                        and (key_held_frames - KEY_INITIAL_DELAY) % KEY_REPEAT_EVERY == 0
                    ):
                        moved = state.handle_player_move(d[0], d[1])
                        if moved:
                            player_moved = True
                            if d[0] != 0:
                                mouse_facing = d[0]
            else:
                key_last_dir = (0, 0)
                key_held_frames = 0

        # ---- virtual joystick auto-repeat (runs every frame while held) -----
        if vjoy_active and phase == "playing":
            d = _vjoy_dir(vjoy_offset)
            if d != (0, 0):
                if d != vjoy_last_dir:
                    # New direction — move immediately, reset hold counter
                    vjoy_last_dir = d
                    vjoy_held_frames = 0
                    if _apply_vjoy_move(d):
                        player_moved = True
                else:
                    vjoy_held_frames += 1
                    if vjoy_held_frames == VJOY_INITIAL_DELAY or (
                        vjoy_held_frames > VJOY_INITIAL_DELAY
                        and (vjoy_held_frames - VJOY_INITIAL_DELAY) % VJOY_REPEAT_EVERY == 0
                    ):
                        if _apply_vjoy_move(d):
                            player_moved = True
            else:
                vjoy_last_dir = (0, 0)
                vjoy_held_frames = 0

        if phase == "playing" and not state.paused and not show_help:
            # Countdown: tick down, block cat movement until it expires
            if countdown_ms > 0:
                countdown_ms = max(0, countdown_ms - dt_ms)
            # Handle respawn-triggered countdowns
            if state.respawn_pending and not state.game_over:
                state.respawn_pending = False
                countdown_ms = COUNTDOWN_TOTAL_MS
            if not state.game_over and countdown_ms <= 0:
                cat_ms_accum += dt_ms
                # Levels 1-20: slow ramp (+20ms/level). After 20: steeper ramp (+50ms/level extra).
                _lvl = state.level - 1
                _base_ramp = min(_lvl, 20) * 20
                _extra_ramp = max(0, _lvl - 20) * 50
                cat_delay_ms = max(150, CAT_MOVE_DELAY_MS - _base_ramp - _extra_ramp + state.cat_delay_bonus)
                if cat_ms_accum >= cat_delay_ms:
                    cat_ms_accum = 0
                    state.step_cats()

            if state.level_clear_delay > 0 and not state.game_over:
                state.level_clear_delay -= 1
                if state.level_clear_delay == 0:
                    state.reset_level(state.level + 1)
                    block_tweens.clear()
                    countdown_ms = COUNTDOWN_TOTAL_MS
                    cat_ms_accum = 0

            if state.respawn_flash > 0:
                state.respawn_flash -= 1

            if state.game_over and not score_saved:
                new_high_score = is_high_score(state.score)
                if new_high_score and not entering_initials:
                    entering_initials = True
                    entry_initials = ""
                elif not new_high_score:
                    save_score(state.score, state.level)
                    score_saved = True
                    scores = load_scores()

            if state.last_block_push is not None:
                fx, fy, tx, ty = state.last_block_push
                block_tweens.append({"gx0": fx, "gy0": fy, "gx1": tx, "gy1": ty, "t": 0.0})
                state.last_block_push = None
            for tw in block_tweens:
                tw["t"] = min(1.0, tw["t"] + 1.0 / TWEEN_FRAMES)
            block_tweens[:] = [tw for tw in block_tweens if tw["t"] < 1.0]

            for snd_name in state.pending_sounds:
                s = snd.get(snd_name)
                if s:
                    s.play()
            state.pending_sounds.clear()

        if phase == "playing":
            draw_board()
            if countdown_ms > 0 and not state.game_over and not state.paused:
                # Countdown overlay: dim screen then show big number
                _cd_ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                _cd_ov.fill((0, 0, 0, 110))
                screen.blit(_cd_ov, (0, 0))
                if countdown_ms > COUNTDOWN_GO_MS:
                    _cd_step = math.ceil((countdown_ms - COUNTDOWN_GO_MS) / COUNTDOWN_STEP_MS)
                    _cd_label = str(max(1, min(3, _cd_step)))
                    _cd_col = (255, 220, 60)
                else:
                    _cd_label = "GO!"
                    _cd_col = (100, 255, 130)
                _cd_shadow = title_font.render(_cd_label, True, (0, 0, 0))
                _cd_surf   = title_font.render(_cd_label, True, _cd_col)
                _cd_x = SCREEN_WIDTH  // 2 - _cd_surf.get_width()  // 2
                _cd_y = SCREEN_HEIGHT // 2 - _cd_surf.get_height() // 2
                screen.blit(_cd_shadow, (_cd_x + 3, _cd_y + 3))
                screen.blit(_cd_surf,   (_cd_x,     _cd_y))
            if state.paused and not state.game_over:
                # Pause overlay
                ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                ov.fill((0, 0, 0, 130))
                screen.blit(ov, (0, 0))
                # Blurred panel
                panel_w, panel_h = 340, 200
                panel_x = SCREEN_WIDTH // 2 - panel_w // 2
                panel_y = SCREEN_HEIGHT // 2 - panel_h // 2
                panel_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
                panel_bg.fill((20, 18, 14, 220))
                screen.blit(panel_bg, (panel_x, panel_y))
                pygame.draw.rect(screen, (160, 148, 110), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=12)
                # Title
                p_title = title_font.render("PAUSED", True, (240, 220, 100))
                screen.blit(p_title, (SCREEN_WIDTH // 2 - p_title.get_width() // 2, panel_y + 24))
                # Hints
                p_hint1 = small_font.render("Press  P  or tap PAUSE to resume", True, (180, 170, 140))
                screen.blit(p_hint1, (SCREEN_WIDTH // 2 - p_hint1.get_width() // 2, panel_y + 82))
                # Resume button
                _tbtn_resume_rect.center = (SCREEN_WIDTH // 2, panel_y + 148)
                _draw_touch_btn(screen, _tbtn_resume_rect, "RESUME", (48, 110, 58), (180, 255, 190))
            draw_virtual_joystick()
            if entering_initials:
                draw_initials_entry()
            if show_help:
                draw_help_overlay()
        else:
            draw_title_screen()

        pygame.display.flip()
        await asyncio.sleep(0)  # required for pygbag / WebAssembly
        dt_ms = clock.tick(FPS)

    pygame.quit()
