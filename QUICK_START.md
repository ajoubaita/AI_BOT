# Quick Start Guide - Autonomous Bot Operation

## ✅ Problem Solved

Your bot is now running **24/7 autonomously** with automatic restart on crashes!

---

## 🚀 Deployment

```bash
cd /home/user/AI_BOT
./deploy_autonomous.sh
```

That's it! The bot will now:
- ✅ Run 24/7 in the background
- ✅ Automatically restart if it crashes
- ✅ Keep running even if you close your terminal
- ✅ Survive network hiccups and API failures

---

## 📊 Monitoring

### Check Status

```bash
# See if bot and watchdog are running
ps aux | grep -E "main.py|run_autonomous" | grep -v grep
```

### View Logs

```bash
# Bot activity logs
tail -f /home/user/AI_BOT/arbitrage_bot.log

# Error logs
tail -f /home/user/AI_BOT/arbitrage_bot_error.log

# Watchdog restart logs
tail -f /home/user/AI_BOT/watchdog.log

# Watch last 30 lines updating every 3 seconds
watch -n 3 'tail -30 /home/user/AI_BOT/arbitrage_bot.log'
```

### Check Paper Trading Performance

```bash
# View all paper trades
grep "PAPER TRADE" /home/user/AI_BOT/arbitrage_bot.log

# Count opportunities found
grep -c "Found.*opportunities" /home/user/AI_BOT/arbitrage_bot.log

# View locked-in profits
grep "LOCKED-IN PROFIT" /home/user/AI_BOT/arbitrage_bot.log

# View running PnL
grep "Running Total Paper PnL" /home/user/AI_BOT/arbitrage_bot.log
```

---

## 🛑 Control

### Stop the Bot

```bash
pkill -f run_autonomous.sh
```

This stops both the watchdog and the bot.

### Restart the Bot

```bash
./deploy_autonomous.sh
```

This will:
1. Stop any existing instances
2. Update code (if you pulled changes)
3. Restart watchdog and bot

---

## 🔍 Troubleshooting

### Bot Not Running

```bash
# Check watchdog logs
tail -50 /home/user/AI_BOT/watchdog.log

# Check error logs
tail -50 /home/user/AI_BOT/arbitrage_bot_error.log

# Redeploy
./deploy_autonomous.sh
```

### Bot Keeps Crashing

The watchdog will automatically restart the bot up to 5 times. If it fails 5 times in a row, it means there's a serious issue.

```bash
# Check what's wrong
tail -100 /home/user/AI_BOT/arbitrage_bot_error.log

# Common issues:
# 1. Missing .env file
# 2. API credentials expired
# 3. Network connectivity issues
```

### View Crash History

```bash
# See all restart attempts
grep "Bot not running" /home/user/AI_BOT/watchdog.log

# See successful restarts
grep "✅ Bot started successfully" /home/user/AI_BOT/watchdog.log
```

---

## 🧪 Testing Auto-Restart

Want to verify the bot restarts automatically?

```bash
# Kill the bot process (simulates crash)
pkill -f "python.*main.py"

# Wait 5 seconds
sleep 5

# Check if it restarted
ps aux | grep "main.py" | grep -v grep

# You should see a new bot process running!
```

---

## 📈 How the Watchdog Works

The watchdog script (`run_autonomous.sh`) runs continuously in the background and:

1. **Monitors** the bot process every 30 seconds
2. **Detects** if the bot has crashed or stopped
3. **Restarts** the bot automatically with a new process
4. **Logs** all restart attempts to `watchdog.log`
5. **Backs off** exponentially if bot fails repeatedly (10s, 20s, 30s, ...)
6. **Gives up** after 5 consecutive failures (indicates serious problem)

---

## 🎯 What's Different Now?

### Before (The Problem):
- Bot would stop running after WebSocket errors
- Required keeping terminal open
- No automatic recovery
- Manual intervention needed

### After (The Solution):
- Bot runs independently in background
- Watchdog monitors and restarts automatically
- Runs 24/7 without user intervention
- Close your terminal anytime - bot keeps running!

---

## 💡 Pro Tips

### 1. Monitor Uptime

```bash
# See when watchdog started
grep "Watchdog Started" /home/user/AI_BOT/watchdog.log

# Count total restarts
grep -c "Bot not running" /home/user/AI_BOT/watchdog.log
```

### 2. Archive Old Logs

```bash
cd /home/user/AI_BOT
tar -czf logs_$(date +%Y%m%d).tar.gz *.log
> arbitrage_bot.log      # Clear current log
> watchdog.log
```

### 3. Update Bot Code

```bash
git pull origin claude/arbitrage-trading-bot-011CUwBKDUvEnEjbP8mjMugD
./deploy_autonomous.sh  # Redeploy with new code
```

---

## ✅ Success Indicators

Your bot is running correctly if you see:

1. **Two processes running:**
   - `/bin/bash ./run_autonomous.sh` (watchdog)
   - `python /home/user/AI_BOT/main.py` (bot)

2. **Logs being written:**
   - `arbitrage_bot.log` file size increasing
   - Recent timestamps in logs

3. **Watchdog confirms success:**
   - "✅ Bot started successfully" in `watchdog.log`

---

## 🎉 You're All Set!

Your bot is now truly autonomous. You can:
- ✅ Close your SSH session
- ✅ Turn off your local computer
- ✅ Come back days/weeks later
- ✅ Bot will still be running!

Just check logs occasionally to see paper trading results.

**The bot will keep scanning markets 24/7 and log all arbitrage opportunities it finds!**
