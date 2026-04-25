EXACT = 0
LOWER = 1
UPPER = 2


class TranspositionTable:
    def __init__(self):
        self._table = {}

    def probe(self, key):
        return self._table.get(key)

    def store(self, key, depth, flag, score, best_move):
        self._table[key] = (depth, flag, score, best_move)

    def clear(self):
        self._table.clear()
