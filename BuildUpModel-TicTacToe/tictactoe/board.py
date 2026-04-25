"""
Tic Tac Toe: GameState implementation.

Board is a 3x3 list of ints: 0 = empty, +1 = X, -1 = O.
Moves are (row, col) tuples, 0-indexed.
"""

from __future__ import annotations
from typing import List, Optional, Tuple

from core.game import GameState

Move = Tuple[int, int]

_LINES: List[List[Tuple[int, int]]] = [
    # rows
    [(0,0),(0,1),(0,2)],
    [(1,0),(1,1),(1,2)],
    [(2,0),(2,1),(2,2)],
    # cols
    [(0,0),(1,0),(2,0)],
    [(0,1),(1,1),(2,1)],
    [(0,2),(1,2),(2,2)],
    # diagonals
    [(0,0),(1,1),(2,2)],
    [(0,2),(1,1),(2,0)],
]


class TTTState(GameState):
    def __init__(
        self,
        board: Optional[List[List[int]]] = None,
        player: int = 1,
    ) -> None:
        self._board: List[List[int]] = (
            board if board is not None else [[0] * 3 for _ in range(3)]
        )
        self._player = player

    # ---- GameState interface ------------------------------------------------

    @property
    def current_player(self) -> int:
        return self._player

    def get_legal_moves(self) -> List[Move]:
        return [
            (r, c)
            for r in range(3)
            for c in range(3)
            if self._board[r][c] == 0
        ]

    def apply_move(self, move: Move) -> TTTState:
        r, c = move
        new_board = [row[:] for row in self._board]
        new_board[r][c] = self._player
        return TTTState(new_board, -self._player)

    def is_terminal(self) -> bool:
        return self.get_winner() is not None or len(self.get_legal_moves()) == 0

    def get_winner(self) -> Optional[int]:
        for line in _LINES:
            vals = [self._board[r][c] for r, c in line]
            s = sum(vals)
            if s == 3:
                return 1
            if s == -3:
                return -1
        return None

    def evaluate(self) -> float:
        w = self.get_winner()
        if w == 1:
            return 1.0
        if w == -1:
            return -1.0
        return 0.0

    # ---- helpers ------------------------------------------------------------

    def __str__(self) -> str:
        sym = {0: ".", 1: "X", -1: "O"}
        return "\n".join(" ".join(sym[v] for v in row) for row in self._board)
