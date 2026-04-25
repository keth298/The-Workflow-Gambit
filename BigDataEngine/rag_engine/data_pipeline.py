"""
Dataset ingestion pipeline.

Reads chess games, opening CSVs/TSVs, and puzzle CSVs; writes a single SQLite
database at LargeDataset/chess_data.db.

Data sources
------------
  Games    : HF streaming  (angeluriot/chess_games — no local download needed)
             Fallback: any *.pgn files under LargeDataset/chess_games/
  Openings : niklasf/chess-openings TSV  (a.tsv … e.tsv)
             Fallback: any *.csv in LargeDataset/openings/
  Puzzles  : Lichess puzzle CSV  (LargeDataset/puzzles/lichess_puzzles.csv)

Tables
------
  positions  (id, fen, source, outcome)
  move_stats (fen, move, count, total_outcome)
      avg_outcome = total_outcome / count  ∈ [-1, +1] for side-to-move

Run:
    python data_pipeline.py                     # full mode  (~30-60 min)
    python data_pipeline.py --fast              # fast mode  (~5-10 min)
    python data_pipeline.py --max-games 10000   # custom limit
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

import chess
import chess.pgn
from tqdm import tqdm

ROOT        = Path(__file__).parent.parent
DATASET_DIR = ROOT / "LargeDataset"
DB_PATH     = DATASET_DIR / "chess_data.db"


# ── Schema ────────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    fen     TEXT    NOT NULL,
    source  TEXT    NOT NULL,
    outcome REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pos_fen ON positions(fen);

CREATE TABLE IF NOT EXISTS move_stats (
    fen           TEXT NOT NULL,
    move          TEXT NOT NULL,
    count         INTEGER NOT NULL DEFAULT 0,
    total_outcome REAL    NOT NULL DEFAULT 0.0,
    PRIMARY KEY (fen, move)
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


# ── Batch upsert ──────────────────────────────────────────────────────────────

def _upsert_batch(conn: sqlite3.Connection, rows: list[tuple]) -> None:
    """rows: (fen, source, outcome, move_uci)  — move_uci may be None."""
    pos_rows  = [(fen, src, out)      for fen, src, out, _ in rows]
    stat_rows = [(fen, mv, out)       for fen, _, out, mv in rows if mv]

    conn.executemany(
        "INSERT OR IGNORE INTO positions (fen, source, outcome) VALUES (?,?,?)",
        pos_rows,
    )
    conn.executemany(
        """INSERT INTO move_stats (fen, move, count, total_outcome)
           VALUES (?, ?, 1, ?)
           ON CONFLICT(fen, move) DO UPDATE SET
               count         = count + 1,
               total_outcome = total_outcome + excluded.total_outcome""",
        stat_rows,
    )


# ── Outcome helpers ───────────────────────────────────────────────────────────

def _outcome_from_pgn(result: str, turn: bool) -> float | None:
    if result == "1-0":   val = 1.0
    elif result == "0-1": val = -1.0
    elif result == "1/2-1/2": val = 0.0
    else: return None
    return val if turn == chess.WHITE else -val


def _outcome_from_winner(winner: str | None, turn: bool) -> float | None:
    if winner == "white":      val = 1.0
    elif winner == "black":    val = -1.0
    elif winner is None:       val = 0.0
    else:                      return None
    return val if turn == chess.WHITE else -val


# ─────────────────────────────────────────────────────────────────────────────
# GAMES — Hugging Face streaming  (primary)
# ─────────────────────────────────────────────────────────────────────────────

def process_hf_games(conn: sqlite3.Connection, max_games: int,
                     sample_every: int) -> int:
    """Stream games from HF (angeluriot/chess_games). Returns game count."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("[WARN] 'datasets' not installed — run: pip install datasets",
              file=sys.stderr)
        return 0

    print("  Connecting to Hugging Face (streaming)...", file=sys.stderr)
    try:
        dataset = load_dataset(
            "angeluriot/chess_games", streaming=True, split="train",
            trust_remote_code=True,
        )
    except Exception as e:
        print(f"[WARN] HF load failed: {e}", file=sys.stderr)
        return 0

    count  = 0
    batch: list[tuple] = []
    BATCH  = 5_000

    pbar = tqdm(total=max_games, desc="  HF games", unit=" games")
    for game in dataset:
        if count >= max_games:
            break

        winner    = game.get("winner")
        moves_uci = game.get("moves_uci") or []
        board     = chess.Board()

        for ply, move_uci in enumerate(moves_uci):
            try:
                move = chess.Move.from_uci(move_uci)
                if not board.is_legal(move):
                    break
                if ply % sample_every == 0:
                    out = _outcome_from_winner(winner, board.turn)
                    if out is not None:
                        batch.append((board.fen(), "game", out, move_uci))
                board.push(move)
            except Exception:
                break

        count += 1
        pbar.update(1)

        if len(batch) >= BATCH:
            _upsert_batch(conn, batch)
            conn.commit()
            batch.clear()

    pbar.close()
    if batch:
        _upsert_batch(conn, batch)
        conn.commit()

    print(f"[Games/HF] {count:,} games ingested.", file=sys.stderr)
    return count


