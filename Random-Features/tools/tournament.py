#!/usr/bin/env python3
"""
Tournament: full round-robin across all engines in engines/variants/ + engines/base/.

Usage:
    python3 tools/tournament.py [--games N] [--movetime MS]

Each pair plays --games games (must be even, colors alternate).
Prints a leaderboard by total score, then a breakdown of each variant's
win rate specifically against the base engine.
"""

import argparse
import itertools
import os
import sys

# Allow importing Engine / play_game from the sibling arbiter module.
_TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _TOOLS)
from arbiter import Engine, play_game  # noqa: E402

# Human-readable description of each variant's single behavioral change.
_VARIANT_FEATURES = {
    'aggro_push':     'always plays most-advanced pawn push when no captures exist',
    'bishops_only':   'never moves knights (bishops-and-majors style)',
    'first_rank_lock':'locks back-rank pieces for the first 10 moves',
    'fortress':       'restricts all pieces to own half of the board after move 15',
    'king_walk':      'never castles; steers king toward the centre',
    'mirror_queen':   'responds to any opponent queen move with its own queen move',
    'no_pawn_push':   'stops pushing pawns entirely after move 20',
    'random_blunder': 'plays a random legal move on every 5th full-move number',
}


def discover_engines(repo_root):
    """Return list of (name, path) for base + all variants."""
    engines = []

    base_path = os.path.join(repo_root, 'engines', 'base', 'engine.py')
    if os.path.isfile(base_path):
        engines.append(('base', base_path))

    variants_dir = os.path.join(repo_root, 'engines', 'variants')
    if os.path.isdir(variants_dir):
        for variant in sorted(os.listdir(variants_dir)):
            path = os.path.join(variants_dir, variant, 'engine.py')
            if os.path.isfile(path):
                engines.append((variant, path))

    return engines


def run_tournament(engines, games_per_match, movetime_ms):
    """
    Run a round-robin. Returns:
      scores  : {name: float}   — total points across all matches
      wins    : {name: int}
      losses  : {name: int}
      draws   : {name: int}
      vs_base : {name: (score, total_games)}  — each variant's record vs base only
    """
    names = [name for name, _ in engines]
    paths = {name: path for name, path in engines}

    scores  = {n: 0.0 for n in names}
    wins    = {n: 0   for n in names}
    losses  = {n: 0   for n in names}
    draws   = {n: 0   for n in names}
    vs_base = {n: [0.0, 0] for n in names}  # [score_vs_base, games_vs_base]

    pairs = list(itertools.combinations(names, 2))
    total_matches = len(pairs)

    print(f'Engines : {len(names)}')
    print(f'Matches : {total_matches}  ({games_per_match} games each, '
          f'{movetime_ms} ms/move)\n')

    for match_idx, (n1, n2) in enumerate(pairs, 1):
        e1 = Engine(paths[n1])
        e2 = Engine(paths[n2])
        e1.init()
        e2.init()

        match_scores = {n1: 0.0, n2: 0.0}
        match_wins   = {n1: 0,   n2: 0}
        match_losses = {n1: 0,   n2: 0}
        match_draws  = {n1: 0,   n2: 0}

        for g in range(games_per_match):
            if g % 2 == 0:
                white, black = e1, e2
                wname, bname = n1, n2
            else:
                white, black = e2, e1
                wname, bname = n2, n1

            result = play_game(white, black, movetime_ms)

            if result == 'white':
                match_scores[wname] += 1.0
                match_wins[wname]   += 1
                match_losses[bname] += 1
            elif result == 'black':
                match_scores[bname] += 1.0
                match_wins[bname]   += 1
                match_losses[wname] += 1
            else:
                match_scores[n1] += 0.5
                match_scores[n2] += 0.5
                match_draws[n1]  += 1
                match_draws[n2]  += 1

        e1.quit()
        e2.quit()

        for n in (n1, n2):
            scores[n]  += match_scores[n]
            wins[n]    += match_wins[n]
            losses[n]  += match_losses[n]
            draws[n]   += match_draws[n]

        # Track performance vs base for each side
        for n, opponent in ((n1, n2), (n2, n1)):
            if opponent == 'base' and n != 'base':
                vs_base[n][0] += match_scores[n]
                vs_base[n][1] += games_per_match

        s1, s2 = match_scores[n1], match_scores[n2]
        label = (f'{n1} wins' if s1 > s2 else
                 f'{n2} wins' if s2 > s1 else 'Draw')
        print(f'[{match_idx:2d}/{total_matches}] {n1} vs {n2}  →  '
              f'{s1:.1f}–{s2:.1f}  ({label})')

    return scores, wins, losses, draws, vs_base


