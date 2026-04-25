"""
FAISS-based position retrieval.

Given a board position, returns the K nearest positions from the training
corpus and aggregates per-move statistics into:
  - A position evaluation score  ∈ [-1, +1]
  - A move policy dict  {uci_str: prior_score}

Both are from the perspective of the side to move.

Usage
-----
    ret = RetrievalEngine()
    eval_score   = ret.evaluate(board)           # float in [-1, 1]
    move_priors  = ret.move_policy(board)        # {uci: float}, sum ≈ 1
    confidence   = ret.confidence(board)         # float in [0, 1]
"""

from __future__ import annotations

import os
import pickle
import sqlite3
import sys
from pathlib import Path
from typing import Optional

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import chess
import faiss
faiss.omp_set_num_threads(1)   # prevent OMP conflict with PyTorch on macOS
import numpy as np

ROOT        = Path(__file__).parent.parent
DATASET_DIR = ROOT / "LargeDataset"
INDEX_PATH  = DATASET_DIR / "faiss.index"
ID_MAP_PATH = DATASET_DIR / "id_to_fen.pkl"
DB_PATH     = DATASET_DIR / "chess_data.db"

sys.path.insert(0, str(Path(__file__).parent))
from encoder import encode_board_normalized, FEATURE_DIM


class RetrievalEngine:
    K = 20          # neighbours to fetch
    MIN_SIM = 0.85  # cosine similarity threshold to trust a neighbour

    def __init__(self) -> None:
        self._index: Optional[faiss.Index] = None
        self._id_to_fen: Optional[list[str]] = None
        self._conn: Optional[sqlite3.Connection] = None
        self._loaded = False
        self._cache: dict[str, tuple[float, dict[str, float], float]] = {}

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not INDEX_PATH.exists() or not ID_MAP_PATH.exists():
            print("[Retrieval] FAISS index not found — retrieval disabled.", file=sys.stderr)
            self._loaded = True
            return

        self._index = faiss.read_index(str(INDEX_PATH))
        with open(ID_MAP_PATH, "rb") as fh:
            self._id_to_fen = pickle.load(fh)

        # check_same_thread=False is safe here: we only do reads, never writes.
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._loaded = True
        print(f"[Retrieval] Index loaded  ({self._index.ntotal:,} vectors).", file=sys.stderr)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load()

    # ── Core retrieval ────────────────────────────────────────────────────────

    def _query(self, board: chess.Board) -> tuple[list[str], list[float]]:
        """Return (neighbour_fens, cosine_similarities) for *board*."""
        self._ensure_loaded()
        if self._index is None:
            return [], []

        vec = encode_board_normalized(board).reshape(1, -1)
        sims, ids = self._index.search(vec, self.K)
        sims, ids = sims[0], ids[0]

        fens: list[str] = []
        used_sims: list[float] = []
        for sim, idx in zip(sims, ids):
            if idx < 0:
                continue
            if sim < self.MIN_SIM:
                break
            fens.append(self._id_to_fen[idx])
            used_sims.append(float(sim))

        return fens, used_sims

    def _fetch_move_stats(self, fens: list[str]) -> dict[str, tuple[int, float]]:
        """Return {move: (count, total_outcome)} for all moves under *fens*."""
        if not fens or self._conn is None:
            return {}
        placeholders = ",".join("?" * len(fens))
        rows = self._conn.execute(
            f"SELECT move, SUM(count), SUM(total_outcome) "
            f"FROM move_stats WHERE fen IN ({placeholders}) "
            f"GROUP BY move",
            fens,
        ).fetchall()
        return {row[0]: (row[1], row[2]) for row in rows}

    def _fetch_position_outcomes(self, fens: list[str]) -> list[float]:
        """Return one averaged outcome per FEN, preserving the order of *fens*."""
        if not fens or self._conn is None:
            return []
        placeholders = ",".join("?" * len(fens))
        rows = self._conn.execute(
            f"SELECT fen, AVG(outcome) FROM positions "
            f"WHERE fen IN ({placeholders}) GROUP BY fen",
            fens,
        ).fetchall()
        outcome_map = {r[0]: float(r[1]) for r in rows}
        return [outcome_map.get(f, 0.0) for f in fens]

    # ── Public API ────────────────────────────────────────────────────────────

    def query_all(self, board: chess.Board) -> tuple[float, dict[str, float], float]:
        """
        Return (eval_score, move_policy, confidence) for *board*.
          eval_score ∈ [-1, +1], from side-to-move perspective
          move_policy: {uci: prior}, values sum to ~1
          confidence  ∈ [0, 1]
        """
        fen = board.fen()
        if fen in self._cache:
            return self._cache[fen]

        neighbour_fens, sims = self._query(board)
        n_useful = len(neighbour_fens)
        confidence = min(1.0, n_useful / self.K)

        if n_useful == 0:
            result = (0.0, {}, 0.0)
            self._cache[fen] = result
            return result

        # ── Position evaluation ───────────────────────────────────────────────
        outcomes   = self._fetch_position_outcomes(neighbour_fens)
        weights    = sims[:len(outcomes)]
        if outcomes and sum(weights) > 0:
            eval_score = float(np.average(outcomes, weights=weights))
        else:
            eval_score = 0.0

        # Flip to side-to-move perspective
        if board.turn == chess.BLACK:
            eval_score = -eval_score

        # ── Move policy ───────────────────────────────────────────────────────
        move_stats = self._fetch_move_stats(neighbour_fens)
        legal_ucis = {m.uci() for m in board.legal_moves}

        raw: dict[str, float] = {}
        for move_uci, (count, total) in move_stats.items():
            if move_uci not in legal_ucis:
                continue
            avg_outcome = total / count if count > 0 else 0.0
            # Score = frequency × outcome quality
            raw[move_uci] = count * (avg_outcome + 1.0) / 2.0  # [0, ∞)

        # Softmax-style normalisation
        if raw:
            total_raw = sum(raw.values())
            policy = {m: v / total_raw for m, v in raw.items()}
        else:
            policy = {}

        result = (eval_score, policy, confidence)
        self._cache[fen] = result
        return result

    def evaluate(self, board: chess.Board) -> float:
        score, _, _ = self.query_all(board)
        return score

    def move_policy(self, board: chess.Board) -> dict[str, float]:
        _, policy, _ = self.query_all(board)
        return policy

    def confidence(self, board: chess.Board) -> float:
        _, _, conf = self.query_all(board)
        return conf
