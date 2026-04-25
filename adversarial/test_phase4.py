import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from attacker import RawAttackData
from code_patcher import PATCHABLE_FILES
from communication import AttackReport, BuilderPatch, Weakness
from engine_tester import EngineTester, TestResult as EngineTestResult
from iteration_tracker import IterationRecord, IterationTracker
from orchestrator import AdversarialOrchestrator


class FakeAttacker:
    def __init__(self, engine_path: str):
        self.engine_path = engine_path

    def run(self, iteration: int) -> RawAttackData:
        results = [
            EngineTestResult(
                name="fork_knight",
                fen="8/8/8/8/8/8/8/K6k w - - 0 1",
                expected_move="a1a2",
                engine_move="a1a1",
                passed=False,
                depth_searched=3,
                time_ms=5.0,
            )
        ]
        return RawAttackData(
            iteration=iteration,
            engine_path=self.engine_path,
            results=results,
            compliance_ok=True,
            elapsed_s=0.01,
        )


class FakeAttackerAgent:
    def __init__(self, confidence: float = 0.9):
        self.confidence = confidence

    def analyze(self, raw: RawAttackData, engine_source: dict[str, str]) -> AttackReport:
        return AttackReport(
            iteration=raw.iteration,
            timestamp="2026-04-25T12:00:00+00:00",
            engine_version=raw.engine_path,
            total_tests=len(raw.results),
            pass_count=0,
            fail_count=1,
            weaknesses=[
                Weakness(
                    position_fen=raw.results[0].fen,
                    weakness_type="eval_error",
                    description="Baseline evaluation ignores a simple tactic.",
                    engine_move=raw.results[0].engine_move,
                    best_move=raw.results[0].expected_move,
                    depth_needed=3,
                    confidence=self.confidence,
                )
            ],
            summary="One consistent tactical miss.",
            overall_confidence=self.confidence,
        )


class FakeBuilderAgent:
    def __init__(self, confidence: float = 0.9, patch_factory=None):
        self.confidence = confidence
        self.patch_factory = patch_factory

    def patch(
        self,
        report: AttackReport,
        engine_source: dict[str, str],
        iteration: int,
    ) -> BuilderPatch:
        code_changes = self.patch_factory(engine_source) if self.patch_factory else {
            "evaluation.py": engine_source["evaluation.py"] + "\n"
        }
        return BuilderPatch(
            iteration=iteration,
            timestamp="2026-04-25T12:01:00+00:00",
            files_modified=list(code_changes.keys()),
            code_changes=code_changes,
            changes_summary="Test patch",
            reason="Exercise orchestrator flow",
            confidence=self.confidence,
        )


def _copy_engine(tmp_path: Path) -> None:
    for filename in ["engine.py", *sorted(PATCHABLE_FILES)]:
        (tmp_path / filename).write_text((ROOT / filename).read_text(encoding="utf-8"), encoding="utf-8")


def _benchmark_sequence(*values: float):
    iterator = iter(values)
    return lambda: next(iterator)


def test_iteration_tracker_stalls_after_non_improving_iterations(tmp_path):
    tracker = IterationTracker(str(tmp_path / "iterations.json"))
    tracker.append(
        IterationRecord(
            iteration=0,
            timestamp="2026-04-25T12:00:00+00:00",
            improvement=0.0,
            status="stalled",
            reason="no change",
        )
    )
    tracker.append(
        IterationRecord(
            iteration=1,
            timestamp="2026-04-25T12:01:00+00:00",
            improvement=-0.1,
            status="rolled_back",
            reason="regression",
        )
    )

    assert tracker.last_n_improvements(2) == [0.0, -0.1]
    assert tracker.is_stalled()


def test_orchestrator_run_iteration_creates_record_and_snapshot(tmp_path):
    _copy_engine(tmp_path)
    orchestrator = AdversarialOrchestrator(
        engine_dir=str(tmp_path),
        attacker=FakeAttacker(str(tmp_path / "engine.py")),
        attacker_agent=FakeAttackerAgent(),
        builder_agent=FakeBuilderAgent(),
        tracker=IterationTracker(str(tmp_path / "iterations.json")),
    )
    orchestrator._benchmark_score = _benchmark_sequence(0.2, 0.5)

    record = orchestrator.run_iteration(0)

    assert record.status == "improved"
    assert record.improvement == 0.3
    assert (tmp_path / "iterations.json").exists()
    assert (tmp_path / "snapshots" / "v0" / "evaluation.py").exists()
    loaded = orchestrator.tracker.load()
    assert len(loaded) == 1
    assert loaded[0].status == "improved"

    tester = EngineTester(str(tmp_path / "engine.py"))
    assert tester.check_uci_compliance()


def test_orchestrator_rolls_back_on_uci_failure(tmp_path):
    _copy_engine(tmp_path)

    def broken_patch(engine_source: dict[str, str]) -> dict[str, str]:
        return {"evaluation.py": "raise RuntimeError('boom')\n"}

    orchestrator = AdversarialOrchestrator(
        engine_dir=str(tmp_path),
        attacker=FakeAttacker(str(tmp_path / "engine.py")),
        attacker_agent=FakeAttackerAgent(),
        builder_agent=FakeBuilderAgent(patch_factory=broken_patch),
        tracker=IterationTracker(str(tmp_path / "iterations.json")),
    )
    orchestrator._benchmark_score = _benchmark_sequence(0.4)
    original_evaluation = (tmp_path / "evaluation.py").read_text(encoding="utf-8")

    record = orchestrator.run_iteration(0)

    assert record.status == "rolled_back"
    assert "UCI compliance" in record.reason
    assert (tmp_path / "evaluation.py").read_text(encoding="utf-8") == original_evaluation

    tester = EngineTester(str(tmp_path / "engine.py"))
    assert tester.check_uci_compliance()


def test_run_loop_stops_after_two_low_builder_confidence_iterations(tmp_path):
    _copy_engine(tmp_path)
    orchestrator = AdversarialOrchestrator(
        engine_dir=str(tmp_path),
        attacker=FakeAttacker(str(tmp_path / "engine.py")),
        attacker_agent=FakeAttackerAgent(),
        builder_agent=FakeBuilderAgent(confidence=0.1),
        tracker=IterationTracker(str(tmp_path / "iterations.json")),
    )
    orchestrator._benchmark_score = _benchmark_sequence(0.3, 0.3)

    records = orchestrator.run_loop(max_iterations=5)

    assert len(records) == 2
    assert [record.status for record in records] == ["stalled", "stalled"]
    assert len(orchestrator.tracker.load()) == 2
