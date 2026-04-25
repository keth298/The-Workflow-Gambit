# Variant Engines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create 8 UCI-compliant variant chess engines in `engines/variants/`, each with one behavioral change from `engines/base/`.

**Architecture:** Each variant has exactly 2 files (`engine.py` + `search.py`). `engine.py` is identical to base except `id name` and sys.path setup that imports `evaluate.py` + `tt.py` from `engines/base/`. `search.py` is a copy of base with exactly one behavioral modification.

**Tech Stack:** Python 3, python-chess, subprocess-based pytest tests

---

## File Structure

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

tests/variants/
  __init__.py
  no_pawn_push/    __init__.py  test_no_pawn_push.py
  mirror_queen/    __init__.py  test_mirror_queen.py
  king_walk/       __init__.py  test_king_walk.py
  bishops_only/    __init__.py  test_bishops_only.py
  first_rank_lock/ __init__.py  test_first_rank_lock.py
  aggro_push/      __init__.py  test_aggro_push.py
  fortress/        __init__.py  test_fortress.py
  random_blunder/  __init__.py  test_random_blunder.py
```

---

### Task 0: Scaffold directories

**Files:**
- Create: `engines/variants/__init__.py` (and 8 subdirs)
- Create: `tests/variants/__init__.py` (and 8 subdirs)

- [ ] **Step 1: Create all directories and __init__.py files**

```bash
BASE=/Users/kimet/Documents/GitHub/Probabilistic-Poker-Engine-PPE-/Probabilistic-Poker-Engine-PPE-/Probabilistic-Poker-Engine-PPE-/Point72Hackathon

for name in no_pawn_push mirror_queen king_walk bishops_only first_rank_lock aggro_push fortress random_blunder; do
  mkdir -p "$BASE/engines/variants/$name"
  touch "$BASE/engines/variants/$name/__init__.py"
  mkdir -p "$BASE/tests/variants/$name"
  touch "$BASE/tests/variants/$name/__init__.py"
done
touch "$BASE/engines/variants/__init__.py"
touch "$BASE/tests/variants/__init__.py"
```

- [ ] **Step 2: Verify structure exists**

```bash
ls engines/variants/ && ls tests/variants/
```

Expected: 8 subdirectory names printed for each.

- [ ] **Step 3: Commit**

```bash
git add engines/variants/ tests/variants/
git commit -m "feat: scaffold variant engine and test directories"
```

---

### Task 1: no_pawn_push variant

**Files:**
- Create: `tests/variants/no_pawn_push/test_no_pawn_push.py`
- Create: `engines/variants/no_pawn_push/engine.py`
- Create: `engines/variants/no_pawn_push/search.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/variants/no_pawn_push/test_no_pawn_push.py
import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engines', 'variants', 'no_pawn_push', 'engine.py')


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
    assert any(l.startswith('id name NoPawnPushEngine') for l in lines)


def test_isready_response():
    lines = _run(['isready', 'quit'])
    assert 'readyok' in lines


def test_bestmove_startpos():
    lines = _run(['position startpos', 'go depth 3', 'quit'], timeout=60)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    move = chess.Move.from_uci(bm[0].split()[1])
    assert move in board.legal_moves


def test_no_pawn_push_after_move_20():
    # fullmove=21: filter kicks in, bestmove must not be a pawn move
    fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 21'
    lines = _run([f'position fen {fen}', 'go depth 1', 'quit'])
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board(fen)
    move = chess.Move.from_uci(bm[0].split()[1])
    piece = board.piece_at(move.from_square)
    assert piece is not None
    assert piece.piece_type != chess.PAWN
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/kimet/Documents/GitHub/Probabilistic-Poker-Engine-PPE-/Probabilistic-Poker-Engine-PPE-/Probabilistic-Poker-Engine-PPE-/Point72Hackathon
pytest tests/variants/no_pawn_push/ -v
```

Expected: ERRORS (engine file not found).

- [ ] **Step 3: Write engine.py**

```python
# engines/variants/no_pawn_push/engine.py
import sys
import os
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.join(_HERE, '..', '..', 'base')
sys.path.insert(0, _HERE)
sys.path.insert(1, _BASE)

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
            try:
                board.push_uci(uci)
            except Exception as e:
                _log(f'illegal move in position: {uci} ({e})')
                break


