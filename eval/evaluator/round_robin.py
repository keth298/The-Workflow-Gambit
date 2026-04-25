"""
Round-Robin Tournament Runner.

For N engines generates all N*(N-1)/2 unique pairings; each pair plays
`games_per_pair` games with alternating colours.  Results are saved
incrementally after every game so the tournament can be resumed.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from evaluator.engine_registry import EngineConfig, EngineRegistry
from evaluator.game_runner import GameRecord, GameRunner, TimeControl


# ------------------------------------------------------------------ #
#  Data models                                                         #
# ------------------------------------------------------------------ #

@dataclass
class EngineStanding:
    engine_id: str
    engine_name: str
    games_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    points: float = 0.0
    illegal_moves: int = 0
    crashes: int = 0
    timeouts: int = 0
    forfeit_wins: int = 0
    forfeit_losses: int = 0

    @property
    def win_rate(self) -> float:
        if self.games_played == 0:
            return 0.0
        return self.wins / self.games_played


@dataclass
class RoundRobinResult:
    tournament_id: str
    engines: List[str]
    games_per_pair: int
    time_control: dict
    random_seed: int
    status: str            # "in_progress" | "completed"
    games: List[dict] = field(default_factory=list)
    standings: List[dict] = field(default_factory=list)
    pairwise: Dict[str, Dict[str, dict]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------------ #
#  Tournament runner                                                   #
# ------------------------------------------------------------------ #

class RoundRobin:
    """
    Runs a round-robin tournament, saving state after each game.

    Resumes transparently if a previous results file is found.
    """

    def __init__(
        self,
        tournament_id: str,
        engines: List[EngineConfig],
        time_control: TimeControl,
        games_per_pair: int = 4,
        random_seed: int = 42,
        results_dir: str = "results/tournaments",
        pgn_dir: str = "results/games",
        opening_suite: Optional[List[str]] = None,
    ):
        self.tournament_id = tournament_id
        self.engines = engines
        self.tc = time_control
        self.games_per_pair = games_per_pair
        self.random_seed = random_seed
        self.results_dir = Path(results_dir)
        self.pgn_dir = Path(pgn_dir)
        self.opening_suite = opening_suite or []
        self._results_path = self.results_dir / f"{tournament_id}.json"

    # ------------------------------------------------------------------ #
    #  Factory                                                             #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_config(
        cls, config: dict, registry: EngineRegistry
    ) -> "RoundRobin":
        tc_data = config.get("time_control", {})
        return cls(
            tournament_id=config.get("tournament_id", "round_robin_main"),
            engines=registry.enabled_engines(),
            time_control=TimeControl.from_dict(tc_data),
            games_per_pair=config.get("games_per_pair", 4),
            random_seed=config.get("random_seed", 42),
            results_dir=str(Path(config.get("results_dir", "results/")) / "tournaments"),
            pgn_dir=config.get("pgn_dir", "results/games"),
        )

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def run(self) -> RoundRobinResult:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.pgn_dir.mkdir(parents=True, exist_ok=True)

        state = self._load_state()
        completed_game_ids = {g["game_id"] for g in state["games"]}

        pairings = self._generate_pairings()
        total = len(pairings)
        done = 0

        for idx, (white_cfg, black_cfg, game_number) in enumerate(pairings):
            game_id = self._game_id(white_cfg, black_cfg, game_number)
            done += 1
            if game_id in completed_game_ids:
                print(f"  [skip] {game_id} already complete ({done}/{total})")
                continue

            print(
                f"  [{done}/{total}] {white_cfg.engine_id} vs "
                f"{black_cfg.engine_id} (game {game_number + 1})"
            )
            runner = GameRunner(
                white_cfg, black_cfg, self.tc,
                tournament_id=self.tournament_id,
                game_id=game_id,
                pgn_dir=str(self.pgn_dir),
                results_dir=str(self.pgn_dir),
            )
            try:
                record = runner.run()
            except Exception as exc:
                print(f"    ERROR running game: {exc}")
                continue

            state["games"].append(record.to_dict())
            self._save_state(state)

        state["status"] = "completed"
        standings, pairwise = self._compute_standings(state["games"])
        state["standings"] = [asdict(s) for s in standings]
        state["pairwise"] = pairwise
        self._save_state(state)

        self._print_standings(standings)
        rr_fields = {k: v for k, v in state.items()
                     if k in RoundRobinResult.__dataclass_fields__}
        return RoundRobinResult(**rr_fields)

    def get_standings(self) -> List[EngineStanding]:
        state = self._load_state()
        standings, _ = self._compute_standings(state["games"])
        return standings

    # ------------------------------------------------------------------ #
    #  Pairing generation                                                  #
    # ------------------------------------------------------------------ #

    def _generate_pairings(self) -> List[Tuple[EngineConfig, EngineConfig, int]]:
        """
        For each unordered pair (A, B) and each game index 0..games_per_pair-1,
        alternate colours: even games → A=white, odd games → A=black.
        """
        pairings: List[Tuple[EngineConfig, EngineConfig, int]] = []
        for e1, e2 in combinations(self.engines, 2):
            for g in range(self.games_per_pair):
                if g % 2 == 0:
                    pairings.append((e1, e2, g))
                else:
                    pairings.append((e2, e1, g))
        return pairings

    def _game_id(
        self, white: EngineConfig, black: EngineConfig, game_number: int
    ) -> str:
        return f"{self.tournament_id}_{white.engine_id}_vs_{black.engine_id}_g{game_number}"

    # ------------------------------------------------------------------ #
    #  Standings computation                                               #
    # ------------------------------------------------------------------ #

    def _compute_standings(
        self, games: List[dict]
    ) -> Tuple[List[EngineStanding], Dict[str, Dict[str, dict]]]:
        standings: Dict[str, EngineStanding] = {
            e.engine_id: EngineStanding(
                engine_id=e.engine_id, engine_name=e.engine_name
            )
            for e in self.engines
        }
        pairwise: Dict[str, Dict[str, dict]] = {
            e.engine_id: {
                o.engine_id: {"wins": 0, "draws": 0, "losses": 0}
                for o in self.engines
                if o.engine_id != e.engine_id
            }
            for e in self.engines
        }

        for g in games:
            w = g["white_engine_id"]
            b = g["black_engine_id"]
            result = g["result"]
            termination = g.get("termination", "")

            if w not in standings or b not in standings:
                continue

            ws = standings[w]
            bs = standings[b]
            ws.games_played += 1
            bs.games_played += 1
            ws.illegal_moves += g.get("white_illegal_moves", 0)
            bs.illegal_moves += g.get("black_illegal_moves", 0)
            if termination == "crash":
                if result == "1-0":
                    bs.crashes += 1
                else:
                    ws.crashes += 1
            if termination == "timeout":
                if result == "1-0":
                    bs.timeouts += 1
                else:
                    ws.timeouts += 1

            if result == "1-0":
                ws.wins += 1
                ws.points += 1.0
                bs.losses += 1
                if w in pairwise and b in pairwise[w]:
                    pairwise[w][b]["wins"] += 1
                if b in pairwise and w in pairwise[b]:
                    pairwise[b][w]["losses"] += 1
            elif result == "0-1":
                bs.wins += 1
                bs.points += 1.0
                ws.losses += 1
                if b in pairwise and w in pairwise[b]:
                    pairwise[b][w]["wins"] += 1
                if w in pairwise and b in pairwise[w]:
                    pairwise[w][b]["losses"] += 1
            else:
                ws.draws += 1
                ws.points += 0.5
                bs.draws += 1
                bs.points += 0.5
                if w in pairwise and b in pairwise[w]:
                    pairwise[w][b]["draws"] += 1
                if b in pairwise and w in pairwise[b]:
                    pairwise[b][w]["draws"] += 1

        ranked = sorted(standings.values(), key=lambda s: s.points, reverse=True)
        return ranked, pairwise

    # ------------------------------------------------------------------ #
    #  State persistence                                                   #
    # ------------------------------------------------------------------ #

    def _load_state(self) -> dict:
        if self._results_path.exists():
            with open(self._results_path) as f:
                return json.load(f)
        return {
            "tournament_id": self.tournament_id,
            "type": "round_robin",
            "engines": [e.engine_id for e in self.engines],
            "games_per_pair": self.games_per_pair,
            "time_control": {
                "base_seconds": self.tc.base_seconds,
                "increment_seconds": self.tc.increment_seconds,
            },
            "random_seed": self.random_seed,
            "status": "in_progress",
            "games": [],
            "standings": [],
            "pairwise": {},
        }

    def _save_state(self, state: dict) -> None:
        with open(self._results_path, "w") as f:
            json.dump(state, f, indent=2)

    # ------------------------------------------------------------------ #
    #  Display                                                             #
    # ------------------------------------------------------------------ #

    def _print_standings(self, standings: List[EngineStanding]) -> None:
        print(f"\n{'='*60}")
        print(f"Round-Robin Standings — {self.tournament_id}")
        print(f"{'='*60}")
        header = f"{'#':>3}  {'Engine':<30} {'Pts':>5} {'W':>4} {'D':>4} {'L':>4}"
        print(header)
        print("-" * 60)
        for rank, s in enumerate(standings, 1):
            print(
                f"{rank:>3}  {s.engine_name:<30} {s.points:>5.1f} "
                f"{s.wins:>4} {s.draws:>4} {s.losses:>4}"
            )
        print()
