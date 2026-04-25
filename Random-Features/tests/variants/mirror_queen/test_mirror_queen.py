import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engines', 'variants', 'mirror_queen', 'engine.py')


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
    assert any(l.startswith('id name MirrorQueenEngine') for l in lines)


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


def test_mirror_queen_responds_with_queen():
    # After 1.e4 d5 2.exd5 Qxd5, black queen is on d5 (last move).
    # White must respond with a queen move.
    moves_str = 'e2e4 d7d5 e4d5 d8d5'
    lines = _run([f'position startpos moves {moves_str}', 'go depth 1', 'quit'])
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    for m in moves_str.split():
        board.push_uci(m)
    move = chess.Move.from_uci(bm[0].split()[1])
    piece = board.piece_at(move.from_square)
    assert piece is not None
    assert piece.piece_type == chess.QUEEN
