from rodents_revenge.game import BLOCK, CHEESE, EMPTY, GameState, WALL, TRAP_SCORE


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


def test_level_increases_when_all_cats_removed() -> None:
    state = blank_state()
    state.cats = []

    state.step_cats()

    assert state.level == 2
