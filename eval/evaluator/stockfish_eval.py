"""
Stockfish Baseline Evaluator.

Runs each engine against Stockfish at multiple skill levels and records:
- Score percentage (wins + 0.5*draws) / games
- Survival length (average plies before defeat vs strong Stockfish)
- Per-game records
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from evaluator.engine_registry import EngineConfig, EngineRegistry
from evaluator.game_runner import GameRecord, GameRunner, TimeControl


STOCKFISH_ENGINE_ID = "stockfish_baseline"
STOCKFISH_COMMAND = "stockfish"


@dataclass
class StockfishLevelResult:
    engine_id: str
    stockfish_skill_level: int
    games_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    score_pct: float = 0.0
    avg_survival_plies: float = 0.0
    total_plies: int = 0


@dataclass
class StockfishEvalRecord:
    engine_id: str
    results_by_level: List[dict] = field(default_factory=list)


def _make_stockfish_config(skill_level: int) -> EngineConfig:
    """Build an EngineConfig for Stockfish at a given skill level."""
    options: dict = {"Skill Level": str(skill_level)}
    if skill_level <= 5:
        options["UCI_LimitStrength"] = "true"
    return EngineConfig(
        engine_id=f"stockfish_skill_{skill_level}",
        engine_name=f"Stockfish (Skill {skill_level})",
        strategy_name="Baseline",
        owner="evaluator",
        uci_command="stockfish",
        language="C++",
        stockfish_derived=True,
        enabled=True,
        uci_options=options,
    )


class StockfishEvaluator:
    """
    Benchmarks each enabled engine against Stockfish at configured skill levels.

    Two games per level (engine as white, engine as black).
    """

    def __init__(
        self,
        registry: EngineRegistry,
        tournament_config: dict,
        scoring_config: dict,
    ):
        self.registry = registry
        self.tc = TimeControl.from_dict(
            tournament_config.get("time_control", {})
        )
        self.skill_levels: List[int] = scoring_config.get(
            "stockfish_skill_levels", [0, 5, 10, 20]
        )
        self.results_dir = (
            Path(tournament_config.get("results_dir", "results/")) / "puzzles"
        )
        self.pgn_dir = Path(tournament_config.get("pgn_dir", "results/games"))
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.pgn_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, StockfishEvalRecord]:
        records: Dict[str, StockfishEvalRecord] = {}

        for engine in self.registry.enabled_engines():
            if engine.stockfish_derived and engine.engine_id.startswith("stockfish"):
                continue  # don't benchmark Stockfish against itself
            out_path = self.results_dir / f"stockfish_eval_{engine.engine_id}.json"
            if out_path.exists():
                print(f"  [skip] {engine.engine_id} — results already exist")
                continue
            print(f"\nStockfish eval: {engine.engine_id}")
            record = self._eval_engine(engine)
            records[engine.engine_id] = record

            with open(out_path, "w") as f:
                json.dump(asdict(record), f, indent=2)
            print(f"  Saved to {out_path}")

        return records

    def _eval_engine(self, engine: EngineConfig) -> StockfishEvalRecord:
        level_results: List[StockfishLevelResult] = []

        for skill in self.skill_levels:
            result = StockfishLevelResult(
                engine_id=engine.engine_id,
                stockfish_skill_level=skill,
            )
            sf_cfg = _make_stockfish_config(skill)

            # Game 1: engine is white
            game1_id = f"sf_eval_{engine.engine_id}_skill{skill}_as_white"
            print(f"  Skill {skill}: {engine.engine_id} (W) vs Stockfish")
            g1 = self._play_game(engine, sf_cfg, game1_id, skill_level=skill)
            if g1:
                result.games_played += 1
                result.total_plies += g1.plies
                if g1.result == "1-0":
                    result.wins += 1
                elif g1.result == "0-1":
                    result.losses += 1
                else:
                    result.draws += 1

            # Game 2: engine is black
            game2_id = f"sf_eval_{engine.engine_id}_skill{skill}_as_black"
            print(f"  Skill {skill}: Stockfish (W) vs {engine.engine_id} (B)")
            g2 = self._play_game(sf_cfg, engine, game2_id, skill_level=skill,
                                 engine_is_black=True)
            if g2:
                result.games_played += 1
                result.total_plies += g2.plies
                if g2.result == "0-1":
                    result.wins += 1
                elif g2.result == "1-0":
                    result.losses += 1
                else:
                    result.draws += 1

            if result.games_played:
                score = result.wins + 0.5 * result.draws
                result.score_pct = score / result.games_played * 100
                result.avg_survival_plies = result.total_plies / result.games_played

            level_results.append(result)

        return StockfishEvalRecord(
            engine_id=engine.engine_id,
            results_by_level=[asdict(r) for r in level_results],
        )

    def _play_game(
        self,
        white_cfg: EngineConfig,
        black_cfg: EngineConfig,
        game_id: str,
        skill_level: int = 20,
        engine_is_black: bool = False,
    ) -> Optional[GameRecord]:
        runner = GameRunner(
            white_cfg, black_cfg, self.tc,
            tournament_id="stockfish_eval",
            game_id=game_id,
            pgn_dir=str(self.pgn_dir),
            results_dir=str(self.pgn_dir),
        )
        try:
            return runner.run()
        except Exception as exc:
            print(f"    Game error: {exc}")
            return None