def _handle_go(board, line):
    parts = line.split()
    max_depth = None
    deadline = None
    if 'infinite' in parts:
        deadline = time.time() + 30.0
    elif 'depth' in parts:
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
            print('id name NoPawnPushEngine')
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
            try:
                move = _handle_go(board, line)
                if move:
                    print(f'bestmove {move.uci()}')
                    sys.stdout.flush()
                    _log(f'> bestmove {move.uci()}')
                else:
                    print('bestmove 0000')
                    sys.stdout.flush()
            except Exception as e:
                _log(f'error in go handler: {e}')
                print('bestmove 0000')
                sys.stdout.flush()
        elif line == 'stop':
            pass
        elif line == 'quit':
            break


if __name__ == '__main__':
    uci_loop()
```

- [ ] **Step 4: Write search.py**

```python
# engines/variants/no_pawn_push/search.py
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

    # VARIANT: after move 20, filter out pawn moves
    moves = list(board.legal_moves)
    if board.fullmove_number > 20:
        filtered = [m for m in moves if board.piece_at(m.from_square).piece_type != chess.PAWN]
        if filtered:
            moves = filtered

    orig_alpha = alpha
    best_score = -10_000_000
    best_move = None
    any_completed = False

    for move in _order_moves(board, moves, tt_move):
        board.push(move)
        score, _ = _alpha_beta(board, depth - 1, -beta, -alpha, deadline)
        board.pop()
        if score is None:
            if not any_completed:
                continue
            return None, best_move
        any_completed = True
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

    if not any_completed:
        return None, None
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

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/variants/no_pawn_push/ -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add engines/variants/no_pawn_push/ tests/variants/no_pawn_push/
git commit -m "feat: add no_pawn_push variant engine"
```

---

### Task 2: mirror_queen variant

**Files:**
- Create: `tests/variants/mirror_queen/test_mirror_queen.py`
- Create: `engines/variants/mirror_queen/engine.py`
- Create: `engines/variants/mirror_queen/search.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/variants/mirror_queen/test_mirror_queen.py
import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engines', 'variants', 'mirror_queen', 'engine.py')


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
    assert any(l.startswith('id name MirrorQueenEngine') for l in lines)


def test_isready_response():
    lines = _run(['isready', 'quit'])
    assert 'readyok' in lines


def test_bestmove_startpos():
    lines = _run(['position startpos', 'go depth 3', 'quit'], timeout=60)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    move = chess.Move.from_uci(bm[0].split()[1])
    assert move in board.legal_moves


def test_mirror_queen_responds_with_queen():
    # After 1.e4 d5 2.exd5 Qxd5, black queen is on d5 (last move).
    # White must respond with a queen move.
    moves_str = 'e2e4 d7d5 e4d5 d8d5'
    lines = _run([f'position startpos moves {moves_str}', 'go depth 1', 'quit'])
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    for m in moves_str.split():
        board.push_uci(m)
    move = chess.Move.from_uci(bm[0].split()[1])
    piece = board.piece_at(move.from_square)
    assert piece is not None
    assert piece.piece_type == chess.QUEEN
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/variants/mirror_queen/ -v
```

Expected: ERRORS (engine file not found).

- [ ] **Step 3: Write engine.py**

```python
# engines/variants/mirror_queen/engine.py
import sys
import os
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.join(_HERE, '..', '..', 'base')
sys.path.insert(0, _HERE)
sys.path.insert(1, _BASE)

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
            try:
                board.push_uci(uci)
            except Exception as e:
                _log(f'illegal move in position: {uci} ({e})')
                break


