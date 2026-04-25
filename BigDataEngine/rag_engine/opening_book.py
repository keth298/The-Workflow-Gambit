"""
Opening book — fast O(1) lookup using FEN-based hashing.

The book is built from move_stats rows whose source is 'opening' (or any source
with high frequency). It maps each FEN to a weighted-random or best move.

Usage
-----
    from opening_book import OpeningBook
    book = OpeningBook()          # loads from DB once, then caches in memory
    move_uci = book.lookup(board) # returns str or None
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import chess

ROOT    = Path(__file__).parent.parent
DB_PATH = ROOT / "LargeDataset" / "chess_data.db"


class OpeningBook:
    """In-memory opening book built from move_stats."""

    def __init__(self, min_count: int = 3) -> None:
        # book[fen] = list of (move_uci, score)
        self._book: dict[str, list[tuple[str, float]]] = {}
        self._loaded = False
        self._min_count = min_count

    def _load(self) -> None:
        if not DB_PATH.exists():
            self._loaded = True
            return

        conn = sqlite3.connect(DB_PATH)
        # Pull rows with at least min_count occurrences
        rows = conn.execute(
            """SELECT fen, move, count, total_outcome
               FROM move_stats
               WHERE count >= ?""",
            (self._min_count,),
        ).fetchall()
        conn.close()

        for fen, move, count, total in rows:
            # Score = count × (normalised outcome in [0,1])
            avg = total / count if count > 0 else 0.0
            score = count * (avg + 1.0) / 2.0   # remap [-1,1] → [0,1], weight by count
            self._book.setdefault(fen, []).append((move, score))

        # Pre-sort each entry by score descending
        for fen in self._book:
            self._book[fen].sort(key=lambda t: t[1], reverse=True)

        self._loaded = True
        print(f"[OpeningBook] Loaded {len(self._book):,} positions.", file=sys.stderr)

    # ── Public API ────────────────────────────────────────────────────────────

    def lookup(self, board: chess.Board) -> str | None:
        """Return the best UCI move for *board*, or None if not in book."""
        if not self._loaded:
            self._load()

        fen = board.fen()
        entries = self._book.get(fen)
        if not entries:
            return None

        # Return the highest-scoring legal move
        legal = {m.uci() for m in board.legal_moves}
        for move_uci, _ in entries:
            if move_uci in legal:
                return move_uci

        return None

    def __contains__(self, board: chess.Board) -> bool:
        if not self._loaded:
            self._load()
        return board.fen() in self._book
