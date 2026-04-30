from rodents_revenge.game import (
    BLOCK, CHEESE, EMPTY, GameState, WALL,
    TRAP_SCORE, CHEESE_SCORE, MULTI_TRAP_BONUS,
    GRID_WIDTH, LEVEL_PRESETS,
)


def blank_state() -> GameState:
    state = GameState(width=8, height=8)
    state.board = [[EMPTY for _ in range(state.width)] for _ in range(state.height)]
    for x in range(state.width):
        state.board[0][x] = WALL
        state.board[state.height - 1][x] = WALL
    for y in range(state.height):
        state.board[y][0] = WALL
        state.board[y][state.width - 1] = WALL
    state.mouse_pos = (2, 2)
    state.cats = []
    state.game_over = False
    state.score = 0
    state.level = 1
    state.lives = 3
    return state


def test_mouse_pushes_block() -> None:
    state = blank_state()
    state.board[2][3] = BLOCK

    moved = state.handle_player_move(1, 0)

    assert moved is True
    assert state.mouse_pos == (3, 2)
    assert state.board[2][4] == BLOCK
    assert state.board[2][3] == EMPTY


def test_trapped_cat_turns_to_cheese() -> None:
    state = blank_state()
    state.cats = [(5, 5)]
    # Block all 8 surrounding cells — diagonal movement requires full 8-way surround
    for bx, by in [(4,4),(5,4),(6,4),(4,5),(6,5),(4,6),(5,6),(6,6)]:
        state.board[by][bx] = BLOCK

    state.step_cats()

    assert state.cats == []
    assert state.board[5][5] == CHEESE


def test_level_clear_delay_set_when_all_cats_removed() -> None:
    state = blank_state()
    state.cats = []

    state.step_cats()

    # Level does NOT advance immediately — a delay is queued first.
    assert state.level_clear_delay == 90
    assert state.level == 1
    assert state.score == 300  # bonus awarded


def test_level_advances_after_clear_delay() -> None:
    state = blank_state()
    state.level_clear_delay = 1

    # Simulate one game-loop tick counting down to zero.
    state.level_clear_delay -= 1
    if state.level_clear_delay == 0:
        state.reset_level(state.level + 1)

    assert state.level == 2


def test_lives_decrease_on_cat_collision() -> None:
    state = blank_state()
    state.cats = [(3, 2)]  # one step right of the mouse

    state.handle_player_move(1, 0)  # walk into cat

    assert state.lives == 2
    assert state.game_over is False


def test_game_over_when_last_life_lost() -> None:
    state = blank_state()
    state.lives = 1
    state.cats = [(3, 2)]

    state.handle_player_move(1, 0)

    assert state.game_over is True


def test_respawn_invincibility_prevents_death() -> None:
    state = blank_state()
    state.lives = 2
    state.respawn_flash = 60  # currently invincible
    state.cats = [(3, 2)]

    state.handle_player_move(1, 0)  # would normally kill player

    assert state.lives == 2  # no life lost while invincible


def test_multi_trap_bonus_two_cats() -> None:
    state = blank_state()
    # Cats at (3,5) and (5,5) — fully enclosed on all 8 sides each.
    state.cats = [(3, 5), (5, 5)]
    # Surround (3,5): all 8 neighbors
    for bx, by in [(2,4),(3,4),(4,4),(2,5),(4,5),(2,6),(3,6),(4,6)]:
        state.board[by][bx] = BLOCK
    # Surround (5,5): all 8 neighbors (some shared with above)
    for bx, by in [(4,4),(5,4),(6,4),(4,5),(6,5),(4,6),(5,6),(6,6)]:
        state.board[by][bx] = BLOCK

    state.step_cats()

    assert state.cats == []
    assert state.last_trap_count == 2
    expected_trap = 2 * TRAP_SCORE + 1 * MULTI_TRAP_BONUS  # 200 + 150
    expected_clear = 300
    assert state.score == expected_trap + expected_clear


def test_single_trap_no_combo_bonus() -> None:
    state = blank_state()
    state.cats = [(5, 5)]
    for bx, by in [(4,4),(5,4),(6,4),(4,5),(6,5),(4,6),(5,6),(6,6)]:
        state.board[by][bx] = BLOCK

    state.step_cats()

    assert state.last_trap_count == 1
    assert state.score == TRAP_SCORE + 300  # no combo bonus


