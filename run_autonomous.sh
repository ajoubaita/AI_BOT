#!/bin/bash
# Autonomous bot wrapper with auto-restart
# Keeps the bot running 24/7 and restarts it if it crashes

BOT_DIR="/home/user/AI_BOT"
LOG_FILE="$BOT_DIR/arbitrage_bot.log"
ERROR_LOG="$BOT_DIR/arbitrage_bot_error.log"
WATCHDOG_LOG="$BOT_DIR/watchdog.log"
PYTHON="$BOT_DIR/venv/bin/python"
SCRIPT="$BOT_DIR/main.py"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$WATCHDOG_LOG"
}

# Function to check if bot is running
is_running() {
    pgrep -f "python.*main.py" > /dev/null
}

# Trap signals for graceful shutdown
trap 'log "Watchdog received shutdown signal"; kill $BOT_PID 2>/dev/null; exit 0' SIGTERM SIGINT

log "========================================="
log "Autonomous Bot Watchdog Started"
log "========================================="

# Ensure we're in the right directory
cd "$BOT_DIR" || exit 1

# Ensure virtual environment exists
if [ ! -d "venv" ]; then
    log "ERROR: Virtual environment not found. Run deploy.sh first."
    exit 1
fi

# Main watchdog loop
restart_count=0
consecutive_failures=0
max_consecutive_failures=5

while true; do
    if ! is_running; then
        restart_count=$((restart_count + 1))

        log "Bot not running. Starting attempt #$restart_count..."
        log "Command: $PYTHON $SCRIPT"

        # Start the bot in the background
        nohup "$PYTHON" "$SCRIPT" >> "$LOG_FILE" 2>> "$ERROR_LOG" &
        BOT_PID=$!

        log "Bot started with PID: $BOT_PID"

        # Wait a bit to see if it starts successfully
        sleep 10

        if is_running; then
            log "✅ Bot started successfully (PID: $BOT_PID)"
            consecutive_failures=0
        else
            consecutive_failures=$((consecutive_failures + 1))
            log "❌ Bot failed to start (attempt $consecutive_failures/$max_consecutive_failures)"

            # Show last error
            log "Last error from logs:"
            tail -5 "$ERROR_LOG" | while read line; do
                log "  ERROR: $line"
            done

            if [ $consecutive_failures -ge $max_consecutive_failures ]; then
                log "CRITICAL: Bot failed to start $max_consecutive_failures times in a row"
                log "CRITICAL: Something is seriously wrong. Check logs and restart manually."
                log "CRITICAL: Logs are in: $LOG_FILE and $ERROR_LOG"
                exit 1
            fi

            # Exponential backoff
            backoff_seconds=$((10 * consecutive_failures))
            log "Waiting $backoff_seconds seconds before retry..."
            sleep $backoff_seconds
        fi
    else
        # Bot is running, just monitor it
        sleep 30  # Check every 30 seconds
    fi
done
