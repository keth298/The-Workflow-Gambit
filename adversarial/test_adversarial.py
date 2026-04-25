import json
import subprocess
import sys
import time
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from attacker import Attacker, RawAttackData
from builder_agent import BuilderAgent
from code_patcher import PATCHABLE_FILES
from communication import AttackReport, BuilderPatch, Weakness
from engine_tester import EngineTester, TestResult as EngineTestResult
from iteration_tracker import IterationTracker
from orchestrator import AdversarialOrchestrator
from syntax_validator import validate_patch

ENGINE_PATH = ROOT / "engine.py"


class _FakeBlock:
    type = "text"

    def __init__(self, text: str):
        self.text = text


class _FakeResponse:
    def __init__(self, text: str):
        self.content = [_FakeBlock(text)]


class _FakeMessages:
    def __init__(self, text: str):
        self.text = text

    def create(self, **kwargs):
        return _FakeResponse(self.text)


class _FakeClient:
    def __init__(self, text: str):
        self.messages = _FakeMessages(text)


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
                ),
                Weakness(
                    position_fen=raw.results[0].fen,
                    weakness_type="tactical",
                    description="Search is too shallow in forcing lines.",
                    engine_move=raw.results[0].engine_move,
                    best_move=raw.results[0].expected_move,
                    depth_needed=4,
                    confidence=self.confidence,
                ),
            ],
            summary="Two reproducible weaknesses from one failing position.",
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


class ExplodingAttackerAgent:
    def analyze(self, raw: RawAttackData, engine_source: dict[str, str]) -> AttackReport:
        raise RuntimeError("Connection error.")


def _engine_source() -> dict[str, str]:
    return {
        filename: (ROOT / filename).read_text(encoding="utf-8")
        for filename in PATCHABLE_FILES
    }


def _copy_engine(tmp_path: Path) -> None:
    for filename in ["engine.py", *sorted(PATCHABLE_FILES)]:
        (tmp_path / filename).write_text((ROOT / filename).read_text(encoding="utf-8"), encoding="utf-8")


def _benchmark_sequence(*values: float):
    iterator = iter(values)
    return lambda: next(iterator)


