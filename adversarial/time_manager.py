from typing import Optional, Tuple


class TimeManager:
    def allocate(
        self,
        wtime: Optional[int] = None,
        btime: Optional[int] = None,
        winc: int = 0,
        binc: int = 0,
        movestogo: Optional[int] = None,
        movetime: Optional[int] = None,
        depth: Optional[int] = None,
        side_to_move: bool = True,  # True = White
    ) -> Tuple[Optional[int], Optional[int]]:
        """Return (target_ms, max_ms). None means search to depth, not time."""
        if depth is not None:
            return None, None

        if movetime is not None:
            return movetime, movetime

        remaining = (wtime if side_to_move else btime) or 0
        increment = (winc if side_to_move else binc) or 0

        if movestogo is not None and movestogo > 0:
            target = remaining // movestogo + increment
        else:
            target = remaining // 30 + increment

        max_ms = min(remaining - 50, target * 3)
        max_ms = max(max_ms, 1)
        target = max(target, 1)
        return target, max_ms
