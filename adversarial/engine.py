#!/usr/bin/env python3
import sys
import chess
from search import iterative_deepening
from time_manager import TimeManager

ENGINE_NAME = "AdversarialEngine v1"
ENGINE_AUTHOR = "Point72Hackathon"
DEFAULT_DEPTH = 3


class Engine:
    def __init__(self):
        self.board = chess.Board()
        self.time_manager = TimeManager()

    def run(self):
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            tokens = line.strip().split()
            if not tokens:
                continue
            cmd = tokens[0]
            if cmd == "uci":
                self._handle_uci()
            elif cmd == "isready":
                self._handle_isready()
            elif cmd == "ucinewgame":
                self._handle_ucinewgame()
            elif cmd == "position":
                self._handle_position(tokens[1:])
            elif cmd == "go":
                self._handle_go(tokens[1:])
            elif cmd == "quit":
                break

    def _send(self, msg: str) -> None:
        print(msg, flush=True)

    def _log(self, msg: str) -> None:
        print(msg, file=sys.stderr, flush=True)

    def _handle_uci(self) -> None:
        self._send(f"id name {ENGINE_NAME}")
        self._send(f"id author {ENGINE_AUTHOR}")
        self._send("uciok")

    def _handle_isready(self) -> None:
        self._send("readyok")

    def _handle_ucinewgame(self) -> None:
        self.board = chess.Board()

    def _handle_position(self, tokens: list[str]) -> None:
        if not tokens:
            return
        if tokens[0] == "startpos":
            self.board = chess.Board()
            move_tokens = tokens[2:] if len(tokens) > 1 and tokens[1] == "moves" else []
        elif tokens[0] == "fen":
            fen_parts = []
            i = 1
            while i < len(tokens) and tokens[i] != "moves":
                fen_parts.append(tokens[i])
                i += 1
            self.board = chess.Board(" ".join(fen_parts))
            move_tokens = tokens[i + 1:] if i < len(tokens) and tokens[i] == "moves" else []
        else:
            return

        for uci_move in move_tokens:
            self.board.push_uci(uci_move)

    def _handle_go(self, tokens: list[str]) -> None:
        params: dict = {}
        i = 0
        while i < len(tokens):
            key = tokens[i]
            if key in ("wtime", "btime", "winc", "binc", "movestogo", "movetime", "depth"):
                if i + 1 < len(tokens):
                    params[key] = int(tokens[i + 1])
                    i += 2
                    continue
            i += 1

        target_ms, max_ms = self.time_manager.allocate(
            wtime=params.get("wtime"),
            btime=params.get("btime"),
            winc=params.get("winc", 0),
            binc=params.get("binc", 0),
            movestogo=params.get("movestogo"),
            movetime=params.get("movetime"),
            depth=params.get("depth"),
            side_to_move=(self.board.turn == chess.WHITE),
        )

        search_depth = params.get("depth", DEFAULT_DEPTH)
        time_limit = target_ms

        move = iterative_deepening(self.board, search_depth, time_limit)

        if move is None:
            legal = list(self.board.legal_moves)
            move = legal[0] if legal else None

        self._send(f"bestmove {move.uci() if move else '0000'}")


if __name__ == "__main__":
    Engine().run()
