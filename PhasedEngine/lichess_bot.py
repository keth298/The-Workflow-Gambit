#!/usr/bin/env python3
"""
PhasedEngine Lichess Bot Client

Connects PhasedEngine to Lichess for real ranked games and rating assessment.
"""

import berserk
import chess
import threading
import time
import sys
import os
import subprocess
from typing import Optional, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PhasedEngineBot:
    def __init__(self, token: str, engine_path: str, max_games: int = 3, timeout_minutes: int = 10):
        self.engine_path = os.path.abspath(engine_path)
        self.session = berserk.TokenSession(token)
        self.client = berserk.Client(self.session)
        self.game_threads: Dict[str, threading.Thread] = {}
        self.is_running = False
        self.max_games = max_games
        self.games_played = 0
        self.start_rating = None
        self.start_time = None
        self.timeout_minutes = timeout_minutes

    def get_engine_move(self, board: chess.Board, wtime: int = 1000, btime: int = 1000) -> Optional[chess.Move]:
        """Get a move from PhasedEngine with time controls."""
        proc = subprocess.Popen(
            ["python3", self.engine_path],
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
            f"go wtime {wtime} btime {btime}",
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

    def handle_game(self, game_id: str):
        """Handle a single game."""
        logger.info(f"Starting game {game_id}")

        try:
            game = self.client.games.export(game_id, moves=False)
            board = chess.Board()
            is_white = game['players']['white']['user']['id'] == self.client.account.get()['id']

            logger.info(f"Playing as {'white' if is_white else 'black'}")

            while not board.is_game_over():
                # Get current game state
                game_state = self.client.games.export(game_id, moves=True)
                moves = game_state.get('moves', '').split()

                # Update board with moves
                board = chess.Board()
                for move in moves:
                    board.push_uci(move)

                # Check if it's our turn
                if (is_white and board.turn == chess.WHITE) or (not is_white and board.turn == chess.BLACK):
                    # Get time remaining
                    wtime = game_state.get('wtime', 1000)
                    btime = game_state.get('btime', 1000)

                    # Get engine move
                    move = self.get_engine_move(board, wtime, btime)

                    if move:
                        # Make the move
                        self.client.games.make_move(game_id, move.uci())
                        logger.info(f"Played {move.uci()}")
                    else:
                        logger.error("Engine returned no move!")
                        break

                time.sleep(1)  # Small delay to avoid overwhelming the API

            logger.info(f"Game {game_id} finished")
            self.games_played += 1
            
            # Check if we've reached the game limit
            if self.games_played >= self.max_games:
                logger.info(f"Reached maximum games ({self.max_games}), stopping bot")
                self.is_running = False

        except Exception as e:
            logger.error(f"Error in game {game_id}: {e}")
        finally:
            if game_id in self.game_threads:
                del self.game_threads[game_id]

    def challenge_handler(self, event):
        """Handle incoming challenges."""
        if self.games_played >= self.max_games:
            logger.info("Reached game limit, ignoring new challenges")
            return
            
        challenge = event['challenge']
        challenger = challenge['challenger']['name']
        rated = challenge.get('rated', False)
        time_control = challenge.get('timeControl', {})

        logger.info(f"Received challenge from {challenger} ({'rated' if rated else 'casual'})")

        # Accept challenges from other bots (not humans for safety)
        if challenge['challenger']['title'] in ['BOT', 'Computer']:
            try:
                self.client.challenges.accept(challenge['id'])
                logger.info(f"Accepted challenge from {challenger}")
            except Exception as e:
                logger.error(f"Failed to accept challenge: {e}")

    def game_start_handler(self, event):
        """Handle game start events."""
        game_id = event['game']['id']
        logger.info(f"Game started: {game_id} (Game {self.games_played + 1}/{self.max_games})")

        # Start a thread to handle this game
        thread = threading.Thread(target=self.handle_game, args=(game_id,))
        thread.daemon = True
        self.game_threads[game_id] = thread
        thread.start()

    def run(self):
        """Main bot loop."""
        logger.info("Starting PhasedEngine Lichess Bot")

        try:
            # Get starting rating
            account = self.client.account.get()
            logger.info(f"Account info: {account}")
            self.start_rating = account.get('perfs', {}).get('classical', {}).get('rating', 1500)
            logger.info(f"Starting rating: {self.start_rating}")

            # Bot is automatically online when connected with bot token
            self.is_running = True
            self.start_time = time.time()

            # Start event stream
            logger.info("Listening for challenges...")
            for event in self.client.bots.stream_incoming_events():
                # Check timeout
                elapsed_minutes = (time.time() - self.start_time) / 60
                if elapsed_minutes > self.timeout_minutes:
                    logger.info(f"Timeout reached ({self.timeout_minutes} minutes), stopping bot")
                    self.is_running = False
                    break
                    
                logger.info(f"Received event: {event.get('type')}")
                if not self.is_running:
                    break
                    
                if event['type'] == 'challenge':
                    self.challenge_handler(event)
                elif event['type'] == 'gameStart':
                    self.game_start_handler(event)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            # Get final rating
            try:
                account = self.client.account.get()
                final_rating = account.get('perfs', {}).get('classical', {}).get('rating', 'Unknown')
                rating_change = final_rating - self.start_rating if isinstance(final_rating, int) and isinstance(self.start_rating, int) else "Unknown"
                
                logger.info("=== FINAL RESULTS ===")
                logger.info(f"Games played: {self.games_played}")
                logger.info(f"Starting rating: {self.start_rating}")
                logger.info(f"Final rating: {final_rating}")
                logger.info(f"Rating change: {rating_change}")
                
                print("\n" + "="*50)
                print("🎯 PHASENGINE LICHESS BOT RESULTS")
                print("="*50)
                print(f"Games Played: {self.games_played}")
                print(f"Starting Rating: {self.start_rating}")
                print(f"Final Rating: {final_rating}")
                print(f"Rating Change: {rating_change}")
                print("="*50)
                
            except Exception as e:
                logger.error(f"Could not get final rating: {e}")
            
            # Cleanup
            for thread in self.game_threads.values():
                thread.join(timeout=5)
            logger.info("Bot shutdown complete")

def main():
    # Get token from environment variable (for security)
    token = os.getenv('LICHESS_BOT_TOKEN')

    if not token:
        print("""
🚫 LICHESS_BOT_TOKEN environment variable not set!

To use this bot, you need to:

1. Create a Lichess bot account at: https://lichess.org/account/oauth/token/create
   - Go to https://lichess.org/account/oauth/token
   - Create a new personal token with "Play games with the bot API" permission
   - Copy the token

2. Set the environment variable:
   export LICHESS_BOT_TOKEN="your_token_here"

3. Run the bot:
   python3 lichess_bot.py

⚠️  WARNING: Bot accounts can only play other bots, not humans!
   Make sure your account is marked as a bot.

Example usage:
   LICHESS_BOT_TOKEN="your_token" python3 lichess_bot.py
        """)
        return

    engine_path = os.path.join(os.path.dirname(__file__), "engine.py")

    if not os.path.exists(engine_path):
        print(f"❌ Engine not found at {engine_path}")
        return

    bot = PhasedEngineBot(token, engine_path, max_games=3)
    bot.run()

if __name__ == "__main__":
    main()