from __future__ import annotations

import time

import chess

DEFAULT_MOVETIME_MS = 1000
MOVES_REMAINING = 40
SAFETY_MARGIN_MS = 50
OVERHEAD_MS = 20


class TimeBudget:
    def __init__(
        self,
        turn: chess.Color,
        wtime_ms: int | None = None,
        btime_ms: int | None = None,
        winc_ms: int = 0,
        binc_ms: int = 0,
        movetime_ms: int | None = None,
        depth_limit: int | None = None,
    ) -> None:
        self.turn = turn
        self.wtime_ms = wtime_ms
        self.btime_ms = btime_ms
        self.winc_ms = winc_ms or 0
        self.binc_ms = binc_ms or 0
        self.movetime_ms = movetime_ms
        self._depth_limit = max(1, depth_limit) if depth_limit is not None else None
        self._allocated_ms = self._compute_allocated_ms()
        self._start: float | None = None

    def _compute_allocated_ms(self) -> int:
        if self._depth_limit is not None:
            return 0

        if self.movetime_ms is not None:
            return max(self.movetime_ms - OVERHEAD_MS, 10)

        remaining = self.wtime_ms if self.turn == chess.WHITE else self.btime_ms
        inc = self.winc_ms if self.turn == chess.WHITE else self.binc_ms

        if remaining is not None:
            base = remaining // MOVES_REMAINING
            allocated = base + inc - OVERHEAD_MS
            allocated = min(allocated, max(remaining - SAFETY_MARGIN_MS, 0), remaining // 5)
            return max(allocated, 10)

        return max(DEFAULT_MOVETIME_MS - OVERHEAD_MS, 10)

    def allocated_ms(self) -> int:
        return self._allocated_ms

    def depth_limit(self) -> int | None:
        return self._depth_limit

    def should_stop(self) -> bool:
        if self._allocated_ms == 0 or self._start is None:
            return False
        elapsed_ms = (time.monotonic() - self._start) * 1000
        return elapsed_ms >= self._allocated_ms

    def start(self) -> None:
        self._start = time.monotonic()
