#!/bin/bash
# Autonomous deployment script for arbitrage bot
# Sets up systemd service for 24/7 autonomous operation with auto-restart
# ALWAYS starts in paper trading mode by default

set -e  # Exit on error

echo "🚀 Deploying Arbitrage Bot with Autonomous Operation..."

# Navigate to bot directory
BOT_DIR="/home/user/AI_BOT"
cd "$BOT_DIR" || exit 1

# Check if running as root (needed for systemd)
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  This script needs root access to set up systemd service"
    echo "   Re-running with sudo..."
    exec sudo bash "$0" "$@"
fi

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

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Always start in TEST MODE (paper trading)
echo "🧪 Configuring PAPER TRADING MODE..."
if [ -f .env ]; then
    sed -i 's/TEST_MODE=false/TEST_MODE=true/' .env
    # Also ensure it's set if not present
    if ! grep -q "TEST_MODE" .env; then
        echo "TEST_MODE=true" >> .env
    fi
else
    echo "❌ .env file not found! Please create it first."
    exit 1
fi

# Stop any running instances (systemd service or manual)
echo "🛑 Stopping existing bot instances..."
systemctl stop arbitrage-bot 2>/dev/null || echo "Service not running"
pkill -f "python.*main.py" 2>/dev/null || echo "No manual instances found"
sleep 2

# Install systemd service
echo "📋 Installing systemd service for autonomous operation..."

# Copy service file to systemd directory
cp "$BOT_DIR/arbitrage-bot.service" /etc/systemd/system/arbitrage-bot.service

# Reload systemd to recognize new service
systemctl daemon-reload

# Enable service to start on boot
systemctl enable arbitrage-bot

# Start the service
echo "▶️  Starting arbitrage bot as systemd service..."
systemctl start arbitrage-bot

# Wait for startup
sleep 3

# Check status
if systemctl is-active --quiet arbitrage-bot; then
    echo ""
    echo "✅ ✅ ✅ BOT DEPLOYED SUCCESSFULLY! ✅ ✅ ✅"
    echo ""
    echo "🤖 The bot is now running AUTONOMOUSLY:"
    echo "   • Runs 24/7 in the background"
    echo "   • Auto-restarts if it crashes"
    echo "   • Auto-starts on system reboot"
    echo "   • Paper trading mode (no real money)"
    echo ""
    echo "📊 The bot is:"
    echo "   • Scanning 20k+ Polymarket markets"
    echo "   • Scanning 115k+ Kalshi markets"
    echo "   • Detecting arbitrage opportunities"
    echo "   • Simulating trades with PnL tracking"
    echo ""
    echo "📈 Useful Commands:"
    echo "   View live logs:        tail -f $BOT_DIR/arbitrage_bot.log"
    echo "   View error logs:       tail -f $BOT_DIR/arbitrage_bot_error.log"
    echo "   Service status:        systemctl status arbitrage-bot"
    echo "   Restart bot:           systemctl restart arbitrage-bot"
    echo "   Stop bot:              systemctl stop arbitrage-bot"
    echo "   View service logs:     journalctl -u arbitrage-bot -f"
    echo ""
    echo "🔍 Service Status:"
    systemctl status arbitrage-bot --no-pager -l
    echo ""
    echo "💡 The bot will keep running even if you close your terminal!"
    echo "💡 It will automatically restart if it crashes!"
    echo "💡 Let it run for a week, then review paper trading results!"
else
    echo ""
    echo "❌ Failed to start bot service."
    echo ""
    echo "🔍 Checking logs..."
    journalctl -u arbitrage-bot -n 50 --no-pager
    echo ""
    echo "📋 Service status:"
    systemctl status arbitrage-bot --no-pager -l
    exit 1
fi