def _handle_go(board, line):
    parts = line.split()
    max_depth = None
    deadline = None
    if 'infinite' in parts:
        deadline = time.time() + 30.0
    elif 'depth' in parts:
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
            print('id name MirrorQueenEngine')
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
            try:
                move = _handle_go(board, line)
                if move:
                    print(f'bestmove {move.uci()}')
                    sys.stdout.flush()
                    _log(f'> bestmove {move.uci()}')
                else:
                    print('bestmove 0000')
                    sys.stdout.flush()
            except Exception as e:
                _log(f'error in go handler: {e}')
                print('bestmove 0000')
                sys.stdout.flush()
        elif line == 'stop':
            pass
        elif line == 'quit':
            break


if __name__ == '__main__':
    uci_loop()
```

- [ ] **Step 4: Write search.py**

```python
# engines/variants/mirror_queen/search.py
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
    any_completed = False

    for move in _order_moves(board, list(board.legal_moves), tt_move):
        board.push(move)
        score, _ = _alpha_beta(board, depth - 1, -beta, -alpha, deadline)
        board.pop()
        if score is None:
            if not any_completed:
                continue
            return None, best_move
        any_completed = True
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

    if not any_completed:
        return None, None
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

    # VARIANT: if opponent's last move was a queen move, restrict root to our queen moves
    if board.move_stack:
        last = board.peek()
        piece = board.piece_at(last.to_square)
        if piece and piece.piece_type == chess.QUEEN and piece.color != board.turn:
            queen_moves = [m for m in moves
                           if board.piece_at(m.from_square) and
                              board.piece_at(m.from_square).piece_type == chess.QUEEN]
            if queen_moves:
                moves = queen_moves

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

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/variants/mirror_queen/ -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add engines/variants/mirror_queen/ tests/variants/mirror_queen/
git commit -m "feat: add mirror_queen variant engine"
```

---

### Task 3: king_walk variant

**Files:**
- Create: `tests/variants/king_walk/test_king_walk.py`
- Create: `engines/variants/king_walk/engine.py`
- Create: `engines/variants/king_walk/search.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/variants/king_walk/test_king_walk.py
import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engines', 'variants', 'king_walk', 'engine.py')


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
    assert any(l.startswith('id name KingWalkEngine') for l in lines)


def test_isready_response():
    lines = _run(['isready', 'quit'])
    assert 'readyok' in lines


def test_bestmove_startpos():
    lines = _run(['position startpos', 'go depth 3', 'quit'], timeout=60)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    move = chess.Move.from_uci(bm[0].split()[1])
    assert move in board.legal_moves


def test_king_walk_does_not_castle():
    # Position where white can castle kingside; verify it chooses not to
    # After 1.e4 e5 2.Nf3 Nc6 3.Bc4 Bc5, white can castle next move
    fen = 'r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4'
    lines = _run([f'position fen {fen}', 'go depth 1', 'quit'])
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board(fen)
    move = chess.Move.from_uci(bm[0].split()[1])
    assert not board.is_castling(move)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/variants/king_walk/ -v
```

Expected: ERRORS (engine file not found).

- [ ] **Step 3: Write engine.py**

```python
# engines/variants/king_walk/engine.py
import sys
import os
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.join(_HERE, '..', '..', 'base')
sys.path.insert(0, _HERE)
sys.path.insert(1, _BASE)

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
            try:
                board.push_uci(uci)
            except Exception as e:
                _log(f'illegal move in position: {uci} ({e})')
                break


def _handle_go(board, line):
    parts = line.split()
    max_depth = None
    deadline = None
    if 'infinite' in parts:
        deadline = time.time() + 30.0
    elif 'depth' in parts:
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
            print('id name KingWalkEngine')
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
            try:
                move = _handle_go(board, line)
                if move:
                    print(f'bestmove {move.uci()}')
                    sys.stdout.flush()
                    _log(f'> bestmove {move.uci()}')
                else:
                    print('bestmove 0000')
                    sys.stdout.flush()
            except Exception as e:
                _log(f'error in go handler: {e}')
                print('bestmove 0000')
                sys.stdout.flush()
        elif line == 'stop':
            pass
        elif line == 'quit':
            break


