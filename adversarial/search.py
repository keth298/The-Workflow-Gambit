import time
from typing import Optional, Tuple, List
import chess
import chess.polyglot
from evaluation import evaluate, MATERIAL
from transposition_table import TranspositionTable, TT_EXACT, TT_LOWER, TT_UPPER

CHECKMATE_SCORE = 30000
INF = 10_000_000

# MVV-LVA table for capture ordering
MVV_LVA_VICTIM = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 100,
}

MVV_LVA_ATTACKER = {
    chess.PAWN: 6,
    chess.KNIGHT: 5,
    chess.BISHOP: 4,
    chess.ROOK: 3,
    chess.QUEEN: 2,
    chess.KING: 1,
}


def _mvv_lva_score(board: chess.Board, move: chess.Move) -> int:
    """Score a capture move by MVV-LVA."""
    victim = board.piece_type_at(move.to_square)
    attacker = board.piece_type_at(move.from_square)
    if victim is None:
        # En passant
        victim = chess.PAWN
    v = MVV_LVA_VICTIM.get(victim, 0)
    a = MVV_LVA_ATTACKER.get(attacker, 0)
    return v * 10 + a


def _order_moves(board: chess.Board, tt_move: Optional[chess.Move] = None) -> List[chess.Move]:
    """Order moves: TT move first, then checks, then captures (MVV-LVA), then quiets."""
    moves = list(board.legal_moves)
    
    scored = []
    for move in moves:
        if tt_move is not None and move == tt_move:
            score = 100000  # TT move first
        elif board.is_capture(move):
            score = 10000 + _mvv_lva_score(board, move)
        elif move.promotion is not None:
            score = 9000 + (MATERIAL.get(move.promotion, 0))
        else:
            # Check if move gives check
            board.push(move)
            in_check = board.is_check()
            board.pop()
            if in_check:
                score = 8000
            else:
                score = 0
        scored.append((score, move))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored]


def quiescence(board: chess.Board, alpha: int, beta: int, ply: int) -> int:
    """Quiescence search: only consider captures and promotions."""
    stand_pat = evaluate(board, ply)
    if board.turn == chess.BLACK:
        stand_pat = -stand_pat

    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    # Generate captures and promotions
    capture_moves = []
    for move in board.legal_moves:
        if board.is_capture(move) or move.promotion is not None:
            capture_moves.append(move)
    
    # Sort captures by MVV-LVA
    capture_moves.sort(key=lambda m: _mvv_lva_score(board, m) if board.is_capture(m) else 0, reverse=True)

    for move in capture_moves:
        board.push(move)
        score = -quiescence(board, -beta, -alpha, ply + 1)
        board.pop()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


def minimax(board: chess.Board, depth: int, alpha: int, beta: int, ply: int,
            tt: TranspositionTable, is_root: bool = False) -> Tuple[int, Optional[chess.Move]]:
    """Alpha-beta search with TT. Returns (score, best_move) from the side-to-move perspective."""
    key = chess.polyglot.zobrist_hash(board)

    # TT lookup - but at the root, only use TT for move ordering, not cutoffs
    tt_move = None
    tt_entry = tt.get_entry(key)
    if tt_entry is not None:
        tt_move = tt_entry.get("move")
        if not is_root and tt_entry["depth"] >= depth:
            score = tt_entry["score"]
            flag = tt_entry["flag"]
            if flag == TT_EXACT:
                return score, tt_move
            if flag == TT_LOWER and score >= beta:
                return score, tt_move
            if flag == TT_UPPER and score <= alpha:
                return score, tt_move

    # Terminal node or depth=0
    if board.is_game_over():
        score = evaluate(board, ply)
        if board.turn == chess.BLACK:
            score = -score
        return score, None

    if depth <= 0:
        # Quiescence search
        score = quiescence(board, alpha, beta, ply)
        return score, None

    # Check extension: extend search by 1 ply when in check
    in_check = board.is_check()
    extend = 1 if in_check else 0

    best_move = None
    original_alpha = alpha
    ordered = _order_moves(board, tt_move)

    if not ordered:
        # No legal moves (shouldn't happen since we check game_over above)
        score = evaluate(board, ply)
        if board.turn == chess.BLACK:
            score = -score
        return score, None

    for move in ordered:
        board.push(move)
        child_score, _ = minimax(board, depth - 1 + extend, -beta, -alpha, ply + 1, tt, False)
        child_score = -child_score
        board.pop()

        if child_score > alpha:
            alpha = child_score
            best_move = move
            if alpha >= beta:
                break

    # If no move improved alpha, set best_move to first move searched
    # This ensures we always have a move to return from root
    if best_move is None:
        best_move = ordered[0]

    if alpha <= original_alpha:
        flag = TT_UPPER
    elif alpha >= beta:
        flag = TT_LOWER
    else:
        flag = TT_EXACT
    tt.store(key, depth, alpha, flag, best_move)
    return alpha, best_move


def iterative_deepening(board: chess.Board, max_depth: int, time_limit_ms: Optional[int]) -> Optional[chess.Move]:
    tt = TranspositionTable()
    best_move = None
    deadline = time.monotonic() + (time_limit_ms / 1000.0) if time_limit_ms is not None else None

    # Ensure we always have at least one legal move as fallback
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return None
    best_move = legal_moves[0]

    for depth in range(1, max_depth + 1):
        if deadline is not None and time.monotonic() >= deadline:
            break
        score, move = minimax(board, depth, -INF, INF, 0, tt, is_root=True)
        if move is not None:
            best_move = move
        # If we found a checkmate, stop searching
        if abs(score) >= CHECKMATE_SCORE - 100:
            break
        if deadline is not None and time.monotonic() >= deadline:
            break

    return best_move
