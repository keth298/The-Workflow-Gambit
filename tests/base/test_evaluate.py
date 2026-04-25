import chess
from evaluate import evaluate


def test_starting_position_is_zero():
    board = chess.Board()
    assert evaluate(board) == 0


def test_missing_white_pawn_is_negative():
    board = chess.Board()
    board.remove_piece_at(chess.E2)
    assert evaluate(board) < 0


def test_missing_black_pawn_is_positive():
    board = chess.Board()
    board.remove_piece_at(chess.E7)
    assert evaluate(board) > 0


def test_white_up_queen_is_large_positive():
    board = chess.Board()
    board.remove_piece_at(chess.D8)
    assert evaluate(board) > 800


def test_checkmate_position_from_white_perspective():
    # Black is mated (white to move after delivering mate is not possible;
    # this is a position where black's king has no moves and is in check)
    # Use a known checkmated position: black is in checkmate, white just moved.
    # board.turn is black, board.is_checkmate() is True.
    board = chess.Board("r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4")
    assert board.is_checkmate()
    # Black (side to move) is mated → very negative score for black → large positive for white
    score = evaluate(board)
    assert score > 20000
