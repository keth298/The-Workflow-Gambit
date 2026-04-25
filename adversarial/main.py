#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from orchestrator import AdversarialOrchestrator


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--threshold", type=float, default=0.02)
    parser.add_argument("--verbose", action="store_true")
    return parser


def _format_iteration(record) -> list[str]:
    report = record.attack_report or {}
    patch = record.builder_patch or {}
    lines = []

    if report:
        lines.append(
            f"[Iteration {record.iteration + 1}] Attack: "
            f"{report.get('fail_count', 0)}/{report.get('total_tests', 0)} tests failed. "
            f"Weaknesses: {len(report.get('weaknesses', []))} "
            f"(confidence {report.get('overall_confidence', 0.0):.2f})"
        )

    if patch:
        files = ", ".join(patch.get("files_modified", [])) or "none"
        lines.append(
            f"[Iteration {record.iteration + 1}] Build: patching {files} "
            f"(confidence {patch.get('confidence', 0.0):.2f})"
        )

    if record.score_before is not None or record.score_after is not None:
        before = "n/a" if record.score_before is None else f"{record.score_before:.2f}"
        after = "n/a" if record.score_after is None else f"{record.score_after:.2f}"
        delta = f"{record.improvement:+.2f}"
        lines.append(
            f"[Iteration {record.iteration + 1}] Benchmark: {before} -> {after} ({delta}) "
            f"- {record.status.upper()}"
        )
    else:
        lines.append(
            f"[Iteration {record.iteration + 1}] Status: {record.status.upper()} ({record.reason})"
        )

    return lines


def _format_score(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def _format_delta(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:+.2f}"


def _short_fingerprint(value: str) -> str:
    return value[:12] if value else "n/a"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY must be set.", file=sys.stderr)
        return 1

    engine_dir = Path(__file__).resolve().parent
    orchestrator = AdversarialOrchestrator(
        engine_dir=str(engine_dir),
        api_key=api_key,
        improvement_threshold=args.threshold,
    )
    records = orchestrator.run_loop(max_iterations=args.iterations)
    summary = orchestrator.tracker.write_performance_summary(
        str(engine_dir / "performance_summary.json")
    )

    if args.verbose:
        for record in records:
            for line in _format_iteration(record):
                print(line)

    print(f"Baseline benchmark score: {_format_score(summary.baseline_score)}")
    print(f"Final benchmark score: {_format_score(summary.final_score)}")
    print(f"Net benchmark change: {_format_delta(summary.net_improvement)}")
    print(
        f"Best benchmark score: {_format_score(summary.best_score)} "
        f"({summary.best_stage})"
    )
    print(
        f"Engine fingerprint: {_short_fingerprint(summary.baseline_fingerprint)} "
        f"-> {_short_fingerprint(summary.final_fingerprint)}"
    )
    print(f"Performance summary saved to {engine_dir / 'performance_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
