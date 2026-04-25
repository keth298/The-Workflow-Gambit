from __future__ import annotations

import datetime
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Optional

from attacker import Attacker
from attacker_agent import AttackerAgent
from benchmark_positions import BENCHMARK_POSITIONS
from builder_agent import BuilderAgent
from code_patcher import (
    PATCHABLE_FILES,
    apply_patches,
    engine_fingerprint,
    restore_snapshot,
    snapshot_engine_code,
    snapshot_fingerprint,
)
from communication import AttackReport, BuilderPatch
from config import (
    ENGINE_TIMEOUT_S,
    IMPROVEMENT_THRESHOLD,
    MAX_ITERATIONS,
    MIN_ATTACKER_CONFIDENCE,
    MIN_BUILDER_CONFIDENCE,
    STALL_ITERATIONS,
    VALIDATION_DEPTH,
    VALIDATION_POSITIONS,
)
from engine_tester import EngineTester
from iteration_tracker import IterationRecord, IterationTracker
from syntax_validator import validate_patch


class AdversarialOrchestrator:
    def __init__(
        self,
        engine_dir: str,
        api_key: Optional[str] = None,
        attacker: Optional[Attacker] = None,
        attacker_agent: Optional[AttackerAgent] = None,
        builder_agent: Optional[BuilderAgent] = None,
        tracker: Optional[IterationTracker] = None,
        benchmark_positions: Optional[Iterable[dict]] = None,
        improvement_threshold: float = IMPROVEMENT_THRESHOLD,
    ):
        self.engine_dir = Path(engine_dir).resolve()
        self.engine_path = str(self.engine_dir / "engine.py")
        self.snapshot_root = self.engine_dir / "snapshots"
        self.performance_summary_path = self.engine_dir / "performance_summary.json"
        self.snapshot_root.mkdir(parents=True, exist_ok=True)

        self.attacker = attacker or Attacker(self.engine_path)
        self.attacker_agent = attacker_agent or AttackerAgent(api_key=api_key)
        self.builder_agent = builder_agent or BuilderAgent(api_key=api_key)
        self.tracker = tracker or IterationTracker(str(self.engine_dir / "iterations.json"))
        self.benchmark_positions = list(benchmark_positions or BENCHMARK_POSITIONS)
        self.improvement_threshold = improvement_threshold

        self._attacker_stalls = 0
        self._builder_stalls = 0
        self._current_stage = "idle"

    def run_loop(self, max_iterations: int = MAX_ITERATIONS) -> list[IterationRecord]:
        iteration = len(self.tracker.load())
        records: list[IterationRecord] = []

        try:
            while iteration < max_iterations:
                if self.tracker.is_stalled():
                    break
                if self._attacker_stalls >= STALL_ITERATIONS:
                    break
                if self._builder_stalls >= STALL_ITERATIONS:
                    break

                records.append(self.run_iteration(iteration))
                iteration += 1
        except KeyboardInterrupt:
            return records
        finally:
            self.tracker.write_performance_summary(str(self.performance_summary_path))

        return records

    def run_iteration(self, iteration: int) -> IterationRecord:
        timestamp = self._timestamp()
        snapshot = snapshot_engine_code(str(self.engine_dir))
        fingerprint_before = snapshot_fingerprint(snapshot)
        self._persist_snapshot(iteration, snapshot)
        patch_applied = False
        report: Optional[AttackReport] = None
        patch: Optional[BuilderPatch] = None
        score_before: Optional[float] = None
        score_after: Optional[float] = None

        try:
            self._current_stage = "attacker_run"
            raw = self.attacker.run(iteration)
            self._current_stage = "attacker_analyze"
            report = self.attacker_agent.analyze(raw, snapshot)

            if report.overall_confidence < MIN_ATTACKER_CONFIDENCE:
                self._attacker_stalls += 1
                record = self._make_record(
                    iteration=iteration,
                    timestamp=timestamp,
                    attack_report=report,
                    builder_patch=None,
                    score_before=None,
                    score_after=None,
                    improvement=0.0,
                    status="stalled",
                    reason=(
                        f"attacker confidence {report.overall_confidence:.2f} "
                        f"below minimum {MIN_ATTACKER_CONFIDENCE:.2f}"
                    ),
                    engine_fingerprint_before=fingerprint_before,
                    engine_fingerprint_after=fingerprint_before,
                )
                return self._store_record(record)

            self._attacker_stalls = 0
            self._current_stage = "benchmark_before"
            score_before = self._benchmark_score()

            self._current_stage = "builder_patch"
            patch = self.builder_agent.patch(report, snapshot, iteration)
            if patch.confidence < MIN_BUILDER_CONFIDENCE:
                self._builder_stalls += 1
                record = self._make_record(
                    iteration=iteration,
                    timestamp=timestamp,
                    attack_report=report,
                    builder_patch=patch,
                    score_before=score_before,
                    score_after=score_before,
                    improvement=0.0,
                    status="stalled",
                    reason=(
                        f"builder confidence {patch.confidence:.2f} "
                        f"below minimum {MIN_BUILDER_CONFIDENCE:.2f}"
                    ),
                    engine_fingerprint_before=fingerprint_before,
                    engine_fingerprint_after=fingerprint_before,
                )
                return self._store_record(record)

            self._builder_stalls = 0
            for filename, source in patch.code_changes.items():
                is_valid, message = validate_patch(filename, source)
                if not is_valid:
                    raise ValueError(message)

            apply_patches(str(self.engine_dir), patch.code_changes)
            patch_applied = True

            self._current_stage = "uci_validate"
            if not self._engine_still_uci_compliant():
                restore_snapshot(str(self.engine_dir), snapshot)
                record = self._make_record(
                    iteration=iteration,
                    timestamp=timestamp,
                    attack_report=report,
                    builder_patch=patch,
                    score_before=score_before,
                    score_after=None,
                    improvement=0.0,
                    status="rolled_back",
                    reason="patched engine failed UCI compliance",
                    engine_fingerprint_before=fingerprint_before,
                    engine_fingerprint_after=engine_fingerprint(str(self.engine_dir)),
                )
                return self._store_record(record)

            self._current_stage = "benchmark_after"
            score_after = self._benchmark_score()
            improvement = score_after - score_before
            if improvement < 0:
                restore_snapshot(str(self.engine_dir), snapshot)
                record = self._make_record(
                    iteration=iteration,
                    timestamp=timestamp,
                    attack_report=report,
                    builder_patch=patch,
                    score_before=score_before,
                    score_after=score_after,
                    improvement=improvement,
                    status="rolled_back",
                    reason="benchmark regressed after patch; restored previous snapshot",
                    engine_fingerprint_before=fingerprint_before,
                    engine_fingerprint_after=engine_fingerprint(str(self.engine_dir)),
                )
                return self._store_record(record)

            status = "improved" if improvement >= self.improvement_threshold else "stalled"
            reason = (
                f"benchmark improved by {improvement:.2f}"
                if status == "improved"
                else f"benchmark change {improvement:.2f} below threshold {self.improvement_threshold:.2f}"
            )
            record = self._make_record(
                iteration=iteration,
                timestamp=timestamp,
                attack_report=report,
                builder_patch=patch,
                score_before=score_before,
                score_after=score_after,
                improvement=improvement,
                status=status,
                reason=reason,
                engine_fingerprint_before=fingerprint_before,
                engine_fingerprint_after=engine_fingerprint(str(self.engine_dir)),
            )
            return self._store_record(record)
        except Exception as exc:
            if patch_applied:
                restore_snapshot(str(self.engine_dir), snapshot)
            reason = f"{self._current_stage}: {type(exc).__name__}: {exc}"
            record = self._make_record(
                iteration=iteration,
                timestamp=timestamp,
                attack_report=report,
                builder_patch=patch,
                score_before=score_before,
                score_after=score_after,
                improvement=0.0,
                status="error",
                reason=reason,
                engine_fingerprint_before=fingerprint_before,
                engine_fingerprint_after=engine_fingerprint(str(self.engine_dir)),
            )
            return self._store_record(record)
        finally:
            self._current_stage = "idle"

    def _benchmark_score(self) -> float:
        positions = []
        for position in self.benchmark_positions[:VALIDATION_POSITIONS]:
            item = dict(position)
            item["depth"] = item.get("depth", VALIDATION_DEPTH)
            positions.append(item)

        tester = EngineTester(self.engine_path)
        results = tester.run_batch(positions, timeout_s=ENGINE_TIMEOUT_S)
        if not results:
            return 0.0
        correct = sum(1 for result in results if result.passed)
        return correct / len(results)

    def _engine_still_uci_compliant(self) -> bool:
        tester = EngineTester(self.engine_path)
        return tester.check_uci_compliance()

    def _persist_snapshot(self, iteration: int, snapshot: dict[str, str]) -> None:
        snapshot_dir = self.snapshot_root / f"v{iteration}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        for filename in sorted(PATCHABLE_FILES):
            (snapshot_dir / filename).write_text(snapshot[filename], encoding="utf-8")

    def _store_record(self, record: IterationRecord) -> IterationRecord:
        self.tracker.append(record)
        self.tracker.write_performance_summary(str(self.performance_summary_path))
        return record

    @staticmethod
    def _timestamp() -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    @staticmethod
    def _make_record(
        iteration: int,
        timestamp: str,
        attack_report: Optional[AttackReport],
        builder_patch: Optional[BuilderPatch],
        score_before: Optional[float],
        score_after: Optional[float],
        improvement: float,
        status: str,
        reason: str,
        engine_fingerprint_before: str,
        engine_fingerprint_after: str,
    ) -> IterationRecord:
        return IterationRecord(
            iteration=iteration,
            timestamp=timestamp,
            attack_report=asdict(attack_report) if attack_report is not None else {},
            builder_patch=asdict(builder_patch) if builder_patch is not None else {},
            score_before=score_before,
            score_after=score_after,
            improvement=improvement,
            status=status,
            reason=reason,
            engine_fingerprint_before=engine_fingerprint_before,
            engine_fingerprint_after=engine_fingerprint_after,
        )
