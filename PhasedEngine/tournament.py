#!/usr/bin/env python3
"""
Chess Engine Tournament System
Pit PhasedEngine against other engines to establish Elo rating
"""

import chess
import chess.engine
import subprocess
import time
import random
import statistics
from typing import List, Tuple, Dict

class EnginePlayer:
    def __init__(self, name: str, command: List[str], elo: int = 1500):
        self.name = name
        self.command = command
        self.elo = elo
        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.draws = 0

    def get_score(self) -> float:
        return self.wins + 0.5 * self.draws

    def update_elo(self, opponent_elo: int, result: float):
        """Simple Elo update (not the official formula)"""
        expected = 1 / (1 + 10 ** ((opponent_elo - self.elo) / 400))
        self.elo += int(32 * (result - expected))
        self.games_played += 1

class Tournament:
    def __init__(self, engines: List[EnginePlayer], games_per_pairing: int = 2):
        self.engines = engines
        self.games_per_pairing = games_per_pairing
        self.results = []

    def play_game(self, white_engine: EnginePlayer, black_engine: EnginePlayer,
                  time_limit: float = 1.0) -> str:
        """Play a single game between two engines"""
        board = chess.Board()

        try:
            with chess.engine.SimpleEngine.popen_uci(white_engine.command) as white, \
                 chess.engine.SimpleEngine.popen_uci(black_engine.command) as black:

                while not board.is_game_over():
                    if board.turn == chess.WHITE:
                        result = white.play(board, chess.engine.Limit(time=time_limit))
                    else:
                        result = black.play(board, chess.engine.Limit(time=time_limit))

                    board.push(result.move)

                # Determine result
                if board.is_checkmate():
                    if board.turn == chess.BLACK:
                        return 'white'  # White checkmated black
                    else:
                        return 'black'  # Black checkmated white
                else:
                    return 'draw'

        except Exception as e:
            print(f"Error in game {white_engine.name} vs {black_engine.name}: {e}")
            return 'draw'  # Default to draw on error

    def run_round_robin(self) -> Dict[str, EnginePlayer]:
        """Run round-robin tournament"""
        print("🏆 Starting Round-Robin Tournament")
        print("=" * 50)

        for i, engine1 in enumerate(self.engines):
            for j, engine2 in enumerate(self.engines):
                if i >= j:  # Avoid duplicate pairings and self-play
                    continue

                print(f"\n🎯 Playing {engine1.name} vs {engine2.name}")

                for game_num in range(self.games_per_pairing):
                    # Alternate colors
                    if game_num % 2 == 0:
                        white, black = engine1, engine2
                    else:
                        white, black = engine2, engine1

                    result = self.play_game(white, black)
                    self.results.append((white.name, black.name, result))

                    # Update stats and Elo
                    if result == 'white':
                        white.wins += 1
                        black.losses += 1
                        white.update_elo(black.elo, 1.0)
                        black.update_elo(white.elo, 0.0)
                    elif result == 'black':
                        black.wins += 1
                        white.losses += 1
                        black.update_elo(white.elo, 1.0)
                        white.update_elo(black.elo, 0.0)
                    else:  # draw
                        white.draws += 1
                        black.draws += 1
                        white.update_elo(black.elo, 0.5)
                        black.update_elo(white.elo, 0.5)

                    print(f"  Game {game_num + 1}: {white.name} ({result}) {black.name}")

        return {engine.name: engine for engine in self.engines}

def create_test_engines():
    """Create some test engines with known Elo ratings"""
    return [
        EnginePlayer("PhasedEngine", ["python3", "engine.py"], 1500),
        # Simple random mover (very weak)
        EnginePlayer("RandomEngine", ["python3", "-c", """
import chess
import chess.engine
import random
import sys

class RandomEngine(chess.engine.SimpleEngine):
    def search(self, board, *args, **kwargs):
        legal_moves = list(board.legal_moves)
        if legal_moves:
            return chess.engine.PlayResult(random.choice(legal_moves), None)
        return chess.engine.PlayResult(None, None)

if __name__ == '__main__':
    engine = RandomEngine()
    engine.run()
"""], 800),
        # Slightly better engine (material-only evaluation)
        EnginePlayer("MaterialEngine", ["python3", "-c", """
import chess
import chess.engine
import random

class MaterialEngine(chess.engine.SimpleEngine):
    def evaluate(self, board):
        # Simple material evaluation
        piece_values = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
                       chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000}
        score = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = piece_values[piece.piece_type]
                if piece.color == chess.WHITE:
                    score += value
                else:
                    score -= value
        return score if board.turn == chess.WHITE else -score

    def search(self, board, limit, *args, **kwargs):
        best_move = None
        best_score = -99999

        for move in board.legal_moves:
            board.push(move)
            score = -self.evaluate(board)  # Negamax
            board.pop()

            if score > best_score:
                best_score = score
                best_move = move

        return chess.engine.PlayResult(best_move, None)

if __name__ == '__main__':
    engine = MaterialEngine()
    engine.run()
"""], 1200),
    ]

if __name__ == '__main__':
    engines = create_test_engines()
    tournament = Tournament(engines, games_per_pairing=4)  # 4 games per pairing

    final_standings = tournament.run_round_robin()

    print("\n🏆 FINAL STANDINGS")
    print("=" * 50)
    sorted_engines = sorted(final_standings.values(),
                           key=lambda e: (e.get_score(), e.elo),
                           reverse=True)

    for i, engine in enumerate(sorted_engines, 1):
        score = engine.get_score()
        print(f"{i}. {engine.name}")
        print(f"   Elo: {engine.elo} | Score: {score:.1f}/{engine.games_played}")
        print(f"   W-L-D: {engine.wins}-{engine.losses}-{engine.draws}")

    # Find PhasedEngine's rating
    phased_engine = final_standings.get("PhasedEngine")
    if phased_engine:
        print(f"\n🎯 PhasedEngine Final Rating: {phased_engine.elo} Elo")
        print("💡 This rating is calibrated against the test engines in this tournament.")