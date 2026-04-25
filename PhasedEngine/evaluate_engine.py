#!/usr/bin/env python3
"""
Chess Engine Evaluation Script
Tests PhasedEngine against standard positions and calculates performance metrics
"""

import subprocess
import chess
import chess.engine
import time
import statistics
import sys

def evaluate_engine(engine_path, test_positions, time_limit=1.0):
    """Evaluate engine on test positions"""
    results = []

    try:
        with chess.engine.SimpleEngine.popen_uci(['python3', engine_path]) as engine:
            for fen, expected_score in test_positions:
                board = chess.Board(fen)
                try:
                    result = engine.analyse(board, chess.engine.Limit(time=time_limit))
                    score = result['score'].relative.score(mate_score=10000)
                    results.append((fen, score, expected_score))
                    print(f'Position: {fen[:50]}...')
                    print(f'Engine score: {score}, Expected: {expected_score}')
                except Exception as e:
                    print(f'Error analyzing position {fen[:30]}...: {e}')
    except Exception as e:
        print(f'Failed to start engine: {e}')
        return []

    return results

def calculate_elo_from_results(results):
    """Calculate approximate Elo rating from position evaluation results"""
    if not results:
        return None

    # Simple heuristic: better evaluation accuracy = higher Elo
    total_error = 0
    for fen, actual_score, expected_score in results:
        error = abs(actual_score - expected_score)
        total_error += error

    avg_error = total_error / len(results)

    # Rough mapping: lower error = higher Elo
    # This is a very simplified model
    if avg_error < 50:
        base_elo = 2200
    elif avg_error < 100:
        base_elo = 2000
    elif avg_error < 200:
        base_elo = 1800
    elif avg_error < 300:
        base_elo = 1600
    else:
        base_elo = 1400

    # Adjust based on consistency
    error_std = statistics.stdev([abs(r[1] - r[2]) for r in results]) if len(results) > 1 else 0
    consistency_bonus = max(0, 100 - error_std)

    return base_elo + consistency_bonus

# Test positions with expected centipawn scores (approximate)
test_positions = [
    ('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', 0),  # Starting position
    ('r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3', 50),  # Early game
    ('r1bq1rk1/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQ1RK1 w - - 4 7', 30),  # Opening
    ('r1bq1rk1/1ppp1ppp/p1n2n2/2b1p3/4P3/1B1P1N2/PPP2PPP/RNBQR1K1 b - - 1 8', -20),  # Black has some compensation
    ('r1b2rk1/ppq2ppp/2n1pn2/2b1p3/2B1P3/2NP1N2/PPPQ1PPP/R1B2RK1 w - - 1 10', 80),  # White advantage
    ('r4rk1/pp1bqppp/2n1pn2/2b1p3/2B1P3/2NP1N2/PPPQ1PPP/3R1RK1 w - - 3 11', 120),  # White better
]

if __name__ == '__main__':
    print('🧪 Testing PhasedEngine on standard positions...')
    print('=' * 50)

    results = evaluate_engine('./engine.py', test_positions, time_limit=2.0)

    if results:
        print(f'\n✅ Completed analysis of {len(results)} positions')

        # Calculate metrics
        errors = [abs(actual - expected) for _, actual, expected in results]
        avg_error = statistics.mean(errors)
        max_error = max(errors)
        min_error = min(errors)

        print(f'\n📊 Performance Metrics:')
        print(f'Average evaluation error: {avg_error:.1f} centipawns')
        print(f'Max error: {max_error} centipawns')
        print(f'Min error: {min_error} centipawns')

        # Estimate Elo
        estimated_elo = calculate_elo_from_results(results)
        if estimated_elo:
            print(f'\n🎯 Estimated Elo rating: ~{estimated_elo}')

        print('\n💡 Note: This is a rough estimate based on evaluation accuracy.')
        print('   Real Elo requires playing rated games against calibrated opponents.')
    else:
        print('❌ Failed to evaluate engine - check if engine.py exists and is UCI compliant')