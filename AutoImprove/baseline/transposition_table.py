from __future__ import annotations

import chess
from typing import Optional, Tuple

TT_EXACT = 0
TT_LOWER = 1
TT_UPPER = 2

TTEntry = Tuple[int, int, int, Optional[chess.Move]]


class TranspositionTable:
    def __init__(self) -> None:
        self._table: dict[int, TTEntry] = {}

    def get(self, key: int) -> TTEntry | None:
        return self._table.get(key)

    def put(self, key: int, score: int, depth: int, flag: int, best_move: chess.Move | None) -> None:
        existing = self._table.get(key)
        if existing is None or depth >= existing[1]:
            self._table[key] = (score, depth, flag, best_move)

    def clear(self) -> None:
        self._table.clear()
