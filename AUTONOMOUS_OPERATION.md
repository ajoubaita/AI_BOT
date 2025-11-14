# Autonomous Bot Operation Guide

## Overview

The arbitrage bot now runs as a **systemd service**, ensuring:
- ✅ 24/7 autonomous operation
- ✅ Automatic restart on crashes
- ✅ Auto-start on system reboot
- ✅ Proper logging and monitoring
- ✅ No need to keep terminal open

---

## Initial Deployment

Run the deployment script:

```bash
cd /home/user/AI_BOT
./deploy.sh
```

The script will:
1. Set up Python virtual environment
2. Install all dependencies
3. Configure paper trading mode
4. Install systemd service
5. Enable auto-start on boot
6. Start the bot

---

## Managing the Bot

### Check Status

```bash
# Quick status check
systemctl status arbitrage-bot

# Detailed service logs
journalctl -u arbitrage-bot -f

# Live bot logs
tail -f /home/user/AI_BOT/arbitrage_bot.log

# Error logs
tail -f /home/user/AI_BOT/arbitrage_bot_error.log
```

### Start/Stop/Restart

```bash
# Start the bot
systemctl start arbitrage-bot

# Stop the bot
systemctl stop arbitrage-bot

# Restart the bot
systemctl restart arbitrage-bot

# Check if running
systemctl is-active arbitrage-bot
```

### Enable/Disable Auto-Start

```bash
# Enable auto-start on boot
systemctl enable arbitrage-bot

# Disable auto-start on boot
systemctl disable arbitrage-bot
```

---

## Monitoring

### Real-Time Logs

```bash
# Watch bot logs in real-time
tail -f /home/user/AI_BOT/arbitrage_bot.log

# Watch last 50 lines, updating every 2 seconds
watch -n 2 'tail -50 /home/user/AI_BOT/arbitrage_bot.log'

# Filter for opportunities found
tail -f /home/user/AI_BOT/arbitrage_bot.log | grep "Found.*opportunities"

# Filter for paper trades
tail -f /home/user/AI_BOT/arbitrage_bot.log | grep "PAPER TRADE"
```

### Service Health

```bash
# Check if service is active
systemctl is-active arbitrage-bot

# Check if service is enabled (auto-start)
systemctl is-enabled arbitrage-bot

# View service details
systemctl show arbitrage-bot

# View recent service restarts
journalctl -u arbitrage-bot | grep "Started\|Stopped"
```

---

## Troubleshooting

### Bot Not Starting

```bash
# Check service status
systemctl status arbitrage-bot

# View detailed error logs
journalctl -u arbitrage-bot -n 100 --no-pager

# Check Python errors
tail -100 /home/user/AI_BOT/arbitrage_bot_error.log

# Verify .env file exists
ls -la /home/user/AI_BOT/.env
```

### Bot Keeps Restarting

```bash
# View restart history
journalctl -u arbitrage-bot | grep "Started arbitrage-bot.service"

# Check for errors
journalctl -u arbitrage-bot | grep "ERROR\|CRITICAL\|Failed"

# View last crash
journalctl -u arbitrage-bot -n 200 --no-pager
```

### Bot Not Finding Markets

```bash
# Check market discovery logs
tail -200 /home/user/AI_BOT/arbitrage_bot.log | grep "Discovered\|markets"

# Verify API credentials in .env
grep -E "KALSHI_|POLYMARKET_" /home/user/AI_BOT/.env

# Test market discovery manually
cd /home/user/AI_BOT
source venv/bin/activate
python test_polymarket_discovery.py
```

---

## Auto-Restart Configuration

The systemd service is configured to automatically restart the bot:

- **Restart Policy**: Always restart
- **Restart Delay**: 10 seconds
- **No Restart Limit**: Unlimited restart attempts

These settings are in `/etc/systemd/system/arbitrage-bot.service`:

```ini
Restart=always
RestartSec=10
StartLimitInterval=0
```

---

## Watchdog Features

The bot includes a built-in watchdog that:

1. **Monitors WebSocket Health**
   - Checks every 60 seconds
   - Detects stale connections
   - Auto-restarts WebSocket if dead

2. **Retry Logic**
   - Initialization: 5 retries with exponential backoff
   - Market discovery: 3 retries
   - WebSocket failures: Non-fatal, bot continues

3. **Graceful Degradation**
   - If WebSockets fail, bot continues with API polling
   - If one platform fails, bot continues with other platform
   - Circuit breakers prevent runaway losses

---

## Performance Monitoring

### Check Bot Uptime

```bash
# View service start time
systemctl show arbitrage-bot --property=ActiveEnterTimestamp

# View all restarts
journalctl -u arbitrage-bot | grep "Started"
```

### Check Resource Usage

```bash
# CPU and memory usage
systemctl status arbitrage-bot

# Detailed resource stats
ps aux | grep "python.*main.py"

# Monitor resource usage over time
top -p $(pgrep -f "python.*main.py")
```

### Paper Trading Performance

```bash
# View paper trading results
grep "PAPER TRADE" /home/user/AI_BOT/arbitrage_bot.log

# Count opportunities found
grep -c "Found.*opportunities" /home/user/AI_BOT/arbitrage_bot.log

# View PnL updates
grep "Paper PnL" /home/user/AI_BOT/arbitrage_bot.log
```

---

## Updating the Bot

When you make code changes:

```bash
cd /home/user/AI_BOT
./deploy.sh
```

This will:
1. Pull latest code
2. Update dependencies
3. Restart the service

---

## Logs Rotation

Logs are stored in:
- `/home/user/AI_BOT/arbitrage_bot.log` - Main logs
- `/home/user/AI_BOT/arbitrage_bot_error.log` - Error logs

To prevent disk space issues:

```bash
# Check log file sizes
ls -lh /home/user/AI_BOT/*.log

# Archive old logs
cd /home/user/AI_BOT
tar -czf logs_backup_$(date +%Y%m%d).tar.gz *.log
> arbitrage_bot.log  # Clear current log
> arbitrage_bot_error.log

# Or use logrotate (advanced)
# Create /etc/logrotate.d/arbitrage-bot
```

---

## Emergency Stop

If you need to stop the bot immediately:

```bash
# Stop service
sudo systemctl stop arbitrage-bot

# Disable auto-restart
sudo systemctl disable arbitrage-bot

# Kill any remaining processes
pkill -f "python.*main.py"
```

---

## Testing Autonomous Restart

To verify the bot restarts automatically after a crash:

```bash
# Get bot PID
PID=$(pgrep -f "python.*main.py")

# Kill the process (simulates crash)
kill -9 $PID

# Wait 10 seconds
sleep 10

# Check if it restarted
systemctl status arbitrage-bot

# You should see a new PID and "active (running)" status
```

---

## Summary

**The bot is now truly autonomous:**

✅ No need to keep terminal open
✅ Survives server reboots
✅ Auto-restarts on crashes
✅ Monitors its own health
✅ Logs everything for debugging

**You can now:**
- Close your SSH session
- Turn off your local computer
- Come back days/weeks later

**The bot will keep running 24/7!**
