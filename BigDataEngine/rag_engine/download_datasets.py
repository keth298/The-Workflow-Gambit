"""
Download all datasets required by the RAG chess engine.

Sources
-------
  Chess games : Hugging Face — angeluriot/chess_games  (streamed during pipeline)
  Openings    : Kaggle — alexandrelemercier/all-chess-openings  (requires kaggle.json)
  Puzzles     : Lichess public database  (streamed + saved subset, no account needed)

Run:
    python download_datasets.py [--puzzles 100000]
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import requests
import zstandard as zstd

DATASET_DIR = Path(__file__).parent.parent / "LargeDataset"


# ── Opening database (Kaggle: alexandrelemercier/all-chess-openings) ──────────

def download_openings() -> None:
    """Download via Kaggle CLI: alexandrelemercier/all-chess-openings."""
    op_dir = DATASET_DIR / "openings"
    op_dir.mkdir(parents=True, exist_ok=True)

    existing = list(op_dir.glob("*.csv")) + list(op_dir.glob("*.tsv"))
    if existing:
        print(f"  Opening files already present ({len(existing)} file(s)) — skipping.")
        print("[Openings] Done.")
        return

    try:
        import kaggle  # noqa: F401 — triggers auth check
        from kaggle.api.kaggle_api_extended import KaggleApiExtended
        api = KaggleApiExtended()
        api.authenticate()
    except Exception:
        print("[WARN] Kaggle not configured. To download openings:")
        print("  1. Create an account at kaggle.com")
        print("  2. Go to Account → Create New API Token → download kaggle.json")
        print("  3. Place it at ~/.kaggle/kaggle.json  (chmod 600)")
        print("  4. Re-run: python rag_engine/download_datasets.py")
        print("[WARN] Continuing without openings — engine still works.")
        return

    print("  Downloading alexandrelemercier/all-chess-openings from Kaggle...")
    try:
        api.dataset_download_files(
            "alexandrelemercier/all-chess-openings",
            path=str(op_dir),
            unzip=True,
            quiet=False,
        )
        print("[Openings] Done.")
    except Exception as e:
        print(f"[WARN] Kaggle download failed: {e}", file=sys.stderr)


# ── Puzzle database (Lichess public CSV, zstd-compressed) ─────────────────────

PUZZLE_URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"

def download_puzzles(limit: int) -> None:
    puz_dir = DATASET_DIR / "puzzles"
    puz_dir.mkdir(parents=True, exist_ok=True)
    out_path = puz_dir / "lichess_puzzles.csv"

    # Check if we already have enough rows
    if out_path.exists() and out_path.stat().st_size > 0:
        with open(out_path) as fh:
            existing = sum(1 for _ in fh) - 1   # minus header
        if existing >= limit:
            print(f"  {out_path.name} already has {existing:,} rows — skipping.")
            print("[Puzzles] Done.")
            return
        print(f"  Found {existing:,} rows, need {limit:,} — re-downloading.")

    print(f"  Streaming Lichess puzzle CSV (first {limit:,} rows) from lichess.org ...")
    print("  This may take 1-3 minutes depending on connection speed.")

    dctx     = zstd.ZstdDecompressor()
    written  = 0

    with requests.get(PUZZLE_URL, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with dctx.stream_reader(resp.raw) as raw_reader:
            text_reader = io.TextIOWrapper(raw_reader, encoding="utf-8")
            with open(out_path, "w", encoding="utf-8") as out_fh:
                for i, line in enumerate(text_reader):
                    out_fh.write(line)
                    if i > 0:
                        written += 1
                    if written >= limit:
                        break
                    if written % 10_000 == 0 and written > 0:
                        print(f"  ... {written:,} / {limit:,}", end="\r", flush=True)

    print(f"\n  Saved {out_path.name}  ({written:,} puzzle rows).")
    print("[Puzzles] Done.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzles", type=int, default=100_000,
                    help="Number of Lichess puzzle rows to download (default 100 000)")
    args = ap.parse_args()

    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    print("=== [1/2] Downloading opening database (niklasf/chess-openings) ===")
    try:
        download_openings()
    except Exception as e:
        print(f"[WARN] Opening download failed: {e}", file=sys.stderr)

    print(f"\n=== [2/2] Downloading puzzle database (Lichess, {args.puzzles:,} rows) ===")
    try:
        download_puzzles(args.puzzles)
    except Exception as e:
        print(f"[WARN] Puzzle download failed: {e}", file=sys.stderr)
        print("[WARN] Engine will still work without puzzles.", file=sys.stderr)

    print("\n=== Downloads complete ===")
    print("Chess games will be streamed from Hugging Face during data_pipeline.py")
    print("  (no separate download needed — requires internet access during pipeline)")


if __name__ == "__main__":
    main()
