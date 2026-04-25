import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engines', 'variants', 'random_blunder', 'engine.py')


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
    assert any(l.startswith('id name RandomBlunderEngine') for l in lines)


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


def test_random_blunder_skips_search_on_multiple_of_5():
    # fullmove=5: engine returns random move without searching (no info depth lines)
    fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 5'
    lines = _run([f'position fen {fen}', 'go depth 5', 'quit'])
    info_lines = [l for l in lines if l.startswith('info depth')]
    assert len(info_lines) == 0
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board(fen)
    move = chess.Move.from_uci(bm[0].split()[1])
    assert move in board.legal_moves
