"""Unit tests for UCI Runner — parsing, handshake, move responses."""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import chess
import pytest

from evaluator.engine_registry import EngineConfig
from evaluator.uci_runner import MoveResult, UCIEngine


DUMMY_DIR = Path(__file__).parent / "dummy_engines"

RANDOM_ENGINE_CMD = f"{sys.executable} {DUMMY_DIR / 'random_engine.py'}"
FIRST_ENGINE_CMD = f"{sys.executable} {DUMMY_DIR / 'first_move_engine.py'}"
ILLEGAL_ENGINE_CMD = f"{sys.executable} {DUMMY_DIR / 'illegal_engine.py'}"
TIMEOUT_ENGINE_CMD = f"{sys.executable} {DUMMY_DIR / 'timeout_engine.py'}"


def _make_config(cmd: str, eid: str = "test") -> EngineConfig:
    return EngineConfig(
        engine_id=eid,
        engine_name="Test",
        strategy_name="Test",
        owner="tester",
        uci_command=cmd,
        language="Python",
    )


# ------------------------------------------------------------------ #
#  Health check                                                         #
# ------------------------------------------------------------------ #

def test_health_check_random_engine():
    config = _make_config(RANDOM_ENGINE_CMD)
    ok, msg = config.health_check(timeout=5.0)
    assert ok, f"Health check failed: {msg}"


def test_health_check_bad_command():
    config = _make_config("nonexistent_binary_xyz")
    ok, msg = config.health_check(timeout=2.0)
    assert not ok


# ------------------------------------------------------------------ #
#  UCI handshake and lifecycle                                          #
# ------------------------------------------------------------------ #

def test_start_stop():
    config = _make_config(RANDOM_ENGINE_CMD)
    engine = UCIEngine(config)
    engine.start()
    assert engine.is_alive
    engine.stop()
    assert not engine.is_alive


def test_context_manager():
    config = _make_config(RANDOM_ENGINE_CMD)
    with UCIEngine(config) as engine:
        assert engine.is_alive
    assert not engine.is_alive


# ------------------------------------------------------------------ #
#  Move requests                                                       #
# ------------------------------------------------------------------ #

def test_random_engine_returns_legal_move():
    config = _make_config(RANDOM_ENGINE_CMD)
    board = chess.Board()
    with UCIEngine(config) as engine:
        engine.new_game()
        resp = engine.get_move(board, time_left_ms=5000, increment_ms=100)
    assert resp.result == MoveResult.OK
    assert resp.move is not None
    assert resp.elapsed_ms >= 0


def test_first_engine_deterministic():
    config = _make_config(FIRST_ENGINE_CMD)
    board = chess.Board()
    moves = []
    for _ in range(3):
        with UCIEngine(config) as engine:
            engine.new_game()
            resp = engine.get_move(board, time_left_ms=5000, increment_ms=100)
            assert resp.result == MoveResult.OK
            moves.append(resp.move.uci())
    # Same starting position → same first move
    assert len(set(moves)) == 1


def test_illegal_engine_returns_illegal():
    config = _make_config(ILLEGAL_ENGINE_CMD)
    board = chess.Board()
    with UCIEngine(config, move_timeout_s=3.0) as engine:
        engine.new_game()
        resp = engine.get_move(board, time_left_ms=5000, increment_ms=100)
    assert resp.result == MoveResult.ILLEGAL


def test_timeout_engine_returns_timeout():
    config = _make_config(TIMEOUT_ENGINE_CMD)
    board = chess.Board()
    with UCIEngine(config, move_timeout_s=1.0) as engine:
        engine.new_game()
        resp = engine.get_move(
            board, time_left_ms=500, increment_ms=0, max_move_ms=500
        )
    assert resp.result == MoveResult.TIMEOUT


# ------------------------------------------------------------------ #
#  Multi-move sequence                                                  #
# ------------------------------------------------------------------ #

def test_multi_move_sequence():
    """Engine can play 10 moves from an evolving board."""
    config = _make_config(RANDOM_ENGINE_CMD)
    board = chess.Board()
    with UCIEngine(config) as engine:
        engine.new_game()
        for _ in range(10):
            if board.is_game_over():
                break
            resp = engine.get_move(board, time_left_ms=10000, increment_ms=100)
            assert resp.result == MoveResult.OK
            board.push(resp.move)
    assert len(board.move_stack) >= 1