# ─────────────────────────────────────────────────────────────────────────────
# GAMES — local PGN files  (fallback if chess_games/*.pgn exist)
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_EVERY = 4

def _process_pgn_file(path: Path, conn: sqlite3.Connection,
                      max_games: int, sample_every: int) -> int:
    games = 0
    batch: list[tuple] = []

    with open(path, encoding="utf-8", errors="replace") as fh:
        pbar = tqdm(desc=f"  {path.name}", unit=" games", leave=False)
        while games < max_games:
            game = chess.pgn.read_game(fh)
            if game is None:
                break
            result = game.headers.get("Result", "*")
            board  = game.board()
            for ply, move in enumerate(game.mainline_moves()):
                out = _outcome_from_pgn(result, board.turn)
                if out is not None and ply % sample_every == 0:
                    batch.append((board.fen(), "game", out, move.uci()))
                board.push(move)
            games += 1
            pbar.update(1)
            if len(batch) >= 5_000:
                _upsert_batch(conn, batch)
                conn.commit()
                batch.clear()
        pbar.close()

    if batch:
        _upsert_batch(conn, batch)
        conn.commit()
    return games


def process_all_pgn(conn: sqlite3.Connection, max_games: int,
                    sample_every: int = SAMPLE_EVERY) -> None:
    game_dir   = DATASET_DIR / "chess_games"
    pgn_files  = sorted(game_dir.rglob("*.pgn")) if game_dir.exists() else []

    if pgn_files:
        total = 0
        for pgn in pgn_files:
            n = _process_pgn_file(pgn, conn, max(0, max_games - total), sample_every)
            total += n
            print(f"  {pgn.name}: {n} games (total {total})", file=sys.stderr)
            if total >= max_games:
                break
        print(f"[Games/PGN] {total} games ingested.", file=sys.stderr)
    else:
        print("  No local PGN files — streaming from Hugging Face.", file=sys.stderr)
        process_hf_games(conn, max_games, sample_every)


# ─────────────────────────────────────────────────────────────────────────────
# OPENINGS — niklasf/chess-openings TSV  (a.tsv … e.tsv)
# ─────────────────────────────────────────────────────────────────────────────

_OPENING_WEIGHT = 5


def _ingest_uci_line(moves_uci: list[str], batch: list, source: str) -> int:
    """Walk UCI moves from start, appending (fen, source, 0, move) rows."""
    board = chess.Board()
    added = 0
    for uci_str in moves_uci:
        try:
            move = chess.Move.from_uci(uci_str)
            if not board.is_legal(move):
                break
            fen = board.fen()
            for _ in range(_OPENING_WEIGHT):
                batch.append((fen, source, 0.0, uci_str))
            board.push(move)
            added += 1
        except Exception:
            break
    return added


def _parse_san_line(pgn_str: str) -> list[str]:
    """Convert a SAN move sequence to a list of UCI strings."""
    board = chess.Board()
    ucis: list[str] = []
    for tok in pgn_str.split():
        if tok[0].isdigit():  # move-number token like "1." or "1..."
            continue
        try:
            m = board.parse_san(tok)
        except Exception:
            break
        if not board.is_legal(m):
            break
        ucis.append(m.uci())
        board.push(m)
    return ucis


