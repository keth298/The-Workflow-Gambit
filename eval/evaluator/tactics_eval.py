"""
Tactical Puzzle Evaluator.

Loads puzzles from datasets/tactics.yaml, asks each engine for its best move,
and records accuracy per puzzle and by category.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import chess
import yaml

from evaluator.engine_registry import EngineConfig, EngineRegistry
from evaluator.uci_runner import MoveResult, UCIEngine


# ------------------------------------------------------------------ #
#  Data models                                                         #
# ------------------------------------------------------------------ #

@dataclass
class PuzzleResult:
    puzzle_id: str
    engine_id: str
    tags: List[str]
    correct: bool
    engine_move: Optional[str]
    expected_moves: List[str]
    elapsed_ms: float
    timeout: bool = False
    illegal: bool = False
    no_move: bool = False


@dataclass
class TacticsReport:
    engine_id: str
    total_puzzles: int
    correct: int
    accuracy_pct: float
    avg_time_ms: float
    by_category: Dict[str, dict] = field(default_factory=dict)
    puzzle_results: List[dict] = field(default_factory=list)


# ------------------------------------------------------------------ #
#  Evaluator                                                           #
# ------------------------------------------------------------------ #

class TacticsEvaluator:
    """
    Evaluates each engine on a fixed tactical puzzle set.

    Each puzzle presents a FEN; the engine must return the best UCI move
    within max_time_ms.  The move is checked against a list of accepted answers.
    """

    def __init__(
        self,
        registry: EngineRegistry,
        dataset_path: str = "datasets/tactics.yaml",
        results_dir: str = "results/puzzles",
    ):
        self.registry = registry
        self.dataset_path = dataset_path
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.puzzles = self._load_puzzles()

    def _load_puzzles(self) -> list:
        with open(self.dataset_path) as f:
            data = yaml.safe_load(f)
        return data.get("puzzles", [])

    def run(self) -> Dict[str, TacticsReport]:
        reports: Dict[str, TacticsReport] = {}

        for engine in self.registry.enabled_engines():
            if engine.stockfish_derived:
                continue
            out_path = self.results_dir / f"tactics_{engine.engine_id}.json"
            if out_path.exists():
                print(f"  [skip] {engine.engine_id} — results already exist")
                continue
            print(f"\nTactics eval: {engine.engine_id} ({len(self.puzzles)} puzzles)")
            report = self._eval_engine(engine)
            reports[engine.engine_id] = report

            with open(out_path, "w") as f:
                json.dump(asdict(report), f, indent=2)
            print(
                f"  Accuracy: {report.accuracy_pct:.1f}% "
                f"({report.correct}/{report.total_puzzles}) "
                f"| avg {report.avg_time_ms:.0f}ms"
            )

        return reports

    def _eval_engine(self, engine: EngineConfig) -> TacticsReport:
        puzzle_results: List[PuzzleResult] = []

        with UCIEngine(engine, move_timeout_s=10.0) as uci:
            uci.new_game()
            for puzzle in self.puzzles:
                result = self._run_puzzle(uci, engine.engine_id, puzzle)
                puzzle_results.append(result)

        return self._compile_report(engine.engine_id, puzzle_results)

    def _run_puzzle(
        self,
        uci: UCIEngine,
        engine_id: str,
        puzzle: dict,
    ) -> PuzzleResult:
        puzzle_id = puzzle["puzzle_id"]
        fen = puzzle["fen"]
        best_moves = [m.lower() for m in puzzle.get("best_uci_moves", [])]
        max_ms = puzzle.get("max_time_ms", 2000)
        tags = puzzle.get("tags", [])

        board = chess.Board(fen)

        resp = uci.get_move(
            board,
            time_left_ms=max_ms,
            increment_ms=0,
            max_move_ms=max_ms,
        )

        engine_move = resp.move.uci().lower() if resp.move else None
        correct = engine_move in best_moves if engine_move else False

        return PuzzleResult(
            puzzle_id=puzzle_id,
            engine_id=engine_id,
            tags=tags,
            correct=correct,
            engine_move=engine_move,
            expected_moves=best_moves,
            elapsed_ms=resp.elapsed_ms,
            timeout=resp.result == MoveResult.TIMEOUT,
            illegal=resp.result == MoveResult.ILLEGAL,
            no_move=resp.result == MoveResult.NO_MOVE,
        )

    def _compile_report(
        self, engine_id: str, results: List[PuzzleResult]
    ) -> TacticsReport:
        total = len(results)
        correct_count = sum(1 for r in results if r.correct)
        accuracy = correct_count / total * 100 if total else 0
        avg_time = sum(r.elapsed_ms for r in results) / total if total else 0

        # Category breakdown
        category_data: Dict[str, Dict[str, int]] = {}
        for r in results:
            for tag in r.tags:
                if tag not in category_data:
                    category_data[tag] = {"total": 0, "correct": 0}
                category_data[tag]["total"] += 1
                if r.correct:
                    category_data[tag]["correct"] += 1

        by_category = {
            tag: {
                "total": d["total"],
                "correct": d["correct"],
                "accuracy_pct": d["correct"] / d["total"] * 100 if d["total"] else 0,
            }
            for tag, d in category_data.items()
        }

        return TacticsReport(
            engine_id=engine_id,
            total_puzzles=total,
            correct=correct_count,
            accuracy_pct=accuracy,
            avg_time_ms=avg_time,
            by_category=by_category,
            puzzle_results=[asdict(r) for r in results],
        )
