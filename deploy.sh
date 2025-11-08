#!/bin/bash
# Quick deployment script for DigitalOcean server

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

# Start the bot
echo "▶️ Starting bot..."
echo ""
echo "Choose mode:"
echo "1) Test Mode (Paper Trading)"
echo "2) Production Mode (Real Trading)"
read -p "Enter choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    echo "Starting in TEST MODE (Paper Trading)..."
    # Update .env to enable test mode
    sed -i 's/TEST_MODE=false/TEST_MODE=true/' .env

    screen -dmS arbitrage_bot bash -c "source venv/bin/activate && python main.py"
    echo ""
    echo "✅ Bot started in TEST MODE!"
    echo "   Paper trading PnL will be tracked"
elif [ "$choice" = "2" ]; then
    echo "Starting in PRODUCTION MODE (Real Trading)..."
    # Update .env to disable test mode
    sed -i 's/TEST_MODE=true/TEST_MODE=false/' .env

    read -p "⚠️  WARNING: This uses REAL MONEY. Are you sure? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        screen -dmS arbitrage_bot bash -c "source venv/bin/activate && python main.py"
        echo ""
        echo "✅ Bot started in PRODUCTION MODE!"
        echo "   Real trades will be executed"
    else
        echo "Cancelled."
        exit 0
    fi
else
    echo "Invalid choice. Exiting."
    exit 1
fi

echo ""
echo "📊 Useful Commands:"
echo "   View logs:      tail -f ~/AI_BOT/arbitrage_bot.log"
echo "   Attach screen:  screen -r arbitrage_bot"
echo "   Stop bot:       pkill -f 'python.*main.py'"
echo "   Check status:   ps aux | grep main.py"
echo ""
