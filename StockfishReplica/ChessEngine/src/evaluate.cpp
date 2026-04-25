#include "evaluate.h"
#include "bitboard.h"
#include <algorithm>

// ── Piece-Square Tables (middlegame, then endgame) ────────────────────────────
// Scores are from White's perspective; Black's are mirrored.
// Format: a1..h8 (rank 0 first)

static const int PST_PAWN_MG[64] = {
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
};
static const int PST_PAWN_EG[64] = {
     0,  0,  0,  0,  0,  0,  0,  0,
    80, 80, 80, 80, 80, 80, 80, 80,
    50, 50, 50, 50, 50, 50, 50, 50,
    30, 30, 30, 30, 30, 30, 30, 30,
    15, 15, 15, 15, 15, 15, 15, 15,
     5,  5,  5,  5,  5,  5,  5,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0
};
static const int PST_KNIGHT_MG[64] = {
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
};
static const int PST_KNIGHT_EG[64] = {
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
};
static const int PST_BISHOP_MG[64] = {
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
};
static const int PST_BISHOP_EG[64] = {
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10,  0, 10, 15, 15, 10,  0,-10,
    -10,  0, 10, 15, 15, 10,  0,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
};
static const int PST_ROOK_MG[64] = {
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0
};
static const int PST_ROOK_EG[64] = {
     5,  5,  5,  5,  5,  5,  5,  5,
     5,  5,  5,  5,  5,  5,  5,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0
};
static const int PST_QUEEN_MG[64] = {
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
};
static const int PST_QUEEN_EG[64] = {
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -10,  5,  5,  5,  5,  5,  0,-10,
      0,  0,  5,  5,  5,  5,  0, -5,
     -5,  0,  5,  5,  5,  5,  0, -5,
    -10,  0,  5,  5,  5,  5,  0,-10,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
};
static const int PST_KING_MG[64] = {
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20
};
static const int PST_KING_EG[64] = {
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50
};

static const int *PST_MG[6] = {
    PST_PAWN_MG, PST_KNIGHT_MG, PST_BISHOP_MG,
    PST_ROOK_MG, PST_QUEEN_MG,  PST_KING_MG
};
static const int *PST_EG[6] = {
    PST_PAWN_EG, PST_KNIGHT_EG, PST_BISHOP_EG,
    PST_ROOK_EG, PST_QUEEN_EG,  PST_KING_EG
};

// Mirror square for black (row-flip)
static inline int mirror(int s) { return s ^ 56; }

// ── Pawn structure helpers ─────────────────────────────────────────────────────
static Bitboard passed_pawn_mask(Color c, Square s) {
    // Files adjacent and same, all ranks in front
    Bitboard front;
    if (c == WHITE) front = ~((Bitboard(1) << (8 * (rank_of(s) + 1))) - 1);
    else            front = (Bitboard(1) << (8 * rank_of(s))) - 1;
    Bitboard adj_files = file_bb(file_of(s));
    if (file_of(s) > 0) adj_files |= file_bb(file_of(s) - 1);
    if (file_of(s) < 7) adj_files |= file_bb(file_of(s) + 1);
    return front & adj_files;
}

