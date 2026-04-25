# uci.py — UCI protocol shell

import sys
from board import Board, START_FEN, uci_to_move, move_to_uci
from search import search

def log(msg):
    print(msg, file=sys.stderr, flush=True)

def uci_loop():
    board = Board.from_fen()

    while True:
        try:
            line = input().strip()
        except EOFError:
            break
        if not line:
            continue

        if line == 'uci':
            print('id name PhaseEngine')
            print('id author Team')
            print('uciok')
            sys.stdout.flush()

        elif line == 'isready':
            print('readyok')
            sys.stdout.flush()

        elif line == 'ucinewgame':
            import tt as TT
            TT.clear()
            board = Board.from_fen()

        elif line.startswith('position'):
            board = _parse_position(line)

        elif line.startswith('go'):
            movetime = _parse_movetime(line, board.side)
            mv = search(board, movetime_ms=movetime)
            print(f'bestmove {move_to_uci(mv) if mv else "0000"}')
            sys.stdout.flush()

        elif line == 'quit':
            break

        elif line == 'd':
            # Debug: print board
            log(str(board))

def _parse_movetime(line, side):
    """Extract a millisecond budget from a 'go' command."""
    from board import WHITE
    parts = line.split()
    # movetime takes priority
    if 'movetime' in parts:
        return int(parts[parts.index('movetime') + 1])
    # time+increment
    time_key = 'wtime' if side == WHITE else 'btime'
    inc_key  = 'winc'  if side == WHITE else 'binc'
    t = int(parts[parts.index(time_key) + 1]) if time_key in parts else None
    inc = int(parts[parts.index(inc_key) + 1]) if inc_key in parts else 0
    if t is not None:
        return max(50, t // 30 + inc)
    return 1000  # default 1 second

def _parse_position(line):
    parts = line.split()
    idx = 1

    if parts[idx] == 'startpos':
        board = Board.from_fen()
        idx += 1
    elif parts[idx] == 'fen':
        fen = ' '.join(parts[idx+1:idx+7])
        board = Board.from_fen(fen)
        idx += 7
    else:
        board = Board.from_fen()

    if idx < len(parts) and parts[idx] == 'moves':
        for uci in parts[idx+1:]:
            mv = uci_to_move(uci, board)
            if mv is not None:
                board.make(mv)
            else:
                log(f'WARNING: could not parse move {uci}')

    return board
