import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from builder_agent import BuilderAgent
from code_patcher import PATCHABLE_FILES, apply_patches, restore_snapshot, snapshot_engine_code
from communication import AttackReport, Weakness
from engine_tester import EngineTester
from syntax_validator import validate_no_forbidden_imports, validate_patch, validate_python


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
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(self.text)


class _FakeClient:
    def __init__(self, text: str):
        self.messages = _FakeMessages(text)


def _mock_report() -> AttackReport:
    return AttackReport(
        iteration=2,
        timestamp="2026-04-25T12:00:00",
        engine_version="engine.py",
        total_tests=10,
        pass_count=7,
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
            )
        ],
        summary="Evaluation is too shallow in simple endgames.",
        overall_confidence=0.81,
    )


def _engine_source() -> dict[str, str]:
    return {
        filename: (ROOT / filename).read_text(encoding="utf-8")
        for filename in PATCHABLE_FILES
    }


def _copy_engine(tmp_path: Path) -> None:
    for filename in ["engine.py", "search.py", "evaluation.py", "time_manager.py", "transposition_table.py"]:
        (tmp_path / filename).write_text((ROOT / filename).read_text(encoding="utf-8"), encoding="utf-8")


def test_builder_agent_patch_returns_valid_python():
    patched_eval = """import chess

MATERIAL = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}


def evaluate(board: chess.Board) -> int:
    if board.is_checkmate():
        return -20000 if board.turn == chess.WHITE else 20000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    for piece_type, value in MATERIAL.items():
        score += len(board.pieces(piece_type, chess.WHITE)) * value
        score -= len(board.pieces(piece_type, chess.BLACK)) * value
    score += len(list(board.legal_moves))
    return score
"""
    fake_client = _FakeClient(
        json.dumps(
            {
                "files_modified": ["evaluation.py"],
                "code_changes": {"evaluation.py": patched_eval},
                "changes_summary": "Added a basic mobility bonus.",
                "reason": "Addresses eval_error weaknesses in quiet positions.",
                "confidence": 0.74,
            }
        )
    )
    agent = BuilderAgent(api_key="test-key", client=fake_client)

    patch = agent.patch(_mock_report(), _engine_source(), iteration=3)

    assert patch.iteration == 3
    assert patch.files_modified == ["evaluation.py"]
    assert patch.code_changes["evaluation.py"] == patched_eval
    assert patch.confidence == 0.74

    is_valid, message = validate_patch("evaluation.py", patch.code_changes["evaluation.py"])
    assert is_valid, message

    prompt = fake_client.messages.calls[0]["messages"][0]["content"]
    assert "Attack report (iteration 3)" in prompt
    assert "Evaluation is too shallow in simple endgames." in prompt


def test_builder_agent_rejects_forbidden_imports():
    fake_client = _FakeClient(
        json.dumps(
            {
                "files_modified": ["evaluation.py"],
                "code_changes": {
                    "evaluation.py": "import LLMPlayer\n",
                },
                "changes_summary": "Bad patch",
                "reason": "Should fail validation",
                "confidence": 0.1,
            }
        )
    )
    agent = BuilderAgent(api_key="test-key", client=fake_client)

    try:
        agent.patch(_mock_report(), _engine_source(), iteration=4)
    except ValueError as exc:
        assert "forbidden module" in str(exc)
    else:
        raise AssertionError("expected forbidden import validation to fail")


def test_code_patcher_apply_and_restore_snapshot(tmp_path):
    _copy_engine(tmp_path)
    snapshot = snapshot_engine_code(str(tmp_path))

    patched_eval = snapshot["evaluation.py"] + "\n"
    apply_patches(str(tmp_path), {"evaluation.py": patched_eval})

    tester = EngineTester(str(tmp_path / "engine.py"))
    assert tester.check_uci_compliance()

    restore_snapshot(str(tmp_path), snapshot)
    assert snapshot_engine_code(str(tmp_path)) == snapshot


def test_syntax_validator_reports_results():
    assert validate_python("def ok():\n    return 1\n") == (True, "")

    is_valid, message = validate_python("def broken(:\n    pass\n")
    assert not is_valid
    assert "syntax error:" in message

    is_valid, message = validate_no_forbidden_imports("from LLMPlayer.engine import run\n")
    assert not is_valid
    assert "forbidden module" in message
