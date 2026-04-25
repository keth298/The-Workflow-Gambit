# Phase 3: Search Engine

## Purpose
Find the best move using iterative-deepening alpha-beta search with quiescence, transposition table, and move ordering. This is the engine's core "brain."

## Provides
```python
# search.py
def best_move(board: chess.Board, budget: "TimeBudget") -> chess.Move | None
```
- Returns the best legal move found, or `None` if the position is already terminal
- Also emits `info depth N score cp X nodes N pv <move>` lines to stdout during search (UCI info)

```python
# transposition_table.py
class TranspositionTable:
    def get(self, key: int) -> tuple[int, int, int] | None  # (score, depth, flag)
    def put(self, key: int, score: int, depth: int, flag: int) -> None
    def clear(self) -> None

TT_EXACT = 0
TT_LOWER = 1   # beta cutoff (score is a lower bound)
TT_UPPER = 2   # alpha cutoff (score is an upper bound)
```

## Depends On

**Phase 2 — `evaluate(board) -> int`**
Stub for isolated development:
```python
# evaluation.py stub
import chess
def evaluate(board: chess.Board) -> int:
    return 0
```

**Phase 4 — `TimeBudget`**
Stub for isolated development:
```python
# time_manager.py stub
class TimeBudget:
    def should_stop(self) -> bool: return False
    def depth_limit(self) -> int | None: return None
    def start(self) -> None: pass
```

---

## Implementation Spec

### Constants
```python
MATE_SCORE    = 30_000   # returned when side-to-move is mated (at ply 0)
MAX_DEPTH     = 64       # hard ceiling for iterative deepening
INF           = 32_000
```

### File: `transposition_table.py`

Simple dict-based TT. Unbounded size (can add LRU eviction later if needed).

```python
class TranspositionTable:
    def __init__(self) -> None:
        self._table: dict[int, tuple[int, int, int]] = {}

    def get(self, key: int) -> tuple[int, int, int] | None:
        return self._table.get(key)

    def put(self, key: int, score: int, depth: int, flag: int) -> None:
        existing = self._table.get(key)
        # Only overwrite if new entry searched deeper
        if existing is None or depth >= existing[1]:
            self._table[key] = (score, depth, flag)

    def clear(self) -> None:
        self._table.clear()
```

### File: `search.py`

#### Move Ordering (MVV-LVA)
```python
MVV_LVA_SCORES = {
    (chess.QUEEN,  chess.PAWN):   55,
    (chess.QUEEN,  chess.KNIGHT): 54,
    ...  # attacker, victim → priority score
}

def _order_moves(board: chess.Board, moves: list[chess.Move], tt_move: chess.Move | None) -> list[chess.Move]:
    """Sort: TT move first, then captures (MVV-LVA), then quiet moves."""
```

MVV-LVA priority = `victim_value * 10 - attacker_value` (higher = better capture).

Full priority order per move:
1. TT move (score = 20000)
2. Captures sorted by MVV-LVA (score = 10000 + mvv_lva)
3. Quiet moves (score = 0, no further sorting in Phase 3)

#### Alpha-Beta

```
alpha_beta(board, depth, alpha, beta, ply, nodes_ref) -> int

1. TT lookup: key = board.zobrist_hash()
   if entry exists and entry.depth >= depth:
     if flag == EXACT: return score
     if flag == LOWER: alpha = max(alpha, score)
     if flag == UPPER: beta = min(beta, score)
     if alpha >= beta: return score

2. Terminal checks:
   if board.is_checkmate(): return -MATE_SCORE + ply
   if board.is_stalemate() or draw: return 0

3. Leaf node (depth == 0): return quiescence(board, alpha, beta, ply, nodes_ref)

4. Move loop:
   tt_move = entry.best_move if TT hit else None
   for move in _order_moves(board, legal_moves, tt_move):
     board.push(move)
     score = -alpha_beta(board, depth-1, -beta, -alpha, ply+1, nodes_ref)
     board.pop()
     nodes_ref[0] += 1

     if score > alpha:
       alpha = score
       best_move = move
       flag = TT_EXACT
     if alpha >= beta:
       flag = TT_LOWER
       break  # beta cutoff

5. TT store: tt.put(key, alpha, depth, flag)
6. Return alpha
```

> Store best_move in TT alongside score for use as TT move in future lookups.
> TT entry structure: `(score, depth, flag, best_move)` — update `TranspositionTable` accordingly.

