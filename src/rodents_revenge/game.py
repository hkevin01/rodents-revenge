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
CONTROL_LANE_W = 420
ACTION_LANE_W = 360
BOARD_ORIGIN_X = CONTROL_LANE_W
BOARD_PIXEL_W = GRID_WIDTH * TILE_SIZE
BOARD_RIGHT_X = BOARD_ORIGIN_X + BOARD_PIXEL_W
SCREEN_WIDTH = BOARD_ORIGIN_X + BOARD_PIXEL_W + ACTION_LANE_W
SCREEN_HEIGHT = GRID_HEIGHT * TILE_SIZE + HUD_HEIGHT

EMPTY = 0
BLOCK = 1
WALL = 2
CHEESE = 3

MOUSE_STEP_SCORE = 0
CHEESE_SCORE = 25
TRAP_SCORE = 100
MULTI_TRAP_BONUS = 150

CAT_MOVE_DELAY_MS = 2000
COUNTDOWN_STEP_MS = 800
COUNTDOWN_GO_MS = 500
COUNTDOWN_TOTAL_MS = 3 * COUNTDOWN_STEP_MS + COUNTDOWN_GO_MS
GAME_TITLE = "Rodent's Revenge"

VJOY_RADIUS = 190
VJOY_THUMB_R = 68
VJOY_DEADZONE = 30
VJOY_INITIAL_REPEAT_MS = 350
VJOY_REPEAT_MS = 300
VJOY_FLOAT = False
VJOY_TOUCH_RADIUS = 380
VJOY_AXIS_LOCK_RATIO = 3.0
VJOY_ENGAGE_PCT = 0.36
VJOY_RELEASE_PCT = 0.24
VJOY_ANCHOR_X_PCT = 0.24
VJOY_ANCHOR_Y_PCT = 0.50

KEY_INITIAL_DELAY = 10
KEY_REPEAT_EVERY = 5

TBTN_W = 90
TBTN_H = 50

