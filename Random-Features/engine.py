#!/usr/bin/env python3
"""
Final UCI chess engine — base variant.
Variant feature: standard alpha-beta with no behavioral restriction
Selected by tournament: highest total score, best win rate vs base engine.
"""

import sys
import time
import chess
import chess.polyglot

# ── Transposition Table ─────────────────────────────────────────────────────
EXACT = 0
LOWER = 1
UPPER = 2


class TranspositionTable:
    def __init__(self):
        self._table = {}

    def probe(self, key):
        return self._table.get(key)

    def store(self, key, depth, flag, score, best_move):
        existing = self._table.get(key)
        if existing is None or depth >= existing[0]:
            self._table[key] = (depth, flag, score, best_move)

    def clear(self):
        self._table.clear()

# ── Evaluation ──────────────────────────────────────────────────────────────
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
    return total < 1300


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

# ── Search (base variant) ────────────────────────────────────────────
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
                continue  # keep trying other moves in case they complete quickly
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

# ── UCI Interface ────────────────────────────────────────────────────────────
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
        deadline = time.time() + 30.0  # search up to 30s, effectively unlimited for hackathon
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
            pass  # search already finished synchronously; nothing to stop

        elif line == 'quit':
            break


if __name__ == '__main__':
    uci_loop()
