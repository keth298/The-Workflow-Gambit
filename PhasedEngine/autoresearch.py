#!/usr/bin/env python3
"""
Autoresearch: iteratively improve the engine via LLM-proposed evaluation changes
validated by self-play matches (challenger vs champion). Keeps improvements, reverts regressions.

Usage:
    python3 autoresearch.py [--iterations N] [--games N] [--threshold F]
    python3 autoresearch.py --report [--validate N]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import anthropic
import chess
import chess.engine
from dotenv import load_dotenv

ENGINE_DIR = Path(__file__).parent.resolve()
load_dotenv(ENGINE_DIR / ".env")
CHAMPION_DIR = ENGINE_DIR / "champion"
BASELINE_DIR = ENGINE_DIR / "baseline"
LOG_FILE = ENGINE_DIR / "autoresearch_log.json"
EVAL_FILE = ENGINE_DIR / "evaluation.py"
GRAPH_FILE = ENGINE_DIR / "autoresearch_progress.png"

SNAPSHOT_FILES = [
    "engine.py",
    "search.py",
    "evaluation.py",
    "time_manager.py",
    "transposition_table.py",
]

DEFAULT_THRESHOLD = 0.55
DEFAULT_GAMES = 20
DEFAULT_ITERATIONS = 20
TIME_PER_MOVE = 0.1  # seconds per move during evaluation games
MAX_GAME_MOVES = 200

# Diverse opening positions to rotate through — reduces symmetric draws
OPENING_FENS = [
    None,  # starting position
    "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",   # Ruy Lopez setup
    "rnbqkb1r/pp2pppp/3p1n2/2p5/3PP3/2N2N2/PPP2PPP/R1BQKB1R b KQkq - 1 4", # Sicilian
    "rnbqkb1r/ppp2ppp/4pn2/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 0 4",   # QGD
    "rnbqk2r/ppppppbp/5np1/8/2PPP3/2N5/PP3PPP/R1BQKBNR b KQkq - 0 5",     # King's Indian
    "rnbqkb1r/pp3ppp/2p1pn2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq - 0 5", # Nimzo/QGD
    "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQK2R b KQkq - 0 6", # Italian
    "rnbq1rk1/ppp1ppbp/3p1np1/8/2PPP3/2N2N2/PP3PPP/R1BQKB1R w KQ - 2 6",  # King's Indian classical
    "r1bqkb1r/pp3ppp/2np1n2/4p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 0 6", # Open Sicilian
    "rnbqr1k1/pp3pbp/2pp1np1/5p2/2PPP3/2N1BN2/PP3PPP/R2QKB1R w KQ - 0 9",  # King's Indian saemisch
    "r1bq1rk1/pp2ppbp/2np1np1/3p4/2PP4/2N1PN2/PP2BPPP/R1BQK2R w KQ - 2 8", # Grunfeld-like
    "r1bqkb1r/ppp2ppp/2np1n2/4p3/4P3/2NP1N2/PPP2PPP/R1BQKB1R b KQkq - 0 5", # Four Knights
]


# ── Champion / baseline management ───────────────────────────────────────────

def _snapshot(dest: Path) -> None:
    dest.mkdir(exist_ok=True)
    for name in SNAPSHOT_FILES:
        src = ENGINE_DIR / name
        if src.exists():
            shutil.copy2(src, dest / name)


def save_champion() -> None:
    _snapshot(CHAMPION_DIR)


def save_baseline() -> None:
    if not BASELINE_DIR.exists():
        _snapshot(BASELINE_DIR)


def champion_eval() -> str:
    return (CHAMPION_DIR / "evaluation.py").read_text()


def current_eval() -> str:
    return EVAL_FILE.read_text()


def apply_eval(code: str) -> None:
    EVAL_FILE.write_text(code)


# ── Validation ────────────────────────────────────────────────────────────────

def syntax_ok(code: str) -> bool:
    try:
        compile(code, "<evaluation.py>", "exec")
        return True
    except SyntaxError as e:
        print(f"  syntax error: {e}", file=sys.stderr, flush=True)
        return False


def engine_ok() -> bool:
    """Start the full engine and verify it completes the UCI handshake."""
    try:
        with chess.engine.SimpleEngine.popen_uci(
            ["python3", "engine.py"],
            cwd=str(ENGINE_DIR),
            stderr=subprocess.DEVNULL,
        ):
            pass
        return True
    except Exception as e:
        print(f"  engine startup failed: {e}", file=sys.stderr, flush=True)
        return False


# ── Self-play match ───────────────────────────────────────────────────────────

DRAW_ABORT_AFTER = 8   # abort if first N games all draw (eval unchanged)
LOSS_ABORT_AFTER = 6   # abort if first N games all lose (eval is harmful)

def play_match(n_games: int) -> tuple[int, int, int]:
    """Play n_games, challenger (ENGINE_DIR) vs champion (CHAMPION_DIR).
    Returns (challenger_wins, draws, champion_wins)."""
    c_wins = draws = c_losses = 0
    try:
        with (
            chess.engine.SimpleEngine.popen_uci(
                ["python3", "engine.py"],
                cwd=str(ENGINE_DIR),
                stderr=subprocess.DEVNULL,
            ) as challenger,
            chess.engine.SimpleEngine.popen_uci(
                ["python3", "engine.py"],
                cwd=str(CHAMPION_DIR),
                stderr=subprocess.DEVNULL,
            ) as champion,
        ):
            limit = chess.engine.Limit(time=TIME_PER_MOVE)
            for i in range(n_games):
                challenger_white = i % 2 == 0
                start_fen = OPENING_FENS[i % len(OPENING_FENS)]
                result = _play_game(challenger, champion, challenger_white, limit, start_fen)
                if result == "challenger":
                    c_wins += 1
                elif result == "champion":
                    c_losses += 1
                else:
                    draws += 1
                total = i + 1
                score = (c_wins + 0.5 * draws) / total
                print(
                    f"  [{i+1:>{len(str(n_games))}}/{n_games}] {result:10s}  "
                    f"W{c_wins}/D{draws}/L{c_losses}  running {score:.0%}",
                    flush=True,
                )
                if total == DRAW_ABORT_AFTER and c_wins == 0 and c_losses == 0:
                    print(
                        f"  all {DRAW_ABORT_AFTER} games drawn — evaluation likely unchanged, aborting match",
                        flush=True,
                    )
                    break
                if total == LOSS_ABORT_AFTER and c_wins == 0 and draws == 0:
                    print(
                        f"  all {LOSS_ABORT_AFTER} games lost — evaluation is harmful, aborting match",
                        flush=True,
                    )
                    break
    except Exception as e:
        print(f"  match error: {e}", file=sys.stderr, flush=True)
    return c_wins, draws, c_losses


def _play_game(
    challenger: chess.engine.SimpleEngine,
    champion: chess.engine.SimpleEngine,
    challenger_white: bool,
    limit: chess.engine.Limit,
    start_fen: str | None = None,
) -> str:
    board = chess.Board(start_fen) if start_fen else chess.Board()
    white_eng = challenger if challenger_white else champion
    black_eng = champion if challenger_white else challenger
    try:
        while not board.is_game_over(claim_draw=True) and board.fullmove_number <= MAX_GAME_MOVES:
            eng = white_eng if board.turn == chess.WHITE else black_eng
            result = eng.play(board, limit)
            if result.move is None:
                break
            board.push(result.move)
    except chess.engine.EngineTerminatedError:
        # Challenger process died — count as champion win
        return "champion"
    except Exception as e:
        print(f"  game error: {e}", file=sys.stderr, flush=True)
        return "draw"

    outcome = board.outcome(claim_draw=True)
    if outcome is None or outcome.winner is None:
        return "draw"
    challenger_won = (outcome.winner == chess.WHITE) == challenger_white
    return "challenger" if challenger_won else "champion"


# ── LLM proposal ─────────────────────────────────────────────────────────────

_SYSTEM = """\
You are improving a Python chess engine's static evaluation function to maximise \
playing strength in self-play. The engine uses iterative-deepening alpha-beta search \
with quiescence and a transposition table. Your job: propose ONE targeted improvement \
to evaluation.py.

