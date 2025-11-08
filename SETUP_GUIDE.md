# Setup Guide for Arbitrage Trading Bot

This guide walks you through setting up the arbitrage bot from scratch.

## 📋 Prerequisites Checklist

Before you begin, ensure you have:

- [ ] Python 3.10+ installed
- [ ] Kalshi account with API access
- [ ] Polymarket wallet on Polygon network
- [ ] Basic understanding of prediction markets
- [ ] Capital for trading (start small!)

## 🔧 Step-by-Step Setup

### Step 1: Install Python Dependencies

```bash
cd AI_BOT
pip install -r requirements.txt
```

Verify installation:
```bash
python -c "import websockets, aiohttp; print('✅ Dependencies installed')"
```

### Step 2: Set Up Kalshi Authentication

#### Option A: Email/Password + API Key

1. Log in to [Kalshi](https://kalshi.com)
2. Navigate to Settings → API
3. Generate an API key
4. Copy your API key

#### Option B: RSA Key Authentication (Recommended for production)

1. Generate RSA private key:
```bash
openssl genrsa -out kalshi_private_key.pem 2048
```

2. Extract public key:
```bash
openssl rsa -in kalshi_private_key.pem -pubout -out kalshi_public_key.pem
```

3. Upload public key to Kalshi:
   - Go to Kalshi Settings → API
   - Upload `kalshi_public_key.pem`
   - Copy your API key

4. Store private key securely:
```bash
chmod 600 kalshi_private_key.pem
mv kalshi_private_key.pem ~/.ssh/  # Or secure location
```

### Step 3: Set Up Polymarket Wallet

1. Create a Polygon wallet:
   - Use MetaMask or another Web3 wallet
   - Switch to Polygon network (Chain ID: 137)

2. Fund your wallet:
   - Bridge USDC to Polygon
   - Or buy MATIC and swap for USDC on Polygon

3. Export private key:
   - ⚠️ **NEVER share your private key**
   - In MetaMask: Settings → Security → Export Private Key
   - Copy the private key (starts with 0x)

4. Approve USDC spending:
   - Visit [Polymarket](https://polymarket.com)
   - Connect wallet
   - Approve USDC for trading

### Step 4: Configure Environment Variables

1. Copy example config:
```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:

```bash
nano .env  # or use your preferred editor
```

Required fields:
```bash
# Kalshi
KALSHI_EMAIL=your.email@example.com
KALSHI_PASSWORD=your_password
KALSHI_API_KEY=your_api_key_here
KALSHI_PRIVATE_KEY_PATH=/home/user/.ssh/kalshi_private_key.pem

# Polymarket
POLYMARKET_PRIVATE_KEY=0x1234567890abcdef...  # Your wallet private key
```

3. Secure the .env file:
```bash
chmod 600 .env
```

### Step 5: Test Configuration

Run the test script to verify everything works:

```bash
python test_bot.py
```

Expected output:
```
🧪 Testing Arbitrage Detection

Test Case 1: Cross-Platform Arbitrage
--------------------------------------------------
✅ Found: ArbitrageOpportunity(type=cross_platform, profit=$0.0168, confidence=67%)
...
```

### Step 6: Start with Test Mode

Before trading real money, run in test mode:

```bash
# Edit .env and set:
TEST_MODE=true

# Run the bot
python main.py
```

In test mode:
- Market discovery runs normally
- Opportunities are detected
- Orders are logged but NOT executed

### Step 7: Configure Risk Parameters

Based on your risk tolerance, adjust these in `.env`:

**Conservative (Recommended for beginners):**
```bash
MIN_PROFIT_THRESHOLD=0.03
MAX_POSITION_SIZE=10
MAX_DAILY_LOSS=100
CIRCUIT_BREAKER_LOSS=50
```

**Moderate:**
```bash
MIN_PROFIT_THRESHOLD=0.01
MAX_POSITION_SIZE=50
MAX_DAILY_LOSS=500
CIRCUIT_BREAKER_LOSS=250
```

**Aggressive (Experienced only):**
```bash
MIN_PROFIT_THRESHOLD=0.005
MAX_POSITION_SIZE=100
MAX_DAILY_LOSS=1000
CIRCUIT_BREAKER_LOSS=500
```

### Step 8: Run in Production

Once you've tested thoroughly:

1. Disable test mode:
```bash
# Edit .env
TEST_MODE=false
```

2. Start the bot:
```bash
python main.py
```

3. Monitor the logs:
```bash
tail -f arbitrage_bot.log
```

## 🔍 Verification Steps

### Verify Kalshi Connection

```python
import asyncio
from kalshi_trader import KalshiTrader

async def test():
    async with KalshiTrader() as trader:
        balance = await trader.get_balance()
        print(f"Balance: {balance}")

asyncio.run(test())
```

### Verify Polymarket Connection

```python
import asyncio
from polymarket_trader import PolymarketTrader

async def test():
    async with PolymarketTrader() as trader:
        balance = await trader.get_balance()
        print(f"Balance: {balance}")

asyncio.run(test())
```

## 🚨 Common Setup Issues

### Issue 1: ModuleNotFoundError

**Error:** `ModuleNotFoundError: No module named 'py_clob_client'`

**Solution:**
```bash
pip install py-clob-client
```

### Issue 2: Kalshi Authentication Failed

**Error:** `Kalshi authentication failed: 401`

**Solutions:**
- Verify email/password in `.env`
- Check API key is correct
- Ensure RSA private key path is correct
- Try regenerating API key on Kalshi

### Issue 3: Polymarket Connection Failed

**Error:** `Error initializing Polymarket client`

**Solutions:**
- Verify private key in `.env` starts with '0x'
- Check wallet has USDC balance
- Ensure USDC spending is approved
- Verify you're on Polygon mainnet (chain ID 137)

### Issue 4: No Markets Discovered

**Error:** `No markets discovered!`

**Solutions:**
- Check internet connection
- Verify API URLs are correct
- Check if APIs are experiencing downtime
- Review API rate limits

### Issue 5: WebSocket Connection Fails

**Error:** `Error connecting to Kalshi WebSocket`

**Solutions:**
- Check firewall settings
- Verify WebSocket URLs in `.env`
- Try different network connection
- Check if behind corporate proxy

## 📊 Monitoring Your Bot

### View Real-Time Logs

```bash
# Follow main log
tail -f arbitrage_bot.log

# Filter for opportunities
tail -f arbitrage_bot.log | grep "Found.*arbitrage"

# Filter for executions
tail -f arbitrage_bot.log | grep "executed"
```

### Check Bot Status

The bot prints status every ~60 seconds. Look for:

```
============================================================
📊 ARBITRAGE BOT STATUS
============================================================
Uptime: 0:12:34
Opportunities Found: 5
Opportunities Executed: 2
Trades Executed: 4
Daily PnL: $12.50
Total PnL: $12.50
Circuit Breaker: OK
Live Markets: 84
============================================================
```

### Monitor Resource Usage

```bash
# CPU and memory usage
top -p $(pgrep -f main.py)

# Network connections
netstat -an | grep ESTABLISHED | grep -E "(kalshi|polymarket)"
```

## 🛡️ Security Best Practices

1. **Never commit credentials to git:**
   ```bash
   # Verify .gitignore is working
   git status  # Should not show .env or *.pem files
   ```

2. **Secure your private keys:**
   ```bash
   chmod 600 .env
   chmod 600 kalshi_private_key.pem
   ```

3. **Use a dedicated wallet:**
   - Don't use your main wallet for bot trading
   - Only fund with amount you can afford to lose

4. **Enable 2FA:**
   - Enable two-factor authentication on Kalshi
   - Use hardware wallet for Polymarket if possible

5. **Regular backups:**
   ```bash
   # Backup your configuration (excluding secrets)
   cp .env .env.backup
   # Store backup in secure, offline location
   ```

## 📈 Next Steps

Once the bot is running successfully:

1. **Monitor performance** for the first few days
2. **Adjust parameters** based on results
3. **Review logs** for any errors or warnings
4. **Scale gradually** if profitable
5. **Keep software updated** with latest versions

## 🆘 Getting Help

If you encounter issues:

1. Check the logs: `cat arbitrage_bot.log`
2. Review this guide and the main README
3. Verify all configuration settings
4. Test with smaller position sizes
5. Run in TEST_MODE to debug without risk

## ⚠️ Final Reminders

- **Start small** - Use minimum position sizes initially
- **Monitor closely** - Watch the bot especially in first 24 hours
- **Set limits** - Use circuit breakers and daily loss limits
- **Test thoroughly** - Run in test mode until comfortable
- **Stay informed** - Understand the markets you're trading

---

**You're now ready to run the arbitrage bot! Good luck and trade responsibly! 🚀**
