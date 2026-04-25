"""
Double-Elimination Tournament Runner.

Bracket structure:
  - Every engine starts in the winners bracket.
  - First loss → moves to losers bracket.
  - Second loss → eliminated.
  - Grand final: winners bracket champion vs losers bracket champion.
  - Optional bracket reset if the losers side champion wins the first grand final.

Matches default to best-of-2 (one game each colour) with tiebreak if needed.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from evaluator.engine_registry import EngineConfig, EngineRegistry
from evaluator.game_runner import GameRunner, TimeControl


# ------------------------------------------------------------------ #
#  Data models                                                         #
# ------------------------------------------------------------------ #

@dataclass
class MatchResult:
    match_id: str
    round_name: str
    engine_a: str
    engine_b: str
    winner: Optional[str]
    score_a: float
    score_b: float
    games: List[dict] = field(default_factory=list)
    tiebreak_used: bool = False


@dataclass
class BracketPlacement:
    engine_id: str
    placement: int          # 1 = champion, 2 = runner-up, etc.
    eliminated_by: Optional[str] = None
    elimination_round: Optional[str] = None


@dataclass
class DoubleElimResult:
    tournament_id: str
    engines: List[str]
    status: str
    matches: List[dict] = field(default_factory=list)
    placements: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------------ #
#  Tournament runner                                                   #
# ------------------------------------------------------------------ #

class DoubleElimination:
    """
    Double-elimination tournament with configurable match format.

    Parameters
    ----------
    games_per_match:
        Number of games per match (use even numbers for fair colour splits).
        Default is 2 (one as white, one as black).
    bracket_reset:
        If True and the losers-bracket champion wins the grand final, a
        reset game is played to determine the ultimate winner.
    """

    def __init__(
        self,
        tournament_id: str,
        engines: List[EngineConfig],
        time_control: TimeControl,
        games_per_match: int = 2,
        bracket_reset: bool = True,
        seeding: Optional[List[str]] = None,
        results_dir: str = "results/tournaments",
        pgn_dir: str = "results/games",
    ):
        self.tournament_id = tournament_id
        self.tc = time_control
        self.games_per_match = games_per_match
        self.bracket_reset = bracket_reset
        self.results_dir = Path(results_dir)
        self.pgn_dir = Path(pgn_dir)
        self._results_path = self.results_dir / f"{tournament_id}.json"

        # Apply seeding or use supplied order
        engine_map = {e.engine_id: e for e in engines}
        if seeding:
            self.engines = [engine_map[eid] for eid in seeding if eid in engine_map]
        else:
            self.engines = list(engines)

    # ------------------------------------------------------------------ #
    #  Factory                                                             #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_config(
        cls,
        config: dict,
        registry: EngineRegistry,
        seed_results_path: Optional[str] = None,
    ) -> "DoubleElimination":
        tc_data = config.get("time_control", {})
        seeding: Optional[List[str]] = None

        if seed_results_path:
            try:
                with open(seed_results_path) as f:
                    rr = json.load(f)
                seeding = [s["engine_id"] for s in rr.get("standings", [])]
            except Exception as exc:
                print(f"Warning: could not load seed results: {exc}")

        engines = registry.enabled_engines()
        base = Path(config.get("results_dir", "results/"))
        return cls(
            tournament_id=config.get("tournament_id", "double_elim_main")
            .replace("round_robin", "double_elim"),
            engines=engines,
            time_control=TimeControl.from_dict(tc_data),
            results_dir=str(base / "tournaments"),
            pgn_dir=config.get("pgn_dir", "results/games"),
            seeding=seeding,
        )

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def run(self) -> DoubleElimResult:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.pgn_dir.mkdir(parents=True, exist_ok=True)

        state = self._load_state()
        completed_match_ids = {m["match_id"] for m in state["matches"]}

        winners: List[str] = [e.engine_id for e in self.engines]
        losers: List[str] = []
        eliminated: List[str] = []
        placements: Dict[str, BracketPlacement] = {}
        all_matches: List[MatchResult] = [
            MatchResult(**m) for m in state["matches"]
        ]
        engine_map = {e.engine_id: e for e in self.engines}

        round_num = 0

        # ---- Winners bracket ----------------------------------------- #
        while len(winners) > 1:
            round_num += 1
            round_name = f"winners_r{round_num}"
            winners, new_losers, round_matches = self._play_bracket_round(
                winners, round_name, engine_map, completed_match_ids
            )
            losers.extend(new_losers)
            all_matches.extend(round_matches)
            state["matches"] = [asdict(m) for m in all_matches]
            self._save_state(state)

        winners_champion = winners[0] if winners else None

        # ---- Losers bracket ------------------------------------------ #
        losers_round = 0
        while len(losers) > 1:
            losers_round += 1
            round_name = f"losers_r{losers_round}"
            losers, newly_eliminated, round_matches = self._play_bracket_round(
                losers, round_name, engine_map, completed_match_ids
            )
            for eid in newly_eliminated:
                placements[eid] = BracketPlacement(
                    engine_id=eid,
                    placement=len(self.engines) - len(eliminated),
                    elimination_round=round_name,
                )
            eliminated.extend(newly_eliminated)
            all_matches.extend(round_matches)
            state["matches"] = [asdict(m) for m in all_matches]
            self._save_state(state)

        losers_champion = losers[0] if losers else None

        # ---- Grand final --------------------------------------------- #
        if winners_champion and losers_champion:
            gf_match = self._play_match(
                winners_champion, losers_champion,
                "grand_final", engine_map, completed_match_ids
            )
            all_matches.append(gf_match)
            state["matches"] = [asdict(m) for m in all_matches]
            self._save_state(state)

            if gf_match.winner == losers_champion and self.bracket_reset:
                # Reset: losers champ won; play one more game
                reset_match = self._play_match(
                    winners_champion, losers_champion,
                    "grand_final_reset", engine_map, completed_match_ids
                )
                all_matches.append(reset_match)
                ultimate_winner = reset_match.winner or winners_champion
            else:
                ultimate_winner = gf_match.winner or winners_champion

            placements[ultimate_winner] = BracketPlacement(
                engine_id=ultimate_winner, placement=1
            )
            runner_up = (
                losers_champion if ultimate_winner == winners_champion
                else winners_champion
            )
            placements[runner_up] = BracketPlacement(
                engine_id=runner_up, placement=2
            )

        # Fill remaining placements
        for rank, eid in enumerate(reversed(eliminated), start=3):
            if eid not in placements:
                placements[eid] = BracketPlacement(engine_id=eid, placement=rank)

        sorted_placements = sorted(placements.values(), key=lambda p: p.placement)
        state["placements"] = [asdict(p) for p in sorted_placements]
        state["status"] = "completed"
        state["matches"] = [asdict(m) for m in all_matches]
        self._save_state(state)

        self._print_placements(sorted_placements)
        return DoubleElimResult(**state)

    # ------------------------------------------------------------------ #
    #  Bracket round helpers                                               #
    # ------------------------------------------------------------------ #

    def _play_bracket_round(
        self,
        participants: List[str],
        round_name: str,
        engine_map: Dict[str, EngineConfig],
        completed: set,
    ) -> Tuple[List[str], List[str], List[MatchResult]]:
        """Play one round; return (winners, losers/eliminated, matches)."""
        winners: List[str] = []
        losers: List[str] = []
        matches: List[MatchResult] = []

        pairs = list(zip(participants[::2], participants[1::2]))
        if len(participants) % 2 == 1:
            # Bye — last participant advances automatically
            winners.append(participants[-1])

        for a, b in pairs:
            match = self._play_match(a, b, round_name, engine_map, completed)
            matches.append(match)
            if match.winner == a:
                winners.append(a)
                losers.append(b)
            else:
                winners.append(b)
                losers.append(a)

        return winners, losers, matches

    def _play_match(
        self,
        engine_a_id: str,
        engine_b_id: str,
        round_name: str,
        engine_map: Dict[str, EngineConfig],
        completed: set,
    ) -> MatchResult:
        match_id = f"{self.tournament_id}_{round_name}_{engine_a_id}_vs_{engine_b_id}"
        if match_id in completed:
            # Reconstruct from state (for resume)
            return MatchResult(
                match_id=match_id,
                round_name=round_name,
                engine_a=engine_a_id,
                engine_b=engine_b_id,
                winner=None,  # will be filled in later from state
                score_a=0,
                score_b=0,
            )

        cfg_a = engine_map[engine_a_id]
        cfg_b = engine_map[engine_b_id]
        score_a = 0.0
        score_b = 0.0
        games: List[dict] = []

        for g in range(self.games_per_match):
            white_cfg = cfg_a if g % 2 == 0 else cfg_b
            black_cfg = cfg_b if g % 2 == 0 else cfg_a
            game_id = f"{match_id}_g{g}"

            print(f"    {white_cfg.engine_id} (W) vs {black_cfg.engine_id} (B) [{round_name}]")
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
                print(f"      ERROR: {exc}")
                continue

            games.append(record.to_dict())
            # Accumulate scores relative to engine_a
            if record.result == "1-0":
                if white_cfg.engine_id == engine_a_id:
                    score_a += 1
                else:
                    score_b += 1
            elif record.result == "0-1":
                if black_cfg.engine_id == engine_a_id:
                    score_a += 1
                else:
                    score_b += 1
            else:
                score_a += 0.5
                score_b += 0.5

        # Determine winner; tiebreak goes to engine_a (seeding advantage)
        tiebreak = False
        if score_a > score_b:
            winner = engine_a_id
        elif score_b > score_a:
            winner = engine_b_id
        else:
            # Tiebreak: play one blitz game with engine_b as white
            print(f"    TIEBREAK: {engine_b_id} (W) vs {engine_a_id} (B)")
            tb_runner = GameRunner(
                cfg_b, cfg_a, self.tc,
                tournament_id=self.tournament_id,
                game_id=f"{match_id}_tb",
                pgn_dir=str(self.pgn_dir),
                results_dir=str(self.pgn_dir),
            )
            try:
                tb = tb_runner.run()
                games.append(tb.to_dict())
                if tb.result == "1-0":
                    winner = engine_b_id
                elif tb.result == "0-1":
                    winner = engine_a_id
                else:
                    winner = engine_a_id  # seeding tiebreak
            except Exception:
                winner = engine_a_id
            tiebreak = True

        return MatchResult(
            match_id=match_id,
            round_name=round_name,
            engine_a=engine_a_id,
            engine_b=engine_b_id,
            winner=winner,
            score_a=score_a,
            score_b=score_b,
            games=games,
            tiebreak_used=tiebreak,
        )

    # ------------------------------------------------------------------ #
    #  State persistence                                                   #
    # ------------------------------------------------------------------ #

    def _load_state(self) -> dict:
        if self._results_path.exists():
            with open(self._results_path) as f:
                return json.load(f)
        return {
            "tournament_id": self.tournament_id,
            "type": "double_elimination",
            "engines": [e.engine_id for e in self.engines],
            "status": "in_progress",
            "matches": [],
            "placements": [],
        }

    def _save_state(self, state: dict) -> None:
        with open(self._results_path, "w") as f:
            json.dump(state, f, indent=2)

    # ------------------------------------------------------------------ #
    #  Display                                                             #
    # ------------------------------------------------------------------ #

    def _print_placements(self, placements: List[BracketPlacement]) -> None:
        print(f"\n{'='*50}")
        print(f"Double-Elimination Placements — {self.tournament_id}")
        print(f"{'='*50}")
        for p in placements:
            print(f"  #{p.placement:<3} {p.engine_id}")
        print()
