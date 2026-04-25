"""
Checkers CLI.

Human = b/B (player -1, moves toward row 0).
AI    = r/R (player +1, moves toward row 7), goes first.

Move input: space-separated row-col pairs.
  Simple:    "2 1 3 2"           (from row2,col1 to row3,col2)
  Jump:      "2 1 4 3"
  Multi-jump:"2 1 4 3 6 1"
"""

from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from checkers.board import CheckersState
from core.engine import MinimaxEngine

SEARCH_DEPTH = 6


def _parse_move(text: str, legal: list):
    try:
        nums = text.strip().split()
        if len(nums) < 4 or len(nums) % 2 != 0:
            return None
        coords = tuple(
            (int(nums[i]), int(nums[i + 1])) for i in range(0, len(nums), 2)
        )
        return coords if coords in legal else None
    except ValueError:
        return None


def _prompt_move(state: CheckersState):
    legal = state.get_legal_moves()
    print("Legal moves:")
    for m in legal:
        print("  " + "  ->  ".join(f"({r},{c})" for r, c in m))
    while True:
        raw = input("Your move (row col pairs): ").strip()
        move = _parse_move(raw, legal)
        if move is not None:
            return move
        print("  Invalid or illegal — try again.")


def main() -> None:
    state = CheckersState()
    engine = MinimaxEngine(max_depth=SEARCH_DEPTH)

    print("=== Checkers (English Draughts) ===")
    print(f"AI = r/R (+1), moves down.  You = b/B (-1), moves up.  Depth={SEARCH_DEPTH}\n")

    while not state.is_terminal():
        print(state)
        print()

        if state.current_player == 1:
            print("AI thinking...")
            move = engine.get_best_move(state)
            print(f"AI plays: {move}\n")
        else:
            move = _prompt_move(state)

        state = state.apply_move(move)

    print(state)
    winner = state.get_winner()
    if winner == 1:
        print("\nAI (r) wins!")
    elif winner == -1:
        print("\nYou (b) win!")
    else:
        print("\nDraw!")


if __name__ == "__main__":
    main()
