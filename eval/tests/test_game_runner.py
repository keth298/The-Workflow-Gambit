"""Unit and integration tests for GameRunner."""

import json
import sys
from pathlib import Path

import chess
import pytest

from evaluator.engine_registry import EngineConfig
from evaluator.game_runner import GameRunner, TimeControl, Termination


DUMMY_DIR = Path(__file__).parent / "dummy_engines"
RANDOM_CMD = f"{sys.executable} {DUMMY_DIR / 'random_engine.py'}"
FIRST_CMD = f"{sys.executable} {DUMMY_DIR / 'first_move_engine.py'}"
ILLEGAL_CMD = f"{sys.executable} {DUMMY_DIR / 'illegal_engine.py'}"


def _config(cmd, eid, name="Dummy"):
    return EngineConfig(
        engine_id=eid, engine_name=name, strategy_name="test",
        owner="tester", uci_command=cmd, language="Python",
    )


def _fast_tc():
    return TimeControl(base_seconds=30, increment_seconds=0.5,
                       max_move_seconds=5)


# ------------------------------------------------------------------ #
#  Basic game completion                                               #
# ------------------------------------------------------------------ #

def test_game_completes(tmp_path):
    """Two random engines should produce a valid game record."""
    w = _config(RANDOM_CMD, "white_r")
    b = _config(RANDOM_CMD, "black_r")
    runner = GameRunner(
        w, b, _fast_tc(),
        pgn_dir=str(tmp_path / "games"),
        results_dir=str(tmp_path / "games"),
        max_ply=60,
    )
    record = runner.run()
    assert record.result in ("1-0", "0-1", "1/2-1/2")
    assert record.plies >= 0


def test_pgn_file_created(tmp_path):
    w = _config(RANDOM_CMD, "wp")
    b = _config(RANDOM_CMD, "bp")
    runner = GameRunner(
        w, b, _fast_tc(),
        pgn_dir=str(tmp_path / "pgns"),
        results_dir=str(tmp_path / "games"),
        max_ply=20,
    )
    record = runner.run()
    assert Path(record.pgn_path).exists()
    content = Path(record.pgn_path).read_text()
    assert "[White" in content
    assert "[Result" in content


def test_json_metadata_created(tmp_path):
    w = _config(RANDOM_CMD, "wm")
    b = _config(RANDOM_CMD, "bm")
    runner = GameRunner(
        w, b, _fast_tc(),
        pgn_dir=str(tmp_path),
        results_dir=str(tmp_path),
        max_ply=20,
    )
    record = runner.run()
    meta = json.loads(Path(record.metadata_path).read_text())
    assert meta["white_engine_id"] == "wm"
    assert meta["black_engine_id"] == "bm"
    assert "result" in meta


# ------------------------------------------------------------------ #
#  Forfeit scenarios                                                   #
# ------------------------------------------------------------------ #

def test_illegal_white_forfeits(tmp_path):
    w = _config(ILLEGAL_CMD, "ill_w")
    b = _config(RANDOM_CMD, "rand_b")
    runner = GameRunner(
        w, b, _fast_tc(),
        pgn_dir=str(tmp_path),
        results_dir=str(tmp_path),
        max_ply=200,
    )
    record = runner.run()
    assert record.result == "0-1"
    assert record.termination == Termination.ILLEGAL_MOVE.value
    assert record.white_illegal_moves == 1


def test_illegal_black_forfeits(tmp_path):
    w = _config(RANDOM_CMD, "rand_w2")
    b = _config(ILLEGAL_CMD, "ill_b")
    runner = GameRunner(
        w, b, _fast_tc(),
        pgn_dir=str(tmp_path),
        results_dir=str(tmp_path),
        max_ply=200,
    )
    record = runner.run()
    assert record.result == "1-0"
    assert record.black_illegal_moves == 1


# ------------------------------------------------------------------ #
#  Timing fields                                                       #
# ------------------------------------------------------------------ #

def test_timing_fields_populated(tmp_path):
    w = _config(FIRST_CMD, "ft_w")
    b = _config(FIRST_CMD, "ft_b")
    runner = GameRunner(
        w, b, _fast_tc(),
        pgn_dir=str(tmp_path),
        results_dir=str(tmp_path),
        max_ply=10,
    )
    record = runner.run()
    assert record.white_time_ms_total >= 0
    assert record.black_time_ms_total >= 0
    assert len(record.move_times_ms) == record.plies
