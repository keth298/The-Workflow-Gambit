#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# RAGEngine fast setup — completes in < 30 minutes on a modern laptop.
#
# What it does:
#   1. Install Python dependencies
#   2. Download openings (niklasf/chess-openings, ~200 KB, GitHub)
#      Download puzzles  (Lichess public DB, first 100k rows, ~30 MB)
#      Games stream live from Hugging Face during step 3 (no pre-download)
#   3. Ingest 25k games + 75k puzzles + all openings into SQLite  (~5-10 min)
#   4. Build FAISS index over ~150k positions  (~2-3 min)
#   5. Train value+policy network for 3 epochs on 150k rows  (~5-10 min)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

T0=$(date +%s)
echo "========================================================"
echo " RAGEngine fast setup  (target: < 30 min)"
echo "========================================================"

echo ""
echo "[1/5] Installing Python dependencies..."
pip3 install -q python-chess numpy torch faiss-cpu tqdm datasets requests zstandard

echo ""
echo "[2/5] Downloading datasets..."
python3 rag_engine/download_datasets.py --puzzles 100000

echo ""
echo "[3/5] Running data pipeline (fast mode)..."
python3 rag_engine/data_pipeline.py --fast

echo ""
echo "[4/5] Building FAISS index..."
python3 rag_engine/build_index.py --nlist 256

echo ""
echo "[5/5] Training value + policy network (fast mode)..."
python3 rag_engine/train.py --fast

T1=$(date +%s)
ELAPSED=$(( T1 - T0 ))
echo ""
echo "========================================================"
printf " Done in %d min %02d s\n" $(( ELAPSED / 60 )) $(( ELAPSED % 60 ))
echo " Start the engine:  python3 rag_engine/engine.py"
echo "========================================================"
