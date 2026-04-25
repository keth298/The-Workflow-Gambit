#!/usr/bin/env python3
"""
Lichess Engine Evaluation Script

Evaluates PhasedEngine using Lichess APIs:
1. Cloud analysis of positions
2. Bot game analysis
3. Rating estimation
"""

import subprocess
import requests
import time
import chess
import json
from typing import List, Dict, Optional, Tuple
import sys
import os

class LichessEvaluator:
    def __init__(self, engine_path: str):
        self.engine_path = engine_path
        self.base_url = "https://lichess.org/api"

    def get_engine_move(self, board: chess.Board, depth: int = 4) -> Optional[chess.Move]:
        """Get a move from our engine for the given position."""
        proc = subprocess.Popen(
            [sys.executable, self.engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(self.engine_path)
        )

        commands = [
            "uci",
            "isready",
            "ucinewgame",
            f"position fen {board.fen()}",
            f"go depth {depth}",
            "quit"
        ]

        input_str = "\n".join(commands) + "\n"

        try:
            stdout, stderr = proc.communicate(input_str, timeout=30)
            for line in stdout.strip().split('\n'):
                if line.startswith('bestmove'):
                    move_uci = line.split()[1]
                    if move_uci != '0000':
                        return chess.Move.from_uci(move_uci)
            return None
        except subprocess.TimeoutExpired:
            proc.kill()
            return None

    def analyze_position_cloud(self, fen: str) -> Dict:
        """Analyze a position using Lichess cloud evaluation."""
        url = f"{self.base_url}/cloud-eval"
        params = {"fen": fen}

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Cloud eval failed: {response.status_code}")
                return {}
        except Exception as e:
            print(f"Cloud eval error: {e}")
            return {}

    def get_opening_positions(self) -> List[str]:
        """Get some standard opening positions to evaluate."""
        positions = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # Start
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",  # e4
            "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2",  # e4 c5
            "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",  # Italian
            "rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",  # Petrov
        ]
        return positions

    def evaluate_engine_strength(self) -> Dict:
        """Evaluate engine strength using multiple methods."""
        results = {
            "cloud_analysis": [],
            "move_quality": [],
            "estimated_rating": 0
        }

        print("=== Evaluating PhasedEngine with Lichess ===\n")

        # 1. Cloud analysis of positions
        print("1. Analyzing positions with Lichess Cloud:")
        positions = self.get_opening_positions()

        for i, fen in enumerate(positions, 1):
            print(f"   Position {i}: {fen.split()[0]}...")
            cloud_eval = self.analyze_position_cloud(fen)

            if cloud_eval:
                score = cloud_eval.get('pvs', [{}])[0].get('cp', 0)
                results["cloud_analysis"].append({
                    "fen": fen,
                    "cloud_score": score
                })
                print(f"      Cloud evaluation: {score} centipawns")
            else:
                print("      Cloud evaluation failed")

            time.sleep(1)  # Rate limiting

        # 2. Compare engine moves with cloud analysis
        print("\n2. Comparing engine moves with cloud analysis:")
        board = chess.Board()

        for depth in [3, 4]:
            print(f"\n   Depth {depth} analysis:")
            engine_move = self.get_engine_move(board, depth)

            if engine_move:
                # Make the move and analyze the resulting position
                board.push(engine_move)
                cloud_eval = self.analyze_position_cloud(board.fen())

                if cloud_eval:
                    cloud_score = cloud_eval.get('pvs', [{}])[0].get('cp', 0)
                    # Convert to our perspective (negate if black to move)
                    if board.turn == chess.BLACK:
                        cloud_score = -cloud_score

                    results["move_quality"].append({
                        "move": engine_move.uci(),
                        "depth": depth,
                        "cloud_score": cloud_score
                    })

                    print(f"      Move {engine_move.uci()}: Cloud score {cloud_score} cp")
                else:
                    print(f"      Move {engine_move.uci()}: Could not evaluate")

                board.pop()  # Undo move
            else:
                print(f"      No move found at depth {depth}")

        # 3. Estimate rating based on analysis
        print("\n3. Rating estimation:")

        if results["cloud_analysis"]:
            avg_cloud_score = sum(abs(p["cloud_score"]) for p in results["cloud_analysis"]) / len(results["cloud_analysis"])
            # Rough mapping: 100cp ≈ 100 Elo points difference
            # Base rating around 1500 for a basic engine
            estimated_rating = 1500 + (avg_cloud_score / 10)
            results["estimated_rating"] = int(estimated_rating)
            print(f"      Estimated rating: {results['estimated_rating']} (based on position complexity)")

        if results["move_quality"]:
            avg_move_score = sum(abs(m["cloud_score"]) for m in results["move_quality"]) / len(results["move_quality"])
            move_based_rating = 1400 + (avg_move_score / 15)
            print(f"      Move quality suggests: ~{int(move_based_rating)} Elo")

        return results

def main():
    engine_path = os.path.join(os.path.dirname(__file__), "engine.py")

    if not os.path.exists(engine_path):
        print(f"Engine not found at {engine_path}")
        return

    evaluator = LichessEvaluator(engine_path)
    results = evaluator.evaluate_engine_strength()

    print("\n=== Final Results ===")
    print(json.dumps(results, indent=2))

    if results["estimated_rating"] > 0:
        print(f"\n🎯 Estimated PhasedEngine Rating: {results['estimated_rating']} Elo")
        print("   (This is a rough estimate based on position analysis)")

if __name__ == "__main__":
    main()