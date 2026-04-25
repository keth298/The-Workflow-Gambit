"""
Game Runner — orchestrates a single chess game between two UCI engines.

Produces:
- A PGN file
- A JSON metadata file matching PRD section 8.2 data model
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import chess
import chess.pgn

from evaluator.engine_registry import EngineConfig
from evaluator.uci_runner import MoveResult, UCIEngine


class Termination(str, Enum):
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    INSUFFICIENT_MATERIAL = "insufficient_material"
    SEVENTYFIVE_MOVES = "seventyfive_moves"
    FIVEFOLD_REPETITION = "fivefold_repetition"
    FIFTY_MOVES = "fifty_moves"
    THREEFOLD_REPETITION = "threefold_repetition"
    MAX_PLY = "max_ply"
    ILLEGAL_MOVE = "illegal_move"
    TIMEOUT = "timeout"
    CRASH = "crash"
    NO_MOVE = "no_move"
    UNKNOWN = "unknown"


class GameResult(str, Enum):
    WHITE_WIN = "1-0"
    BLACK_WIN = "0-1"
    DRAW = "1/2-1/2"
    WHITE_FORFEIT = "0-1"   # white forfeited
    BLACK_FORFEIT = "1-0"   # black forfeited


@dataclass
class TimeControl:
    base_seconds: float = 30.0
    increment_seconds: float = 0.5
    max_move_seconds: float = 5.0

    @classmethod
    def from_dict(cls, d: dict) -> "TimeControl":
        return cls(
            base_seconds=d.get("base_seconds", 30.0),
            increment_seconds=d.get("increment_seconds", 0.5),
            max_move_seconds=d.get("max_move_seconds", 5.0),
        )


@dataclass
class GameRecord:
    game_id: str
    tournament_id: str
    white_engine_id: str
    black_engine_id: str
    start_fen: str
    result: str                    # "1-0" / "0-1" / "1/2-1/2"
    termination: str
    plies: int
    white_illegal_moves: int
    black_illegal_moves: int
    white_time_ms_total: float
    black_time_ms_total: float
    white_avg_move_ms: float
    black_avg_move_ms: float
    move_times_ms: List[float] = field(default_factory=list)
    pgn_path: str = ""
    metadata_path: str = ""
    error_log: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class GameRunner:
    """
    Runs a single chess game between two EngineConfig instances.

    Parameters
    ----------
    white_config, black_config:
        Engine configurations for white and black.
    time_control:
        TimeControl instance.
    tournament_id:
        ID of the parent tournament (for output filenames / metadata).
    start_fen:
        Starting position FEN; defaults to the standard starting position.
    game_id:
        If None, a UUID is generated.
    pgn_dir:
        Directory to write the PGN.
    results_dir:
        Directory to write the JSON metadata.
    max_ply:
        Hard limit on game length to prevent infinite games.
    """

    def __init__(
        self,
        white_config: EngineConfig,
        black_config: EngineConfig,
        time_control: TimeControl,
        tournament_id: str = "standalone",
        start_fen: str = chess.STARTING_FEN,
        game_id: Optional[str] = None,
        pgn_dir: str = "results/games",
        results_dir: str = "results/games",
        max_ply: int = 500,
    ):
        self.white_config = white_config
        self.black_config = black_config
        self.tc = time_control
        self.tournament_id = tournament_id
        self.start_fen = start_fen
        self.game_id = game_id or f"game_{uuid.uuid4().hex[:8]}"
        self.pgn_dir = Path(pgn_dir)
        self.results_dir = Path(results_dir)
        self.max_ply = max_ply

    def run(self) -> GameRecord:
        """Execute the game and return the completed GameRecord."""
        self.pgn_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        board = chess.Board(self.start_fen)
        game = chess.pgn.Game()
        game.headers["Event"] = self.tournament_id
        game.headers["White"] = self.white_config.engine_name
        game.headers["Black"] = self.black_config.engine_name
        game.headers["Date"] = time.strftime("%Y.%m.%d")
        if self.start_fen != chess.STARTING_FEN:
            game.headers["FEN"] = self.start_fen
            game.headers["SetUp"] = "1"
        node = game

        white_time_left_ms = self.tc.base_seconds * 1000
        black_time_left_ms = self.tc.base_seconds * 1000
        white_illegal = 0
        black_illegal = 0
        move_times: List[float] = []
        white_move_times: List[float] = []
        black_move_times: List[float] = []
        error_log: List[str] = []

        result = GameResult.DRAW
        termination = Termination.UNKNOWN

        with UCIEngine(self.white_config, move_timeout_s=self.tc.max_move_seconds + 2) as w_engine, \
             UCIEngine(self.black_config, move_timeout_s=self.tc.max_move_seconds + 2) as b_engine:

            w_engine.new_game()
            b_engine.new_game()

            while not board.is_game_over() and board.fullmove_number * 2 <= self.max_ply:
                is_white_turn = board.turn == chess.WHITE
                active_engine = w_engine if is_white_turn else b_engine
                active_id = self.white_config.engine_id if is_white_turn else self.black_config.engine_id
                time_left_ms = int(white_time_left_ms if is_white_turn else black_time_left_ms)
                increment_ms = int(self.tc.increment_seconds * 1000)

                resp = active_engine.get_move(
                    board,
                    time_left_ms=time_left_ms,
                    increment_ms=increment_ms,
                    max_move_ms=int(self.tc.max_move_seconds * 1000),
                )
                move_times.append(resp.elapsed_ms)

                if is_white_turn:
                    white_move_times.append(resp.elapsed_ms)
                    white_time_left_ms = max(
                        0, white_time_left_ms - resp.elapsed_ms + increment_ms
                    )
                else:
                    black_move_times.append(resp.elapsed_ms)
                    black_time_left_ms = max(
                        0, black_time_left_ms - resp.elapsed_ms + increment_ms
                    )

                if resp.result == MoveResult.OK:
                    board.push(resp.move)
                    node = node.add_variation(resp.move)
                elif resp.result == MoveResult.ILLEGAL:
                    if is_white_turn:
                        white_illegal += 1
                        result = GameResult.BLACK_WIN
                    else:
                        black_illegal += 1
                        result = GameResult.WHITE_WIN
                    termination = Termination.ILLEGAL_MOVE
                    msg = f"Illegal move by {active_id}: {resp.error}"
                    error_log.append(msg)
                    break
                elif resp.result == MoveResult.TIMEOUT:
                    result = GameResult.BLACK_WIN if is_white_turn else GameResult.WHITE_WIN
                    termination = Termination.TIMEOUT
                    error_log.append(f"Timeout by {active_id}")
                    break
                elif resp.result == MoveResult.CRASH:
                    result = GameResult.BLACK_WIN if is_white_turn else GameResult.WHITE_WIN
                    termination = Termination.CRASH
                    error_log.append(f"Crash by {active_id}: {resp.error}")
                    break
                elif resp.result == MoveResult.NO_MOVE:
                    result = GameResult.BLACK_WIN if is_white_turn else GameResult.WHITE_WIN
                    termination = Termination.NO_MOVE
                    error_log.append(f"No move from {active_id}: {resp.error}")
                    break

            else:
                # Determine result from board state
                outcome = board.outcome()
                if outcome:
                    termination = _map_termination(outcome.termination)
                    if outcome.winner == chess.WHITE:
                        result = GameResult.WHITE_WIN
                    elif outcome.winner == chess.BLACK:
                        result = GameResult.BLACK_WIN
                    else:
                        result = GameResult.DRAW
                elif board.fullmove_number * 2 > self.max_ply:
                    termination = Termination.MAX_PLY
                    result = GameResult.DRAW

        # Finalise PGN
        game.headers["Result"] = result.value
        pgn_path = self.pgn_dir / f"{self.game_id}.pgn"
        with open(pgn_path, "w") as f:
            print(game, file=f, end="\n\n")

        white_total = sum(white_move_times)
        black_total = sum(black_move_times)
        record = GameRecord(
            game_id=self.game_id,
            tournament_id=self.tournament_id,
            white_engine_id=self.white_config.engine_id,
            black_engine_id=self.black_config.engine_id,
            start_fen=self.start_fen,
            result=result.value,
            termination=termination.value,
            plies=len(board.move_stack),
            white_illegal_moves=white_illegal,
            black_illegal_moves=black_illegal,
            white_time_ms_total=white_total,
            black_time_ms_total=black_total,
            white_avg_move_ms=white_total / len(white_move_times) if white_move_times else 0,
            black_avg_move_ms=black_total / len(black_move_times) if black_move_times else 0,
            move_times_ms=move_times,
            pgn_path=str(pgn_path),
            metadata_path=str(self.results_dir / f"{self.game_id}.json"),
            error_log=error_log,
        )

        meta_path = self.results_dir / f"{self.game_id}.json"
        with open(meta_path, "w") as f:
            json.dump(record.to_dict(), f, indent=2)

        return record


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _map_termination(t: chess.Termination) -> Termination:
    mapping: Dict[chess.Termination, Termination] = {
        chess.Termination.CHECKMATE: Termination.CHECKMATE,
        chess.Termination.STALEMATE: Termination.STALEMATE,
        chess.Termination.INSUFFICIENT_MATERIAL: Termination.INSUFFICIENT_MATERIAL,
        chess.Termination.SEVENTYFIVE_MOVES: Termination.SEVENTYFIVE_MOVES,
        chess.Termination.FIVEFOLD_REPETITION: Termination.FIVEFOLD_REPETITION,
        chess.Termination.FIFTY_MOVES: Termination.FIFTY_MOVES,
        chess.Termination.THREEFOLD_REPETITION: Termination.THREEFOLD_REPETITION,
        chess.Termination.VARIANT_WIN: Termination.UNKNOWN,
        chess.Termination.VARIANT_LOSS: Termination.UNKNOWN,
        chess.Termination.VARIANT_DRAW: Termination.UNKNOWN,
    }
    return mapping.get(t, Termination.UNKNOWN)
