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


PAWN_PST = _flatten_ranks(
    [0, 0, 0, 0, 0, 0, 0, 0],
    [50, 50, 50, 50, 50, 50, 50, 50],
    [10, 10, 20, 30, 30, 20, 10, 10],
    [5, 5, 10, 25, 25, 10, 5, 5],
    [0, 0, 0, 20, 20, 0, 0, 0],
    [5, -5, -10, 0, 0, -10, -5, 5],
    [5, 10, 10, -20, -20, 10, 10, 5],
    [0, 0, 0, 0, 0, 0, 0, 0],
)

KNIGHT_PST = _flatten_ranks(
    [-50, -40, -30, -30, -30, -30, -40, -50],
    [-40, -20, 0, 0, 0, 0, -20, -40],
    [-30, 0, 10, 15, 15, 10, 0, -30],
    [-30, 5, 15, 20, 20, 15, 5, -30],
    [-30, 0, 15, 20, 20, 15, 0, -30],
    [-30, 5, 10, 15, 15, 10, 5, -30],
    [-40, -20, 0, 5, 5, 0, -20, -40],
    [-50, -40, -30, -30, -30, -30, -40, -50],
)

BISHOP_PST = _flatten_ranks(
    [-20, -10, -10, -10, -10, -10, -10, -20],
    [-10, 0, 0, 0, 0, 0, 0, -10],
    [-10, 0, 5, 10, 10, 5, 0, -10],
    [-10, 5, 5, 10, 10, 5, 5, -10],
    [-10, 0, 10, 10, 10, 10, 0, -10],
    [-10, 10, 10, 10, 10, 10, 10, -10],
    [-10, 5, 0, 0, 0, 0, 5, -10],
    [-20, -10, -10, -10, -10, -10, -10, -20],
)

ROOK_PST = _flatten_ranks(
    [0, 0, 0, 0, 0, 0, 0, 0],
    [5, 10, 10, 10, 10, 10, 10, 5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [0, 0, 0, 5, 5, 0, 0, 0],
)

QUEEN_PST = _flatten_ranks(
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

PST = {
    chess.PAWN: PAWN_PST,
    chess.KNIGHT: KNIGHT_PST,
    chess.BISHOP: BISHOP_PST,
    chess.ROOK: ROOK_PST,
    chess.QUEEN: QUEEN_PST,
    chess.KING: KING_MIDDLEGAME_PST,
}


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


def _pst_bonus(piece: chess.Piece, square: chess.Square, endgame: bool) -> int:
    table = PST[piece.piece_type]
    if piece.piece_type == chess.KING:
        table = KING_ENDGAME_PST if endgame else KING_MIDDLEGAME_PST
    if piece.color == chess.WHITE:
        return table[square]
    return table[square ^ 56]


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


def evaluate(board: chess.Board) -> int:
    """Return centipawns from the side-to-move perspective."""
    endgame = is_endgame(board)
    score = 0

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue

        value = PIECE_VALUES[piece.piece_type]
        pst = _pst_bonus(piece, square, endgame)
        if piece.color == chess.WHITE:
            score += value + pst
        else:
            score -= value + pst

    score += _pawn_structure_bonus(board)
    return score if board.turn == chess.WHITE else -score
