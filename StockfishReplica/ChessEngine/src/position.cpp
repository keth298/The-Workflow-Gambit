#include "position.h"
#include "bitboard.h"
#include "zobrist.h"
#include <sstream>
#include <cstring>
#include <algorithm>

// ── Internal helpers ──────────────────────────────────────────────────────────
void Position::put_piece(Piece p, Square s) {
    board_[s]           = p;
    Bitboard bit        = sq_bb(s);
    by_type_[type_of(p)] |= bit;
    occupancy_[color_of(p)] |= bit;
    occupancy_[2]         |= bit;
    if (type_of(p) == KING) king_sq_[color_of(p)] = s;
}

void Position::remove_piece(Square s) {
    Piece p = board_[s];
    Bitboard bit = sq_bb(s);
    by_type_[type_of(p)] &= ~bit;
    occupancy_[color_of(p)] &= ~bit;
    occupancy_[2]           &= ~bit;
    board_[s] = NO_PIECE;
}

void Position::move_piece(Square from, Square to) {
    Piece p = board_[from];
    Bitboard mask = sq_bb(from) | sq_bb(to);
    by_type_[type_of(p)] ^= mask;
    occupancy_[color_of(p)] ^= mask;
    occupancy_[2]           ^= mask;
    board_[to]   = p;
    board_[from] = NO_PIECE;
    if (type_of(p) == KING) king_sq_[color_of(p)] = to;
}

// ── Check / pin computation ───────────────────────────────────────────────────
void Position::compute_check_info(StateInfo &st) const {
    Color us  = stm_;
    Color opp = ~us;
    Square ksq = king_sq_[us];

    // Checkers: all opponent pieces attacking the king
    st.checkers = attackers_to(ksq, pieces()) & pieces(opp);

    // Pinned pieces for both sides
    for (Color c : {WHITE, BLACK}) {
        st.pinned[c] = 0;
        Square ks = king_sq_[c];
        Color  att = ~c;
        Bitboard snipers = (BB::rook_attacks  (ks, 0) & pieces(att, ROOK,   QUEEN))
                         | (BB::bishop_attacks(ks, 0) & pieces(att, BISHOP, QUEEN));
        Bitboard occ = pieces();
        while (snipers) {
            Square sn = pop_lsb(snipers);
            Bitboard between = BB::between(ks, sn) & occ;
            if (between && !more_than_one(between)) {
                // Exactly one piece between king and sniper
                if (between & pieces(c))
                    st.pinned[c] |= between;
            }
        }
    }

    // check_sq[pt]: squares from which pt gives check to the opponent king
    Square opp_ksq = king_sq_[opp];
    Bitboard occ = pieces();
    st.check_sq[PAWN]   = BB::pawn_attacks(opp, opp_ksq);
    st.check_sq[KNIGHT] = BB::knight_attacks(opp_ksq);
    st.check_sq[BISHOP] = BB::bishop_attacks(opp_ksq, occ);
    st.check_sq[ROOK]   = BB::rook_attacks  (opp_ksq, occ);
    st.check_sq[QUEEN]  = st.check_sq[BISHOP] | st.check_sq[ROOK];
    st.check_sq[KING]   = 0;
}

// ── Attackers to a square ─────────────────────────────────────────────────────
Bitboard Position::attackers_to(Square s, Bitboard occ) const {
    return (BB::pawn_attacks(BLACK, s) & pieces(WHITE, PAWN))
         | (BB::pawn_attacks(WHITE, s) & pieces(BLACK, PAWN))
         | (BB::knight_attacks(s)      & pieces(KNIGHT))
         | (BB::king_attacks(s)        & pieces(KING))
         | (BB::bishop_attacks(s, occ) & pieces(BISHOP, QUEEN))
         | (BB::rook_attacks  (s, occ) & pieces(ROOK,   QUEEN));
}

bool Position::is_attacked(Square s, Color by) const {
    return attackers_to(s, pieces()) & pieces(by);
}