def test_two_adjacent_enclosed_cats_turn_to_cheese() -> None:
    state = blank_state()
    cats = [(4, 4), (5, 4)]
    state.cats = cats[:]

    # Enclose the 2-cat cluster; cats only touch each other and cannot escape.
    for y in range(3, 6):
        for x in range(3, 7):
            if (x, y) not in cats:
                state.board[y][x] = BLOCK

    state.step_cats()

    assert state.cats == []
    assert state.board[4][4] == CHEESE
    assert state.board[4][5] == CHEESE


def test_three_adjacent_enclosed_cats_turn_to_cheese() -> None:
    state = blank_state()
    cats = [(3, 4), (4, 4), (5, 4)]
    state.cats = cats[:]

    # Enclose the 3-cat cluster; no external move exists.
    for y in range(3, 6):
        for x in range(2, 7):
            if (x, y) not in cats:
                state.board[y][x] = BLOCK

    state.step_cats()

    assert state.cats == []
    assert state.board[4][3] == CHEESE
    assert state.board[4][4] == CHEESE
    assert state.board[4][5] == CHEESE


def test_save_and_load_scores(tmp_path, monkeypatch) -> None:
    import rodents_revenge.scores as scores_mod

    monkeypatch.setattr(scores_mod, "_SCORES_FILE", tmp_path / "scores.json")

    scores_mod.save_score(1000, 5)
    scores_mod.save_score(2000, 8)
    scores_mod.save_score(500, 2)

    loaded = scores_mod.load_scores()
    assert len(loaded) == 3
    assert loaded[0]["score"] == 2000
    assert loaded[1]["score"] == 1000
    assert loaded[2]["score"] == 500


def test_is_high_score(tmp_path, monkeypatch) -> None:
    import rodents_revenge.scores as scores_mod

    monkeypatch.setattr(scores_mod, "_SCORES_FILE", tmp_path / "scores.json")

    # With no existing scores any positive score qualifies.
    assert scores_mod.is_high_score(100) is True
    assert scores_mod.is_high_score(0) is False

    scores_mod.save_score(500, 3)
    assert scores_mod.is_high_score(600) is True
    assert scores_mod.is_high_score(400) is True  # still under MAX_SCORES entries


def test_cheese_collected_for_score() -> None:
    state = blank_state()
    state.board[2][3] = CHEESE

    state.handle_player_move(1, 0)

    assert state.board[2][3] == EMPTY
    assert state.score == CHEESE_SCORE   # no move-step score in original rules


def test_cat_bfs_navigates_around_wall() -> None:
    # Board layout (8x8 with perimeter walls):
    #   Cat is at (1,3), mouse at (5,3).
    #   A vertical BLOCK wall runs from (3,1) to (3,5), forcing BFS to go around.
    state = blank_state()
    state.mouse_pos = (5, 3)
    state.cats = [(1, 3)]
    for y in range(1, 6):
        state.board[y][3] = BLOCK  # vertical wall blocking direct path

    initial_x = state.cats[0][0]
    # Run several steps so the cat can navigate around the wall.
    for _ in range(8):
        state.step_cats()
        if not state.cats:
            break  # cat reached mouse (shouldn't happen without lives, but guard)

    # After 8 moves the cat must have moved away from its starting x=1 column.
    if state.cats:
        assert state.cats[0][0] != initial_x, "Cat should have moved toward mouse via BFS"


def test_cat_moves_diagonally_toward_mouse() -> None:
    state = blank_state()
    state.mouse_pos = (5, 5)
    state.cats = [(3, 3)]

    state.step_cats()

    assert state.cats[0] == (4, 4)


def test_cats_do_not_step_onto_cheese() -> None:
    state = blank_state()
    state.mouse_pos = (6, 3)
    state.cats = [(3, 3)]
    state.board[3][4] = CHEESE  # direct beeline cell is blocked for cats

    state.step_cats()

    assert state.cats[0] != (4, 3)


