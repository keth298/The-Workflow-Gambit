# tt.py — Transposition table with Zobrist hashing

# ── Entry flags ───────────────────────────────────────────────────────────────
EXACT      = 0   # score is exact
LOWERBOUND = 1   # score >= beta (failed high — a cut node)
UPPERBOUND = 2   # score <= alpha (failed low — all moves were bad)

# ── Table ─────────────────────────────────────────────────────────────────────
_SIZE = 1 << 20          # 1M slots (~50 MB)
_MASK = _SIZE - 1

# Each slot: [hash, depth, score, flag, best_move] or None
_table = [None] * _SIZE

def clear():
    global _table
    _table = [None] * _SIZE

def probe(h, depth, alpha, beta):
    """
    Look up position hash `h`.
    Returns (score, best_move) if we can use the stored result, else (None, None).
    best_move is always returned when available, even if score is unusable.
    """
    entry = _table[h & _MASK]
    if entry is None or entry[0] != h:
        return None, None

    stored_hash, stored_depth, score, flag, best_move = entry

    if stored_depth >= depth:
        if flag == EXACT:
            return score, best_move
        if flag == LOWERBOUND and score >= beta:
            return beta, best_move
        if flag == UPPERBOUND and score <= alpha:
            return alpha, best_move

    # Depth insufficient for a score cutoff, but still return the best move
    # for move ordering (hash move ordering)
    return None, best_move

def store(h, depth, score, flag, best_move):
    """Store an entry. Replace-by-depth: overwrite only if new entry is deeper."""
    idx   = h & _MASK
    entry = _table[idx]
    if entry is None or entry[0] != h or depth >= entry[1]:
        _table[idx] = (h, depth, score, flag, best_move)
