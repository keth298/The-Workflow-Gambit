"""
Generic minimax engine with alpha-beta pruning.

Works for any GameState subclass. Player +1 maximises; player -1 minimises.
"""

from __future__ import annotations
import math
from typing import Any, Optional

from .game import GameState


class MinimaxEngine:
    def __init__(self, max_depth: Optional[int] = None) -> None:
        self.max_depth = max_depth

    def get_best_move(self, state: GameState) -> Any:
        """Return the move that leads to the best outcome for current_player."""
        maximizing = state.current_player == 1
        best_move: Any = None
        best_score = -math.inf if maximizing else math.inf

        for move in state.get_legal_moves():
            child = state.apply_move(move)
            score = self._minimax(child, -math.inf, math.inf, not maximizing, depth=1)

            if maximizing and score > best_score:
                best_score, best_move = score, move
            elif not maximizing and score < best_score:
                best_score, best_move = score, move

        return best_move

    def _minimax(
        self,
        state: GameState,
        alpha: float,
        beta: float,
        maximizing: bool,
        depth: int,
    ) -> float:
        if state.is_terminal():
            return state.evaluate()
        if self.max_depth is not None and depth >= self.max_depth:
            return state.evaluate()

        if maximizing:
            value = -math.inf
            for move in state.get_legal_moves():
                value = max(value, self._minimax(
                    state.apply_move(move), alpha, beta, False, depth + 1
                ))
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value
        else:
            value = math.inf
            for move in state.get_legal_moves():
                value = min(value, self._minimax(
                    state.apply_move(move), alpha, beta, True, depth + 1
                ))
                beta = min(beta, value)
                if alpha >= beta:
                    break
            return value
