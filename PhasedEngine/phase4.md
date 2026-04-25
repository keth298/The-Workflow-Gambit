# Phase 4: Time Manager

## Purpose
Parse the `go` command's time parameters and provide a clean stopping interface to the search. The search polls `budget.should_stop()` every N nodes to know when to abort.

## Provides
```python
# time_manager.py
class TimeBudget:
    def __init__(
        self,
        turn: chess.Color,               # whose turn (chess.WHITE or chess.BLACK)
        wtime_ms: int | None = None,
        btime_ms: int | None = None,
        winc_ms: int = 0,
        binc_ms: int = 0,
        movetime_ms: int | None = None,
        depth_limit: int | None = None,
    ) -> None: ...

    def allocated_ms(self) -> int:
        """Milliseconds allocated for this move (0 = unlimited)."""

    def depth_limit(self) -> int | None:
        """Max depth to search, or None if time-based."""

    def should_stop(self) -> bool:
        """True when elapsed time >= allocated time. Fast; call every 1024 nodes."""

    def start(self) -> None:
        """Record start time. Called once before search begins."""
```

## Depends On
Only `time` (stdlib) and `chess` (for `chess.Color`). No other phases needed.

---

## Implementation Spec

### File: `time_manager.py`

### Time Allocation Logic

**Priority order:**
1. If `movetime_ms` given → use exactly that value (minus 20ms safety margin)
2. If `wtime_ms`/`btime_ms` given → compute time share
3. Otherwise → use `DEFAULT_MOVETIME_MS = 1000`

**Time share formula (for clock-based games):**
```python
MOVES_REMAINING = 40          # assume 40 moves left in game
SAFETY_MARGIN_MS = 50         # never go below this much remaining on clock
OVERHEAD_MS = 20              # network/protocol overhead buffer

remaining = wtime_ms if turn == WHITE else btime_ms
inc = winc_ms if turn == WHITE else binc_ms

# Base allocation: remaining / MOVES_REMAINING
base = remaining // MOVES_REMAINING

# Add increment (but keep safety margin)
allocated = base + inc - OVERHEAD_MS

# Never allocate more than 1/5 of remaining clock (avoid flag risk)
allocated = min(allocated, remaining // 5)

# Never go below 10ms
allocated = max(allocated, 10)
```

**`depth_limit` priority:**
- If `depth_limit` was provided in `go` command → set max depth; ignore time
- If `movetime_ms` or clock → use time, no depth cap (set to `MAX_DEPTH = 64`)

### `should_stop` Implementation
```python
import time

def start(self) -> None:
    self._start = time.monotonic()

def should_stop(self) -> bool:
    if self._allocated_ms == 0:
        return False  # unlimited (depth-only mode)
    elapsed_ms = (time.monotonic() - self._start) * 1000
    return elapsed_ms >= self._allocated_ms
```

> **Note for search integration:** Check `should_stop()` every 1024 nodes evaluated (not every node — the `monotonic()` call has overhead). Use a node counter modulo 1024.

---

## Verification

```python
import time, chess
from time_manager import TimeBudget

# movetime=500 → allocated ~480ms
b = TimeBudget(turn=chess.WHITE, movetime_ms=500)
b.start()
assert b.allocated_ms() == 480
assert not b.should_stop()
time.sleep(0.5)
assert b.should_stop()

# depth only → no time limit
b2 = TimeBudget(turn=chess.WHITE, depth_limit=5)
b2.start()
assert b2.depth_limit() == 5
assert not b2.should_stop()  # never stops on time
time.sleep(5)
assert not b2.should_stop()

# clock game: 10s remaining, no increment
b3 = TimeBudget(turn=chess.WHITE, wtime_ms=10000, btime_ms=10000)
b3.start()
alloc = b3.allocated_ms()
assert 100 <= alloc <= 2000, f"got {alloc}ms from 10s clock"

# clock game: 1min + 2s increment
b4 = TimeBudget(turn=chess.BLACK, wtime_ms=60000, btime_ms=60000, winc_ms=2000, binc_ms=2000)
b4.start()
alloc = b4.allocated_ms()
assert alloc > 1500, f"should get more with increment, got {alloc}ms"
```

Automated verification now lives in `test_time_manager.py`:

```bash
cd PhasedEngine
python3 -m pytest test_time_manager.py -q
```

---

## Completion Checklist
- [x] `TimeBudget.__init__` accepts all `go` time parameters
- [x] `allocated_ms()` correct for movetime / clock / depth-only cases
- [x] `should_stop()` uses `time.monotonic()` (not `time.time()`)
- [x] `start()` records start time before search begins
- [x] Safety margin prevents flagging (never > 1/5 of remaining clock)
- [x] Minimum allocation of 10ms enforced
- [x] depth-only mode: `should_stop()` always returns False

## Future Plan Impact
No search-side API changes are needed for Phase 5. The current `TimeBudget` implementation matches the search contract, now has dedicated pytest coverage in `test_time_manager.py`, and is already exercised through real `go depth`, `go movetime`, and clock-based searches.

## Dependencies
None (standalone component).
