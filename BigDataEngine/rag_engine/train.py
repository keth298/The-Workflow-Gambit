"""
Train the ChessNet value + policy networks on the SQLite database.

Loss
----
  value_loss  = MSE( pred_value, outcome )
  policy_loss = CrossEntropy( pred_policy, best_move_idx )
  total_loss  = value_loss + policy_loss

Run:
    python train.py [--epochs 5] [--batch 256] [--lr 1e-3] [--limit 2000000]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import chess
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

ROOT       = Path(__file__).parent.parent
DB_PATH    = ROOT / "LargeDataset" / "chess_data.db"
MODEL_PATH = ROOT / "LargeDataset" / "model.pt"

sys.path.insert(0, str(Path(__file__).parent))
from encoder import encode_board, FEATURE_DIM, POLICY_DIM, move_to_idx
from evaluator import ChessNet


# ── Dataset ───────────────────────────────────────────────────────────────────

class ChessDataset(Dataset):
    """Loads (features, outcome, move_idx) triples from SQLite."""

    def __init__(self, rows: list[tuple]) -> None:
        # rows: (fen, outcome, move_uci)
        self._data: list[tuple[np.ndarray, float, int]] = []

        for fen, outcome, move_uci in tqdm(rows, desc="Encoding", unit=" pos", leave=False):
            try:
                board = chess.Board(fen)
                feat  = encode_board(board)
                m     = chess.Move.from_uci(move_uci)
                idx   = move_to_idx(m)
                self._data.append((feat, float(outcome), idx))
            except Exception:
                continue

    def __len__(self) -> int:
        return len(self._data)

    def __getitem__(self, i: int):
        feat, outcome, idx = self._data[i]
        return (
            torch.tensor(feat, dtype=torch.float32),
            torch.tensor(outcome, dtype=torch.float32),
            torch.tensor(idx, dtype=torch.long),
        )


# ── Training loop ─────────────────────────────────────────────────────────────

def train(epochs: int, batch_size: int, lr: float, limit: int) -> None:
    if not DB_PATH.exists():
        sys.exit(f"[ERROR] {DB_PATH} not found. Run data_pipeline.py first.")

    conn = sqlite3.connect(DB_PATH)
    print("Loading training rows...", file=sys.stderr)
    rows = conn.execute(
        """SELECT p.fen, p.outcome, ms.move
           FROM positions p
           JOIN move_stats ms ON p.fen = ms.fen
           WHERE ms.count >= 2
           ORDER BY RANDOM()
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()

    print(f"Loaded {len(rows):,} (fen, outcome, move) rows.", file=sys.stderr)

    dataset = ChessDataset(rows)
    loader  = DataLoader(dataset, batch_size=batch_size, shuffle=True,
                         num_workers=0, pin_memory=False)

    net    = ChessNet()
    optmzr = optim.Adam(net.parameters(), lr=lr)
    sched  = optim.lr_scheduler.CosineAnnealingLR(optmzr, T_max=epochs)

    mse_fn = nn.MSELoss()
    ce_fn  = nn.CrossEntropyLoss()

    for epoch in range(1, epochs + 1):
        net.train()
        total_loss = val_loss_sum = pol_loss_sum = 0.0
        n_batches = 0

        pbar = tqdm(loader, desc=f"Epoch {epoch}/{epochs}", unit=" batch")
        for feat, outcomes, move_idxs in pbar:
            values, policy_logits = net(feat)

            val_loss = mse_fn(values, outcomes)
            pol_loss = ce_fn(policy_logits, move_idxs)
            loss     = val_loss + pol_loss

            optmzr.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            optmzr.step()

            total_loss    += loss.item()
            val_loss_sum  += val_loss.item()
            pol_loss_sum  += pol_loss.item()
            n_batches     += 1
            pbar.set_postfix(
                loss=f"{total_loss/n_batches:.4f}",
                val=f"{val_loss_sum/n_batches:.4f}",
                pol=f"{pol_loss_sum/n_batches:.4f}",
            )

        sched.step()
        print(f"  Epoch {epoch}: avg_loss={total_loss/max(n_batches,1):.4f}", file=sys.stderr)

    torch.save(net.state_dict(), MODEL_PATH)
    print(f"[Train] Model saved to {MODEL_PATH}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description="Train the RAG chess value+policy network.")
    ap.add_argument("--fast",   action="store_true",
                    help="Fast mode: 3 epochs, 150k rows, batch 512 (~5-10 min)")
    ap.add_argument("--epochs", type=int, default=0,
                    help="Training epochs (0 = use mode default)")
    ap.add_argument("--batch",  type=int, default=0,
                    help="Batch size (0 = use mode default)")
    ap.add_argument("--lr",     type=float, default=1e-3)
    ap.add_argument("--limit",  type=int, default=0,
                    help="Max training rows (0 = use mode default)")
    args = ap.parse_args()

    if args.fast:
        epochs = args.epochs or 3
        batch  = args.batch  or 512
        limit  = args.limit  or 150_000
    else:
        epochs = args.epochs or 5
        batch  = args.batch  or 256
        limit  = args.limit  or 2_000_000

    mode = "FAST" if args.fast else "FULL"
    print(f"[Train] {mode} mode — epochs={epochs}  batch={batch}  limit={limit:,}",
          file=sys.stderr)
    train(epochs, batch, args.lr, limit)


if __name__ == "__main__":
    main()