// ── FEN parsing ───────────────────────────────────────────────────────────────
void Position::set_fen(const std::string &fen) {
    for (int i = 0; i < 64; ++i) board_[i] = NO_PIECE;
    memset(occupancy_, 0, sizeof(occupancy_));
    memset(by_type_,   0, sizeof(by_type_));
    game_ply_ = 0;
    state_    = state_stack_;
    memset(state_, 0, sizeof(StateInfo));

    std::istringstream ss(fen);
    std::string piece_str, side_str, castle_str, ep_str;
    int half_move = 0, full_move = 1;
    ss >> piece_str >> side_str >> castle_str >> ep_str >> half_move >> full_move;

    // Piece placement
    int rank = 7, file = 0;
    for (char c : piece_str) {
        if (c == '/') { --rank; file = 0; }
        else if (c >= '1' && c <= '8') { file += c - '0'; }
        else {
            const std::string order = "PNBRQK";
            PieceType pt = PieceType(order.find(toupper(c)));
            Color col = isupper(c) ? WHITE : BLACK;
            put_piece(make_piece(col, pt), make_sq(file, rank));
            ++file;
        }
    }

    stm_ = (side_str == "w") ? WHITE : BLACK;

    // Castling
    state_->castling = NO_CASTLE;
    for (char c : castle_str) {
        if (c == 'K') state_->castling |= W_OO;
        if (c == 'Q') state_->castling |= W_OOO;
        if (c == 'k') state_->castling |= B_OO;
        if (c == 'q') state_->castling |= B_OOO;
    }

    // En passant
    state_->ep_sq = NO_SQ;
    if (ep_str != "-") {
        int f = ep_str[0] - 'a';
        int r = ep_str[1] - '1';
        state_->ep_sq = make_sq(f, r);
    }

    state_->fifty          = half_move;
    state_->captured       = NO_PIECE;
    state_->plies_from_null = 0;
    game_ply_ = (full_move - 1) * 2 + (stm_ == BLACK ? 1 : 0);

    // Build Zobrist hash from scratch
    u64 h = 0;
    for (Square s = A1; s <= H8; ++s)
        if (board_[s] != NO_PIECE)
            h ^= Zobrist::PIECE_SQ[board_[s]][s];
    if (stm_ == BLACK) h ^= Zobrist::SIDE_TO_MOVE;
    h ^= Zobrist::CASTLING[state_->castling];
    if (state_->ep_sq != NO_SQ) h ^= Zobrist::EP_FILE[file_of(state_->ep_sq)];
    state_->hash = h;

    compute_check_info(*state_);
}

// ── FEN output ────────────────────────────────────────────────────────────────
std::string Position::fen() const {
    const std::string pc = "PNBRQKpnbrqk";
    std::string s;
    for (int r = 7; r >= 0; --r) {
        int empty = 0;
        for (int f = 0; f < 8; ++f) {
            Piece p = board_[make_sq(f, r)];
            if (p == NO_PIECE) { ++empty; }
            else {
                if (empty) { s += char('0' + empty); empty = 0; }
                s += pc[p];
            }
        }
        if (empty) s += char('0' + empty);
        if (r > 0) s += '/';
    }
    s += ' ';
    s += (stm_ == WHITE) ? 'w' : 'b';
    s += ' ';
    std::string cas;
    if (state_->castling & W_OO)  cas += 'K';
    if (state_->castling & W_OOO) cas += 'Q';
    if (state_->castling & B_OO)  cas += 'k';
    if (state_->castling & B_OOO) cas += 'q';
    if (cas.empty()) cas = "-";
    s += cas;
    s += ' ';
    s += sq_name(state_->ep_sq);
    s += ' ';
    s += std::to_string(state_->fifty);
    s += ' ';
    s += std::to_string(1 + (game_ply_ - (stm_ == BLACK)) / 2);
    return s;
}

