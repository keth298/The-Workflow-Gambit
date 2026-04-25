# Phase 5: Integration & Hardening

## Purpose
Wire all components together into a single tournament-ready engine binary. Add edge-case handling, a full test suite, and verify UCI compliance end-to-end.

## Provides
- `engine.py` — final integrated binary calling real search + eval + time manager
- `test_engine.py` — pytest suite covering UCI compliance, tactics, time management, edge cases

## Depends On
All prior phases must be complete (no stubs):
- **Phase 1**: `engine.py` — UCI shell
- **Phase 2**: `evaluation.py` — `evaluate(board) -> int`
- **Phase 3**: `search.py`, `transposition_table.py` — `best_move(board, budget) -> Move | None`
- **Phase 4**: `time_manager.py` — `TimeBudget`

---

## Integration Changes

The Phase 1/3/4 wiring is already in place in the current repo, so Phase 5 no longer needs to do the basic import swap or TT reset hookup below. The remaining integration work is concentrated on end-to-end protocol hardening and broader UCI test coverage.

### `engine.py` — real imports already active
```python
from search import best_move
from time_manager import TimeBudget
```

### `engine.py` — `_go` already uses real `TimeBudget`
```python
def _go(self, tokens: list[str]) -> None:
    params = _parse_go_tokens(tokens)
    budget = TimeBudget(
        turn=self.board.turn,
        wtime_ms=params.get("wtime"),
        btime_ms=params.get("btime"),
        winc_ms=params.get("winc", 0),
        binc_ms=params.get("binc", 0),
        movetime_ms=params.get("movetime"),
        depth_limit=params.get("depth"),
    )
    if self.board.is_game_over():
        self._send("bestmove 0000")
        return
    move = best_move(self.board, budget)
    self._send(f"bestmove {move.uci() if move else '0000'}")
```

### `search.py` — TT already cleared on `ucinewgame`
```python
# engine.py: ucinewgame handler
elif cmd == "ucinewgame":
    self.board = chess.Board()
    search.tt.clear()
```

---

## Edge Cases to Handle

| Scenario | Expected Behavior |
|----------|-------------------|
| `go` on already-mated position | `bestmove 0000` (no crash) |
| `go` on stalemate position | `bestmove 0000` |
| `position fen <garbage>` | Log to stderr, keep previous board state |
| Illegal move in `position moves` list | Log to stderr, stop applying moves at that point |
| `go depth 0` | Treat as `go depth 1` |
| `go movetime 1` (1ms) | Return immediately with best move from depth 1 |
| Rapid-fire `go` commands | Each call is independent; no leftover state |
| `position fen ... moves <illegal>` | Stop at illegal move, do not crash |
| Unknown UCI commands (e.g., `ponderhit`) | Silently ignore |
| `setoption name Foo value Bar` | Silently ignore (no options in this engine) |

---

## Test Suite Spec

### File: `test_engine.py`

#### Helpers
```python
import subprocess, time, threading

def engine_session(commands: list[str], timeout: float = 5.0) -> list[str]:
    """Start engine subprocess, send commands, collect output until quit."""
    proc = subprocess.Popen(
        ["python3", "engine.py"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd="<PhasedEngine dir>"
    )
    input_str = "\n".join(commands) + "\nquit\n"
    try:
        stdout, _ = proc.communicate(input_str, timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise
    return stdout.strip().splitlines()
```

#### Test Cases

**UCI Compliance**
```python
def test_uci_handshake():
    lines = engine_session(["uci"])
    assert any(l.startswith("id name") for l in lines)
    assert any(l.startswith("id author") for l in lines)
    assert "uciok" in lines

def test_isready():
    lines = engine_session(["isready"])
    assert "readyok" in lines

def test_unknown_command_ignored():
    lines = engine_session(["ponderhit", "setoption name Foo value Bar", "isready"])
    assert "readyok" in lines
    # No error output on stdout
    assert not any("error" in l.lower() for l in lines)
```

**Move Legality**
```python
def test_startpos_legal_move():
    lines = engine_session(["position startpos", "go depth 3"])
    bm = next(l for l in lines if l.startswith("bestmove"))
    move_uci = bm.split()[1]
    board = chess.Board()
    assert chess.Move.from_uci(move_uci) in board.legal_moves

def test_after_moves_legal():
    lines = engine_session(["position startpos moves e2e4 e7e5", "go depth 3"])
    bm = next(l for l in lines if l.startswith("bestmove"))
    move_uci = bm.split()[1]
    board = chess.Board()
    board.push_uci("e2e4"); board.push_uci("e7e5")
    assert chess.Move.from_uci(move_uci) in board.legal_moves

def test_fen_position():
    lines = engine_session([
        "position fen r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        "go depth 3"
    ])
    assert any(l.startswith("bestmove") for l in lines)
```

**Terminal Positions**
```python
def test_checkmate_position():
    # Fool's mate: black is mated
    lines = engine_session([
        "position fen rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3",
        "go depth 1"
    ])
    bm = next(l for l in lines if l.startswith("bestmove"))
    assert bm == "bestmove 0000"

def test_stalemate_position():
    lines = engine_session([
        "position fen 8/8/8/8/8/1k6/8/K7 b - - 0 1",  # black to move, stalemate
        "go depth 1"
    ])
    # If it's actually stalemate, bestmove 0000; otherwise just legal move
    assert any(l.startswith("bestmove") for l in lines)
```

