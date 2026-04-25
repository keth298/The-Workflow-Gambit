# search.py — Negamax alpha-beta + iterative deepening + quiescence search
#             Phase 3: MVV-LVA capture ordering, killer moves, history heuristic

import sys
import time
from board import (
    Board, is_capture, is_promo, from_sq, to_sq, flags,
    move_to_uci,
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK,
)
from eval import evaluate, INF, MATERIAL
import tt as TT

MAX_PLY = 64

# ── MVV-LVA table ─────────────────────────────────────────────────────────────
# Score = VICTIM_VALUE - ATTACKER_VALUE/10  (higher = search first)
# Piece order by value: P=0 N=1 B=2 R=3 Q=4 K=5
_PIECE_VAL = [100, 320, 330, 500, 900, 20000,
              100, 320, 330, 500, 900, 20000]

def _mvv_lva(mv, board):
    victim   = board.piece_at(to_sq(mv))
    attacker = board.piece_at(from_sq(mv))
    v_val = _PIECE_VAL[victim]   if victim   >= 0 else 0
    a_val = _PIECE_VAL[attacker] if attacker >= 0 else 0
    return v_val * 10 - a_val

# ── Searcher (carries killer + history state across recursive calls) ──────────
class Searcher:
    def __init__(self):
        # killers[ply] = [mv1, mv2]
        self.killers  = [[None, None] for _ in range(MAX_PLY)]
        # history[from][to] = score (quiet moves that caused cutoffs)
        self.history  = [[0] * 64 for _ in range(64)]
        self.nodes    = 0
        self.timeout  = False
        self.deadline = 1e18

    def _store_killer(self, mv, ply):
        if mv != self.killers[ply][0]:
            self.killers[ply][1] = self.killers[ply][0]
            self.killers[ply][0] = mv

    def _order(self, moves, board, ply, tt_move=None):
        """Score each move; sort descending."""
        def score(mv):
            if mv == tt_move:
                return 3_000_000          # hash move first — already searched deeply
            if is_capture(mv):
                return 2_000_000 + _mvv_lva(mv, board)
            if is_promo(mv):
                return 1_900_000
            if mv == self.killers[ply][0]:
                return 1_000_000
            if mv == self.killers[ply][1]:
                return 999_999
            return self.history[from_sq(mv)][to_sq(mv)]
        return sorted(moves, key=score, reverse=True)

    # ── Quiescence ────────────────────────────────────────────────────────────
    def quiescence(self, board, alpha, beta):
        self.nodes += 1
        stand_pat = evaluate(board)
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        captures = [m for m in board.legal_moves() if is_capture(m)]
        for mv in sorted(captures, key=lambda m: _mvv_lva(m, board), reverse=True):
            board.make(mv)
            score = -self.quiescence(board, -beta, -alpha)
            board.unmake()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    # ── Negamax alpha-beta ────────────────────────────────────────────────────
    def negamax(self, board, depth, alpha, beta, ply, null_ok=True):
        self.nodes += 1

        if self.nodes & 2047 == 0:
            if time.time() > self.deadline:
                self.timeout = True
                return 0
        if self.timeout:
            return 0

        in_check = board.in_check(board.side)

        # Check extension
        if in_check:
            depth += 1

        if depth == 0:
            return self.quiescence(board, alpha, beta)

        orig_alpha = alpha

        # ── TT probe ─────────────────────────────────────────────────────────
        tt_score, tt_move = TT.probe(board.hash, depth, alpha, beta)
        if tt_score is not None and ply > 0:
            return tt_score

        # ── Null move pruning ─────────────────────────────────────────────────
        R = 3 if depth >= 6 else 2
        if (null_ok and not in_check and ply > 0
                and depth >= R + 1
                and board.has_non_pawn_material(board.side)):
            board.make_null()
            null_score = -self.negamax(board, depth - R - 1, -beta, -beta + 1, ply + 1, null_ok=False)
            board.unmake_null()
            if self.timeout:
                return 0
            if null_score >= beta:
                return beta

        # ── Futility pruning ──────────────────────────────────────────────────
        FUTILITY = {1: 100, 2: 300, 3: 500}
        futility_ok = (
            not in_check
            and depth in FUTILITY
            and alpha < INF - 1000
        )
        static_eval = evaluate(board) if futility_ok else 0

        moves = board.legal_moves()
        if not moves:
            return -(INF - ply) if in_check else 0

        ordered = self._order(moves, board, ply, tt_move)
        best      = -INF
        best_move = None

        for i, mv in enumerate(ordered):
            quiet = not is_capture(mv) and not is_promo(mv)

            # ── Futility pruning ──────────────────────────────────────────────
            if futility_ok and quiet and i > 0:
                if static_eval + FUTILITY[depth] <= alpha:
                    continue

            # ── Late move reduction ───────────────────────────────────────────
            reduce = 0
            if depth >= 3 and i >= 4 and quiet and not in_check:
                reduce = 1 + (i >= 8)

            board.make(mv)
            if reduce:
                score = -self.negamax(board, depth - 1 - reduce, -alpha - 1, -alpha, ply + 1)
                if not self.timeout and score > alpha:
                    score = -self.negamax(board, depth - 1, -beta, -alpha, ply + 1)
            else:
                score = -self.negamax(board, depth - 1, -beta, -alpha, ply + 1)
            board.unmake()

            if self.timeout:
                return alpha

            if score > best:
                best      = score
                best_move = mv
            if score >= beta:
                if quiet:
                    self._store_killer(mv, ply)
                    self.history[from_sq(mv)][to_sq(mv)] += depth * depth
                TT.store(board.hash, depth, beta, TT.LOWERBOUND, mv)
                return beta
            if score > alpha:
                alpha = score

        # ── TT store ─────────────────────────────────────────────────────────
        if best_move:
            flag = TT.EXACT if alpha > orig_alpha else TT.UPPERBOUND
            TT.store(board.hash, depth, best, flag, best_move)

        return best

# ── Iterative deepening entry point ──────────────────────────────────────────
def search(board, movetime_ms=None, max_depth=64):
    """Search from `board`. Returns best move (int)."""
    moves = board.legal_moves()
    if not moves:
        return None
    if len(moves) == 1:
        return moves[0]

    searcher  = Searcher()
    searcher.deadline = time.time() + (movetime_ms / 1000 if movetime_ms else 1e9)
    best_move = None

    for depth in range(1, max_depth + 1):
        searcher.nodes   = 0
        searcher.timeout = False
        alpha    = -INF
        beta     =  INF
        candidate = None

        ordered = searcher._order(moves, board, 0)
        for mv in ordered:
            board.make(mv)
            score = -searcher.negamax(board, depth - 1, -beta, -alpha, 1)
            board.unmake()

            if searcher.timeout:
                break

            if score > alpha:
                alpha     = score
                candidate = mv

        if searcher.timeout:
            break

        if candidate:
            best_move = candidate

        print(
            f"info depth {depth} score cp {alpha} "
            f"nodes {searcher.nodes} pv {move_to_uci(best_move)}",
            file=sys.stderr, flush=True
        )

        if alpha >= INF - 1000:
            break  # forced mate found

    return best_move
