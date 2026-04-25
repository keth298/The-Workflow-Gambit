#include "zobrist.h"
#include <random>

namespace Zobrist {

u64 PIECE_SQ[12][64];
u64 SIDE_TO_MOVE;
u64 CASTLING[16];
u64 EP_FILE[8];

void init() {
    // Deterministic PRNG seeded to a fixed value for reproducibility
    std::mt19937_64 rng(0xDEADBEEFCAFEBABEULL);
    auto next = [&]() -> u64 { return rng(); };

    for (int p = 0; p < 12; ++p)
        for (int s = 0; s < 64; ++s)
            PIECE_SQ[p][s] = next();

    SIDE_TO_MOVE = next();

    for (int c = 0; c < 16; ++c)
        CASTLING[c] = next();

    for (int f = 0; f < 8; ++f)
        EP_FILE[f] = next();
}

} // namespace Zobrist
