# Variant Engines Design

**Date:** 2026-04-25
**Branch:** Unconventional-Ideas

---

## Goal

Create 8 variant chess engines in `engines/variants/`, each derived from `engines/base/` with exactly one behavioral change. All variants are standalone UCI-compliant engines.

---

## File Structure

Each variant lives in `engines/variants/<name>/` and contains exactly **2 files**: `engine.py` and `search.py`. `evaluate.py` and `tt.py` are **not** copied — they are imported from `engines/base/` via sys.path.

```
engines/variants/
  no_pawn_push/    engine.py  search.py
  mirror_queen/    engine.py  search.py
  king_walk/       engine.py  search.py
  bishops_only/    engine.py  search.py
  first_rank_lock/ engine.py  search.py
  aggro_push/      engine.py  search.py
  fortress/        engine.py  search.py
  random_blunder/  engine.py  search.py
```

---

## Shared sys.path Setup

Every variant's `engine.py` starts with:

```python
_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.join(_HERE, '..', '..', 'base')
sys.path.insert(0, _HERE)   # variant search.py takes precedence over base
sys.path.insert(1, _BASE)   # base evaluate.py + tt.py
```

Every variant's `engine.py` is identical to base except for the `id name` line and this sys.path setup. Every variant's `search.py` is a copy of base's `search.py` with exactly one behavioral modification.

---

## Fallback Rule

For every variant: if the behavioral filter reduces legal moves to zero, fall back to the full unfiltered legal move list. The engine must never crash or return an illegal move.

---

## Per-Variant Specifications

### 1. `no_pawn_push`

**id name:** NoPawnPushEngine

**Hook:** `_alpha_beta` (propagates to all search depths)

**Behavior:** When `board.fullmove_number > 20`, filter out any move where the moving piece is a pawn before calling `_order_moves`.

```python
# In _alpha_beta, before _order_moves:
moves = list(board.legal_moves)
if board.fullmove_number > 20:
    filtered = [m for m in moves if board.piece_at(m.from_square).piece_type != chess.PAWN]
    if filtered:
        moves = filtered
```

---

### 2. `mirror_queen`

**id name:** MirrorQueenEngine

**Hook:** `iterative_deepening` (root only)

