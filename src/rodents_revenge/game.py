from __future__ import annotations

import array
import heapq
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import pygame


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

MOUSE_STEP_SCORE = 1
CHEESE_SCORE = 25
TRAP_SCORE = 100
MULTI_TRAP_BONUS = 150

CAT_MOVE_DELAY_FRAMES = 8

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
    # Prefer the older-style strips for a closer retro look.
    mouse_frames = _load_strip_frames(raw_dir / "rat" / "rat_0_walk.png", sprite_size, max_frames=4)
    cat_frames = _load_strip_frames(raw_dir / "cat_1" / "cat_1_walk.png", sprite_size, max_frames=8)

    if not mouse_frames:
        mouse_frames = _load_strip_frames(raw_dir / "mouse" / "mouse_0_walk.png", sprite_size, max_frames=4)
    if not cat_frames:
        cat_frames = _load_strip_frames(raw_dir / "cat_0" / "cat_0_walk.png", sprite_size, max_frames=8)

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

        wall_count = min(8 + level * 2, 40)
        block_count = min(24 + level * 8, 150)
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
        extra_blocks = min(4 + level * 2, 24)
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
                self._lose_life()
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
                self._lose_life()
                life_lost = True
            new_positions.append((nx, ny))
            occupied.add((nx, ny))

        self.cats = new_positions
        self._resolve_trapped_cats()

    def _resolve_trapped_cats(self) -> None:
        survivors: list[tuple[int, int]] = []
        trap_count = 0
        for cat in self.cats:
            if self.is_cat_trapped(*cat):
                cx, cy = cat
                self.board[cy][cx] = CHEESE
                trap_count += 1
            else:
                survivors.append(cat)
        self.cats = survivors
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
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not self.in_bounds(nx, ny):
                continue
            if (nx, ny) == self.mouse_pos:
                return False
            if self._cat_at(nx, ny):
                return False
            if self.board[ny][nx] in (EMPTY, CHEESE):
                return False
        return True

    def _lose_life(self) -> None:
        self.lives -= 1
        self.pending_sounds.append("death")
        if self.lives <= 0:
            self.game_over = True
        else:
            self.respawn_flash = 90
            self.mouse_pos = self._find_free_cell(prefer_corner=True)

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
            if self.board[ny][nx] in (BLOCK, WALL):
                return False
            # No corner-cutting: diagonal movement requires both edge-adjacent cells open.
            if nx != cx and ny != cy:
                if self.board[cy][nx] in (BLOCK, WALL):
                    return False
                if self.board[ny][cx] in (BLOCK, WALL):
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

    def _find_free_cell(
        self,
        prefer_corner: bool = False,
        min_distance_from: tuple[int, int] | None = None,
        min_distance: int = 0,
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

        if prefer_corner:
            candidates.sort(key=lambda p: p[0] + p[1])
            return candidates[0]

        return random.choice(candidates)

    def _cat_at(self, x: int, y: int) -> bool:
        return (x, y) in self.cats

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height


def _draw_wall_tile(surface: pygame.Surface, rect: pygame.Rect) -> None:
    ts = rect.width
    pygame.draw.rect(surface, (72, 62, 52), rect.inflate(-2, -2))
    for row in range(1, 3):
        y = rect.y + row * ts // 3
        pygame.draw.line(surface, (42, 35, 28), (rect.x + 2, y), (rect.x + ts - 3, y), 1)
    for row in range(3):
        y0 = rect.y + row * ts // 3 + 1
        y1 = rect.y + (row + 1) * ts // 3 - 1
        if row % 2 == 0:
            x = rect.x + ts // 2
            pygame.draw.line(surface, (42, 35, 28), (x, y0), (x, y1), 1)
        else:
            for x in (rect.x + ts // 4, rect.x + 3 * ts // 4):
                pygame.draw.line(surface, (42, 35, 28), (x, y0), (x, y1), 1)


def _draw_block_tile(surface: pygame.Surface, rect: pygame.Rect) -> None:
    inner = rect.inflate(-4, -4)
    pygame.draw.rect(surface, (210, 185, 140), inner, border_radius=3)
    pygame.draw.rect(surface, (145, 115, 75), inner, 2, border_radius=3)
    cross = inner.inflate(-6, -6)
    pygame.draw.line(surface, (145, 115, 75), cross.topleft, cross.bottomright, 1)
    pygame.draw.line(surface, (145, 115, 75), cross.topright, cross.bottomleft, 1)


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


def run_game() -> None:
    try:
        pygame.mixer.pre_init(22050, -16, 1, 512)
    except Exception:
        pass
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Rodent's Revenge")
    pygame.display.set_icon(_make_icon())
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 24, bold=True)
    small_font = pygame.font.SysFont("monospace", 20)
    tiny_font = pygame.font.SysFont("monospace", 14)
    sprites = _load_sprite_pack(TILE_SIZE)
    title_font = pygame.font.SysFont("monospace", 40, bold=True)
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
        "mouse": (190, 230, 120),
        "cat": (235, 102, 75),
        "cheese": (254, 220, 90),
        "hud": (25, 23, 20),
        "text": (235, 226, 206),
        "alert": (255, 130, 130),
        "levelup": (140, 220, 160),
    }

    DIFFICULTIES = ["easy", "normal", "hard"]
    DIFF_SETTINGS: dict[str, dict[str, int]] = {
        "easy":   {"cat_delay_bonus":  3, "cat_count_offset": -1},
        "normal": {"cat_delay_bonus":  0, "cat_count_offset":  0},
        "hard":   {"cat_delay_bonus": -2, "cat_count_offset":  1},
    }
    diff_idx = 1  # default: normal
    TWEEN_FRAMES = 6
    block_tweens: list[dict] = []
    mouse_facing = 1   # +1 = right (default), -1 = left
    cat_alert: dict[tuple[int, int], int] = {}  # cat pos -> remaining flash frames
    show_help = False
    from rodents_revenge.scores import load_scores, save_score, is_high_score
    state = GameState()
    cat_frame_counter = 0
    animation_frame = 0
    phase = "title"  # "title" | "playing"
    score_saved = False
    new_high_score = False
    scores = load_scores()
    running = True

    def draw_board() -> None:
        _tween_dests = {(tw["gx1"], tw["gy1"]) for tw in block_tweens}
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
        screen.fill(colors["bg"])
        for y in range(state.height):
            for x in range(state.width):
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, colors["grid"], rect, 1)

                tile = state.board[y][x]
                if tile == WALL:
                    _draw_wall_tile(screen, rect)
                elif tile == BLOCK and (x, y) not in _tween_dests:
                    _draw_block_tile(screen, rect)
                elif tile == CHEESE:
                    _draw_cheese_tile(screen, rect)

        for cx, cy in state.cats:
            rect = pygame.Rect(cx * TILE_SIZE, cy * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE)
            if (cx, cy) in cat_alert:
                # draw orange glow ring behind sprite
                glow_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                alpha = min(180, 80 + cat_alert[(cx, cy)] * 5)
                pygame.draw.ellipse(glow_surf, (255, 140, 0, alpha),
                                    glow_surf.get_rect().inflate(-4, -4))
                screen.blit(glow_surf, rect.topleft)
            if sprites.cat_frames:
                frame = sprites.cat_frames[(animation_frame // 10) % len(sprites.cat_frames)]
                screen.blit(
                    frame,
                    (
                        rect.centerx - frame.get_width() // 2,
                        rect.centery - frame.get_height() // 2,
                    ),
                )
            else:
                pygame.draw.ellipse(screen, colors["cat"], rect.inflate(-6, -8))

        mx, my = state.mouse_pos
        mouse_rect = pygame.Rect(mx * TILE_SIZE, my * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE)
        if sprites.mouse_frames:
            frame = sprites.mouse_frames[(animation_frame // 8) % len(sprites.mouse_frames)]
            if mouse_facing < 0:
                frame = pygame.transform.flip(frame, True, False)
            screen.blit(
                frame,
                (
                    mouse_rect.centerx - frame.get_width() // 2,
                    mouse_rect.centery - frame.get_height() // 2,
                ),
            )
        else:
            pygame.draw.ellipse(screen, colors["mouse"], mouse_rect.inflate(-8, -8))

        for tw in block_tweens:
            t = tw["t"]
            px = int(tw["gx0"] * TILE_SIZE + (tw["gx1"] - tw["gx0"]) * TILE_SIZE * t)
            py = int(tw["gy0"] * TILE_SIZE + HUD_HEIGHT + (tw["gy1"] - tw["gy0"]) * TILE_SIZE * t)
            _draw_block_tile(screen, pygame.Rect(px, py, TILE_SIZE, TILE_SIZE))

        hud_rect = pygame.Rect(0, 0, SCREEN_WIDTH, HUD_HEIGHT)
        pygame.draw.rect(screen, colors["hud"], hud_rect)
        hud_text = font.render(
            f"Score {state.score:05d}   Level {state.level}   Cats {len(state.cats)}",
            True,
            colors["text"],
        )
        screen.blit(hud_text, (16, 18))
        pause_hint = small_font.render("P=pause", True, (110, 105, 85))
        screen.blit(pause_hint, (SCREEN_WIDTH // 2 - pause_hint.get_width() // 2, 20))

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
            text2 = small_font.render(
                "ENTER — menu    R — restart    Esc — quit", True, colors["text"]
            )
            y0 = SCREEN_HEIGHT // 2 - 55
            screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, y0))
            if new_high_score:
                hs_surf = font.render("NEW HIGH SCORE!", True, (255, 220, 50))
                screen.blit(hs_surf,   (SCREEN_WIDTH // 2 - hs_surf.get_width()   // 2, y0 + 38))
                screen.blit(score_surf,(SCREEN_WIDTH // 2 - score_surf.get_width() // 2, y0 + 76))
                screen.blit(text2,     (SCREEN_WIDTH // 2 - text2.get_width()     // 2, y0 + 114))
            else:
                screen.blit(score_surf,(SCREEN_WIDTH // 2 - score_surf.get_width() // 2, y0 + 38))
                screen.blit(text2,     (SCREEN_WIDTH // 2 - text2.get_width()     // 2, y0 + 76))

        if state.paused:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            screen.blit(overlay, (0, 0))
            p1 = font.render("PAUSED", True, (220, 215, 180))
            p2 = small_font.render("Press P to resume", True, (160, 155, 130))
            screen.blit(p1, (SCREEN_WIDTH // 2 - p1.get_width() // 2, SCREEN_HEIGHT // 2 - 28))
            screen.blit(p2, (SCREEN_WIDTH // 2 - p2.get_width() // 2, SCREEN_HEIGHT // 2 + 12))

    def draw_help_overlay() -> None:
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

        close = small_font.render("Press H to close", True, (110, 105, 80))
        screen.blit(close, (SCREEN_WIDTH // 2 - close.get_width() // 2, panel_y + panel_h - 28))

    def draw_title_screen() -> None:
        screen.fill((10, 8, 6))
        title_surf = title_font.render("RODENT'S REVENGE", True, (220, 200, 80))
        screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 55))
        sub_surf = small_font.render("Python Clone", True, (140, 130, 90))
        screen.blit(sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 108))
        if scores:
            label = font.render("HIGH SCORES", True, colors["text"])
            screen.blit(label, (SCREEN_WIDTH // 2 - label.get_width() // 2, 158))
            for i, entry in enumerate(scores[:5]):
                line = small_font.render(
                    f"{i + 1}.  {entry['score']:05d}   LVL {entry['level']:02d}",
                    True,
                    (255, 220, 60) if i == 0 else (200, 190, 160),
                )
                screen.blit(line, (SCREEN_WIDTH // 2 - line.get_width() // 2, 192 + i * 28))
        # Difficulty selector
        dlabel = small_font.render("DIFFICULTY  ← →", True, (160, 155, 130))
        screen.blit(dlabel, (SCREEN_WIDTH // 2 - dlabel.get_width() // 2, SCREEN_HEIGHT - 175))
        diff_colors = {"easy": (120, 210, 140), "normal": (235, 226, 206), "hard": (255, 130, 130)}
        x_offsets = [-220, 0, 220]
        for i, d in enumerate(DIFFICULTIES):
            col = diff_colors[d] if i == diff_idx else (90, 85, 70)
            label_str = f"[ {d.upper()} ]" if i == diff_idx else f"  {d.upper()}  "
            ds = small_font.render(label_str, True, col)
            screen.blit(ds, (SCREEN_WIDTH // 2 + x_offsets[i] - ds.get_width() // 2, SCREEN_HEIGHT - 148))

        if (animation_frame // 30) % 2 == 0:
            enter_surf = font.render("PRESS ENTER TO PLAY", True, colors["levelup"])
            screen.blit(enter_surf, (SCREEN_WIDTH // 2 - enter_surf.get_width() // 2, SCREEN_HEIGHT - 100))
        legal1 = tiny_font.render("Inspired by Microsoft Rodent's Revenge (Windows 95)", True, (120, 115, 95))
        legal2 = tiny_font.render("Unofficial fan remake using CC-BY licensed assets", True, (120, 115, 95))
        screen.blit(legal1, (SCREEN_WIDTH // 2 - legal1.get_width() // 2, SCREEN_HEIGHT - 84))
        screen.blit(legal2, (SCREEN_WIDTH // 2 - legal2.get_width() // 2, SCREEN_HEIGHT - 68))
        esc_surf = small_font.render("ESC to quit", True, (100, 95, 75))
        screen.blit(esc_surf, (SCREEN_WIDTH // 2 - esc_surf.get_width() // 2, SCREEN_HEIGHT - 58))

    while running:
        animation_frame += 1
        player_moved = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif phase == "title":
                    if event.key == pygame.K_RETURN:
                        s = DIFF_SETTINGS[DIFFICULTIES[diff_idx]]
                        state = GameState(
                            cat_delay_bonus=s["cat_delay_bonus"],
                            cat_count_offset=s["cat_count_offset"],
                        )
                        cat_frame_counter = 0
                        block_tweens.clear()
                        score_saved = False
                        new_high_score = False
                        phase = "playing"
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        diff_idx = (diff_idx - 1) % len(DIFFICULTIES)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        diff_idx = (diff_idx + 1) % len(DIFFICULTIES)
                elif phase == "playing":
                    if state.game_over:
                        if event.key == pygame.K_RETURN:
                            phase = "title"
                            scores = load_scores()
                        elif event.key == pygame.K_r:
                            state.restart_game()
                            block_tweens.clear()
                            score_saved = False
                            new_high_score = False
                    elif event.key == pygame.K_p:
                        state.paused = not state.paused
                    elif event.key == pygame.K_h:
                        show_help = not show_help
                    elif not state.paused and not show_help:
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

        if phase == "playing" and not state.paused and not show_help:
            if player_moved and not state.game_over:
                cat_frame_counter += 1
                cat_delay = max(2, CAT_MOVE_DELAY_FRAMES - (state.level - 1) + state.cat_delay_bonus)
                if cat_frame_counter >= cat_delay:
                    cat_frame_counter = 0
                    state.step_cats()

            if state.level_clear_delay > 0 and not state.game_over:
                state.level_clear_delay -= 1
                if state.level_clear_delay == 0:
                    state.reset_level(state.level + 1)
                    block_tweens.clear()

            if state.respawn_flash > 0:
                state.respawn_flash -= 1

            if state.game_over and not score_saved:
                new_high_score = is_high_score(state.score)
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
            if show_help:
                draw_help_overlay()
        else:
            draw_title_screen()

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