if __name__ == '__main__':
    uci_loop()
```

- [ ] **Step 4: Write search.py**

```python
# engines/variants/king_walk/search.py
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
    # VARIANT: king moves toward center get +bonus in sort key
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

    # VARIANT: filter all castling moves
    moves = list(board.legal_moves)
    filtered = [m for m in moves if not board.is_castling(m)]
    if filtered:
        moves = filtered

    orig_alpha = alpha
    best_score = -10_000_000
    best_move = None
    any_completed = False

    for move in _order_moves(board, moves, tt_move):
        board.push(move)
        score, _ = _alpha_beta(board, depth - 1, -beta, -alpha, deadline)
        board.pop()
        if score is None:
            if not any_completed:
                continue
            return None, best_move
        any_completed = True
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

    if not any_completed:
        return None, None
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

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/variants/king_walk/ -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add engines/variants/king_walk/ tests/variants/king_walk/
git commit -m "feat: add king_walk variant engine"
```

---

### Task 4: bishops_only variant

**Files:**
- Create: `tests/variants/bishops_only/test_bishops_only.py`
- Create: `engines/variants/bishops_only/engine.py`
- Create: `engines/variants/bishops_only/search.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/variants/bishops_only/test_bishops_only.py
import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engines', 'variants', 'bishops_only', 'engine.py')


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
    assert any(l.startswith('id name BishopsOnlyEngine') for l in lines)


def test_isready_response():
    lines = _run(['isready', 'quit'])
    assert 'readyok' in lines


def test_bestmove_startpos():
    lines = _run(['position startpos', 'go depth 3', 'quit'], timeout=60)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    move = chess.Move.from_uci(bm[0].split()[1])
    assert move in board.legal_moves


def test_bishops_only_no_knight_moves():
    # From startpos at depth 1, only pawn moves survive the filter (knights filtered)
    lines = _run(['position startpos', 'go depth 1', 'quit'])
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    move = chess.Move.from_uci(bm[0].split()[1])
    piece = board.piece_at(move.from_square)
    assert piece is not None
    assert piece.piece_type != chess.KNIGHT
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/variants/bishops_only/ -v
```

Expected: ERRORS (engine file not found).

- [ ] **Step 3: Write engine.py**

```python
# engines/variants/bishops_only/engine.py
import sys
import os
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.join(_HERE, '..', '..', 'base')
sys.path.insert(0, _HERE)
sys.path.insert(1, _BASE)

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
            try:
                board.push_uci(uci)
            except Exception as e:
                _log(f'illegal move in position: {uci} ({e})')
                break


def _handle_go(board, line):
    parts = line.split()
    max_depth = None
    deadline = None
    if 'infinite' in parts:
        deadline = time.time() + 30.0
    elif 'depth' in parts:
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
            print('id name BishopsOnlyEngine')
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
            try:
                move = _handle_go(board, line)
                if move:
                    print(f'bestmove {move.uci()}')
                    sys.stdout.flush()
                    _log(f'> bestmove {move.uci()}')
                else:
                    print('bestmove 0000')
                    sys.stdout.flush()
            except Exception as e:
                _log(f'error in go handler: {e}')
                print('bestmove 0000')
                sys.stdout.flush()
        elif line == 'stop':
            pass
        elif line == 'quit':
            break


if __name__ == '__main__':
    uci_loop()
