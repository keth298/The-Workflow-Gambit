#!/usr/bin/env python3
"""
Dummy UCI engine for testing — always returns an illegal move.
Used to test illegal-move forfeiture logic.
"""
import sys


def main():
    while True:
        try:
            line = sys.stdin.readline()
        except EOFError:
            break
        if not line:
            break
        cmd = line.strip()

        if cmd == "uci":
            print("id name DummyIllegal")
            print("id author TestSuite")
            print("uciok")
            sys.stdout.flush()

        elif cmd == "isready":
            print("readyok")
            sys.stdout.flush()

        elif cmd.startswith("go"):
            # Always return an impossible move
            print("bestmove a1a1")
            sys.stdout.flush()

        elif cmd == "quit":
            break


if __name__ == "__main__":
    main()
