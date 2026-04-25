# PhasedEngine Lichess Bot Setup Guide

## Overview
PhasedEngine can now play **real ranked games** on Lichess against other bots to get an accurate Elo rating!

## How It Works
- Connects to Lichess Bot API
- Accepts challenges from other bots
- Plays ranked games using PhasedEngine
- Earns real Elo rating based on performance

## Setup Instructions

### 1. Create a Lichess Bot Account

1. Go to https://lichess.org/account/oauth/token
2. Create a new personal token with these permissions:
   - ✅ Play games with the bot API
   - ✅ Read incoming challenges
   - ✅ Create, accept, decline challenges
3. Copy the token (keep it secret!)

### 2. Mark Your Account as a Bot

**Important**: Bot accounts can only play other bots, not humans!

1. Go to https://lichess.org/account/profile
2. Set your title to "BOT"
3. This restricts you to bot-only games

### 3. Run the Bot

```bash
# Set your token as environment variable
export LICHESS_BOT_TOKEN="your_token_here"

# Run the bot
cd /Users/fastcheetah/Point72/Point72Hackathon/PhasedEngine
python3 lichess_bot.py
```

## What Happens Next

1. **Bot goes online** - appears in Lichess bot lists
2. **Receives challenges** - other bots will challenge you
3. **Plays games** - uses PhasedEngine with proper time controls
4. **Gets rated** - Elo changes based on wins/losses

## Rating Estimation

Based on our earlier analysis (~1262 Elo), expect:
- **Starting rating**: Around 1200-1300 Elo
- **After 10-20 games**: More accurate rating
- **Long-term**: Should stabilize around true strength

## Safety Features

- ✅ Only accepts challenges from other bots (not humans)
- ✅ Proper time management using UCI `wtime`/`btime`
- ✅ Handles game termination gracefully
- ✅ Logs all activity for debugging

## Monitoring Your Bot

1. **Check rating**: https://lichess.org/@/your_username
2. **View games**: https://lichess.org/@/your_username/all
3. **Bot logs**: Check terminal output for game progress

## Example Output

```
2026-04-25 12:00:00 - INFO - Starting PhasedEngine Lichess Bot
2026-04-25 12:00:05 - INFO - Received challenge from StockfishBot (rated)
2026-04-25 12:00:05 - INFO - Accepted challenge from StockfishBot
2026-04-25 12:00:10 - INFO - Game started: abc123def456
2026-04-25 12:00:10 - INFO - Playing as white
2026-04-25 12:00:15 - INFO - Played e2e4
2026-04-25 12:01:30 - INFO - Game abc123def456 finished
```

## Troubleshooting

### Bot won't accept challenges
- Make sure your account is marked as "BOT"
- Check that the token has correct permissions
- Verify the token is set correctly

### Engine crashes during games
- Check that `engine.py` is in the same directory
- Ensure all dependencies are installed
- Look at stderr output for error messages

### Poor performance
- The bot uses time controls from Lichess
- Engine may play differently with real time pressure
- Consider adjusting search depth or time management

## Alternative: Test Mode

If you don't want to create a real bot account, you can still test the integration:

```bash
# Test without token (shows setup instructions)
python3 lichess_bot.py

# Test engine integration only
python3 -c "
from lichess_bot import PhasedEngineBot
import chess
bot = PhasedEngineBot('dummy_token', 'engine.py')
board = chess.Board()
move = bot.get_engine_move(board)
print(f'Engine move: {move}')
"
```

## Expected Rating Progression

| Games Played | Rating Range | Confidence |
|--------------|--------------|------------|
| 0 | 1200-1300 | Initial estimate |
| 5 | 1150-1350 | Low confidence |
| 20 | 1100-1400 | Medium confidence |
| 50+ | 1050-1450 | High confidence |

## Next Steps

1. **Create bot account** and get token
2. **Run the bot** and let it play games
3. **Monitor progress** via Lichess website
4. **Analyze games** to identify weaknesses
5. **Improve engine** based on real-game performance

This will give you the most accurate rating possible! 🎯