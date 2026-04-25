"""
Blunder Evaluator — centipawn-loss analysis using Stockfish.

For each curated position:
1. Ask the engine for its best move.
2. Get Stockfish's evaluation of the position BEFORE the move.
3. Apply the engine's move.
4. Get Stockfish's evaluation AFTER the move.
5. Compute centipawn loss and classify the move.

Classification thresholds (PRD §7.8):
  Inaccuracy:           50–150 cp loss
  Mistake:             150–300 cp loss
  Blunder:             300+   cp loss
  Catastrophic:        missed/allowed forced mate
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import chess
import yaml

from evaluator.engine_registry import EngineConfig, EngineRegistry
from evaluator.stockfish_eval import _make_stockfish_config
from evaluator.uci_runner import MoveResult, UCIEngine


# ------------------------------------------------------------------ #
#  Constants & thresholds                                              #
# ------------------------------------------------------------------ #

INACCURACY_THRESHOLD = 50
MISTAKE_THRESHOLD = 150
BLUNDER_THRESHOLD = 300
MATE_SCORE = 30_000
STOCKFISH_EVAL_DEPTH = 15
STOCKFISH_EVAL_SKILL = 20   # full strength for analysis


class MoveClassification(str, Enum):
    BEST = "best"
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    BLUNDER = "blunder"
    CATASTROPHIC = "catastrophic"
    NO_MOVE = "no_move"


# ------------------------------------------------------------------ #
#  Data models                                                         #
# ------------------------------------------------------------------ #

@dataclass
class PositionBlunderResult:
    position_id: str
    engine_id: str
    tags: List[str]
    engine_move: Optional[str]
    score_before_cp: Optional[int]   # from side-to-move perspective
    score_after_cp: Optional[int]    # from side-to-move perspective after move
    cp_loss: Optional[float]
    classification: str
    best_move_agreement: bool


@dataclass
class BlunderReport:
    engine_id: str
    total_positions: int
    avg_cp_loss: float
    median_cp_loss: float
    blunder_count: int
    blunder_rate_pct: float
    catastrophic_count: int
    inaccuracy_count: int
    mistake_count: int
    best_move_agreement_pct: float
    results: List[dict] = field(default_factory=list)


# ------------------------------------------------------------------ #
#  Evaluator                                                           #
# ------------------------------------------------------------------ #

class BlunderEvaluator:
    """
    Evaluates centipawn loss for each engine across curated positions.

    Requires Stockfish to be installed and accessible via the command 'stockfish'.
    """

    def __init__(
        self,
        registry: EngineRegistry,
        dataset_path: str = "datasets/curated_positions.yaml",
        results_dir: str = "results/puzzles",
        eval_depth: int = STOCKFISH_EVAL_DEPTH,
    ):
        self.registry = registry
        self.dataset_path = dataset_path
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.eval_depth = eval_depth
        self.positions = self._load_positions()

    def _load_positions(self) -> list:
        with open(self.dataset_path) as f:
            data = yaml.safe_load(f)
        return data.get("positions", [])

    def run(self) -> Dict[str, BlunderReport]:
        reports: Dict[str, BlunderReport] = {}

        for engine in self.registry.enabled_engines():
            if engine.stockfish_derived:
                continue
            out_path = self.results_dir / f"blunder_{engine.engine_id}.json"
            if out_path.exists():
                print(f"  [skip] {engine.engine_id} — results already exist")
                continue
            print(f"\nBlunder eval: {engine.engine_id} ({len(self.positions)} positions)")
            report = self._eval_engine(engine)
            reports[engine.engine_id] = report

            with open(out_path, "w") as f:
                json.dump(asdict(report), f, indent=2)
            print(
                f"  Avg CP loss: {report.avg_cp_loss:.1f} | "
                f"Blunder rate: {report.blunder_rate_pct:.1f}%"
            )

        return reports

    def _eval_engine(self, engine: EngineConfig) -> BlunderReport:
        results: List[PositionBlunderResult] = []
        sf_config = _make_stockfish_config(STOCKFISH_EVAL_SKILL)

        with UCIEngine(engine, move_timeout_s=10.0) as uci_engine, \
             UCIEngine(sf_config, move_timeout_s=30.0) as sf_engine:
            uci_engine.new_game()
            sf_engine.new_game()

            for position in self.positions:
                result = self._eval_position(
                    uci_engine, sf_engine, engine.engine_id, position
                )
                results.append(result)

        return self._compile_report(engine.engine_id, results)

    def _eval_position(
        self,
        uci_engine: UCIEngine,
        sf_engine: UCIEngine,
        engine_id: str,
        position: dict,
    ) -> PositionBlunderResult:
        position_id = position["position_id"]
        fen = position["fen"]
        tags = position.get("tags", [])

        board = chess.Board(fen)

        # Step 1: Stockfish evaluation BEFORE the engine's move
        score_before = self._get_sf_score(sf_engine, board)

        # Step 2: Ask the engine for its move
        resp = uci_engine.get_move(board, time_left_ms=5000, increment_ms=0,
                                   max_move_ms=5000)

        if resp.result != MoveResult.OK or resp.move is None:
            return PositionBlunderResult(
                position_id=position_id,
                engine_id=engine_id,
                tags=tags,
                engine_move=None,
                score_before_cp=score_before,
                score_after_cp=None,
                cp_loss=None,
                classification=MoveClassification.NO_MOVE.value,
                best_move_agreement=False,
            )

        engine_move_uci = resp.move.uci()

        # Step 3: Apply engine move and re-evaluate
        board_after = board.copy()
        board_after.push(resp.move)
        score_after_raw = self._get_sf_score(sf_engine, board_after)

        # Flip score perspective: after the move it's the opponent's turn,
        # so negate to get it from the original side's perspective
        score_after = -score_after_raw if score_after_raw is not None else None

        # Step 4: Compute centipawn loss
        cp_loss: Optional[float] = None
        if score_before is not None and score_after is not None:
            cp_loss = float(score_before - score_after)
            cp_loss = max(0.0, cp_loss)  # loss can't be negative (engine might find better)

        # Step 5: Get Stockfish's best move for agreement check
        sf_board = board.copy()
        sf_resp = sf_engine.get_move(sf_board, time_left_ms=5000, increment_ms=0,
                                     max_move_ms=5000)
        sf_best = sf_resp.move.uci() if sf_resp.move else None
        best_move_agreement = (engine_move_uci == sf_best)

        # Step 6: Classify
        classification = self._classify(cp_loss, score_before, score_after)

        return PositionBlunderResult(
            position_id=position_id,
            engine_id=engine_id,
            tags=tags,
            engine_move=engine_move_uci,
            score_before_cp=score_before,
            score_after_cp=score_after,
            cp_loss=cp_loss,
            classification=classification.value,
            best_move_agreement=best_move_agreement,
        )

    def _get_sf_score(
        self, sf_engine: UCIEngine, board: chess.Board
    ) -> Optional[int]:
        """Use Stockfish to evaluate a position. Returns centipawns from side-to-move."""
        return sf_engine.evaluate_position(board, depth=self.eval_depth)

    def _classify(
        self,
        cp_loss: Optional[float],
        score_before: Optional[int],
        score_after: Optional[int],
    ) -> MoveClassification:
        # Catastrophic: missed mate or allowed mate
        if score_before is not None and abs(score_before) >= MATE_SCORE - 100:
            return MoveClassification.CATASTROPHIC
        if score_after is not None and abs(score_after) >= MATE_SCORE - 100:
            return MoveClassification.CATASTROPHIC

        if cp_loss is None:
            return MoveClassification.NO_MOVE

        if cp_loss >= BLUNDER_THRESHOLD:
            return MoveClassification.BLUNDER
        if cp_loss >= MISTAKE_THRESHOLD:
            return MoveClassification.MISTAKE
        if cp_loss >= INACCURACY_THRESHOLD:
            return MoveClassification.INACCURACY
        return MoveClassification.BEST

    def _compile_report(
        self, engine_id: str, results: List[PositionBlunderResult]
    ) -> BlunderReport:
        losses = [r.cp_loss for r in results if r.cp_loss is not None]
        total = len(results)

        avg_cp = sum(losses) / len(losses) if losses else 0.0
        sorted_losses = sorted(losses)
        median_cp = (
            sorted_losses[len(sorted_losses) // 2] if sorted_losses else 0.0
        )

        blunders = [r for r in results if r.classification == MoveClassification.BLUNDER.value]
        catastrophic = [r for r in results if r.classification == MoveClassification.CATASTROPHIC.value]
        inaccuracies = [r for r in results if r.classification == MoveClassification.INACCURACY.value]
        mistakes = [r for r in results if r.classification == MoveClassification.MISTAKE.value]
        agreements = [r for r in results if r.best_move_agreement]

        return BlunderReport(
            engine_id=engine_id,
            total_positions=total,
            avg_cp_loss=avg_cp,
            median_cp_loss=median_cp,
            blunder_count=len(blunders),
            blunder_rate_pct=len(blunders) / total * 100 if total else 0,
            catastrophic_count=len(catastrophic),
            inaccuracy_count=len(inaccuracies),
            mistake_count=len(mistakes),
            best_move_agreement_pct=len(agreements) / total * 100 if total else 0,
            results=[asdict(r) for r in results],
        )
