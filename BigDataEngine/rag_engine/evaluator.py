"""
Neural network evaluator — value network + policy network.

Architecture (both share the same 4-layer torso)
-------------------------------------------------
Input:  773-dim float32 feature vector
Torso:  Linear(773→512) → ReLU → LayerNorm
        Linear(512→256)  → ReLU → LayerNorm
Value head:  Linear(256→64) → ReLU → Linear(64→1) → Tanh  → scalar ∈ [-1, +1]
Policy head: Linear(256→4096) (logits; masked + softmax at inference)

Weights are saved/loaded from LargeDataset/model.pt.
The network gives reasonable random-ish output even before training, and is
used as a fallback when retrieval confidence is low.
"""

from __future__ import annotations

import sys
from pathlib import Path

import chess
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
from encoder import encode_board, FEATURE_DIM, POLICY_DIM, legal_move_mask

ROOT       = Path(__file__).parent.parent
MODEL_PATH = ROOT / "LargeDataset" / "model.pt"


# ── Architecture ──────────────────────────────────────────────────────────────

class ChessNet(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.torso = nn.Sequential(
            nn.Linear(FEATURE_DIM, 512),
            nn.ReLU(),
            nn.LayerNorm(512),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.LayerNorm(256),
        )
        self.value_head = nn.Sequential(
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Tanh(),
        )
        self.policy_head = nn.Linear(256, POLICY_DIM)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Return (value, policy_logits)."""
        h = self.torso(x)
        return self.value_head(h).squeeze(-1), self.policy_head(h)


# ── Evaluator wrapper ─────────────────────────────────────────────────────────

class NeuralEvaluator:
    def __init__(self) -> None:
        self._net   = ChessNet()
        self._loaded = False
        self._device = torch.device("cpu")

    def _load(self) -> None:
        if MODEL_PATH.exists():
            state = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
            self._net.load_state_dict(state)
            print("[NeuralEval] Loaded weights from model.pt", file=sys.stderr)
        else:
            print("[NeuralEval] No model.pt found — using random-initialised weights.", file=sys.stderr)
        self._net.eval()
        self._loaded = True

    def _ensure(self) -> None:
        if not self._loaded:
            self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def evaluate(self, board: chess.Board) -> float:
        """Return value estimate ∈ [-1, +1] from side-to-move perspective."""
        self._ensure()
        with torch.no_grad():
            x   = torch.tensor(encode_board(board), dtype=torch.float32).unsqueeze(0)
            val, _ = self._net(x)
        score = val.item()
        return score if board.turn == chess.WHITE else -score

    def policy(self, board: chess.Board) -> dict[str, float]:
        """Return dict {uci: prior} over legal moves (sums to 1)."""
        self._ensure()
        mask = legal_move_mask(board)
        with torch.no_grad():
            x = torch.tensor(encode_board(board), dtype=torch.float32).unsqueeze(0)
            _, logits = self._net(x)
        logits_np = logits.squeeze(0).numpy()

        # Mask illegal moves by setting their logits to -∞
        logits_np[mask == 0] = -1e9
        exp = np.exp(logits_np - logits_np.max())
        exp[mask == 0] = 0.0
        total = exp.sum()
        if total == 0.0:
            return {}
        probs = exp / total

        result: dict[str, float] = {}
        for m in board.legal_moves:
            idx = m.from_square * 64 + m.to_square
            result[m.uci()] = float(probs[idx])
        return result

    def model(self) -> ChessNet:
        self._ensure()
        return self._net