**Behavior:** Check the last move in the board's move stack. If that move was made by the opponent's queen (i.e., `board.piece_at(last_move.to_square)` is a queen of the opponent's color after the position is set), restrict root moves to our queen moves only. Fall back to all moves if we have no legal queen moves.

```python
# In iterative_deepening, before the depth loop:
moves = list(board.legal_moves)
if board.move_stack:
    last = board.peek()
    piece = board.piece_at(last.to_square)
    if piece and piece.piece_type == chess.QUEEN and piece.color != board.turn:
        queen_moves = [m for m in moves
                       if board.piece_at(m.from_square) and
                          board.piece_at(m.from_square).piece_type == chess.QUEEN]
        if queen_moves:
            moves = queen_moves
```

Pass `moves` (not `board.legal_moves`) into the search.

---

### 3. `king_walk`

**id name:** KingWalkEngine

**Hook:** `_alpha_beta` (filter) + `_order_moves` (boost)

**Behavior (two parts):**
1. Filter all castling moves at every node.
2. In `_order_moves`, boost king moves that reduce the king's Manhattan distance to the center squares (d4/d5/e4/e5, i.e., files 3–4, ranks 3–4). King moves closer to center get +10000 bonus in the sort key.

```python
# In _alpha_beta:
moves = list(board.legal_moves)
filtered = [m for m in moves if not board.is_castling(m)]
if filtered:
    moves = filtered

# In _order_moves key function, replace the body with:
def key(m):
    if m == tt_move:
        return 1_000_000
    if board.is_capture(m):
        return 100_000 + _mvv_lva(board, m)
    score = _history[m.from_square][m.to_square]
    piece = board.piece_at(m.from_square)
    if piece and piece.piece_type == chess.KING:
        dest_file = chess.square_file(m.to_square)
        dest_rank = chess.square_rank(m.to_square)
        dist = abs(dest_file - 3.5) + abs(dest_rank - 3.5)
        score += int((7 - dist) * 1000)
    return score
```

---

### 4. `bishops_only`

**id name:** BishopsOnlyEngine

**Hook:** `_alpha_beta` (propagates to all search depths)

**Behavior:** Filter all knight moves from legal moves at every node.

```python
# In _alpha_beta, before _order_moves:
moves = list(board.legal_moves)
filtered = [m for m in moves
            if board.piece_at(m.from_square).piece_type != chess.KNIGHT]
if filtered:
    moves = filtered
```

---

### 5. `first_rank_lock`

**id name:** FirstRankLockEngine

**Hook:** `_alpha_beta` (propagates to all search depths)

**Behavior:** When `board.fullmove_number <= 10`, filter out moves where a piece starts on its own back rank and would leave it. White back rank = rank index 0 (rank 1). Black back rank = rank index 7 (rank 8).

```python
# In _alpha_beta:
moves = list(board.legal_moves)
if board.fullmove_number <= 10:
    own_back = 0 if board.turn == chess.WHITE else 7
    filtered = [m for m in moves
                if not (chess.square_rank(m.from_square) == own_back and
                        chess.square_rank(m.to_square) != own_back)]
    if filtered:
        moves = filtered
```

---

### 6. `aggro_push`

**id name:** AggroPushEngine

**Hook:** `iterative_deepening` (root only)

**Behavior:** At the root, if no captures are available in the legal moves, return the push of the most-advanced pawn without searching. "Most advanced" = highest rank for white, lowest rank for black. If multiple pawns share the most-advanced rank, pick any one. Fall back to normal search if no pawn push is available after filtering.

```python
# In iterative_deepening, before the depth loop:
moves = list(board.legal_moves)
captures = [m for m in moves if board.is_capture(m)]
if not captures:
    pawn_pushes = [m for m in moves
                   if board.piece_at(m.from_square) and
                      board.piece_at(m.from_square).piece_type == chess.PAWN and
                      not board.is_capture(m)]
    if pawn_pushes:
        if board.turn == chess.WHITE:
            best_rank = max(chess.square_rank(m.from_square) for m in pawn_pushes)
        else:
            best_rank = min(chess.square_rank(m.from_square) for m in pawn_pushes)
        advanced = [m for m in pawn_pushes
                    if chess.square_rank(m.from_square) == best_rank]
        return advanced[0]
```

---

### 7. `fortress`

**id name:** FortressEngine

**Hook:** `_alpha_beta` (propagates to all search depths)

**Behavior:** When `board.fullmove_number > 15`, filter out moves where `to_square` is in the opponent's half of the board. White's half = rank indices 0–3 (ranks 1–4). Black's half = rank indices 4–7 (ranks 5–8).

```python
# In _alpha_beta:
moves = list(board.legal_moves)
if board.fullmove_number > 15:
    if board.turn == chess.WHITE:
        filtered = [m for m in moves if chess.square_rank(m.to_square) <= 3]
    else:
        filtered = [m for m in moves if chess.square_rank(m.to_square) >= 4]
    if filtered:
        moves = filtered
```

---

### 8. `random_blunder`

**id name:** RandomBlunderEngine

**Hook:** `iterative_deepening` (root only)

**Behavior:** When `board.fullmove_number % 5 == 0`, return a random legal move instead of searching.

```python
import random  # at module level

# In iterative_deepening, before the depth loop:
if board.fullmove_number % 5 == 0:
    return random.choice(list(board.legal_moves))
```

---

## Testing

Each variant engine is verified by running the three-command spec test:

```bash
echo -e "uci\nisready\nposition startpos\ngo depth 3\nquit" | python3 engines/variants/<name>/engine.py
```

Expected: `uciok`, `readyok`, `bestmove <valid-move>` in stdout.
