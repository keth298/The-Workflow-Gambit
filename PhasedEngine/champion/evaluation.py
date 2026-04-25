from __future__ import annotations

import chess

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


def _flatten_ranks(*ranks: list[int]) -> tuple[int, ...]:
    """Convert rank-8-to-rank-1 tables into chess.square index order."""
    return tuple(value for rank in reversed(ranks) for value in rank)


PAWN_PST_MG = _flatten_ranks(
    [0, 0, 0, 0, 0, 0, 0, 0],
    [50, 50, 50, 50, 50, 50, 50, 50],
    [10, 10, 20, 30, 30, 20, 10, 10],
    [5, 5, 10, 25, 25, 10, 5, 5],
    [0, 0, 0, 20, 20, 0, 0, 0],
    [5, -5, -10, 0, 0, -10, -5, 5],
    [5, 10, 10, -20, -20, 10, 10, 5],
    [0, 0, 0, 0, 0, 0, 0, 0],
)

PAWN_PST_EG = _flatten_ranks(
    [0, 0, 0, 0, 0, 0, 0, 0],
    [80, 80, 80, 80, 80, 80, 80, 80],
    [30, 30, 30, 30, 30, 30, 30, 30],
    [20, 20, 20, 20, 20, 20, 20, 20],
    [10, 10, 10, 10, 10, 10, 10, 10],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [-5, -5, -5, -5, -5, -5, -5, -5],
    [0, 0, 0, 0, 0, 0, 0, 0],
)

KNIGHT_PST_MG = _flatten_ranks(
    [-50, -40, -30, -30, -30, -30, -40, -50],
    [-40, -20, 0, 0, 0, 0, -20, -40],
    [-30, 0, 10, 15, 15, 10, 0, -30],
    [-30, 5, 15, 20, 20, 15, 5, -30],
    [-30, 0, 15, 20, 20, 15, 0, -30],
    [-30, 5, 10, 15, 15, 10, 5, -30],
    [-40, -20, 0, 5, 5, 0, -20, -40],
    [-50, -40, -30, -30, -30, -30, -40, -50],
)

KNIGHT_PST_EG = _flatten_ranks(
    [-50, -40, -30, -30, -30, -30, -40, -50],
    [-40, -20, 0, 0, 0, 0, -20, -40],
    [-30, 0, 10, 15, 15, 10, 0, -30],
    [-30, 5, 15, 20, 20, 15, 5, -30],
    [-30, 0, 15, 20, 20, 15, 0, -30],
    [-30, 5, 10, 15, 15, 10, 5, -30],
    [-40, -20, 0, 5, 5, 0, -20, -40],
    [-50, -40, -30, -30, -30, -30, -40, -50],
)

BISHOP_PST_MG = _flatten_ranks(
    [-20, -10, -10, -10, -10, -10, -10, -20],
    [-10, 0, 0, 0, 0, 0, 0, -10],
    [-10, 0, 5, 10, 10, 5, 0, -10],
    [-10, 5, 5, 10, 10, 5, 5, -10],
    [-10, 0, 10, 10, 10, 10, 0, -10],
    [-10, 10, 10, 10, 10, 10, 10, -10],
    [-10, 5, 0, 0, 0, 0, 5, -10],
    [-20, -10, -10, -10, -10, -10, -10, -20],
)

BISHOP_PST_EG = _flatten_ranks(
    [-20, -10, -10, -10, -10, -10, -10, -20],
    [-10, 0, 0, 0, 0, 0, 0, -10],
    [-10, 0, 5, 10, 10, 5, 0, -10],
    [-10, 5, 5, 10, 10, 5, 5, -10],
    [-10, 0, 10, 10, 10, 10, 0, -10],
    [-10, 10, 10, 10, 10, 10, 10, -10],
    [-10, 5, 0, 0, 0, 0, 5, -10],
    [-20, -10, -10, -10, -10, -10, -10, -20],
)

