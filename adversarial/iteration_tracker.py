import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from config import STALL_ITERATIONS


@dataclass
class IterationRecord:
    iteration: int
    timestamp: str
    attack_report: dict = field(default_factory=dict)
    builder_patch: dict = field(default_factory=dict)
    score_before: Optional[float] = None
    score_after: Optional[float] = None
    improvement: float = 0.0
    status: str = "error"
    reason: str = ""
    engine_fingerprint_before: str = ""
    engine_fingerprint_after: str = ""

    def effective_score_after(self) -> Optional[float]:
        if self.status == "rolled_back":
            return self.score_before
        if self.score_after is not None:
            return self.score_after
        return self.score_before

    def files_modified(self) -> list[str]:
        raw_files = self.builder_patch.get("files_modified", [])
        if not isinstance(raw_files, list):
            return []
        return [filename for filename in raw_files if isinstance(filename, str)]


@dataclass
class PerformanceHistoryEntry:
    iteration: int
    status: str
    reason: str
    score_before: Optional[float] = None
    score_after: Optional[float] = None
    effective_score_after: Optional[float] = None
    improvement: float = 0.0
    files_modified: list[str] = field(default_factory=list)
    engine_fingerprint_before: str = ""
    engine_fingerprint_after: str = ""


@dataclass
class PerformanceSummary:
    total_iterations: int = 0
    baseline_score: Optional[float] = None
    final_score: Optional[float] = None
    best_score: Optional[float] = None
    best_iteration: Optional[int] = None
    best_stage: str = "n/a"
    net_improvement: Optional[float] = None
    status_counts: dict[str, int] = field(default_factory=dict)
    baseline_fingerprint: str = ""
    final_fingerprint: str = ""
    iterations: list[PerformanceHistoryEntry] = field(default_factory=list)


class IterationTracker:
    def __init__(self, path: str = "iterations.json"):
        self.path = Path(path)

    def load(self) -> list[IterationRecord]:
        if not self.path.exists():
            return []

        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("iterations.json must contain a JSON list")
        return [IterationRecord(**item) for item in data]

    def append(self, record: IterationRecord) -> None:
        records = self.load()
        records.append(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(item) for item in records]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def performance_summary(self) -> PerformanceSummary:
        records = self.load()
        if not records:
            return PerformanceSummary()

        baseline_score = next(
            (record.score_before for record in records if record.score_before is not None),
            None,
        )
        final_score = records[-1].effective_score_after()

        best_score = baseline_score
        best_iteration = 0 if baseline_score is not None else None
        for record in records:
            effective_score = record.effective_score_after()
            if effective_score is None:
                continue
            if best_score is None or effective_score > best_score:
                best_score = effective_score
                best_iteration = record.iteration + 1

        best_stage = "n/a"
        if best_iteration is not None:
            best_stage = "baseline" if best_iteration == 0 else f"iteration {best_iteration}"

        status_counts: dict[str, int] = {}
        history: list[PerformanceHistoryEntry] = []
        for record in records:
            status_counts[record.status] = status_counts.get(record.status, 0) + 1
            history.append(
                PerformanceHistoryEntry(
                    iteration=record.iteration + 1,
                    status=record.status,
                    reason=record.reason,
                    score_before=record.score_before,
                    score_after=record.score_after,
                    effective_score_after=record.effective_score_after(),
                    improvement=record.improvement,
                    files_modified=record.files_modified(),
                    engine_fingerprint_before=record.engine_fingerprint_before,
                    engine_fingerprint_after=record.engine_fingerprint_after,
                )
            )

        net_improvement = None
        if baseline_score is not None and final_score is not None:
            net_improvement = final_score - baseline_score

        return PerformanceSummary(
            total_iterations=len(records),
            baseline_score=baseline_score,
            final_score=final_score,
            best_score=best_score,
            best_iteration=best_iteration,
            best_stage=best_stage,
            net_improvement=net_improvement,
            status_counts=status_counts,
            baseline_fingerprint=records[0].engine_fingerprint_before,
            final_fingerprint=records[-1].engine_fingerprint_after or records[-1].engine_fingerprint_before,
            iterations=history,
        )

    def write_performance_summary(self, path: Optional[str] = None) -> PerformanceSummary:
        summary = self.performance_summary()
        target = Path(path) if path else self.path.with_name("performance_summary.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
        return summary

    def last_n_improvements(self, n: int) -> list[float]:
        if n <= 0:
            return []
        return [record.improvement for record in self.load()[-n:]]

    def is_stalled(self) -> bool:
        improvements = self.last_n_improvements(STALL_ITERATIONS)
        return len(improvements) == STALL_ITERATIONS and all(value <= 0 for value in improvements)
