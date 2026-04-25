"""
Chess: GameState implementation.

Board: 8×8 int array.
  Row 0 = rank 8 (black's back rank).  Row 7 = rank 1 (white's back rank).
  Col 0 = file a,  Col 7 = file h.

Piece encoding:
   0  empty
   1  white pawn      -1  black pawn
   2  white knight    -2  black knight
   3  white bishop    -3  black bishop
   4  white rook      -4  black rook
   5  white queen     -5  black queen
   6  white king      -6  black king

Player: +1 = white (maximiser), -1 = black (minimiser).
Move:   (from_row, from_col, to_row, to_col, promo)
        promo = None | 2..5 (knight/bishop/rook/queen, always unsigned)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple

from core.game import GameState

# ---- piece constants -------------------------------------------------------
EMPTY = 0
WP, WN, WB, WR, WQ, WK =  1,  2,  3,  4,  5,  6
BP, BN, BB, BR, BQ, BK = -1, -2, -3, -4, -5, -6

Move = Tuple[int, int, int, int, Optional[int]]

PIECE_FROM_CHAR: Dict[str, int] = {
    'P': WP, 'N': WN, 'B': WB, 'R': WR, 'Q': WQ, 'K': WK,
    'p': BP, 'n': BN, 'b': BB, 'r': BR, 'q': BQ, 'k': BK,
}
CHAR_FROM_PIECE: Dict[int, str] = {v: k for k, v in PIECE_FROM_CHAR.items()}
PROMO_FROM_CHAR: Dict[str, int] = {'q': 5, 'r': 4, 'b': 3, 'n': 2}
PROMO_TO_CHAR:   Dict[int, str] = {5: 'q', 4: 'r', 3: 'b', 2: 'n'}

START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

# ---- material values (centipawns) ------------------------------------------
MATERIAL: Dict[int, int] = {1: 100, 2: 320, 3: 330, 4: 500, 5: 900, 6: 20000}

# ---- move deltas -----------------------------------------------------------
_KNIGHT_D = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
_KING_D   = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
_DIAG     = [(-1,-1),(-1,1),(1,-1),(1,1)]
_STRAIGHT = [(-1,0),(1,0),(0,-1),(0,1)]
_ALL      = _DIAG + _STRAIGHT

# ---- Piece-Square Tables (white's perspective; row 0 = rank 8) -------------
_PST_PAWN = [
    [  0,  0,  0,  0,  0,  0,  0,  0],
    [ 50, 50, 50, 50, 50, 50, 50, 50],
    [ 10, 10, 20, 30, 30, 20, 10, 10],
    [  5,  5, 10, 25, 25, 10,  5,  5],
    [  0,  0,  0, 20, 20,  0,  0,  0],
    [  5, -5,-10,  0,  0,-10, -5,  5],
    [  5, 10, 10,-20,-20, 10, 10,  5],
    [  0,  0,  0,  0,  0,  0,  0,  0],
]
_PST_KNIGHT = [
    [-50,-40,-30,-30,-30,-30,-40,-50],
    [-40,-20,  0,  0,  0,  0,-20,-40],
    [-30,  0, 10, 15, 15, 10,  0,-30],
    [-30,  5, 15, 20, 20, 15,  5,-30],
    [-30,  0, 15, 20, 20, 15,  0,-30],
    [-30,  5, 10, 15, 15, 10,  5,-30],
    [-40,-20,  0,  5,  5,  0,-20,-40],
    [-50,-40,-30,-30,-30,-30,-40,-50],
]
_PST_BISHOP = [
    [-20,-10,-10,-10,-10,-10,-10,-20],
    [-10,  0,  0,  0,  0,  0,  0,-10],
    [-10,  0,  5, 10, 10,  5,  0,-10],
    [-10,  5,  5, 10, 10,  5,  5,-10],
    [-10,  0, 10, 10, 10, 10,  0,-10],
    [-10, 10, 10, 10, 10, 10, 10,-10],
    [-10,  5,  0,  0,  0,  0,  5,-10],
    [-20,-10,-10,-10,-10,-10,-10,-20],
]
_PST_ROOK = [
    [  0,  0,  0,  0,  0,  0,  0,  0],
    [  5, 10, 10, 10, 10, 10, 10,  5],
    [ -5,  0,  0,  0,  0,  0,  0, -5],
    [ -5,  0,  0,  0,  0,  0,  0, -5],
    [ -5,  0,  0,  0,  0,  0,  0, -5],
    [ -5,  0,  0,  0,  0,  0,  0, -5],
    [ -5,  0,  0,  0,  0,  0,  0, -5],
    [  0,  0,  0,  5,  5,  0,  0,  0],
]
_PST_QUEEN = [
    [-20,-10,-10, -5, -5,-10,-10,-20],
    [-10,  0,  0,  0,  0,  0,  0,-10],
    [-10,  0,  5,  5,  5,  5,  0,-10],
    [ -5,  0,  5,  5,  5,  5,  0, -5],
    [  0,  0,  5,  5,  5,  5,  0, -5],
    [-10,  5,  5,  5,  5,  5,  0,-10],
    [-10,  0,  5,  0,  0,  0,  0,-10],
    [-20,-10,-10, -5, -5,-10,-10,-20],
]
_PST_KING = [
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-20,-30,-30,-40,-40,-30,-30,-20],
    [-10,-20,-20,-20,-20,-20,-20,-10],
    [ 20, 20,  0,  0,  0,  0, 20, 20],
    [ 20, 30, 10,  0,  0, 10, 30, 20],
]
_PST: Dict[int, List] = {
    1: _PST_PAWN, 2: _PST_KNIGHT, 3: _PST_BISHOP,
    4: _PST_ROOK, 5: _PST_QUEEN,  6: _PST_KING,
}


# ---- coordinate helpers ----------------------------------------------------

def sq_to_uci(row: int, col: int) -> str:
    return chr(ord('a') + col) + str(8 - row)

def uci_to_sq(s: str) -> Tuple[int, int]:
    return (8 - int(s[1]), ord(s[0]) - ord('a'))

def move_to_uci(move: Move) -> str:
    fr, fc, tr, tc, promo = move
    s = sq_to_uci(fr, fc) + sq_to_uci(tr, tc)
    if promo:
        s += PROMO_TO_CHAR[promo]
    return s

def uci_to_move(s: str) -> Move:
    fr, fc = uci_to_sq(s[:2])
    tr, tc = uci_to_sq(s[2:4])
    promo = PROMO_FROM_CHAR.get(s[4]) if len(s) > 4 else None
    return (fr, fc, tr, tc, promo)


# ---- board-level utilities (operate on raw int arrays) ---------------------

def _find_king(board: List[List[int]], player: int) -> Optional[Tuple[int, int]]:
    king = WK if player == 1 else BK
    for r in range(8):
        for c in range(8):
            if board[r][c] == king:
                return (r, c)
    return None

def _is_attacked(board: List[List[int]], row: int, col: int, by_player: int) -> bool:
    """True when (row, col) is attacked by any piece belonging to by_player."""
    # Pawns — a white pawn at (row+1, col±1) attacks (row, col)
    pawn   = WP if by_player == 1 else BP
    pr     = row + (1 if by_player == 1 else -1)
    if 0 <= pr < 8:
        for pc in (col - 1, col + 1):
            if 0 <= pc < 8 and board[pr][pc] == pawn:
                return True

    # Knights
    kn = WN if by_player == 1 else BN
    for dr, dc in _KNIGHT_D:
        nr, nc = row + dr, col + dc
        if 0 <= nr < 8 and 0 <= nc < 8 and board[nr][nc] == kn:
            return True

    # Bishops / Queens on diagonals
    b = WB if by_player == 1 else BB
    q = WQ if by_player == 1 else BQ
    for dr, dc in _DIAG:
        nr, nc = row + dr, col + dc
        while 0 <= nr < 8 and 0 <= nc < 8:
            p = board[nr][nc]
            if p != EMPTY:
                if p == b or p == q:
                    return True
                break
            nr += dr; nc += dc

    # Rooks / Queens on ranks/files
    rk = WR if by_player == 1 else BR
    for dr, dc in _STRAIGHT:
        nr, nc = row + dr, col + dc
        while 0 <= nr < 8 and 0 <= nc < 8:
            p = board[nr][nc]
            if p != EMPTY:
                if p == rk or p == q:
                    return True
                break
            nr += dr; nc += dc

    # King (adjacent)
    kg = WK if by_player == 1 else BK
    for dr, dc in _KING_D:
        nr, nc = row + dr, col + dc
        if 0 <= nr < 8 and 0 <= nc < 8 and board[nr][nc] == kg:
            return True

    return False


# ---- FEN helpers -----------------------------------------------------------

def _board_from_fen(fen_board: str) -> List[List[int]]:
    board = [[EMPTY] * 8 for _ in range(8)]
    for r, rank in enumerate(fen_board.split('/')):
        c = 0
        for ch in rank:
            if ch.isdigit():
                c += int(ch)
            else:
                board[r][c] = PIECE_FROM_CHAR[ch]
                c += 1
    return board

def _board_to_fen(board: List[List[int]]) -> str:
    ranks = []
    for row in board:
        empty = 0
        s = ''
        for p in row:
            if p == EMPTY:
                empty += 1
            else:
                if empty:
                    s += str(empty); empty = 0
                s += CHAR_FROM_PIECE[p]
        if empty:
            s += str(empty)
        ranks.append(s)
    return '/'.join(ranks)


# ---- ChessState ------------------------------------------------------------

class ChessState(GameState):

    def __init__(
        self,
        board: List[List[int]],
        player: int,
        castling: Dict[str, bool],
        ep_square: Optional[Tuple[int, int]],
        halfmove: int,
        fullmove: int,
    ) -> None:
        self._board    = board
        self._player   = player
        self._castling = castling
        self._ep       = ep_square
        self._hm       = halfmove
        self._fm       = fullmove
        self._legal_cache: Optional[List[Move]] = None

    # ---- constructors -------------------------------------------------------

    @classmethod
    def from_fen(cls, fen: str) -> ChessState:
        parts = fen.split()
        board  = _board_from_fen(parts[0])
        player = 1 if parts[1] == 'w' else -1
        cs     = parts[2]
        castling = {'K': 'K' in cs, 'Q': 'Q' in cs, 'k': 'k' in cs, 'q': 'q' in cs}
        ep     = None if parts[3] == '-' else uci_to_sq(parts[3])
        return cls(board, player, castling, ep, int(parts[4]), int(parts[5]))

    @classmethod
    def start(cls) -> ChessState:
        return cls.from_fen(START_FEN)

    def to_fen(self) -> str:
        cs  = ''.join(k for k in ('K', 'Q', 'k', 'q') if self._castling[k]) or '-'
        ep  = sq_to_uci(*self._ep) if self._ep else '-'
        pl  = 'w' if self._player == 1 else 'b'
        return f'{_board_to_fen(self._board)} {pl} {cs} {ep} {self._hm} {self._fm}'

    # ---- GameState interface ------------------------------------------------

    @property
    def current_player(self) -> int:
        return self._player

    def get_legal_moves(self) -> List[Move]:
        if self._legal_cache is None:
            self._legal_cache = self._build_legal_moves()
        return self._legal_cache

    def apply_move(self, move: Move) -> ChessState:
        fr, fc, tr, tc, promo = move
        board  = [row[:] for row in self._board]
        piece  = board[fr][fc]
        target = board[tr][tc]

        is_pawn   = abs(piece) == 1
        is_ep     = is_pawn and self._ep == (tr, tc)
        is_castle = abs(piece) == 6 and abs(tc - fc) == 2

        new_ep = None
        new_cs = dict(self._castling)
        new_hm = 0 if (is_pawn or target != EMPTY) else self._hm + 1

        if is_ep:                          # remove captured pawn
            board[fr][tc] = EMPTY

        if is_castle:                      # slide the rook
            rook = WR if self._player == 1 else BR
            if tc == 6:
                board[fr][7] = EMPTY; board[fr][5] = rook
            else:
                board[fr][0] = EMPTY; board[fr][3] = rook

        board[fr][fc] = EMPTY
        board[tr][tc] = (promo * self._player) if promo else piece

        if abs(piece) == 6:                # king moved → lose both castling rights
            if self._player == 1:
                new_cs['K'] = new_cs['Q'] = False
            else:
                new_cs['k'] = new_cs['q'] = False

        # Rook left or was captured on its origin square
        for sq, key in [((7,7),'K'), ((7,0),'Q'), ((0,7),'k'), ((0,0),'q')]:
            if (fr, fc) == sq or (tr, tc) == sq:
                new_cs[key] = False

        if is_pawn and abs(tr - fr) == 2:  # double push → set ep square
            new_ep = ((fr + tr) // 2, fc)

        new_fm = self._fm + (1 if self._player == -1 else 0)
        return ChessState(board, -self._player, new_cs, new_ep, new_hm, new_fm)

    def is_terminal(self) -> bool:
        return self.get_winner() is not None

    def get_winner(self) -> Optional[int]:
        if self._hm >= 100:
            return 0
        if self._insufficient_material():
            return 0
        if not self.get_legal_moves():
            kp = _find_king(self._board, self._player)
            if kp and _is_attacked(self._board, kp[0], kp[1], -self._player):
                return -self._player   # checkmate
            return 0                   # stalemate
        return None

    def evaluate(self) -> float:
        winner = self.get_winner()
        if winner is not None:
            return float(winner)
        score = 0
        for r in range(8):
            for c in range(8):
                p = self._board[r][c]
                if p == EMPTY:
                    continue
                pt  = abs(p)
                val = MATERIAL.get(pt, 0)
                pst = _PST.get(pt)
                if pst:
                    pr = r if p > 0 else 7 - r
                    val += pst[pr][c]
                score += val if p > 0 else -val
        return max(-0.99, min(0.99, score / 4000.0))

    # ---- move generation internals -----------------------------------------

    def _build_legal_moves(self) -> List[Move]:
        legal: List[Move] = []
        for move in self._pseudo_legal():
            after = self.apply_move(move)
            kp = _find_king(after._board, self._player)
            if kp and not _is_attacked(after._board, kp[0], kp[1], -self._player):
                legal.append(move)
        # Move ordering: captures/promotions first
        legal.sort(key=lambda m: 0 if (self._board[m[2]][m[3]] != EMPTY or m[4]) else 1)
        return legal

    def _pseudo_legal(self) -> List[Move]:
        moves: List[Move] = []
        for r in range(8):
            for c in range(8):
                p = self._board[r][c]
                if p == EMPTY or (p > 0) != (self._player > 0):
                    continue
                pt = abs(p)
                if   pt == 1: moves.extend(self._pawn_moves(r, c))
                elif pt == 2: moves.extend(self._step_moves(r, c, _KNIGHT_D, one_step=True))
                elif pt == 3: moves.extend(self._slide_moves(r, c, _DIAG))
                elif pt == 4: moves.extend(self._slide_moves(r, c, _STRAIGHT))
                elif pt == 5: moves.extend(self._slide_moves(r, c, _ALL))
                elif pt == 6: moves.extend(self._king_moves(r, c))
        return moves

    def _pawn_moves(self, r: int, c: int) -> List[Move]:
        moves: List[Move] = []
        d         = -1 if self._player == 1 else 1
        start_r   =  6 if self._player == 1 else 1
        promo_r   =  0 if self._player == 1 else 7
        nr = r + d

        if 0 <= nr < 8:
            if self._board[nr][c] == EMPTY:
                self._add_pawn(moves, r, c, nr, c, nr == promo_r)
                if r == start_r:
                    nr2 = r + 2 * d
                    if self._board[nr2][c] == EMPTY:
                        moves.append((r, c, nr2, c, None))
            for dc in (-1, 1):
                nc = c + dc
                if 0 <= nc < 8:
                    tgt = self._board[nr][nc]
                    is_ep = self._ep == (nr, nc)
                    if (tgt != EMPTY and (tgt > 0) != (self._player > 0)) or is_ep:
                        self._add_pawn(moves, r, c, nr, nc, nr == promo_r)
        return moves

    @staticmethod
    def _add_pawn(moves: List[Move], fr: int, fc: int, tr: int, tc: int, promo: bool) -> None:
        if promo:
            for pt in (5, 4, 3, 2):
                moves.append((fr, fc, tr, tc, pt))
        else:
            moves.append((fr, fc, tr, tc, None))

    def _step_moves(self, r: int, c: int, deltas: List, one_step: bool = True) -> List[Move]:
        moves: List[Move] = []
        for dr, dc in deltas:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                tgt = self._board[nr][nc]
                if tgt == EMPTY or (tgt > 0) != (self._player > 0):
                    moves.append((r, c, nr, nc, None))
        return moves

    def _slide_moves(self, r: int, c: int, dirs: List) -> List[Move]:
        moves: List[Move] = []
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                tgt = self._board[nr][nc]
                if tgt == EMPTY:
                    moves.append((r, c, nr, nc, None))
                elif (tgt > 0) != (self._player > 0):
                    moves.append((r, c, nr, nc, None))
                    break
                else:
                    break
                nr += dr; nc += dc
        return moves

    def _king_moves(self, r: int, c: int) -> List[Move]:
        moves = self._step_moves(r, c, _KING_D)
        moves.extend(self._castling_moves())
        return moves

    def _castling_moves(self) -> List[Move]:
        moves: List[Move] = []
        kp = _find_king(self._board, self._player)
        if kp is None or _is_attacked(self._board, kp[0], kp[1], -self._player):
            return moves          # can't castle while in check

        opp = -self._player
        if self._player == 1:
            kr = 7
            if self._castling['K'] and \
               self._board[7][5] == EMPTY and self._board[7][6] == EMPTY and \
               not _is_attacked(self._board, 7, 5, opp) and \
               not _is_attacked(self._board, 7, 6, opp):
                moves.append((7, 4, 7, 6, None))
            if self._castling['Q'] and \
               self._board[7][3] == EMPTY and self._board[7][2] == EMPTY and \
               self._board[7][1] == EMPTY and \
               not _is_attacked(self._board, 7, 3, opp) and \
               not _is_attacked(self._board, 7, 2, opp):
                moves.append((7, 4, 7, 2, None))
        else:
            if self._castling['k'] and \
               self._board[0][5] == EMPTY and self._board[0][6] == EMPTY and \
               not _is_attacked(self._board, 0, 5, opp) and \
               not _is_attacked(self._board, 0, 6, opp):
                moves.append((0, 4, 0, 6, None))
            if self._castling['q'] and \
               self._board[0][3] == EMPTY and self._board[0][2] == EMPTY and \
               self._board[0][1] == EMPTY and \
               not _is_attacked(self._board, 0, 3, opp) and \
               not _is_attacked(self._board, 0, 2, opp):
                moves.append((0, 4, 0, 2, None))
        return moves

    def _insufficient_material(self) -> bool:
        non_king = [abs(self._board[r][c])
                    for r in range(8) for c in range(8)
                    if self._board[r][c] != EMPTY and abs(self._board[r][c]) != 6]
        if not non_king:
            return True
        if len(non_king) == 1 and non_king[0] in (2, 3):
            return True
        return False

    # ---- display -----------------------------------------------------------

    def __str__(self) -> str:
        sym = {EMPTY:'.', WP:'P', WN:'N', WB:'B', WR:'R', WQ:'Q', WK:'K',
               BP:'p', BN:'n', BB:'b', BR:'r', BQ:'q', BK:'k'}
        hdr = '  a b c d e f g h'
        rows = [hdr]
        for r in range(8):
            rows.append(str(8 - r) + ' ' +
                        ' '.join(sym[self._board[r][c]] for c in range(8)))
        rows.append(hdr)
        return '\n'.join(rows)
