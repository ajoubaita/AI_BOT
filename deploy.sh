#!/bin/bash
# Quick deployment script for DigitalOcean server
# ALWAYS starts in paper trading mode by default

echo "🚀 Deploying Arbitrage Bot Updates..."

# Navigate to bot directory
cd ~/AI_BOT || exit 1

# Pull latest changes
echo "📥 Pulling latest code..."
git pull origin claude/arbitrage-trading-bot-011CUwBKDUvEnEjbP8mjMugD

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet

# Stop any running bot instances
echo "🛑 Stopping existing bot instances..."
pkill -f "python.*main.py" || echo "No running instances found"

# Always start in TEST MODE (paper trading)
echo "▶️ Starting bot in PAPER TRADING MODE..."

# Ensure .env has test mode enabled
sed -i 's/TEST_MODE=false/TEST_MODE=true/' .env

# Start bot in background screen session
screen -dmS arbitrage_bot bash -c "source venv/bin/activate && python main.py"

# Wait a moment for startup
sleep 2

# Check if it's running
if ps aux | grep -v grep | grep "python.*main.py" > /dev/null; then
    echo ""
    echo "✅ Bot started successfully in PAPER TRADING MODE!"
    echo ""
    echo "📊 The bot is now:"
    echo "   • Scanning 115k+ Kalshi markets"
    echo "   • Detecting arbitrage opportunities"
    echo "   • Simulating trades (no real money)"
    echo "   • Tracking paper trading PnL"
    echo ""
    echo "📈 Useful Commands:"
    echo "   View live logs:     tail -f ~/AI_BOT/arbitrage_bot.log"
    echo "   Monitor in real-time: watch -n 5 'tail -30 ~/AI_BOT/arbitrage_bot.log'"
    echo "   Attach to session:  screen -r arbitrage_bot"
    echo "   Stop bot:           pkill -f 'python.*main.py'"
    echo "   Check if running:   ps aux | grep main.py"
    echo ""
    echo "💡 Let it run for a week, then review paper trading results!"
else
    echo ""
    echo "❌ Failed to start bot. Check logs:"
    echo "   tail -50 ~/AI_BOT/arbitrage_bot.log"
    exit 1
fi
