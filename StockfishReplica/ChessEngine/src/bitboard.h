#pragma once
#include "types.h"

namespace BB {

// ── Precomputed attack tables ─────────────────────────────────────────────────
extern Bitboard KNIGHT_ATTACKS[64];
extern Bitboard KING_ATTACKS[64];
extern Bitboard PAWN_ATTACKS[2][64];  // [color][sq]

// Ray tables for slider logic
extern Bitboard BETWEEN_BB[64][64];   // squares strictly between two squares
extern Bitboard LINE_BB[64][64];      // full line through two squares (if aligned)

// Magic bitboard structures
struct MagicEntry {
    Bitboard mask;
    u64      magic;
    int      shift;
    Bitboard *attacks;
};

extern MagicEntry ROOK_MAGIC[64];
extern MagicEntry BISHOP_MAGIC[64];

// Attack storage pools are internal to bitboard.cpp (flat per-square arrays)

void init();   // must be called once at startup

// ── Inline attack getters ─────────────────────────────────────────────────────
inline Bitboard knight_attacks(Square s) { return KNIGHT_ATTACKS[s]; }
inline Bitboard king_attacks  (Square s) { return KING_ATTACKS[s]; }
inline Bitboard pawn_attacks  (Color c, Square s) { return PAWN_ATTACKS[c][s]; }

inline Bitboard rook_attacks(Square s, Bitboard occ) {
    const MagicEntry &m = ROOK_MAGIC[s];
    return m.attacks[((occ & m.mask) * m.magic) >> m.shift];
}
inline Bitboard bishop_attacks(Square s, Bitboard occ) {
    const MagicEntry &m = BISHOP_MAGIC[s];
    return m.attacks[((occ & m.mask) * m.magic) >> m.shift];
}
inline Bitboard queen_attacks(Square s, Bitboard occ) {
    return rook_attacks(s, occ) | bishop_attacks(s, occ);
}

// ── Shift helpers (safe: masked before shift to avoid UB) ────────────────────
template<Direction D> Bitboard shift(Bitboard b);

template<> inline Bitboard shift<NORTH>(Bitboard b) { return b << 8; }
template<> inline Bitboard shift<SOUTH>(Bitboard b) { return b >> 8; }
template<> inline Bitboard shift<EAST> (Bitboard b) { return (b & ~FILEH_BB) << 1; }
template<> inline Bitboard shift<WEST> (Bitboard b) { return (b & ~FILEA_BB) >> 1; }
template<> inline Bitboard shift<NE>   (Bitboard b) { return (b & ~FILEH_BB) << 9; }
template<> inline Bitboard shift<NW>   (Bitboard b) { return (b & ~FILEA_BB) << 7; }
template<> inline Bitboard shift<SE>   (Bitboard b) { return (b & ~FILEH_BB) >> 7; }
template<> inline Bitboard shift<SW>   (Bitboard b) { return (b & ~FILEA_BB) >> 9; }

// ── Geometry helpers ──────────────────────────────────────────────────────────
inline Bitboard between(Square s1, Square s2) { return BETWEEN_BB[s1][s2]; }
inline Bitboard line   (Square s1, Square s2) { return LINE_BB[s1][s2]; }

// ── Slow slider (occupancy-aware ray walk) – used only during init ────────────
Bitboard sliding_attacks(PieceType pt, Square s, Bitboard occ);

} // namespace BB
