from __future__ import annotations

import chess

from time_manager import TimeBudget


def test_movetime_allocation_and_stop(monkeypatch) -> None:
    now = 100.0

    def fake_monotonic() -> float:
        return now

    monkeypatch.setattr("time_manager.time.monotonic", fake_monotonic)

    budget = TimeBudget(turn=chess.WHITE, movetime_ms=500)
    assert budget.allocated_ms() == 480

    budget.start()
    assert not budget.should_stop()

    now += 0.479
    assert not budget.should_stop()

    now += 0.001
    assert budget.should_stop()


def test_depth_only_mode_never_times_out(monkeypatch) -> None:
    now = 50.0

    def fake_monotonic() -> float:
        return now

    monkeypatch.setattr("time_manager.time.monotonic", fake_monotonic)

    budget = TimeBudget(turn=chess.WHITE, depth_limit=5)
    assert budget.depth_limit() == 5
    assert budget.allocated_ms() == 0

    budget.start()
    assert not budget.should_stop()

    now += 60.0
    assert not budget.should_stop()


def test_clock_allocation_without_increment() -> None:
    budget = TimeBudget(turn=chess.WHITE, wtime_ms=10_000, btime_ms=10_000)
    alloc = budget.allocated_ms()
    assert 100 <= alloc <= 2_000


def test_clock_allocation_with_increment() -> None:
    budget = TimeBudget(
        turn=chess.BLACK,
        wtime_ms=60_000,
        btime_ms=60_000,
        winc_ms=2_000,
        binc_ms=2_000,
    )
    assert budget.allocated_ms() > 1_500


def test_depth_limit_overrides_time_controls() -> None:
    budget = TimeBudget(
        turn=chess.WHITE,
        wtime_ms=30_000,
        btime_ms=30_000,
        movetime_ms=2_000,
        depth_limit=4,
    )
    assert budget.depth_limit() == 4
    assert budget.allocated_ms() == 0


def test_minimum_allocation_is_enforced() -> None:
    budget = TimeBudget(turn=chess.WHITE, movetime_ms=1)
    assert budget.allocated_ms() == 10
