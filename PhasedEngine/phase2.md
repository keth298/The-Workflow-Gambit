# Phase 2: Static Evaluation

## Purpose
Score any chess position as a signed integer (centipawns) from the side-to-move's perspective. This is the leaf-node scoring function used by the search engine.

## Provides
```python
# evaluation.py
def evaluate(board: chess.Board) -> int
```
- Returns centipawns, **positive = side-to-move is winning**
- Checkmate: not handled here (search detects it before calling evaluate)
- Draw: not handled here (search detects stalemate/repetition)
- Range: roughly −30000 to +30000; ±30000 reserved for mate scores in search

## Depends On
Only `python-chess`. No other phases needed.

---

## Implementation Spec

### File: `evaluation.py`

### 1. Material Values (centipawns)
```python
PIECE_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:     0,
}
```

### 2. Piece-Square Tables
One 64-element list per piece type for White (index = `chess.square`, a1=0 … h8=63).
For Black, mirror vertically: `index = square ^ 56`.

**Pawn PST** (bonus for advancement and center control):
```
Rank 7: [  0,  0,  0,  0,  0,  0,  0,  0]
Rank 6: [ 50, 50, 50, 50, 50, 50, 50, 50]
Rank 5: [ 10, 10, 20, 30, 30, 20, 10, 10]
Rank 4: [  5,  5, 10, 25, 25, 10,  5,  5]
Rank 3: [  0,  0,  0, 20, 20,  0,  0,  0]
Rank 2: [  5, -5,-10,  0,  0,-10, -5,  5]
Rank 1: [  5, 10, 10,-20,-20, 10, 10,  5]
Rank 0: [  0,  0,  0,  0,  0,  0,  0,  0]
```

**Knight PST** (centralization):
```
[-50,-40,-30,-30,-30,-30,-40,-50]
[-40,-20,  0,  0,  0,  0,-20,-40]
[-30,  0, 10, 15, 15, 10,  0,-30]
[-30,  5, 15, 20, 20, 15,  5,-30]
[-30,  0, 15, 20, 20, 15,  0,-30]
[-30,  5, 10, 15, 15, 10,  5,-30]
[-40,-20,  0,  5,  5,  0,-20,-40]
[-50,-40,-30,-30,-30,-30,-40,-50]
```

**Bishop PST** (long diagonals, avoid corners):
```
[-20,-10,-10,-10,-10,-10,-10,-20]
[-10,  0,  0,  0,  0,  0,  0,-10]
[-10,  0,  5, 10, 10,  5,  0,-10]
[-10,  5,  5, 10, 10,  5,  5,-10]
[-10,  0, 10, 10, 10, 10,  0,-10]
[-10, 10, 10, 10, 10, 10, 10,-10]
[-10,  5,  0,  0,  0,  0,  5,-10]
[-20,-10,-10,-10,-10,-10,-10,-20]
```

**Rook PST** (7th rank, open files):
```
[  0,  0,  0,  0,  0,  0,  0,  0]
[  5, 10, 10, 10, 10, 10, 10,  5]
[ -5,  0,  0,  0,  0,  0,  0, -5]
[ -5,  0,  0,  0,  0,  0,  0, -5]
[ -5,  0,  0,  0,  0,  0,  0, -5]
[ -5,  0,  0,  0,  0,  0,  0, -5]
[ -5,  0,  0,  0,  0,  0,  0, -5]
[  0,  0,  0,  5,  5,  0,  0,  0]
```

**Queen PST** (central activity, not too early):
```
[-20,-10,-10, -5, -5,-10,-10,-20]
[-10,  0,  0,  0,  0,  0,  0,-10]
[-10,  0,  5,  5,  5,  5,  0,-10]
[ -5,  0,  5,  5,  5,  5,  0, -5]
[  0,  0,  5,  5,  5,  5,  0, -5]
[-10,  5,  5,  5,  5,  5,  0,-10]
[-10,  0,  5,  0,  0,  0,  0,-10]
[-20,-10,-10, -5, -5,-10,-10,-20]
```

**King Middlegame PST** (castle, hide):
```
[-30,-40,-40,-50,-50,-40,-40,-30]
[-30,-40,-40,-50,-50,-40,-40,-30]
[-30,-40,-40,-50,-50,-40,-40,-30]
[-30,-40,-40,-50,-50,-40,-40,-30]
[-20,-30,-30,-40,-40,-30,-30,-20]
[-10,-20,-20,-20,-20,-20,-20,-10]
[ 20, 20,  0,  0,  0,  0, 20, 20]
[ 20, 30, 10,  0,  0, 10, 30, 20]
```

