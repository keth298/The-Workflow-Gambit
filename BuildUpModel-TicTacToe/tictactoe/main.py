"""
Tic Tac Toe CLI.

Human plays O (-1); AI plays X (+1) and goes first.
Run from BuildUpModel/: python -m tictactoe.main
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tictactoe.board import TTTState
from core.engine import MinimaxEngine


def _prompt_move(state: TTTState):
    while True:
        raw = input("Your move (row col, 0-indexed, e.g. '1 2'): ").strip()
        try:
            r, c = map(int, raw.split())
            if (r, c) in state.get_legal_moves():
                return (r, c)
            print("  Illegal move — square occupied or out of range.")
        except (ValueError, TypeError):
            print("  Enter two integers separated by a space.")


def main() -> None:
    state = TTTState()
    engine = MinimaxEngine()  # no depth limit — TTT tree is tiny

    print("=== Tic Tac Toe ===")
    print("AI = X (+1) moves first.  You = O (-1).")
    print("Squares are (row col) from (0 0) top-left to (2 2) bottom-right.\n")

    while not state.is_terminal():
        print(state)
        print()

        if state.current_player == 1:
            move = engine.get_best_move(state)
            print(f"AI plays: {move}\n")
        else:
            move = _prompt_move(state)

        state = state.apply_move(move)

    print(state)
    winner = state.get_winner()
    if winner == 1:
        print("\nAI (X) wins!")
    elif winner == -1:
        print("\nYou (O) win!")
    else:
        print("\nDraw!")


if __name__ == "__main__":
    main()