```

- [ ] **Step 4: Write search.py**

```python
# engines/variants/bishops_only/search.py
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

    # VARIANT: filter all knight moves
    moves = list(board.legal_moves)
    filtered = [m for m in moves
                if board.piece_at(m.from_square).piece_type != chess.KNIGHT]
    if filtered:
        moves = filtered

    orig_alpha = alpha
    best_score = -10_000_000
    best_move = None
    any_completed = False

    for move in _order_moves(board, moves, tt_move):
        board.push(move)
        score, _ = _alpha_beta(board, depth - 1, -beta, -alpha, deadline)
        board.pop()
        if score is None:
            if not any_completed:
                continue
            return None, best_move
        any_completed = True
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

    if not any_completed:
        return None, None
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

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/variants/bishops_only/ -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add engines/variants/bishops_only/ tests/variants/bishops_only/
git commit -m "feat: add bishops_only variant engine"
```

---

### Task 5: first_rank_lock variant

**Files:**
- Create: `tests/variants/first_rank_lock/test_first_rank_lock.py`
- Create: `engines/variants/first_rank_lock/engine.py`
- Create: `engines/variants/first_rank_lock/search.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/variants/first_rank_lock/test_first_rank_lock.py
import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engines', 'variants', 'first_rank_lock', 'engine.py')


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
    assert any(l.startswith('id name FirstRankLockEngine') for l in lines)


def test_isready_response():
    lines = _run(['isready', 'quit'])
    assert 'readyok' in lines


def test_bestmove_startpos():
    lines = _run(['position startpos', 'go depth 3', 'quit'], timeout=60)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    move = chess.Move.from_uci(bm[0].split()[1])
    assert move in board.legal_moves


def test_first_rank_lock_no_piece_leaves_back_rank():
    # fullmove=1: back rank pieces must not leave rank 0
    # From startpos only knights (rank 0) and pawns (rank 1) can move;
    # knights filtered, so only pawn moves remain.
    lines = _run(['position startpos', 'go depth 1', 'quit'])
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    move = chess.Move.from_uci(bm[0].split()[1])
    from_rank = chess.square_rank(move.from_square)
    to_rank = chess.square_rank(move.to_square)
    assert not (from_rank == 0 and to_rank != 0)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/variants/first_rank_lock/ -v
```

Expected: ERRORS (engine file not found).

- [ ] **Step 3: Write engine.py**

```python
# engines/variants/first_rank_lock/engine.py
import sys
import os
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.join(_HERE, '..', '..', 'base')
sys.path.insert(0, _HERE)
sys.path.insert(1, _BASE)

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
            try:
                board.push_uci(uci)
            except Exception as e:
                _log(f'illegal move in position: {uci} ({e})')
                break


def _handle_go(board, line):
    parts = line.split()
    max_depth = None
    deadline = None
    if 'infinite' in parts:
        deadline = time.time() + 30.0
    elif 'depth' in parts:
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
            print('id name FirstRankLockEngine')
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
            try:
                move = _handle_go(board, line)
                if move:
                    print(f'bestmove {move.uci()}')
                    sys.stdout.flush()
                    _log(f'> bestmove {move.uci()}')
                else:
                    print('bestmove 0000')
                    sys.stdout.flush()
            except Exception as e:
                _log(f'error in go handler: {e}')
                print('bestmove 0000')
                sys.stdout.flush()
        elif line == 'stop':
            pass
        elif line == 'quit':
            break


if __name__ == '__main__':
    uci_loop()
