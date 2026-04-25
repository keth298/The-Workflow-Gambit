# board.py — Bitboard-based board representation

import random as _random

# ── Piece indices ──────────────────────────────────────────────────────────────
WP, WN, WB, WR, WQ, WK = 0, 1, 2, 3, 4, 5
BP, BN, BB, BR, BQ, BK = 6, 7, 8, 9, 10, 11
WHITE, BLACK = 0, 1
PIECE_NAMES = ['P','N','B','R','Q','K','p','n','b','r','q','k']

# ── Zobrist keys ───────────────────────────────────────────────────────────────
_rng = _random.Random(0xDEADBEEF)   # fixed seed → reproducible hashes
def _r64(): return _rng.getrandbits(64)

ZOBRIST_PIECE     = [[_r64() for _ in range(64)] for _ in range(12)]
ZOBRIST_SIDE      = _r64()                          # XOR when black to move
ZOBRIST_CASTLING  = [_r64() for _ in range(16)]    # indexed by castling mask
ZOBRIST_EP        = [_r64() for _ in range(8)]     # indexed by ep file

# ── Castling masks ─────────────────────────────────────────────────────────────
WK_SIDE = 1
WQ_SIDE = 2
BK_SIDE = 4
BQ_SIDE = 8

# ── Precomputed masks ──────────────────────────────────────────────────────────
FULL  = 0xFFFFFFFFFFFFFFFF
FILE  = [0x0101010101010101 << f for f in range(8)]   # FILE[0]=A … FILE[7]=H
RANK  = [0xFF << (8 * r) for r in range(8)]            # RANK[0]=1 … RANK[7]=8
NOT_A = FULL ^ FILE[0]
NOT_H = FULL ^ FILE[7]

# ── Square helpers ─────────────────────────────────────────────────────────────
def sq_idx(file, rank):   return rank * 8 + file
def file_of(sq):          return sq & 7
def rank_of(sq):          return sq >> 3
def bit(sq):              return 1 << sq

SQ_NAMES = [f"{chr(ord('a')+f)}{r+1}" for r in range(8) for f in range(8)]

def sq_from_name(name):
    return (ord(name[0]) - ord('a')) + (int(name[1]) - 1) * 8

# ── Move encoding ──────────────────────────────────────────────────────────────
# bits 0-5: from_sq  bits 6-11: to_sq  bits 12-15: flags
QUIET       = 0
DOUBLE_PUSH = 1
CASTLE_K    = 2
CASTLE_Q    = 3
CAPTURE     = 4
EP_CAPTURE  = 5
PROMO_N     = 8
PROMO_B     = 9
PROMO_R     = 10
PROMO_Q     = 11
PROMO_CN    = 12
PROMO_CB    = 13
PROMO_CR    = 14
PROMO_CQ    = 15

def make_move(fr, to, flags=QUIET):  return fr | (to << 6) | (flags << 12)
def from_sq(mv):   return mv & 0x3F
def to_sq(mv):     return (mv >> 6) & 0x3F
def flags(mv):     return (mv >> 12) & 0xF
def is_capture(mv):    return flags(mv) in (CAPTURE, EP_CAPTURE, PROMO_CN, PROMO_CB, PROMO_CR, PROMO_CQ)
def is_promo(mv):      return flags(mv) >= PROMO_N
def promo_piece(mv, side):
    f = flags(mv)
    idx = (f & 3)  # 0=N,1=B,2=R,3=Q
    base = WN if side == WHITE else BN
    return base + idx

def move_to_uci(mv):
    s = SQ_NAMES[from_sq(mv)] + SQ_NAMES[to_sq(mv)]
    if is_promo(mv):
        s += 'nbrq'[flags(mv) & 3]
    return s

def uci_to_move(uci, board):
    """Convert UCI string to move integer using the legal move list."""
    for mv in board.legal_moves():
        if move_to_uci(mv) == uci:
            return mv
    return None

# ── LSB / popcount ─────────────────────────────────────────────────────────────
def lsb(bb):        return (bb & -bb).bit_length() - 1
def pop_lsb(bb):    s = lsb(bb); return s, bb & (bb - 1)
def popcount(bb):   return bin(bb).count('1')

# ── Precomputed attack tables ──────────────────────────────────────────────────
KNIGHT_ATTACKS = [0] * 64
KING_ATTACKS   = [0] * 64
PAWN_ATTACKS   = [[0]*64, [0]*64]   # [side][sq]

