TT_EXACT = 0
TT_LOWER = 1
TT_UPPER = 2


class TranspositionTable:
    def __init__(self, max_size: int = 1 << 20):
        self._table: dict = {}
        self._max_size = max_size

    def store(self, key: int, depth: int, score: int, flag: int, move) -> None:
        if len(self._table) >= self._max_size:
            # Evict ~25% of entries instead of clearing everything
            keys_to_remove = list(self._table.keys())[:self._max_size // 4]
            for k in keys_to_remove:
                del self._table[k]
        existing = self._table.get(key)
        if existing is None or existing["depth"] <= depth:
            self._table[key] = {"depth": depth, "score": score, "flag": flag, "move": move}

    def get_entry(self, key: int):
        """Return the raw TT entry (or None) without depth/bound filtering."""
        return self._table.get(key)

    def lookup(self, key: int, depth: int, alpha: int, beta: int):
        """Lookup with depth and bound filtering. Returns (score, move) or None."""
        entry = self._table.get(key)
        if entry is None or entry["depth"] < depth:
            return None
        score = entry["score"]
        flag = entry["flag"]
        move = entry["move"]
        if flag == TT_EXACT:
            return score, move
        if flag == TT_LOWER and score >= beta:
            return score, move
        if flag == TT_UPPER and score <= alpha:
            return score, move
        return None

    def clear(self) -> None:
        self._table.clear()