// ── Main evaluation ───────────────────────────────────────────────────────────
Score evaluate(const Position &pos) {
    int mg_score[2] = {0, 0};
    int eg_score[2] = {0, 0};
    int phase = 0;

    Bitboard occ = pos.pieces();

    for (Color c : {WHITE, BLACK}) {
        // Material + PST
        for (int pt = PAWN; pt <= KING; ++pt) {
            Bitboard bb = pos.pieces(c, PieceType(pt));
            phase += popcount(bb) * PHASE_WEIGHT[pt];
            while (bb) {
                Square s = pop_lsb(bb);
                int pst_sq = (c == WHITE) ? mirror(s) : s;
                int mat = PIECE_VALUE[pt];
                mg_score[c] += mat + PST_MG[pt][pst_sq];
                eg_score[c] += mat + PST_EG[pt][pst_sq];
            }
        }

        // Pawn structure
        Bitboard own_pawns = pos.pieces(c, PAWN);
        Bitboard opp_pawns = pos.pieces(~c, PAWN);

        // Doubled pawns
        for (int f = 0; f < 8; ++f) {
            int cnt = popcount(own_pawns & file_bb(f));
            if (cnt > 1) {
                mg_score[c] -= 10 * (cnt - 1);
                eg_score[c] -= 20 * (cnt - 1);
            }
        }

        // Isolated and passed pawns
        Bitboard tmp = own_pawns;
        while (tmp) {
            Square s = pop_lsb(tmp);
            int f = file_of(s);
            Bitboard adj_files = 0;
            if (f > 0) adj_files |= file_bb(f - 1);
            if (f < 7) adj_files |= file_bb(f + 1);
            if (!(own_pawns & adj_files)) {
                mg_score[c] -= 15;
                eg_score[c] -= 20;
            }
            if (!(passed_pawn_mask(c, s) & opp_pawns)) {
                int r = (c == WHITE) ? rank_of(s) : 7 - rank_of(s);
                mg_score[c] += 5 + r * r * 2;
                eg_score[c] += 10 + r * r * 5;
            }
        }

        // Bishop pair bonus
        if (popcount(pos.pieces(c, BISHOP)) >= 2) {
            mg_score[c] += 30;
            eg_score[c] += 50;
        }

        // Rooks on open/semi-open files
        Bitboard rooks = pos.pieces(c, ROOK);
        while (rooks) {
            Square s = pop_lsb(rooks);
            Bitboard file = file_bb(file_of(s));
            if (!(own_pawns & file)) {
                if (!(opp_pawns & file)) { mg_score[c] += 20; eg_score[c] += 15; }
                else                     { mg_score[c] += 10; eg_score[c] +=  7; }
            }
        }

        // King safety (simple: penalize open files near king in MG)
        Square ksq = pos.king_sq(c);
        int kf = file_of(ksq);
        for (int df = -1; df <= 1; ++df) {
            int f = kf + df;
            if (f < 0 || f > 7) continue;
            if (!(own_pawns & file_bb(f))) {
                mg_score[c] -= 20;
                if (!(opp_pawns & file_bb(f))) mg_score[c] -= 10;
            }
        }

        // Mobility bonus
        Bitboard mob_area = ~pos.pieces(c);
        for (int pt : {KNIGHT, BISHOP, ROOK, QUEEN}) {
            Bitboard pieces = pos.pieces(c, PieceType(pt));
            while (pieces) {
                Square s = pop_lsb(pieces);
                int mob = 0;
                Bitboard att;
                switch (pt) {
                    case KNIGHT: att = BB::knight_attacks(s) & mob_area; break;
                    case BISHOP: att = BB::bishop_attacks(s, occ) & mob_area; break;
                    case ROOK:   att = BB::rook_attacks  (s, occ) & mob_area; break;
                    case QUEEN:  att = BB::queen_attacks (s, occ) & mob_area; break;
                    default: att = 0;
                }
                mob = popcount(att);
                static const int MOB_MG[4] = {4, 3, 2, 1};
                static const int MOB_EG[4] = {4, 3, 3, 2};
                mg_score[c] += mob * MOB_MG[pt - KNIGHT];
                eg_score[c] += mob * MOB_EG[pt - KNIGHT];
            }
        }
    }

    // Tapered evaluation: interpolate between MG and EG
    int total_phase = 24; // max phase
    phase = std::min(phase, total_phase);
    int mg = mg_score[WHITE] - mg_score[BLACK];
    int eg = eg_score[WHITE] - eg_score[BLACK];
    Score score = Score((mg * phase + eg * (total_phase - phase)) / total_phase);

    // Contempt (slight bonus for having more material in drawn-ish positions)
    // Tempo bonus
    score += 10;  // a small bonus for side to move

    return pos.side_to_move() == WHITE ? score : -score;
}