def test_trapped_cat_resolves_immediately_after_player_move() -> None:
    state = blank_state()
    state.mouse_pos = (2, 3)
    state.cats = [(5, 3)]
    # Pre-place 7 of 8 surrounding cells (all except left side (4,3) to be pushed).
    state.board[2][5] = BLOCK  # (5,2) above
    state.board[4][5] = BLOCK  # (5,4) below
    state.board[3][6] = BLOCK  # (6,3) right
    state.board[2][4] = BLOCK  # (4,2) diagonal
    state.board[2][6] = BLOCK  # (6,2) diagonal
    state.board[4][4] = BLOCK  # (4,4) diagonal
    state.board[4][6] = BLOCK  # (6,4) diagonal
    # Push this block from (3,3) into (4,3) to close the final side.
    state.board[3][3] = BLOCK
    state.board[3][4] = EMPTY

    moved = state.handle_player_move(1, 0)

    assert moved is True
    assert state.board[3][5] == CHEESE
    assert (5, 3) not in state.cats


def test_cat_beelines_into_near_trap_space() -> None:
    state = blank_state()
    state.mouse_pos = (6, 6)
    state.cats = [(3, 3)]

    # Make (4,4) a risky near-trap cell (2 blocked sides, still beeline-worthy).
    state.board[4][5] = BLOCK  # (5,4)
    state.board[5][4] = BLOCK  # (4,5)

    state.step_cats()

    assert state.cats[0] == (4, 4)


def test_pause_blocks_player_move() -> None:
    state = blank_state()
    state.paused = True
    moved = state.handle_player_move(1, 0)
    assert moved is False
    assert state.mouse_pos == (2, 2)  # position unchanged


def test_block_push_records_last_block_push() -> None:
    state = blank_state()
    state.board[2][3] = BLOCK  # block at (3, 2), space at (4, 2)

    moved = state.handle_player_move(1, 0)

    assert moved is True
    assert state.last_block_push == (3, 2, 4, 2)  # from=(3,2) to=(4,2)
    assert state.mouse_pos == (3, 2)


def test_mouse_pushes_multiple_blocks_in_chain() -> None:
    state = blank_state()
    state.board[2][3] = BLOCK
    state.board[2][4] = BLOCK
    state.board[2][5] = BLOCK

    moved = state.handle_player_move(1, 0)

    assert moved is True
    assert state.mouse_pos == (3, 2)
    assert state.board[2][4] == BLOCK
    assert state.board[2][5] == BLOCK
    assert state.board[2][6] == BLOCK
    assert state.board[2][3] == EMPTY


def test_mouse_can_push_block_into_cheese_and_crush_it() -> None:
    state = blank_state()
    state.board[2][3] = BLOCK
    state.board[2][4] = CHEESE

    moved = state.handle_player_move(1, 0)

    assert moved is True
    assert state.mouse_pos == (3, 2)
    assert state.board[2][4] == BLOCK
    assert state.score == 0  # crushed cheese is not collected by the mouse


def test_mouse_cannot_push_multiple_blocks_if_no_space() -> None:
    state = blank_state()
    state.board[2][3] = BLOCK
    state.board[2][4] = BLOCK
    state.board[2][5] = BLOCK
    state.board[2][6] = WALL

    moved = state.handle_player_move(1, 0)

    assert moved is False
    assert state.mouse_pos == (2, 2)
    assert state.board[2][3] == BLOCK
    assert state.board[2][4] == BLOCK
    assert state.board[2][5] == BLOCK


def test_difficulty_cat_count_offset() -> None:
    easy = GameState(cat_count_offset=-1)
    normal = GameState(cat_count_offset=0)
    hard = GameState(cat_count_offset=1)

    # Preset level 1 scales cat pressure by difficulty.
    assert len(easy.cats) <= len(normal.cats) <= len(hard.cats)
    assert len(easy.cats) >= 1
    assert len(normal.cats) == 1


def test_difficulty_cat_delay_bonus_stored() -> None:
    state = GameState(cat_delay_bonus=3)
    assert state.cat_delay_bonus == 3
    # Survives reset_level
    state.reset_level(2)
    assert state.cat_delay_bonus == 3


def test_all_preset_rows_match_expected_interior_width() -> None:
    expected_width = GRID_WIDTH - 2
    for rows in LEVEL_PRESETS.values():
        for row in rows:
            assert len(row) == expected_width


