from dataclasses import dataclass, field


@dataclass
class Weakness:
    position_fen: str
    weakness_type: str       # "tactical" | "positional" | "time" | "eval_error"
    description: str
    engine_move: str         # UCI
    best_move: str           # UCI, empty if unknown
    depth_needed: int
    confidence: float        # 0.0–1.0


@dataclass
class AttackReport:
    iteration: int
    timestamp: str
    engine_version: str
    total_tests: int
    pass_count: int
    fail_count: int
    weaknesses: list[Weakness]
    summary: str
    overall_confidence: float


@dataclass
class BuilderPatch:
    iteration: int
    timestamp: str
    files_modified: list[str]
    code_changes: dict[str, str]   # filename -> full new source
    changes_summary: str
    reason: str
    confidence: float
