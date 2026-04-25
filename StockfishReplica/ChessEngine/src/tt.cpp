#include "tt.h"
#include <cstdlib>
#include <cstring>
#include <algorithm>

TranspositionTable TT;

TranspositionTable::TranspositionTable() { resize(64); }
TranspositionTable::~TranspositionTable() { free(table_); }

void TranspositionTable::resize(size_t mb) {
    size_t bytes = mb * 1024 * 1024;
    cluster_count_ = bytes / sizeof(TTCluster);
    free(table_);
    table_ = static_cast<TTCluster*>(malloc(cluster_count_ * sizeof(TTCluster)));
    clear();
}

void TranspositionTable::clear() {
    memset(table_, 0, cluster_count_ * sizeof(TTCluster));
    generation_ = 0;
}

void TranspositionTable::new_search() {
    generation_ = (generation_ + 1) & 63;
}

TTEntry *TranspositionTable::probe(u64 hash, bool &hit) {
    TTCluster &cluster = table_[hash % cluster_count_];
    // Prefer exact match, else return the best replacement candidate
    TTEntry *replace = &cluster.entries[0];
    for (int i = 0; i < 4; ++i) {
        TTEntry &e = cluster.entries[i];
        if (e.key32 == u32(hash)) {
            hit = true;
            return &e;
        }
        // Replacement: prefer lowest depth, older entries
        if ((replace->gen() == generation_ ? replace->depth : 0)
            > (e.gen() == generation_ ? e.depth : 0))
            replace = &e;
    }
    hit = false;
    return replace;
}

void TranspositionTable::save(u64 hash, Score score, Score static_eval,
                               Move best, Depth depth, TTFlag flag, int ply)
{
    bool hit;
    TTEntry *e = probe(hash, hit);

    // Don't overwrite a deeper exact entry with a shallower one from same gen
    if (hit && flag != TT_EXACT && e->depth > depth + 2) return;

    e->key32       = u32(hash);
    e->score       = i16(score_to_tt(score, ply));
    e->static_eval = i16(static_eval);
    e->best_move   = best;
    e->depth       = u8(std::clamp(depth, 0, 255));
    e->flags       = u8(flag | (generation_ << 2));
}

Score TranspositionTable::score_to_tt(Score s, int ply) {
    if (s >= SCORE_MATE - 512) return s + ply;
    if (s <= -SCORE_MATE + 512) return s - ply;
    return s;
}

Score TranspositionTable::score_from_tt(Score s, int ply) {
    if (s >= SCORE_MATE - 512) return s - ply;
    if (s <= -SCORE_MATE + 512) return s + ply;
    return s;
}
