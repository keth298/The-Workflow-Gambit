#pragma once
#include "types.h"
#include "position.h"
#include "movegen.h"
#include <atomic>
#include <chrono>

// ── Search limits ─────────────────────────────────────────────────────────────
struct SearchLimits {
    int  depth        = 64;    // max depth
    int  movetime     = 0;     // fixed ms per move (0 = use time management)
    int  wtime        = 0;
    int  btime        = 0;
    int  winc         = 0;
    int  binc         = 0;
    int  movestogo    = 0;
    bool infinite     = false;
    bool ponder       = false;
};

// ── Search info per thread ────────────────────────────────────────────────────
struct SearchInfo {
    long long nodes     = 0;
    int       seldepth  = 0;
    bool      stopped   = false;
};

// ── Move ordering tables ──────────────────────────────────────────────────────
constexpr int MAX_PLY = 128;
constexpr int KILLER_SLOTS = 2;

struct MoveOrderTables {
    Move  killers[MAX_PLY][KILLER_SLOTS];
    int   history[2][64][64];    // [color][from][to]
    Move  counter_move[2][64][64]; // [color][from][to] → counter

    void clear() {
        for (auto &row : killers) for (auto &k : row) k = NO_MOVE;
        for (auto &c : history)  for (auto &f : c) for (auto &v : f) v = 0;
        for (auto &c : counter_move) for (auto &f : c) for (auto &v : f) v = NO_MOVE;
    }
    void update_killers(Move m, int ply) {
        if (killers[ply][0] != m) {
            killers[ply][1] = killers[ply][0];
            killers[ply][0] = m;
        }
    }
    void update_history(Color c, Move m, int bonus) {
        int &h = history[c][from_sq(m)][to_sq(m)];
        h += bonus - h * std::abs(bonus) / 16384;
    }
};

// ── Main search class ─────────────────────────────────────────────────────────
class Searcher {
public:
    Searcher() { tables_.clear(); }

    // Called by UCI to start a search
    void search(Position &pos, const SearchLimits &limits);

    // Signal stop
    void stop() { stop_.store(true); }
    void reset() { stop_.store(false); tables_.clear(); }

private:
    MoveOrderTables tables_;
    SearchInfo      info_;
    SearchLimits    limits_;
    std::chrono::steady_clock::time_point start_time_;
    std::atomic<bool> stop_{false};
    Move  root_best_move_ = NO_MOVE;

    long long time_limit_ms_ = 0;

    // Time management
    long long elapsed_ms() const;
    bool should_stop() const;
    long long alloc_time(Color stm) const;

    // Core search
    Score alpha_beta(Position &pos, Score alpha, Score beta, Depth depth,
                     int ply, bool is_pv, bool cut_node, Move prev_move);

    Score quiescence(Position &pos, Score alpha, Score beta, int ply);

    // (move ordering integrated into alpha_beta)

    void extract_pv(Position &pos, Move best, int depth, std::string &pv_str);
};

extern Searcher ENGINE;
