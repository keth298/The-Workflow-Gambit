#include "movegen.h"
#include "bitboard.h"
#include <algorithm>

// ── Internal helpers ──────────────────────────────────────────────────────────
static void add_promotions(MoveList &ml, Square from, Square to, bool quiet) {
    ml.push(make_promo(from, to, QUEEN));
    if (quiet) {
        ml.push(make_promo(from, to, ROOK));
        ml.push(make_promo(from, to, BISHOP));
        ml.push(make_promo(from, to, KNIGHT));
    } else {
        // Under-promotions that might capture (still useful for search)
        ml.push(make_promo(from, to, KNIGHT));
    }
}

// ── Pawn moves ────────────────────────────────────────────────────────────────
static void gen_pawns(const Position &pos, MoveList &ml, GenMode mode,
                      Bitboard target_mask)
{
    Color us = pos.side_to_move();
    Color opp = ~us;
    Bitboard pawns = pos.pieces(us, PAWN);
    Bitboard occ   = pos.pieces();
    Bitboard opp_bb = pos.pieces(opp);

    // Promotion rank and push direction
    Bitboard promo_rank = (us == WHITE) ? RANK8_BB : RANK1_BB;
    Bitboard start_rank = (us == WHITE) ? RANK2_BB : RANK7_BB;

    if (mode != GEN_QUIET) {
        // Captures
        Bitboard cap_l, cap_r;
        if (us == WHITE) {
            cap_l = BB::shift<NW>(pawns) & opp_bb & target_mask;
            cap_r = BB::shift<NE>(pawns) & opp_bb & target_mask;
        } else {
            cap_l = BB::shift<SW>(pawns) & opp_bb & target_mask;
            cap_r = BB::shift<SE>(pawns) & opp_bb & target_mask;
        }
        while (cap_l) {
            Square to = pop_lsb(cap_l);
            Square from = Square(to + ((us == WHITE) ? -7 : 9));
            if (sq_bb(to) & promo_rank) add_promotions(ml, from, to, false);
            else ml.push(make_move(from, to));
        }
        while (cap_r) {
            Square to = pop_lsb(cap_r);
            Square from = Square(to + ((us == WHITE) ? -9 : 7));
            if (sq_bb(to) & promo_rank) add_promotions(ml, from, to, false);
            else ml.push(make_move(from, to));
        }
        // En passant
        if (pos.ep_sq() != NO_SQ) {
            Bitboard ep_att = BB::pawn_attacks(opp, pos.ep_sq()) & pawns;
            while (ep_att) {
                Square from = pop_lsb(ep_att);
                ml.push(make_ep(from, pos.ep_sq()));
            }
        }
    }

    if (mode != GEN_CAPTURES) {
        // Single and double pushes
        Bitboard empty = ~occ;
        Bitboard push1 = (us == WHITE) ? BB::shift<NORTH>(pawns) & empty
                                        : BB::shift<SOUTH>(pawns) & empty;
        Bitboard push2 = (us == WHITE) ? BB::shift<NORTH>(push1 & ~promo_rank) & empty & start_rank << 16
                                        : BB::shift<SOUTH>(push1 & ~promo_rank) & empty & start_rank >> 16;
        // Simpler double push
        push2 = (us == WHITE) ? BB::shift<NORTH>(BB::shift<NORTH>(pawns & start_rank) & empty) & empty
                               : BB::shift<SOUTH>(BB::shift<SOUTH>(pawns & start_rank) & empty) & empty;

        Bitboard promo_pushes = push1 & promo_rank & target_mask;
        push1 &= ~promo_rank & target_mask;
        push2 &= target_mask;

        while (promo_pushes) {
            Square to = pop_lsb(promo_pushes);
            Square from = Square(to + (us == WHITE ? -8 : 8));
            add_promotions(ml, from, to, true);
        }
        while (push1) {
            Square to = pop_lsb(push1);
            ml.push(make_move(Square(to + (us == WHITE ? -8 : 8)), to));
        }
        while (push2) {
            Square to = pop_lsb(push2);
            ml.push(make_move(Square(to + (us == WHITE ? -16 : 16)), to));
        }
    }
}

// ── Piece moves ───────────────────────────────────────────────────────────────
static void gen_piece(const Position &pos, MoveList &ml, PieceType pt,
                      Bitboard target_mask)
{
    Color us = pos.side_to_move();
    Bitboard occ  = pos.pieces();
    Bitboard src  = pos.pieces(us, pt);
    while (src) {
        Square from = pop_lsb(src);
        Bitboard att;
        switch (pt) {
            case KNIGHT: att = BB::knight_attacks(from); break;
            case BISHOP: att = BB::bishop_attacks(from, occ); break;
            case ROOK:   att = BB::rook_attacks  (from, occ); break;
            case QUEEN:  att = BB::queen_attacks (from, occ); break;
            case KING:   att = BB::king_attacks  (from); break;
            default:     att = 0; break;
        }
        att &= target_mask;
        while (att) {
            ml.push(make_move(from, pop_lsb(att)));
        }
    }
}

