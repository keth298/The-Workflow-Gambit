#pragma once
#include "types.h"
#include "position.h"

// ── Game phase ────────────────────────────────────────────────────────────────
// Used to interpolate between middlegame and endgame scores (tapered eval)
constexpr int PHASE_MG = 128;
constexpr int PHASE_EG = 0;

// Phase material contributions
constexpr int PHASE_WEIGHT[6] = { 0, 1, 1, 2, 4, 0 };

// ── Main evaluation entry point ───────────────────────────────────────────────
// Returns score from side-to-move's perspective
Score evaluate(const Position &pos);

// ── Lazy evaluation bound ─────────────────────────────────────────────────────
// If material difference is more than this, skip detailed evaluation
constexpr Score LAZY_MARGIN = 500;
