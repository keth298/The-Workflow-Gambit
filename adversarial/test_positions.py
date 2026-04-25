TEST_POSITIONS: list[dict] = [
    # --- Mate in 1 ---
    {
        "name": "mate1_back_rank",
        "fen": "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1",
        "expected": "a1a8",
        "depth": 1,
    },
    {
        "name": "mate1_queen",
        "fen": "k7/8/KQ6/8/8/8/8/8 w - - 0 1",
        "expected": "b6b7",
        "depth": 1,
    },
    {
        "name": "mate1_rook",
        "fen": "8/8/8/8/8/k7/8/KR6 b - - 0 1",
        "expected": "a3a2",
        "depth": 1,
    },
    # --- Mate in 2 ---
    {
        "name": "mate2_smothered",
        "fen": "6rk/6pp/7N/8/8/8/8/6K1 w - - 0 1",
        "expected": "h6f7",
        "depth": 4,
    },
    {
        "name": "mate2_ladder",
        "fen": "8/8/8/8/8/2k5/2Q5/2K5 w - - 0 1",
        "expected": "c2c3",
        "depth": 4,
    },
    # --- Hanging piece ---
    {
        "name": "hanging_queen",
        "fen": "rnb1kbnr/pppp1ppp/8/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR b KQkq - 0 3",
        "expected": "d8h4",
        "depth": 2,
    },
    {
        "name": "hanging_rook",
        "fen": "4k3/8/8/3r4/8/8/8/4K1R1 b - - 0 1",
        "expected": "d5g5",
        "depth": 2,
    },
    # --- Tactics ---
    {
        "name": "fork_knight",
        "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "expected": "f3e5",
        "depth": 3,
    },
    {
        "name": "fork_knight2",
        "fen": "8/8/8/3k4/8/4N3/8/3K4 w - - 0 1",
        "expected": "e3f5",
        "depth": 3,
    },
    {
        "name": "pin_bishop",
        "fen": "r1bqk2r/ppp2ppp/2n1pn2/3p4/1bPP4/2N1PN2/PP3PPP/R1BQKB1R w KQkq - 2 6",
        "expected": "d1a4",
        "depth": 3,
    },
    {
        "name": "skewer_rook",
        "fen": "4k3/8/8/8/8/8/8/R3K3 w Q - 0 1",
        "expected": "a1a8",
        "depth": 3,
    },
    {
        "name": "discovered_check",
        "fen": "4k3/8/8/b7/8/8/2B5/3RK3 w - - 0 1",
        "expected": "c2b3",
        "depth": 4,
    },
    # --- Promotion ---
    {
        "name": "promotion_queen",
        "fen": "8/3P4/8/8/8/8/8/k1K5 w - - 0 1",
        "expected": "d7d8q",
        "depth": 2,
    },
    {
        "name": "promotion_forced",
        "fen": "8/P7/8/8/8/8/8/k1K5 w - - 0 1",
        "expected": "a7a8q",
        "depth": 2,
    },
    # --- Endgame ---
    {
        "name": "kp_opposition",
        "fen": "8/8/8/3k4/8/3K4/3P4/8 w - - 0 1",
        "expected": "d3e3",
        "depth": 6,
    },
    {
        "name": "kq_vs_k_mate",
        "fen": "8/8/8/8/8/8/6QK/7k w - - 0 1",
        "expected": "g2g1",
        "depth": 4,
    },
    # --- Stalemate avoidance ---
    {
        "name": "stalemate_avoid",
        "fen": "8/8/8/8/8/7k/7p/7K w - - 0 1",
        "expected": "h1g1",
        "depth": 3,
    },
    # --- Material grab ---
    {
        "name": "capture_free_rook",
        "fen": "4k3/8/8/3r4/8/8/8/4K3 w - - 0 1",
        "expected": "e1d1",
        "depth": 2,
    },
    # --- Checkmate patterns ---
    {
        "name": "mate1_anastasia",
        "fen": "5rk1/R4ppp/8/8/8/8/8/6K1 w - - 0 1",
        "expected": "a7a8",
        "depth": 2,
    },
    {
        "name": "mate1_corridor",
        "fen": "6k1/6pp/8/8/8/8/8/5RK1 w - - 0 1",
        "expected": "f1f8",
        "depth": 1,
    },
    # --- Simple wins ---
    {
        "name": "win_queen_for_free",
        "fen": "rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3",
        "expected": "g4g5",
        "depth": 2,
    },
    {
        "name": "avoid_losing_queen",
        "fen": "rnbqkbnr/ppp2ppp/3p4/4p3/4P3/3P1N2/PPP2PPP/RNBQKB1R w KQkq - 0 4",
        "expected": "f1b5",
        "depth": 3,
    },
]
