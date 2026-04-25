import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engines', 'variants', 'king_walk', 'engine.py')


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
    assert any(l.startswith('id name KingWalkEngine') for l in lines)


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


def test_king_walk_does_not_castle():
    fen = 'r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4'
    lines = _run([f'position fen {fen}', 'go depth 1', 'quit'])
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board(fen)
    move = chess.Move.from_uci(bm[0].split()[1])
    assert not board.is_castling(move)
