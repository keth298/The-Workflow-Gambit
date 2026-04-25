from __future__ import annotations

import chess
import chess.polyglot

from evaluation import evaluate
from transposition_table import TT_EXACT, TT_LOWER, TT_UPPER, TranspositionTable

MATE_SCORE = 30000
MAX_DEPTH = 64
INF = 32000
DELTA_PRUNING_MARGIN = 200
NODE_POLL_INTERVAL = 1024

MVV_LVA_SCORES = {
    (attacker, victim): (value_victim * 10) - value_attacker
    for attacker, value_attacker in {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 0,
    }.items()
    for victim, value_victim in {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 0,
    }.items()
}

tt = TranspositionTable()


class SearchTimeout(Exception):
    pass


def _budget_depth_limit(budget) -> int | None:
    depth_limit = getattr(budget, "depth_limit", None)
    if callable(depth_limit):
        depth_limit = depth_limit()
    return max(1, depth_limit) if depth_limit is not None else None


def _touch_node(nodes: list[int], budget) -> None:
    nodes[0] += 1
    if nodes[0] % NODE_POLL_INTERVAL == 0 and budget.should_stop():
        raise SearchTimeout


def _terminal_score(board: chess.Board, ply: int) -> int | None:
    if board.is_checkmate():
        return -MATE_SCORE + ply
    if (
        board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_fifty_moves()
        or board.is_repetition(3)
    ):
        return 0
    return None


def _captured_piece_type(board: chess.Board, move: chess.Move) -> int | None:
    if board.is_en_passant(move):
        return chess.PAWN
    captured = board.piece_at(move.to_square)
    return captured.piece_type if captured is not None else None


def _move_priority(board: chess.Board, move: chess.Move, tt_move: chess.Move | None) -> int:
    if tt_move is not None and move == tt_move:
        return 20000
    if board.is_capture(move):
        attacker = board.piece_at(move.from_square)
        victim_type = _captured_piece_type(board, move)
        if attacker is None or victim_type is None:
            return 10000
        return 10000 + MVV_LVA_SCORES[(attacker.piece_type, victim_type)]
    return 0


def _order_moves(board: chess.Board, moves: list[chess.Move], tt_move: chess.Move | None) -> list[chess.Move]:
    return sorted(moves, key=lambda move: _move_priority(board, move, tt_move), reverse=True)


def quiescence(board: chess.Board, alpha: int, beta: int, ply: int, nodes: list[int], budget) -> int:
    _touch_node(nodes, budget)

    terminal = _terminal_score(board, ply)
    if terminal is not None:
        return terminal

    stand_pat = evaluate(board)
    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    capture_moves = _order_moves(board, list(board.generate_pseudo_legal_captures()), None)
    for move in capture_moves:
        if not board.is_legal(move):
            continue

        victim_type = _captured_piece_type(board, move)
        captured_value = 0 if victim_type is None else MVV_LVA_SCORES[(chess.KING, victim_type)] // 10
        if stand_pat + captured_value + DELTA_PRUNING_MARGIN < alpha:
            continue

        board.push(move)
        score = -quiescence(board, -beta, -alpha, ply + 1, nodes, budget)
        board.pop()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


def alpha_beta(board: chess.Board, depth: int, alpha: int, beta: int, ply: int, nodes: list[int], budget) -> int:
    _touch_node(nodes, budget)

    key = chess.polyglot.zobrist_hash(board)
    entry = tt.get(key)
    original_alpha = alpha

    if entry is not None and entry[1] >= depth:
        score, _, flag, _ = entry
        if flag == TT_EXACT:
            return score
        if flag == TT_LOWER:
            alpha = max(alpha, score)
        elif flag == TT_UPPER:
            beta = min(beta, score)
        if alpha >= beta:
            return score

    terminal = _terminal_score(board, ply)
    if terminal is not None:
        return terminal

    if depth == 0:
        return quiescence(board, alpha, beta, ply, nodes, budget)

    tt_move = entry[3] if entry is not None else None
    best_move: chess.Move | None = None
    best_score = -INF

    for move in _order_moves(board, list(board.legal_moves), tt_move):
        board.push(move)
        score = -alpha_beta(board, depth - 1, -beta, -alpha, ply + 1, nodes, budget)
        board.pop()

        if score > best_score:
            best_score = score
            best_move = move
        if score > alpha:
            alpha = score
        if alpha >= beta:
            tt.put(key, alpha, depth, TT_LOWER, best_move)
            return alpha

    flag = TT_UPPER if alpha <= original_alpha else TT_EXACT
    tt.put(key, alpha, depth, flag, best_move)
    return alpha


def best_move(board: chess.Board, budget) -> chess.Move | None:
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return None

    budget.start()
    tt.clear()

    best = legal_moves[0]
    nodes = [0]
    depth_limit = _budget_depth_limit(budget)

    for depth in range(1, MAX_DEPTH + 1):
        if depth_limit is not None and depth > depth_limit:
            break

        try:
            score, move = _search_root(board, depth, nodes, budget)
        except SearchTimeout:
            break

        if move is not None:
            best = move

        print(f"info depth {depth} score cp {score} nodes {nodes[0]} pv {best.uci()}", flush=True)

        if budget.should_stop():
            break
        if abs(score) >= MATE_SCORE - MAX_DEPTH:
            break

    return best


def _search_root(board: chess.Board, depth: int, nodes: list[int], budget) -> tuple[int, chess.Move | None]:
    alpha, beta = -INF, INF
    best_score = -INF
    best_move: chess.Move | None = None

    entry = tt.get(chess.polyglot.zobrist_hash(board))
    tt_move = entry[3] if entry is not None else None

    for move in _order_moves(board, list(board.legal_moves), tt_move):
        board.push(move)
        score = -alpha_beta(board, depth - 1, -beta, -alpha, 1, nodes, budget)
        board.pop()

        if score > best_score:
            best_score = score
            best_move = move
        if score > alpha:
            alpha = score

        if nodes[0] % NODE_POLL_INTERVAL == 0 and budget.should_stop():
            break

    return alpha, best_move
