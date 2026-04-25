import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', 'engines', 'base', 'engine.py')


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
    assert any(l.startswith('id name') for l in lines)
    assert any(l.startswith('id author') for l in lines)


def test_isready_response():
    lines = _run(['isready', 'quit'])
    assert 'readyok' in lines


def test_bestmove_startpos_depth5():
    lines = _run(['position startpos', 'go depth 5', 'quit'], timeout=60)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    move_str = bm[0].split()[1]
    board = chess.Board()
    move = chess.Move.from_uci(move_str)
    assert move in board.legal_moves


def test_bestmove_after_moves():
    lines = _run(['position startpos moves e2e4 e7e5', 'go depth 3', 'quit'], timeout=30)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    board.push_uci('e2e4')
    board.push_uci('e7e5')
    move = chess.Move.from_uci(bm[0].split()[1])
    assert move in board.legal_moves


def test_ucinewgame_resets_state():
    lines = _run(['ucinewgame', 'position startpos', 'go depth 2', 'quit'])
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1


def test_no_uci_output_on_stderr_leak():
    result = subprocess.run(
        [sys.executable, ENGINE],
        input='uci\nisready\nquit\n',
        capture_output=True, text=True, timeout=10
    )
    # stdout must contain only UCI lines, stderr is logs (anything goes there)
    for line in result.stdout.strip().split('\n'):
        if line:
            assert any(line.startswith(p) for p in ('id ', 'uciok', 'readyok', 'bestmove', 'info'))
