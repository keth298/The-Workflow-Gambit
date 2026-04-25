#!/usr/bin/env python3
"""
Dummy UCI engine for testing — hangs forever on 'go' commands.
Used to test timeout handling.
"""
import sys
import time


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
            print("id name DummyTimeout")
            print("id author TestSuite")
            print("uciok")
            sys.stdout.flush()

        elif cmd == "isready":
            print("readyok")
            sys.stdout.flush()

        elif cmd.startswith("go"):
            # Never respond — simulates a hung engine
            time.sleep(9999)

        elif cmd == "quit":
            break


if __name__ == "__main__":
    main()
