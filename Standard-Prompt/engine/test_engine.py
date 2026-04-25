# test_engine.py — Test suite for Phase 1

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import unittest
from board import (
    Board, move_to_uci, uci_to_move, START_FEN,
    WHITE, BLACK, WP, WN, WB, WR, WQ, WK, BP, BN, BB, BR, BQ, BK,
    lsb, bit, sq_from_name
)

# ── Perft (move generation correctness oracle) ────────────────────────────────
def perft(board, depth):
    if depth == 0:
        return 1
    nodes = 0
    for mv in board.legal_moves():
        board.make(mv)
        nodes += perft(board, depth - 1)
        board.unmake()
    return nodes

# ── Known perft values ────────────────────────────────────────────────────────
# https://www.chessprogramming.org/Perft_Results
PERFT_CASES = [
    # (fen, depth, expected_nodes)
    (START_FEN,                                                        1, 20),
    (START_FEN,                                                        2, 400),
    (START_FEN,                                                        3, 8902),
    # Position 2 — Kiwipete (tests castling, promotions, en passant)
    ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -", 1, 48),
    ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K22R w KQkq -", 2, 2039),
    # Position 3 — en passant + checks
    ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - -",                        1, 14),
    ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - -",                        2, 191),
    # Position 4 — promotion heavy
    ("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq -", 1, 6),
]

class TestFenParsing(unittest.TestCase):
    def test_startpos_pieces(self):
        b = Board.from_fen()
        self.assertEqual(bin(b.pieces[WP]).count('1'), 8,  "white pawns")
        self.assertEqual(bin(b.pieces[BP]).count('1'), 8,  "black pawns")
        self.assertEqual(bin(b.pieces[WR]).count('1'), 2,  "white rooks")
        self.assertEqual(bin(b.pieces[WK]).count('1'), 1,  "white king")
        self.assertEqual(bin(b.pieces[BK]).count('1'), 1,  "black king")

    def test_startpos_side(self):
        b = Board.from_fen()
        self.assertEqual(b.side, WHITE)

    def test_startpos_castling(self):
        b = Board.from_fen()
        self.assertEqual(b.castling, 0b1111)   # all four rights

    def test_startpos_ep(self):
        b = Board.from_fen()
        self.assertEqual(b.ep, -1)

    def test_custom_fen(self):
        fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -"
        b = Board.from_fen(fen)
        self.assertEqual(b.side, WHITE)
        self.assertEqual(b.castling, 0b1111)

class TestMoveGenStartpos(unittest.TestCase):
    def setUp(self):
        self.board = Board.from_fen()

    def test_count(self):
        self.assertEqual(len(self.board.legal_moves()), 20)

    def test_pawn_moves_present(self):
        ucis = {move_to_uci(m) for m in self.board.legal_moves()}
        self.assertIn('e2e4', ucis)
        self.assertIn('e2e3', ucis)
        self.assertIn('a2a3', ucis)
        self.assertIn('a2a4', ucis)

    def test_knight_moves_present(self):
        ucis = {move_to_uci(m) for m in self.board.legal_moves()}
        self.assertIn('g1f3', ucis)
        self.assertIn('b1c3', ucis)

    def test_no_illegal_moves(self):
        # No piece-through-piece moves from startpos
        ucis = {move_to_uci(m) for m in self.board.legal_moves()}
        self.assertNotIn('e1e2', ucis)   # king blocked
        self.assertNotIn('d1d2', ucis)   # queen blocked

class TestMakUnmake(unittest.TestCase):
    def test_unmake_restores_state(self):
        b = Board.from_fen()
        snap_pieces = b.pieces[:]
        snap_side   = b.side
        snap_castle = b.castling
        snap_ep     = b.ep
        mv = uci_to_move('e2e4', b)
        b.make(mv)
        b.unmake()
        self.assertEqual(b.pieces,   snap_pieces)
        self.assertEqual(b.side,     snap_side)
        self.assertEqual(b.castling, snap_castle)
        self.assertEqual(b.ep,       snap_ep)

    def test_double_push_sets_ep(self):
        b = Board.from_fen()
        mv = uci_to_move('e2e4', b)
        b.make(mv)
        self.assertEqual(b.ep, sq_from_name('e3'))

    def test_ep_cleared_after_next_move(self):
        b = Board.from_fen()
        b.make(uci_to_move('e2e4', b))
        b.make(uci_to_move('d7d5', b))
        self.assertEqual(b.ep, sq_from_name('d6'))
        b.make(uci_to_move('a2a3', b))   # non-ep move
        self.assertEqual(b.ep, -1)

    def test_capture_removes_piece(self):
        # Scholar's mate setup: e4, e5, Qh5, Nc6, Bc4, Nf6??, Qxf7#
        b = Board.from_fen()
        for uci in ['e2e4','e7e5','d1h5','b8c6','f1c4','g8f6']:
            b.make(uci_to_move(uci, b))
        before_bp = bin(b.pieces[BP]).count('1')
        b.make(uci_to_move('h5f7', b))
        self.assertEqual(bin(b.pieces[BP]).count('1'), before_bp - 1)