def process_openings(conn: sqlite3.Connection) -> None:
    op_dir = DATASET_DIR / "openings"
    if not op_dir.exists():
        print("[WARN] openings/ not found — skipping.", file=sys.stderr)
        return

    tsv_files = sorted(op_dir.glob("*.tsv"))
    csv_files = sorted(op_dir.glob("*.csv"))
    all_files = tsv_files + csv_files

    if not all_files:
        print("[WARN] No opening files found in openings/.", file=sys.stderr)
        return

    batch: list[tuple] = []
    total = 0

    for fpath in all_files:
        delim = "\t" if fpath.suffix == ".tsv" else ","
        with open(fpath, encoding="utf-8", errors="replace") as fh:
            reader = csv.DictReader(fh, delimiter=delim)
            for row in reader:
                # niklasf TSV has 'uci' column with space-separated UCI moves
                uci_str = row.get("uci", "").strip()
                if uci_str:
                    added = _ingest_uci_line(uci_str.split(), batch, "opening")
                    total += added
                else:
                    # Fall back to SAN column
                    pgn_str = (row.get("pgn") or row.get("Moves") or
                               row.get("moves") or row.get("PGN") or "").strip()
                    if pgn_str:
                        ucis  = _parse_san_line(pgn_str)
                        added = _ingest_uci_line(ucis, batch, "opening")
                        total += added

                if len(batch) >= 10_000:
                    _upsert_batch(conn, batch)
                    conn.commit()
                    batch.clear()

    if batch:
        _upsert_batch(conn, batch)
        conn.commit()

    print(f"[Openings] {total} position-moves ingested.", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# PUZZLES — Lichess CSV
# ─────────────────────────────────────────────────────────────────────────────

_PUZZLE_WEIGHT = 10


def process_puzzles(conn: sqlite3.Connection, max_puzzles: int = 0) -> None:
    puz_dir = DATASET_DIR / "puzzles"
    if not puz_dir.exists():
        print("[WARN] puzzles/ not found — skipping.", file=sys.stderr)
        return

    csv_files = sorted(puz_dir.glob("*.csv"))
    if not csv_files:
        print("[WARN] No puzzle CSV files found.", file=sys.stderr)
        return

    batch: list[tuple] = []
    total = 0

    for csv_path in csv_files:
        with open(csv_path, encoding="utf-8", errors="replace") as fh:
            reader = csv.DictReader(fh)
            for row in tqdm(reader, desc=f"  {csv_path.name}",
                            unit=" puzzles", leave=False):
                if max_puzzles and total >= max_puzzles:
                    break
                try:
                    fen   = row["FEN"]
                    moves = row["Moves"].split()
                    if len(moves) < 2:
                        continue
                    board = chess.Board(fen)
                    board.push(chess.Move.from_uci(moves[0]))
                    best = moves[1]
                    m = chess.Move.from_uci(best)
                    if not board.is_legal(m):
                        continue
                    puzzle_fen = board.fen()
                    for _ in range(_PUZZLE_WEIGHT):
                        batch.append((puzzle_fen, "puzzle", 1.0, best))
                    total += 1
                    if len(batch) >= 10_000:
                        _upsert_batch(conn, batch)
                        conn.commit()
                        batch.clear()
                except Exception:
                    continue

    if batch:
        _upsert_batch(conn, batch)
        conn.commit()

    print(f"[Puzzles] {total} puzzle positions ingested.", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

FAST_MAX_GAMES    = 25_000
FAST_SAMPLE_EVERY = 10
FAST_MAX_PUZZLES  = 75_000


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Ingest chess datasets into SQLite."
    )
    ap.add_argument("--fast", action="store_true",
                    help="Fast mode: small limits, ~5-10 min total")
    ap.add_argument("--max-games",    type=int, default=0)
    ap.add_argument("--max-puzzles",  type=int, default=0)
    ap.add_argument("--sample-every", type=int, default=0)
    args = ap.parse_args()

    if args.fast:
        max_games    = args.max_games    or FAST_MAX_GAMES
        max_puzzles  = args.max_puzzles  or FAST_MAX_PUZZLES
        sample_every = args.sample_every or FAST_SAMPLE_EVERY
    else:
        max_games    = args.max_games    or 500_000
        max_puzzles  = args.max_puzzles  or 0
        sample_every = args.sample_every or SAMPLE_EVERY

    mode = "FAST" if args.fast else "FULL"
    print(
        f"[Pipeline] {mode} — max_games={max_games:,}  "
        f"max_puzzles={'∞' if not max_puzzles else max_puzzles:,}  "
        f"sample_every={sample_every}",
        file=sys.stderr,
    )

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-65536")
    init_db(conn)

    print("\n=== Step 1/3: Ingesting games ===", file=sys.stderr)
    process_all_pgn(conn, max_games, sample_every=sample_every)

    print("\n=== Step 2/3: Ingesting openings ===", file=sys.stderr)
    process_openings(conn)

    print("\n=== Step 3/3: Ingesting puzzles ===", file=sys.stderr)
    process_puzzles(conn, max_puzzles=max_puzzles)

    n_pos   = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
    n_stats = conn.execute("SELECT COUNT(*) FROM move_stats").fetchone()[0]
    print(
        f"\n[Done] {n_pos:,} positions  |  {n_stats:,} unique (fen, move) pairs.",
        file=sys.stderr,
    )
    conn.close()


if __name__ == "__main__":
    main()
