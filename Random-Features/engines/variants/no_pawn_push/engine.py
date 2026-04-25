import sys
import os
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.join(_HERE, '..', '..', 'base')
sys.path.insert(0, _HERE)
sys.path.insert(1, _BASE)

import chess
from search import iterative_deepening, clear_state


def _log(*args):
    print(*args, file=sys.stderr, flush=True)


def _handle_position(board, line):
    parts = line.split()
    idx = 1
    if idx >= len(parts):
        return
    if parts[idx] == 'startpos':
        board.set_fen(chess.STARTING_FEN)
        idx = 2
    elif parts[idx] == 'fen':
        fen = ' '.join(parts[idx + 1: idx + 7])
        board.set_fen(fen)
        idx += 7
    if idx < len(parts) and parts[idx] == 'moves':
        for uci in parts[idx + 1:]:
            try:
                board.push_uci(uci)
            except Exception as e:
                _log(f'illegal move in position: {uci} ({e})')
                break


def _handle_go(board, line):
    parts = line.split()
    max_depth = None
    deadline = None
    if 'infinite' in parts:
        deadline = time.time() + 30.0
    elif 'depth' in parts:
        max_depth = int(parts[parts.index('depth') + 1])
    elif 'movetime' in parts:
        ms = int(parts[parts.index('movetime') + 1])
        deadline = time.time() + ms / 1000.0
    else:
        color_key = 'wtime' if board.turn == chess.WHITE else 'btime'
        inc_key   = 'winc'  if board.turn == chess.WHITE else 'binc'
        if color_key in parts:
            remaining = int(parts[parts.index(color_key) + 1])
            inc = int(parts[parts.index(inc_key) + 1]) if inc_key in parts else 0
            think_ms = max(remaining * 0.05 + inc * 0.5, 100)
            deadline = time.time() + think_ms / 1000.0
        else:
            deadline = time.time() + 1.0
    return iterative_deepening(board, max_depth=max_depth, deadline=deadline)


def uci_loop():
    board = chess.Board()
    while True:
        try:
            line = input().strip()
        except EOFError:
            break
        _log(f'< {line}')
        if line == 'uci':
            print('id name NoPawnPushEngine')
            print('id author Point72Hackathon')
            print('uciok')
            sys.stdout.flush()
        elif line == 'isready':
            print('readyok')
            sys.stdout.flush()
        elif line == 'ucinewgame':
            board = chess.Board()
            clear_state()
        elif line.startswith('position'):
            _handle_position(board, line)
        elif line.startswith('go'):
            try:
                move = _handle_go(board, line)
                if move:
                    print(f'bestmove {move.uci()}')
                    sys.stdout.flush()
                    _log(f'> bestmove {move.uci()}')
                else:
                    print('bestmove 0000')
                    sys.stdout.flush()
            except Exception as e:
                _log(f'error in go handler: {e}')
                print('bestmove 0000')
                sys.stdout.flush()
        elif line == 'stop':
            pass
        elif line == 'quit':
            break


if __name__ == '__main__':
    uci_loop()
