#!/usr/bin/env python3
"""
stats.py: run the full tournament, analyze results, build a standalone engine.

Usage:
    python3 tools/stats.py [--games N] [--movetime MS] [--log FILE]

Steps:
  1. Read build_log.jsonl for historical token / runtime totals
  2. Run tools/tournament.py, capture output, measure wall-clock time
  3. Parse leaderboard and per-variant vs-base results
  4. Select best engine: total score → win rate vs base → lowest loss rate
  5. Assemble a clean standalone engine.py at the repo root
  6. Verify engine.py answers 'uci' and 'isready' correctly
  7. Write results/report.txt
  8. Append a new entry to build_log.jsonl
  9. Rewrite build_report.txt with cumulative totals
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

_TOOLS   = os.path.dirname(os.path.abspath(__file__))
_ROOT    = os.path.dirname(_TOOLS)
_LOG     = os.path.join(_ROOT, 'build_log.jsonl')
_REPORT  = os.path.join(_ROOT, 'build_report.txt')
_RESULTS = os.path.join(_ROOT, 'results', 'report.txt')
_ENGINE  = os.path.join(_ROOT, 'engine.py')

_VARIANT_FEATURES = {
    'aggro_push':      'always plays most-advanced pawn push when no captures exist',
    'bishops_only':    'never moves knights (bishops-and-majors style)',
    'first_rank_lock': 'locks back-rank pieces for the first 10 moves',
    'fortress':        'restricts all pieces to own half of the board after move 15',
    'king_walk':       'never castles; steers king toward the centre',
    'mirror_queen':    'responds to any opponent queen move with its own queen move',
    'no_pawn_push':    'stops pushing pawns entirely after move 20',
    'random_blunder':  'plays a random legal move on every 5th full-move number',
    'base':            'standard alpha-beta with no behavioral restriction',
}


# ── Log I/O ──────────────────────────────────────────────────────────────────

def read_log():
    if not os.path.isfile(_LOG):
        return []
    entries = []
    with open(_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def append_log(entry):
    with open(_LOG, 'a') as f:
        f.write(json.dumps(entry) + '\n')


# ── Tournament runner ─────────────────────────────────────────────────────────

def run_tournament(games, movetime_ms):
    """Run tournament.py, return (stdout_text, elapsed_seconds)."""
    cmd = [
        sys.executable,
        os.path.join(_TOOLS, 'tournament.py'),
        '--games',    str(games),
        '--movetime', str(movetime_ms),
    ]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    if proc.returncode != 0:
        print('tournament.py stderr:', proc.stderr[:500], file=sys.stderr)
        raise RuntimeError(f'tournament.py exited with code {proc.returncode}')
    return proc.stdout, elapsed


# ── Output parsers ────────────────────────────────────────────────────────────

def _is_separator(line):
    s = line.strip()
    return bool(s) and all(c in '─-' for c in s)


def parse_leaderboard(output):
    """Return list of dicts: name, score, wins, losses, draws (sorted by score desc)."""
    lines = output.splitlines()
    results = []
    header_seen = False
    in_table = False

    for line in lines:
        if re.search(r'Engine\s+Score\s+Pts', line):
            header_seen = True
            continue
        if header_seen and _is_separator(line):
            if in_table:
                break
            in_table = True
            continue
        if not in_table:
            continue
        parts = re.split(r'\s{2,}', line.strip())
        if len(parts) >= 5:
            try:
                results.append({
                    'name':   parts[0],
                    'score':  float(parts[1]),
                    'wins':   int(parts[3]),
                    'losses': int(parts[4]),
                    'draws':  int(parts[5]) if len(parts) > 5 else 0,
                })
            except (ValueError, IndexError):
                pass

    return sorted(results, key=lambda r: r['score'], reverse=True)


def parse_vs_base(output):
    """Return list of dicts: name, score, games, win_rate (float 0-1), feature."""
    lines = output.splitlines()
    results = []
    header_seen = False
    in_table = False

    for line in lines:
        if re.search(r'Variant\s+Score\s+Games', line):
            header_seen = True
            continue
        if header_seen and _is_separator(line):
            if in_table:
                break
            in_table = True
            continue
        if not in_table:
            continue
        parts = re.split(r'\s{2,}', line.strip())
        if len(parts) >= 4:
            try:
                win_rate_str = parts[3].rstrip('%')
                results.append({
                    'name':     parts[0],
                    'score':    float(parts[1]),
                    'games':    int(parts[2]),
                    'win_rate': float(win_rate_str) / 100.0,
                    'feature':  parts[4] if len(parts) > 4 else '',
                })
            except (ValueError, IndexError):
                pass

    return sorted(results, key=lambda r: r['win_rate'], reverse=True)


# ── Engine selection ──────────────────────────────────────────────────────────

def select_best(leaderboard, vs_base):
    """
    Primary key:   total score (descending)
    Secondary key: win rate vs base engine (descending)
    Tertiary key:  loss rate (ascending)
    Returns the chosen entry from leaderboard.
    """
    if not leaderboard:
        return None

    win_rate_map = {r['name']: r['win_rate'] for r in vs_base}
    total_games  = {r['name']: r['wins'] + r['losses'] + r['draws'] for r in leaderboard}

    def sort_key(r):
        name  = r['name']
        wrvb  = win_rate_map.get(name, 0.0)
        tg    = total_games.get(name, 1)
        lr    = r['losses'] / tg if tg else 0.0
        return (r['score'], wrvb, -lr)

    return max(leaderboard, key=sort_key)


# ── Standalone engine assembly ────────────────────────────────────────────────

_STRIP_EXACT = {
    'import chess',
    'import chess.polyglot',
    'import time',
    'import os',
    'import sys',
    'import random',
}
_STRIP_PREFIX = (
    'from tt import',
    'from evaluate import',
    'from search import',
    'sys.path.insert',
    'sys.path.append',
)


def _strip_imports(src):
    out = []
    for line in src.splitlines():
        s = line.strip()
        if s in _STRIP_EXACT:
            continue
        if any(s.startswith(p) for p in _STRIP_PREFIX):
            continue
        out.append(line)
    # trim leading blank lines
    while out and not out[0].strip():
        out.pop(0)
    return '\n'.join(out)


def build_standalone(variant_name):
    base = os.path.join(_ROOT, 'engines', 'base')
    if variant_name == 'base':
        search_path = os.path.join(base, 'search.py')
    else:
        search_path = os.path.join(_ROOT, 'engines', 'variants', variant_name, 'search.py')

    tt_src     = open(os.path.join(base, 'tt.py')).read()
    eval_src   = open(os.path.join(base, 'evaluate.py')).read()
    search_src = open(search_path).read()
    engine_src = open(os.path.join(base, 'engine.py')).read()

    needs_random = 'import random' in search_src

    display_name = variant_name.replace('_', ' ').title() + 'Engine'
    engine_src = engine_src.replace("'id name BaseEngine'",
                                    f"'id name {display_name}'")

    feature = _VARIANT_FEATURES.get(variant_name, '')

    header_lines = [
        '#!/usr/bin/env python3',
        '"""',
        f'Final UCI chess engine — {variant_name} variant.',
        f'Variant feature: {feature}',
        'Selected by tournament: highest total score, best win rate vs base engine.',
        '"""',
        '',
        'import sys',
        'import time',
        'import chess',
        'import chess.polyglot',
    ]
    if needs_random:
        header_lines.append('import random')

    sections = [
        '\n'.join(header_lines),
        '',
        '# ── Transposition Table ─────────────────────────────────────────────────────',
        _strip_imports(tt_src),
        '',
        '# ── Evaluation ──────────────────────────────────────────────────────────────',
        _strip_imports(eval_src),
        '',
        f'# ── Search ({variant_name} variant) ────────────────────────────────────────────',
        _strip_imports(search_src),
        '',
        '# ── UCI Interface ────────────────────────────────────────────────────────────',
        _strip_imports(engine_src),
    ]

    return '\n'.join(sections) + '\n'