// ── Castling rights update table ──────────────────────────────────────────────
// When a piece moves to/from these squares, the corresponding rights are lost.
static const int CASTLING_RIGHTS_MASK[64] = {
    ~W_OOO,15,15,15,~(W_OO|W_OOO),15,15,~W_OO,
    15,15,15,15,15,15,15,15,
    15,15,15,15,15,15,15,15,
    15,15,15,15,15,15,15,15,
    15,15,15,15,15,15,15,15,
    15,15,15,15,15,15,15,15,
    15,15,15,15,15,15,15,15,
    ~B_OOO,15,15,15,~(B_OO|B_OOO),15,15,~B_OO
};

// ── do_move ───────────────────────────────────────────────────────────────────
void Position::do_move(Move m, StateInfo &ns) {
    // Copy state and chain to previous
    ns = *state_;
    ns.previous        = state_;
    ns.captured        = NO_PIECE;
    ns.plies_from_null = state_->plies_from_null + 1;

    Square from = from_sq(m);
    Square to   = to_sq(m);
    MoveType mt = move_type(m);
    Piece    pc = board_[from];
    Color    us = stm_;
    Color    opp= ~us;

    u64 h = ns.hash;

    // Remove old ep
    if (ns.ep_sq != NO_SQ) {
        h ^= Zobrist::EP_FILE[file_of(ns.ep_sq)];
        ns.ep_sq = NO_SQ;
    }

    // Update castling hash
    h ^= Zobrist::CASTLING[ns.castling];

    if (mt == MT_CASTLE) {
        // King and rook move
        move_piece(from, to);
        h ^= Zobrist::PIECE_SQ[pc][from] ^ Zobrist::PIECE_SQ[pc][to];
        // Rook
        Square rfrom, rto;
        if (to > from) { rfrom = (us == WHITE) ? H1 : H8; rto = (us == WHITE) ? F1 : F8; }
        else           { rfrom = (us == WHITE) ? A1 : A8; rto = (us == WHITE) ? D1 : D8; }
        Piece rook = board_[rfrom];
        move_piece(rfrom, rto);
        h ^= Zobrist::PIECE_SQ[rook][rfrom] ^ Zobrist::PIECE_SQ[rook][rto];
    }
    else if (mt == MT_EP) {
        Square cap_sq = make_sq(file_of(to), rank_of(from));
        Piece  cap_pc = board_[cap_sq];
        ns.captured = cap_pc;
        remove_piece(cap_sq);
        h ^= Zobrist::PIECE_SQ[cap_pc][cap_sq];
        move_piece(from, to);
        h ^= Zobrist::PIECE_SQ[pc][from] ^ Zobrist::PIECE_SQ[pc][to];
    }
    else {
        // Normal or promo
        if (!empty(to)) {
            ns.captured = board_[to];
            h ^= Zobrist::PIECE_SQ[ns.captured][to];
            remove_piece(to);
        }
        if (mt == MT_PROMO) {
            PieceType promo_pt = promo_type(m);
            Piece promo_pc = make_piece(us, promo_pt);
            remove_piece(from);
            put_piece(promo_pc, to);
            h ^= Zobrist::PIECE_SQ[pc][from] ^ Zobrist::PIECE_SQ[promo_pc][to];
        } else {
            move_piece(from, to);
            h ^= Zobrist::PIECE_SQ[pc][from] ^ Zobrist::PIECE_SQ[pc][to];
        }
        // Set new en passant square
        if (type_of(pc) == PAWN && std::abs(to - from) == 16) {
            ns.ep_sq = Square((from + to) / 2);
            h ^= Zobrist::EP_FILE[file_of(ns.ep_sq)];
        }
    }

    // Update castling rights
    ns.castling &= CASTLING_RIGHTS_MASK[from] & CASTLING_RIGHTS_MASK[to];
    h ^= Zobrist::CASTLING[ns.castling];

    // Fifty-move rule
    if (type_of(pc) == PAWN || ns.captured != NO_PIECE) ns.fifty = 0;
    else ++ns.fifty;

    // Flip side
    stm_ = opp;
    h ^= Zobrist::SIDE_TO_MOVE;
    ns.hash = h;

    state_ = &ns;
    ++game_ply_;

    compute_check_info(*state_);
}