def _init_tables():
    for sq in range(64):
        b = bit(sq)
        # Knight
        att = 0
        att |= (b << 17) & NOT_A
        att |= (b << 15) & NOT_H
        att |= (b <<  10) & ~(FILE[0] | FILE[1])
        att |= (b <<  6)  & ~(FILE[6] | FILE[7])
        att |= (b >> 17) & NOT_H
        att |= (b >> 15) & NOT_A
        att |= (b >> 10) & ~(FILE[6] | FILE[7])
        att |= (b >>  6) & ~(FILE[0] | FILE[1])
        KNIGHT_ATTACKS[sq] = att & FULL
        # King
        att = 0
        att |= (b << 8)
        att |= (b >> 8)
        att |= (b << 1) & NOT_A
        att |= (b >> 1) & NOT_H
        att |= (b << 9) & NOT_A
        att |= (b << 7) & NOT_H
        att |= (b >> 7) & NOT_A
        att |= (b >> 9) & NOT_H
        KING_ATTACKS[sq] = att & FULL
        # Pawn attacks
        PAWN_ATTACKS[WHITE][sq] = ((b << 9) & NOT_A | (b << 7) & NOT_H) & FULL
        PAWN_ATTACKS[BLACK][sq] = ((b >> 7) & NOT_A | (b >> 9) & NOT_H) & FULL

_init_tables()

def sliding_attacks(sq, occupied, deltas):
    """Compute sliding piece attacks along given (df, dr) directions."""
    att = 0
    f0, r0 = file_of(sq), rank_of(sq)
    for df, dr in deltas:
        f, r = f0 + df, r0 + dr
        while 0 <= f <= 7 and 0 <= r <= 7:
            s = sq_idx(f, r)
            att |= bit(s)
            if occupied & bit(s):
                break
            f += df; r += dr
    return att

BISHOP_DIRS = [( 1, 1),( 1,-1),(-1, 1),(-1,-1)]
ROOK_DIRS   = [( 1, 0),(-1, 0),( 0, 1),( 0,-1)]
QUEEN_DIRS  = BISHOP_DIRS + ROOK_DIRS

