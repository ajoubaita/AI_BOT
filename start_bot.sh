#!/bin/bash
# Simple script to start the bot in paper trading mode
# No prompts - just starts immediately

cd ~/AI_BOT || exit 1

# Ensure test mode is enabled
sed -i 's/TEST_MODE=false/TEST_MODE=true/' .env

# Stop any existing instances
pkill -f "python.*main.py" 2>/dev/null

# Activate virtual environment and start
source venv/bin/activate
screen -dmS arbitrage_bot bash -c "source venv/bin/activate && python main.py"

sleep 2

if ps aux | grep -v grep | grep "python.*main.py" > /dev/null; then
    echo "✅ Arbitrage bot started in PAPER TRADING mode"
    echo "📊 View logs: tail -f ~/AI_BOT/arbitrage_bot.log"
else
    echo "❌ Failed to start. Check: tail ~/AI_BOT/arbitrage_bot.log"
    exit 1
fi
