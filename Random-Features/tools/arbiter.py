#!/usr/bin/env python3
"""
Arbiter: run a 10-game match between two UCI engines.

Usage:
    python3 tools/arbiter.py engines/base/engine.py engines/variants/aggro_push/engine.py

Each game uses movetime 1000 ms per move. Colors alternate each game.
Prints per-game results and a final summary table.
"""

import argparse
import subprocess
import sys
import threading
import time


class Engine:
    def __init__(self, path):
        self.path = path
        self.name = path
        self.proc = subprocess.Popen(
            [sys.executable, path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._lock = threading.Lock()

    def send(self, line):
        self.proc.stdin.write(line + '\n')
        self.proc.stdin.flush()

    def readline(self, timeout=10.0):
        """Read one line with a deadline; returns '' on timeout."""
        result = []
        done = threading.Event()

        def _read():
            try:
                result.append(self.proc.stdout.readline())
            except Exception:
                result.append('')
            done.set()

        t = threading.Thread(target=_read, daemon=True)
        t.start()
        if not done.wait(timeout):
            return ''
        return result[0].rstrip('\n') if result else ''

    def read_until(self, token, timeout=10.0):
        """Read lines until one starts with token; return that line."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            remaining = deadline - time.time()
            line = self.readline(timeout=max(remaining, 0.1))
            if not line:
                break
            if line.startswith(token):
                return line
        return ''

    def init(self):
        """Handshake: uci → uciok, then isready → readyok."""
        self.send('uci')
        resp = self.read_until('uciok', timeout=5.0)
        # Extract id name if present (scan earlier lines won't work with
        # read_until, so just use path as fallback if already set)
        self.send('isready')
        self.read_until('readyok', timeout=5.0)

    def new_game(self):
        self.send('ucinewgame')
        self.send('isready')
        self.read_until('readyok', timeout=5.0)

    def get_move(self, position_cmd, movetime_ms=1000):
        """Send position + go movetime, return the bestmove string."""
        self.send(position_cmd)
        self.send(f'go movetime {movetime_ms}')
        line = self.read_until('bestmove', timeout=movetime_ms / 1000.0 + 5.0)
        if not line.startswith('bestmove'):
            return None
        parts = line.split()
        return parts[1] if len(parts) >= 2 else None

    def quit(self):
        try:
            self.send('quit')
            self.proc.wait(timeout=3.0)
        except Exception:
            self.proc.kill()


def play_game(white_engine, black_engine, movetime_ms=1000):
    """
    Play one game. Returns 'white', 'black', or 'draw'.
    """
    import chess

    board = chess.Board()
    white_engine.new_game()
    black_engine.new_game()

    move_history = []

    while not board.is_game_over(claim_draw=True):
        # Build position command
        if move_history:
            pos_cmd = 'position startpos moves ' + ' '.join(move_history)
        else:
            pos_cmd = 'position startpos'

        engine = white_engine if board.turn == chess.WHITE else black_engine
        move_str = engine.get_move(pos_cmd, movetime_ms)

        if move_str is None or move_str == '0000':
            # Engine resigned or timed out — other side wins
            return 'black' if board.turn == chess.WHITE else 'white'

        try:
            move = chess.Move.from_uci(move_str)
            if move not in board.legal_moves:
                # Illegal move — other side wins
                return 'black' if board.turn == chess.WHITE else 'white'
            board.push(move)
            move_history.append(move_str)
        except ValueError:
            return 'black' if board.turn == chess.WHITE else 'white'

        # Limit game length to avoid infinite loops (350 half-moves)
        if len(move_history) >= 350:
            return 'draw'

    outcome = board.outcome(claim_draw=True)
    if outcome is None:
        return 'draw'
    if outcome.winner is None:
        return 'draw'
    return 'white' if outcome.winner == chess.WHITE else 'black'


def run_match(path1, path2, num_games=10, movetime_ms=1000):
    import chess  # noqa: ensure available

    e1 = Engine(path1)
    e2 = Engine(path2)

    print(f'Initialising engines...')
    e1.init()
    e2.init()

    # Try to read id name by reinitialising — simpler: just use basename
    import os
    name1 = os.path.basename(os.path.dirname(path1)) or os.path.basename(path1)
    name2 = os.path.basename(os.path.dirname(path2)) or os.path.basename(path2)

    # Make names unique if identical
    if name1 == name2:
        name1 = name1 + '_A'
        name2 = name2 + '_B'

    print(f'Engine 1: {name1}  ({path1})')
    print(f'Engine 2: {name2}  ({path2})')
    print(f'Match: {num_games} games, {movetime_ms} ms/move\n')

    results = []  # list of ('white_name', 'black_name', result)

    for g in range(num_games):
        # Alternate colours every game
        if g % 2 == 0:
            white, black = e1, e2
            wname, bname = name1, name2
        else:
            white, black = e2, e1
            wname, bname = name2, name1

        result = play_game(white, black, movetime_ms)
        results.append((wname, bname, result))

        if result == 'white':
            winner = wname
            label = f'{wname} wins'
        elif result == 'black':
            winner = bname
            label = f'{bname} wins'
        else:
            label = 'Draw'

        print(f'Game {g + 1:2d}: {wname} (W) vs {bname} (B)  →  {label}')

    e1.quit()
    e2.quit()

    # Tally scores
    scores = {name1: 0.0, name2: 0.0}
    wins   = {name1: 0,   name2: 0}
    losses = {name1: 0,   name2: 0}
    draws  = {name1: 0,   name2: 0}

    for wname, bname, result in results:
        if result == 'white':
            scores[wname] += 1.0
            wins[wname]   += 1
            losses[bname] += 1
        elif result == 'black':
            scores[bname] += 1.0
            wins[bname]   += 1
            losses[wname] += 1
        else:
            scores[name1] += 0.5
            scores[name2] += 0.5
            draws[name1]  += 1
            draws[name2]  += 1

    col = max(len(name1), len(name2), 6)
    header = f"\n{'Engine':<{col}}  {'Score':>5}  {'Wins':>4}  {'Losses':>6}  {'Draws':>5}"
    sep    = '-' * len(header)
    print(sep)
    print(header)
    print(sep)
    for name in (name1, name2):
        print(
            f'{name:<{col}}  {scores[name]:>5.1f}  {wins[name]:>4}  '
            f'{losses[name]:>6}  {draws[name]:>5}'
        )
    print(sep)

    total = num_games
    print(f'\nTotal games: {total}')
    if scores[name1] > scores[name2]:
        print(f'Winner: {name1}')
    elif scores[name2] > scores[name1]:
        print(f'Winner: {name2}')
    else:
        print('Match drawn')


def main():
    parser = argparse.ArgumentParser(
        description='Run a UCI chess engine match.'
    )
    parser.add_argument('engine1', help='Path to first engine script')
    parser.add_argument('engine2', help='Path to second engine script')
    parser.add_argument(
        '--games', type=int, default=10,
        help='Number of games (default: 10, must be even)'
    )
    parser.add_argument(
        '--movetime', type=int, default=1000,
        help='Time per move in milliseconds (default: 1000)'
    )
    args = parser.parse_args()

    if args.games % 2 != 0:
        parser.error('--games must be even so colors are balanced')

    run_match(args.engine1, args.engine2, args.games, args.movetime)


if __name__ == '__main__':
    main()
