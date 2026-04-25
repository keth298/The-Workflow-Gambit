# eval.py — Evaluation: material, PST, pawn structure, king safety, mobility

from board import (
    WHITE, BLACK,
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK,
    lsb, pop_lsb, popcount, bit,
    file_of, rank_of,
    sliding_attacks, KNIGHT_ATTACKS, KING_ATTACKS, PAWN_ATTACKS,
    BISHOP_DIRS, ROOK_DIRS, QUEEN_DIRS,
    FILE, RANK, FULL, NOT_A, NOT_H
)

INF = 10_000_000

# ── Material (centipawns) ─────────────────────────────────────────────────────
MATERIAL = [100, 320, 330, 500, 900, 20000,
            100, 320, 330, 500, 900, 20000]

# Phase weights for tapering (N=1, B=1, R=2, Q=4). Max phase = 24.
_PHASE_W = [0, 1, 1, 2, 4, 0,  0, 1, 1, 2, 4, 0]
MAX_PHASE = 24

# ── Piece-square tables ───────────────────────────────────────────────────────
def _pst(table_r8_to_r1):
    out = [0] * 64
    for rank in range(8):
        for file in range(8):
            src = (7 - rank) * 8 + file
            dst = rank * 8 + file
            out[dst] = table_r8_to_r1[src]
    return out

def _mirror(table):
    out = [0] * 64
    for sq in range(64):
        out[sq] = table[(7 - rank_of(sq)) * 8 + file_of(sq)]
    return out

# Middlegame PSTs
_MG_PAWN = _pst([
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
])
_MG_KNIGHT = _pst([
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
])
_MG_BISHOP = _pst([
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
])
_MG_ROOK = _pst([
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
])
_MG_QUEEN = _pst([
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
])
_MG_KING = _pst([
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
])

# Endgame PSTs — king active, pawns advanced
_EG_PAWN = _pst([
     0,  0,  0,  0,  0,  0,  0,  0,
    80, 80, 80, 80, 80, 80, 80, 80,
    50, 50, 50, 50, 50, 50, 50, 50,
    30, 30, 30, 30, 30, 30, 30, 30,
    20, 20, 20, 20, 20, 20, 20, 20,
    10, 10, 10, 10, 10, 10, 10, 10,
     5,  5,  5,  5,  5,  5,  5,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
])
_EG_KING = _pst([
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50,
])

# PST[piece][sq] -> (mg_bonus, eg_bonus)
PST = [None] * 12
_mg = [_MG_PAWN, _MG_KNIGHT, _MG_BISHOP, _MG_ROOK, _MG_QUEEN, _MG_KING]
_eg = [_EG_PAWN, _MG_KNIGHT, _MG_BISHOP, _MG_ROOK, _MG_QUEEN, _EG_KING]
for i in range(6):
    PST[i]     = list(zip(_mg[i], _eg[i]))                    # white
    PST[i + 6] = list(zip(_mirror(_mg[i]), _mirror(_eg[i])))  # black

# ── Pawn structure masks ──────────────────────────────────────────────────────
# PASSED_MASK[side][sq] = squares that must be free of enemy pawns for sq to be passed
_PASSED = [[0]*64, [0]*64]
# ISOLATED_MASK[sq] = adjacent file squares (enemy pawns here = not isolated)
_ADJ_FILES = [0]*64

for _sq in range(64):
    _f, _r = file_of(_sq), rank_of(_sq)
    # adjacent file mask (all ranks)
    _adj = 0
    if _f > 0: _adj |= FILE[_f - 1]
    if _f < 7: _adj |= FILE[_f + 1]
    _ADJ_FILES[_sq] = _adj

    # white passed mask: same file + adj files, ranks above sq
    _ahead_w = 0
    for _rr in range(_r + 1, 8):
        for _ff in range(max(0, _f-1), min(7, _f+1) + 1):
            _ahead_w |= bit(_rr * 8 + _ff)
    _PASSED[WHITE][_sq] = _ahead_w

    # black passed mask: ranks below sq
    _ahead_b = 0
    for _rr in range(0, _r):
        for _ff in range(max(0, _f-1), min(7, _f+1) + 1):
            _ahead_b |= bit(_rr * 8 + _ff)
    _PASSED[BLACK][_sq] = _ahead_b

# Passed pawn bonus by rank (from own side's perspective, rank 1=0 .. rank 7=6)
_PASSED_BONUS = [0, 10, 20, 35, 55, 80, 120, 0]

# ── King zone attack weights ──────────────────────────────────────────────────
_ATTACKER_WEIGHT = [0, 20, 20, 40, 80, 0,  0, 20, 20, 40, 80, 0]

def _king_zone(sq):
    """3x3 zone around king plus one rank ahead."""
    bb = KING_ATTACKS[sq] | bit(sq)
    return bb & FULL

