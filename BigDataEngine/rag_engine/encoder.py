"""
Board → feature vector encoding.

Output: 773-dimensional float32 vector.
  [0..767]  : 12 piece planes × 64 squares  (white P/N/B/R/Q/K, then black)
  [768]     : side to move  (1 = white, 0 = black)
  [769..772]: castling rights  (WK, WQ, BK, BQ)
"""

from __future__ import annotations

import chess
import numpy as np

# Maps (piece_type, color) → plane index 0..11
_PLANE: dict[tuple[int, bool], int] = {}
for _pt in chess.PIECE_TYPES:          # 1..6
    _PLANE[(_pt, chess.WHITE)] = _pt - 1
    _PLANE[(_pt, chess.BLACK)] = _pt - 1 + 6

FEATURE_DIM = 773
POLICY_DIM  = 4096   # from_sq * 64 + to_sq   (promotions share to_sq)


def encode_board(board: chess.Board) -> np.ndarray:
    """Return a 773-dim float32 feature vector for *board*."""
    vec = np.zeros(FEATURE_DIM, dtype=np.float32)

    for sq, piece in board.piece_map().items():
        plane = _PLANE[(piece.piece_type, piece.color)]
        vec[plane * 64 + sq] = 1.0

    vec[768] = 1.0 if board.turn == chess.WHITE else 0.0
    vec[769] = 1.0 if board.has_kingside_castling_rights(chess.WHITE)  else 0.0
    vec[770] = 1.0 if board.has_queenside_castling_rights(chess.WHITE) else 0.0
    vec[771] = 1.0 if board.has_kingside_castling_rights(chess.BLACK)  else 0.0
    vec[772] = 1.0 if board.has_queenside_castling_rights(chess.BLACK) else 0.0

    return vec


def encode_board_normalized(board: chess.Board) -> np.ndarray:
    """L2-normalised version of encode_board (for cosine similarity via inner product)."""
    vec = encode_board(board)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0.0 else vec


def move_to_idx(move: chess.Move) -> int:
    """Losslessly map a move to an integer in [0, 4095]."""
    return move.from_square * 64 + move.to_square


def legal_move_mask(board: chess.Board) -> np.ndarray:
    """Return a 4096-dim float32 mask: 1.0 for each legal move, 0.0 otherwise."""
    mask = np.zeros(POLICY_DIM, dtype=np.float32)
    for m in board.legal_moves:
        mask[move_to_idx(m)] = 1.0
    return mask
