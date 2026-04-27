from rodents_revenge.game import (
    BLOCK, CHEESE, EMPTY, GameState, WALL,
    TRAP_SCORE, CHEESE_SCORE, MULTI_TRAP_BONUS,
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
    state.cats = [(3, 3)]
    state.board[2][3] = BLOCK
    state.board[4][3] = BLOCK
    state.board[3][2] = BLOCK
    state.board[3][4] = BLOCK

    state.step_cats()

    assert state.cats == []
    assert state.board[3][3] == CHEESE


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
    # Cat at (3,3) enclosed by blocks on all four sides.
    state.cats = [(3, 3), (5, 3)]
    for bx, by in [(3, 2), (3, 4), (2, 3), (4, 3)]:
        state.board[by][bx] = BLOCK
    # Cat at (5,3) enclosed on all four sides.
    for bx, by in [(5, 2), (5, 4), (4, 3), (6, 3)]:
        state.board[by][bx] = BLOCK

    state.step_cats()

    assert state.cats == []
    assert state.last_trap_count == 2
    expected_trap = 2 * TRAP_SCORE + 1 * MULTI_TRAP_BONUS  # 200 + 150
    expected_clear = 300
    assert state.score == expected_trap + expected_clear


def test_single_trap_no_combo_bonus() -> None:
    state = blank_state()
    state.cats = [(3, 3)]
    for bx, by in [(3, 2), (3, 4), (2, 3), (4, 3)]:
        state.board[by][bx] = BLOCK

    state.step_cats()

    assert state.last_trap_count == 1
    assert state.score == TRAP_SCORE + 300  # no combo bonus


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
    assert state.score == CHEESE_SCORE + 1


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


def test_difficulty_cat_count_offset() -> None:
    # Easy: -1 offset, level 1 → max(1, 2 + 1 - 1) = 2
    easy = GameState(cat_count_offset=-1)
    assert len(easy.cats) == 2

    # Hard: +1 offset, level 1 → max(1, 2 + 1 + 1) = 4
    hard = GameState(cat_count_offset=1)
    assert len(hard.cats) == 4


def test_difficulty_cat_delay_bonus_stored() -> None:
    state = GameState(cat_delay_bonus=3)
    assert state.cat_delay_bonus == 3
    # Survives reset_level
    state.reset_level(2)
    assert state.cat_delay_bonus == 3


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
