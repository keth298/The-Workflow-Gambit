import subprocess
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class TestResult:
    name: str
    fen: str
    expected_move: str
    engine_move: str
    passed: bool
    depth_searched: int
    time_ms: float


class EngineTester:
    def __init__(self, engine_path: str):
        self.engine_path = engine_path
        self._proc: Optional[subprocess.Popen] = None

    def _start(self):
        self._proc = subprocess.Popen(
            ["python3", self.engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

    def _send(self, cmd: str):
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("engine process is not running")
        self._proc.stdin.write(cmd + "\n")
        self._proc.stdin.flush()

    def _read_until(self, keyword: str, timeout: float = 10.0) -> list[str]:
        lines = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self._proc.stdout.readline()
            if not line:
                break
            line = line.rstrip()
            lines.append(line)
            if line.startswith(keyword):
                return lines
        return lines

    def check_uci_compliance(self) -> bool:
        try:
            self._start()
            self._send("uci")
            lines = self._read_until("uciok", timeout=5.0)
            uciok = any(l.strip() == "uciok" for l in lines)
            self._send("isready")
            lines2 = self._read_until("readyok", timeout=5.0)
            readyok = any(l.strip() == "readyok" for l in lines2)
            return uciok and readyok
        except Exception:
            return False
        finally:
            self.close()

    def run_position(
        self,
        fen: str,
        depth: int = 5,
        movetime_ms: Optional[int] = None,
        timeout_s: float = 30.0,
    ) -> str:
        self._send("ucinewgame")
        self._send(f"position fen {fen}")
        if movetime_ms is not None:
            self._send(f"go movetime {movetime_ms}")
        else:
            self._send(f"go depth {depth}")
        lines = self._read_until("bestmove", timeout=timeout_s)
        for line in reversed(lines):
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
        return ""

    def run_batch(self, positions: list[dict], timeout_s: float = 30.0) -> list[TestResult]:
        self._start()
        self._send("uci")
        self._read_until("uciok", timeout=5.0)
        self._send("isready")
        self._read_until("readyok", timeout=5.0)

        results = []
        for pos in positions:
            name = pos["name"]
            fen = pos["fen"]
            expected = pos["expected"]
            depth = pos.get("depth", 5)
            movetime = pos.get("movetime_ms")

            t0 = time.time()
            move = self.run_position(
                fen,
                depth=depth,
                movetime_ms=movetime,
                timeout_s=timeout_s,
            )
            elapsed_ms = (time.time() - t0) * 1000

            results.append(TestResult(
                name=name,
                fen=fen,
                expected_move=expected,
                engine_move=move,
                passed=(move == expected),
                depth_searched=depth,
                time_ms=elapsed_ms,
            ))
        self.close()
        return results

    def close(self):
        if self._proc and self._proc.poll() is None:
            try:
                self._send("quit")
            except Exception:
                pass
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