// ── Castling ──────────────────────────────────────────────────────────────────
static void gen_castling(const Position &pos, MoveList &ml) {
    Color us  = pos.side_to_move();
    Color opp = ~us;
    Bitboard occ = pos.pieces();

    if (us == WHITE) {
        if (pos.can_castle(W_OO)) {
            // F1, G1 must be empty; king and rook squares not attacked
            if (!(occ & (sq_bb(F1) | sq_bb(G1)))
                && !pos.is_attacked(E1, opp)
                && !pos.is_attacked(F1, opp)
                && !pos.is_attacked(G1, opp))
                ml.push(make_castle(E1, G1));
        }
        if (pos.can_castle(W_OOO)) {
            if (!(occ & (sq_bb(B1) | sq_bb(C1) | sq_bb(D1)))
                && !pos.is_attacked(E1, opp)
                && !pos.is_attacked(D1, opp)
                && !pos.is_attacked(C1, opp))
                ml.push(make_castle(E1, C1));
        }
    } else {
        if (pos.can_castle(B_OO)) {
            if (!(occ & (sq_bb(F8) | sq_bb(G8)))
                && !pos.is_attacked(E8, opp)
                && !pos.is_attacked(F8, opp)
                && !pos.is_attacked(G8, opp))
                ml.push(make_castle(E8, G8));
        }
        if (pos.can_castle(B_OOO)) {
            if (!(occ & (sq_bb(B8) | sq_bb(C8) | sq_bb(D8)))
                && !pos.is_attacked(E8, opp)
                && !pos.is_attacked(D8, opp)
                && !pos.is_attacked(C8, opp))
                ml.push(make_castle(E8, C8));
        }
    }
}

// ── Main generator ────────────────────────────────────────────────────────────
void generate_moves(const Position &pos, MoveList &ml, GenMode mode) {
    Color us  = pos.side_to_move();
    Color opp = ~us;
    Bitboard opp_bb  = pos.pieces(opp);
    Bitboard empty_bb = ~pos.pieces();
    Bitboard occ     = pos.pieces();

    // Check evasions: restrict target squares
    Bitboard checkers = pos.checkers();
    if (checkers && mode != GEN_CAPTURES) mode = GEN_EVASIONS;

    Bitboard target;
    switch (mode) {
        case GEN_CAPTURES:  target = opp_bb; break;
        case GEN_QUIET:     target = empty_bb; break;
        case GEN_EVASIONS:
            if (more_than_one(checkers)) {
                // Double check: only king moves
                Bitboard k_att = BB::king_attacks(pos.king_sq(us)) & ~pos.pieces(us);
                while (k_att) ml.push(make_move(pos.king_sq(us), pop_lsb(k_att)));
                return;
            }
            // Single checker: block or capture it
            target = checkers | BB::between(pos.king_sq(us), lsb(checkers));
            break;
        default: // GEN_ALL
            target = ~pos.pieces(us);
            break;
    }

    gen_pawns(pos, ml, mode, target);

    Bitboard not_us = ~pos.pieces(us);
    Bitboard t = (mode == GEN_EVASIONS) ? target : not_us;
    if (mode == GEN_CAPTURES) t = opp_bb;
    if (mode == GEN_QUIET)    t = empty_bb;

    for (PieceType pt : {KNIGHT, BISHOP, ROOK, QUEEN})
        gen_piece(pos, ml, pt, t);

    // King moves (always vs. ~own_pieces, legality checked later)
    {
        Bitboard k_att = BB::king_attacks(pos.king_sq(us)) & ~pos.pieces(us);
        if (mode == GEN_CAPTURES) k_att &= opp_bb;
        if (mode == GEN_QUIET)    k_att &= empty_bb;
        while (k_att) ml.push(make_move(pos.king_sq(us), pop_lsb(k_att)));
    }

    if (mode == GEN_ALL || mode == GEN_QUIET)
        if (!checkers) gen_castling(pos, ml);
}

// ── Legal wrapper ─────────────────────────────────────────────────────────────
LegalMoveList::LegalMoveList(const Position &pos, GenMode mode) {
    MoveList pseudo;
    generate_moves(pos, pseudo, mode);
    for (Move m : pseudo)
        if (pos.is_legal(m))
            list.push(m);
}
