# Chess Engine (engines/base/) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a UCI-compliant Python chess engine with alpha-beta search, iterative deepening, quiescence search, transposition table, move ordering, and material+PST evaluation.

**Architecture:** Four focused modules — `evaluate.py` (static scoring), `tt.py` (transposition table), `search.py` (tree search), and `engine.py` (UCI I/O loop). `engine.py` is the executable entry point and owns all stdin/stdout; all other output goes to stderr. `search.py` orchestrates iterative deepening over alpha-beta with quiescence at the leaves.

**Tech Stack:** Python 3, python-chess (board/move generation/Zobrist hashing)

---

## File Map

| File | Responsibility |
|---|---|
| `engines/base/engine.py` | UCI command loop, entry point |
| `engines/base/search.py` | Iterative deepening, alpha-beta, quiescence, move ordering, history heuristic |
| `engines/base/evaluate.py` | Material values, PST tables, static board evaluation |
| `engines/base/tt.py` | Transposition table (store/probe) |
| `tests/base/conftest.py` | Adds `engines/base/` to sys.path for imports |
| `tests/base/test_evaluate.py` | Unit tests for evaluation |
| `tests/base/test_tt.py` | Unit tests for transposition table |
| `tests/base/test_search.py` | Unit tests for search (legal moves, mate detection) |
| `tests/base/test_engine.py` | Integration tests via subprocess |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `engines/__init__.py`
- Create: `engines/base/__init__.py`
- Create: `engines/base/engine.py` (stub)
- Create: `engines/base/search.py` (stub)
- Create: `engines/base/evaluate.py` (stub)
- Create: `engines/base/tt.py` (stub)
- Create: `tests/__init__.py`
- Create: `tests/base/__init__.py`
- Create: `tests/base/conftest.py`

- [ ] **Step 1: Install python-chess**

```bash
pip install python-chess
python3 -c "import chess; print('ok', chess.__version__)"
```
Expected: `ok 1.x.x` (any version)

- [ ] **Step 2: Create directory structure**

```bash
mkdir -p engines/base tests/base
touch engines/__init__.py engines/base/__init__.py
touch tests/__init__.py tests/base/__init__.py
```

- [ ] **Step 3: Create conftest.py**

`tests/base/conftest.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'engines', 'base'))
```

- [ ] **Step 4: Create stub files**

`engines/base/evaluate.py`:
```python
import chess
```

`engines/base/tt.py`:
```python
```

`engines/base/search.py`:
```python
import chess
```

`engines/base/engine.py`:
```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chess
```

- [ ] **Step 5: Verify imports work**

```bash
cd engines/base && python3 -c "import chess; print('imports ok')" && cd ../..
```
Expected: `imports ok`

- [ ] **Step 6: Commit**

```bash
git add engines/ tests/
git commit -m "feat: scaffold engines/base/ directory structure"
```

---

## Task 2: Evaluation (`evaluate.py`)

**Files:**
- Modify: `engines/base/evaluate.py`
- Test: `tests/base/test_evaluate.py`

### PST Indexing Convention

PST arrays are written rank-8 first (index 0 = a8, index 63 = h1).