def _start_engine():
    return subprocess.Popen(
        ["python3", str(ENGINE_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )


def _send(proc: subprocess.Popen, command: str) -> None:
    assert proc.stdin is not None
    proc.stdin.write(command + "\n")
    proc.stdin.flush()


def _read_until(proc: subprocess.Popen, prefix: str, timeout_s: float = 5.0) -> list[str]:
    assert proc.stdout is not None
    lines = []
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.rstrip()
        lines.append(line)
        if line.startswith(prefix):
            return lines
    return lines


def _mock_report() -> AttackReport:
    return AttackReport(
        iteration=1,
        timestamp="2026-04-25T12:00:00+00:00",
        engine_version=str(ENGINE_PATH),
        total_tests=8,
        pass_count=5,
        fail_count=3,
        weaknesses=[
            Weakness(
                position_fen="8/8/8/8/8/8/8/K6k w - - 0 1",
                weakness_type="eval_error",
                description="Material-only evaluation misses king activity.",
                engine_move="a1a2",
                best_move="a1b2",
                depth_needed=2,
                confidence=0.81,
            ),
            Weakness(
                position_fen="8/8/8/8/8/8/8/K6k w - - 0 1",
                weakness_type="tactical",
                description="Move ordering misses a forcing continuation.",
                engine_move="a1a2",
                best_move="a1b1",
                depth_needed=3,
                confidence=0.75,
            ),
        ],
        summary="Evaluation and search both need work.",
        overall_confidence=0.8,
    )


def test_engine_uci_compliant():
    proc = _start_engine()
    try:
        _send(proc, "uci")
        uci_lines = _read_until(proc, "uciok")
        _send(proc, "isready")
        ready_lines = _read_until(proc, "readyok")
        _send(proc, "quit")

        assert "uciok" in uci_lines
        assert "readyok" in ready_lines
    finally:
        proc.kill()
        proc.wait()


def test_engine_returns_legal_move():
    proc = _start_engine()
    board = chess.Board()
    try:
        _send(proc, "uci")
        _read_until(proc, "uciok")
        _send(proc, "isready")
        _read_until(proc, "readyok")
        _send(proc, "position startpos")
        _send(proc, "go depth 1")
        lines = _read_until(proc, "bestmove")
        _send(proc, "quit")

        bestmove = next(line.split()[1] for line in lines if line.startswith("bestmove"))
        assert bestmove in {move.uci() for move in board.legal_moves}
    finally:
        proc.kill()
        proc.wait()


def test_attacker_finds_weaknesses():
    raw = Attacker(str(ENGINE_PATH), dynamic_positions=4).run(iteration=0)

    assert raw.compliance_ok
    assert len(raw.results) > 0
    assert sum(1 for result in raw.results if not result.passed) >= 3


def test_builder_produces_valid_patch():
    engine_source = _engine_source()
    code_changes = {
        "evaluation.py": engine_source["evaluation.py"] + "\n",
        "search.py": engine_source["search.py"] + "\n",
    }
    fake_client = _FakeClient(
        json.dumps(
            {
                "files_modified": ["evaluation.py", "search.py"],
                "code_changes": code_changes,
                "changes_summary": "Touch evaluation and search.",
                "reason": "Addresses the two reported weaknesses.",
                "confidence": 0.72,
            }
        )
    )
    agent = BuilderAgent(api_key="test-key", client=fake_client)

    patch = agent.patch(_mock_report(), engine_source, iteration=1)

    assert set(patch.code_changes).issubset(PATCHABLE_FILES)
    for filename, source in patch.code_changes.items():
        is_valid, message = validate_patch(filename, source)
        assert is_valid, message


def test_orchestrator_single_iteration(tmp_path):
    _copy_engine(tmp_path)
    orchestrator = AdversarialOrchestrator(
        engine_dir=str(tmp_path),
        attacker=FakeAttacker(str(tmp_path / "engine.py")),
        attacker_agent=FakeAttackerAgent(),
        builder_agent=FakeBuilderAgent(),
        tracker=IterationTracker(str(tmp_path / "iterations.json")),
    )
    orchestrator._benchmark_score = _benchmark_sequence(0.25, 0.45)

    record = orchestrator.run_iteration(0)
    summary = json.loads((tmp_path / "performance_summary.json").read_text(encoding="utf-8"))

    assert record.status == "improved"
    assert (tmp_path / "iterations.json").exists()
    assert (tmp_path / "performance_summary.json").exists()
    assert len(orchestrator.tracker.load()) == 1
    assert summary["baseline_score"] == 0.25
    assert summary["final_score"] == 0.45
    assert summary["best_score"] == 0.45
    assert summary["best_iteration"] == 1
    assert summary["best_stage"] == "iteration 1"
    assert summary["status_counts"] == {"improved": 1}
    assert summary["baseline_fingerprint"] != summary["final_fingerprint"]
    assert summary["iterations"][0]["files_modified"] == ["evaluation.py"]
    assert EngineTester(str(tmp_path / "engine.py")).check_uci_compliance()


def test_loop_terminates_on_max(tmp_path):
    _copy_engine(tmp_path)
    orchestrator = AdversarialOrchestrator(
        engine_dir=str(tmp_path),
        attacker=FakeAttacker(str(tmp_path / "engine.py")),
        attacker_agent=FakeAttackerAgent(),
        builder_agent=FakeBuilderAgent(),
        tracker=IterationTracker(str(tmp_path / "iterations.json")),
    )
    orchestrator._benchmark_score = _benchmark_sequence(0.10, 0.20, 0.20, 0.30)

    records = orchestrator.run_loop(max_iterations=2)

    assert len(records) == 2
    assert len(orchestrator.tracker.load()) == 2


def test_rollback_on_worse_engine(tmp_path):
    _copy_engine(tmp_path)

    def bad_patch(engine_source: dict[str, str]) -> dict[str, str]:
        return {
            "evaluation.py": (
                "import chess\n\n"
                "def evaluate(board: chess.Board) -> int:\n"
                "    return 0\n"
            )
        }

    orchestrator = AdversarialOrchestrator(
        engine_dir=str(tmp_path),
        attacker=FakeAttacker(str(tmp_path / "engine.py")),
        attacker_agent=FakeAttackerAgent(),
        builder_agent=FakeBuilderAgent(patch_factory=bad_patch),
        tracker=IterationTracker(str(tmp_path / "iterations.json")),
    )
    orchestrator._benchmark_score = _benchmark_sequence(0.40, 0.20)
    original_evaluation = (tmp_path / "evaluation.py").read_text(encoding="utf-8")

    record = orchestrator.run_iteration(0)
    summary = json.loads((tmp_path / "performance_summary.json").read_text(encoding="utf-8"))

    assert record.status == "rolled_back"
    assert (
        "regressed" in record.reason
        or "failed UCI compliance" in record.reason
    )
    assert (tmp_path / "evaluation.py").read_text(encoding="utf-8") == original_evaluation
    assert summary["baseline_score"] == 0.40
    assert summary["final_score"] == 0.40
    assert summary["best_score"] == 0.40
    assert summary["best_iteration"] == 0
    assert summary["best_stage"] == "baseline"
    assert summary["baseline_fingerprint"] == summary["final_fingerprint"]
    assert summary["iterations"][0]["effective_score_after"] == 0.40
    assert EngineTester(str(tmp_path / "engine.py")).check_uci_compliance()


def test_orchestrator_records_error_stage(tmp_path):
    _copy_engine(tmp_path)
    orchestrator = AdversarialOrchestrator(
        engine_dir=str(tmp_path),
        attacker=FakeAttacker(str(tmp_path / "engine.py")),
        attacker_agent=ExplodingAttackerAgent(),
        builder_agent=FakeBuilderAgent(),
        tracker=IterationTracker(str(tmp_path / "iterations.json")),
    )

    record = orchestrator.run_iteration(0)

    assert record.status == "error"
    assert record.reason.startswith("attacker_analyze: RuntimeError: Connection error.")
