#!/usr/bin/env python3
from __future__ import annotations
import sys
import chess
import search
from time_manager import TimeBudget

NAME = "PhasedEngine"
AUTHOR = "JD"


class UCIEngine:
    def __init__(self) -> None:
        self.board = chess.Board()

    def run(self) -> None:
        for line in sys.stdin:
            self._handle(line.strip())

    def _send(self, msg: str) -> None:
        print(msg, flush=True)

    def _log(self, msg: str) -> None:
        print(msg, file=sys.stderr, flush=True)

    def _handle(self, line: str) -> None:
        if not line:
            return
        tokens = line.split()
        cmd = tokens[0]

        if cmd == "uci":
            self._send(f"id name {NAME}")
            self._send(f"id author {AUTHOR}")
            self._send("uciok")
        elif cmd == "isready":
            self._send("readyok")
        elif cmd == "ucinewgame":
            self.board = chess.Board()
            search.tt.clear()
        elif cmd == "position":
            self._position(tokens[1:])
        elif cmd == "go":
            self._go(tokens[1:])
        elif cmd == "quit":
            sys.exit(0)

    def _position(self, tokens: list[str]) -> None:
        if not tokens:
            return

        if tokens[0] == "startpos":
            self.board = chess.Board()
            moves = tokens[2:] if len(tokens) > 1 and tokens[1] == "moves" else []
        elif tokens[0] == "fen":
            try:
                i = 1
                fen_parts: list[str] = []
                while i < len(tokens) and tokens[i] != "moves":
                    fen_parts.append(tokens[i])
                    i += 1
                self.board = chess.Board(" ".join(fen_parts))
                moves = tokens[i + 1:] if i < len(tokens) else []
            except Exception as e:
                self._log(f"invalid fen: {e}")
                return
        else:
            return

        for uci_str in moves:
            try:
                move = chess.Move.from_uci(uci_str)
                if move in self.board.legal_moves:
                    self.board.push(move)
                else:
                    self._log(f"illegal move skipped: {uci_str}")
                    break
            except Exception as e:
                self._log(f"bad move {uci_str}: {e}")
                break

    def _go(self, tokens: list[str]) -> None:
        params: dict[str, int] = {}
        i = 0
        while i < len(tokens):
            key = tokens[i]
            if i + 1 < len(tokens):
                try:
                    params[key] = int(tokens[i + 1])
                    i += 2
                    continue
                except ValueError:
                    pass
            i += 1

        budget = TimeBudget(
            wtime_ms=params.get("wtime"),
            btime_ms=params.get("btime"),
            winc_ms=params.get("winc", 0),
            binc_ms=params.get("binc", 0),
            movetime_ms=params.get("movetime"),
            depth_limit=params.get("depth"),
            turn=self.board.turn,
        )

        if self.board.is_game_over():
            self._send("bestmove 0000")
            return

        move = search.best_move(self.board, budget)
        self._send(f"bestmove {move.uci() if move else '0000'}")


if __name__ == "__main__":
    UCIEngine().run()