# ── Main evaluation ───────────────────────────────────────────────────────────
def evaluate(board):
    """
    Tapered static evaluation (middlegame↔endgame blend).
    Returns score from the perspective of the side to move.
    """
    mg, eg = 0, 0
    phase  = 0

    # ── Material + PST ────────────────────────────────────────────────────────
    for i in range(12):
        bb   = board.pieces[i]
        sign = 1 if i < 6 else -1
        phase += popcount(bb) * _PHASE_W[i]
        while bb:
            sq, bb = pop_lsb(bb)
            mg_b, eg_b = PST[i][sq]
            mg += sign * (MATERIAL[i] + mg_b)
            eg += sign * (MATERIAL[i] + eg_b)

    # ── Pawn structure ────────────────────────────────────────────────────────
    wp = board.pieces[WP]
    bp = board.pieces[BP]

    for side, my_pawns, opp_pawns, sign in (
        (WHITE, wp, bp,  1),
        (BLACK, bp, wp, -1),
    ):
        bb = my_pawns
        while bb:
            sq, bb = pop_lsb(bb)
            f = file_of(sq)
            r = rank_of(sq) if side == WHITE else 7 - rank_of(sq)

            # Doubled pawn — another friendly pawn on the same file ahead
            file_mask = FILE[f]
            if popcount(my_pawns & file_mask) > 1:
                mg += sign * -15
                eg += sign * -20

            # Isolated pawn — no friendly pawns on adjacent files
            if not (my_pawns & _ADJ_FILES[sq]):
                mg += sign * -15
                eg += sign * -25

            # Passed pawn — no enemy pawns blocking or attacking ahead
            if not (opp_pawns & _PASSED[side][sq]):
                mg += sign * (_PASSED_BONUS[r] // 2)
                eg += sign * _PASSED_BONUS[r]

    # ── Bishop pair ───────────────────────────────────────────────────────────
    if popcount(board.pieces[WB]) >= 2:
        mg += 25; eg += 50
    if popcount(board.pieces[BB]) >= 2:
        mg -= 25; eg -= 50

    # ── Rook on open / semi-open file ─────────────────────────────────────────
    for sq_bb, piece, sign in (
        (board.pieces[WR], WR,  1),
        (board.pieces[BR], BR, -1),
    ):
        bb = sq_bb
        while bb:
            sq, bb = pop_lsb(bb)
            f = file_of(sq)
            if not (wp & FILE[f]) and not (bp & FILE[f]):
                mg += sign * 20; eg += sign * 15   # open file
            elif not ((wp if sign == 1 else bp) & FILE[f]):
                mg += sign * 10; eg += sign * 8    # semi-open

    # ── King safety ───────────────────────────────────────────────────────────
    all_occ = board.all_occ()
    for side, opp, ksq_piece, sign in (
        (WHITE, BLACK, WK,  1),
        (BLACK, WHITE, BK, -1),
    ):
        ksq  = lsb(board.pieces[ksq_piece])
        zone = _king_zone(ksq)

        # Pawn shield — friendly pawns in front of king
        shield = popcount(board.pieces[WP if side==WHITE else BP] & zone)
        mg += sign * shield * 8

        # Count attacker weight hitting the king zone
        opp_base = 6 if side == WHITE else 0
        attack_score = 0
        # Knights
        bb = board.pieces[opp_base + 1]
        while bb:
            sq2, bb = pop_lsb(bb)
            if KNIGHT_ATTACKS[sq2] & zone:
                attack_score += _ATTACKER_WEIGHT[opp_base + 1]
        # Bishops
        bb = board.pieces[opp_base + 2]
        while bb:
            sq2, bb = pop_lsb(bb)
            if sliding_attacks(sq2, all_occ, BISHOP_DIRS) & zone:
                attack_score += _ATTACKER_WEIGHT[opp_base + 2]
        # Rooks
        bb = board.pieces[opp_base + 3]
        while bb:
            sq2, bb = pop_lsb(bb)
            if sliding_attacks(sq2, all_occ, ROOK_DIRS) & zone:
                attack_score += _ATTACKER_WEIGHT[opp_base + 3]
        # Queens
        bb = board.pieces[opp_base + 4]
        while bb:
            sq2, bb = pop_lsb(bb)
            if sliding_attacks(sq2, all_occ, QUEEN_DIRS) & zone:
                attack_score += _ATTACKER_WEIGHT[opp_base + 4]

        mg -= sign * min(attack_score, 400)   # cap so it doesn't dominate

    # ── Mobility ─────────────────────────────────────────────────────────────
    # Count pseudo-legal squares for non-pawn pieces; each sq ≈ 3cp MG, 4cp EG
    for side, sign in ((WHITE, 1), (BLACK, -1)):
        base = 0 if side == WHITE else 6
        own  = board.occ(side)
        mob  = 0
        # Knights
        bb = board.pieces[base + 1]
        while bb:
            sq, bb = pop_lsb(bb)
            mob += popcount(KNIGHT_ATTACKS[sq] & ~own)
        # Bishops
        bb = board.pieces[base + 2]
        while bb:
            sq, bb = pop_lsb(bb)
            mob += popcount(sliding_attacks(sq, all_occ, BISHOP_DIRS) & ~own)
        # Rooks
        bb = board.pieces[base + 3]
        while bb:
            sq, bb = pop_lsb(bb)
            mob += popcount(sliding_attacks(sq, all_occ, ROOK_DIRS) & ~own)
        # Queens
        bb = board.pieces[base + 4]
        while bb:
            sq, bb = pop_lsb(bb)
            mob += popcount(sliding_attacks(sq, all_occ, QUEEN_DIRS) & ~own)
        mg += sign * mob * 3
        eg += sign * mob * 4

    # ── Taper ─────────────────────────────────────────────────────────────────
    phase    = min(phase, MAX_PHASE)
    score    = (mg * phase + eg * (MAX_PHASE - phase)) // MAX_PHASE

    return score if board.side == WHITE else -score