```

- [ ] **Step 4: Write search.py**

```python
# engines/variants/first_rank_lock/search.py
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

    # VARIANT: first 10 moves, pieces on own back rank cannot leave it
    moves = list(board.legal_moves)
    if board.fullmove_number <= 10:
        own_back = 0 if board.turn == chess.WHITE else 7
        filtered = [m for m in moves
                    if not (chess.square_rank(m.from_square) == own_back and
                            chess.square_rank(m.to_square) != own_back)]
        if filtered:
            moves = filtered

    orig_alpha = alpha
    best_score = -10_000_000
    best_move = None
    any_completed = False

    for move in _order_moves(board, moves, tt_move):
        board.push(move)
        score, _ = _alpha_beta(board, depth - 1, -beta, -alpha, deadline)
        board.pop()
        if score is None:
            if not any_completed:
                continue
            return None, best_move
        any_completed = True
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

    if not any_completed:
        return None, None
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

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/variants/first_rank_lock/ -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add engines/variants/first_rank_lock/ tests/variants/first_rank_lock/
git commit -m "feat: add first_rank_lock variant engine"
```

---

### Task 6: aggro_push variant

**Files:**
- Create: `tests/variants/aggro_push/test_aggro_push.py`
- Create: `engines/variants/aggro_push/engine.py`
- Create: `engines/variants/aggro_push/search.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/variants/aggro_push/test_aggro_push.py
import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engines', 'variants', 'aggro_push', 'engine.py')


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
    assert any(l.startswith('id name AggroPushEngine') for l in lines)


def test_isready_response():
    lines = _run(['isready', 'quit'])
    assert 'readyok' in lines


def test_bestmove_startpos():
    lines = _run(['position startpos', 'go depth 3', 'quit'], timeout=60)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    move = chess.Move.from_uci(bm[0].split()[1])
    assert move in board.legal_moves


def test_aggro_push_pushes_pawn_when_no_captures():
    # From startpos no captures are available; engine must push a pawn immediately
    lines = _run(['position startpos', 'go depth 5', 'quit'], timeout=30)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    move = chess.Move.from_uci(bm[0].split()[1])
    piece = board.piece_at(move.from_square)
    assert piece is not None
    assert piece.piece_type == chess.PAWN
    assert not board.is_capture(move)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/variants/aggro_push/ -v
```

Expected: ERRORS (engine file not found).

- [ ] **Step 3: Write engine.py**

```python
# engines/variants/aggro_push/engine.py
import sys
import os
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.join(_HERE, '..', '..', 'base')
sys.path.insert(0, _HERE)
sys.path.insert(1, _BASE)

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
            try:
                board.push_uci(uci)
            except Exception as e:
                _log(f'illegal move in position: {uci} ({e})')
                break


def _handle_go(board, line):
    parts = line.split()
    max_depth = None
    deadline = None
    if 'infinite' in parts:
        deadline = time.time() + 30.0
    elif 'depth' in parts:
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
            print('id name AggroPushEngine')
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
            try:
                move = _handle_go(board, line)
                if move:
                    print(f'bestmove {move.uci()}')
                    sys.stdout.flush()
                    _log(f'> bestmove {move.uci()}')
                else:
                    print('bestmove 0000')
                    sys.stdout.flush()
            except Exception as e:
                _log(f'error in go handler: {e}')
                print('bestmove 0000')
                sys.stdout.flush()
        elif line == 'stop':
            pass
        elif line == 'quit':
            break


if __name__ == '__main__':
    uci_loop()
```

- [ ] **Step 4: Write search.py**

```python
# engines/variants/aggro_push/search.py
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
    any_completed = False

    for move in _order_moves(board, list(board.legal_moves), tt_move):
        board.push(move)
        score, _ = _alpha_beta(board, depth - 1, -beta, -alpha, deadline)
        board.pop()
        if score is None:
            if not any_completed:
                continue
            return None, best_move
        any_completed = True
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

    if not any_completed:
        return None, None
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

    # VARIANT: if no captures, return push of most advanced pawn immediately
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

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/variants/aggro_push/ -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add engines/variants/aggro_push/ tests/variants/aggro_push/
git commit -m "feat: add aggro_push variant engine"
```

---

### Task 7: fortress variant

**Files:**
- Create: `tests/variants/fortress/test_fortress.py`
- Create: `engines/variants/fortress/engine.py`
- Create: `engines/variants/fortress/search.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/variants/fortress/test_fortress.py
import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engines', 'variants', 'fortress', 'engine.py')


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
    assert any(l.startswith('id name FortressEngine') for l in lines)


def test_isready_response():
    lines = _run(['isready', 'quit'])
    assert 'readyok' in lines


