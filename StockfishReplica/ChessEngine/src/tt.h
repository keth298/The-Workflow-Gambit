#pragma once
#include "types.h"

// ── Entry flags ───────────────────────────────────────────────────────────────
enum TTFlag : u8 { TT_NONE=0, TT_EXACT=1, TT_LOWER=2, TT_UPPER=3 };

// ── Transposition table entry (10 bytes + 2 pad = 12 bytes) ──────────────────
struct TTEntry {
    u32   key32;    // lower 32 bits of hash for verification
    i16   score;
    i16   static_eval;
    Move  best_move;
    u8    depth;
    u8    flags;    // TTFlag in bits 0-1, generation in bits 2-7
    u8    pad[2];

    bool  matches(u64 hash) const { return key32 == u32(hash); }
    TTFlag flag()  const { return TTFlag(flags & 3); }
    int    gen()   const { return flags >> 2; }
};

static_assert(sizeof(TTEntry) == 16, "TTEntry size check");

// ── Cluster: 4 entries per cache line ────────────────────────────────────────
struct TTCluster {
    TTEntry entries[4];
};

// ── Transposition table ───────────────────────────────────────────────────────
class TranspositionTable {
public:
    TranspositionTable();
    ~TranspositionTable();

    void  resize(size_t mb);
    void  clear();
    void  new_search();  // bump generation

    // Returns pointer to entry if hit, nullptr otherwise
    TTEntry *probe(u64 hash, bool &hit);

    // Save result
    void save(u64 hash, Score score, Score static_eval, Move best,
              Depth depth, TTFlag flag, int ply);

    // Adjust mate scores for storage (ply-independent)
    static Score score_to_tt  (Score s, int ply);
    static Score score_from_tt(Score s, int ply);

    size_t size() const { return cluster_count_; }
    int    generation() const { return generation_; }

private:
    TTCluster *table_      = nullptr;
    size_t     cluster_count_ = 0;
    int        generation_ = 0;
};

extern TranspositionTable TT;
