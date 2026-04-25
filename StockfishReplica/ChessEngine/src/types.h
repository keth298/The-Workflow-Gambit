#pragma once
#include <cstdint>
#include <cassert>
#include <string>

// ── Fundamental integer types ─────────────────────────────────────────────────
using u8  = uint8_t;
using u16 = uint16_t;
using u32 = uint32_t;
using u64 = uint64_t;
using i8  = int8_t;
using i16 = int16_t;
using i32 = int32_t;
using i64 = int64_t;

using Bitboard = u64;
using Square   = int;
using Score    = int;
using Depth    = int;

// ── Board squares ─────────────────────────────────────────────────────────────
enum Squares : Square {
    A1,B1,C1,D1,E1,F1,G1,H1,
    A2,B2,C2,D2,E2,F2,G2,H2,
    A3,B3,C3,D3,E3,F3,G3,H3,
    A4,B4,C4,D4,E4,F4,G4,H4,
    A5,B5,C5,D5,E5,F5,G5,H5,
    A6,B6,C6,D6,E6,F6,G6,H6,
    A7,B7,C7,D7,E7,F7,G7,H7,
    A8,B8,C8,D8,E8,F8,G8,H8,
    NO_SQ = 64
};

// ── Colors ────────────────────────────────────────────────────────────────────
enum Color : int { WHITE = 0, BLACK = 1, NO_COLOR = 2 };
inline Color operator~(Color c) { return Color(c ^ 1); }

// ── Piece types ───────────────────────────────────────────────────────────────
enum PieceType : int {
    PAWN=0, KNIGHT, BISHOP, ROOK, QUEEN, KING, NO_PIECE_TYPE=6
};

// ── Pieces (color × type) ─────────────────────────────────────────────────────
enum Piece : int {
    W_PAWN=0, W_KNIGHT, W_BISHOP, W_ROOK, W_QUEEN, W_KING,
    B_PAWN=6, B_KNIGHT, B_BISHOP, B_ROOK, B_QUEEN, B_KING,
    NO_PIECE=12
};

inline Piece make_piece(Color c, PieceType pt) {
    return Piece(c * 6 + pt);
}
inline PieceType type_of(Piece p) { return PieceType(p % 6); }
inline Color     color_of(Piece p) { return Color(p / 6); }

// ── Move encoding (32-bit) ────────────────────────────────────────────────────
// bits  0- 5  from square
// bits  6-11  to square
// bits 12-13  move type (0=normal,1=castle,2=ep,3=promo)
// bits 14-15  promo piece type (0=knight,1=bishop,2=rook,3=queen)
using Move = u32;
const Move NO_MOVE   = 0;
const Move NULL_MOVE = 0xFFFFFFFF;

enum MoveType : int { MT_NORMAL=0, MT_CASTLE=1, MT_EP=2, MT_PROMO=3 };

inline Move make_move(Square from, Square to) {
    return Move(from | (to << 6));
}
inline Move make_castle(Square from, Square to) {
    return Move(from | (to << 6) | (MT_CASTLE << 12));
}
inline Move make_ep(Square from, Square to) {
    return Move(from | (to << 6) | (MT_EP << 12));
}
inline Move make_promo(Square from, Square to, PieceType promo) {
    int pp = promo - KNIGHT; // 0=knight..3=queen
    return Move(from | (to << 6) | (MT_PROMO << 12) | (pp << 14));
}

inline Square   from_sq(Move m)   { return Square(m & 0x3F); }
inline Square   to_sq(Move m)     { return Square((m >> 6) & 0x3F); }
inline MoveType move_type(Move m) { return MoveType((m >> 12) & 3); }
inline PieceType promo_type(Move m){ return PieceType(((m >> 14) & 3) + KNIGHT); }

// ── Castling rights flags ─────────────────────────────────────────────────────
enum CastlingRights : int {
    NO_CASTLE = 0,
    W_OO  = 1,   // white kingside
    W_OOO = 2,   // white queenside
    B_OO  = 4,   // black kingside
    B_OOO = 8,   // black queenside
    ALL_CASTLE = 15
};

// ── Score constants ───────────────────────────────────────────────────────────
constexpr Score SCORE_ZERO    =  0;
constexpr Score SCORE_INF     =  32000;
constexpr Score SCORE_MATE    =  31000;
constexpr Score SCORE_MATED   = -31000;
constexpr Score SCORE_DRAW    =  0;
constexpr Score SCORE_TB_WIN  =  30000;

inline bool is_mate_score(Score s) { return std::abs(s) >= SCORE_MATE - 512; }
inline Score mate_in(int ply)   { return  SCORE_MATE - ply; }
inline Score mated_in(int ply)  { return -SCORE_MATE + ply; }

// ── Piece values (centipawns) ─────────────────────────────────────────────────
constexpr Score PIECE_VALUE[7] = { 100, 320, 330, 500, 950, 0, 0 };

// ── Directions ────────────────────────────────────────────────────────────────
enum Direction : int {
    NORTH =  8, SOUTH = -8,
    EAST  =  1, WEST  = -1,
    NE    =  9, NW    =  7,
    SE    = -7, SW    = -9
};

// ── File / rank helpers ───────────────────────────────────────────────────────
inline int  file_of(Square s)  { return s & 7; }
inline int  rank_of(Square s)  { return s >> 3; }
inline Square make_sq(int f, int r) { return Square(r * 8 + f); }
inline Square flip_rank(Square s)   { return Square(s ^ 56); }

inline std::string sq_name(Square s) {
    if (s == NO_SQ) return "-";
    std::string n;
    n += char('a' + file_of(s));
    n += char('1' + rank_of(s));
    return n;
}

// ── Bitboard square bit ───────────────────────────────────────────────────────
inline Bitboard sq_bb(Square s) { return Bitboard(1) << s; }

// ── Rank / file masks ─────────────────────────────────────────────────────────
constexpr Bitboard RANK1_BB = 0x00000000000000FFull;
constexpr Bitboard RANK2_BB = 0x000000000000FF00ull;
constexpr Bitboard RANK7_BB = 0x00FF000000000000ull;
constexpr Bitboard RANK8_BB = 0xFF00000000000000ull;
constexpr Bitboard FILEA_BB = 0x0101010101010101ull;
constexpr Bitboard FILEH_BB = 0x8080808080808080ull;
constexpr Bitboard ALL_BB   = 0xFFFFFFFFFFFFFFFFull;

inline Bitboard rank_bb(int r) { return RANK1_BB << (r * 8); }
inline Bitboard file_bb(int f) { return FILEA_BB << f; }

// ── Population count / LSB / MSB ─────────────────────────────────────────────
inline int popcount(Bitboard b) {
    return __builtin_popcountll(b);
}
inline int lsb(Bitboard b) {
    assert(b);
    return __builtin_ctzll(b);
}
inline int msb(Bitboard b) {
    assert(b);
    return 63 - __builtin_clzll(b);
}
inline Square pop_lsb(Bitboard &b) {
    Square s = Square(lsb(b));
    b &= b - 1;
    return s;
}
inline bool more_than_one(Bitboard b) { return b & (b - 1); }
