#!/usr/bin/env python3
"""
Dummy UCI engine for testing — always plays the first legal move.

Deterministic, useful for golden-test comparisons.
"""
import sys

import chess


def main():
    board = chess.Board()

    while True:
        try:
            line = sys.stdin.readline()
        except EOFError:
            break
        if not line:
            break
        cmd = line.strip()

        if cmd == "uci":
            print("id name DummyFirst")
            print("id author TestSuite")
            print("uciok")
            sys.stdout.flush()

        elif cmd == "isready":
            print("readyok")
            sys.stdout.flush()

        elif cmd == "ucinewgame":
            board = chess.Board()

        elif cmd.startswith("position"):
            board = chess.Board()
            parts = cmd.split()
            if "moves" in parts:
                moves_idx = parts.index("moves")
                for uci_move in parts[moves_idx + 1:]:
                    try:
                        board.push_uci(uci_move)
                    except Exception:
                        pass

        elif cmd.startswith("go"):
            moves = list(board.legal_moves)
            if moves:
                move = moves[0]
                print(f"bestmove {move.uci()}")
            else:
                print("bestmove (none)")
            sys.stdout.flush()

        elif cmd == "quit":
            break


if __name__ == "__main__":
    main()