def print_leaderboard(scores, wins, losses, draws, engines):
    names = [n for n, _ in engines]
    ranked = sorted(names, key=lambda n: scores[n], reverse=True)
    games_played = {n: wins[n] + losses[n] + draws[n] for n in names}

    col = max(len(n) for n in names)
    col = max(col, 6)
    header = (f"\n{'Engine':<{col}}  {'Score':>6}  {'Pts/G':>5}  "
              f"{'Wins':>4}  {'Losses':>6}  {'Draws':>5}")
    sep = '─' * len(header)
    print(sep)
    print(header)
    print(sep)
    for rank, name in enumerate(ranked, 1):
        gp = games_played[name]
        ppg = scores[name] / gp if gp else 0.0
        print(
            f'{name:<{col}}  {scores[name]:>6.1f}  {ppg:>5.3f}  '
            f'{wins[name]:>4}  {losses[name]:>6}  {draws[name]:>5}'
        )
    print(sep)


def print_vs_base(vs_base, engines):
    """Print each variant's win-rate against the base engine, sorted descending."""
    variants = [(n, p) for n, p in engines if n != 'base']
    if not variants:
        return

    # Filter to those that actually played base
    data = [(n, vs_base[n][0], vs_base[n][1]) for n, _ in variants
            if vs_base[n][1] > 0]
    if not data:
        return

    data.sort(key=lambda x: x[1] / x[2], reverse=True)

    col_name = max(len(n) for n, *_ in data)
    col_name = max(col_name, 6)

    print(f"\n{'Variant vs Base Engine':}")
    header2 = (f"{'Variant':<{col_name}}  {'Score':>6}  {'Games':>5}  "
               f"{'WinRate':>7}  Feature")
    sep2 = '─' * max(len(header2), 72)
    print(sep2)
    print(header2)
    print(sep2)
    for name, score, total in data:
        rate = score / total
        feature = _VARIANT_FEATURES.get(name, '(unknown)')
        print(f'{name:<{col_name}}  {score:>6.1f}  {total:>5}  {rate:>7.1%}  {feature}')
    print(sep2)

    best_name, best_score, best_total = data[0]
    best_rate = best_score / best_total
    if best_rate > 0.5:
        print(f'\nHighest win-rate vs base: {best_name} ({best_rate:.1%})')
        print(f'  → Feature: {_VARIANT_FEATURES.get(best_name, "(unknown)")}')
    elif best_rate == 0.5:
        print('\nNo variant achieved a win-rate above 50% vs base.')
    else:
        print('\nNo variant beat the base engine (best was below 50%).')


def main():
    parser = argparse.ArgumentParser(
        description='Round-robin tournament across all UCI engines.'
    )
    parser.add_argument(
        '--games', type=int, default=4,
        help='Games per match (must be even, default: 4)'
    )
    parser.add_argument(
        '--movetime', type=int, default=1000,
        help='Time per move in milliseconds (default: 1000)'
    )
    args = parser.parse_args()

    if args.games % 2 != 0:
        parser.error('--games must be even so colors are balanced')

    repo_root = os.path.dirname(_TOOLS)
    engines = discover_engines(repo_root)

    if len(engines) < 2:
        print('Need at least 2 engines to run a tournament.', file=sys.stderr)
        sys.exit(1)

    print(f'=== Round-Robin Tournament ===\n')
    for name, path in engines:
        print(f'  {name:<20} {path}')
    print()

    scores, wins, losses, draws, vs_base = run_tournament(
        engines, args.games, args.movetime
    )

    print('\n=== Leaderboard ===')
    print_leaderboard(scores, wins, losses, draws, engines)

    print('\n=== Variant Performance vs Base Engine ===')
    print_vs_base(vs_base, engines)


if __name__ == '__main__':
    main()