ROOK_PST_MG = _flatten_ranks(
    [0, 0, 0, 0, 0, 0, 0, 0],
    [5, 10, 10, 10, 10, 10, 10, 5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [0, 0, 0, 5, 5, 0, 0, 0],
)

ROOK_PST_EG = _flatten_ranks(
    [0, 0, 0, 0, 0, 0, 0, 0],
    [5, 10, 10, 10, 10, 10, 10, 5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [0, 0, 0, 5, 5, 0, 0, 0],
)

QUEEN_PST_MG = _flatten_ranks(
    [-20, -10, -10, -5, -5, -10, -10, -20],
    [-10, 0, 0, 0, 0, 0, 0, -10],
    [-10, 0, 5, 5, 5, 5, 0, -10],
    [-5, 0, 5, 5, 5, 5, 0, -5],
    [0, 0, 5, 5, 5, 5, 0, -5],
    [-10, 5, 5, 5, 5, 5, 0, -10],
    [-10, 0, 5, 0, 0, 0, 0, -10],
    [-20, -10, -10, -5, -5, -10, -10, -20],
)

QUEEN_PST_EG = _flatten_ranks(
    [-20, -10, -10, -5, -5, -10, -10, -20],
    [-10, 0, 0, 0, 0, 0, 0, -10],
    [-10, 0, 5, 5, 5, 5, 0, -10],
    [-5, 0, 5, 5, 5, 5, 0, -5],
    [0, 0, 5, 5, 5, 5, 0, -5],
    [-10, 5, 5, 5, 5, 5, 0, -10],
    [-10, 0, 5, 0, 0, 0, 0, -10],
    [-20, -10, -10, -5, -5, -10, -10, -20],
)

KING_MIDDLEGAME_PST = _flatten_ranks(
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-20, -30, -30, -40, -40, -30, -30, -20],
    [-10, -20, -20, -20, -20, -20, -20, -10],
    [20, 20, 0, 0, 0, 0, 20, 20],
    [20, 30, 10, 0, 0, 10, 30, 20],
)

KING_ENDGAME_PST = _flatten_ranks(
    [-50, -40, -30, -20, -20, -30, -40, -50],
    [-30, -20, -10, 0, 0, -10, -20, -30],
    [-30, -10, 20, 30, 30, 20, -10, -30],
    [-30, -10, 30, 40, 40, 30, -10, -30],
    [-30, -10, 30, 40, 40, 30, -10, -30],
    [-30, -10, 20, 30, 30, 20, -10, -30],
    [-30, -30, 0, 0, 0, 0, -30, -30],
    [-50, -30, -30, -30, -30, -30, -30, -50],
)

# Phase weights for each piece type (used for tapered eval)
# Total phase at game start = 4*1 + 4*1 + 4*2 + 2*4 = 4+4+8+8 = 24
PHASE_WEIGHTS = {
    chess.PAWN: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 1,
    chess.ROOK: 2,
    chess.QUEEN: 4,
    chess.KING: 0,
}
MAX_PHASE = 24

# Mobility bonus per extra legal move (centipawns), per piece type
MOBILITY_BONUS = {
    chess.KNIGHT: 4,
    chess.BISHOP: 3,
    chess.ROOK: 2,
    chess.QUEEN: 1,
    chess.PAWN: 0,
    chess.KING: 0,
}

# Passed pawn bonus by rank (from the pawn's own perspective, rank 1..8)
PASSED_PAWN_BONUS = [0, 0, 10, 20, 35, 55, 80, 0]

# Bishop pair bonus (centipawns) awarded when a side has both bishops
BISHOP_PAIR_BONUS = 30

# Outpost bonus for knights
KNIGHT_OUTPOST_BONUS = 20

# King pawn shelter: penalty per file that lacks a friendly pawn
KING_SHELTER_PENALTY = 15

# Rook open/semi-open file bonuses
ROOK_OPEN_FILE_BONUS = 20
ROOK_SEMI_OPEN_FILE_BONUS = 10

# Backward pawn penalty
BACKWARD_PAWN_PENALTY = 15

# Connected rooks bonus (when two friendly rooks see each other on rank or file)
CONNECTED_ROOKS_BONUS = 15

# Rook on 7th rank bonus
ROOK_ON_SEVENTH_BONUS = 30

# Hanging piece bonus: fraction of piece value awarded for attacking an undefended enemy piece
HANGING_PIECE_BONUS_FRACTION = 0.1

# Center control bonus per attack on a center square (d4, e4, d5, e5), scaled by phase
# Only applied in middlegame (phase > 0.3)
CENTER_ATTACK_BONUS = 4

# The four central squares
_CENTER_SQUARES = frozenset([chess.D4, chess.E4, chess.D5, chess.E5])


def is_endgame(board: chess.Board) -> bool:
    queens = board.pieces(chess.QUEEN, chess.WHITE) | board.pieces(chess.QUEEN, chess.BLACK)
    if not queens:
        return True

    white_non_queen = (
        len(board.pieces(chess.ROOK, chess.WHITE))
        + len(board.pieces(chess.BISHOP, chess.WHITE))
        + len(board.pieces(chess.KNIGHT, chess.WHITE))
    )
    black_non_queen = (
        len(board.pieces(chess.ROOK, chess.BLACK))
        + len(board.pieces(chess.BISHOP, chess.BLACK))
        + len(board.pieces(chess.KNIGHT, chess.BLACK))
    )
    return white_non_queen <= 1 and black_non_queen <= 1


def _compute_phase(board: chess.Board) -> float:
    """Return a phase value in [0.0, 1.0]: 1.0 = full middlegame, 0.0 = full endgame."""
    phase = 0
    for piece_type, weight in PHASE_WEIGHTS.items():
        if weight == 0:
            continue
        phase += weight * len(board.pieces(piece_type, chess.WHITE))
        phase += weight * len(board.pieces(piece_type, chess.BLACK))
    # Clamp and normalize
    phase = min(phase, MAX_PHASE)
    return phase / MAX_PHASE


def _pst_bonus_tapered(piece: chess.Piece, square: chess.Square, phase: float) -> int:
    """Return tapered PST bonus interpolated between MG and EG tables."""
    pt = piece.piece_type
    sq = square if piece.color == chess.WHITE else square ^ 56

    if pt == chess.KING:
        mg_val = KING_MIDDLEGAME_PST[sq]
        eg_val = KING_ENDGAME_PST[sq]
    elif pt == chess.PAWN:
        mg_val = PAWN_PST_MG[sq]
        eg_val = PAWN_PST_EG[sq]
    elif pt == chess.KNIGHT:
        mg_val = KNIGHT_PST_MG[sq]
        eg_val = KNIGHT_PST_EG[sq]
    elif pt == chess.BISHOP:
        mg_val = BISHOP_PST_MG[sq]
        eg_val = BISHOP_PST_EG[sq]
    elif pt == chess.ROOK:
        mg_val = ROOK_PST_MG[sq]
        eg_val = ROOK_PST_EG[sq]
    elif pt == chess.QUEEN:
        mg_val = QUEEN_PST_MG[sq]
        eg_val = QUEEN_PST_EG[sq]
    else:
        return 0

    # Interpolate: phase=1.0 means full MG, phase=0.0 means full EG
    return int(phase * mg_val + (1.0 - phase) * eg_val)


def _pawn_structure_bonus(board: chess.Board) -> int:
    score = 0
    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        pawns = list(board.pieces(chess.PAWN, color))
        file_counts = [0] * 8
        for square in pawns:
            file_counts[chess.square_file(square)] += 1

        for count in file_counts:
            if count > 1:
                score -= sign * 20 * (count - 1)

        for square in pawns:
            file_index = chess.square_file(square)
            has_neighbor = False
            if file_index > 0 and file_counts[file_index - 1] > 0:
                has_neighbor = True
            if file_index < 7 and file_counts[file_index + 1] > 0:
                has_neighbor = True
            if not has_neighbor:
                score -= sign * 15

    return score


def _passed_pawn_bonus(board: chess.Board) -> int:
    """Award a bonus for passed pawns."""
    score = 0

    white_pawns = board.pieces(chess.PAWN, chess.WHITE)
    black_pawns = board.pieces(chess.PAWN, chess.BLACK)

    black_pawn_files: dict[int, list[int]] = {}
    for sq in black_pawns:
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        black_pawn_files.setdefault(f, []).append(r)

    white_pawn_files: dict[int, list[int]] = {}
    for sq in white_pawns:
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        white_pawn_files.setdefault(f, []).append(r)

    for sq in white_pawns:
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        is_passed = True
        for adj_f in (f - 1, f, f + 1):
            if adj_f < 0 or adj_f > 7:
                continue
            for br in black_pawn_files.get(adj_f, []):
                if br > r:
                    is_passed = False
                    break
            if not is_passed:
                break
        if is_passed:
            score += PASSED_PAWN_BONUS[r]

    for sq in black_pawns:
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        is_passed = True
        for adj_f in (f - 1, f, f + 1):
            if adj_f < 0 or adj_f > 7:
                continue
            for wr in white_pawn_files.get(adj_f, []):
                if wr < r:
                    is_passed = False
                    break
            if not is_passed:
                break
        if is_passed:
            black_rank = 7 - r
            score -= PASSED_PAWN_BONUS[black_rank]

    return score


def _backward_pawn_penalty(board: chess.Board) -> int:
    """Penalize backward pawns: pawns that cannot be supported by friendly pawns
    and whose stop square is controlled by an enemy pawn."""
    score = 0

    white_pawns = board.pieces(chess.PAWN, chess.WHITE)
    black_pawns = board.pieces(chess.PAWN, chess.BLACK)

    # Build file->ranks maps for quick lookup
    white_pawn_ranks: dict[int, list[int]] = {}
    for sq in white_pawns:
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        white_pawn_ranks.setdefault(f, []).append(r)

    black_pawn_ranks: dict[int, list[int]] = {}
    for sq in black_pawns:
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        black_pawn_ranks.setdefault(f, []).append(r)

    # Precompute black pawn attack squares
    black_pawn_attacks = chess.BB_EMPTY
    for sq in black_pawns:
        black_pawn_attacks |= chess.BB_PAWN_ATTACKS[chess.BLACK][sq]

    # Precompute white pawn attack squares
    white_pawn_attacks = chess.BB_EMPTY
    for sq in white_pawns:
        white_pawn_attacks |= chess.BB_PAWN_ATTACKS[chess.WHITE][sq]

    # Check white pawns for backward
    for sq in white_pawns:
        f = chess.square_file(sq)
        r = chess.square_rank(sq)

        can_be_supported = False
        for adj_f in (f - 1, f + 1):
            if adj_f < 0 or adj_f > 7:
                continue
            for wr in white_pawn_ranks.get(adj_f, []):
                if wr <= r:
                    can_be_supported = True
                    break
            if can_be_supported:
                break

        if not can_be_supported:
            stop_sq = chess.square(f, r + 1)
            if chess.BB_SQUARES[stop_sq] & black_pawn_attacks:
                score -= BACKWARD_PAWN_PENALTY

    # Check black pawns for backward
    for sq in black_pawns:
        f = chess.square_file(sq)
        r = chess.square_rank(sq)

        can_be_supported = False
        for adj_f in (f - 1, f + 1):
            if adj_f < 0 or adj_f > 7:
                continue
            for br in black_pawn_ranks.get(adj_f, []):
                if br >= r:
                    can_be_supported = True
                    break
            if can_be_supported:
                break

        if not can_be_supported:
            stop_sq = chess.square(f, r - 1)
            if chess.BB_SQUARES[stop_sq] & white_pawn_attacks:
                score += BACKWARD_PAWN_PENALTY

    return score


def _mobility_bonus(board: chess.Board) -> int:
    """Count attacked squares per piece type for each side and return a bonus."""
    score = 0
    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        for piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            bonus_per_move = MOBILITY_BONUS[piece_type]
            if bonus_per_move == 0:
                continue
            for square in board.pieces(piece_type, color):
                attacks = board.attacks(square)
                mobility = len(attacks)
                score += sign * bonus_per_move * mobility
    return score


def _bishop_pair_bonus(board: chess.Board) -> int:
    """Award a bonus for having both bishops."""
    score = 0
    if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
        score += BISHOP_PAIR_BONUS
    if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
        score -= BISHOP_PAIR_BONUS
    return score


def _knight_outpost_bonus(board: chess.Board) -> int:
    """Award a bonus for knights on outpost squares."""
    score = 0

    black_pawn_attacks = chess.BB_EMPTY
    for sq in board.pieces(chess.PAWN, chess.BLACK):
        black_pawn_attacks |= chess.BB_PAWN_ATTACKS[chess.BLACK][sq]

    white_pawn_attacks = chess.BB_EMPTY
    for sq in board.pieces(chess.PAWN, chess.WHITE):
        white_pawn_attacks |= chess.BB_PAWN_ATTACKS[chess.WHITE][sq]

    for sq in board.pieces(chess.KNIGHT, chess.WHITE):
        rank = chess.square_rank(sq)
        if 3 <= rank <= 5:
            if not (chess.BB_SQUARES[sq] & black_pawn_attacks):
                score += KNIGHT_OUTPOST_BONUS

    for sq in board.pieces(chess.KNIGHT, chess.BLACK):
        rank = chess.square_rank(sq)
        if 2 <= rank <= 4:
            if not (chess.BB_SQUARES[sq] & white_pawn_attacks):
                score -= KNIGHT_OUTPOST_BONUS

    return score


def _king_pawn_shelter(board: chess.Board, phase: float) -> int:
    """Penalize castled kings for missing pawns in the two ranks directly in front."""
    if phase < 0.4:
        return 0

    score = 0
    shelter_weight = phase

    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        king_sq = board.king(color)
        if king_sq is None:
            continue

        king_file = chess.square_file(king_sq)
        king_rank = chess.square_rank(king_sq)

        if 2 <= king_file <= 5:
            continue

        pawn_squares = board.pieces(chess.PAWN, color)
        if color == chess.WHITE:
            shelter_ranks = range(king_rank + 1, min(8, king_rank + 3))
        else:
            shelter_ranks = range(max(0, king_rank - 2), king_rank)

        missing = 0
        for f in range(max(0, king_file - 1), min(8, king_file + 2)):
            if not any(chess.square(f, r) in pawn_squares for r in shelter_ranks):
                missing += 1

        score -= sign * int(missing * KING_SHELTER_PENALTY * shelter_weight)

    return score


def _rook_open_file_bonus(board: chess.Board) -> int:
    """Award bonus for rooks on open or semi-open files."""
    score = 0

    white_pawn_files = set()
    for sq in board.pieces(chess.PAWN, chess.WHITE):
        white_pawn_files.add(chess.square_file(sq))

    black_pawn_files = set()
    for sq in board.pieces(chess.PAWN, chess.BLACK):
        black_pawn_files.add(chess.square_file(sq))

    for sq in board.pieces(chess.ROOK, chess.WHITE):
        f = chess.square_file(sq)
        has_white_pawn = f in white_pawn_files
        has_black_pawn = f in black_pawn_files
        if not has_white_pawn and not has_black_pawn:
            score += ROOK_OPEN_FILE_BONUS
        elif not has_white_pawn:
            score += ROOK_SEMI_OPEN_FILE_BONUS

    for sq in board.pieces(chess.ROOK, chess.BLACK):
        f = chess.square_file(sq)
        has_white_pawn = f in white_pawn_files
        has_black_pawn = f in black_pawn_files
        if not has_black_pawn and not has_white_pawn:
            score -= ROOK_OPEN_FILE_BONUS
        elif not has_black_pawn:
            score -= ROOK_SEMI_OPEN_FILE_BONUS

    return score


def _connected_rooks_bonus(board: chess.Board) -> int:
    """Award a bonus when two friendly rooks see each other on a rank or file
    with no pieces between them (i.e., they protect each other)."""
    score = 0

    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        rook_squares = list(board.pieces(chess.ROOK, color))
        if len(rook_squares) < 2:
            continue

        # Check all pairs of rooks
        for i in range(len(rook_squares)):
            for j in range(i + 1, len(rook_squares)):
                sq1 = rook_squares[i]
                sq2 = rook_squares[j]
                r1, f1 = chess.square_rank(sq1), chess.square_file(sq1)
                r2, f2 = chess.square_rank(sq2), chess.square_file(sq2)

                connected = False
                if r1 == r2:
                    # Same rank: check if path between them is clear
                    min_f, max_f = min(f1, f2), max(f1, f2)
                    between = chess.BB_EMPTY
                    for f in range(min_f + 1, max_f):
                        between |= chess.BB_SQUARES[chess.square(f, r1)]
                    if not (board.occupied & between):
                        connected = True
                elif f1 == f2:
                    # Same file: check if path between them is clear
                    min_r, max_r = min(r1, r2), max(r1, r2)
                    between = chess.BB_EMPTY
                    for r in range(min_r + 1, max_r):
                        between |= chess.BB_SQUARES[chess.square(f1, r)]
                    if not (board.occupied & between):
                        connected = True

                if connected:
                    score += sign * CONNECTED_ROOKS_BONUS

    return score


def _rook_on_seventh_bonus(board: chess.Board) -> int:
    """Award a bonus for rooks on the 7th rank (rank index 6 for white, rank index 1 for black),
    especially when the enemy king is on the back rank or there are enemy pawns on the 7th."""
    score = 0

    # White rooks on rank 7 (index 6)
    for sq in board.pieces(chess.ROOK, chess.WHITE):
        if chess.square_rank(sq) == 6:
            # Bonus if enemy king is on rank 8 (index 7) or there are black pawns on rank 7
            black_king_sq = board.king(chess.BLACK)
            black_king_on_back = black_king_sq is not None and chess.square_rank(black_king_sq) == 7
            black_pawns_on_seventh = any(
                chess.square_rank(s) == 6 for s in board.pieces(chess.PAWN, chess.BLACK)
            )
            if black_king_on_back or black_pawns_on_seventh:
                score += ROOK_ON_SEVENTH_BONUS
            else:
                score += ROOK_ON_SEVENTH_BONUS // 2

    # Black rooks on rank 2 (index 1)
    for sq in board.pieces(chess.ROOK, chess.BLACK):
        if chess.square_rank(sq) == 1:
            white_king_sq = board.king(chess.WHITE)
            white_king_on_back = white_king_sq is not None and chess.square_rank(white_king_sq) == 0
            white_pawns_on_second = any(
                chess.square_rank(s) == 1 for s in board.pieces(chess.PAWN, chess.WHITE)
            )
            if white_king_on_back or white_pawns_on_second:
                score -= ROOK_ON_SEVENTH_BONUS
            else:
                score -= ROOK_ON_SEVENTH_BONUS // 2

    return score


def _hanging_piece_bonus(board: chess.Board) -> int:
    """Award a bonus for each undefended (hanging) enemy piece that we attack.
    A piece is hanging if it is not defended by any enemy piece."""
    score = 0

    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        enemy_color = not color

        for sq in chess.SQUARES:
            piece = board.piece_at(sq)
            if piece is None or piece.color != enemy_color:
                continue
            # Skip pawns and kings (low value or not worth tracking as hanging)
            if piece.piece_type in (chess.PAWN, chess.KING):
                continue
            # Check if the enemy piece is defended by any enemy piece
            defenders = board.attackers(enemy_color, sq)
            if defenders:
                continue
            # Check if we attack this square
            attackers = board.attackers(color, sq)
            if attackers:
                piece_val = PIECE_VALUES[piece.piece_type]
                score += sign * int(piece_val * HANGING_PIECE_BONUS_FRACTION)

    return score


def _center_control_bonus(board: chess.Board, phase: float) -> int:
    """Award a bonus for controlling (attacking) the four central squares d4/e4/d5/e5.
    Only meaningful in the middlegame, so scaled by phase."""
    if phase < 0.3:
        return 0

    score = 0
    scale = phase  # stronger bonus in the middlegame

    for center_sq in _CENTER_SQUARES:
        white_attackers = len(board.attackers(chess.WHITE, center_sq))
        black_attackers = len(board.attackers(chess.BLACK, center_sq))
        score += int((white_attackers - black_attackers) * CENTER_ATTACK_BONUS * scale)

    return score


def evaluate(board: chess.Board) -> int:
    """Return centipawns from the side-to-move perspective."""
    endgame = is_endgame(board)
    phase = _compute_phase(board)
    score = 0

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue

        value = PIECE_VALUES[piece.piece_type]
        pst = _pst_bonus_tapered(piece, square, phase)
        if piece.color == chess.WHITE:
            score += value + pst
        else:
            score -= value + pst

    score += _pawn_structure_bonus(board)
    score += _passed_pawn_bonus(board)
    score += _backward_pawn_penalty(board)
    score += _mobility_bonus(board)
    score += _bishop_pair_bonus(board)
    score += _knight_outpost_bonus(board)
    score += _king_pawn_shelter(board, phase)
    score += _rook_open_file_bonus(board)
    score += _connected_rooks_bonus(board)
    score += _rook_on_seventh_bonus(board)
    score += _hanging_piece_bonus(board)
    score += _center_control_bonus(board, phase)
    return score if board.turn == chess.WHITE else -score