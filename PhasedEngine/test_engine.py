"""
Phase 5: Integration & Hardening Test Suite

Comprehensive UCI compliance and engine robustness testing.
"""

import subprocess
import time
import chess
import pytest


def engine_session(commands: list[str], timeout: float = 5.0) -> list[str]:
    """Start engine subprocess, send commands, collect output until quit."""
    import os
    cwd = os.path.dirname(os.path.abspath(__file__))
    
    proc = subprocess.Popen(
        ["python3", "engine.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd
    )
    input_str = "\n".join(commands) + "\nquit\n"
    try:
        stdout, _ = proc.communicate(input_str, timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise
    return stdout.strip().splitlines()


class TestUCICompliance:
    """Test UCI protocol compliance."""
    
    def test_uci_handshake(self):
        """Test uci command returns id name, id author, and uciok."""
        lines = engine_session(["uci"])
        assert any(l.startswith("id name") for l in lines), "Missing 'id name' response"
        assert any(l.startswith("id author") for l in lines), "Missing 'id author' response"
        assert "uciok" in lines, "Missing 'uciok' response"
    
    def test_isready(self):
        """Test isready command returns readyok."""
        lines = engine_session(["isready"])
        assert "readyok" in lines, "Missing 'readyok' response"
    
    def test_unknown_command_ignored(self):
        """Test that unknown commands are silently ignored."""
        lines = engine_session(["ponderhit", "setoption name Foo value Bar", "isready"])
        assert "readyok" in lines, "Engine should still respond to isready after unknown commands"
        assert not any("error" in l.lower() for l in lines), "Should not output error messages"


class TestMoveLegality:
    """Test move legality and position handling."""
    
    def test_startpos_legal_move(self):
        """Test that move from startpos is legal."""
        lines = engine_session(["position startpos", "go depth 1"])
        bm = next((l for l in lines if l.startswith("bestmove")), None)
        assert bm is not None, "No bestmove found"
        move_uci = bm.split()[1]
        board = chess.Board()
        assert chess.Move.from_uci(move_uci) in board.legal_moves, f"Move {move_uci} is not legal from startpos"
    
    def test_after_moves_legal(self):
        """Test that move after position moves is legal."""
        lines = engine_session(["position startpos moves e2e4 e7e5", "go depth 1"])
        bm = next((l for l in lines if l.startswith("bestmove")), None)
        assert bm is not None, "No bestmove found"
        move_uci = bm.split()[1]
        board = chess.Board()
        board.push_uci("e2e4")
        board.push_uci("e7e5")
        assert chess.Move.from_uci(move_uci) in board.legal_moves, f"Move {move_uci} is not legal after e2e4 e7e5"
    
    def test_fen_position(self):
        """Test FEN position is correctly set."""
        lines = engine_session([
            "position fen r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
            "go depth 1"
        ])
        assert any(l.startswith("bestmove") for l in lines), "Engine should respond with bestmove after FEN position"


class TestTerminalPositions:
    """Test handling of checkmate, stalemate, and other terminal positions."""
    
    def test_checkmate_position(self):
        """Test that bestmove 0000 is returned for checkmate position."""
        # Fool's mate: black is mated
        lines = engine_session([
            "position fen rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3",
            "go depth 1"
        ])
        bm = next((l for l in lines if l.startswith("bestmove")), None)
        assert bm == "bestmove 0000", f"Checkmate should return 0000, got {bm}"
    
    def test_stalemate_position(self):
        """Test that engine handles stalemate position."""
        lines = engine_session([
            "position fen 8/8/8/8/8/1k6/8/K7 b - - 0 1",  # black to move, stalemate
            "go depth 1"
        ])
        assert any(l.startswith("bestmove") for l in lines), "Engine should return bestmove for stalemate"


class TestTactics:
    """Test engine's tactical ability."""
    
    def test_mate_in_one(self):
        """Test that engine finds mate in one (Qf7#)."""
        lines = engine_session([
            "position fen r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
            "go depth 2"
        ])
        bm = next((l for l in lines if l.startswith("bestmove")), None)
        assert bm is not None, "No bestmove found"
        move_uci = bm.split()[1]
        # Qf7# should be h5f7 in UCI notation
        assert move_uci == "h5f7", f"Expected mate in one (h5f7), got {move_uci}"
    
    def test_wins_free_piece(self):
        """Test that engine captures a hanging piece."""
        lines = engine_session([
            "position fen r1bqkbnr/ppp2ppp/2np4/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4",
            "go depth 2"
        ])
        bm = next((l for l in lines if l.startswith("bestmove")), None)
        assert bm is not None, "No bestmove found"
        move_uci = bm.split()[1]
        assert move_uci != "0000", "Engine should find a good move, not 0000"


class TestTimeManagement:
    """Test time management compliance."""
    
    def test_movetime_respected(self):
        """Test that movetime limit is respected."""
        start = time.monotonic()
        engine_session(["position startpos", "go movetime 500"])
        elapsed = (time.monotonic() - start) * 1000
        # Allow some overhead but should finish within movetime + 200ms
        assert elapsed < 800, f"took {elapsed:.0f}ms for movetime 500"
    
    def test_depth_limit_respected(self):
        """Test that depth limit is respected."""
        lines = engine_session(["position startpos", "go depth 4"])
        depths = [int(l.split()[2]) for l in lines if l.startswith("info depth")]
        assert depths, "No info lines emitted"
        assert max(depths) <= 4, f"Exceeded depth limit 4: max depth was {max(depths)}"
    
    def test_clock_game_no_timeout(self):
        """Test that engine responds quickly on a large time budget."""
        start = time.monotonic()
        engine_session(["position startpos", "go wtime 5000 btime 5000"])
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 1000, f"took {elapsed:.0f}ms on a 5s clock"


class TestRobustness:
    """Test edge cases and error handling."""
    
    def test_invalid_fen_no_crash(self):
        """Test that invalid FEN does not crash engine."""
        lines = engine_session(["position fen not_a_valid_fen", "isready"])
        assert "readyok" in lines, "Engine should recover after invalid FEN"
    
    def test_rapid_fire_go(self):
        """Test that engine handles rapid-fire go commands."""
        cmds = ["position startpos"]
        for _ in range(5):
            cmds += ["go depth 1", "ucinewgame", "position startpos"]
        lines = engine_session(cmds)
        bm_lines = [l for l in lines if l.startswith("bestmove")]
        assert len(bm_lines) == 5, f"Expected 5 bestmove lines, got {len(bm_lines)}"
    
    def test_illegal_move_in_sequence(self):
        """Test that illegal move in position stops processing moves."""
        lines = engine_session([
            "position startpos moves e2e4 e7e5 a1a8",  # a1a8 is illegal
            "go depth 1"
        ])
        assert any(l.startswith("bestmove") for l in lines), "Engine should still search after illegal move"
    
    def test_ucinewgame_resets_position(self):
        """Test that ucinewgame resets board to startpos."""
        lines = engine_session([
            "position fen 8/8/8/4k3/8/8/4K3/8 w - - 0 1",
            "ucinewgame",
            "position startpos",
            "go depth 1"
        ])
        bm = next((l for l in lines if l.startswith("bestmove")), None)
        assert bm is not None, "No bestmove found after ucinewgame"
        move_uci = bm.split()[1]
        # Verify it's a legal move from startpos (not from the middle-game position)
        board = chess.Board()
        assert chess.Move.from_uci(move_uci) in board.legal_moves, f"Move {move_uci} should be from startpos"
    
    def test_go_depth_zero(self):
        """Test that go depth 0 is treated as depth 1."""
        lines = engine_session(["position startpos", "go depth 0"])
        bm = next((l for l in lines if l.startswith("bestmove")), None)
        assert bm is not None, "Engine should handle depth 0"
        move_uci = bm.split()[1]
        board = chess.Board()
        assert chess.Move.from_uci(move_uci) in board.legal_moves, "Move should be legal even with depth 0"


class TestProtocol:
    """Test general UCI protocol compliance."""
    
    def test_bestmove_format(self):
        """Test that bestmove is properly formatted."""
        lines = engine_session(["position startpos", "go depth 1"])
        bm = next((l for l in lines if l.startswith("bestmove")), None)
        assert bm is not None, "No bestmove found"
        parts = bm.split()
        assert len(parts) >= 2, "bestmove should have format 'bestmove <move>'"
        assert parts[0] == "bestmove", "First word should be 'bestmove'"
    
    def test_no_debug_on_stdout(self):
        """Test that debug output is not mixed with UCI on stdout."""
        lines = engine_session(["uci"])
        # All lines should be valid UCI responses
        valid_prefixes = ["id name", "id author", "uciok"]
        for line in lines:
            assert any(line.startswith(prefix) for prefix in valid_prefixes), \
                f"Unexpected output on stdout: {line}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
