import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engines', 'variants', 'first_rank_lock', 'engine.py')


def _run(commands, timeout=30):
    result = subprocess.run(
        [sys.executable, ENGINE],
        input='\n'.join(commands) + '\n',
        capture_output=True, text=True, timeout=timeout
    )
    return [l for l in result.stdout.strip().split('\n') if l]


def test_uci_response():
    lines = _run(['uci', 'quit'])
    assert 'uciok' in lines
    assert any(l.startswith('id name FirstRankLockEngine') for l in lines)


def test_isready_response():
    lines = _run(['isready', 'quit'])
    assert 'readyok' in lines


def test_bestmove_startpos():
    lines = _run(['position startpos', 'go depth 3', 'quit'], timeout=60)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    move = chess.Move.from_uci(bm[0].split()[1])
    assert move in board.legal_moves


def test_first_rank_lock_no_piece_leaves_back_rank():
    lines = _run(['position startpos', 'go depth 1', 'quit'])
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    move = chess.Move.from_uci(bm[0].split()[1])
    from_rank = chess.square_rank(move.from_square)
    to_rank = chess.square_rank(move.to_square)
    assert not (from_rank == 0 and to_rank != 0)