// ── undo_move ─────────────────────────────────────────────────────────────────
void Position::undo_move(Move m) {
    --game_ply_;
    stm_ = ~stm_;

    Square from = from_sq(m);
    Square to   = to_sq(m);
    MoveType mt = move_type(m);
    Color us    = stm_;
    const StateInfo &cur = *state_;

    if (mt == MT_CASTLE) {
        move_piece(to, from);
        Square rfrom, rto;
        if (to > from) { rfrom = (us == WHITE) ? H1 : H8; rto = (us == WHITE) ? F1 : F8; }
        else           { rfrom = (us == WHITE) ? A1 : A8; rto = (us == WHITE) ? D1 : D8; }
        move_piece(rto, rfrom);
    }
    else if (mt == MT_EP) {
        move_piece(to, from);
        Square cap_sq = make_sq(file_of(to), rank_of(from));
        put_piece(cur.captured, cap_sq);
    }
    else {
        if (mt == MT_PROMO) {
            remove_piece(to);
            put_piece(make_piece(us, PAWN), from);
        } else {
            move_piece(to, from);
        }
        if (cur.captured != NO_PIECE)
            put_piece(cur.captured, to);
    }

    state_ = cur.previous;
}

// ── Null move ─────────────────────────────────────────────────────────────────
void Position::do_null_move(StateInfo &ns) {
    ns = *state_;
    ns.previous = state_;
    if (ns.ep_sq != NO_SQ) {
        ns.hash ^= Zobrist::EP_FILE[file_of(ns.ep_sq)];
        ns.ep_sq = NO_SQ;
    }
    ns.hash ^= Zobrist::SIDE_TO_MOVE;
    ns.fifty++;
    ns.plies_from_null = 0;
    ns.captured = NO_PIECE;

    stm_ = ~stm_;
    state_ = &ns;
    ++game_ply_;
    compute_check_info(*state_);
}

void Position::undo_null_move() {
    --game_ply_;
    stm_ = ~stm_;
    state_ = state_->previous;
}

// ── Legal move check ──────────────────────────────────────────────────────────
bool Position::is_legal(Move m) const {
    Square from = from_sq(m);
    Square to   = to_sq(m);
    Color  us   = stm_;
    Square ksq  = king_sq_[us];
    Bitboard occ = pieces();

    if (move_type(m) == MT_EP) {
        Square cap = make_sq(file_of(to), rank_of(from));
        Bitboard new_occ = (occ ^ sq_bb(from) ^ sq_bb(cap)) | sq_bb(to);
        return !(BB::rook_attacks  (ksq, new_occ) & pieces(~us, ROOK,   QUEEN))
            && !(BB::bishop_attacks(ksq, new_occ) & pieces(~us, BISHOP, QUEEN));
    }

    if (move_type(m) == MT_CASTLE) {
        // Castling: king must not pass through check
        Color opp = ~us;
        int step = (to > from) ? 1 : -1;
        for (Square s = from; s != to + step; s = Square(s + step))
            if (is_attacked(s, opp)) return false;
        return true;
    }

    // Normal: if king moves, verify destination not attacked
    if (from == ksq)
        return !is_attacked(to, ~us);

    // Non-king: must not leave king in check (pinned logic)
    if (!(state_->pinned[us] & sq_bb(from)))
        return true;

    // Pinned piece: must move along pin ray
    return BB::line(ksq, from) & sq_bb(to);
}

