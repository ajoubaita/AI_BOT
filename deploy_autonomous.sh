#!/bin/bash
# Autonomous deployment for non-systemd environments
# Uses watchdog script for 24/7 operation with auto-restart

set -e

echo "🚀 Deploying Arbitrage Bot with Autonomous Watchdog..."

BOT_DIR="/home/user/AI_BOT"
cd "$BOT_DIR" || exit 1

# Pull latest changes if git repo exists
if [ -d .git ]; then
    echo "📥 Pulling latest code..."
    git pull origin claude/arbitrage-trading-bot-011CUwBKDUvEnEjbP8mjMugD || echo "Git pull skipped"
fi

# Set up virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3.10 -m venv venv
fi

# Activate and update virtual environment
echo "🔧 Updating Python environment..."
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Configure paper trading mode
echo "🧪 Configuring PAPER TRADING MODE..."
if [ -f .env ]; then
    sed -i 's/TEST_MODE=false/TEST_MODE=true/' .env
    if ! grep -q "TEST_MODE" .env; then
        echo "TEST_MODE=true" >> .env
    fi
else
    echo "❌ .env file not found! Please create it first."
    exit 1
fi

# Stop any existing instances
echo "🛑 Stopping existing bot instances..."
pkill -f "run_autonomous.sh" 2>/dev/null || echo "No watchdog running"
pkill -f "python.*main.py" 2>/dev/null || echo "No bot instances found"
sleep 2

# Make watchdog script executable
chmod +x run_autonomous.sh

# Start the autonomous watchdog in the background
echo "▶️  Starting autonomous watchdog..."
nohup ./run_autonomous.sh > watchdog_nohup.log 2>&1 &
WATCHDOG_PID=$!

# Wait a bit for startup
sleep 5

# Check if watchdog is running
if ps -p $WATCHDOG_PID > /dev/null 2>&1; then
    echo ""
    echo "✅ ✅ ✅ AUTONOMOUS BOT DEPLOYED SUCCESSFULLY! ✅ ✅ ✅"
    echo ""
    echo "🤖 The bot is now running AUTONOMOUSLY:"
    echo "   • Watchdog PID: $WATCHDOG_PID"
    echo "   • Runs 24/7 in the background"
    echo "   • Auto-restarts if it crashes"
    echo "   • Paper trading mode (no real money)"
    echo ""
    echo "📊 The bot is:"
    echo "   • Scanning 20k+ Polymarket markets"
    echo "   • Scanning 115k+ Kalshi markets"
    echo "   • Detecting arbitrage opportunities"
    echo "   • Simulating trades with PnL tracking"
    echo ""
    echo "📈 Useful Commands:"
    echo "   View bot logs:         tail -f $BOT_DIR/arbitrage_bot.log"
    echo "   View error logs:       tail -f $BOT_DIR/arbitrage_bot_error.log"
    echo "   View watchdog logs:    tail -f $BOT_DIR/watchdog.log"
    echo "   Check if running:      ps aux | grep -E 'main.py|run_autonomous'"
    echo "   Stop bot:              pkill -f run_autonomous.sh"
    echo "   Restart bot:           ./deploy_autonomous.sh"
    echo ""
    echo "🔍 Current Status:"
    ps aux | grep -E "main.py|run_autonomous" | grep -v grep
    echo ""
    echo "💡 The bot will keep running even if you close your terminal!"
    echo "💡 It will automatically restart if it crashes!"
    echo "💡 Let it run for a week, then review paper trading results!"
else
    echo ""
    echo "❌ Failed to start watchdog."
    echo ""
    echo "🔍 Checking logs..."
    tail -20 watchdog_nohup.log
    exit 1
fi
