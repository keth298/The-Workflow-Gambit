#!/usr/bin/env bash
# Download all datasets required by the RAG chess engine.
# Requires: git, kaggle CLI (pip install kaggle), and a ~/.kaggle/kaggle.json API token.

set -euo pipefail
cd "$(dirname "$0")"

echo "=== RAG Chess Engine — Dataset Setup ==="

# ─── 1. Chess Games ──────────────────────────────────────────────────────────
if [ -d "chess_games/.git" ]; then
    echo "[1/3] chess_games already cloned — pulling latest..."
    git -C chess_games pull --ff-only
else
    echo "[1/3] Cloning angeluriot/Chess_games..."
    git clone https://github.com/angeluriot/Chess_games chess_games
fi

# ─── 2. Openings ─────────────────────────────────────────────────────────────
if ls openings/*.csv 2>/dev/null | head -1 | grep -q .; then
    echo "[2/3] Opening CSV already present — skipping."
else
    echo "[2/3] Downloading all-chess-openings from Kaggle..."
    mkdir -p openings
    kaggle datasets download -d alexandrelemercier/all-chess-openings \
        -p openings --unzip
fi

# ─── 3. Puzzles ──────────────────────────────────────────────────────────────
if ls puzzles/*.csv 2>/dev/null | head -1 | grep -q .; then
    echo "[3/3] Puzzle CSV already present — skipping."
else
    echo "[3/3] Downloading lichess-chess-puzzle-dataset from Kaggle..."
    mkdir -p puzzles
    kaggle datasets download -d tianmin/lichess-chess-puzzle-dataset \
        -p puzzles --unzip
fi

echo ""
echo "=== Downloads complete. ==="
echo "Next steps:"
echo "  cd .. && python rag_engine/data_pipeline.py   # build SQLite DB (~20-60 min)"
echo "  python rag_engine/build_index.py              # build FAISS index (~5-15 min)"
echo "  python rag_engine/train.py                    # train value+policy networks"
echo "  python rag_engine/engine.py                   # start UCI engine"
