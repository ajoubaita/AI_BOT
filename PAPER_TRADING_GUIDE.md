# Paper Trading Guide

## Understanding Arbitrage Profit

**Important:** Arbitrage profit is **IMMEDIATE and LOCKED-IN** when you execute both legs simultaneously. Unlike traditional trading, you don't wait for price movements - the profit is guaranteed the moment both trades execute.

## How It Works

### Intra-Platform Arbitrage (Kalshi)
```
Example:
- Buy YES @ $0.45
- Buy NO @ $0.50
- Total Cost: $0.95
- Guaranteed Payout: $1.00
- IMMEDIATE LOCKED-IN PROFIT: $0.05 per contract
```

When the market resolves, one contract pays $1.00, the other pays $0.00. You spent $0.95, you get $1.00 back.

### Cross-Platform Arbitrage
```
Example:
- Polymarket selling YES @ $0.55
- Kalshi buying YES @ $0.60
- Action: Buy on Polymarket, immediately sell on Kalshi
- IMMEDIATE LOCKED-IN PROFIT: $0.05 per contract
```

You buy and sell simultaneously, locking in the price difference.

## Paper Trading Output

When running with `TEST_MODE=true`, you'll see detailed logs:

### Example 1: Intra-Platform Arbitrage

```
💰 Found 1 arbitrage opportunities!
   Executing: ArbitrageOpportunity(type=intra_platform, profit=$0.0456, confidence=99%)

[PAPER TRADE] Simulating intra_platform arbitrage
[PAPER TRADE] Executing 2 legs:
[PAPER TRADE]   Leg 1: BUY 10 KXTOPAPT-26-JAN01-META YES @ $0.4500 on Kalshi
[PAPER TRADE]   Leg 2: BUY 10 KXTOPAPT-26-JAN01-META NO @ $0.5000 on Kalshi
✅ [PAPER TRADE] IMMEDIATE LOCKED-IN PROFIT: $0.4560
[PAPER TRADE] Strategy: intra_platform
[PAPER TRADE] Confidence: 99.0%
[PAPER TRADE] Mechanism: Buy YES+NO < $1.00, guaranteed payout $1.00
[PAPER TRADE] Running Total Paper PnL: $0.46 (Daily: $0.46)
----------------------------------------------------------------------
```

**What this means:**
- Bought 10 YES contracts @ $0.45 each = $4.50
- Bought 10 NO contracts @ $0.50 each = $5.00
- Total spent: $9.50
- When market resolves, get $10.00 back
- Profit: $0.50 (before fees ~7%) = **~$0.46 net**

### Example 2: Cross-Platform Arbitrage

```
[PAPER TRADE] Simulating cross_platform arbitrage
[PAPER TRADE] Executing 2 legs:
[PAPER TRADE]   Leg 1: BUY 25 contracts @ $0.5500 on Polymarket (token: 0x1a2b3c...)
[PAPER TRADE]   Leg 2: SELL 25 PRES2024 YES @ $0.6000 on Kalshi
✅ [PAPER TRADE] IMMEDIATE LOCKED-IN PROFIT: $1.1875
[PAPER TRADE] Strategy: cross_platform
[PAPER TRADE] Confidence: 83.3%
[PAPER TRADE] Mechanism: Buy low on one platform, sell high on other
[PAPER TRADE] Running Total Paper PnL: $1.65 (Daily: $1.65)
----------------------------------------------------------------------
```

**What this means:**
- Buy 25 contracts on Polymarket @ $0.55 = $13.75
- Simultaneously sell 25 contracts on Kalshi @ $0.60 = $15.00
- Immediate profit: $1.25
- After fees (~9%): **~$1.19 net**

## Status Updates

Every ~60 seconds, you'll see:

```
============================================================
📊 ARBITRAGE BOT STATUS
============================================================
Uptime: 0:15:32
Opportunities Found: 47
Opportunities Executed: 12
Trades Executed: 24
Daily PnL: $5.67      ← Your hypothetical profit today
Total PnL: $5.67      ← Your total paper trading profit
Circuit Breaker: OK
Live Markets: 127
============================================================
```

## What to Watch For

### Good Signs ✅
- Consistent opportunities found
- High confidence (>80%)
- Positive Daily PnL trending upward
- Multiple arbitrage types detected

