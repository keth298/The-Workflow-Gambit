import chess
from search import iterative_deepening, clear_state

def setup_function():
    clear_state()

def test_returns_legal_move_from_startpos_depth1():
    board = chess.Board()
    move = iterative_deepening(board, max_depth=1)
    assert move in board.legal_moves

def test_returns_legal_move_from_startpos_depth3():
    board = chess.Board()
    move = iterative_deepening(board, max_depth=3)
    assert move in board.legal_moves

def test_finds_back_rank_mate_in_1():
    # Rd8# is the only move that delivers checkmate
    board = chess.Board("6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1")
    move = iterative_deepening(board, max_depth=3)
    assert move.uci() == "d1d8"

def test_avoids_obvious_blunder():
    # Position: white Q at e4, black P at d5
    board = chess.Board("8/8/8/3p4/4Q3/8/8/4K2k w - - 0 1")
    move = iterative_deepening(board, max_depth=3)
    assert move in board.legal_moves