def test_bestmove_startpos():
    lines = _run(['position startpos', 'go depth 3', 'quit'], timeout=60)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    move = chess.Move.from_uci(bm[0].split()[1])
    assert move in board.legal_moves


def test_fortress_no_advance_after_move_15():
    # fullmove=16: white must not move to ranks 4-7 (rank indices >= 4)
    fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 16'
    lines = _run([f'position fen {fen}', 'go depth 1', 'quit'])
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board(fen)
    move = chess.Move.from_uci(bm[0].split()[1])
    to_rank = chess.square_rank(move.to_square)
    assert to_rank <= 3
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/variants/fortress/ -v
```

Expected: ERRORS (engine file not found).

- [ ] **Step 3: Write engine.py**

```python
# engines/variants/fortress/engine.py
import sys
import os
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.join(_HERE, '..', '..', 'base')
sys.path.insert(0, _HERE)
sys.path.insert(1, _BASE)

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
            try:
                board.push_uci(uci)
            except Exception as e:
                _log(f'illegal move in position: {uci} ({e})')
                break


def _handle_go(board, line):
    parts = line.split()
    max_depth = None
    deadline = None
    if 'infinite' in parts:
        deadline = time.time() + 30.0
    elif 'depth' in parts:
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
            print('id name FortressEngine')
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
            try:
                move = _handle_go(board, line)
                if move:
                    print(f'bestmove {move.uci()}')
                    sys.stdout.flush()
                    _log(f'> bestmove {move.uci()}')
                else:
                    print('bestmove 0000')
                    sys.stdout.flush()
            except Exception as e:
                _log(f'error in go handler: {e}')
                print('bestmove 0000')
                sys.stdout.flush()
        elif line == 'stop':
            pass
        elif line == 'quit':
            break


if __name__ == '__main__':
    uci_loop()
```

- [ ] **Step 4: Write search.py**

```python
# engines/variants/fortress/search.py
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

    # VARIANT: after move 15, stay in own half of the board
    moves = list(board.legal_moves)
    if board.fullmove_number > 15:
        if board.turn == chess.WHITE:
            filtered = [m for m in moves if chess.square_rank(m.to_square) <= 3]
        else:
            filtered = [m for m in moves if chess.square_rank(m.to_square) >= 4]
        if filtered:
            moves = filtered

    orig_alpha = alpha
    best_score = -10_000_000
    best_move = None
    any_completed = False

    for move in _order_moves(board, moves, tt_move):
        board.push(move)
        score, _ = _alpha_beta(board, depth - 1, -beta, -alpha, deadline)
        board.pop()
        if score is None:
            if not any_completed:
                continue
            return None, best_move
        any_completed = True
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

    if not any_completed:
        return None, None
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

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/variants/fortress/ -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add engines/variants/fortress/ tests/variants/fortress/
git commit -m "feat: add fortress variant engine"
```

---

### Task 8: random_blunder variant

**Files:**
- Create: `tests/variants/random_blunder/test_random_blunder.py`
- Create: `engines/variants/random_blunder/engine.py`
- Create: `engines/variants/random_blunder/search.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/variants/random_blunder/test_random_blunder.py
import subprocess
import sys
import os
import chess

ENGINE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'engines', 'variants', 'random_blunder', 'engine.py')


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
    assert any(l.startswith('id name RandomBlunderEngine') for l in lines)


def test_isready_response():
    lines = _run(['isready', 'quit'])
    assert 'readyok' in lines


def test_bestmove_startpos():
    lines = _run(['position startpos', 'go depth 3', 'quit'], timeout=60)
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board()
    move = chess.Move.from_uci(bm[0].split()[1])
    assert move in board.legal_moves