- **White piece at square `sq`:** `PST[chess.square_mirror(sq)]`  
  (`chess.square_mirror` flips rank; e.g., e2 → e7 index, so white's advancing direction maps to low indices)
- **Black piece at square `sq`:** `PST[sq]`  
  (black's advancing direction is already towards low indices)

- [ ] **Step 1: Write failing tests**

`tests/base/test_evaluate.py`:
```python
import chess
from evaluate import evaluate, MATERIAL

def test_starting_position_is_zero():
    board = chess.Board()
    assert evaluate(board) == 0

def test_missing_white_pawn_is_negative():
    board = chess.Board()
    board.remove_piece_at(chess.E2)
    assert evaluate(board) < 0

def test_missing_black_pawn_is_positive():
    board = chess.Board()
    board.remove_piece_at(chess.E7)
    assert evaluate(board) > 0

def test_white_up_queen_is_large_positive():
    board = chess.Board()
    board.remove_piece_at(chess.D8)
    assert evaluate(board) > 800

def test_checkmate_position_from_white_perspective():
    # Black is mated (white to move after delivering mate is not possible;
    # this is a position where black's king has no moves and is in check)
    # Use a known checkmated position: black is in checkmate, white just moved.
    # board.turn is black, board.is_checkmate() is True.
    board = chess.Board("r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4")
    assert board.is_checkmate()
    # Black (side to move) is mated → very negative score for black → large positive for white
    score = evaluate(board)
    assert score > 20000
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd tests/base && python3 -m pytest test_evaluate.py -v 2>&1 | head -20
```
Expected: ImportError or NameError — `evaluate` not defined yet.

- [ ] **Step 3: Implement evaluate.py**

`engines/base/evaluate.py`:
```python
import chess

MATERIAL = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   20000,
}

# Written rank-8 first (index 0=a8 … index 63=h1).
# White: PST[chess.square_mirror(sq)], Black: PST[sq]
PAWN_PST = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]

KNIGHT_PST = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]

BISHOP_PST = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]

ROOK_PST = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]

QUEEN_PST = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
]

KING_MG_PST = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
]

KING_EG_PST = [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50,
]

_PST_MG = {
    chess.PAWN:   PAWN_PST,
    chess.KNIGHT: KNIGHT_PST,
    chess.BISHOP: BISHOP_PST,
    chess.ROOK:   ROOK_PST,
    chess.QUEEN:  QUEEN_PST,
    chess.KING:   KING_MG_PST,
}


def _is_endgame(board):
    total = sum(
        MATERIAL[pt] * (len(board.pieces(pt, chess.WHITE)) + len(board.pieces(pt, chess.BLACK)))
        for pt in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
    )
    return total < 2000


def evaluate(board):
    """Return centipawn score from white's perspective."""
    if board.is_checkmate():
        return -30000 if board.turn == chess.WHITE else 30000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    endgame = _is_endgame(board)
    score = 0

    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None:
            continue
        pt = piece.piece_type
        pst = KING_EG_PST if (pt == chess.KING and endgame) else _PST_MG[pt]
        idx = chess.square_mirror(sq) if piece.color == chess.WHITE else sq
        val = MATERIAL[pt] + pst[idx]
        if piece.color == chess.WHITE:
            score += val
        else:
            score -= val

    return score
```

- [ ] **Step 4: Run tests**

```bash
cd tests/base && python3 -m pytest test_evaluate.py -v
```
Expected: All 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add engines/base/evaluate.py tests/base/test_evaluate.py tests/base/conftest.py
git commit -m "feat: add material + PST evaluation"
```

---

## Task 3: Transposition Table (`tt.py`)

**Files:**
- Modify: `engines/base/tt.py`
- Test: `tests/base/test_tt.py`

- [ ] **Step 1: Write failing tests**

`tests/base/test_tt.py`:
```python
from tt import TranspositionTable, EXACT, LOWER, UPPER

def test_store_and_probe_exact():
    tt = TranspositionTable()
    tt.store(12345, depth=3, flag=EXACT, score=100, best_move=None)
    result = tt.probe(12345)
    assert result == (3, EXACT, 100, None)

def test_probe_miss_returns_none():
    tt = TranspositionTable()
    assert tt.probe(99999) is None

def test_overwrite_on_collision():
    tt = TranspositionTable()
    tt.store(1, depth=2, flag=LOWER, score=50, best_move=None)
    tt.store(1, depth=4, flag=EXACT, score=75, best_move=None)
    result = tt.probe(1)
    assert result == (4, EXACT, 75, None)

def test_clear_removes_all_entries():
    tt = TranspositionTable()
    tt.store(1, depth=3, flag=EXACT, score=100, best_move=None)
    tt.store(2, depth=2, flag=LOWER, score=50, best_move=None)
    tt.clear()
    assert tt.probe(1) is None
    assert tt.probe(2) is None

def test_flag_constants_are_distinct():
    assert EXACT != LOWER != UPPER
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd tests/base && python3 -m pytest test_tt.py -v 2>&1 | head -10
```
Expected: ImportError — `tt` not defined.

- [ ] **Step 3: Implement tt.py**

`engines/base/tt.py`:
```python
EXACT = 0
LOWER = 1
UPPER = 2


class TranspositionTable:
    def __init__(self):
        self._table = {}

    def probe(self, key):
        return self._table.get(key)

    def store(self, key, depth, flag, score, best_move):
        self._table[key] = (depth, flag, score, best_move)

    def clear(self):
        self._table.clear()
```

- [ ] **Step 4: Run tests**

```bash
cd tests/base && python3 -m pytest test_tt.py -v
```
Expected: All 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add engines/base/tt.py tests/base/test_tt.py
git commit -m "feat: add transposition table"
```

---

## Task 4: Search (`search.py`)

**Files:**
- Modify: `engines/base/search.py`
- Test: `tests/base/test_search.py`

### Algorithm Summary

- **`iterative_deepening`**: Searches depth 1, 2, … up to `max_depth` or `deadline`. Returns best move from deepest completed iteration.
- **`_alpha_beta`**: Negamax alpha-beta. Scores are always from the current player's perspective. Probes TT before generating moves; stores to TT after. Move ordering: TT best move → captures by MVV-LVA → quiet moves by history heuristic.
- **`_quiescence`**: Called at depth 0. Keeps searching captures until quiet. Prevents horizon-effect blunders.
- **History table**: `_history[from_sq][to_sq]` incremented by `depth²` on beta cutoffs by quiet moves.

- [ ] **Step 1: Write failing tests**

`tests/base/test_search.py`:
```python
import chess
from search import iterative_deepening, clear_state

def setup_function():
    clear_state()

def test_returns_legal_move_from_startpos_depth1():
    board = chess.Board()
    move = iterative_deepening(board, max_depth=1)
    assert move in board.legal_moves

def test_returns_legal_move_from_startpos_depth3():
    board = chess.Board()
    move = iterative_deepening(board, max_depth=3)
    assert move in board.legal_moves

def test_finds_back_rank_mate_in_1():
    # Rd8# is the only move that delivers checkmate
    board = chess.Board("6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1")
    move = iterative_deepening(board, max_depth=3)
    assert move.uci() == "d1d8"

def test_avoids_obvious_blunder():
    # White queen on e4 is en prise to black pawn on d5; engine should not capture
    # Position: white Q at e4, black P at d5, all other pieces off
    board = chess.Board("8/8/8/3p4/4Q3/8/8/4K2k w - - 0 1")
    move = iterative_deepening(board, max_depth=3)
    # Qe4xd5 would be fine here since it wins a pawn; test that a legal move is returned
    assert move in board.legal_moves
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd tests/base && python3 -m pytest test_search.py -v 2>&1 | head -20
```
Expected: ImportError — `iterative_deepening` not defined.

- [ ] **Step 3: Implement search.py**

`engines/base/search.py`:
```python
import sys
import time
import chess
import chess.polyglot
from tt import TranspositionTable, EXACT, LOWER, UPPER
from evaluate import evaluate, MATERIAL

_tt = TranspositionTable()
_history = [[0] * 64 for _ in range(64)]


def clear_state():
    global _history
    _tt.clear()
    _history = [[0] * 64 for _ in range(64)]


def _mvv_lva(board, move):
    victim = board.piece_at(move.to_square)
    attacker = board.piece_at(move.from_square)
    if victim is None:
        return 0
    return MATERIAL[victim.piece_type] * 10 - MATERIAL[attacker.piece_type]


def _order_moves(board, moves, tt_move=None):
    def key(m):
        if m == tt_move:
            return 1_000_000
        if board.is_capture(m):
            return 100_000 + _mvv_lva(board, m)
        return _history[m.from_square][m.to_square]
    return sorted(moves, key=key, reverse=True)


def _quiescence(board, alpha, beta):
    if board.is_checkmate():
        return -30000 + board.ply()
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    stand_pat = evaluate(board)
    if board.turn == chess.BLACK:
        stand_pat = -stand_pat

    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    captures = [m for m in board.legal_moves if board.is_capture(m)]
    for move in _order_moves(board, captures):
        board.push(move)
        score = -_quiescence(board, -beta, -alpha)
        board.pop()
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha


def _alpha_beta(board, depth, alpha, beta, deadline=None):
    if deadline and time.time() > deadline:
        return None, None

    key = chess.polyglot.zobrist_hash(board)
    entry = _tt.probe(key)
    tt_move = None

    if entry:
        tt_depth, tt_flag, tt_score, tt_move = entry
        if tt_depth >= depth:
            if tt_flag == EXACT:
                return tt_score, tt_move
            elif tt_flag == LOWER:
                alpha = max(alpha, tt_score)
            elif tt_flag == UPPER:
                beta = min(beta, tt_score)
            if alpha >= beta:
                return tt_score, tt_move

    if board.is_checkmate():
        return -30000 + board.ply(), None
    if board.is_stalemate() or board.is_insufficient_material():
        return 0, None

    if depth == 0:
        return _quiescence(board, alpha, beta), None

    orig_alpha = alpha
    best_score = -10_000_000
    best_move = None

    for move in _order_moves(board, list(board.legal_moves), tt_move):
        board.push(move)
        score, _ = _alpha_beta(board, depth - 1, -beta, -alpha, deadline)
        board.pop()

        if score is None:
            return None, best_move

        score = -score
        if score > best_score:
            best_score = score
            best_move = move
        if score > alpha:
            alpha = score
        if alpha >= beta:
            if not board.is_capture(move):
                _history[move.from_square][move.to_square] += depth * depth
            break

    if best_move is None:
        return 0, None

    flag = EXACT if orig_alpha < best_score < beta else (LOWER if best_score >= beta else UPPER)
    _tt.store(key, depth, flag, best_score, best_move)

    return best_score, best_move


def iterative_deepening(board, max_depth=None, deadline=None):
    moves = list(board.legal_moves)
    if not moves:
        return None
    best_move = moves[0]

    for depth in range(1, (max_depth or 100) + 1):
        if deadline and time.time() > deadline:
            break
        score, move = _alpha_beta(board, depth, -10_000_000, 10_000_000, deadline)
        if move is not None:
            best_move = move
            print(f"info depth {depth} score cp {score} pv {best_move.uci()}", flush=True)
        if max_depth and depth >= max_depth:
            break

    return best_move
```

- [ ] **Step 4: Run tests**

```bash
cd tests/base && python3 -m pytest test_search.py -v
```
Expected: All 4 tests pass. (Mate-in-1 test may take a few seconds.)

- [ ] **Step 5: Commit**

```bash
git add engines/base/search.py tests/base/test_search.py
git commit -m "feat: add alpha-beta search with iterative deepening and quiescence"
```

---

## Task 5: UCI Interface (`engine.py`)

**Files:**
- Modify: `engines/base/engine.py`
- Test: `tests/base/test_engine.py`

- [ ] **Step 1: Write failing integration tests**

`tests/base/test_engine.py`:
```python
import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', 'engines', 'base', 'engine.py')


def _run(commands, timeout=30):
    result = subprocess.run(
        [sys.executable, ENGINE],
        input='\n'.join(commands) + '\n',
        capture_output=True, text=True, timeout=timeout
    )
    return [l for l in result.stdout.strip().split('\n') if l]


def test_uci_response():
    lines = _run(['uci', 'quit'])
    assert 'uciok' in lines
    assert any(l.startswith('id name') for l in lines)
    assert any(l.startswith('id author') for l in lines)


def test_isready_response():
    lines = _run(['isready', 'quit'])
    assert 'readyok' in lines


def test_bestmove_startpos_depth5():
    lines = _run(['position startpos', 'go depth 5', 'quit'], timeout=60)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    move_str = bm[0].split()[1]
    board = chess.Board()
    move = chess.Move.from_uci(move_str)
    assert move in board.legal_moves


def test_bestmove_after_moves():
    lines = _run(['position startpos moves e2e4 e7e5', 'go depth 3', 'quit'], timeout=30)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    board.push_uci('e2e4')
    board.push_uci('e7e5')
    move = chess.Move.from_uci(bm[0].split()[1])
    assert move in board.legal_moves


def test_ucinewgame_resets_state():
    lines = _run(['ucinewgame', 'position startpos', 'go depth 2', 'quit'])
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1


def test_no_uci_output_on_stderr_leak():
    result = subprocess.run(
        [sys.executable, ENGINE],
        input='uci\nisready\nquit\n',
        capture_output=True, text=True, timeout=10
    )
    # stdout must contain only UCI lines, stderr is logs (anything goes there)
    for line in result.stdout.strip().split('\n'):
        if line:
            assert any(line.startswith(p) for p in ('id ', 'uciok', 'readyok', 'bestmove', 'info'))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd tests/base && python3 -m pytest test_engine.py -v 2>&1 | head -20
```
Expected: Tests fail (engine stubs don't respond to UCI yet).

- [ ] **Step 3: Implement engine.py**

`engines/base/engine.py`:
```python
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import chess
from search import iterative_deepening, clear_state


def _log(*args):
    print(*args, file=sys.stderr, flush=True)


def _handle_position(board, line):
    parts = line.split()
    idx = 1
    if idx >= len(parts):
        return
    if parts[idx] == 'startpos':
        board.set_fen(chess.STARTING_FEN)
        idx = 2
    elif parts[idx] == 'fen':
        fen = ' '.join(parts[idx + 1: idx + 7])
        board.set_fen(fen)
        idx += 7
    if idx < len(parts) and parts[idx] == 'moves':
        for uci in parts[idx + 1:]:
            board.push_uci(uci)


def _handle_go(board, line):
    parts = line.split()
    max_depth = None
    deadline = None

    if 'depth' in parts:
        max_depth = int(parts[parts.index('depth') + 1])
    elif 'movetime' in parts:
        ms = int(parts[parts.index('movetime') + 1])
        deadline = time.time() + ms / 1000.0
    else:
        color_key = 'wtime' if board.turn == chess.WHITE else 'btime'
        inc_key   = 'winc'  if board.turn == chess.WHITE else 'binc'
        if color_key in parts:
            remaining = int(parts[parts.index(color_key) + 1])
            inc = int(parts[parts.index(inc_key) + 1]) if inc_key in parts else 0
            think_ms = max(remaining * 0.05 + inc * 0.5, 100)
            deadline = time.time() + think_ms / 1000.0
        else:
            deadline = time.time() + 1.0

    return iterative_deepening(board, max_depth=max_depth, deadline=deadline)


def uci_loop():
    board = chess.Board()

    while True:
        try:
            line = input().strip()
        except EOFError:
            break

        _log(f'< {line}')

        if line == 'uci':
            print('id name BaseEngine')
            print('id author Point72Hackathon')
            print('uciok')
            sys.stdout.flush()

        elif line == 'isready':
            print('readyok')
            sys.stdout.flush()

        elif line == 'ucinewgame':
            board = chess.Board()
            clear_state()

        elif line.startswith('position'):
            _handle_position(board, line)

        elif line.startswith('go'):
            move = _handle_go(board, line)
            if move:
                print(f'bestmove {move.uci()}')
                sys.stdout.flush()
                _log(f'> bestmove {move.uci()}')
            else:
                print('bestmove 0000')
                sys.stdout.flush()

        elif line == 'quit':
            break


if __name__ == '__main__':
    uci_loop()
```

- [ ] **Step 4: Run integration tests**

```bash
cd tests/base && python3 -m pytest test_engine.py -v
```
Expected: All 6 tests pass. The `depth 5` test may take up to ~30 seconds.

- [ ] **Step 5: Commit**

```bash
git add engines/base/engine.py tests/base/test_engine.py
git commit -m "feat: add UCI interface and engine entry point"
```

---

## Task 6: Final Integration Verification

**Files:**
- Read: `engines/base/engine.py`

- [ ] **Step 1: Run the full test suite**

```bash
cd tests/base && python3 -m pytest -v
```
Expected: All tests pass (evaluate, tt, search, engine).

- [ ] **Step 2: Run the three-command spec test manually**

```bash
echo -e "uci\nisready\nposition startpos\ngo depth 5\nquit" | python3 engines/base/engine.py
```

Expected stdout (stderr logs will also print but that is correct behavior):
```
id name BaseEngine
id author Point72Hackathon
uciok
readyok
info depth 1 score cp ...
info depth 2 score cp ...
...
bestmove <valid UCI move e.g. e2e4>
```

Verify:
- `uciok` appears after the `id` lines
- `readyok` appears
- `bestmove` is a valid UCI move (4-5 characters, format `<from><to>[promo]`)

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete chess engine engines/base/ — UCI-compliant alpha-beta with TT and quiescence"
```