Constraints:
- Preserve exact signatures: evaluate(board: chess.Board) -> int
  (centipawns from side-to-move perspective) and is_endgame(board: chess.Board) -> bool
- Only import the `chess` module and Python standard library
- Make exactly ONE focused change per call; do not rewrite the whole file

High-value improvements to consider (pick what fits given the history):
  mobility bonus (count legal moves for each side), passed pawn detection & bonus,
  rook on open / semi-open file bonus, bishop pair bonus (+30 cp), king-pawn shelter,
  connected rooks, outpost square bonus for knights, backward pawn penalty,
  tapered evaluation (mg/eg interpolation via phase weight), PST value tuning

Output format — strictly follow this, no other text:
RATIONALE: <one sentence describing the single change>
```python
<complete new evaluation.py>
```"""


def propose(eval_code: str, history: list[dict]) -> Optional[tuple[str, str]]:
    """Returns (rationale, new_eval_code) or None on failure."""
    client = anthropic.Anthropic()

    history_text = ""
    if history:
        history_text = "\nRecent iterations (most recent last):\n"
        for h in history[-6:]:
            tag = "KEPT" if h["accepted"] else "REVERTED"
            history_text += f"  [{tag} {h['score']:.0%}] {h['rationale']}\n"

    user = f"Current evaluation.py:\n```python\n{eval_code}\n```\n{history_text}"

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=16000,
                system=_SYSTEM,
                messages=[{"role": "user", "content": user}],
            )
            text = response.content[0].text.strip()
            break
        except Exception as e:
            print(f"  LLM error (attempt {attempt+1}): {e}", file=sys.stderr, flush=True)
            if attempt == 2:
                return None
    else:
        return None

    rationale = "unknown change"
    for line in text.splitlines():
        if line.startswith("RATIONALE:"):
            rationale = line[len("RATIONALE:"):].strip()
            break

    if "```python" not in text:
        print("  LLM response missing code block", file=sys.stderr, flush=True)
        return None

    code = text.split("```python", 1)[1].split("```", 1)[0].strip()
    return rationale, code


# ── Arbitrary match between two snapshot dirs ────────────────────────────────

def play_match_between(dir_a: Path, dir_b: Path, n_games: int, label_a: str = "A", label_b: str = "B") -> tuple[int, int, int]:
    """Play n_games between dir_a (white first) and dir_b. Returns (a_wins, draws, b_wins)."""
    a_wins = draws = b_wins = 0
    try:
        with (
            chess.engine.SimpleEngine.popen_uci(
                ["python3", "engine.py"], cwd=str(dir_a), stderr=subprocess.DEVNULL
            ) as eng_a,
            chess.engine.SimpleEngine.popen_uci(
                ["python3", "engine.py"], cwd=str(dir_b), stderr=subprocess.DEVNULL
            ) as eng_b,
        ):
            limit = chess.engine.Limit(time=TIME_PER_MOVE)
            for i in range(n_games):
                a_is_white = i % 2 == 0
                white_eng = eng_a if a_is_white else eng_b
                black_eng = eng_b if a_is_white else eng_a
                start_fen = OPENING_FENS[i % len(OPENING_FENS)]
                board = chess.Board(start_fen) if start_fen else chess.Board()
                try:
                    while not board.is_game_over(claim_draw=True) and board.fullmove_number <= MAX_GAME_MOVES:
                        eng = white_eng if board.turn == chess.WHITE else black_eng
                        result = eng.play(board, limit)
                        if result.move is None:
                            break
                        board.push(result.move)
                except Exception:
                    draws += 1
                    continue
                outcome = board.outcome(claim_draw=True)
                if outcome is None or outcome.winner is None:
                    draws += 1
                elif (outcome.winner == chess.WHITE) == a_is_white:
                    a_wins += 1
                else:
                    b_wins += 1
                total = i + 1
                score = (a_wins + 0.5 * draws) / total
                print(f"  [{i+1:>{len(str(n_games))}}/{n_games}] {label_a} score: {score:.0%}", flush=True)
    except Exception as e:
        print(f"  match error: {e}", file=sys.stderr, flush=True)
    return a_wins, draws, b_wins


# ── Report & graph ────────────────────────────────────────────────────────────

def plot_progress(log: list[dict], champion_vs_baseline: Optional[tuple[float, int, int, int]] = None) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    played = [e for e in log if e["wins"] + e["draws"] + e["losses"] > 0]

    iterations = [e["iteration"] for e in played]
    scores = [e["score"] for e in played]
    accepted = [e["accepted"] for e in played]

    cumulative = []
    total = 0
    for e in played:
        if e["accepted"]:
            total += 1
        cumulative.append(total)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    fig.suptitle("Autoresearch Progress", fontsize=14, fontweight="bold")

    colors = ["#2ecc71" if a else "#e74c3c" for a in accepted]
    ax1.bar(iterations, scores, color=colors, alpha=0.85, zorder=3)
    ax1.axhline(DEFAULT_THRESHOLD, color="#3498db", linestyle="--", linewidth=1.2, label=f"threshold ({DEFAULT_THRESHOLD:.0%})")
    ax1.axhline(0.5, color="#95a5a6", linestyle=":", linewidth=1, label="50%")
    ax1.set_ylabel("Challenger score")
    ax1.set_ylim(0, 1)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax1.legend(loc="upper right", fontsize=8)
    ax1.grid(axis="y", alpha=0.3, zorder=0)
    kept_patch = mpatches.Patch(color="#2ecc71", alpha=0.85, label="accepted")
    reverted_patch = mpatches.Patch(color="#e74c3c", alpha=0.85, label="reverted")
    ax1.legend(handles=[kept_patch, reverted_patch] + ax1.get_legend_handles_labels()[0][:2],
               loc="upper right", fontsize=8)

    ax2.step(iterations, cumulative, where="post", color="#3498db", linewidth=2)
    ax2.fill_between(iterations, cumulative, step="post", alpha=0.15, color="#3498db")
    ax2.set_ylabel("Cumulative improvements")
    ax2.set_xlabel("Iteration")
    ax2.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax2.grid(axis="y", alpha=0.3)

    if champion_vs_baseline is not None:
        score, w, d, l = champion_vs_baseline
        fig.text(
            0.99, 0.01,
            f"Champion vs Baseline: {score:.0%}  (W{w}/D{d}/L{l})",
            ha="right", va="bottom", fontsize=9, color="#8e44ad",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#8e44ad", alpha=0.8),
        )

    plt.tight_layout()
    plt.savefig(GRAPH_FILE, dpi=150, bbox_inches="tight")
    print(f"Graph saved to {GRAPH_FILE}", flush=True)
    plt.close()


def report(validate_games: int = 0) -> None:
    log = load_log()
    if not log:
        print("No iterations logged yet.")
        return

    accepted = [e for e in log if e["accepted"]]
    total = len(log)

    print(f"\n{'='*60}")
    print(f"Autoresearch report  —  {total} iterations, {len(accepted)} accepted")
    print(f"{'='*60}")
    print(f"{'#':>4}  {'Score':>6}  {'Result':>8}  Rationale")
    print(f"{'─'*60}")
    for e in log:
        tag = "KEPT   " if e["accepted"] else "reverted"
        rationale = e["rationale"][:48] + "…" if len(e["rationale"]) > 49 else e["rationale"]
        print(f"{e['iteration']:>4}  {e['score']:>5.0%}  {tag}  {rationale}")

    if accepted:
        avg_score = sum(e["score"] for e in accepted) / len(accepted)
        print(f"\nAccepted avg score: {avg_score:.0%}")

    champion_vs_baseline = None
    if validate_games > 0 and BASELINE_DIR.exists() and CHAMPION_DIR.exists():
        print(f"\nValidation: champion vs baseline ({validate_games} games)...")
        w, d, l = play_match_between(CHAMPION_DIR, BASELINE_DIR, validate_games, "champion", "baseline")
        final_score = (w + 0.5 * d) / validate_games
        print(f"Champion score vs baseline: {final_score:.0%}  (W{w}/D{d}/L{l})")
        champion_vs_baseline = (final_score, w, d, l)
    elif validate_games > 0:
        print("\nBaseline not found — run the main loop first to create it.")

    plot_progress(log, champion_vs_baseline)


# ── Log helpers ───────────────────────────────────────────────────────────────

def load_log() -> list[dict]:
    return json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []


def save_log(log: list[dict]) -> None:
    LOG_FILE.write_text(json.dumps(log, indent=2))


# ── Main loop ─────────────────────────────────────────────────────────────────

def run(n_iterations: int, n_games: int, threshold: float) -> None:
    if not CHAMPION_DIR.exists() or not (CHAMPION_DIR / "evaluation.py").exists():
        print("Saving initial champion snapshot...", flush=True)
        save_champion()

    save_baseline()  # no-op if already saved
    log = load_log()
    accepted_total = sum(1 for e in log if e["accepted"])

    for iteration in range(1, n_iterations + 1):
        divider = "─" * 60
        print(f"\n{divider}", flush=True)
        print(
            f"Iteration {iteration}/{n_iterations}  "
            f"(improvements so far: {accepted_total})",
            flush=True,
        )
        print(divider, flush=True)

        eval_code = current_eval()

        print("Proposing modification...", flush=True)
        new_eval = rationale = None
        for attempt in range(3):
            result = propose(eval_code, log)
            if result is None:
                print(f"  proposal failed (attempt {attempt+1})", flush=True)
                continue
            r, code = result
            if not syntax_ok(code):
                print(f"  syntax error on attempt {attempt+1}, retrying...", flush=True)
                continue
            if code.strip() == eval_code.strip():
                print("  no change proposed, retrying...", flush=True)
                continue
            rationale, new_eval = r, code
            break

        if new_eval is None:
            print("Could not get a valid proposal — skipping.", flush=True)
            continue

        print(f"Change: {rationale}", flush=True)
        apply_eval(new_eval)

        if not engine_ok():
            print("Engine startup failed — skipping.", flush=True)
            apply_eval(champion_eval())
            continue

        print(f"Running {n_games}-game match...", flush=True)
        c_wins, draws, c_losses = play_match(n_games)
        score = (c_wins + 0.5 * draws) / n_games
        accepted = score > threshold

        if accepted:
            print(f"KEPT     score={score:.0%}  promoting to champion", flush=True)
            save_champion()
            accepted_total += 1
        else:
            print(f"REVERTED score={score:.0%}", flush=True)
            apply_eval(champion_eval())

        log.append(
            {
                "iteration": len(log) + 1,
                "rationale": rationale,
                "wins": c_wins,
                "draws": draws,
                "losses": c_losses,
                "score": score,
                "accepted": accepted,
                "timestamp": time.time(),
            }
        )
        save_log(log)

    print(f"\n{'=' * 60}", flush=True)
    print(f"Done. {accepted_total} improvement(s) accepted.", flush=True)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Autoresearch: LLM-driven iterative engine improvement via self-play"
    )
    parser.add_argument("--iterations", "-n", type=int, default=DEFAULT_ITERATIONS,
                        help=f"Number of iterations (default: {DEFAULT_ITERATIONS})")
    parser.add_argument("--games", "-g", type=int, default=DEFAULT_GAMES,
                        help=f"Games per match (default: {DEFAULT_GAMES})")
    parser.add_argument("--threshold", "-t", type=float, default=DEFAULT_THRESHOLD,
                        help=f"Win-rate threshold to accept a change (default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--report", action="store_true",
                        help="Print summary and show progress graph")
    parser.add_argument("--validate", type=int, default=0, metavar="N",
                        help="With --report: play N games champion vs baseline")
    args = parser.parse_args()

    if args.report:
        report(validate_games=args.validate)
    else:
        run(n_iterations=args.iterations, n_games=args.games, threshold=args.threshold)
