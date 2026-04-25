"""
Build a FAISS approximate-nearest-neighbour index over all positions in the
SQLite database.

Produces
--------
LargeDataset/faiss.index   — FAISS IndexIVFFlat (inner-product, cosine sim)
LargeDataset/id_to_fen.pkl — list mapping FAISS int-id → FEN string

Run:
    python build_index.py [--nlist 1024] [--batch 50000]
"""

from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import faiss
import numpy as np
import sqlite3
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from encoder import encode_board_normalized, FEATURE_DIM

ROOT        = Path(__file__).parent.parent
DATASET_DIR = ROOT / "LargeDataset"
DB_PATH     = DATASET_DIR / "chess_data.db"
INDEX_PATH  = DATASET_DIR / "faiss.index"
ID_MAP_PATH = DATASET_DIR / "id_to_fen.pkl"


def build_index(nlist: int, batch_size: int) -> None:
    if not DB_PATH.exists():
        sys.exit(f"[ERROR] Database not found at {DB_PATH}. Run data_pipeline.py first.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(DISTINCT fen) FROM positions").fetchone()[0]
    print(f"Distinct FENs to index: {total:,}", file=sys.stderr)

    # ── Collect unique FENs ──────────────────────────────────────────────────
    print("Loading FENs...", file=sys.stderr)
    rows = conn.execute("SELECT DISTINCT fen FROM positions").fetchall()
    fens = [r[0] for r in rows]
    n    = len(fens)

    # ── Encode in batches ────────────────────────────────────────────────────
    import chess
    print("Encoding positions...", file=sys.stderr)
    vecs = np.zeros((n, FEATURE_DIM), dtype=np.float32)
    for i, fen in enumerate(tqdm(fens, unit=" pos")):
        try:
            board = chess.Board(fen)
            vecs[i] = encode_board_normalized(board)
        except Exception:
            pass   # leave as zeros — won't be a meaningful neighbour

    # ── Build FAISS IVF index ────────────────────────────────────────────────
    # nlist = number of Voronoi cells; rule of thumb: sqrt(N)..4*sqrt(N)
    nlist = min(nlist, max(1, n // 40))
    print(f"Building IndexIVFFlat  (d={FEATURE_DIM}, nlist={nlist})...", file=sys.stderr)
    quantizer = faiss.IndexFlatIP(FEATURE_DIM)
    index     = faiss.IndexIVFFlat(quantizer, FEATURE_DIM, nlist, faiss.METRIC_INNER_PRODUCT)

    # Train on a random subsample (≤ 500 k) to set Voronoi centroids
    train_n = min(n, 500_000)
    idx     = np.random.choice(n, train_n, replace=False)
    print(f"Training on {train_n:,} samples...", file=sys.stderr)
    index.train(vecs[idx])

    # Add all vectors in batches
    print("Adding vectors...", file=sys.stderr)
    for start in tqdm(range(0, n, batch_size), unit=" batch"):
        end = min(start + batch_size, n)
        index.add_with_ids(vecs[start:end], np.arange(start, end, dtype=np.int64))

    index.nprobe = min(32, nlist)   # search 32 cells at query time

    # ── Persist ──────────────────────────────────────────────────────────────
    faiss.write_index(index, str(INDEX_PATH))
    with open(ID_MAP_PATH, "wb") as fh:
        pickle.dump(fens, fh, protocol=4)

    conn.close()
    print(f"[Done] Index saved to {INDEX_PATH}  ({n:,} vectors).", file=sys.stderr)
    print(f"       ID map saved to {ID_MAP_PATH}.", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nlist",  type=int, default=1024,
                    help="Number of IVF cells (default 1024)")
    ap.add_argument("--batch",  type=int, default=50_000,
                    help="Encoding batch size (default 50 000)")
    args = ap.parse_args()
    build_index(args.nlist, args.batch)


if __name__ == "__main__":
    main()
