"""
UCI protocol loop for the chess engine.

stdin/stdout = UCI communication only.
stderr       = debug/info logging.

Run from BuildUpModel/: python -m chess.uci
"""

from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess.board import ChessState, uci_to_move, move_to_uci
from core.engine import MinimaxEngine

ENGINE_NAME   = "BuildUp Chess"
ENGINE_AUTHOR = "BuildUpModel"
DEFAULT_DEPTH = 3


def _parse_position(cmd: str) -> ChessState:
    tokens = cmd.split()
    i = 1  # skip 'position'

    if tokens[i] == 'startpos':
        state = ChessState.start()
        i += 1
    else:                    # 'fen ...'
        i += 1               # skip 'fen'
        fen_toks = []
        while i < len(tokens) and tokens[i] != 'moves':
            fen_toks.append(tokens[i])
            i += 1
        state = ChessState.from_fen(' '.join(fen_toks))

    if i < len(tokens) and tokens[i] == 'moves':
        i += 1
        for uci in tokens[i:]:
            legal = state.get_legal_moves()
            matched = next((m for m in legal if move_to_uci(m) == uci), None)
            if matched:
                state = state.apply_move(matched)
            else:
                print(f'info string illegal move: {uci}', file=sys.stderr)
    return state


def main() -> None:
    state  = ChessState.start()
    engine = MinimaxEngine(max_depth=DEFAULT_DEPTH)

    for line in sys.stdin:
        cmd = line.strip()
        if not cmd:
            continue

        if cmd == 'uci':
            sys.stdout.write(f'id name {ENGINE_NAME}\n')
            sys.stdout.write(f'id author {ENGINE_AUTHOR}\n')
            sys.stdout.write('uciok\n')
            sys.stdout.flush()

        elif cmd == 'isready':
            sys.stdout.write('readyok\n')
            sys.stdout.flush()

        elif cmd == 'ucinewgame':
            state = ChessState.start()

        elif cmd.startswith('position'):
            state = _parse_position(cmd)

        elif cmd.startswith('go'):
            toks = cmd.split()
            depth = DEFAULT_DEPTH
            if 'depth' in toks:
                try:
                    depth = int(toks[toks.index('depth') + 1])
                except (IndexError, ValueError):
                    pass

            if state.is_terminal():
                sys.stdout.write('bestmove 0000\n')
            else:
                move = MinimaxEngine(max_depth=depth).get_best_move(state)
                bm = move_to_uci(move) if move else '0000'
                sys.stdout.write(f'bestmove {bm}\n')
            sys.stdout.flush()

        elif cmd == 'quit':
            break
        # unknown commands silently ignored per UCI spec


if __name__ == '__main__':
    main()
