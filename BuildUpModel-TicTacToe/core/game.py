"""
Abstract base classes for the game engine framework.

Convention:
  current_player is always +1 (first player / maximizer)
                           or -1 (second player / minimizer).
  evaluate() always returns a score from the perspective of player +1.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, List, Optional


class GameState(ABC):
    """Immutable game-state snapshot. apply_move() returns a new instance."""

    @property
    @abstractmethod
    def current_player(self) -> int:
        """Who moves next: +1 or -1."""

    @abstractmethod
    def get_legal_moves(self) -> List[Any]:
        """All moves available to current_player."""

    @abstractmethod
    def apply_move(self, move: Any) -> GameState:
        """Return the state that results from current_player making move."""

    @abstractmethod
    def is_terminal(self) -> bool:
        """True when the game is over (win, loss, or draw)."""

    @abstractmethod
    def get_winner(self) -> Optional[int]:
        """Return +1, -1, or 0 (draw). None if the game is not over."""

    @abstractmethod
    def evaluate(self) -> float:
        """
        Static evaluation of this position from player +1's perspective.
        Called only at terminal nodes or depth-limit leaves.
        """
