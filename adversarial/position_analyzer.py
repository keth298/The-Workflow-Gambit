import random
import chess


def random_endgame_positions(n: int) -> list[str]:
    piece_pool = [
        chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.QUEEN,
    ]
    results = []
    attempts = 0
    while len(results) < n and attempts < n * 50:
        attempts += 1
        board = chess.Board(fen=None)
        board.clear()

        white_king_sq = random.randint(0, 63)
        board.set_piece_at(white_king_sq, chess.Piece(chess.KING, chess.WHITE))

        black_king_sq = random.randint(0, 63)
        if (
            black_king_sq == white_king_sq
            or chess.square_distance(white_king_sq, black_king_sq) <= 1
        ):
            continue
        board.set_piece_at(black_king_sq, chess.Piece(chess.KING, chess.BLACK))

        num_pieces = random.randint(1, 3)
        occupied = {white_king_sq, black_king_sq}
        ok = True
        for _ in range(num_pieces):
            color = random.choice([chess.WHITE, chess.BLACK])
            piece_type = random.choice(piece_pool)
            sq = random.randint(0, 63)
            if sq in occupied:
                ok = False
                break
            occupied.add(sq)
            board.set_piece_at(sq, chess.Piece(piece_type, color))

        if not ok:
            continue

        board.turn = chess.WHITE
        if not board.is_valid() or board.is_game_over():
            continue

        results.append(board.fen())
    return results


def pawn_endgame_positions(n: int) -> list[str]:
    results = []
    attempts = 0
    while len(results) < n and attempts < n * 50:
        attempts += 1
        board = chess.Board(fen=None)
        board.clear()

        white_king_sq = random.randint(0, 63)
        board.set_piece_at(white_king_sq, chess.Piece(chess.KING, chess.WHITE))

        black_king_sq = random.randint(0, 63)
        if (
            black_king_sq == white_king_sq
            or chess.square_distance(white_king_sq, black_king_sq) <= 1
        ):
            continue
        board.set_piece_at(black_king_sq, chess.Piece(chess.KING, chess.BLACK))

        num_pawns = random.randint(1, 4)
        occupied = {white_king_sq, black_king_sq}
        ok = True
        for _ in range(num_pawns):
            color = random.choice([chess.WHITE, chess.BLACK])
            rank = random.randint(1, 6)
            file = random.randint(0, 7)
            sq = chess.square(file, rank)
            if sq in occupied:
                ok = False
                break
            occupied.add(sq)
            board.set_piece_at(sq, chess.Piece(chess.PAWN, color))

        if not ok:
            continue

        board.turn = chess.WHITE
        if not board.is_valid() or board.is_game_over():
            continue

        results.append(board.fen())
    return results


def tactical_noise_positions(base_fen: str, n: int) -> list[str]:
    results = []
    attempts = 0
    while len(results) < n and attempts < n * 20:
        attempts += 1
        board = chess.Board(base_fen)
        num_moves = random.randint(2, 4)
        ok = True
        for _ in range(num_moves):
            legal = list(board.legal_moves)
            if not legal or board.is_game_over():
                ok = False
                break
            board.push(random.choice(legal))
        if not ok or board.is_game_over():
            continue
        results.append(board.fen())
    return results
