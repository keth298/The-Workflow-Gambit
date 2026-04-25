#pragma once
#include "types.h"

namespace Zobrist {

extern u64 PIECE_SQ[12][64];   // [piece][square]
extern u64 SIDE_TO_MOVE;       // XOR when it's black's turn
extern u64 CASTLING[16];       // castling rights nibble
extern u64 EP_FILE[8];         // en-passant file

void init();

} // namespace Zobrist