def test_random_blunder_skips_search_on_multiple_of_5():
    # fullmove=5: engine returns random move without searching (no info depth lines)
    fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 5'
    lines = _run([f'position fen {fen}', 'go depth 5', 'quit'])
    info_lines = [l for l in lines if l.startswith('info depth')]
    assert len(info_lines) == 0
    bm = [l for l in lines if l.startswith('bestmove')]
    assert len(bm) == 1
    board = chess.Board(fen)
    move = chess.Move.from_uci(bm[0].split()[1])
    assert move in board.legal_moves
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/variants/random_blunder/ -v
```

Expected: ERRORS (engine file not found).

- [ ] **Step 3: Write engine.py**

```python
# engines/variants/random_blunder/engine.py
import sys
import os
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.join(_HERE, '..', '..', 'base')
sys.path.insert(0, _HERE)
sys.path.insert(1, _BASE)

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
            try:
                board.push_uci(uci)
            except Exception as e:
                _log(f'illegal move in position: {uci} ({e})')
                break


def _handle_go(board, line):
    parts = line.split()
    max_depth = None
    deadline = None
    if 'infinite' in parts:
        deadline = time.time() + 30.0
    elif 'depth' in parts:
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
            print('id name RandomBlunderEngine')
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
            try:
                move = _handle_go(board, line)
                if move:
                    print(f'bestmove {move.uci()}')
                    sys.stdout.flush()
                    _log(f'> bestmove {move.uci()}')
                else:
                    print('bestmove 0000')
                    sys.stdout.flush()
            except Exception as e:
                _log(f'error in go handler: {e}')
                print('bestmove 0000')
                sys.stdout.flush()
        elif line == 'stop':
            pass
        elif line == 'quit':
            break


if __name__ == '__main__':
    uci_loop()
```

- [ ] **Step 4: Write search.py**

```python
# engines/variants/random_blunder/search.py
import random
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
    any_completed = False

    for move in _order_moves(board, list(board.legal_moves), tt_move):
        board.push(move)
        score, _ = _alpha_beta(board, depth - 1, -beta, -alpha, deadline)
        board.pop()
        if score is None:
            if not any_completed:
                continue
            return None, best_move
        any_completed = True
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

    if not any_completed:
        return None, None
    if best_move is None:
        return 0, None

    flag = EXACT if orig_alpha < best_score < beta else (LOWER if best_score >= beta else UPPER)
    _tt.store(key, depth, flag, best_score, best_move)
    return best_score, best_move


def iterative_deepening(board, max_depth=None, deadline=None):
    moves = list(board.legal_moves)
    if not moves:
        return None

    # VARIANT: on every 5th fullmove, return a random legal move without searching
    if board.fullmove_number % 5 == 0:
        return random.choice(moves)

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

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/variants/random_blunder/ -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add engines/variants/random_blunder/ tests/variants/random_blunder/
git commit -m "feat: add random_blunder variant engine"
```

---

### Task 9: Final integration verification

**Files:** None (read-only verification)

- [ ] **Step 1: Run all variant tests together**

```bash
pytest tests/variants/ -v
```

Expected: 32 tests PASSED (4 per variant × 8 variants).

- [ ] **Step 2: Smoke test each variant with the spec command**

```bash
BASE=/Users/kimet/Documents/GitHub/Probabilistic-Poker-Engine-PPE-/Probabilistic-Poker-Engine-PPE-/Probabilistic-Poker-Engine-PPE-/Point72Hackathon
for name in no_pawn_push mirror_queen king_walk bishops_only first_rank_lock aggro_push fortress random_blunder; do
  echo -n "$name: "
  echo -e "uci\nisready\nposition startpos\ngo depth 3\nquit" | python3 "$BASE/engines/variants/$name/engine.py" | grep -E "uciok|readyok|bestmove"
done
```

Expected: Each variant prints `uciok`, `readyok`, and `bestmove <valid-move>`.

- [ ] **Step 3: Run base tests to confirm no regressions**

```bash
pytest tests/base/ -v
```

Expected: 20 tests PASSED (all base tests still pass).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: complete all 8 variant engines with tests"
```
