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
