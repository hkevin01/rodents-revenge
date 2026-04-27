from __future__ import annotations

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

CAT_MOVE_DELAY_FRAMES = 8


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
    mouse_frames = _load_strip_frames(raw_dir / "mouse" / "mouse_0_walk.png", sprite_size, max_frames=4)
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
    board: list[list[int]] = field(default_factory=list)
    mouse_pos: tuple[int, int] = (1, 1)
    cats: list[tuple[int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.board:
            self.reset_level(self.level)

    def reset_level(self, level: int) -> None:
        self.level = level
        self.game_over = False
        self.win_level_flash = 30
        self.respawn_flash = 0
        self.level_clear_delay = 0
        self.board = [[EMPTY for _ in range(self.width)] for _ in range(self.height)]

        for x in range(self.width):
            self.board[0][x] = WALL
            self.board[self.height - 1][x] = WALL
        for y in range(self.height):
            self.board[y][0] = WALL
            self.board[y][self.width - 1] = WALL

        wall_count = min(8 + level * 2, 40)
        block_count = min(18 + level * 6, 120)
        cat_count = min(2 + level, 12)

        self._place_random_cells(WALL, wall_count)
        self._place_random_cells(BLOCK, block_count)

        self.mouse_pos = self._find_free_cell(prefer_corner=True)
        self.cats = []
        for _ in range(cat_count):
            self.cats.append(self._find_free_cell(min_distance_from=self.mouse_pos, min_distance=5))

    def restart_game(self) -> None:
        self.score = 0
        self.lives = 3
        self.reset_level(1)

    def handle_player_move(self, dx: int, dy: int) -> bool:
        if self.game_over or self.level_clear_delay > 0:
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
            self.score += MOUSE_STEP_SCORE
            return True

        if target == BLOCK:
            bx, by = nx + dx, ny + dy
            if not self.in_bounds(bx, by):
                return False
            if self.board[by][bx] != EMPTY or self._cat_at(bx, by) or (bx, by) == self.mouse_pos:
                return False
            self.board[by][bx] = BLOCK
            self.board[ny][nx] = EMPTY
            self.mouse_pos = (nx, ny)
            self.score += MOUSE_STEP_SCORE
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
        for cat in self.cats:
            if self.is_cat_trapped(*cat):
                cx, cy = cat
                self.board[cy][cx] = CHEESE
                self.score += TRAP_SCORE
            else:
                survivors.append(cat)
        self.cats = survivors
        if not self.cats and not self.game_over and self.level_clear_delay == 0:
            self.score += 300
            self.level_clear_delay = 90

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
        if self.lives <= 0:
            self.game_over = True
        else:
            self.respawn_flash = 90
            self.mouse_pos = self._find_free_cell(prefer_corner=True)

    def _next_cat_position(self, cat: tuple[int, int], occupied: set[tuple[int, int]]) -> tuple[int, int]:
        x, y = cat
        mx, my = self.mouse_pos

        horiz = (1 if mx > x else -1, 0) if mx != x else None
        vert = (0, 1 if my > y else -1) if my != y else None

        attempts: list[tuple[int, int]] = []
        if horiz:
            attempts.append(horiz)
        if vert:
            attempts.append(vert)
        random_dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        random.shuffle(random_dirs)
        attempts.extend(random_dirs)

        for dx, dy in attempts:
            nx, ny = x + dx, y + dy
            if not self.in_bounds(nx, ny):
                continue
            if (nx, ny) in occupied:
                continue
            if self.board[ny][nx] in (BLOCK, WALL):
                continue
            return nx, ny

        return x, y

    def _place_random_cells(self, kind: int, count: int) -> None:
        placed = 0
        attempts = 0
        limit = count * 50
        while placed < count and attempts < limit:
            attempts += 1
            x = random.randint(1, self.width - 2)
            y = random.randint(1, self.height - 2)
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


def run_game() -> None:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Rodent's Revenge Clone")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 24, bold=True)
    small_font = pygame.font.SysFont("monospace", 20)
    sprites = _load_sprite_pack(TILE_SIZE)

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

    state = GameState()
    cat_frame_counter = 0
    animation_frame = 0
    running = True

    def draw_board() -> None:
        screen.fill(colors["bg"])
        for y in range(state.height):
            for x in range(state.width):
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, colors["grid"], rect, 1)

                tile = state.board[y][x]
                if tile == WALL:
                    pygame.draw.rect(screen, colors["wall"], rect.inflate(-4, -4), border_radius=5)
                elif tile == BLOCK:
                    pygame.draw.rect(screen, colors["block"], rect.inflate(-6, -6), border_radius=4)
                elif tile == CHEESE:
                    pygame.draw.circle(screen, colors["cheese"], rect.center, TILE_SIZE // 3)

        for cx, cy in state.cats:
            rect = pygame.Rect(cx * TILE_SIZE, cy * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE)
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
            screen.blit(
                frame,
                (
                    mouse_rect.centerx - frame.get_width() // 2,
                    mouse_rect.centery - frame.get_height() // 2,
                ),
            )
        else:
            pygame.draw.ellipse(screen, colors["mouse"], mouse_rect.inflate(-8, -8))

        hud_rect = pygame.Rect(0, 0, SCREEN_WIDTH, HUD_HEIGHT)
        pygame.draw.rect(screen, colors["hud"], hud_rect)
        hud_text = font.render(
            f"Score {state.score:05d}   Level {state.level}   Cats {len(state.cats)}",
            True,
            colors["text"],
        )
        screen.blit(hud_text, (16, 18))

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

        if state.level_clear_delay > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 80))
            screen.blit(overlay, (0, 0))
            msg = font.render("Get ready...", True, colors["levelup"])
            screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, SCREEN_HEIGHT // 2 - 20))

        if state.respawn_flash > 0 and (state.respawn_flash // 6) % 2 == 0:
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 200, 35))
            screen.blit(flash, (0, 0))

        if state.game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            screen.blit(overlay, (0, 0))
            text1 = font.render("Game Over", True, colors["alert"])
            text2 = small_font.render("Press R to restart, Esc to quit", True, colors["text"])
            screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, SCREEN_HEIGHT // 2 - 30))
            screen.blit(text2, (SCREEN_WIDTH // 2 - text2.get_width() // 2, SCREEN_HEIGHT // 2 + 8))

    while running:
        animation_frame += 1
        player_moved = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif state.game_over and event.key == pygame.K_r:
                    state.restart_game()
                elif not state.game_over:
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        player_moved = state.handle_player_move(-1, 0)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        player_moved = state.handle_player_move(1, 0)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        player_moved = state.handle_player_move(0, -1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        player_moved = state.handle_player_move(0, 1)

        if player_moved and not state.game_over:
            cat_frame_counter += 1
            cat_delay = max(2, CAT_MOVE_DELAY_FRAMES - (state.level - 1))
            if cat_frame_counter >= cat_delay:
                cat_frame_counter = 0
                state.step_cats()

        if state.level_clear_delay > 0 and not state.game_over:
            state.level_clear_delay -= 1
            if state.level_clear_delay == 0:
                state.reset_level(state.level + 1)

        if state.respawn_flash > 0:
            state.respawn_flash -= 1

        draw_board()
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
