#!/usr/bin/env python3
from __future__ import annotations
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# torch must be imported and pinned to single-threaded BEFORE faiss loads its
# own OpenMP runtime, otherwise both libraries conflict and segfault on macOS.
import torch
torch.set_num_threads(1)

"""
RAG Chess Engine — UCI entry point.

Architecture summary
--------------------
1. Opening book  (O(1) hash lookup from SQLite move_stats)
2. FAISS retrieval  (cosine-similarity KNN → position eval + move priors)
3. Neural network  (value + policy; small MLP trained on game outcomes)
4. Alpha-beta search  (iterative deepening, ~3-6 ply in real time)

The evaluation at each leaf is a blend of retrieval and neural output,
weighted by the retrieval confidence (how many similar positions were found).

UCI commands implemented
------------------------
uci  isready  ucinewgame  position  go  stop  quit
"""

import sys
import threading
import time
from pathlib import Path

import chess

sys.path.insert(0, str(Path(__file__).parent))
from opening_book import OpeningBook
from retrieval     import RetrievalEngine
from evaluator     import NeuralEvaluator
from search        import Searcher

# ── Time management ───────────────────────────────────────────────────────────

DEFAULT_MOVE_MS = 3_000   # fallback: 3 s


def _allocate_time(params: dict) -> int:
    """Return milliseconds to think for this move."""
    wtime  = int(params.get("wtime",  0))
    btime  = int(params.get("btime",  0))
    winc   = int(params.get("winc",   0))
    binc   = int(params.get("binc",   0))
    mvtime = int(params.get("movetime", 0))
    movestogo = int(params.get("movestogo", 0))

    if mvtime:
        return max(10, mvtime - 50)   # leave 50 ms overhead

    # Decide which clock to use
    our_time = wtime   # will be corrected to btime inside the engine loop
    our_inc  = winc

    if our_time <= 0:
        return DEFAULT_MOVE_MS

    if movestogo > 0:
        alloc = our_time // movestogo + our_inc // 2
    else:
        # Assume ~40 remaining moves
        alloc = our_time // 40 + our_inc // 2

    return max(50, min(alloc, our_time - 100))


# ── UCI engine ────────────────────────────────────────────────────────────────

class RAGEngine:
    NAME   = "RAGChess"
    AUTHOR = "Point72Hackathon"

    def __init__(self) -> None:
        self._board     = chess.Board()
        self._book      = OpeningBook()
        self._retrieval = RetrievalEngine()
        self._neural    = NeuralEvaluator()
        self._searcher  = Searcher(self._neural, self._retrieval)
        self._search_thread: threading.Thread | None = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _parse_position(self, tokens: list[str]) -> None:
        if not tokens:
            return
        if tokens[0] == "startpos":
            self._board = chess.Board()
            rest = tokens[2:] if len(tokens) > 1 and tokens[1] == "moves" else []
        elif tokens[0] == "fen":
            fen_parts: list[str] = []
            i = 1
            while i < len(tokens) and tokens[i] != "moves":
                fen_parts.append(tokens[i])
                i += 1
            self._board = chess.Board(" ".join(fen_parts))
            rest = tokens[i + 1:] if i < len(tokens) and tokens[i] == "moves" else []
        else:
            return

        for uci_move in rest:
            try:
                self._board.push(chess.Move.from_uci(uci_move))
            except Exception:
                break

    def _parse_go_params(self, tokens: list[str]) -> dict:
        params: dict = {}
        i = 0
        while i < len(tokens):
            key = tokens[i]
            if i + 1 < len(tokens):
                try:
                    params[key] = tokens[i + 1]
                    i += 2
                    continue
                except Exception:
                    pass
            i += 1
        return params

    # ── Search thread ─────────────────────────────────────────────────────────

    def _run_search(self, time_ms: int) -> None:
        board_copy = self._board.copy()

        # 1. Opening book
        book_move = self._book.lookup(board_copy)
        if book_move:
            print(f"bestmove {book_move}", flush=True)
            return

        # 2. Iterative-deepening search (blends retrieval + neural)
        best = self._searcher.search(board_copy, time_ms)
        uci  = best.uci() if best else "0000"
        print(f"bestmove {uci}", flush=True)

    # ── Command handlers ──────────────────────────────────────────────────────

    def handle(self, line: str) -> bool:
        """Process one UCI line. Returns False on 'quit'."""
        tokens = line.split()
        if not tokens:
            return True
        cmd = tokens[0]

        if cmd == "uci":
            print(f"id name {self.NAME}")
            print(f"id author {self.AUTHOR}")
            print("uciok", flush=True)

        elif cmd == "isready":
            # Eagerly load all components on first isready so 'go' is instant
            _ = self._book.lookup(chess.Board())
            _ = self._retrieval.confidence(chess.Board())
            _ = self._neural.evaluate(chess.Board())
            print("readyok", flush=True)

        elif cmd == "ucinewgame":
            self._board = chess.Board()
            self._searcher._tt.clear()

        elif cmd == "position":
            self._parse_position(tokens[1:])

        elif cmd == "go":
            params = self._parse_go_params(tokens[1:])
            # Correct clock to side to move
            if self._board.turn == chess.BLACK:
                params["wtime"] = params.pop("btime", params.get("wtime", "0"))
                params["winc"]  = params.pop("binc",  params.get("winc",  "0"))
            time_ms = _allocate_time(params)

            # Run search in background so we can handle 'stop'
            self._search_thread = threading.Thread(
                target=self._run_search, args=(time_ms,), daemon=True
            )
            self._search_thread.start()

        elif cmd == "stop":
            self._searcher._stop = True
            if self._search_thread:
                self._search_thread.join(timeout=2.0)

        elif cmd == "quit":
            return False

        return True

    def run(self) -> None:
        while True:
            try:
                line = sys.stdin.readline()
            except EOFError:
                break
            if not line:
                break
            if not self.handle(line.strip()):
                break


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    RAGEngine().run()
