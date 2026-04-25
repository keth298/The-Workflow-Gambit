"""
Checkers (English Draughts): GameState implementation.

Board: 8×8. Only dark squares (r+c odd) are used.
Piece encoding:
  0   empty
  1   player +1 regular  (starts rows 0-2, moves toward row 7)
  2   player +1 king
 -1   player -1 regular  (starts rows 5-7, moves toward row 0)
 -2   player -1 king

Forced-capture rule: if any jump exists, only jumps are returned.
Promotion stops a jump chain (piece would change type mid-move).
"""

from __future__ import annotations
from typing import List, Optional, Set, Tuple

from core.game import GameState

Move = Tuple[Tuple[int, int], ...]   # ordered sequence of squares visited

BOARD_SIZE = 8
EMPTY = 0
P1    =  1   # player +1 regular
P1K   =  2   # player +1 king
P2    = -1   # player -1 regular
P2K   = -2   # player -1 king

_ALL_DIRS = [(1, -1), (1, 1), (-1, -1), (-1, 1)]


def _belongs_to(piece: int, player: int) -> bool:
    return piece != EMPTY and (piece > 0) == (player > 0)


def _forward_dirs(piece: int) -> List[Tuple[int, int]]:
    if abs(piece) == 2:
        return _ALL_DIRS
    if piece == P1:
        return [(1, -1), (1, 1)]    # P1 advances toward row 7
    return [(-1, -1), (-1, 1)]      # P2 advances toward row 0


def _initial_board() -> List[List[int]]:
    board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    for r in range(3):
        for c in range(BOARD_SIZE):
            if (r + c) % 2 == 1:
                board[r][c] = P1
    for r in range(5, 8):
        for c in range(BOARD_SIZE):
            if (r + c) % 2 == 1:
                board[r][c] = P2
    return board


class CheckersState(GameState):

    def __init__(
        self,
        board: Optional[List[List[int]]] = None,
        player: int = 1,
    ) -> None:
        self._board = board if board is not None else _initial_board()
        self._player = player

    @property
    def current_player(self) -> int:
        return self._player

    # ---- move generation -------------------------------------------------

    def get_legal_moves(self) -> List[Move]:
        jumps: List[Move] = []
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if _belongs_to(self._board[r][c], self._player):
                    jumps.extend(
                        self._collect_jumps(r, c, self._board, [(r, c)], set())
                    )
        if jumps:
            return jumps

        simples: List[Move] = []
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if _belongs_to(self._board[r][c], self._player):
                    simples.extend(self._simple_moves(r, c))
        return simples

    def _simple_moves(self, r: int, c: int) -> List[Move]:
        piece = self._board[r][c]
        moves: List[Move] = []
        for dr, dc in _forward_dirs(piece):
            nr, nc = r + dr, c + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE \
                    and self._board[nr][nc] == EMPTY:
                moves.append(((r, c), (nr, nc)))
        return moves

    def _collect_jumps(
        self,
        r: int,
        c: int,
        board: List[List[int]],
        path: List[Tuple[int, int]],
        captured: Set[Tuple[int, int]],
    ) -> List[Move]:
        piece = board[r][c]
        results: List[Move] = []

        for dr, dc in _forward_dirs(piece):
            mr, mc = r + dr, c + dc           # middle (captured) square
            lr, lc = r + 2 * dr, c + 2 * dc  # landing square

            if not (0 <= lr < BOARD_SIZE and 0 <= lc < BOARD_SIZE):
                continue
            if (mr, mc) in captured:
                continue
            mid = board[mr][mc]
            if mid == EMPTY or _belongs_to(mid, self._player):
                continue
            if board[lr][lc] != EMPTY:
                continue

            nb = [row[:] for row in board]
            nb[r][c]   = EMPTY
            nb[mr][mc] = EMPTY
            nb[lr][lc] = piece

            new_path = path + [(lr, lc)]
            new_cap   = captured | {(mr, mc)}

            # Reaching the promotion square ends the chain
            will_promote = (piece == P1 and lr == BOARD_SIZE - 1) or \
                           (piece == P2 and lr == 0)
            if will_promote:
                results.append(tuple(new_path))
            else:
                continuations = self._collect_jumps(lr, lc, nb, new_path, new_cap)
                if continuations:
                    results.extend(continuations)
                else:
                    results.append(tuple(new_path))

        return results

    # ---- state transition ------------------------------------------------

    def apply_move(self, move: Move) -> CheckersState:
        board = [row[:] for row in self._board]
        sr, sc = move[0]
        piece = board[sr][sc]
        board[sr][sc] = EMPTY

        for i in range(1, len(move)):
            pr, pc = move[i - 1]
            nr, nc = move[i]

            if abs(nr - pr) == 2:              # capture: remove middle piece
                mr, mc = (pr + nr) // 2, (pc + nc) // 2
                board[mr][mc] = EMPTY

            if i > 1:
                board[pr][pc] = EMPTY          # clear intermediate square

            board[nr][nc] = piece

        fr, fc = move[-1]
        if piece == P1 and fr == BOARD_SIZE - 1:
            board[fr][fc] = P1K
        elif piece == P2 and fr == 0:
            board[fr][fc] = P2K

        return CheckersState(board, -self._player)

    # ---- terminal / outcome ----------------------------------------------

    def is_terminal(self) -> bool:
        return self.get_winner() is not None

    def get_winner(self) -> Optional[int]:
        p1 = p2 = 0
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                p = self._board[r][c]
                if p in (P1, P1K):
                    p1 += 1
                elif p in (P2, P2K):
                    p2 += 1
        if p1 == 0:
            return -1
        if p2 == 0:
            return 1
        if not self.get_legal_moves():
            return -self._player   # no moves → current player loses
        return None

    # ---- evaluation ------------------------------------------------------

    def evaluate(self) -> float:
        winner = self.get_winner()
        if winner is not None:
            return float(winner)

        score = 0.0
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                p = self._board[r][c]
                if p == P1:
                    score += 1.0 + 0.05 * r             # reward advancement
                elif p == P1K:
                    score += 1.5
                elif p == P2:
                    score -= 1.0 + 0.05 * (BOARD_SIZE - 1 - r)
                elif p == P2K:
                    score -= 1.5

        return max(-0.99, min(0.99, score / 18.0))

    # ---- display ---------------------------------------------------------

    def __str__(self) -> str:
        sym = {EMPTY: ".", P1: "r", P1K: "R", P2: "b", P2K: "B"}
        header = "  " + " ".join(str(c) for c in range(BOARD_SIZE))
        rows = [header]
        for r in range(BOARD_SIZE):
            rows.append(
                str(r) + " " + " ".join(sym[self._board[r][c]] for c in range(BOARD_SIZE))
            )
        return "\n".join(rows)