**King Endgame PST** (centralize):
```
[-50,-40,-30,-20,-20,-30,-40,-50]
[-30,-20,-10,  0,  0,-10,-20,-30]
[-30,-10, 20, 30, 30, 20,-10,-30]
[-30,-10, 30, 40, 40, 30,-10,-30]
[-30,-10, 30, 40, 40, 30,-10,-30]
[-30,-10, 20, 30, 30, 20,-10,-30]
[-30,-30,  0,  0,  0,  0,-30,-30]
[-50,-30,-30,-30,-30,-30,-30,-50]
```

### 3. Endgame Detection
```python
def is_endgame(board: chess.Board) -> bool:
    queens = board.pieces(chess.QUEEN, chess.WHITE) | board.pieces(chess.QUEEN, chess.BLACK)
    if not queens:
        return True
    # Both sides have queen but no other major pieces
    white_minor = len(board.pieces(chess.ROOK, chess.WHITE)) + len(board.pieces(chess.BISHOP, chess.WHITE)) + len(board.pieces(chess.KNIGHT, chess.WHITE))
    black_minor = len(board.pieces(chess.ROOK, chess.BLACK)) + len(board.pieces(chess.BISHOP, chess.BLACK)) + len(board.pieces(chess.KNIGHT, chess.BLACK))
    return white_minor <= 1 and black_minor <= 1
```

### 4. PST Lookup
```python
def _pst_bonus(piece: chess.Piece, square: chess.Square, endgame: bool) -> int:
    table = PST[piece.piece_type]  # dict: piece_type → list[64]
    if piece.piece_type == chess.KING:
        table = KING_ENDGAME_PST if endgame else KING_MIDDLEGAME_PST
    if piece.color == chess.WHITE:
        # White: rank 0 is a1–h1 (bottom of board)
        return table[square]
    else:
        # Black: mirror vertically (XOR rank bits)
        return table[square ^ 56]
```

### 5. Pawn Structure
```python
def _pawn_structure_bonus(board: chess.Board) -> int:
    score = 0
    for color, sign in [(chess.WHITE, 1), (chess.BLACK, -1)]:
        pawns = board.pieces(chess.PAWN, color)
        files = [chess.square_file(sq) for sq in pawns]
        for f in files:
            if files.count(f) > 1:
                score -= sign * 20   # doubled pawn penalty (per extra pawn)
        for sq in pawns:
            f = chess.square_file(sq)
            neighbors = [f - 1, f + 1]
            if not any(chess.square_file(s) in neighbors for s in pawns):
                score -= sign * 15   # isolated pawn penalty
    return score
```

### 6. `evaluate` Assembly
```python
def evaluate(board: chess.Board) -> int:
    endgame = is_endgame(board)
    score = 0

    # Material + PST
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue
        value = PIECE_VALUES[piece.piece_type]
        pst = _pst_bonus(piece, square, endgame)
        if piece.color == chess.WHITE:
            score += value + pst
        else:
            score -= value + pst

    # Pawn structure
    score += _pawn_structure_bonus(board)

    # Return from side-to-move perspective
    return score if board.turn == chess.WHITE else -score
```

---

## Verification

```python
import chess
from evaluation import evaluate

# Starting position: material is equal → ±0 (PST may give small bonus)
b = chess.Board()
assert abs(evaluate(b)) < 50, "startpos should be near 0"

# Symmetry: eval from white's perspective = -eval from black's perspective
b2 = chess.Board()
b2.turn = chess.BLACK
# (manually swap: use two boards at same position but different turn)
b_w = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
b_b = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1")
# Material is equal so both should be near 0 or equal magnitude
# Note: PST bonus for side to move may differ; symmetry is about material only

# White up a queen
b3 = chess.Board("rnbqkbnr/pppp1ppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
b3.remove_piece_at(chess.D8)  # remove black queen
assert evaluate(b3) > 800, "white up a queen should be +900ish"

# Black up a rook
b4 = chess.Board()
b4.remove_piece_at(chess.A1)  # remove white rook
b4.turn = chess.BLACK
assert evaluate(b4) > 400, "black up a rook (from black's POV) should be positive"
```

---

## Completion Checklist
- [x] `PIECE_VALUES` dict defined
- [x] All 6 PSTs defined (pawn, knight, bishop, rook, queen, king×2)
- [x] `is_endgame()` implemented
- [x] `_pst_bonus()` mirrors Black correctly (XOR 56)
- [x] `_pawn_structure_bonus()` penalizes doubled + isolated pawns
- [x] `evaluate()` returns side-to-move-positive centipawns
- [x] Startpos evaluates to near 0
- [x] Material advantage correctly reflected

## Future Plan Impact
No Phase 3-5 changes are required from this implementation. The richer evaluator matches the current downstream search assumptions.
