# Phase 1: UCI Protocol Shell

## Purpose
Implement the engine's entire UCI I/O layer. This is the entry point — it reads stdin, manages board state, and dispatches to search. All other phases are dependencies that can be stubbed while building this.

## Provides
A runnable `engine.py` that:
- Speaks the full UCI protocol on stdin/stdout
- Maintains board state across commands
- Calls `search.best_move(board, budget)` and outputs the result
- Flushes stdout after every response; all debug output to stderr

## Depends On (can be stubbed)

**`search.best_move`** — stub with first legal move:
```python
# search.py stub for Phase 1 development
import chess
def best_move(board: chess.Board, budget) -> chess.Move | None:
    moves = list(board.legal_moves)
    return moves[0] if moves else None
```

**`time_manager.TimeBudget`** — stub with a simple object:
```python
# time_manager.py stub for Phase 1 development
class TimeBudget:
    def __init__(self, **kwargs): pass
    def should_stop(self) -> bool: return False
```

---

## Implementation Spec

### File: `engine.py`

```
UCIEngine
├── board: chess.Board
├── run() → reads lines from stdin indefinitely
├── _handle(line: str) → dispatches on first token
├── _send(msg: str) → print(msg, flush=True)
└── _log(msg: str) → print(msg, file=stderr, flush=True)
```

### Command Handlers

**`uci`**
```
→ "id name PhasedEngine"
→ "id author JD"
→ "uciok"
```

**`isready`**
```
→ "readyok"
```

**`ucinewgame`**
```
self.board = chess.Board()
(no output)
```

**`position [startpos | fen <fen>] [moves <m1> <m2> ...]`**
```
if startpos:
    self.board = chess.Board()
elif fen:
    collect tokens until "moves" keyword → join as FEN string → chess.Board(fen)
    on exception: log to stderr, return without modifying board

for each move token after "moves":
    move = chess.Move.from_uci(token)
    if move in board.legal_moves: board.push(move)
    else: log illegal move to stderr, stop applying moves
```

**`go [wtime N] [btime N] [winc N] [binc N] [movetime N] [depth N] [infinite] [...]`**
```
Parse tokens into dict of keyword → int value (unknown tokens ignored)
budget = TimeBudget(
    wtime_ms  = params.get("wtime"),
    btime_ms  = params.get("btime"),
    winc_ms   = params.get("winc", 0),
    binc_ms   = params.get("binc", 0),
    movetime_ms = params.get("movetime"),
    depth_limit = params.get("depth"),
    turn = board.turn,
)

if board.is_game_over():
    send "bestmove 0000"
    return

move = search.best_move(board, budget)
send f"bestmove {move.uci() if move else '0000'}"
```

**`quit`**
```
sys.exit(0)
```

### `go` Token Parsing
```python
params = {}
i = 0
while i < len(tokens):
    key = tokens[i]
    if i + 1 < len(tokens):
        try:
            params[key] = int(tokens[i + 1])
            i += 2
            continue
        except ValueError:
            pass
    i += 1
```

---

## Verification

```bash
pip3 install python-chess

printf 'uci\nisready\nquit\n' | python3 engine.py
# Expected:
# id name PhasedEngine
# id author JD
# uciok
# readyok

printf 'ucinewgame\nposition startpos\ngo depth 4\nquit\n' | python3 engine.py
# Expected: bestmove <e2e4 or similar legal move>

printf 'position startpos moves e2e4 e7e5\ngo depth 4\nquit\n' | python3 engine.py
# Expected: bestmove <legal move for white>

printf 'position fen 8/8/8/8/8/8/8/4K2k w - - 0 1\ngo depth 1\nquit\n' | python3 engine.py
# Expected: bestmove <legal king move>

# Game over position (stalemate/checkmate) → bestmove 0000
printf 'position fen 8/8/8/8/8/8/7Q/7K b - - 0 1\ngo depth 1\nquit\n' | python3 engine.py
```

---

## Completion Checklist
- [ ] All 6 required UCI commands implemented
- [ ] `position fen` and `position startpos` both work
- [ ] `moves` list applied correctly after position
- [ ] Illegal/malformed moves logged to stderr, board unchanged
- [ ] `go` parses all time-control tokens without crashing
- [ ] `bestmove 0000` on game-over positions
- [ ] Flush on every `_send` call
- [ ] No UCI output on stderr (only debug logs)
