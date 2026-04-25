"""
Iterative-deepening alpha-beta search with:
  - Transposition table (Zobrist hash)
  - Null-move pruning
  - Quiescence search (captures + promotions)
  - Move ordering: retrieval priors → policy network → MVV-LVA captures first

Evaluation blending
-------------------
  eval = α × retrieval_eval + (1-α) × neural_eval
  where α = retrieval.confidence(board)

Because retrieval is expensive, it is only called at the root and depth 1;
deeper nodes use the neural evaluator exclusively.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

import chess
import chess.polyglot

sys.path.insert(0, str(Path(__file__).parent))
from evaluator import NeuralEvaluator
from retrieval  import RetrievalEngine

# ── Constants ─────────────────────────────────────────────────────────────────

INF    = 1_000_000
MATE   = 900_000    # centipawns equivalent (we work in [-1, +1] floats; mate = ±1 effectively)

# Piece values for MVV-LVA (centipawns)
_PIECE_VAL = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
    chess.ROOK: 500, chess.QUEEN: 900,  chess.KING: 20_000,
}


# ── Transposition table entry ─────────────────────────────────────────────────

EXACT   = 0
LOWER   = 1   # alpha (fail-low)
UPPER   = 2   # beta  (fail-high / cut)

class _TTEntry:
    __slots__ = ("depth", "score", "flag", "best_move")
    def __init__(self, depth: int, score: float, flag: int, best_move: Optional[chess.Move]):
        self.depth     = depth
        self.score     = score
        self.flag      = flag
        self.best_move = best_move


# ── Move ordering helpers ─────────────────────────────────────────────────────

def _mvv_lva(board: chess.Board, move: chess.Move) -> int:
    """Higher = better for ordering captures."""
    victim = board.piece_at(move.to_square)
    if victim is None:
        return 0
    attacker = board.piece_at(move.from_square)
    v_val    = _PIECE_VAL.get(victim.piece_type,  0)
    a_val    = _PIECE_VAL.get(attacker.piece_type, 0) if attacker else 0
    return v_val * 10 - a_val


def _order_moves(board: chess.Board,
                 move_priors: dict[str, float],
                 tt_move: Optional[chess.Move]) -> list[chess.Move]:
    """Return legal moves sorted by priority (TT best → captures → priors)."""
    moves = list(board.legal_moves)
    tt_uci = tt_move.uci() if tt_move else None

    def key(m: chess.Move) -> float:
        uci = m.uci()
        if uci == tt_uci:
            return 1e9
        if board.is_capture(m):
            return 1e6 + _mvv_lva(board, m)
        return move_priors.get(uci, 0.0)

    moves.sort(key=key, reverse=True)
    return moves


# ── Search ────────────────────────────────────────────────────────────────────

class Searcher:
    def __init__(self,
                 neural: NeuralEvaluator,
                 retrieval: RetrievalEngine) -> None:
        self._neural    = neural
        self._retrieval = retrieval
        self._tt: dict[int, _TTEntry] = {}
        self._nodes    = 0
        self._stop     = False
        self._deadline  = 0.0     # epoch seconds

    # ── Evaluation ────────────────────────────────────────────────────────────

    def _blend_eval(self, board: chess.Board, use_retrieval: bool) -> float:
        """Blended position score ∈ [-1, +1] from side-to-move perspective."""
        if use_retrieval:
            ret_score, _, conf = self._retrieval.query_all(board)
            if conf >= 0.5:
                nn_score = self._neural.evaluate(board)
                return conf * ret_score + (1.0 - conf) * nn_score
        return self._neural.evaluate(board)

    # ── Quiescence search ─────────────────────────────────────────────────────

    def _qsearch(self, board: chess.Board, alpha: float, beta: float, ply: int) -> float:
        if self._stop:
            return 0.0

        stand_pat = self._blend_eval(board, use_retrieval=False)
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        if ply >= 8:          # cap quiescence depth
            return alpha

        for move in board.legal_moves:
            if not (board.is_capture(move) or move.promotion):
                continue
            board.push(move)
            score = -self._qsearch(board, -beta, -alpha, ply + 1)
            board.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    # ── Alpha-beta ────────────────────────────────────────────────────────────

    def _alphabeta(self,
                   board: chess.Board,
                   depth: int,
                   alpha: float,
                   beta: float,
                   ply: int,
                   root_priors: dict[str, float]) -> float:
        if self._stop:
            return 0.0

        self._nodes += 1

        # Terminal checks
        if board.is_checkmate():
            return -(1.0 + 0.001 * (20 - ply))   # prefer quicker mates
        if board.is_stalemate() or board.is_insufficient_material() \
                or board.can_claim_draw():
            return 0.0

        if depth <= 0:
            return self._qsearch(board, alpha, beta, 0)

        # Transposition table
        key = chess.polyglot.zobrist_hash(board)
        tt  = self._tt.get(key)
        if tt and tt.depth >= depth:
            if tt.flag == EXACT:
                return tt.score
            if tt.flag == LOWER and tt.score >= beta:
                return beta
            if tt.flag == UPPER and tt.score <= alpha:
                return alpha

        tt_move = tt.best_move if tt else None

        # Null-move pruning (skip at < depth 3 or in check)
        R = 2
        if depth >= 3 and not board.is_check() and ply > 0:
            board.push(chess.Move.null())
            nm_score = -self._alphabeta(board, depth - 1 - R, -beta, -beta + 0.001, ply + 1, {})
            board.pop()
            if nm_score >= beta:
                return beta

        # Only use retrieval priors at root ply
        priors = root_priors if ply == 0 else {}
        use_ret = ply <= 1

        moves     = _order_moves(board, priors, tt_move)
        best_move = None
        orig_alpha = alpha

        for move in moves:
            board.push(move)
            score = -self._alphabeta(board, depth - 1, -beta, -alpha, ply + 1, {})
            board.pop()

            if self._stop:
                break

            if score > alpha:
                alpha     = score
                best_move = move
            if score >= beta:
                # Store cut-node
                self._tt[key] = _TTEntry(depth, beta, LOWER, best_move)
                return beta

        # Store result in TT
        if best_move is not None:
            flag = EXACT if alpha > orig_alpha else UPPER
        else:
            flag = UPPER
        self._tt[key] = _TTEntry(depth, alpha, flag, best_move)

        return alpha

    # ── Iterative deepening ───────────────────────────────────────────────────

    def search(self, board: chess.Board, time_ms: int) -> chess.Move:
        """Run iterative-deepening; return the best move found."""
        self._stop     = False
        self._nodes    = 0
        self._deadline = time.time() + time_ms / 1000.0

        # Pre-fetch retrieval priors for the root (expensive, do once)
        _, root_priors, _ = self._retrieval.query_all(board)
        # Fall back to neural policy if retrieval empty
        if not root_priors:
            root_priors = self._neural.policy(board)

        legal = list(board.legal_moves)
        if not legal:
            return chess.Move.null()
        if len(legal) == 1:
            return legal[0]

        best_move  = legal[0]
        best_score = -INF

        for depth in range(1, 64):
            if time.time() >= self._deadline:
                break

            alpha = -1.1
            beta  =  1.1
            move_scores: list[tuple[float, chess.Move]] = []

            ordered = _order_moves(board, root_priors,
                                   best_move if best_move else None)

            for move in ordered:
                if time.time() >= self._deadline:
                    self._stop = True
                    break

                board.push(move)
                score = -self._alphabeta(board, depth - 1, -beta, -alpha,
                                         ply=1, root_priors={})
                board.pop()

                move_scores.append((score, move))
                if score > alpha:
                    alpha = score
                    best_move  = move
                    best_score = score

            if not self._stop:
                # Update priors for next iteration based on root scores
                total_sc = sum(max(0.001, s + 1.1) for s, _ in move_scores)
                root_priors = {
                    m.uci(): max(0.001, s + 1.1) / total_sc
                    for s, m in move_scores
                }
                print(
                    f"info depth {depth} score cp {int(best_score * 100)} "
                    f"nodes {self._nodes} pv {best_move.uci()}",
                    flush=True,
                )

        return best_move