LEVEL_PRESETS: dict[int, list[str]] = {
    1: [
        "..................",
        "............X.....",
        ".....BBBBBBBB.....",
        "....BBBBBBBBBB....",
        "...BBB......BBB...",
        "...BBB.BBBB.BBB...",
        "...BBB.B..B.BBB...",
        "...BBB.B..B.BBB...",
        "...BBB.BBBB.BBB...",
        "...BBB......BBB...",
        "....BBBBBBBBBB....",
        ".....BBBBBBBB.....",
        ".........C........",
        "..................",
    ],
    2: [
        "..................",
        "..X..........X....",
        "....BBBBBBBBBB....",
        "...BBBBBBBBBBBB...",
        "...BBB.BBBB.BBB...",
        "...BBB.B..B.BBB...",
        "...BBBB....BBBB...",
        "...BBBB....BBBB...",
        "...BBB.B..B.BBB...",
        "...BBB.BBBB.BBB...",
        "...BBBBBBBBBBBB...",
        "....BBBBBBBBBB....",
        ".........C........",
        "..................",
    ],
    3: [
        "..................",
        "..X.....X.....X...",
        "...BBBBBBBBBBBB...",
        "..BB.BBBBBBBB.BB..",
        "..BB.B.BBBB.B.BB..",
        "..BB.BB....BB.BB..",
        "..BB.BB.BB.BB.BB..",
        "..BB.BB.BB.BB.BB..",
        "..BB.BB....BB.BB..",
        "..BB.B.BBBB.B.BB..",
        "..BB.BBBBBBBB.BB..",
        "...BBBBBBBBBBBB...",
        ".........C........",
        "..................",
    ],
    4: [
        "..................",
        "..X..........X....",
        "...BBBB..BBBB.....",
        "..BB..BBBBBB..BB..",
        "..BB.B.BBBB.B.BB..",
        "..BB.BB....BB.BB..",
        "..BB..B.BB.B..BB..",
        "..BB..B.BB.B..BB..",
        "..BB.BB....BB.BB..",
        "..BB.B.BBBB.B.BB..",
        "..BB..BBBBBB..BB..",
        "...BBBB..BBBB..X..",
        ".........C........",
        "..................",
    ],
    5: [
        "..................",
        "..X..........X....",
        "...BBBB..BBBB.....",
        "..BB..######..BB..",
        "..BB.#.BBBB.#.BB..",
        "..BB.#B....B#.BB..",
        "..BB..B.##.B..BB..",
        "..BB.#B....B#.BB..",
        "..BB.#.BBBB.#.BB..",
        "..BB..######..BB..",
        "...BBBB..BBBB..X..",
        ".........C........",
        "..................",
    ],
    6: [
        "..................",
        "..X..........X....",
        "...BBBBBBBBBBBB...",
        "..BB.########.BB..",
        "..BB.#.BBBB.#.BB..",
        "..BB.#B....B#.BB..",
        "..BB.#B.##.B#.BB..",
        "..BB..B....B..BB..",
        "..BB.#B.##.B#.BB..",
        "..BB.#.BBBB.#.BB..",
        "..BB.########.BB..",
        "...BBBBBBBBBBBBX..",
        ".........C........",
        "..................",
    ],
    7: [
        "..................",
        "..X....X.....X....",
        "...BBBBBBBBBBBB...",
        "..BB.########.BB..",
        "..BB.#.BBBB.#.BB..",
        "..BB.#B....B#.BB..",
        "..BB.#B.##.B#.BB..",
        "..BB.#B.##.B#.BB..",
        "..BB.#B....B#.BB..",
        "..BB.#.BBBB.#.BB..",
        "..BB.########.BB..",
        "...BBBBBBBBBBBB...",
        "..X......C........",
        "..................",
    ],
    8: [
        "..................",
        "..X....X.....X....",
        "...BBBBBBBBBBBB...",
        "..BB.########.BB..",
        "..BB.#..BB..#.BB..",
        "..BB.#B.##.B#.BB..",
        "..BB.#B....B#.BB..",
        "..BB.#B....B#.BB..",
        "..BB.#B.##.B#.BB..",
        "..BB.#..BB..#.BB..",
        "..BB.########.BB..",
        "...BBBBBBBBBBBB...",
        "..X.......C.......",
        "..................",
    ],
    9: [
        "..................",
        "..X....X.....X....",
        "..BBBBBBBBBBBBBB..",
        "..BB###BBBB###BB..",
        "..BB#..BBBB..#BB..",
        "..BB#.#.##.#.#BB..",
        "..BB#.#....#.#BB..",
        "..BB#.#....#.#BB..",
        "..BB#.#.##.#.#BB..",
        "..BB#..BBBB..#BB..",
        "..BB###BBBB###BB..",
        "..BBBBBBBBBBBBBB..",
        "..X.......C.......",
        "..................",
    ],
    10: [
        "..................",
        "..X....X.....X....",
        "..BBBB..####..BBBB",
        "..BB..##BB##..BB..",
        "..BB.#.BBBB.#.BB..",
        "..BB.#B.##.B#.BB..",
        "..BB##B....B##BB..",
        "..BB##B....B##BB..",
        "..BB.#B.##.B#.BB..",
        "..BB.#.BBBB.#.BB..",
        "..BB..##BB##..BB..",
        "BBBB..####..BBBBX.",
        "........C.........",
        "..................",
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
        wall_count = min(3 + level // 2, 10)
        block_count = min(64 + level * 10, 220)
        cat_count = max(1, min(2 + level + self.cat_count_offset, 12))
        self.last_block_push = None
        self.near_clear_warned = False

        self._place_random_cells(WALL, wall_count)
        self._place_random_cells(BLOCK, block_count)
        self._place_random_cells(CHEESE, min(1 + level // 20, 4))

        self.mouse_pos = self._find_centerish_free_cell()
        self.cats = self._find_outer_cat_spawns(cat_count, self.mouse_pos)

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

        self._thin_preset_walls(level, mouse_spawn, cat_spawns)

        self.last_block_push = None
        self.near_clear_warned = False

        forbidden: set[tuple[int, int]] = set(cat_spawns)
        if mouse_spawn is not None:
            forbidden.add(mouse_spawn)
        extra_blocks = min(22 + level * 4, 64)
        self._place_random_cells(BLOCK, extra_blocks, forbidden=forbidden)

        self.mouse_pos = self._find_centerish_free_cell(preferred=mouse_spawn)

        base_cat_count = max(1, len(cat_spawns))
        target_cat_count = max(1, base_cat_count + self.cat_count_offset)
        self.cats = self._find_outer_cat_spawns(target_cat_count, self.mouse_pos, preferred=cat_spawns)

        return True

    def _thin_preset_walls(
        self,
        level: int,
        mouse_spawn: tuple[int, int] | None,
        cat_spawns: list[tuple[int, int]],
    ) -> None:
        """Reduce dense handcrafted wall clusters so preset levels stay more open."""
        target_walls = {
            1: 10,
            2: 14,
            3: 18,
            4: 18,
            5: 20,
            6: 22,
            7: 24,
            8: 24,
            9: 28,
            10: 30,
        }.get(level)
        if target_walls is None:
            return

        protected = set(cat_spawns)
        if mouse_spawn is not None:
            protected.add(mouse_spawn)

        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.board[y][x] in (BLOCK, CHEESE):
                    protected.add((x, y))

        current_walls = sum(
            1
            for y in range(1, self.height - 1)
            for x in range(1, self.width - 1)
            if self.board[y][x] == WALL
        )
        if current_walls <= target_walls:
            return

        dirs8 = (
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1),
        )

        def is_protected(cell: tuple[int, int]) -> bool:
            cx, cy = cell
            return any(abs(cx - px) <= 1 and abs(cy - py) <= 1 for px, py in protected)

        def wall_neighbors(cell: tuple[int, int]) -> int:
            cx, cy = cell
            return sum(
                1
                for dx, dy in dirs8
                if self.in_bounds(cx + dx, cy + dy) and self.board[cy + dy][cx + dx] == WALL
            )

        while current_walls > target_walls:
            candidates = [
                (x, y)
                for y in range(1, self.height - 1)
                for x in range(1, self.width - 1)
                if self.board[y][x] == WALL and not is_protected((x, y))
            ]
            if not candidates:
                break

            dense = [cell for cell in candidates if wall_neighbors(cell) >= 3]
            pool = dense or candidates
            remove_x, remove_y = max(
                pool,
                key=lambda cell: (
                    wall_neighbors(cell),
                    min((abs(cell[0] - px) + abs(cell[1] - py) for px, py in protected), default=99),
                ),
            )
            # Prefer converting dense fixed walls into pushable boxes so the map
            # stays interactive rather than simply emptier.
            if wall_neighbors((remove_x, remove_y)) >= 4:
                self.board[remove_y][remove_x] = BLOCK
            else:
                self.board[remove_y][remove_x] = EMPTY
            current_walls -= 1

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
            # Classic behavior: a block may be pushed into cheese, crushing it.
            if self.board[cy][cx] not in (EMPTY, CHEESE) or self._cat_at(cx, cy) or (cx, cy) == self.mouse_pos:
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
        trap_set = self._trapped_cat_set()
        trapped = [cat for cat in self.cats if cat in trap_set]
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
        return (x, y) in self._trapped_cat_set()

    def _trapped_cat_set(self) -> set[tuple[int, int]]:
        """Return all cats that are trapped, including enclosed cat groups.

        Cats are evaluated in 8-way connected components. A component is trapped
        only when no cat in that component has any 8-neighbor escape cell.
        """
        dirs8 = (
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1),
        )
        cat_set = set(self.cats)
        if not cat_set:
            return set()

        trapped: set[tuple[int, int]] = set()
        seen: set[tuple[int, int]] = set()

        for start in cat_set:
            if start in seen:
                continue

            # Collect one 8-connected cat component.
            comp: set[tuple[int, int]] = {start}
            stack = [start]
            seen.add(start)
            while stack:
                cx, cy = stack.pop()
                for dx, dy in dirs8:
                    nx, ny = cx + dx, cy + dy
                    nb = (nx, ny)
                    if nb in cat_set and nb not in seen:
                        seen.add(nb)
                        comp.add(nb)
                        stack.append(nb)

            # A component is not trapped if any cat has at least one open
            # neighboring cell that is not blocked by terrain, cheese, mouse, or cats.
            has_escape = False
            for cx, cy in comp:
                for dx, dy in dirs8:
                    nx, ny = cx + dx, cy + dy
                    if not self.in_bounds(nx, ny):
                        continue
                    nb = (nx, ny)
                    if nb in cat_set:
                        continue
                    if nb == self.mouse_pos:
                        continue
                    if self.board[ny][nx] in (BLOCK, WALL, CHEESE):
                        continue
                    has_escape = True
                    break
                if has_escape:
                    break

            if not has_escape:
                trapped.update(comp)

        return trapped

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

        # No cat group may start already trapped
        if self._trapped_cat_set():
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
        tier_wall_segs  = (2, 3, 3, 4, 4, 5, 5, 6, 6, 7)
        tier_block_cnt  = (64, 68, 72, 78, 84, 90, 96, 102, 108, 114)
        tier_cheese_cnt = ( 1,  1,  1,  1,  1,  1,  2,  2,  2,  2)
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

            # Mouse: classic feel - start near board center.
            mouse = self._find_centerish_free_cell(free_cells=free)
            self.mouse_pos = mouse

            # Cats: prefer the outer ring so they close in from the edges.
            outer_cats = self._find_outer_cat_spawns(cat_cnt, mouse, free_cells=free)
            if len(outer_cats) < cat_cnt:
                continue
            self.cats = outer_cats

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

    def _find_centerish_free_cell(
        self,
        preferred: tuple[int, int] | None = None,
        free_cells: list[tuple[int, int]] | None = None,
    ) -> tuple[int, int]:
        """Pick a free cell nearest the board center for a classic mouse spawn."""
        cells = free_cells if free_cells is not None else [
            (x, y)
            for y in range(1, self.height - 1)
            for x in range(1, self.width - 1)
            if self.board[y][x] == EMPTY
        ]
        if not cells:
            return self._find_free_cell()

        cx = (self.width - 1) / 2
        cy = (self.height - 1) / 2
        preferred_weight = 0 if preferred in cells else 1
        return min(
            cells,
            key=lambda cell: (
                0 if preferred is not None and cell == preferred else preferred_weight,
                abs(cell[0] - cx) + abs(cell[1] - cy),
                abs(cell[0] - cx),
                abs(cell[1] - cy),
            ),
        )

    def _find_outer_cat_spawns(
        self,
        count: int,
        mouse_pos: tuple[int, int],
        preferred: list[tuple[int, int]] | None = None,
        free_cells: list[tuple[int, int]] | None = None,
    ) -> list[tuple[int, int]]:
        """Pick cat spawns near the outer ring, spread apart and away from the mouse."""
        cells = free_cells if free_cells is not None else [
            (x, y)
            for y in range(1, self.height - 1)
            for x in range(1, self.width - 1)
            if self.board[y][x] == EMPTY
        ]
        candidates = [cell for cell in cells if cell != mouse_pos]
        if not candidates:
            return []

        def edge_distance(cell: tuple[int, int]) -> int:
            x, y = cell
            return min(x - 1, y - 1, self.width - 2 - x, self.height - 2 - y)

        def mouse_distance(cell: tuple[int, int]) -> int:
            return abs(cell[0] - mouse_pos[0]) + abs(cell[1] - mouse_pos[1])

        preferred_set = set(preferred or [])
        ordered = sorted(
            candidates,
            key=lambda cell: (
                0 if cell in preferred_set and edge_distance(cell) <= 2 else 1,
                edge_distance(cell),
                -mouse_distance(cell),
            ),
        )

        chosen: list[tuple[int, int]] = []
        min_spacing = 4
        for cell in ordered:
            if mouse_distance(cell) < 7:
                continue
            if any(abs(cell[0] - ox) + abs(cell[1] - oy) < min_spacing for ox, oy in chosen):
                continue
            chosen.append(cell)
            if len(chosen) == count:
                return chosen

        for cell in ordered:
            if cell not in chosen and mouse_distance(cell) >= 6:
                chosen.append(cell)
                if len(chosen) == count:
                    return chosen

        return chosen[:count]

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
        "block_face": (90, 201, 110),
        "block_edge": (38, 126, 54),
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
        "block_face": (90, 201, 110),
        "block_edge": (38, 126, 54),
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
        "block_face": (90, 201, 110),
        "block_edge": (38, 126, 54),
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
        "block_face": (90, 201, 110),
        "block_edge": (38, 126, 54),
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
        "block_face": (90, 201, 110),
        "block_edge": (38, 126, 54),
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
        "block_face": (90, 201, 110),
        "block_edge": (38, 126, 54),
        "grid_col": (138, 116, 92),
    },
]


def get_room_theme(level: int) -> dict:
    """Return the room theme dict for the given level (cycles every 10 levels)."""
    idx = (level - 1) // 10 % len(ROOM_THEMES)
    theme = ROOM_THEMES[idx].copy()
    theme.update({
        "floor_style": "classic",
        "floor_a": (136, 128, 18),
        "floor_b": (122, 116, 16),
        "floor_grout": (106, 100, 14),
        "wall_face": (150, 232, 238),
        "wall_dark": (74, 172, 178),
        "block_face": (90, 201, 110),
        "block_edge": (38, 126, 54),
        "grid_col": (112, 106, 16),
    })
    return theme


def _draw_floor_tile(
    surface: pygame.Surface,
    rect: pygame.Rect,
    gx: int,
    gy: int,
    theme: dict,
) -> None:
    """Draw a single floor tile with the room's pattern."""
    style = theme["floor_style"]
    if style == "classic":
        col = theme["floor_a"] if (gx + gy * 2) % 5 < 3 else theme["floor_b"]
        pygame.draw.rect(surface, col, rect)
        if (gx * 3 + gy) % 7 == 0:
            speck = pygame.Rect(rect.x + rect.w // 3, rect.y + rect.h // 3, max(1, rect.w // 8), max(1, rect.h // 8))
            pygame.draw.rect(surface, theme["floor_grout"], speck)
        pygame.draw.rect(surface, theme["grid_col"], rect, 1)
    elif style == "checker":
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


def _mix_color(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
    ratio: float,
) -> tuple[int, int, int]:
    ratio = max(0.0, min(1.0, ratio))
    return (
        int(a[0] + (b[0] - a[0]) * ratio),
        int(a[1] + (b[1] - a[1]) * ratio),
        int(a[2] + (b[2] - a[2]) * ratio),
    )


def _draw_room_backdrop(
    surface: pygame.Surface,
    board_rect: pygame.Rect,
    theme: dict,
) -> None:
    """Paint subtle room-specific furniture silhouettes behind gameplay tiles."""
    overlay = pygame.Surface(board_rect.size, pygame.SRCALPHA)
    accent = _mix_color(theme["wall_face"], theme["floor_b"], 0.45)
    accent_hi = _mix_color(theme["wall_face"], (255, 255, 255), 0.12)
    outline = _mix_color(theme["wall_dark"], theme["floor_b"], 0.35)
    rug = _mix_color(theme["floor_a"], theme["wall_face"], 0.35)
    name = theme["name"]
    width, height = board_rect.size

    pygame.draw.rect(overlay, (*_mix_color(theme["wall_face"], theme["floor_a"], 0.25), 56), (0, 0, width, 56))
    pygame.draw.rect(overlay, (*_mix_color(theme["wall_dark"], theme["floor_b"], 0.15), 72), (0, 42, width, 14))

    if name == "Kitchen":
        pygame.draw.rect(overlay, (*accent, 64), (36, 18, width - 72, 34), border_radius=6)
        for x in range(64, width - 52, 112):
            pygame.draw.rect(overlay, (*outline, 78), (x, 22, 72, 26), 2, border_radius=5)
        pygame.draw.rect(overlay, (*outline, 84), (width - 180, 10, 92, 42), border_radius=8)
        pygame.draw.circle(overlay, (*accent_hi, 78), (width - 134, 31), 11, 2)
        pygame.draw.rect(overlay, (*accent, 58), (68, height - 158, 180, 82), border_radius=18)
        pygame.draw.ellipse(overlay, (*rug, 52), (88, height - 132, 138, 36))
    elif name == "Dining Room":
        pygame.draw.ellipse(overlay, (*rug, 68), (width // 2 - 184, height // 2 - 108, 368, 216))
        pygame.draw.rect(overlay, (*accent, 78), (width // 2 - 126, height // 2 - 42, 252, 84), border_radius=22)
        for x, y in ((width // 2 - 156, height // 2 - 86), (width // 2 + 116, height // 2 - 86), (width // 2 - 156, height // 2 + 42), (width // 2 + 116, height // 2 + 42)):
            pygame.draw.rect(overlay, (*outline, 80), (x, y, 40, 92), border_radius=10)
    elif name == "Living Room":
        pygame.draw.ellipse(overlay, (*rug, 64), (116, height // 2 - 92, width - 232, 200))
        pygame.draw.rect(overlay, (*accent, 76), (84, 92, 226, 88), border_radius=18)
        pygame.draw.rect(overlay, (*outline, 78), (72, 122, 250, 54), border_radius=18)
        pygame.draw.rect(overlay, (*accent_hi, 70), (width - 208, 86, 124, 78), border_radius=10)
        pygame.draw.rect(overlay, (*outline, 82), (width - 198, 96, 104, 58), 3, border_radius=10)
        pygame.draw.ellipse(overlay, (*accent, 60), (width // 2 - 86, height // 2 - 34, 172, 68))
    elif name == "Bedroom":
        pygame.draw.ellipse(overlay, (*rug, 58), (130, height // 2 - 104, width - 260, 208))
        pygame.draw.rect(overlay, (*accent, 70), (82, 86, 284, 138), border_radius=20)
        pygame.draw.rect(overlay, (*accent_hi, 72), (88, 96, 272, 46), border_radius=16)
        pygame.draw.rect(overlay, (*outline, 80), (382, 104, 92, 70), border_radius=10)
        pygame.draw.rect(overlay, (*outline, 72), (width - 170, 100, 82, 142), border_radius=12)
    elif name == "Bathroom":
        pygame.draw.rect(overlay, (*accent_hi, 74), (72, 92, 276, 128), border_radius=26)
        pygame.draw.rect(overlay, (*outline, 76), (86, 108, 248, 94), 3, border_radius=22)
        pygame.draw.rect(overlay, (*accent, 66), (width - 204, 98, 114, 72), border_radius=12)
        pygame.draw.circle(overlay, (*outline, 76), (width - 146, 136), 16, 3)
        pygame.draw.ellipse(overlay, (*rug, 60), (width // 2 - 88, height - 180, 176, 72))
    elif name == "Attic":
        for offset in range(-60, width + 60, 120):
            pygame.draw.polygon(overlay, (*outline, 72), ((offset, 0), (offset + 60, 0), (offset + 18, 126), (offset - 18, 126)))
        pygame.draw.rect(overlay, (*accent, 62), (84, height - 176, 214, 104), border_radius=14)
        pygame.draw.rect(overlay, (*outline, 78), (104, height - 196, 174, 42), border_radius=8)
        pygame.draw.ellipse(overlay, (*rug, 50), (width - 270, height - 192, 184, 96))

    surface.blit(overlay, board_rect.topleft)


def _draw_wall_tile(
    surface: pygame.Surface,
    rect: pygame.Rect,
    face: tuple[int, int, int] = (72, 62, 52),
    dark: tuple[int, int, int] = (42, 35, 28),
) -> None:
    ts = rect.width
    light = (min(255, face[0] + 26), min(255, face[1] + 18), min(255, face[2] + 14))
    inner = (184, 244, 246)
    outer = rect.inflate(-2, -2)
    pygame.draw.rect(surface, face, outer)
    pygame.draw.line(surface, light, outer.topleft, (outer.right - 1, outer.top), 2)
    pygame.draw.line(surface, light, outer.topleft, (outer.left, outer.bottom - 1), 2)
    pygame.draw.line(surface, dark, (outer.left, outer.bottom - 1), (outer.right - 1, outer.bottom - 1), 2)
    pygame.draw.line(surface, dark, (outer.right - 1, outer.top), (outer.right - 1, outer.bottom - 1), 2)
    inset = max(4, ts // 5)
    gem = pygame.Rect(outer.x + inset, outer.y + inset, outer.width - inset * 2, outer.height - inset * 2)
    if gem.width > 4 and gem.height > 4:
        pygame.draw.rect(surface, inner, gem)
        pygame.draw.rect(surface, dark, gem, 1)
        swirl_y = gem.centery
        pygame.draw.line(surface, dark, (gem.x + 2, swirl_y), (gem.right - 3, swirl_y), 1)
        pygame.draw.line(surface, dark, (gem.centerx, gem.y + 2), (gem.centerx, gem.bottom - 3), 1)


def _draw_block_tile(
    surface: pygame.Surface,
    rect: pygame.Rect,
    face: tuple[int, int, int] = (90, 201, 110),
    edge: tuple[int, int, int] = (38, 126, 54),
) -> None:
    """Draw a classic green block tile closer to the original game's look."""
    ts = rect.width
    x, y = rect.x, rect.y

    base = face
    dark = (max(0, face[0] - 34), max(0, face[1] - 58), max(0, face[2] - 32))
    light = (min(255, face[0] + 34), min(255, face[1] + 26), min(255, face[2] + 24))
    crease = (max(0, face[0] - 12), max(0, face[1] - 24), max(0, face[2] - 12))
    gem = (166, 238, 176)

    pad = 2

    # --- Main body ---
    body = pygame.Rect(x + pad, y + pad, ts - pad * 2, ts - pad * 2)
    pygame.draw.rect(surface, base, body)

    # --- Right and bottom shadow strips ---
    shadow_w = max(3, ts // 7)
    shadow = pygame.Rect(body.right - shadow_w, body.y, shadow_w, body.height)
    pygame.draw.rect(surface, dark, shadow)
    bottom_shadow = pygame.Rect(body.x, body.bottom - shadow_w, body.width, shadow_w)
    pygame.draw.rect(surface, dark, bottom_shadow)

    # --- Classic bevel highlight on top and left ---
    pygame.draw.line(surface, light, (body.x + 1, body.y + 1), (body.right - shadow_w - 2, body.y + 1), 2)
    pygame.draw.line(surface, light, (body.x + 1, body.y + 1), (body.x + 1, body.bottom - shadow_w - 2), 2)

    # --- Interior panel seams to echo the original green block look ---
    inset = max(4, ts // 5)
    inner = pygame.Rect(body.x + inset, body.y + inset, body.width - inset * 2 - 1, body.height - inset * 2 - 1)
    if inner.width > 4 and inner.height > 4:
        pygame.draw.rect(surface, gem, inner)
        pygame.draw.rect(surface, crease, inner, 1)
        pygame.draw.line(surface, edge, inner.topleft, inner.bottomright, 1)
        pygame.draw.line(surface, edge, (inner.right, inner.y), (inner.x, inner.bottom), 1)

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
        # Fill the mobile viewport in landscape and reduce browser gesture interference.
        try:
            canvas = platform.window.canvas
            canvas.style.width = "100vw"
            canvas.style.height = "100vh"
            canvas.style.maxWidth = "100vw"
            canvas.style.maxHeight = "100vh"
            canvas.style.objectFit = "contain"
            canvas.style.display = "block"
            canvas.style.touchAction = "none"
            platform.window.document.body.style.margin = "0"
            platform.window.document.body.style.overflow = "hidden"
            platform.window.document.body.style.background = "#000"
        except Exception:
            pass
    pygame.display.set_icon(_make_icon())
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 24, bold=True)
    small_font = pygame.font.SysFont("arial", 20)
    tiny_font = pygame.font.SysFont("arial", 14)
    sprites = _load_sprite_pack(TILE_SIZE)
    title_font = pygame.font.SysFont("arial", 36, bold=True)
    big_title_font = pygame.font.SysFont("arial", 56, bold=True)
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
        "bg": (128, 128, 128),
        "grid": (96, 96, 96),
        "wall": (150, 232, 238),
        "block": (90, 201, 110),
        "mouse": (188, 188, 182),
        "cat": (244, 194, 58),
        "cheese": (254, 220, 90),
        "hud": (192, 192, 192),
        "text": (10, 10, 10),
        "alert": (170, 30, 30),
        "levelup": (40, 120, 60),
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
    sound_enabled = True

    # --- Virtual joystick touch state ---
    # Center the joystick horizontally in the left control lane so the large ring
    # stays clear of both the screen edge and the map border.
    _vjoy_default_cx = CONTROL_LANE_W // 2   # centered in left lane
    _vjoy_default_cy = int(SCREEN_HEIGHT * VJOY_ANCHOR_Y_PCT)
    _vjoy_default_cy = max(HUD_HEIGHT + VJOY_RADIUS + 14, min(_vjoy_default_cy, SCREEN_HEIGHT - VJOY_RADIUS - 52))
    vjoy_cx = _vjoy_default_cx
    vjoy_cy = _vjoy_default_cy
    vjoy_active = False
    vjoy_finger_id: int | None = None
    vjoy_offset = (0.0, 0.0)   # thumb displacement from center
    vjoy_last_dir = (0, 0)
    vjoy_hold_ms = 0
    vjoy_active_dir = (0, 0)
    vjoy_crossed_neutral = True  # require neutral before allowing opposite direction
    key_last_dir = (0, 0)
    key_held_frames = 0
    key_left_held = False
    key_right_held = False
    key_up_held = False
    key_down_held = False

    # Touch buttons (Pause, Help, Sound) rendered in HUD — rects set in draw_board
    _tbtn_pause_rect = pygame.Rect(0, 0, TBTN_W, TBTN_H)
    _tbtn_help_rect  = pygame.Rect(0, 0, TBTN_W, TBTN_H)
    _tbtn_sound_rect = pygame.Rect(0, 0, TBTN_W, TBTN_H)
    # Overlay action buttons (Menu / Restart on game-over, Resume on pause)
    _tbtn_menu_rect    = pygame.Rect(0, 0, 160, 64)
    _tbtn_restart_rect = pygame.Rect(0, 0, 160, 64)
    _tbtn_resume_rect  = pygame.Rect(0, 0, 200, 64)

    def _touch_to_screen(nx: float, ny: float) -> tuple[int, int]:
        """Map normalized touch coords to logical screen coords, compensating for mobile letterboxing."""
        if sys.platform != "emscripten":
            return int(nx * SCREEN_WIDTH), int(ny * SCREEN_HEIGHT)
        try:
            import platform  # type: ignore[import]

            vw = float(platform.window.innerWidth)
            vh = float(platform.window.innerHeight)
            if vw <= 1 or vh <= 1:
                return int(nx * SCREEN_WIDTH), int(ny * SCREEN_HEIGHT)

            px = nx * vw
            py = ny * vh
            game_aspect = SCREEN_WIDTH / SCREEN_HEIGHT
            view_aspect = vw / vh

            if view_aspect > game_aspect:
                content_h = vh
                content_w = vh * game_aspect
                pad_x = (vw - content_w) * 0.5
                sx = int((px - pad_x) * (SCREEN_WIDTH / content_w))
                sy = int(py * (SCREEN_HEIGHT / content_h))
            else:
                content_w = vw
                content_h = vw / game_aspect
                pad_y = (vh - content_h) * 0.5
                sx = int(px * (SCREEN_WIDTH / content_w))
                sy = int((py - pad_y) * (SCREEN_HEIGHT / content_h))

            return max(0, min(SCREEN_WIDTH - 1, sx)), max(0, min(SCREEN_HEIGHT - 1, sy))
        except Exception:
            return int(nx * SCREEN_WIDTH), int(ny * SCREEN_HEIGHT)

    def _clamp_vjoy_offset(offset: tuple[float, float]) -> tuple[float, float]:
        """Clamp joystick thumb travel to the visible ring radius."""
        ox, oy = offset
        dist = math.hypot(ox, oy)
        max_dist = VJOY_RADIUS - VJOY_THUMB_R - 4
        if dist > max_dist and dist > 0:
            scale = max_dist / dist
            return ox * scale, oy * scale
        return ox, oy

    def _vjoy_dir(offset: tuple[float, float], previous_dir: tuple[int, int] = (0, 0)) -> tuple[int, int]:
        """Map joystick displacement to a stable 4-way grid direction."""
        ox, oy = _clamp_vjoy_offset(offset)
        abs_x = abs(ox)
        abs_y = abs(oy)
        max_dist = VJOY_RADIUS - VJOY_THUMB_R - 4
        if max_dist <= 0:
            return (0, 0)

        dist = math.hypot(ox, oy)
        engage_dist = max(VJOY_DEADZONE, max_dist * VJOY_ENGAGE_PCT)
        release_dist = max(VJOY_DEADZONE * 0.8, max_dist * VJOY_RELEASE_PCT)

        if previous_dir == (0, 0) and dist < engage_dist:
            return (0, 0)
        if previous_dir != (0, 0) and dist < release_dist:
            return (0, 0)

        if abs_x > abs_y * VJOY_AXIS_LOCK_RATIO:
            return (1 if ox > 0 else -1, 0)
        if abs_y > abs_x * VJOY_AXIS_LOCK_RATIO:
            return (0, 1 if oy > 0 else -1)

        # When the thumb sits near a diagonal boundary, prefer the previous axis
        # to avoid left/right or up/down jitter while the player is holding.
        if previous_dir[0] != 0 and abs_x >= VJOY_DEADZONE * 0.85:
            return (1 if ox > 0 else -1, 0)
        if previous_dir[1] != 0 and abs_y >= VJOY_DEADZONE * 0.85:
            return (0, 1 if oy > 0 else -1)

        if abs_x >= abs_y:
            return (1 if ox > 0 else -1, 0)
        return (0, 1 if oy > 0 else -1)

    def _is_opposite_dir(a: tuple[int, int], b: tuple[int, int]) -> bool:
        """True when directions are exact opposites on the same axis."""
        return (a[0] != 0 and a[0] == -b[0]) or (a[1] != 0 and a[1] == -b[1])

    def _apply_vjoy_move(d: tuple[int, int]) -> bool:
        """Issue one grid step from joystick input; return True if player moved."""
        nonlocal mouse_facing, player_moved
        if state.game_over or state.paused or show_help or countdown_ms > 0:
            return False
        moved = state.handle_player_move(d[0], d[1])
        if moved and d[0] != 0:
            mouse_facing = d[0]
        return moved

    def _draw_classic_bevel(
        surf: pygame.Surface,
        rect: pygame.Rect,
        face: tuple[int, int, int],
        light: tuple[int, int, int],
        dark: tuple[int, int, int],
        pressed: bool = False,
    ) -> None:
        pygame.draw.rect(surf, face, rect)
        tl = dark if pressed else light
        br = light if pressed else dark
        pygame.draw.line(surf, tl, rect.topleft, (rect.right - 1, rect.top), 2)
        pygame.draw.line(surf, tl, rect.topleft, (rect.left, rect.bottom - 1), 2)
        pygame.draw.line(surf, br, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1), 2)
        pygame.draw.line(surf, br, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1), 2)

    def _draw_classic_mouse_icon(
        surf: pygame.Surface,
        center: tuple[int, int],
        facing: int = 1,
        scale: int = TILE_SIZE,
    ) -> None:
        """Draw a compact side-view mouse with an irregular silhouette instead of a boxy body."""
        cx, cy = center
        logical = pygame.Surface((26, 18), pygame.SRCALPHA)

        body = (198, 194, 188)
        light = (231, 226, 218)
        shadow = (132, 126, 120)
        outline = (90, 86, 82)
        ear = (205, 188, 191)
        inner_ear = (245, 170, 182)
        tail = (161, 138, 145)
        nose = (248, 150, 166)
        whisker = (181, 172, 164)
        eye = (20, 20, 22)

        pygame.draw.line(logical, tail, False, [(2, 10), (1, 8), (3, 7), (6, 8)], 1)
        pygame.draw.ellipse(logical, shadow, (6, 8, 10, 6))
        pygame.draw.ellipse(logical, body, (7, 7, 10, 5))
        pygame.draw.ellipse(logical, light, (9, 7, 6, 3))
        pygame.draw.circle(logical, body, (18, 7), 3)
        pygame.draw.circle(logical, ear, (16, 4), 2)
        pygame.draw.circle(logical, ear, (18, 3), 2)
        logical.set_at((16, 4), inner_ear)
        logical.set_at((18, 3), inner_ear)
        pygame.draw.line(logical, outline, (7, 12), (8, 14), 1)
        pygame.draw.line(logical, outline, (12, 12), (13, 14), 1)
        pygame.draw.line(logical, outline, (8, 6), (15, 6), 1)
        pygame.draw.line(logical, outline, (7, 8), (7, 11), 1)
        pygame.draw.line(logical, outline, (18, 4), (18, 10), 1)
        logical.set_at((19, 7), eye)
        logical.set_at((21, 8), nose)
        pygame.draw.line(logical, whisker, (20, 8), (24, 7), 1)
        pygame.draw.line(logical, whisker, (20, 9), (24, 9), 1)

        if facing < 0:
            logical = pygame.transform.flip(logical, True, False)

        target_w = max(12, int(scale * 0.82))
        target_h = max(8, int(target_w * logical.get_height() / logical.get_width()))
        sprite = pygame.transform.scale(logical, (target_w, target_h))
        surf.blit(sprite, (cx - sprite.get_width() // 2, cy - sprite.get_height() // 2))

    def _draw_classic_cat_icon(
        surf: pygame.Surface,
        center: tuple[int, int],
        facing: int = 1,
        scale: int = TILE_SIZE,
    ) -> None:
        """Draw a compact side-view cat with a tapered silhouette and pronounced head shape."""
        cx, cy = center
        logical = pygame.Surface((26, 18), pygame.SRCALPHA)

        fur = (241, 186, 58)
        light = (255, 224, 132)
        shadow = (154, 95, 20)
        outline = (107, 64, 10)
        inner_ear = (255, 169, 161)
        iris = (84, 176, 68)
        nose = (255, 171, 157)
        whisker = (240, 233, 211)

        pygame.draw.line(logical, shadow, False, [(2, 9), (1, 7), (3, 6), (6, 7)], 2)
        pygame.draw.ellipse(logical, shadow, (6, 8, 10, 6))
        pygame.draw.ellipse(logical, fur, (7, 7, 10, 5))
        pygame.draw.ellipse(logical, light, (9, 7, 6, 3))
        pygame.draw.circle(logical, fur, (18, 7), 4)
        pygame.draw.polygon(logical, fur, [(16, 4), (17, 1), (19, 4)])
        pygame.draw.polygon(logical, fur, [(19, 4), (21, 1), (22, 4)])
        pygame.draw.polygon(logical, inner_ear, [(17, 3), (18, 2), (18, 4)])
        pygame.draw.polygon(logical, inner_ear, [(20, 3), (21, 2), (21, 4)])
        pygame.draw.line(logical, outline, (7, 13), (7, 16), 1)
        pygame.draw.line(logical, outline, (12, 13), (12, 16), 1)
        pygame.draw.line(logical, outline, (16, 13), (16, 16), 1)
        pygame.draw.line(logical, shadow, (9, 8), (9, 11), 1)
        pygame.draw.line(logical, shadow, (12, 8), (12, 11), 1)
        pygame.draw.line(logical, shadow, (14, 8), (14, 11), 1)
        pygame.draw.line(logical, outline, (6, 7), (17, 7), 1)
        pygame.draw.line(logical, outline, (6, 9), (6, 12), 1)
        logical.set_at((19, 7), iris)
        logical.set_at((20, 7), outline)
        logical.set_at((22, 8), nose)
        pygame.draw.line(logical, whisker, (21, 8), (24, 7), 1)
        pygame.draw.line(logical, whisker, (21, 9), (24, 9), 1)

        if facing < 0:
            logical = pygame.transform.flip(logical, True, False)

        target_w = max(12, int(scale * 0.86))
        target_h = max(8, int(target_w * logical.get_height() / logical.get_width()))
        sprite = pygame.transform.scale(logical, (target_w, target_h))
        surf.blit(sprite, (cx - sprite.get_width() // 2, cy - sprite.get_height() // 2))

    def _draw_touch_btn(
        surf: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        color: tuple[int, int, int] = (70, 65, 50),
        text_color: tuple[int, int, int] = (220, 210, 170),
        active: bool = False,
    ) -> None:
        """Draw a classic beveled button closer to Win3-era UI chrome."""
        bg_col = tuple(min(255, c + 18) for c in color) if active else color  # type: ignore[assignment]
        _draw_classic_bevel(surf, rect, bg_col, (255, 255, 255), (72, 72, 72), pressed=active)
        lbl = small_font.render(label, True, text_color)
        x_off = 1 if active else 0
        y_off = 1 if active else 0
        surf.blit(lbl, (rect.centerx - lbl.get_width() // 2 + x_off, rect.centery - lbl.get_height() // 2 + y_off))

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
        # Windows-style chrome around the playfield.
        screen.fill((128, 128, 128))
        lane_rect = pygame.Rect(0, HUD_HEIGHT, BOARD_ORIGIN_X, SCREEN_HEIGHT - HUD_HEIGHT)
        _draw_classic_bevel(screen, lane_rect, (192, 192, 192), (255, 255, 255), (72, 72, 72))
        # Right action lane
        rlane_rect = pygame.Rect(BOARD_RIGHT_X, HUD_HEIGHT, ACTION_LANE_W, SCREEN_HEIGHT - HUD_HEIGHT)
        _draw_classic_bevel(screen, rlane_rect, (192, 192, 192), (255, 255, 255), (72, 72, 72))

        board_bg = pygame.Rect(BOARD_ORIGIN_X, HUD_HEIGHT, BOARD_PIXEL_W, GRID_HEIGHT * TILE_SIZE)
        pygame.draw.rect(screen, _theme["floor_a"], board_bg)
        for y in range(state.height):
            for x in range(state.width):
                rect = pygame.Rect(BOARD_ORIGIN_X + x * TILE_SIZE, y * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE)
                _draw_floor_tile(screen, rect, x, y, _theme)

        for y in range(state.height):
            for x in range(state.width):
                rect = pygame.Rect(BOARD_ORIGIN_X + x * TILE_SIZE, y * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE)
                tile = state.board[y][x]
                if tile == WALL:
                    _draw_wall_tile(screen, rect, _theme["wall_face"], _theme["wall_dark"])
                elif tile == BLOCK and (x, y) not in _tween_dests:
                    _draw_block_tile(screen, rect, _theme["block_face"], _theme["block_edge"])
                elif tile == CHEESE:
                    _draw_cheese_tile(screen, rect)

        for cx, cy in state.cats:
            rect = pygame.Rect(BOARD_ORIGIN_X + cx * TILE_SIZE, cy * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE)
            if (cx, cy) in cat_alert:
                glow_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                alpha = min(180, 80 + cat_alert[(cx, cy)] * 5)
                pygame.draw.ellipse(glow_surf, (255, 140, 0, alpha), glow_surf.get_rect().inflate(-4, -4))
                screen.blit(glow_surf, rect.topleft)
            cat_fx = 1 if cx <= mx else -1
            _draw_classic_cat_icon(screen, (rect.centerx, rect.centery + int(math.sin(animation_frame / 9.0))), cat_fx, TILE_SIZE)

        mx, my = state.mouse_pos
        mouse_rect = pygame.Rect(BOARD_ORIGIN_X + mx * TILE_SIZE, my * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE)
        bob = int(math.sin(animation_frame / 7.0) * 2)
        fx = 1 if mouse_facing >= 0 else -1
        _draw_classic_mouse_icon(screen, (mouse_rect.centerx, mouse_rect.centery + bob), fx, TILE_SIZE)

        for tw in block_tweens:
            t = tw["t"]
            px = int(BOARD_ORIGIN_X + tw["gx0"] * TILE_SIZE + (tw["gx1"] - tw["gx0"]) * TILE_SIZE * t)
            py = int(tw["gy0"] * TILE_SIZE + HUD_HEIGHT + (tw["gy1"] - tw["gy0"]) * TILE_SIZE * t)
            _draw_block_tile(screen, pygame.Rect(px, py, TILE_SIZE, TILE_SIZE), _theme["block_face"], _theme["block_edge"])

        hud_rect = pygame.Rect(0, 0, SCREEN_WIDTH, HUD_HEIGHT)
        _draw_classic_bevel(screen, hud_rect, colors["hud"], (255, 255, 255), (96, 96, 96))
        hud_text = font.render(
            f"Score {state.score:05d}   Level {state.level}   Cats {len(state.cats)}",
            True,
            colors["text"],
        )
        screen.blit(hud_text, (18, 10))
        room_r = pygame.Rect(14, HUD_HEIGHT - 26, 156, 18)
        _draw_classic_bevel(screen, room_r, (176, 176, 176), (255, 255, 255), (96, 96, 96))
        room_surf = tiny_font.render(_theme["name"], True, (10, 10, 10))
        screen.blit(room_surf, (room_r.centerx - room_surf.get_width() // 2, room_r.centery - room_surf.get_height() // 2))
        # Action buttons — stacked near the bottom of the right lane for right-thumb reach
        _abtn_w = ACTION_LANE_W - 20
        _abtn_h = 52
        _abtn_x = BOARD_RIGHT_X + 10
        _abtn_gap = 14
        _snd_y   = SCREEN_HEIGHT - _abtn_h - _abtn_gap
        _help_y  = _snd_y - _abtn_h - _abtn_gap
        _pause_y = _help_y - _abtn_h - _abtn_gap
        _tbtn_pause_rect.update(_abtn_x, _pause_y, _abtn_w, _abtn_h)
        _tbtn_help_rect.update( _abtn_x, _help_y,  _abtn_w, _abtn_h)
        _tbtn_sound_rect.update(_abtn_x, _snd_y,   _abtn_w, _abtn_h)
        _draw_touch_btn(screen, _tbtn_pause_rect, "PAUSE", active=state.paused)
        _draw_touch_btn(screen, _tbtn_help_rect,  "HELP",  active=show_help)
        _snd_lbl = "SND ON" if sound_enabled else "SND OFF"
        _snd_col = (50, 70, 50) if sound_enabled else (80, 40, 40)
        _draw_touch_btn(screen, _tbtn_sound_rect, _snd_lbl, color=_snd_col, active=False)

        # Lives display — classic mouse icons centered in the right lane, above the action buttons
        _life_cx = BOARD_RIGHT_X + ACTION_LANE_W // 2
        _life_row_y = _pause_y - 36
        for i in range(state.lives):
            _draw_classic_mouse_icon(screen, (int(_life_cx + (i - (state.lives - 1) / 2) * 26), _life_row_y), 1, 16)
        _lives_lbl = tiny_font.render("LIVES", True, (20, 20, 20))
        screen.blit(_lives_lbl, (_life_cx - _lives_lbl.get_width() // 2, _life_row_y + 12))

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
            _lc_ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            _lc_ov.fill((0, 0, 0, 160))
            screen.blit(_lc_ov, (0, 0))
            _lcx = SCREEN_WIDTH // 2
            _lcy = SCREEN_HEIGHT // 2
            next_level = state.level + 1
            # Big level number with shadow + glow
            _lc_num = big_title_font.render(f"LEVEL  {next_level}", True, (255, 230, 80))
            _lc_shd = big_title_font.render(f"LEVEL  {next_level}", True, (0, 0, 0))
            for _dxy in ((-2, 2), (2, 2), (0, 4)):
                _tmp = big_title_font.render(f"LEVEL  {next_level}", True, (0, 0, 0))
                _tmp.set_alpha(100)
                screen.blit(_tmp, (_lcx - _lc_num.get_width() // 2 + _dxy[0], _lcy - 44 + _dxy[1]))
            screen.blit(_lc_num, (_lcx - _lc_num.get_width() // 2, _lcy - 44))
            # Status card: polished loading message
            _card = pygame.Rect(0, 0, 420, 64)
            _card.center = (_lcx, _lcy + 52)
            _card_bg = pygame.Surface((_card.width, _card.height), pygame.SRCALPHA)
            pygame.draw.rect(_card_bg, (16, 14, 10, 210), _card_bg.get_rect(), border_radius=12)
            pygame.draw.rect(_card_bg, (120, 108, 68, 200), _card_bg.get_rect(), 1, border_radius=12)
            screen.blit(_card_bg, _card.topleft)

            _loading = font.render("Loading Next Level", True, (220, 206, 156))
            screen.blit(_loading, (_lcx - _loading.get_width() // 2, _card.y + 9))

            # Animated wait indicator (professional status feedback)
            _dots = "." * ((animation_frame // 18) % 4)
            _wait = small_font.render(f"Please wait{_dots}", True, (174, 165, 132))
            screen.blit(_wait, (_lcx - _wait.get_width() // 2, _card.y + 36))

            _diff_name = DIFFICULTIES[diff_idx].upper()
            _diff_badge_cols = {"EASY": (36, 120, 46), "NORMAL": (38, 40, 120), "HARD": (130, 28, 28)}
            _diff_txt_cols  = {"EASY": (130, 240, 148), "NORMAL": (188, 186, 255), "HARD": (255, 138, 128)}
            _db_col = _diff_badge_cols.get(_diff_name, (80, 78, 50))
            _dt_col = _diff_txt_cols.get(_diff_name, (200, 190, 140))
            _db_surf = small_font.render(_diff_name, True, _dt_col)
            _db_rect = pygame.Rect(0, 0, _db_surf.get_width() + 24, _db_surf.get_height() + 10)
            _db_rect.center = (_lcx, _lcy + 102)
            pygame.draw.rect(screen, _db_col, _db_rect, border_radius=8)
            pygame.draw.rect(screen, _dt_col, _db_rect, 1, border_radius=8)
            screen.blit(_db_surf, (_db_rect.centerx - _db_surf.get_width() // 2,
                                   _db_rect.centery - _db_surf.get_height() // 2))

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
        cur_dir = _vjoy_dir(vjoy_offset, vjoy_last_dir) if vjoy_active else (0, 0)
        for d, pts in arrow_pts.items():
            alpha = 230 if d == cur_dir else 110
            pygame.draw.polygon(joy_surf, (255, 255, 255, alpha), pts)

        # Thumb circle — clamped to ring travel area when active
        if vjoy_active:
            ox, oy = _clamp_vjoy_offset(vjoy_offset)
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
        keys_layout = [list("ABCDEFGHI"), list("JKLMNOPQR"), list("STUVWXYZ") + ["<<"]]
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
                is_bksp = ch == "<<"
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
        done_lbl = small_font.render("DONE", True, (200, 240, 200) if entry_initials else (120, 120, 100))
        screen.blit(done_lbl, (done_r.centerx - done_lbl.get_width() // 2,
                                done_r.centery - done_lbl.get_height() // 2))
        new_key_rects.append(("DONE", done_r))
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
        play_rect = pygame.Rect(0, 0, 420, 88)
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
        pygame.draw.rect(screen, play_col, play_rect, border_radius=18)
        # Top inner sheen
        hi_p = pygame.Surface((play_rect.width - 12, play_rect.height // 2 - 4), pygame.SRCALPHA)
        pygame.draw.rect(hi_p, (255, 255, 255, 42), hi_p.get_rect(), border_radius=12)
        screen.blit(hi_p, (play_rect.x + 6, play_rect.y + 5))
        # Border
        border_g = int(130 + 90 * pulse_v)
        pygame.draw.rect(screen, (border_g // 2, border_g, border_g // 2 + 10), play_rect, 3, border_radius=18)
        # Label using title_font for large readable text
        play_lbl = title_font.render("  START  ", True, (215, 255, 220))
        screen.blit(play_lbl, (play_rect.centerx - play_lbl.get_width() // 2,
                                play_rect.centery - play_lbl.get_height() // 2))

        # "Tap anywhere" hint
        hint = tiny_font.render("Tap START to begin  •  choose difficulty first if needed", True, (96, 92, 68))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 66))

        legal1 = tiny_font.render("Inspired by classic Windows-era cat-and-mouse puzzle games", True, (78, 74, 56))
        legal2 = tiny_font.render("Unofficial fan remake  -  open source", True, (78, 74, 56))
        screen.blit(legal1, (SCREEN_WIDTH // 2 - legal1.get_width() // 2, SCREEN_HEIGHT - 46))
        screen.blit(legal2, (SCREEN_WIDTH // 2 - legal2.get_width() // 2, SCREEN_HEIGHT - 30))

    def _start_from_title() -> None:
        """Start gameplay using currently selected difficulty."""
        nonlocal state, cat_ms_accum, countdown_ms, score_saved, new_high_score
        nonlocal entering_initials, entry_initials, show_help, phase
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
        entering_initials = False
        entry_initials = ""
        show_help = False
        phase = "playing"

    while running:
        animation_frame += 1
        player_moved = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # ---- keyboard quit (skip ESC-to-quit on web) --------------------
            # ---- touch finger events ----------------------------------------
            elif event.type == pygame.FINGERDOWN:
                sx, sy = _touch_to_screen(event.x, event.y)
                if phase == "title":
                    # Difficulty buttons — three distinct rects in bottom strip
                    btn_w2, btn_h2 = 158, 62
                    x_offsets2 = [-170, 0, 170]
                    touched_difficulty = False
                    for ti, _d in enumerate(DIFFICULTIES):
                        r2 = pygame.Rect(0, 0, btn_w2, btn_h2)
                        r2.center = (SCREEN_WIDTH // 2 + x_offsets2[ti], SCREEN_HEIGHT - 195)
                        if r2.collidepoint(sx, sy):
                            diff_idx = ti
                            touched_difficulty = True
                            break
                    # START button with larger touch target.
                    play_r = pygame.Rect(0, 0, 420, 88)
                    play_r.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 112)
                    play_hit_r = play_r.inflate(260, 140)
                    if play_hit_r.collidepoint(sx, sy) or not touched_difficulty:
                        _start_from_title()
                elif phase == "playing":
                    # HUD touch buttons
                    if _tbtn_pause_rect.collidepoint(sx, sy):
                        if not state.game_over:
                            state.paused = not state.paused
                    elif _tbtn_help_rect.collidepoint(sx, sy):
                        if not state.game_over and not state.paused:
                            show_help = not show_help
                    elif _tbtn_sound_rect.collidepoint(sx, sy):
                        sound_enabled = not sound_enabled
                    # Game-over overlay — initials keyboard first, then MENU/RESTART
                    elif state.game_over:
                        if entering_initials:
                            for key_char, key_rect in initials_key_rects:
                                if key_rect.collidepoint(sx, sy):
                                    if key_char == "<<":
                                        entry_initials = entry_initials[:-1]
                                    elif key_char == "DONE" and entry_initials:
                                        save_score(state.score, state.level, entry_initials)
                                        score_saved = True
                                        entering_initials = False
                                        new_high_score = False
                                        scores = load_scores()
                                    elif len(entry_initials) < 3 and key_char not in ("<<", "DONE"):
                                        entry_initials += key_char
                                    break
                        elif _tbtn_menu_rect.collidepoint(sx, sy):
                            phase = "title"
                            scores = load_scores()
                        elif _tbtn_restart_rect.collidepoint(sx, sy):
                            state.restart_game()
                            block_tweens.clear()
                            score_saved = False
                            new_high_score = False
                            entering_initials = False
                            entry_initials = ""
                            countdown_ms = COUNTDOWN_TOTAL_MS
                            cat_ms_accum = 0
                    # Pause resume button
                    elif state.paused:
                        if _tbtn_resume_rect.collidepoint(sx, sy):
                            state.paused = False
                    # Help close — tap anywhere outside panel closes it
                    elif show_help:
                        show_help = False
                    else:
                        # Virtual joystick — fixed bottom-left by default for a
                        # more standard mobile layout, with optional floating mode.
                        _touch_ok = False
                        if VJOY_FLOAT:
                            _touch_ok = sx < BOARD_ORIGIN_X
                        else:
                            _touch_ok = (
                                sx < BOARD_ORIGIN_X
                                and sy >= HUD_HEIGHT
                                and math.hypot(sx - _vjoy_default_cx, sy - _vjoy_default_cy) <= VJOY_TOUCH_RADIUS
                            )

                        if _touch_ok and not vjoy_active:
                            if VJOY_FLOAT:
                                vjoy_cx = max(VJOY_RADIUS + 10, min(sx, BOARD_ORIGIN_X - VJOY_RADIUS - 10))
                                vjoy_cy = max(VJOY_RADIUS + HUD_HEIGHT + 10, min(sy, SCREEN_HEIGHT - VJOY_RADIUS - 10))
                            else:
                                vjoy_cx = _vjoy_default_cx
                                vjoy_cy = _vjoy_default_cy
                            vjoy_active = True
                            vjoy_finger_id = event.finger_id
                            vjoy_offset = _clamp_vjoy_offset((float(sx - vjoy_cx), float(sy - vjoy_cy)))
                            vjoy_last_dir = (0, 0)
                            vjoy_hold_ms = 0
                            vjoy_active_dir = (0, 0)
                            vjoy_crossed_neutral = True
            elif event.type == pygame.FINGERMOTION:
                if vjoy_active and event.finger_id == vjoy_finger_id:
                    sx, sy = _touch_to_screen(event.x, event.y)
                    vjoy_offset = _clamp_vjoy_offset((float(sx - vjoy_cx), float(sy - vjoy_cy)))
            elif event.type == pygame.FINGERUP:
                if vjoy_active and event.finger_id == vjoy_finger_id:
                    vjoy_active = False
                    vjoy_finger_id = None
                    vjoy_offset = (0.0, 0.0)
                    vjoy_last_dir = (0, 0)
                    vjoy_hold_ms = 0
                    vjoy_active_dir = (0, 0)
                    vjoy_crossed_neutral = True
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
                        entering_initials = False
                        entry_initials = ""
                        new_high_score = False
                        score_saved = False
                        show_help = False
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
                        entering_initials = False
                        entry_initials = ""
                        show_help = False
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
                            entering_initials = False
                            entry_initials = ""
                            countdown_ms = COUNTDOWN_TOTAL_MS
                            cat_ms_accum = 0
                        elif entering_initials:
                            if pygame.K_a <= event.key <= pygame.K_z and len(entry_initials) < 3:
                                entry_initials += chr(event.key - pygame.K_a + ord("A"))
                            elif event.key == pygame.K_BACKSPACE:
                                entry_initials = entry_initials[:-1]
                            elif event.key == pygame.K_RETURN and entry_initials:
                                save_score(state.score, state.level, entry_initials)
                                score_saved = True
                                entering_initials = False
                                new_high_score = False
                                scores = load_scores()
                    elif event.key == pygame.K_p:
                        state.paused = not state.paused
                    elif event.key == pygame.K_h:
                        show_help = not show_help
                    elif event.key == pygame.K_m:
                        sound_enabled = not sound_enabled
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
                    clicked_difficulty = False
                    for ti, _d in enumerate(DIFFICULTIES):
                        r_m = pygame.Rect(0, 0, btn_w_m, btn_h_m)
                        r_m.center = (SCREEN_WIDTH // 2 + x_offsets_m[ti], SCREEN_HEIGHT - 195)
                        if r_m.collidepoint(sx, sy):
                            diff_idx = ti
                            clicked_difficulty = True
                            break
                    # START button with larger click target.
                    play_r_m = pygame.Rect(0, 0, 420, 88)
                    play_r_m.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 112)
                    play_hit_m = play_r_m.inflate(260, 140)
                    if play_hit_m.collidepoint(sx, sy) or not clicked_difficulty:
                        _start_from_title()
                elif phase == "playing":
                    if _tbtn_pause_rect.collidepoint(sx, sy):
                        if not state.game_over:
                            state.paused = not state.paused
                    elif _tbtn_help_rect.collidepoint(sx, sy):
                        if not state.game_over and not state.paused:
                            show_help = not show_help
                    elif _tbtn_sound_rect.collidepoint(sx, sy):
                        sound_enabled = not sound_enabled
                    elif state.paused and _tbtn_resume_rect.collidepoint(sx, sy):
                        state.paused = False
                    elif state.game_over:
                        if entering_initials:
                            for key_char, key_rect in initials_key_rects:
                                if key_rect.collidepoint(sx, sy):
                                    if key_char == "<<":
                                        entry_initials = entry_initials[:-1]
                                    elif key_char == "DONE" and entry_initials:
                                        save_score(state.score, state.level, entry_initials)
                                        score_saved = True
                                        entering_initials = False
                                        new_high_score = False
                                        scores = load_scores()
                                    elif len(entry_initials) < 3 and key_char not in ("<<", "DONE"):
                                        entry_initials += key_char
                                    break
                        elif _tbtn_menu_rect.collidepoint(sx, sy):
                            phase = "title"
                            scores = load_scores()
                        elif _tbtn_restart_rect.collidepoint(sx, sy):
                            state.restart_game()
                            block_tweens.clear()
                            score_saved = False
                            new_high_score = False
                            entering_initials = False
                            entry_initials = ""
                            countdown_ms = COUNTDOWN_TOTAL_MS
                            cat_ms_accum = 0

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

        # ---- virtual joystick auto-repeat (time-based for stable touch feel) --
        if vjoy_active and phase == "playing":
            d = _vjoy_dir(vjoy_offset, vjoy_active_dir)
            if d != (0, 0):
                if d != vjoy_active_dir:
                    if (
                        vjoy_active_dir != (0, 0)
                        and _is_opposite_dir(d, vjoy_active_dir)
                        and not vjoy_crossed_neutral
                    ):
                        # Ignore release jitter that briefly reports the opposite
                        # direction before the stick returns to center.
                        vjoy_hold_ms = 0
                    elif vjoy_active_dir == (0, 0):
                        # Fresh press from idle: respond immediately.
                        vjoy_active_dir = d
                        vjoy_last_dir = d
                        vjoy_hold_ms = 0
                        vjoy_crossed_neutral = False
                        if _apply_vjoy_move(d):
                            player_moved = True
                    else:
                        # Direction changed mid-hold: debounce - wait for stability.
                        vjoy_active_dir = d
                        vjoy_last_dir = d
                        vjoy_hold_ms = 0
                        vjoy_crossed_neutral = False
                else:
                    vjoy_hold_ms += dt_ms
                    threshold = VJOY_INITIAL_REPEAT_MS
                    if vjoy_hold_ms >= threshold:
                        vjoy_hold_ms -= VJOY_REPEAT_MS
                        if _apply_vjoy_move(d):
                            player_moved = True
            else:
                vjoy_active_dir = (0, 0)
                vjoy_last_dir = (0, 0)
                vjoy_hold_ms = 0
                vjoy_crossed_neutral = True

        # Auto-pause when tab/app loses focus on web/mobile, and on desktop focus loss.
        if phase == "playing" and not state.game_over:
            if sys.platform == "emscripten":
                try:
                    import platform  # type: ignore[import]

                    doc_hidden = bool(getattr(platform.window.document, "hidden", False))
                    has_focus_fn = getattr(platform.window.document, "hasFocus", None)
                    has_focus = bool(has_focus_fn()) if callable(has_focus_fn) else True
                    if (doc_hidden or not has_focus) and not state.paused:
                        state.paused = True
                except Exception:
                    pass
            elif not pygame.display.get_active() and not state.paused:
                state.paused = True

        if phase == "playing" and not state.paused and not show_help:
            # Countdown: tick down, block cat movement until it expires
            if countdown_ms > 0:
                countdown_ms = max(0, countdown_ms - dt_ms)
            # Handle respawn-triggered countdowns
            if state.respawn_pending and not state.game_over:
                state.respawn_pending = False
                countdown_ms = COUNTDOWN_TOTAL_MS
                cat_ms_accum = 0
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

            if state.game_over and not score_saved and not entering_initials:
                new_high_score = is_high_score(state.score)
                if new_high_score:
                    entering_initials = True
                    entry_initials = ""
                else:
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
                if sound_enabled:
                    s = snd.get(snd_name)
                    if s:
                        s.play()
            state.pending_sounds.clear()

        if phase == "playing":
            draw_board()
            if countdown_ms > 0 and not state.game_over and not state.paused:
                # --- Enhanced Countdown Overlay ---
                _cd_ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                _cd_ov.fill((0, 0, 0, 150))
                screen.blit(_cd_ov, (0, 0))
                _cdcx = SCREEN_WIDTH // 2
                _cdcy = SCREEN_HEIGHT // 2

                if countdown_ms > COUNTDOWN_GO_MS:
                    _cd_step = max(1, min(3, math.ceil((countdown_ms - COUNTDOWN_GO_MS) / COUNTDOWN_STEP_MS)))
                    _cd_label = str(_cd_step)
                    _remaining_in_step = (countdown_ms - COUNTDOWN_GO_MS) - (_cd_step - 1) * COUNTDOWN_STEP_MS
                    _step_t = 1.0 - _remaining_in_step / COUNTDOWN_STEP_MS  # 0=just appeared, 1=about to leave
                    _num_colors = {3: (255, 80, 60), 2: (255, 185, 45), 1: (255, 245, 80)}
                    _cd_col = _num_colors.get(_cd_step, (255, 220, 60))
                else:
                    _cd_label = "GO!"
                    _cd_col = (80, 255, 120)
                    _step_t = 1.0 - countdown_ms / COUNTDOWN_GO_MS

                # Scale: pop in large then ease to normal size
                _cd_scale = 1.0 + 0.55 * max(0.0, 1.0 - min(1.0, _step_t * 3.0))

                # Render and scale the number surface
                _cd_base   = big_title_font.render(_cd_label, True, _cd_col)
                _cd_shd_b  = big_title_font.render(_cd_label, True, (0, 0, 0))
                _bw, _bh   = _cd_base.get_size()
                _sw = max(1, int(_bw * _cd_scale))
                _sh = max(1, int(_bh * _cd_scale))
                _cd_scaled = pygame.transform.smoothscale(_cd_base, (_sw, _sh))
                _cd_shd_sc = pygame.transform.smoothscale(_cd_shd_b, (_sw, _sh))

                # Pulsing glow ring behind number
                _ring_r = int((_bh // 2 + 18) * _cd_scale)
                _glow_a = int(55 + 40 * math.sin(animation_frame / 8.0))
                _glow_sz = _ring_r * 2 + 24
                _glow_s  = pygame.Surface((_glow_sz, _glow_sz), pygame.SRCALPHA)
                pygame.draw.circle(_glow_s, (*_cd_col, _glow_a),
                                   (_glow_sz // 2, _glow_sz // 2), _ring_r, 10)
                screen.blit(_glow_s, (_cdcx - _glow_sz // 2, _cdcy - _glow_sz // 2))

                # Layered drop-shadow for depth
                for _soff in (5, 3, 2):
                    _tmp_s = _cd_shd_sc.copy()
                    _tmp_s.set_alpha(50 + _soff * 10)
                    screen.blit(_tmp_s, (_cdcx - _sw // 2 + _soff, _cdcy - _sh // 2 + _soff))

                # Main number
                screen.blit(_cd_scaled, (_cdcx - _sw // 2, _cdcy - _sh // 2))

                # Level label above the number
                _cd_lvl = font.render(f"LEVEL  {state.level}", True, (200, 186, 135))
                screen.blit(_cd_lvl, (_cdcx - _cd_lvl.get_width() // 2, _cdcy - _sh // 2 - 38))

                # Difficulty badge below the number
                _diff_name = DIFFICULTIES[diff_idx].upper()
                _dbc = {"EASY": (36, 120, 46), "NORMAL": (38, 40, 120), "HARD": (130, 28, 28)}
                _dtc = {"EASY": (130, 240, 148), "NORMAL": (188, 186, 255), "HARD": (255, 138, 128)}
                _db_col = _dbc.get(_diff_name, (80, 78, 50))
                _dt_col = _dtc.get(_diff_name, (200, 190, 140))
                _db_s = small_font.render(_diff_name, True, _dt_col)
                _db_r = pygame.Rect(0, 0, _db_s.get_width() + 22, _db_s.get_height() + 8)
                _db_r.center = (_cdcx, _cdcy + _sh // 2 + 22)
                pygame.draw.rect(screen, _db_col, _db_r, border_radius=7)
                pygame.draw.rect(screen, _dt_col, _db_r, 1, border_radius=7)
                screen.blit(_db_s, (_db_r.centerx - _db_s.get_width() // 2,
                                    _db_r.centery - _db_s.get_height() // 2))
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