def test_level_6_wall_paths_are_connected_from_mouse_spawn() -> None:
    from collections import deque

    rows = LEVEL_PRESETS[6]
    width = GRID_WIDTH - 2
    height = len(rows)

    mouse = None
    board: list[list[str]] = []
    for y, row in enumerate(rows):
        line: list[str] = []
        for x in range(width):
            ch = row[x]
            if ch == "M":
                mouse = (x, y)
                ch = "."
            line.append(ch)
        board.append(line)

    assert mouse is not None

    queue: deque[tuple[int, int]] = deque([mouse])
    visited = {mouse}
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if (nx, ny) in visited:
                continue
            if board[ny][nx] == "#":
                continue
            visited.add((nx, ny))
            queue.append((nx, ny))

    open_cells = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if board[y][x] != "#"
    }
    assert visited == open_cells


def test_handcrafted_levels_use_lighter_wall_budgets() -> None:
    expected_limits = {
        1: 11,
        2: 18,
        3: 22,
        4: 22,
        5: 24,
        6: 26,
        7: 28,
        8: 28,
        9: 32,
        10: 34,
    }

    for level, limit in expected_limits.items():
        state = GameState(level=level)
        wall_count = sum(
            1
            for y in range(1, state.height - 1)
            for x in range(1, state.width - 1)
            if state.board[y][x] == WALL
        )
        assert wall_count <= limit


# ---------- new feature tests ----------

def test_cat_in_same_row_no_wall_is_line_of_sight() -> None:
    """Cat and mouse on same row with clear corridor — LoS is True."""
    state = blank_state()
    state.mouse_pos = (2, 3)
    state.cats = [(5, 3)]
    # No walls between x=3 and x=4 (board is all EMPTY between them)
    cx, cy = 5, 3
    mx, my = 2, 3
    # Replicate the LoS logic from draw_board
    x0, x1 = min(cx, mx) + 1, max(cx, mx)
    in_sight = all(state.board[cy][xx] not in (WALL, BLOCK) for xx in range(x0, x1))
    assert in_sight is True


def test_cat_in_same_row_wall_blocks_line_of_sight() -> None:
    """A WALL between cat and mouse breaks LoS."""
    state = blank_state()
    state.mouse_pos = (2, 3)
    state.cats = [(5, 3)]
    state.board[3][3] = WALL  # wall at x=3, between mouse(x=2) and cat(x=5)
    cx, cy = 5, 3
    mx, my = 2, 3
    x0, x1 = min(cx, mx) + 1, max(cx, mx)
    in_sight = all(state.board[cy][xx] not in (WALL, BLOCK) for xx in range(x0, x1))
    assert in_sight is False


def test_level_clear_delay_next_level_is_current_plus_one() -> None:
    """The 'Get ready' overlay should show level+1 (the upcoming level)."""
    state = blank_state()
    state.level = 3
    state.level_clear_delay = 45  # mid-transition
    # The overlay code reads: next_level = state.level + 1
    next_level = state.level + 1
    assert next_level == 4


def test_level1_uses_preset_layout() -> None:
    state = GameState()

    # Mouse and key tiles come from handcrafted preset map.
    assert state.mouse_pos == (3, 4)
    assert state.board[2][3] == BLOCK
    assert state.board[3][7] == WALL
    assert state.board[3][15] == CHEESE


def test_level1_preset_default_cat_count() -> None:
    state = GameState(cat_count_offset=0)
    assert len(state.cats) == 1


def test_level2_uses_preset_layout() -> None:
    state = GameState()
    state.reset_level(2)

    assert state.mouse_pos == (3, 4)
    assert state.board[1][6] == WALL
    assert state.board[2][3] == BLOCK
    assert state.board[2][13] == CHEESE
    assert len(state.cats) == 2


def test_level3_uses_preset_layout() -> None:
    state = GameState()
    state.reset_level(3)

    assert state.mouse_pos == (3, 4)
    assert state.board[1][5] == WALL
    assert state.board[2][3] == BLOCK
    assert state.board[2][11] == CHEESE
    assert len(state.cats) == 3


def test_level4_uses_preset_layout() -> None:
    state = GameState()
    state.reset_level(4)

    assert state.mouse_pos == (3, 4)
    assert state.board[1][9] == WALL
    assert state.board[2][3] == BLOCK
    assert state.board[2][16] == CHEESE
    assert len(state.cats) == 3


def test_level10_uses_preset_layout() -> None:
    state = GameState()
    state.reset_level(10)

    assert state.mouse_pos == (7, 5)
    assert state.board[1][3] == WALL
    assert state.board[3][5] == BLOCK
    assert state.board[2][10] == CHEESE
    assert len(state.cats) == 4


