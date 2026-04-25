"""
UCI Runner — manages a single UCI engine subprocess.

Handles:
- Process launch and clean termination
- UCI handshake (uci / uciok / isready / readyok)
- Sending position and go commands
- Parsing bestmove with per-move timeout
- Detecting crashes, illegal moves, and timeouts
"""

from __future__ import annotations

import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import chess

from evaluator.engine_registry import EngineConfig


class MoveResult(Enum):
    OK = auto()
    ILLEGAL = auto()
    TIMEOUT = auto()
    CRASH = auto()
    NO_MOVE = auto()


@dataclass
class MoveResponse:
    result: MoveResult
    move: Optional[chess.Move] = None
    elapsed_ms: float = 0.0
    raw_response: str = ""
    error: str = ""


class UCIEngine:
    """
    Wraps a single UCI engine subprocess.

    Usage::

        with UCIEngine(engine_config) as engine:
            engine.new_game()
            response = engine.get_move(board, time_left_ms=30000, increment_ms=500)
    """

    def __init__(self, config: EngineConfig, move_timeout_s: float = 10.0):
        self.config = config
        self.move_timeout_s = move_timeout_s
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._stdout_queue: queue.Queue[Optional[str]] = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ #
    #  Context manager                                                     #
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "UCIEngine":
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """Launch the engine process and complete the UCI handshake."""
        self._proc = subprocess.Popen(
            self.config.uci_command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=self.config.working_directory or None,
        )
        # Background thread pumps stdout into a queue so reads are non-blocking
        self._stdout_queue = queue.Queue()
        self._reader_thread = threading.Thread(
            target=self._stdout_reader, daemon=True
        )
        self._reader_thread.start()
        self._handshake()

    def stop(self) -> None:
        """Send quit and terminate the process."""
        if self._proc and self._proc.poll() is None:
            try:
                self._send("quit")
                self._proc.wait(timeout=3)
            except Exception:
                pass
            finally:
                self._proc.kill()
        self._proc = None

    @property
    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    # ------------------------------------------------------------------ #
    #  Background stdout reader                                            #
    # ------------------------------------------------------------------ #

    def _stdout_reader(self) -> None:
        """Runs in a daemon thread; pushes lines from stdout into the queue."""
        try:
            for line in self._proc.stdout:
                self._stdout_queue.put(line.rstrip("\n"))
        except Exception:
            pass
        finally:
            self._stdout_queue.put(None)  # sentinel: process ended

    # ------------------------------------------------------------------ #
    #  UCI protocol                                                        #
    # ------------------------------------------------------------------ #

    def _send(self, text: str) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.stdin.write(text + "\n")
            self._proc.stdin.flush()

    def _read_until(self, token: str, timeout_s: float = 5.0) -> list[str]:
        """Read lines from the queue until one contains *token*."""
        lines: list[str] = []
        deadline = time.monotonic() + timeout_s
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Engine '{self.config.engine_id}' did not produce "
                    f"'{token}' within {timeout_s}s"
                )
            try:
                line = self._stdout_queue.get(timeout=min(remaining, 0.1))
            except queue.Empty:
                if self._proc and self._proc.poll() is not None:
                    raise RuntimeError(
                        f"Engine '{self.config.engine_id}' crashed while waiting for '{token}'"
                    )
                continue
            if line is None:
                raise RuntimeError(
                    f"Engine '{self.config.engine_id}' stdout closed while waiting for '{token}'"
                )
            lines.append(line)
            if token in line:
                return lines

    def _handshake(self) -> None:
        self._send("uci")
        self._read_until("uciok", timeout_s=5.0)
        # Apply any configured UCI options
        for key, value in self.config.uci_options.items():
            self._send(f"setoption name {key} value {value}")
        self._send("isready")
        self._read_until("readyok", timeout_s=5.0)

    def new_game(self) -> None:
        """Signal the start of a new game."""
        self._send("ucinewgame")
        self._send("isready")
        self._read_until("readyok", timeout_s=5.0)

    # ------------------------------------------------------------------ #
    #  Move request                                                        #
    # ------------------------------------------------------------------ #

    def get_move(
        self,
        board: chess.Board,
        time_left_ms: int = 30_000,
        increment_ms: int = 500,
        max_move_ms: Optional[int] = None,
    ) -> MoveResponse:
        """
        Ask the engine to make a move given the current board state.

        Returns a MoveResponse describing the outcome.
        """
        if not self.is_alive:
            return MoveResponse(result=MoveResult.CRASH, error="Engine not running")

        # Build position command
        if board.move_stack:
            moves_str = " ".join(m.uci() for m in board.move_stack)
            pos_cmd = f"position startpos moves {moves_str}"
        else:
            pos_cmd = "position startpos"

        # Build go command
        wtime = time_left_ms if board.turn == chess.WHITE else time_left_ms
        btime = time_left_ms if board.turn == chess.BLACK else time_left_ms
        winc = increment_ms
        binc = increment_ms

        if self.config.max_search_depth is not None:
            go_cmd = f"go depth {self.config.max_search_depth}"
        else:
            go_parts = ["go", f"wtime {wtime}", f"btime {btime}",
                        f"winc {winc}", f"binc {binc}"]
            if max_move_ms:
                go_parts.append(f"movetime {max_move_ms}")
            go_cmd = " ".join(go_parts)

        t_start = time.monotonic()

        try:
            self._send(pos_cmd)
            self._send(go_cmd)
        except Exception as exc:
            return MoveResponse(result=MoveResult.CRASH, error=str(exc))

        # Read until bestmove with timeout — non-blocking via queue
        effective_timeout = (
            min(max_move_ms / 1000.0, self.move_timeout_s)
            if max_move_ms
            else self.move_timeout_s
        )

        best_move_str: Optional[str] = None
        raw_lines: list[str] = []
        deadline = time.monotonic() + effective_timeout

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return MoveResponse(
                    result=MoveResult.TIMEOUT,
                    elapsed_ms=(time.monotonic() - t_start) * 1000,
                    raw_response="\n".join(raw_lines),
                    error="Move timeout",
                )
            try:
                line = self._stdout_queue.get(timeout=min(remaining, 0.05))
            except queue.Empty:
                if self._proc and self._proc.poll() is not None:
                    return MoveResponse(
                        result=MoveResult.CRASH,
                        elapsed_ms=(time.monotonic() - t_start) * 1000,
                        raw_response="\n".join(raw_lines),
                        error="Engine process terminated unexpectedly",
                    )
                continue

            if line is None:
                # stdout closed — process ended
                return MoveResponse(
                    result=MoveResult.CRASH,
                    elapsed_ms=(time.monotonic() - t_start) * 1000,
                    raw_response="\n".join(raw_lines),
                    error="Engine stdout closed unexpectedly",
                )

            raw_lines.append(line)
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2 and parts[1] != "(none)":
                    best_move_str = parts[1]
                break

        elapsed_ms = (time.monotonic() - t_start) * 1000

        # Validate move legality
        try:
            move = chess.Move.from_uci(best_move_str)
        except ValueError:
            return MoveResponse(
                result=MoveResult.ILLEGAL,
                elapsed_ms=elapsed_ms,
                raw_response="\n".join(raw_lines),
                error=f"Malformed UCI move: {best_move_str!r}",
            )

        if move not in board.legal_moves:
            return MoveResponse(
                result=MoveResult.ILLEGAL,
                move=move,
                elapsed_ms=elapsed_ms,
                raw_response="\n".join(raw_lines),
                error=f"Illegal move: {best_move_str} in position {board.fen()}",
            )

        return MoveResponse(
            result=MoveResult.OK,
            move=move,
            elapsed_ms=elapsed_ms,
            raw_response="\n".join(raw_lines),
        )

    # ------------------------------------------------------------------ #
    #  Stockfish-style evaluation request (for blunder analysis)          #
    # ------------------------------------------------------------------ #

    def evaluate_position(
        self, board: chess.Board, depth: int = 15, timeout_s: float = 10.0
    ) -> Optional[int]:
        """
        Request a centipawn evaluation for a position (engines that support it).

        Returns the score in centipawns from the perspective of the side to move,
        or None if the engine doesn't provide one.
        """
        if not self.is_alive:
            return None

        if board.move_stack:
            moves_str = " ".join(m.uci() for m in board.move_stack)
            pos_cmd = f"position startpos moves {moves_str}"
        else:
            pos_cmd = "position startpos"

        self._send(pos_cmd)
        self._send(f"go depth {depth}")

        score: Optional[int] = None
        deadline = time.monotonic() + timeout_s

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                line = self._stdout_queue.get(timeout=min(remaining, 0.05))
            except queue.Empty:
                if self._proc and self._proc.poll() is not None:
                    break
                continue
            if line is None:
                break
            if "score cp" in line:
                parts = line.split()
                idx = parts.index("cp")
                try:
                    score = int(parts[idx + 1])
                except (IndexError, ValueError):
                    pass
            elif "score mate" in line:
                parts = line.split()
                idx = parts.index("mate")
                try:
                    mate_in = int(parts[idx + 1])
                    score = 30000 if mate_in > 0 else -30000
                except (IndexError, ValueError):
                    pass
            if line.startswith("bestmove"):
                break

        return score