### Warning Signs ⚠️
- Very few opportunities (<5 per hour)
- Low confidence (<50%)
- Large position sizes (>50 contracts)
- Circuit breaker triggered

### Red Flags 🚨
- Negative Daily PnL (shouldn't happen with arbitrage)
- Circuit breaker triggered
- Opportunities found but 0 executed
- API errors in logs

## Understanding Fees

### Kalshi Fees
- 7% on profits only
- If you make $1.00 profit, you pay $0.07 fee
- Net profit: $0.93

### Polymarket Fees
- 2% on trade value
- If you buy $10.00 of contracts, you pay $0.20 fee

### Combined (Cross-Platform)
- Pay fees on both platforms
- Total ~9% on trade value
- Example: $1.00 gross profit → ~$0.91 net

## Paper Trading vs. Real Trading

| Aspect | Paper Trading | Real Trading |
|--------|--------------|--------------|
| **Risk** | None (simulated) | Real money at stake |
| **Execution** | Instant (assumed) | May have slippage |
| **Fills** | Always fills | May partially fill |
| **Network** | No latency | Real network delays |
| **Fees** | Estimated | Actual fees charged |
| **Profit** | Hypothetical | Real profit/loss |

## Transitioning to Real Trading

Before switching `TEST_MODE=false`:

1. **Run paper trading for 24+ hours**
   - Verify opportunities are being found
   - Confirm positive PnL
   - Check no errors in logs

2. **Review paper trading results**
   - What's your average profit per trade?
   - How many opportunities per day?
   - What's the confidence level?

3. **Start small**
   - Set `MAX_POSITION_SIZE=10` (not 100)
   - Set `MIN_PROFIT_THRESHOLD=0.03` (higher threshold)
   - Set `CIRCUIT_BREAKER_LOSS=50` (lower limit)

4. **Monitor closely**
   - Watch logs in real-time: `tail -f arbitrage_bot.log`
   - Check actual fills vs. expected
   - Verify fees match estimates

5. **Scale gradually**
   - If profitable for 48 hours, increase position size
   - Adjust thresholds based on actual results
   - Never risk more than you can afford to lose

## Common Questions

**Q: Why does profit show immediately?**
A: Arbitrage locks in profit when both legs execute. You're not speculating on price movement - you're capturing the price difference right now.

**Q: What if one leg fails?**
A: The bot will try to reverse the successful leg to minimize loss. This is called "partial fill handling."

**Q: Why aren't more opportunities found?**
A: Arbitrage opportunities are rare because:
- Markets are relatively efficient
- Other bots are also searching
- Opportunities exist for milliseconds
- Your profit threshold may be too high

**Q: Can I lose money with arbitrage?**
A: Yes, if:
- One leg executes but the other fails (partial fill)
- Fees are higher than estimated
- Prices move between leg executions
- Technical issues cause errors

**Q: How much can I make?**
A: Depends on:
- Number of opportunities (varies greatly)
- Your position size
- Market conditions
- Competition from other bots
- Realistic: $5-50/day with $1000 capital
- Optimistic: $50-200/day with $5000 capital

## Tips for Success

1. **Run 24/7**: Opportunities happen at random times
2. **Monitor daily**: Check logs at least once per day
3. **Adjust thresholds**: If too many/few opportunities, tweak settings
4. **Track actual fees**: Compare to estimates
5. **Have backup funds**: Don't use your last dollar
6. **Set alerts**: Use circuit breakers appropriately
7. **Keep API keys secure**: Never share credentials
8. **Test updates**: Always test in paper mode first

## Troubleshooting Paper Trading

**No opportunities found:**
- Check if markets are being discovered
- Lower `MIN_PROFIT_THRESHOLD` in .env
- Verify WebSocket connections in logs
- Markets may just be efficient (normal)

**Opportunities found but not executed:**
- Check for error messages in logs
- Verify `TEST_MODE=true` in .env
- Look for circuit breaker messages

**Negative PnL (shouldn't happen):**
- This indicates a bug - report it
- Arbitrage should always be profitable
- Check fee calculations

---

**Ready to start?**

```bash
# On your server
cd ~/AI_BOT
source venv/bin/activate
python main.py

# Watch logs
tail -f arbitrage_bot.log
```

Good luck! 🚀💰