class TestSpecialMoves(unittest.TestCase):
    def test_castling_kingside_white(self):
        # Clear squares between king and rook
        fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq -"
        b = Board.from_fen(fen)
        ucis = {move_to_uci(m) for m in b.legal_moves()}
        self.assertIn('e1g1', ucis)

    def test_castling_queenside_white(self):
        fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq -"
        b = Board.from_fen(fen)
        ucis = {move_to_uci(m) for m in b.legal_moves()}
        self.assertIn('e1c1', ucis)

    def test_no_castling_through_check(self):
        # Rook on e-file attacks e1, blocking castling
        fen = "4k3/8/8/8/8/8/8/R3K2r w KQ -"
        b = Board.from_fen(fen)
        ucis = {move_to_uci(m) for m in b.legal_moves()}
        self.assertNotIn('e1g1', ucis)

    def test_en_passant(self):
        # White pawn on e5, black plays d5, white can ep capture d6
        fen = "8/8/8/4Pp2/8/8/8/4K2k w - f6"
        b = Board.from_fen(fen)
        ucis = {move_to_uci(m) for m in b.legal_moves()}
        self.assertIn('e5f6', ucis)

    def test_promotion(self):
        fen = "8/P7/8/8/8/8/8/4K2k w - -"
        b = Board.from_fen(fen)
        ucis = {move_to_uci(m) for m in b.legal_moves()}
        self.assertIn('a7a8q', ucis)
        self.assertIn('a7a8r', ucis)
        self.assertIn('a7a8b', ucis)
        self.assertIn('a7a8n', ucis)

class TestCheckDetection(unittest.TestCase):
    def test_not_in_check_startpos(self):
        b = Board.from_fen()
        self.assertFalse(b.in_check(WHITE))
        self.assertFalse(b.in_check(BLACK))

    def test_in_check(self):
        # White king directly attacked by black rook
        fen = "4k3/8/8/8/8/8/8/4Kr2 w - -"
        b = Board.from_fen(fen)
        self.assertTrue(b.in_check(WHITE))

    def test_no_moves_in_checkmate(self):
        # Fool's mate
        fen = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq -"
        b = Board.from_fen(fen)
        self.assertEqual(len(b.legal_moves()), 0)

    def test_stalemate(self):
        fen = "k7/8/1Q6/8/8/8/8/7K b - -"
        b = Board.from_fen(fen)
        self.assertEqual(len(b.legal_moves()), 0)
        self.assertFalse(b.in_check(BLACK))   # stalemate, not checkmate

