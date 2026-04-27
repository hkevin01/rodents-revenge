from rodents_revenge.game import BLOCK, CHEESE, EMPTY, GameState, WALL, TRAP_SCORE, CHEESE_SCORE


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


def test_cheese_collected_for_score() -> None:
    state = blank_state()
    state.board[2][3] = CHEESE

    state.handle_player_move(1, 0)  # move onto cheese cell

    assert state.board[2][3] == EMPTY
    assert state.score == CHEESE_SCORE + 1  # cheese + step bonus