// ── gives_check ───────────────────────────────────────────────────────────────
bool Position::gives_check(Move m) const {
    Square from = from_sq(m);
    Square to   = to_sq(m);
    PieceType pt = (move_type(m) == MT_PROMO) ? promo_type(m) : type_of(board_[from]);

    // Direct check
    if (state_->check_sq[pt] & sq_bb(to)) return true;

    // Discovered check
    Square ksq = king_sq_[~stm_];
    if ((state_->pinned[stm_] & sq_bb(from))
        && !(BB::line(ksq, from) & sq_bb(to))) {
        return true; // unblocked discovered check
    }

    if (move_type(m) == MT_CASTLE) {
        Square rto = (to > from) ? Square(from + 1) : Square(from - 1);
        Bitboard occ = (pieces() ^ sq_bb(from) ^ sq_bb(to)) | sq_bb(rto);
        return BB::rook_attacks(rto, occ) & sq_bb(ksq);
    }
    if (move_type(m) == MT_EP) {
        Square cap = make_sq(file_of(to), rank_of(from));
        Bitboard occ = (pieces() ^ sq_bb(from) ^ sq_bb(cap)) | sq_bb(to);
        return (BB::rook_attacks  (ksq, occ) & pieces(stm_, ROOK,   QUEEN))
             | (BB::bishop_attacks(ksq, occ) & pieces(stm_, BISHOP, QUEEN));
    }
    return false;
}

// ── Draw detection ────────────────────────────────────────────────────────────
bool Position::is_draw() const {
    if (state_->fifty >= 100) return true;
    // Insufficient material
    if (!pieces(PAWN) && !pieces(ROOK) && !pieces(QUEEN)) {
        if (popcount(pieces()) <= 3) return true; // K vs K, KN vs K, KB vs K
    }
    // Repetition: walk the chain back by 2 plies at a time
    int cnt = 0;
    const StateInfo *st = state_->previous;
    for (int i = 2; i <= state_->fifty && st; i += 2) {
        if (st->previous) st = st->previous;
        else break;
        if (st->previous) st = st->previous;
        else break;
        if (st->hash == state_->hash && ++cnt >= 2) return true;
    }
    return false;
}

// ── Static Exchange Evaluation (SEE) ─────────────────────────────────────────
int Position::see(Move m, int threshold) const {
    Square from = from_sq(m);
    Square to   = to_sq(m);

    // Gain array: value of captured piece minus value of attacker
    int gain[32];
    int depth = 0;

    Piece target  = board_[to];
    int   cap_val = (target != NO_PIECE) ? PIECE_VALUE[type_of(target)] : 0;
    if (move_type(m) == MT_PROMO)
        cap_val += PIECE_VALUE[promo_type(m)] - PIECE_VALUE[PAWN];

    gain[0] = cap_val;

    Bitboard occ   = pieces();
    Bitboard att   = attackers_to(to, occ);
    Color side     = ~stm_;   // side that just captured (stm_ moved to `to`)
    Piece  attacker = board_[from];

    occ ^= sq_bb(from);

    while (true) {
        ++depth;
        gain[depth] = PIECE_VALUE[type_of(attacker)] - gain[depth - 1];
        if (std::max(-gain[depth - 1], gain[depth]) < 0) break; // prune

        att &= occ;
        att |= (BB::rook_attacks  (to, occ) & pieces(ROOK,   QUEEN))
             | (BB::bishop_attacks(to, occ) & pieces(BISHOP, QUEEN));

        // Find least-valuable attacker for `side`
        Bitboard side_att = att & pieces(side);
        if (!side_att) break;

        for (int pt = PAWN; pt <= KING; ++pt) {
            Bitboard bb = side_att & pieces(PieceType(pt));
            if (bb) {
                attacker = board_[lsb(bb)];
                occ ^= sq_bb(lsb(bb));
                break;
            }
        }
        side = ~side;
    }

    // Minimax over gain array
    --depth;
    while (depth > 0) {
        gain[depth - 1] = -std::max(-gain[depth - 1], gain[depth]);
        --depth;
    }
    return gain[0] >= threshold ? 1 : -1;
}
