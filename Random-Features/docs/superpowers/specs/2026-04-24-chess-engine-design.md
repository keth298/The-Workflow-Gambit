# Chess Engine Design — engines/base/

**Date:** 2026-04-24
**Branch:** Unconventional-Ideas
**Language:** Python
**Board library:** python-chess

---

## Goal

Build a UCI-compliant chess engine strong enough to compete in the hackathon tournament. Correctness (zero illegal moves) is the primary constraint; strength comes second.

---

## File Structure

```
engines/base/
  engine.py    # UCI loop — stdin/stdout, command dispatch
  search.py    # iterative deepening, alpha-beta, quiescence search
  evaluate.py  # material scoring + piece-square tables
  tt.py        # transposition table
```

Each file has one responsibility and no circular dependencies. `engine.py` owns I/O; `search.py` owns tree traversal; `evaluate.py` owns static scoring; `tt.py` owns position caching.

---

## UCI Interface (`engine.py`)

- Blocking `input()` loop on stdin
- Every response printed to stdout and flushed immediately
- All debug/log output to stderr only

| Command | Response |
|---|---|
| `uci` | `id name ...`, `id author ...`, `uciok` |
| `isready` | `readyok` |
| `ucinewgame` | Reset board, clear TT |
| `position startpos [moves ...]` | Set board state |
| `position fen <fen> [moves ...]` | Set board state from FEN |
| `go depth N` | Search to depth N, print `bestmove <move>` |
| `go movetime N` | Search until N ms elapsed, print `bestmove <move>` |
| `go wtime/btime/winc/binc` | Use ~5% of remaining time |
| `quit` | Exit cleanly |

Unknown commands are silently ignored.

---

## Search (`search.py`)

### Iterative Deepening

Search depth 1, 2, 3, … up to the requested depth or time limit. Each completed iteration's best move seeds move ordering for the next. If time expires mid-iteration, the previous iteration's best move is returned.

### Alpha-Beta (Negamax)

Scores from the side-to-move's perspective. At each node:
1. Check transposition table — return early on hit
2. Generate and order moves (see below)
3. Recurse with window `[-beta, -alpha]`
4. Store result in TT with appropriate bound flag (EXACT / LOWER / UPPER)

### Move Ordering

1. TT best move (from previous iteration or TT hit)
2. Captures, sorted by MVV-LVA (most valuable victim / least valuable attacker)
3. Quiet moves, sorted by history heuristic (moves that caused beta cutoffs score higher)

### Quiescence Search

At leaf nodes, continue searching captures-only until the position is quiet. Prevents horizon-effect blunders where the engine stops just before a recapture.

---

## Transposition Table (`tt.py`)

- Fixed-size dict keyed by python-chess Zobrist hash (`board.zobrist_hash()`)
- Entry: `(depth, flag, score, best_move)`
- Flags: `EXACT`, `LOWER` (alpha), `UPPER` (beta)
- Eviction: simple overwrite on collision (no replacement scheme needed at this scale)

---

## Evaluation (`evaluate.py`)

### Material Values (centipawns)

| Piece | Value |
|---|---|
| Pawn | 100 |
| Knight | 320 |
| Bishop | 330 |
| Rook | 500 |
| Queen | 900 |
| King | 20000 |

### Piece-Square Tables

One table per piece type. Values added for white pieces as-is; mirrored vertically for black. Tables cover:
- Pawn: encourage center control and advancement
- Knight: prefer center squares, penalize rim
- Bishop: prefer long diagonals
- Rook: prefer open files and 7th rank
- Queen: prefer center, penalize early development
- King (middlegame): encourage castling / corner safety
- King (endgame): encourage centralization

Score = (white material + white PST) − (black material + black PST), returned from white's perspective. Negated for black's turn in negamax.

---

## Testing

After implementation, verify:

```bash
echo -e "uci\nisready\nposition startpos\ngo depth 5\nquit" | python engines/base/engine.py
```

Expected output includes:
- `uciok`
- `readyok`
- `bestmove <valid UCI move>`

No output on stdout except UCI responses. Search info and logs go to stderr.