# ── UCI smoke test ────────────────────────────────────────────────────────────

def verify_engine(path):
    """Check that engine.py responds to uci and isready correctly."""
    commands = 'uci\nisready\nquit\n'
    result = subprocess.run(
        [sys.executable, path],
        input=commands, capture_output=True, text=True, timeout=10
    )
    stdout = result.stdout
    ok = 'uciok' in stdout and 'readyok' in stdout
    return ok, stdout


# ── Report writing ────────────────────────────────────────────────────────────

def write_results_report(leaderboard, vs_base, best, runtime_s, games, movetime_ms,
                         cum_runtime_s, cum_tokens):
    os.makedirs(os.path.dirname(_RESULTS), exist_ok=True)
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    lines = [
        '=== Tournament Results Report ===',
        f'Generated : {now}',
        f'Games/match: {games}  |  Time/move: {movetime_ms} ms',
        f'Tournament runtime: {runtime_s:.1f}s',
        '',
        '─── Leaderboard ─────────────────────────────────────────────────────────────',
    ]

    col = max((len(r['name']) for r in leaderboard), default=6)
    col = max(col, 6)
    lines.append(f"{'Engine':<{col}}  {'Score':>6}  {'Wins':>4}  {'Losses':>6}  {'Draws':>5}")
    lines.append('─' * (col + 34))
    for r in leaderboard:
        lines.append(
            f"{r['name']:<{col}}  {r['score']:>6.1f}  {r['wins']:>4}  "
            f"{r['losses']:>6}  {r['draws']:>5}"
        )
    lines.append('')

    if vs_base:
        lines.append('─── Variants vs Base Engine ─────────────────────────────────────────────────')
        col2 = max((len(r['name']) for r in vs_base), default=6)
        lines.append(f"{'Variant':<{col2}}  {'Score':>6}  {'Games':>5}  {'WinRate':>7}  Feature")
        lines.append('─' * (col2 + 50))
        for r in vs_base:
            lines.append(
                f"{r['name']:<{col2}}  {r['score']:>6.1f}  {r['games']:>5}  "
                f"{r['win_rate']:>7.1%}  {r['feature']}"
            )
        lines.append('')

    if best:
        feat = _VARIANT_FEATURES.get(best['name'], '')
        vb   = next((r for r in vs_base if r['name'] == best['name']), None)
        wrvb = f"{vb['win_rate']:.1%} vs base" if vb else 'N/A'
        tg   = best['wins'] + best['losses'] + best['draws']
        lr   = best['losses'] / tg if tg else 0.0
        lines += [
            '─── Selected Engine ─────────────────────────────────────────────────────────',
            f"Engine  : {best['name']}",
            f"Score   : {best['score']:.1f}  "
            f"(W={best['wins']} L={best['losses']} D={best['draws']}, "
            f"loss rate={lr:.1%})",
            f"Vs base : {wrvb}",
            f"Feature : {feat}",
            f"Reason  : highest total score",
            f"Output  : engine.py (standalone, fully UCI-compliant)",
            '',
        ]

    lines += [
        '─── Build Costs (cumulative) ────────────────────────────────────────────────',
        f'Total runtime  : {cum_runtime_s:.1f}s  ({cum_runtime_s/60:.1f} min)',
        f'Token estimate : ~{cum_tokens:,}  (≈ output chars / 4)',
        '',
    ]

    with open(_RESULTS, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def write_build_report(entries):
    cum_runtime = sum(e.get('runtime_s', 0) for e in entries)
    cum_tokens  = sum(e.get('token_estimate', 0) for e in entries)
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    lines = [
        '=== Build Report ===',
        f'Updated : {now}',
        '',
        f'Cumulative runtime  : {cum_runtime:.1f}s  ({cum_runtime/60:.1f} min)',
        f'Cumulative tokens   : ~{cum_tokens:,}',
        f'Total runs logged   : {len(entries)}',
        '',
        '─── Run History ─────────────────────────────────────────────────────────────',
        f"{'#':>3}  {'Timestamp':<22}  {'Runtime':>8}  {'Tokens':>8}  Winner",
        '─' * 70,
    ]
    for i, e in enumerate(entries, 1):
        ts      = e.get('timestamp', '')[:19]
        rt      = e.get('runtime_s', 0)
        tok     = e.get('token_estimate', 0)
        winner  = e.get('winner', '?')
        lines.append(f'{i:>3}  {ts:<22}  {rt:>7.1f}s  {tok:>8,}  {winner}')

    with open(_REPORT, 'w') as f:
        f.write('\n'.join(lines) + '\n')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Run tournament, pick best engine, write reports.'
    )
    parser.add_argument('--games',    type=int, default=4,
                        help='Games per match (even, default 4)')
    parser.add_argument('--movetime', type=int, default=1000,
                        help='ms per move (default 1000)')
    args = parser.parse_args()

    if args.games % 2 != 0:
        parser.error('--games must be even')

    # 1. Historical log
    prior_entries = read_log()
    cum_prior_runtime = sum(e.get('runtime_s', 0) for e in prior_entries)
    cum_prior_tokens  = sum(e.get('token_estimate', 0) for e in prior_entries)

    # 2. Run tournament
    print('Running tournament…', flush=True)
    t_output, t_elapsed = run_tournament(args.games, args.movetime)
    print(t_output, end='', flush=True)
    token_est = len(t_output) // 4

    # 3. Parse
    leaderboard = parse_leaderboard(t_output)
    vs_base     = parse_vs_base(t_output)

    if not leaderboard:
        print('ERROR: could not parse leaderboard from tournament output.',
              file=sys.stderr)
        sys.exit(1)

    # 4. Select best engine
    best = select_best(leaderboard, vs_base)
    winner_name = best['name'] if best else 'unknown'
    print(f'\n→ Selected engine: {winner_name}', flush=True)

    # 5. Build standalone engine.py
    print(f'Building standalone engine.py from {winner_name}…', flush=True)
    engine_code = build_standalone(winner_name)
    with open(_ENGINE, 'w') as f:
        f.write(engine_code)

    # 6. Verify UCI compliance
    print('Verifying UCI compliance…', flush=True)
    ok, uci_out = verify_engine(_ENGINE)
    if ok:
        print('  ✓ uciok + readyok received', flush=True)
    else:
        print(f'  ✗ UCI check FAILED. Output:\n{uci_out}', file=sys.stderr)
        sys.exit(1)

    # 7. Write results/report.txt
    cum_runtime = cum_prior_runtime + t_elapsed
    cum_tokens  = cum_prior_tokens  + token_est
    write_results_report(leaderboard, vs_base, best, t_elapsed,
                         args.games, args.movetime, cum_runtime, cum_tokens)
    print(f'Wrote {_RESULTS}', flush=True)

    # 8. Append to build_log.jsonl
    entry = {
        'timestamp':      datetime.now(timezone.utc).isoformat(),
        'event':          'tournament_run',
        'games_per_match': args.games,
        'movetime_ms':    args.movetime,
        'runtime_s':      round(t_elapsed, 2),
        'token_estimate': token_est,
        'winner':         winner_name,
        'engines_count':  len(leaderboard),
    }
    append_log(entry)
    all_entries = prior_entries + [entry]

    # 9. Rewrite build_report.txt
    write_build_report(all_entries)
    print(f'Wrote {_REPORT}', flush=True)

    # Summary
    print(f'\n=== Done ===')
    print(f'Winner  : {winner_name}')
    print(f'Runtime : {t_elapsed:.1f}s')
    print(f'Tokens  : ~{token_est:,} (this run) / ~{cum_tokens:,} (cumulative)')
    print(f'Engine  : {_ENGINE}')
    print(f'Report  : {_RESULTS}')


if __name__ == '__main__':
    main()