#### Quiescence Search

```
quiescence(board, alpha, beta, ply, nodes_ref) -> int

1. Terminal: checkmate/stalemate → same as alpha_beta
2. Stand-pat: score = evaluate(board)
   if score >= beta: return beta  (beta cutoff)
   alpha = max(alpha, score)

3. For each capture move (board.generate_pseudo_legal_captures()):
   Delta pruning: if score + piece_captured_value + 200 < alpha: skip
   if not board.is_legal(move): skip
   board.push(move)
   score = -quiescence(board, -beta, -alpha, ply+1, nodes_ref)
   board.pop()
   nodes_ref[0] += 1
   if score >= beta: return beta
   alpha = max(alpha, score)

4. Return alpha
```

#### Iterative Deepening

```
best_move(board, budget) -> chess.Move | None

budget.start()
tt.clear()  # clear TT on each search (ucinewgame also clears)
best = first legal move (fallback)
nodes = [0]

for depth in range(1, MAX_DEPTH + 1):
   if budget.depth_limit() is not None and depth > budget.depth_limit():
       break

   score, move = _search_root(board, depth, nodes, budget)

   if move is not None:
       best = move

   # Emit UCI info line
   print(f"info depth {depth} score cp {score} nodes {nodes[0]} pv {best.uci()}", flush=True)

   if budget.should_stop():
       break
   if abs(score) >= MATE_SCORE - MAX_DEPTH:
       break  # found a forced mate

return best
```

```
_search_root(board, depth, nodes, budget) -> (score, best_move)

alpha, beta = -INF, INF
best_move = None

for move in _order_moves(board, list(board.legal_moves), tt_move):
   board.push(move)
   score = -alpha_beta(board, depth-1, -beta, -alpha, 1, nodes)
   board.pop()

   if nodes[0] % 1024 == 0 and budget.should_stop():
       break  # return best found so far

   if score > alpha:
       alpha = score
       best_move = move

return alpha, best_move
```

---

## Verification

```bash
pip3 install python-chess

python3 - <<'EOF'
import chess
from search import best_move
from time_manager import TimeBudget  # or use stub

# Startpos depth 4
board = chess.Board()
budget = TimeBudget(turn=chess.WHITE, depth_limit=4)
move = best_move(board, budget)
assert move in board.legal_moves, f"illegal move: {move}"
print(f"startpos depth 4: {move}")

# Checkmate in 1 (white to move: Qh5#)
board2 = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4")
budget2 = TimeBudget(turn=chess.WHITE, depth_limit=2)
move2 = best_move(board2, budget2)
assert move2.uci() == "h5f7", f"expected Qf7#, got {move2}"
print(f"mate in 1: {move2}")

# Wins a queen (black queen on d8 is hanging)
board3 = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
budget3 = TimeBudget(turn=chess.WHITE, depth_limit=3)
move3 = best_move(board3, budget3)
print(f"open queen position depth 3: {move3}")
EOF
```

**Tactical position test** (Légall's Mate setup):
```
position fen r1bqkb1r/pppp1ppp/2n2n2/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4
go depth 6
# Bxf7+ should be found (fork on king + queen)
```

---

## Completion Checklist
- [x] `TranspositionTable` stores `(score, depth, flag, best_move)` per hash
- [x] `alpha_beta` does TT lookup/store correctly with EXACT/LOWER/UPPER
- [x] `quiescence` only expands captures; delta pruning implemented
- [x] `_order_moves` puts TT move first, then captures by MVV-LVA
- [x] `best_move` runs iterative deepening, emits `info depth` lines
- [x] `should_stop()` checked every 1024 nodes (not every node)
- [x] Fallback to first legal move if search aborted on depth 1
- [x] No illegal moves returned
- [x] Mate scores: `-MATE_SCORE + ply` (prefer faster mates)

## Future Plan Impact
Phase 4 is no longer a blocking stub dependency for search verification. `TimeBudget.start()`, `TimeBudget.depth_limit()`, and time-based stopping are now implemented, and `engine.py` already clears the shared TT on `ucinewgame`, so Phase 5 can focus on integration tests and edge-case hardening rather than wiring.

## Dependencies
- **Phase 2** interface: `evaluate(board: chess.Board) -> int`
- **Phase 4** interface: `TimeBudget.should_stop()`, `TimeBudget.depth_limit()`, `TimeBudget.start()`
