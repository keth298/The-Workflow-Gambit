"""
Metrics aggregator — reads all result files and computes the scoring
leaderboards defined in PRD §10.

Produces:
- Raw Strength leaderboard
- Reliability leaderboard
- Engineering Efficiency leaderboard
- Creativity leaderboard (from process metrics files)
- Overall Experimental Winner leaderboard
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ------------------------------------------------------------------ #
#  Data model for one engine's aggregated data                         #
# ------------------------------------------------------------------ #

@dataclass
class EngineMetrics:
    engine_id: str
    engine_name: str = ""

    # --- Competitive strength ---
    rr_points: float = 0.0
    rr_games: int = 0
    rr_wins: int = 0
    rr_draws: int = 0
    rr_losses: int = 0
    de_placement: Optional[int] = None
    de_total_engines: int = 0
    stockfish_score_pct: float = 0.0   # avg across all skill levels
    tactical_accuracy_pct: float = 0.0

    # --- Reliability ---
    illegal_moves: int = 0
    total_moves: int = 0
    crashes: int = 0
    timeouts: int = 0
    games_played: int = 0
    games_completed: int = 0

    # --- Blunder / quality ---
    avg_cp_loss: float = 0.0
    blunder_rate_pct: float = 0.0
    best_move_agreement_pct: float = 0.0

    # --- Engineering / process ---
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    human_time_minutes: int = 0
    prompt_count: int = 0
    human_correction_count: int = 0
    loc: int = 0
    test_count: int = 0
    test_pass_rate: float = 0.0
    doc_word_count: int = 0
    prior_knowledge_score: int = 0
    frustration_score: int = 0
    multitaskability_score: int = 0
    parallelization_score: int = 0

    # --- Creativity ---
    novelty: float = 0.0
    strategic_originality: float = 0.0
    agent_workflow_originality: float = 0.0
    risk_taking: float = 0.0
    coherence: float = 0.0

    # --- Computed scores (filled in by Metrics.aggregate) ---
    raw_strength_score: float = 0.0
    reliability_score: float = 0.0
    engineering_efficiency_score: float = 0.0
    creativity_score: float = 0.0
    overall_score: float = 0.0


@dataclass
class AggregatedData:
    engines: List[EngineMetrics]
    raw_strength_ranking: List[str]
    reliability_ranking: List[str]
    efficiency_ranking: List[str]
    creativity_ranking: List[str]
    overall_ranking: List[str]


# ------------------------------------------------------------------ #
#  Metrics aggregator                                                  #
# ------------------------------------------------------------------ #

class Metrics:
    """
    Loads all results from `results_dir` and computes scoring leaderboards.
    """

    def __init__(self, results_dir: str, scoring_config: dict):
        self.results_dir = Path(results_dir)
        self.cfg = scoring_config

    def aggregate(self) -> AggregatedData:
        engine_data: Dict[str, EngineMetrics] = {}

        self._load_round_robin(engine_data)
        self._load_double_elim(engine_data)
        self._load_stockfish_eval(engine_data)
        self._load_tactics(engine_data)
        self._load_blunder(engine_data)
        self._load_process_metrics(engine_data)
        self._load_creativity_scores(engine_data)

        engines = list(engine_data.values())
        if not engines:
            return AggregatedData(
                engines=[], raw_strength_ranking=[], reliability_ranking=[],
                efficiency_ranking=[], creativity_ranking=[], overall_ranking=[],
            )

        self._compute_scores(engines)

        return AggregatedData(
            engines=engines,
            raw_strength_ranking=self._rank(engines, "raw_strength_score"),
            reliability_ranking=self._rank(engines, "reliability_score"),
            efficiency_ranking=self._rank(engines, "engineering_efficiency_score"),
            creativity_ranking=self._rank(engines, "creativity_score"),
            overall_ranking=self._rank(engines, "overall_score"),
        )

    # ------------------------------------------------------------------ #
    #  Loaders                                                             #
    # ------------------------------------------------------------------ #

    def _load_round_robin(self, data: Dict[str, EngineMetrics]) -> None:
        pattern = self.results_dir / "tournaments" / "*.json"
        for path in self.results_dir.glob("tournaments/*.json"):
            try:
                with open(path) as f:
                    rr = json.load(f)
                if rr.get("type") != "round_robin":
                    continue
                for standing in rr.get("standings", []):
                    eid = standing["engine_id"]
                    em = self._get_or_create(data, eid)
                    em.engine_name = standing.get("engine_name", eid)
                    em.rr_points += standing.get("points", 0)
                    em.rr_games += standing.get("games_played", 0)
                    em.rr_wins += standing.get("wins", 0)
                    em.rr_draws += standing.get("draws", 0)
                    em.rr_losses += standing.get("losses", 0)
                    em.games_played += standing.get("games_played", 0)
                    em.games_completed += standing.get("games_played", 0)
                    em.illegal_moves += standing.get("illegal_moves", 0)
                    em.crashes += standing.get("crashes", 0)
                    em.timeouts += standing.get("timeouts", 0)
            except Exception as exc:
                print(f"Warning: could not load {path}: {exc}")

        # Count total moves from game records
        for path in self.results_dir.glob("games/*.json"):
            try:
                with open(path) as f:
                    g = json.load(f)
                for side in ("white", "black"):
                    eid = g.get(f"{side}_engine_id")
                    if eid:
                        em = self._get_or_create(data, eid)
                        em.total_moves += g.get("plies", 0) // 2

            except Exception:
                pass

    def _load_double_elim(self, data: Dict[str, EngineMetrics]) -> None:
        for path in self.results_dir.glob("tournaments/*.json"):
            try:
                with open(path) as f:
                    de = json.load(f)
                if de.get("type") != "double_elimination":
                    continue
                total = len(de.get("engines", []))
                for placement in de.get("placements", []):
                    eid = placement["engine_id"]
                    em = self._get_or_create(data, eid)
                    em.de_placement = placement.get("placement")
                    em.de_total_engines = total
            except Exception as exc:
                print(f"Warning: could not load {path}: {exc}")

    def _load_stockfish_eval(self, data: Dict[str, EngineMetrics]) -> None:
        for path in self.results_dir.glob("puzzles/stockfish_eval_*.json"):
            try:
                with open(path) as f:
                    rec = json.load(f)
                eid = rec.get("engine_id")
                if not eid:
                    continue
                em = self._get_or_create(data, eid)
                levels = rec.get("results_by_level", [])
                if levels:
                    em.stockfish_score_pct = sum(
                        l.get("score_pct", 0) for l in levels
                    ) / len(levels)
            except Exception as exc:
                print(f"Warning: could not load {path}: {exc}")

    def _load_tactics(self, data: Dict[str, EngineMetrics]) -> None:
        for path in self.results_dir.glob("puzzles/tactics_*.json"):
            try:
                with open(path) as f:
                    rec = json.load(f)
                eid = rec.get("engine_id")
                if not eid:
                    continue
                em = self._get_or_create(data, eid)
                em.tactical_accuracy_pct = rec.get("accuracy_pct", 0)
            except Exception as exc:
                print(f"Warning: could not load {path}: {exc}")

    def _load_blunder(self, data: Dict[str, EngineMetrics]) -> None:
        for path in self.results_dir.glob("puzzles/blunder_*.json"):
            try:
                with open(path) as f:
                    rec = json.load(f)
                eid = rec.get("engine_id")
                if not eid:
                    continue
                em = self._get_or_create(data, eid)
                em.avg_cp_loss = rec.get("avg_cp_loss", 0)
                em.blunder_rate_pct = rec.get("blunder_rate_pct", 0)
                em.best_move_agreement_pct = rec.get("best_move_agreement_pct", 0)
            except Exception as exc:
                print(f"Warning: could not load {path}: {exc}")

    def _load_process_metrics(self, data: Dict[str, EngineMetrics]) -> None:
        """
        Loads process_metrics.yaml (or .json) files from engine subdirectories
        and from the results/ directory.
        """
        for path in list(self.results_dir.glob("process_metrics_*.json")) + \
                    list(self.results_dir.glob("process_metrics_*.yaml")):
            try:
                with open(path) as f:
                    if path.suffix == ".yaml":
                        rec = yaml.safe_load(f)
                    else:
                        rec = json.load(f)
                eid = rec.get("engine_id")
                if not eid:
                    continue
                em = self._get_or_create(data, eid)
                em.input_tokens = rec.get("input_tokens", 0)
                em.output_tokens = rec.get("output_tokens", 0)
                em.estimated_cost_usd = rec.get("estimated_cost_usd", 0)
                em.human_time_minutes = rec.get("human_time_minutes", 0)
                em.prompt_count = rec.get("prompt_count", 0)
                em.human_correction_count = rec.get("human_correction_count", 0)
                em.loc = rec.get("loc", 0)
                em.test_count = rec.get("test_count", 0)
                em.test_pass_rate = rec.get("test_pass_rate", 0)
                em.doc_word_count = rec.get("doc_word_count", 0)
                em.prior_knowledge_score = rec.get("prior_knowledge_required_score", 0)
                em.frustration_score = rec.get("frustration_score", 0)
                em.multitaskability_score = rec.get("multitaskability_score", 0)
                em.parallelization_score = rec.get("parallelization_score", 0)
            except Exception as exc:
                print(f"Warning: could not load {path}: {exc}")

    def _load_creativity_scores(self, data: Dict[str, EngineMetrics]) -> None:
        for path in list(self.results_dir.glob("creativity_*.json")) + \
                    list(self.results_dir.glob("creativity_*.yaml")):
            try:
                with open(path) as f:
                    if path.suffix == ".yaml":
                        rec = yaml.safe_load(f)
                    else:
                        rec = json.load(f)
                eid = rec.get("engine_id")
                if not eid:
                    continue
                em = self._get_or_create(data, eid)
                em.novelty = rec.get("novelty", 0)
                em.strategic_originality = rec.get("strategic_originality", 0)
                em.agent_workflow_originality = rec.get("agent_workflow_originality", 0)
                em.risk_taking = rec.get("risk_taking", 0)
                em.coherence = rec.get("coherence", 0)
            except Exception as exc:
                print(f"Warning: could not load {path}: {exc}")

    # ------------------------------------------------------------------ #
    #  Score computation                                                   #
    # ------------------------------------------------------------------ #

    def _compute_scores(self, engines: List[EngineMetrics]) -> None:
        """Normalise raw values and apply PRD §10 formulas."""
        # Normalise helpers
        def norm(values: List[float]) -> List[float]:
            mn, mx = min(values), max(values)
            if mx == mn:
                return [0.5] * len(values)
            return [(v - mn) / (mx - mn) for v in values]

        n = len(engines)
        if n == 0:
            return

        # ---- Raw Strength (§10.1) ------------------------------------ #
        s = self.cfg.get("raw_strength", {})
        rr_pts = [e.rr_points for e in engines]
        de_pts = [
            (e.de_total_engines - (e.de_placement or e.de_total_engines)) / max(e.de_total_engines - 1, 1)
            for e in engines
        ]
        sf_pts = [e.stockfish_score_pct for e in engines]
        tac_pts = [e.tactical_accuracy_pct for e in engines]

        rr_n, de_n, sf_n, tac_n = norm(rr_pts), norm(de_pts), norm(sf_pts), norm(tac_pts)

        for i, e in enumerate(engines):
            e.raw_strength_score = (
                s.get("round_robin_normalized", 0.45) * rr_n[i]
                + s.get("double_elim_normalized", 0.20) * de_n[i]
                + s.get("stockfish_score_normalized", 0.20) * sf_n[i]
                + s.get("tactical_accuracy_normalized", 0.15) * tac_n[i]
            )

        # ---- Reliability (§10.2) ------------------------------------- #
        r = self.cfg.get("reliability", {})
        for e in engines:
            gp = max(e.games_played, 1)
            tm = max(e.total_moves, 1)
            completion_rate = e.games_completed / gp
            illegal_rate = e.illegal_moves / tm
            crash_rate = e.crashes / gp
            timeout_rate = e.timeouts / gp

            e.reliability_score = (
                r.get("completion_rate", 0.35) * completion_rate
                + r.get("illegal_move_rate", 0.25) * (1 - illegal_rate)
                + r.get("crash_rate", 0.20) * (1 - crash_rate)
                + r.get("timeout_rate", 0.20) * (1 - timeout_rate)
            )

        # ---- Engineering Efficiency (§10.3) -------------------------- #
        eff = self.cfg.get("engineering_efficiency", {})
        for e in engines:
            strength = e.raw_strength_score
            cost = max(e.estimated_cost_usd, 0.01)
            time_ = max(e.human_time_minutes, 1)
            prompts = max(e.prompt_count, 1)
            test_pass = e.test_pass_rate / 100 if e.test_pass_rate > 1 else e.test_pass_rate
            # maintainability: proxy from test count and docs
            maint = min((e.test_count * 0.1 + e.doc_word_count * 0.001) / 10, 1.0)

            e.engineering_efficiency_score = (
                eff.get("strength_per_dollar", 0.30) * min(strength / cost, 1.0)
                + eff.get("strength_per_human_minute", 0.25) * min(strength / time_, 1.0)
                + eff.get("strength_per_prompt", 0.20) * min(strength / prompts, 1.0)
                + eff.get("test_pass_rate", 0.15) * test_pass
                + eff.get("maintainability_score", 0.10) * maint
            )

        # ---- Creativity (§10.4) -------------------------------------- #
        cr = self.cfg.get("creativity", {})
        for e in engines:
            e.creativity_score = (
                cr.get("novelty", 0.25) * e.novelty / 5
                + cr.get("strategic_originality", 0.20) * e.strategic_originality / 5
                + cr.get("agent_workflow_originality", 0.25) * e.agent_workflow_originality / 5
                + cr.get("risk_taking", 0.15) * e.risk_taking / 5
                + cr.get("coherence", 0.15) * e.coherence / 5
            )

        # ---- Overall (§10.5) ---------------------------------------- #
        ov = self.cfg.get("overall", {})
        doc_scores = norm([
            e.doc_word_count + e.test_count * 50 for e in engines
        ])
        for i, e in enumerate(engines):
            e.overall_score = (
                ov.get("raw_strength", 0.40) * e.raw_strength_score
                + ov.get("reliability", 0.20) * e.reliability_score
                + ov.get("engineering_efficiency", 0.20) * e.engineering_efficiency_score
                + ov.get("creativity", 0.10) * e.creativity_score
                + ov.get("documentation_reproducibility", 0.10) * doc_scores[i]
            )

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _get_or_create(
        self, data: Dict[str, EngineMetrics], engine_id: str
    ) -> EngineMetrics:
        if engine_id not in data:
            data[engine_id] = EngineMetrics(engine_id=engine_id)
        return data[engine_id]

    def _rank(self, engines: List[EngineMetrics], attr: str) -> List[str]:
        return [
            e.engine_id
            for e in sorted(engines, key=lambda x: getattr(x, attr), reverse=True)
        ]
