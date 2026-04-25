#include "bitboard.h"
#include <cstring>
#include <cstdlib>
#include <cstdio>

namespace BB {

Bitboard KNIGHT_ATTACKS[64];
Bitboard KING_ATTACKS[64];
Bitboard PAWN_ATTACKS[2][64];
Bitboard BETWEEN_BB[64][64];
Bitboard LINE_BB[64][64];

MagicEntry ROOK_MAGIC[64];
MagicEntry BISHOP_MAGIC[64];

// Conservative table sizes:
// Rook: max 2^12 = 4096 entries per square × 64 = 262144
// Bishop: max 2^9 = 512 entries per square × 64 = 32768
// We use flat arrays to avoid cumulative-offset bugs.
static Bitboard ROOK_FLAT[64][4096];
static Bitboard BISHOP_FLAT[64][512];

// ── Slow occupancy-aware ray walker ──────────────────────────────────────────
Bitboard sliding_attacks(PieceType pt, Square sq, Bitboard occ) {
    const int rook_dirs[4]   = {  8, -8,  1, -1 };
    const int bishop_dirs[4] = {  9, -9,  7, -7 };
    const int *dirs = (pt == ROOK) ? rook_dirs : bishop_dirs;
    Bitboard result = 0;

    for (int d = 0; d < 4; ++d) {
        int cur = sq;
        for (;;) {
            int next = cur + dirs[d];
            if (next < 0 || next >= 64) break;

            // Detect file-wrap (horizontal/diagonal directions)
            if (std::abs(file_of(next) - file_of(cur)) > 1) break;

            result |= sq_bb(next);
            if (occ & sq_bb(next)) break;
            cur = next;
        }
    }
    return result;
}

// ── Occupancy subset from index (for magic init) ──────────────────────────────
static Bitboard occ_subset(int idx, Bitboard mask) {
    Bitboard occ = 0;
    int bit = 0;
    while (mask) {
        Square s = pop_lsb(mask);
        if (idx & (1 << bit)) occ |= sq_bb(s);
        ++bit;
    }
    return occ;
}

// ── LCG random for magic search ───────────────────────────────────────────────
static u64 prng_state = 0x8F4F232BC2E3C7ABULL;
static u64 sparse_rand() {
    // XorShift64* variant – sparse output (few set bits) is better for magics
    prng_state ^= prng_state >> 12;
    prng_state ^= prng_state << 25;
    prng_state ^= prng_state >> 27;
    u64 r = prng_state * 0x2545F4914F6CDD1DULL;
    // Use AND of three randoms to get sparse number
    prng_state ^= prng_state >> 12;
    prng_state ^= prng_state << 25;
    prng_state ^= prng_state >> 27;
    u64 r2 = prng_state * 0x2545F4914F6CDD1DULL;
    prng_state ^= prng_state >> 12;
    prng_state ^= prng_state << 25;
    prng_state ^= prng_state >> 27;
    u64 r3 = prng_state * 0x2545F4914F6CDD1DULL;
    return r & r2 & r3;
}

// ── Find a magic number for one square ───────────────────────────────────────
static u64 find_magic(PieceType pt, Square s, int shift, Bitboard mask,
                      Bitboard *attacks_out, Bitboard *ref_attacks)
{
    int bits = popcount(mask);
    int size = 1 << (64 - shift);   // table entries for this magic
    int n    = 1 << bits;            // number of relevant occupancies

    // Precompute all occupancy subsets and their attack sets
    // Max n = 2^12 = 4096 (rook corners)
    Bitboard occs[4096], atts[4096];
    for (int i = 0; i < n; ++i) {
        occs[i] = occ_subset(i, mask);
        atts[i] = sliding_attacks(pt, s, occs[i]);
    }

    // Temporary table for collision checking
    static Bitboard used[4096];

    for (;;) {
        u64 magic = sparse_rand();

        // Quick filter: high bits of (mask * magic) should have enough set bits
        if (popcount((mask * magic) >> 56) < 6) continue;

        memset(used, 0, sizeof(Bitboard) * size);
        bool fail = false;

        for (int i = 0; i < n && !fail; ++i) {
            int key = int((occs[i] * magic) >> shift);
            if (key < 0 || key >= size) { fail = true; break; }
            if (used[key] && used[key] != atts[i]) fail = true;
            else used[key] = atts[i];
        }

        if (!fail) {
            // Copy into output table
            for (int i = 0; i < size; ++i)
                attacks_out[i] = used[i];
            return magic;
        }
    }
}

// ── Build non-sliding attack tables ──────────────────────────────────────────
static void init_leaper_attacks() {
    for (Square s = A1; s <= H8; ++s) {
        Bitboard bb = sq_bb(s);

        // Knight
        Bitboard kn = 0;
        kn |= ((bb & ~FILEA_BB & ~(FILEA_BB << 1)) << 6);   // south-south-west? no
        // Let's be explicit:
        kn = 0;
        // From sq, knight can go to 8 possible squares
        // N+NE: 2N 1E = +17, but not on H file
        // N+NW: 2N 1W = +15, but not on A file
        // E+NE: 1N 2E = +10, but not on G or H file
        // E+SE: 1S 2E = -6,  but not on G or H file
        // S+SE: 2S 1E = -15, but not on H file
        // S+SW: 2S 1W = -17, but not on A file
        // W+NW: 1N 2W = +6,  but not on A or B file
        // W+SW: 1S 2W = -10, but not on A or B file
        if (rank_of(s) <= 5 && file_of(s) <= 6) kn |= sq_bb(s + 17);  // +2r+1f
        if (rank_of(s) <= 5 && file_of(s) >= 1) kn |= sq_bb(s + 15);  // +2r-1f
        if (rank_of(s) <= 6 && file_of(s) <= 5) kn |= sq_bb(s + 10);  // +1r+2f
        if (rank_of(s) >= 1 && file_of(s) <= 5) kn |= sq_bb(s -  6);  // -1r+2f
        if (rank_of(s) >= 2 && file_of(s) <= 6) kn |= sq_bb(s - 15);  // -2r+1f
        if (rank_of(s) >= 2 && file_of(s) >= 1) kn |= sq_bb(s - 17);  // -2r-1f
        if (rank_of(s) <= 6 && file_of(s) >= 2) kn |= sq_bb(s +  6);  // +1r-2f
        if (rank_of(s) >= 1 && file_of(s) >= 2) kn |= sq_bb(s - 10);  // -1r-2f
        KNIGHT_ATTACKS[s] = kn;

        // King
        Bitboard k = 0;
        k |= shift<NORTH>(bb) | shift<SOUTH>(bb)
           | shift<EAST> (bb) | shift<WEST> (bb)
           | shift<NE>   (bb) | shift<NW>   (bb)
           | shift<SE>   (bb) | shift<SW>   (bb);
        KING_ATTACKS[s] = k;

        // Pawns
        PAWN_ATTACKS[WHITE][s] = shift<NW>(bb) | shift<NE>(bb);
        PAWN_ATTACKS[BLACK][s] = shift<SW>(bb) | shift<SE>(bb);
    }
}

// ── Build BETWEEN and LINE tables ─────────────────────────────────────────────
static void init_between_line() {
    for (int s1 = 0; s1 < 64; ++s1)
    for (int s2 = 0; s2 < 64; ++s2) {
        BETWEEN_BB[s1][s2] = 0;
        LINE_BB[s1][s2]    = 0;
        if (s1 == s2) continue;

        int df = file_of(s2) - file_of(s1);
        int dr = rank_of(s2) - rank_of(s1);

        // Determine alignment and step direction
        int step = 0;
        if      (dr == 0)        step = (df > 0) ? 1 : -1;
        else if (df == 0)        step = (dr > 0) ? 8 : -8;
        else if (df ==  dr)      step = (dr > 0) ? 9 : -9;
        else if (df == -dr)      step = (dr > 0) ? 7 : -7;
        else continue;   // not aligned → skip

        // Squares strictly between s1 and s2
        int cur = s1 + step;
        while (cur != s2) {
            if (cur < 0 || cur >= 64) break;   // safety
            // Check file wrap (for diagonal/horizontal rays)
            if (std::abs(file_of(cur) - file_of(cur - step)) > 1) break;
            BETWEEN_BB[s1][s2] |= sq_bb(cur);
            cur += step;
        }

        // Full line through both squares (on the board)
        // Walk forward from s1
        cur = s1;
        for (;;) {
            int nxt = cur + step;
            if (nxt < 0 || nxt >= 64) break;
            if (std::abs(file_of(nxt) - file_of(cur)) > 1) break;
            LINE_BB[s1][s2] |= sq_bb(nxt);
            cur = nxt;
        }
        // Walk backward from s1
        cur = s1;
        for (;;) {
            int nxt = cur - step;
            if (nxt < 0 || nxt >= 64) break;
            if (std::abs(file_of(nxt) - file_of(cur)) > 1) break;
            LINE_BB[s1][s2] |= sq_bb(nxt);
            cur = nxt;
        }
        LINE_BB[s1][s2] |= sq_bb(s1) | sq_bb(s2);
    }
}

// ── Main init ────────────────────────────────────────────────────────────────
void init() {
    init_leaper_attacks();
    init_between_line();

    // Compute masks and find magic numbers for all squares
    Bitboard edge = RANK1_BB | RANK8_BB | FILEA_BB | FILEH_BB;

    for (Square s = A1; s <= H8; ++s) {
        // Rook
        {
            // Relevant occupancy = inner squares on the rank and file
            Bitboard rank_inner = rank_bb(rank_of(s)) & ~(FILEA_BB | FILEH_BB);
            Bitboard file_inner = file_bb(file_of(s)) & ~(RANK1_BB | RANK8_BB);
            Bitboard mask = (rank_inner | file_inner) & ~sq_bb(s);
            int bits = popcount(mask);
            // Use exactly 'bits' index bits → shift = 64 - bits
            int shift = 64 - bits;

            ROOK_MAGIC[s].mask    = mask;
            ROOK_MAGIC[s].shift   = shift;
            ROOK_MAGIC[s].attacks = ROOK_FLAT[s];

            u64 magic = find_magic(ROOK, s, shift, mask, ROOK_FLAT[s], nullptr);
            ROOK_MAGIC[s].magic = magic;
        }

        // Bishop
        {
            // Relevant occupancy = inner diagonals (exclude board edges)
            Bitboard mask = sliding_attacks(BISHOP, s, 0) & ~edge;
            int bits = popcount(mask);
            int shift = 64 - bits;

            BISHOP_MAGIC[s].mask    = mask;
            BISHOP_MAGIC[s].shift   = shift;
            BISHOP_MAGIC[s].attacks = BISHOP_FLAT[s];

            u64 magic = find_magic(BISHOP, s, shift, mask, BISHOP_FLAT[s], nullptr);
            BISHOP_MAGIC[s].magic = magic;
        }
    }
}

} // namespace BB
