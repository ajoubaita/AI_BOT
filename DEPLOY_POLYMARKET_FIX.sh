#!/bin/bash
# Quick deployment script for Polymarket improvements

echo "🚀 Deploying Polymarket Integration Updates..."
echo ""

# SSH into server and deploy
ssh root@192.241.128.44 << 'ENDSSH'
cd ~/AI_BOT

# Pull latest code
echo "📥 Pulling updates..."
git pull origin claude/arbitrage-trading-bot-011CUwBKDUvEnEjbP8mjMugD

# Activate virtual environment
source venv/bin/activate

# Install dependencies (in case any changed)
pip install -r requirements.txt --quiet

# Run unit tests
echo ""
echo "🧪 Running Polymarket discovery tests..."
python test_polymarket_discovery.py

# If tests passed, restart bot
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Tests passed! Restarting bot..."
    pkill -f "python.*main.py" 2>/dev/null
    ./deploy.sh
else
    echo ""
    echo "❌ Tests failed. Please check the output above."
    exit 1
fi

ENDSSH

echo ""
echo "✅ Deployment complete!"
echo ""
echo "To monitor the bot:"
echo "  ssh root@192.241.128.44 'tail -f ~/AI_BOT/arbitrage_bot.log'"
echo ""
echo "Look for:"
echo "  - Gamma Events API healthy"
echo "  - Polymarket markets discovered"
echo "  - Cross-platform arbitrage opportunities"