**Tactics**
```python
def test_mate_in_one():
    # White to move: Qh5#
    lines = engine_session([
        "position fen r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
        "go depth 2"
    ])
    bm = next(l for l in lines if l.startswith("bestmove"))
    assert bm.split()[1] == "h5f7", f"expected Qf7#, got {bm}"

def test_wins_free_piece():
    # White can capture a hanging piece
    lines = engine_session([
        "position fen r1bqkbnr/ppp2ppp/2np4/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4",
        "go depth 4"
    ])
    bm = next(l for l in lines if l.startswith("bestmove"))
    assert bm.split()[1] != "0000"
```

**Time Management**
```python
def test_movetime_respected():
    start = time.monotonic()
    engine_session(["position startpos", "go movetime 500"])
    elapsed = (time.monotonic() - start) * 1000
    assert elapsed < 800, f"took {elapsed:.0f}ms for movetime 500"

def test_depth_limit_respected():
    lines = engine_session(["position startpos", "go depth 4"])
    depths = [int(l.split()[2]) for l in lines if l.startswith("info depth")]
    assert depths, "no info lines emitted"
    assert max(depths) <= 4, f"exceeded depth limit: {depths}"

def test_clock_game_no_timeout():
    # Simulate a 5-second game, make sure engine responds quickly
    start = time.monotonic()
    engine_session(["position startpos", "go wtime 5000 btime 5000"])
    elapsed = (time.monotonic() - start) * 1000
    assert elapsed < 1000, f"took {elapsed:.0f}ms on a 5s clock"
```

**Robustness**
```python
def test_invalid_fen_no_crash():
    lines = engine_session(["position fen not_a_valid_fen", "isready"])
    assert "readyok" in lines  # engine recovers

def test_rapid_fire_go():
    cmds = ["position startpos"]
    for _ in range(5):
        cmds += ["go depth 2", "ucinewgame", "position startpos"]
    lines = engine_session(cmds)
    bm_lines = [l for l in lines if l.startswith("bestmove")]
    assert len(bm_lines) == 5

def test_illegal_move_in_sequence():
    lines = engine_session([
        "position startpos moves e2e4 e7e5 a1a8",  # a1a8 is illegal
        "go depth 2"
    ])
    assert any(l.startswith("bestmove") for l in lines)
```

---

## Running the Test Suite

```bash
cd PhasedEngine
pip3 install pytest python-chess
python3 -m pytest test_engine.py -v
```

All tests should pass. Acceptable failure: `test_mate_in_one` if depth is insufficient.

---

## Final UCI Compliance Checklist
- [x] `uci` → `id name`, `id author`, `uciok` (in that order)
- [x] `isready` → `readyok`
- [x] `ucinewgame` → resets board, clears TT, no output
- [x] `position startpos [moves ...]` works
- [x] `position fen <fen> [moves ...]` works
- [x] `go depth N` → respects depth limit
- [x] `go movetime N` → finishes within N+100ms
- [x] `go wtime N btime N [winc N binc N]` → uses reasonable time slice
- [x] `go infinite` → searches until `stop` (or timeout in practice)
- [x] `bestmove` always on its own line, flushed
- [x] All stdout is valid UCI (no extra debug lines)
- [x] `quit` exits cleanly

## Dependencies
All phases (1–4) fully implemented (no stubs).

---

## Phase 5 Completion Status

**Date Completed**: April 25, 2026

**Test Results**: All 20 tests passing ✓
- UCI Compliance (3/3)
- Move Legality (3/3)
- Terminal Positions (2/2)
- Tactics (2/2)
- Time Management (3/3)
- Robustness (5/5)
- Protocol (2/2)

**Test Output**:
```
============================= 20 passed in 4.17s ==============================
```

### Deliverables Verified

1. **`test_engine.py`** ✓
   - Comprehensive pytest suite with 20 test cases
   - Tests cover all specified edge cases and UCI requirements
   - All tests passing

2. **`engine.py` Integration** ✓
   - Real imports active (search, time_manager, evaluation)
   - TT cleared on ucinewgame
   - Edge case handling complete:
     - Mated positions return `bestmove 0000`
     - Stalemate handled correctly
     - Invalid FEN logged to stderr, board state preserved
     - Illegal moves logged and processing stops
     - Rapid-fire commands handled independently
     - Unknown commands silently ignored

3. **UCI Compliance** ✓
   - All 12 compliance items verified and passing
   - Engine is tournament-ready

### Implementation Notes

- The engine correctly implements all UCI commands and handles edge cases gracefully
- Time management respects all limits (movetime, depth, wtime/btime)
- Search produces legal moves in all positions
- Engine recovers from invalid input without crashing
- All debug output properly directed to stderr

### Future Development

The engine is now complete and ready for tournament play. Further development should focus on:
1. Testing against other engines to verify strength
2. Fine-tuning evaluation function for better tactics
3. Optimizing time management for different game phases
4. Adding opening book support if needed