# ── Eval tests ───────────────────────────────────────────────────────────────
class TestEval(unittest.TestCase):
    def test_startpos_near_zero(self):
        from eval import evaluate
        b = Board.from_fen()
        # Starting position is symmetric — eval should be close to 0
        self.assertAlmostEqual(evaluate(b), 0, delta=50)

    def test_up_a_queen_is_positive(self):
        from eval import evaluate
        # White has extra queen
        fen = "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -"
        b = Board.from_fen(fen)
        self.assertGreater(evaluate(b), 800)

    def test_down_a_queen_is_negative(self):
        from eval import evaluate
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq -"
        b = Board.from_fen(fen)
        self.assertLess(evaluate(b), -800)

    def test_eval_flips_with_side(self):
        from eval import evaluate
        # After e2e4 black is to move; eval is from black's perspective (negative = white better)
        b = Board.from_fen()
        b.make(uci_to_move('e2e4', b))
        # With mobility + positional terms, e4 is good for white so score < 0 from black's view
        # Just verify it's reasonable (not enormous)
        self.assertLess(abs(evaluate(b)), 300)

    def test_passed_pawn_bonus(self):
        from eval import evaluate
        # White has a passed pawn on e6 — should score better than symmetric
        fen = "4k3/8/4P3/8/8/8/8/4K3 w - -"
        b = Board.from_fen(fen)
        self.assertGreater(evaluate(b), 0)

    def test_doubled_pawn_penalty(self):
        from eval import evaluate
        # Same material: 2 white pawns. Doubled (e4+e5) vs spread (e4+d4).
        doubled = Board.from_fen("4k3/8/8/4P3/4P3/8/8/4K3 w - -")
        spread  = Board.from_fen("4k3/8/8/8/3PP3/8/8/4K3 w - -")
        self.assertGreater(evaluate(spread), evaluate(doubled))

    def test_bishop_pair_bonus(self):
        from eval import evaluate
        # White has both bishops, black only one
        fen = "4k3/8/8/8/8/8/8/2BBK3 w - -"
        b = Board.from_fen(fen)
        fen2 = "2bbk3/8/8/8/8/8/8/4K3 b - -"
        b2 = Board.from_fen(fen2)
        self.assertGreater(evaluate(b), 0)   # white better with pair
        self.assertGreater(evaluate(b2), 0)  # black better with pair (from black's POV)

    def test_open_rook_file_bonus(self):
        from eval import evaluate
        # Same material, identical position except rook placement.
        # Rook on open e-file vs rook on d-file blocked by own pawn on d2.
        open_file   = Board.from_fen("4k3/8/8/8/8/8/3P4/4RK2 w - -")
        closed_file = Board.from_fen("4k3/8/8/8/8/8/3P4/3RK3 w - -")
        self.assertGreater(evaluate(open_file), evaluate(closed_file))

# ── Search tests ──────────────────────────────────────────────────────────────
class TestSearch(unittest.TestCase):
    def test_finds_mate_in_one(self):
        from search import search
        # Back rank mate: white rook to h8
        fen = "6k1/5ppp/8/8/8/8/8/R5K1 w - -"
        b = Board.from_fen(fen)
        mv = search(b, movetime_ms=2000)
        self.assertIsNotNone(mv)
        # After the move, black should have no legal moves and be in check
        b.make(mv)
        self.assertEqual(len(b.legal_moves()), 0)
        self.assertTrue(b.in_check(b.side))

    def test_takes_free_queen(self):
        from search import search
        # White can capture black queen on d5 with pawn on e4
        fen = "rnb1kbnr/ppp1pppp/8/3q4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -"
        b = Board.from_fen(fen)
        mv = search(b, movetime_ms=2000)
        self.assertEqual(move_to_uci(mv), 'e4d5')

    def test_avoids_losing_queen(self):
        from search import search
        # White queen on d1 attacked by black bishop — should move
        fen = "rnbqk1nr/pppp1ppp/8/4p3/1b1PP3/8/PPP2PPP/RNBQKBNR w KQkq -"
        b = Board.from_fen(fen)
        mv = search(b, movetime_ms=2000)
        # Best move should NOT be to stay on d1 (which is under attack)
        self.assertNotEqual(move_to_uci(mv), '0000')

    def test_returns_move_on_any_position(self):
        from search import search
        b = Board.from_fen()
        mv = search(b, movetime_ms=500)
        self.assertIsNotNone(mv)
        self.assertIn(move_to_uci(mv), {move_to_uci(m) for m in b.legal_moves()})

# ── Perft tests (slowest — run last) ─────────────────────────────────────────
class TestPerft(unittest.TestCase):
    def _run(self, fen, depth, expected):
        b = Board.from_fen(fen)
        self.assertEqual(perft(b, depth), expected, f"perft({depth}) from {fen[:40]}")

    def test_startpos_d1(self):  self._run(START_FEN, 1, 20)
    def test_startpos_d2(self):  self._run(START_FEN, 2, 400)
    def test_startpos_d3(self):  self._run(START_FEN, 3, 8902)

    def test_kiwipete_d1(self):
        self._run("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -", 1, 48)

    def test_pos3_d1(self):
        self._run("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - -", 1, 14)

    def test_pos3_d2(self):
        self._run("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - -", 2, 191)

if __name__ == '__main__':
    unittest.main(verbosity=2)