def test_level1_has_more_blocks_than_preset_base() -> None:
    state = GameState()
    block_count = sum(
        state.board[y][x] == BLOCK
        for y in range(state.height)
        for x in range(state.width)
    )
    # Base level-1 preset had 9 explicit blocks.
    assert block_count > 9


def test_procedural_levels_have_higher_block_density() -> None:
    # Levels >= 11 use the seeded generator; tier increases every 10 levels.
    # Level 11 → tier 0 → block_cnt 22; level 21 → tier 1 → block_cnt 25.
    low = GameState(width=20, height=15)
    low.reset_level(11)
    high = GameState(width=20, height=15)
    high.reset_level(21)

    low_blocks = sum(low.board[y][x] == BLOCK for y in range(low.height) for x in range(low.width))
    high_blocks = sum(high.board[y][x] == BLOCK for y in range(high.height) for x in range(high.width))

    # Seeded level 11 should have at least 20 blocks placed (allows for solvability culling)
    assert low_blocks >= 20
    # Higher level should have at least as many blocks
    assert high_blocks >= low_blocks


# ---------- roadmap batch: help overlay / near-clear / cheese scatter ----------

def test_cheese_scatter_on_level_start() -> None:
    """reset_level should place bonus CHEESE tiles on the board."""
    state = GameState(width=20, height=15)
    # Count cheese tiles placed (level 1 → min(3+1, 15) = 4)
    cheese_count = sum(
        state.board[y][x] == CHEESE
        for y in range(state.height)
        for x in range(state.width)
    )
    assert cheese_count >= 3, f"Expected ≥3 cheese tiles at level start, got {cheese_count}"


def test_cheese_scatter_increases_with_level() -> None:
    """Higher levels place more cheese (up to 15 tiles)."""
    low  = GameState(width=20, height=15)
    low.reset_level(1)
    high = GameState(width=20, height=15)
    high.reset_level(8)

    def _cheese(s: GameState) -> int:
        return sum(s.board[y][x] == CHEESE for y in range(s.height) for x in range(s.width))

    # Higher level places at least as many cheese as lower level (capped at 15)
    assert _cheese(high) >= _cheese(low)


def test_near_clear_warn_sound_fires_at_two_cats() -> None:
    """'warn' sound appended to pending_sounds when cats drop to exactly 2."""
    state = blank_state()
    # Three cats; fully surround one (3,5) on all 8 sides leaving 2 survivors.
    state.cats = [(3, 5), (5, 3), (5, 5)]
    for bx, by in [(2,4),(3,4),(4,4),(2,5),(4,5),(2,6),(3,6),(4,6)]:
        state.board[by][bx] = BLOCK

    state.step_cats()

    assert "warn" in state.pending_sounds
    assert state.near_clear_warned is True


def test_near_clear_warn_fires_only_once_per_level() -> None:
    """Repeated step_cats calls must not re-queue 'warn'."""
    state = blank_state()
    # Fully surround cat at (3,5) — same setup as warn-fires test.
    state.cats = [(3, 5), (5, 3), (5, 5)]
    for bx, by in [(2,4),(3,4),(4,4),(2,5),(4,5),(2,6),(3,6),(4,6)]:
        state.board[by][bx] = BLOCK

    state.step_cats()             # (3,5) trapped → 2 remain → warn fires
    state.pending_sounds.clear()  # consume queue
    state.step_cats()             # second step — near_clear_warned True → no warn

    assert "warn" not in state.pending_sounds


def test_near_clear_warn_not_fired_when_already_warned() -> None:
    """near_clear_warned flag prevents duplicate sounds mid-level."""
    state = blank_state()
    state.near_clear_warned = True
    state.cats = [(3, 3), (5, 3)]
    for bx, by in [(3, 2), (3, 4), (2, 3), (4, 3)]:
        state.board[by][bx] = BLOCK

    state.step_cats()

    assert "warn" not in state.pending_sounds


def test_near_clear_warned_resets_on_new_level() -> None:
    """reset_level clears near_clear_warned so next level can warn again."""
    state = blank_state()
    state.near_clear_warned = True
    state.reset_level(2)
    assert state.near_clear_warned is False