# ── Starting position FEN ──────────────────────────────────────────────────────
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# ── Board ──────────────────────────────────────────────────────────────────────
class Board:
    __slots__ = ('pieces','side','castling','ep','halfmove','fullmove','_history','hash')

    def __init__(self):
        self.pieces   = [0] * 12
        self.side     = WHITE
        self.castling = 0
        self.ep       = -1
        self.halfmove = 0
        self.fullmove = 1
        self.hash     = 0
        self._history = []   # stack of (pieces copy, side, castling, ep, halfmove, hash)

    def _compute_hash(self):
        h = 0
        for i, bb in enumerate(self.pieces):
            b = bb
            while b:
                sq, b = pop_lsb(b)
                h ^= ZOBRIST_PIECE[i][sq]
        if self.side == BLACK:
            h ^= ZOBRIST_SIDE
        h ^= ZOBRIST_CASTLING[self.castling]
        if self.ep != -1:
            h ^= ZOBRIST_EP[file_of(self.ep)]
        return h

    # ── derived bitboards ──────────────────────────────────────────────────────
    def occ(self, side):
        base = 0 if side == WHITE else 6
        return self.pieces[base] | self.pieces[base+1] | self.pieces[base+2] \
             | self.pieces[base+3] | self.pieces[base+4] | self.pieces[base+5]

    def all_occ(self):
        return self.occ(WHITE) | self.occ(BLACK)

    def piece_at(self, sq):
        b = bit(sq)
        for i, bb in enumerate(self.pieces):
            if bb & b:
                return i
        return -1

    # ── attack detection ───────────────────────────────────────────────────────
    def attacked_by(self, sq, side):
        """Is square sq attacked by `side`?"""
        occ = self.all_occ()
        base = 0 if side == WHITE else 6
        ep_bb = self.pieces
        # Pawns
        if PAWN_ATTACKS[side ^ 1][sq] & self.pieces[base + 0]:
            return True
        # Knights
        if KNIGHT_ATTACKS[sq] & self.pieces[base + 1]:
            return True
        # Bishops / Queens
        batt = sliding_attacks(sq, occ, BISHOP_DIRS)
        if batt & (self.pieces[base+2] | self.pieces[base+4]):
            return True
        # Rooks / Queens
        ratt = sliding_attacks(sq, occ, ROOK_DIRS)
        if ratt & (self.pieces[base+3] | self.pieces[base+4]):
            return True
        # King
        if KING_ATTACKS[sq] & self.pieces[base + 5]:
            return True
        return False

    def in_check(self, side):
        ksq = lsb(self.pieces[WK if side == WHITE else BK])
        return self.attacked_by(ksq, side ^ 1)

    def has_non_pawn_material(self, side):
        """True if side has at least one piece beyond pawns and king."""
        base = 0 if side == WHITE else 6
        return any(self.pieces[base + i] for i in range(1, 5))  # N B R Q

    # ── make / unmake ──────────────────────────────────────────────────────────
    def make(self, mv):
        self._history.append((
            self.pieces[:],
            self.side,
            self.castling,
            self.ep,
            self.halfmove,
            self.hash,
        ))
        fr, to, fl = from_sq(mv), to_sq(mv), flags(mv)
        side = self.side
        opp  = side ^ 1
        base = 0 if side == WHITE else 6
        obase= 6 if side == WHITE else 0

        moving = self.piece_at(fr)
        self.pieces[moving] ^= bit(fr) | bit(to)
        self.halfmove += 1

        # Capture
        if fl == CAPTURE:
            captured = self.piece_at(to)   # already moved piece, so look at opp
            # re-place moving piece, remove captured, re-place
            self.pieces[moving] ^= bit(to)  # undo placement
            captured = -1
            for i in range(obase, obase+6):
                if self.pieces[i] & bit(to):
                    captured = i; break
            if captured != -1:
                self.pieces[captured] ^= bit(to)
            self.pieces[moving] |= bit(to)
            self.halfmove = 0

        elif fl == EP_CAPTURE:
            ep_sq = to + (8 if side == BLACK else -8)
            self.pieces[obase] ^= bit(ep_sq)
            self.halfmove = 0

        elif fl == DOUBLE_PUSH:
            self.ep = to + (8 if side == BLACK else -8)
            self.halfmove = 0

        elif fl == CASTLE_K:
            if side == WHITE:
                self.pieces[WR] ^= bit(7) | bit(5)
            else:
                self.pieces[BR] ^= bit(63) | bit(61)

        elif fl == CASTLE_Q:
            if side == WHITE:
                self.pieces[WR] ^= bit(0) | bit(3)
            else:
                self.pieces[BR] ^= bit(56) | bit(59)

        elif is_promo(mv):
            self.pieces[moving] ^= bit(to)    # remove pawn from dest
            # remove pawn from source already done above; fix: pawn bit(fr) removed, bit(to) added then removed
            # simpler: redo
            self.pieces[moving] |= bit(fr)    # restore pawn at fr (will clear below)
            self.pieces[moving] ^= bit(fr)    # now pawn gone from fr
            pp = promo_piece(mv, side)
            self.pieces[pp] |= bit(to)
            if fl in (PROMO_CN, PROMO_CB, PROMO_CR, PROMO_CQ):
                for i in range(obase, obase+6):
                    if self.pieces[i] & bit(to) and i != pp:
                        self.pieces[i] ^= bit(to); break
            self.halfmove = 0

        if fl != DOUBLE_PUSH:
            self.ep = -1

        if moving == WP or moving == BP:
            self.halfmove = 0

        # Update castling rights
        if moving == WK: self.castling &= ~(WK_SIDE | WQ_SIDE)
        if moving == BK: self.castling &= ~(BK_SIDE | BQ_SIDE)
        if fr == 0  or to == 0:  self.castling &= ~WQ_SIDE
        if fr == 7  or to == 7:  self.castling &= ~WK_SIDE
        if fr == 56 or to == 56: self.castling &= ~BQ_SIDE
        if fr == 63 or to == 63: self.castling &= ~BK_SIDE

        if side == BLACK:
            self.fullmove += 1
        self.side = opp
        self.hash = self._compute_hash()

    def unmake(self):
        pieces, side, castling, ep, halfmove, h = self._history.pop()
        self.pieces   = pieces
        self.side     = side
        self.castling = castling
        self.ep       = ep
        self.halfmove = halfmove
        self.hash     = h
        self.fullmove -= (1 if side == BLACK else 0)

    def make_null(self):
        """Pass the turn without moving (for null move pruning)."""
        self._history.append((self.pieces[:], self.side, self.castling, self.ep, self.halfmove, self.hash))
        if self.ep != -1:
            self.hash ^= ZOBRIST_EP[file_of(self.ep)]
        self.ep    = -1
        self.hash ^= ZOBRIST_SIDE
        self.side ^= 1

    def unmake_null(self):
        pieces, side, castling, ep, halfmove, h = self._history.pop()
        self.pieces   = pieces
        self.side     = side
        self.castling = castling
        self.ep       = ep
        self.halfmove = halfmove
        self.hash     = h

    # ── legal moves ───────────────────────────────────────────────────────────
    def legal_moves(self):
        legal = []
        for mv in self._pseudo_legal():
            self.make(mv)
            if not self.in_check(self.side ^ 1):
                legal.append(mv)
            self.unmake()
        return legal

    def _pseudo_legal(self):
        moves = []
        side  = self.side
        opp   = side ^ 1
        base  = 0 if side == WHITE else 6
        obase = 6 if side == WHITE else 0
        occ   = self.all_occ()
        own   = self.occ(side)
        opp_bb= self.occ(opp)

        # ── Pawns ──────────────────────────────────────────────────────────────
        pawns = self.pieces[base]
        if side == WHITE:
            # Single push
            single = (pawns << 8) & ~occ & FULL
            bb = single
            while bb:
                to, bb = pop_lsb(bb)
                fr = to - 8
                if rank_of(to) == 7:
                    for fl in (PROMO_N, PROMO_B, PROMO_R, PROMO_Q):
                        moves.append(make_move(fr, to, fl))
                else:
                    moves.append(make_move(fr, to, QUIET))
            # Double push
            double = ((single & RANK[2]) << 8) & ~occ & FULL
            bb = double
            while bb:
                to, bb = pop_lsb(bb)
                moves.append(make_move(to - 16, to, DOUBLE_PUSH))
            # Captures
            bb = pawns
            while bb:
                fr, bb = pop_lsb(bb)
                att = PAWN_ATTACKS[WHITE][fr] & opp_bb
                while att:
                    to, att = pop_lsb(att)
                    if rank_of(to) == 7:
                        for fl in (PROMO_CN, PROMO_CB, PROMO_CR, PROMO_CQ):
                            moves.append(make_move(fr, to, fl))
                    else:
                        moves.append(make_move(fr, to, CAPTURE))
            # En passant
            if self.ep != -1:
                bb = PAWN_ATTACKS[BLACK][self.ep] & pawns
                while bb:
                    fr, bb = pop_lsb(bb)
                    moves.append(make_move(fr, self.ep, EP_CAPTURE))
        else:
            # Single push
            single = (pawns >> 8) & ~occ & FULL
            bb = single
            while bb:
                to, bb = pop_lsb(bb)
                fr = to + 8
                if rank_of(to) == 0:
                    for fl in (PROMO_N, PROMO_B, PROMO_R, PROMO_Q):
                        moves.append(make_move(fr, to, fl))
                else:
                    moves.append(make_move(fr, to, QUIET))
            # Double push
            double = ((single & RANK[5]) >> 8) & ~occ & FULL
            bb = double
            while bb:
                to, bb = pop_lsb(bb)
                moves.append(make_move(to + 16, to, DOUBLE_PUSH))
            # Captures
            bb = pawns
            while bb:
                fr, bb = pop_lsb(bb)
                att = PAWN_ATTACKS[BLACK][fr] & opp_bb
                while att:
                    to, att = pop_lsb(att)
                    if rank_of(to) == 0:
                        for fl in (PROMO_CN, PROMO_CB, PROMO_CR, PROMO_CQ):
                            moves.append(make_move(fr, to, fl))
                    else:
                        moves.append(make_move(fr, to, CAPTURE))
            # En passant
            if self.ep != -1:
                bb = PAWN_ATTACKS[WHITE][self.ep] & pawns
                while bb:
                    fr, bb = pop_lsb(bb)
                    moves.append(make_move(fr, self.ep, EP_CAPTURE))

        # ── Knights ────────────────────────────────────────────────────────────
        bb = self.pieces[base + 1]
        while bb:
            fr, bb = pop_lsb(bb)
            att = KNIGHT_ATTACKS[fr] & ~own
            while att:
                to, att = pop_lsb(att)
                fl = CAPTURE if opp_bb & bit(to) else QUIET
                moves.append(make_move(fr, to, fl))

        # ── Bishops ────────────────────────────────────────────────────────────
        bb = self.pieces[base + 2]
        while bb:
            fr, bb = pop_lsb(bb)
            att = sliding_attacks(fr, occ, BISHOP_DIRS) & ~own
            while att:
                to, att = pop_lsb(att)
                fl = CAPTURE if opp_bb & bit(to) else QUIET
                moves.append(make_move(fr, to, fl))

        # ── Rooks ──────────────────────────────────────────────────────────────
        bb = self.pieces[base + 3]
        while bb:
            fr, bb = pop_lsb(bb)
            att = sliding_attacks(fr, occ, ROOK_DIRS) & ~own
            while att:
                to, att = pop_lsb(att)
                fl = CAPTURE if opp_bb & bit(to) else QUIET
                moves.append(make_move(fr, to, fl))

        # ── Queens ─────────────────────────────────────────────────────────────
        bb = self.pieces[base + 4]
        while bb:
            fr, bb = pop_lsb(bb)
            att = sliding_attacks(fr, occ, QUEEN_DIRS) & ~own
            while att:
                to, att = pop_lsb(att)
                fl = CAPTURE if opp_bb & bit(to) else QUIET
                moves.append(make_move(fr, to, fl))

        # ── King ───────────────────────────────────────────────────────────────
        fr = lsb(self.pieces[base + 5])
        att = KING_ATTACKS[fr] & ~own
        while att:
            to, att = pop_lsb(att)
            fl = CAPTURE if opp_bb & bit(to) else QUIET
            moves.append(make_move(fr, to, fl))

        # ── Castling ───────────────────────────────────────────────────────────
        if side == WHITE:
            if (self.castling & WK_SIDE) and not (occ & (bit(5)|bit(6))) \
               and not self.attacked_by(4,BLACK) and not self.attacked_by(5,BLACK) and not self.attacked_by(6,BLACK):
                moves.append(make_move(4, 6, CASTLE_K))
            if (self.castling & WQ_SIDE) and not (occ & (bit(1)|bit(2)|bit(3))) \
               and not self.attacked_by(4,BLACK) and not self.attacked_by(3,BLACK) and not self.attacked_by(2,BLACK):
                moves.append(make_move(4, 2, CASTLE_Q))
        else:
            if (self.castling & BK_SIDE) and not (occ & (bit(61)|bit(62))) \
               and not self.attacked_by(60,WHITE) and not self.attacked_by(61,WHITE) and not self.attacked_by(62,WHITE):
                moves.append(make_move(60, 62, CASTLE_K))
            if (self.castling & BQ_SIDE) and not (occ & (bit(57)|bit(58)|bit(59))) \
               and not self.attacked_by(60,WHITE) and not self.attacked_by(59,WHITE) and not self.attacked_by(58,WHITE):
                moves.append(make_move(60, 58, CASTLE_Q))

        return moves

    # ── FEN parsing ───────────────────────────────────────────────────────────
    @classmethod
    def from_fen(cls, fen=START_FEN):
        b = cls()
        parts = fen.split()
        rows = parts[0].split('/')
        FEN_MAP = {'P':WP,'N':WN,'B':WB,'R':WR,'Q':WQ,'K':WK,
                   'p':BP,'n':BN,'b':BB,'r':BR,'q':BQ,'k':BK}
        for r, row in enumerate(reversed(rows)):
            f = 0
            for ch in row:
                if ch.isdigit():
                    f += int(ch)
                else:
                    b.pieces[FEN_MAP[ch]] |= bit(sq_idx(f, r))
                    f += 1
        b.side     = WHITE if parts[1] == 'w' else BLACK
        castle_str = parts[2]
        b.castling = 0
        if 'K' in castle_str: b.castling |= WK_SIDE
        if 'Q' in castle_str: b.castling |= WQ_SIDE
        if 'k' in castle_str: b.castling |= BK_SIDE
        if 'q' in castle_str: b.castling |= BQ_SIDE
        b.ep       = sq_from_name(parts[3]) if parts[3] != '-' else -1
        b.halfmove = int(parts[4]) if len(parts) > 4 else 0
        b.fullmove = int(parts[5]) if len(parts) > 5 else 1
        b.hash     = b._compute_hash()
        return b

    def __repr__(self):
        rows = []
        for r in range(7, -1, -1):
            row = ''
            for f in range(8):
                p = self.piece_at(sq_idx(f, r))
                row += (PIECE_NAMES[p] if p != -1 else '.') + ' '
            rows.append(f"{r+1}  {row}")
        rows.append("   a b c d e f g h")
        return '\n'.join(rows)
