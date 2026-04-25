#pragma once
#include "types.h"
#include "position.h"

// ── Move list ─────────────────────────────────────────────────────────────────
struct MoveList {
    static constexpr int MAX_MOVES = 256;
    Move  moves[MAX_MOVES];
    int   count = 0;

    void push(Move m)              { moves[count++] = m; }
    Move *begin()                  { return moves; }
    Move *end()                    { return moves + count; }
    const Move *begin()      const { return moves; }
    const Move *end()        const { return moves + count; }
    int   size()             const { return count; }
    Move  operator[](int i)  const { return moves[i]; }
};

// ── Generation modes ─────────────────────────────────────────────────────────
enum GenMode {
    GEN_ALL,       // all pseudo-legal moves
    GEN_CAPTURES,  // captures + promotions only (for quiescence)
    GEN_QUIET,     // non-captures
    GEN_EVASIONS,  // when in check: all moves that may resolve check
};

// ── Top-level generators ─────────────────────────────────────────────────────
void generate_moves(const Position &pos, MoveList &ml, GenMode mode = GEN_ALL);

// Legal move wrapper: filters pseudo-legals
struct LegalMoveList {
    MoveList list;
    LegalMoveList(const Position &pos, GenMode mode = GEN_ALL);
};
