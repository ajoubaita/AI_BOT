# High-Frequency Arbitrage Trading Bot

A production-grade Python arbitrage trading bot that operates across **Kalshi** and **Polymarket** prediction markets. The system identifies and executes arbitrage opportunities with low latency and high reliability.

## 🎯 Features

### Core Capabilities
- **Cross-Platform Arbitrage**: Exploits price discrepancies between Kalshi and Polymarket
- **Intra-Platform Arbitrage**: Identifies mispriced Yes/No pairs on Kalshi
- **Real-Time Price Feeds**: WebSocket streams for live orderbook updates
- **Automated Execution**: Simultaneous order placement across platforms
- **Risk Management**: Circuit breakers, position limits, and slippage protection

### Technical Features
- Async I/O for high concurrency
- Thread-safe price store
- Automatic reconnection logic
- Rate limit handling
- Comprehensive logging
- Graceful error recovery

## 📁 Project Structure

```
AI_BOT/
├── main.py                    # Main orchestrator
├── market_discovery.py        # Market fetching and matching
├── kalshi_trader.py          # Kalshi API integration
├── polymarket_trader.py      # Polymarket API integration
├── websocket_streamer.py     # WebSocket price feeds
├── arbitrage_engine.py       # Arbitrage detection & execution
├── requirements.txt          # Python dependencies
├── .env.example             # Configuration template
└── README.md                # This file
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10 or higher
- Kalshi API credentials (email, password, API key)
- RSA private key for Kalshi authentication
- Polymarket wallet (Polygon mainnet)
- Polygon private key

### 2. Installation

```bash
# Clone the repository
cd AI_BOT

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Kalshi Configuration
KALSHI_EMAIL=your-email@example.com
KALSHI_PASSWORD=your-password
KALSHI_API_KEY=your-api-key
KALSHI_PRIVATE_KEY_PATH=/path/to/kalshi_private_key.pem

# Polymarket Configuration
POLYMARKET_PRIVATE_KEY=0x1234567890abcdef...

# Trading Parameters
MIN_PROFIT_THRESHOLD=0.01
MAX_POSITION_SIZE=100
SLIPPAGE_TOLERANCE=0.005

# Enable/disable strategies
ENABLE_CROSS_PLATFORM_ARB=true
ENABLE_INTRA_PLATFORM_ARB=true

# Risk Management
MAX_DAILY_LOSS=1000
CIRCUIT_BREAKER_LOSS=500

# Testing
TEST_MODE=false  # Set to true for dry-run mode
```

### 4. Run the Bot

```bash
# Production mode
python main.py

# Test mode (no actual trades)
TEST_MODE=true python main.py
```

## 📚 Module Documentation

### `market_discovery.py`

Discovers and normalizes markets from both platforms.

**Key Functions:**
- `fetch_kalshi_markets()`: Fetches all open Kalshi markets
- `fetch_polymarket_markets()`: Fetches all open Polymarket markets
- `find_matching_markets()`: Identifies matching markets across platforms

**Usage:**
```python
async with MarketDiscovery() as discovery:
    markets = await discovery.discover_all_markets()
    matches = discovery.find_matching_markets(markets)
```

### `kalshi_trader.py`

Handles Kalshi API authentication and order execution.

**Authentication:**
- RSA-PSS-SHA256 signature authentication
- Email/password login fallback

**Key Functions:**
- `place_order()`: Place limit or market orders
- `buy_yes()`, `buy_no()`, `sell_yes()`, `sell_no()`: Convenience methods
- `get_balance()`: Check account balance
- `get_positions()`: View current positions

**Usage:**
```python
async with KalshiTrader() as trader:
    result = await trader.buy_yes('TICKER-23', count=10, price=0.55)
```

### `polymarket_trader.py`

Integrates with Polymarket using py-clob-client SDK.

**Authentication:**
- EOA (Externally Owned Account) signature type
- Polygon private key

**Key Functions:**
- `buy()`, `sell()`: Execute trades
- `get_balance()`: Check balance and allowance
- `get_orderbook()`: Fetch current orderbook
- `cancel_order()`: Cancel open orders

**Usage:**
```python
async with PolymarketTrader() as trader:
    result = await trader.buy(token_id='TOKEN_ID', size=10, price=0.55)
```

### `websocket_streamer.py`

Maintains live price feeds via WebSocket connections.

**Components:**
- `PriceStore`: Thread-safe in-memory price storage
- `KalshiWebSocketStreamer`: Kalshi WebSocket client
- `PolymarketWebSocketStreamer`: Polymarket WebSocket client
- `WebSocketManager`: Orchestrates both connections

**Features:**
- Automatic reconnection
- Heartbeat/ping messages
- Real-time orderbook updates

**Usage:**
```python
price_store = PriceStore()
manager = WebSocketManager(price_store)

await manager.start(
    kalshi_tickers=['TICKER-1', 'TICKER-2'],
    polymarket_tokens=['TOKEN-A', 'TOKEN-B']
)
```

### `arbitrage_engine.py`

Detects and executes arbitrage opportunities.

**Strategies:**

1. **Cross-Platform Arbitrage**
   - Buy low on one platform, sell high on the other
   - Example: Kalshi Yes @ $0.60, Polymarket Yes @ $0.55 → Buy Polymarket, sell Kalshi

2. **Intra-Platform Arbitrage**
   - Exploit mispriced Yes/No pairs
   - Example: Yes @ $0.45 + No @ $0.50 = $0.95 → Buy both for guaranteed $0.05 profit

**Risk Management:**
- Minimum profit threshold
- Slippage tolerance
- Position size limits
- Circuit breaker on losses
- Partial fill handling

**Usage:**
```python
engine = ArbitrageEngine(price_store, kalshi_trader, polymarket_trader)
engine.set_market_mappings(matched_markets)

opportunities = await engine.scan_for_opportunities()
for opp in opportunities:
    result = await engine.execute_opportunity(opp)
```

### `main.py`

Main orchestrator that coordinates all components.

**Lifecycle:**
1. Initialize traders and connections
2. Discover markets and create mappings
3. Start WebSocket streams
4. Run arbitrage detection loop
5. Execute opportunities
6. Daily reset and rediscovery

**Signal Handling:**
- Graceful shutdown on SIGINT/SIGTERM
- Closes all connections properly
- Prints final statistics

## 🔐 Security Considerations

### API Keys and Private Keys
- Store credentials in `.env` file (never commit to git)
- Use environment variables in production
- Rotate API keys regularly

### RSA Key for Kalshi
Generate a private key:
```bash
openssl genrsa -out kalshi_private_key.pem 2048
```

### Polymarket Wallet
- Use a dedicated wallet for trading
- Never expose your private key
- Consider using a hardware wallet for key storage

## ⚠️ Risk Disclaimer

**Important:** This bot trades real money on prediction markets.

- **Capital Risk**: You can lose your entire investment
- **Execution Risk**: Partial fills can create unhedged positions
- **Market Risk**: Prices can move against you quickly
- **Technical Risk**: Bugs or downtime can cause losses

**Recommendations:**
1. Start with small position sizes
2. Use TEST_MODE for initial testing
3. Monitor the bot closely
4. Set appropriate risk limits
5. Understand the markets you're trading

## 🛠️ Configuration Guide

### Trading Parameters

| Parameter | Description | Default | Recommended |
|-----------|-------------|---------|-------------|
| `MIN_PROFIT_THRESHOLD` | Minimum profit per trade | $0.01 | $0.01 - $0.05 |
| `MAX_POSITION_SIZE` | Max contracts per trade | 100 | 10 - 100 |
| `SLIPPAGE_TOLERANCE` | Acceptable price slippage | 0.5% | 0.5% - 1% |

### Risk Management

| Parameter | Description | Default | Recommended |
|-----------|-------------|---------|-------------|
| `MAX_DAILY_LOSS` | Maximum daily loss limit | $1000 | Your risk tolerance |
| `CIRCUIT_BREAKER_LOSS` | Stop trading threshold | $500 | 50% of daily limit |
| `MAX_OPEN_ORDERS` | Max concurrent orders | 10 | 5 - 20 |

## 📊 Monitoring and Logging

### Log Levels
- `INFO`: Normal operation, opportunities, executions
- `WARNING`: Partial fills, reconnections, unusual events
- `ERROR`: Failed operations, API errors
- `CRITICAL`: Circuit breaker triggers

### Status Output

The bot prints status every ~1 minute:

```
============================================================
📊 ARBITRAGE BOT STATUS
============================================================
Uptime: 2:34:12
Opportunities Found: 47
Opportunities Executed: 12
Trades Executed: 24
Daily PnL: $23.45
Total PnL: $156.78
Circuit Breaker: OK
Live Markets: 127
============================================================
```

## 🧪 Testing

### Test Mode
Set `TEST_MODE=true` to run without executing real trades:

```bash
TEST_MODE=true python main.py
```

In test mode:
- Market discovery runs normally
- WebSocket streams connect
- Opportunities are detected
- Orders are logged but NOT executed

### Mock Data
You can add mock price data for testing:

```python
# In main.py or a test script
price_store.update('kalshi', 'TEST-TICKER', {
    'yes_bid': 0.55,
    'yes_ask': 0.57,
    'no_bid': 0.42,
    'no_ask': 0.44
})
```

## 🔧 Troubleshooting

### Common Issues

**1. WebSocket Connection Fails**
- Check network connectivity
- Verify API URLs are correct
- Look for rate limiting

**2. Authentication Errors**
- Verify API credentials in `.env`
- Check RSA private key path
- Ensure Polygon private key is valid

**3. No Opportunities Found**
- Markets may be efficiently priced
- Adjust `MIN_PROFIT_THRESHOLD` lower
- Check if markets are actively trading

**4. Partial Fills**
- Increase `SLIPPAGE_TOLERANCE`
- Reduce `MAX_POSITION_SIZE`
- Check market liquidity

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG python main.py
```

## 📈 Performance Optimization

### Latency Reduction
- Deploy on cloud server near exchange servers
- Use dedicated network connection
- Minimize processing in hot path

### Throughput
- Adjust `scan_interval` in main.py
- Increase `MAX_OPEN_ORDERS` if needed
- Use concurrent execution where possible

## 🤝 Contributing

This is a production trading system. Exercise caution when making changes:

1. Test thoroughly in TEST_MODE
2. Use small position sizes initially
3. Monitor for unexpected behavior
4. Document all changes

## 📄 License

This code is provided as-is for educational and trading purposes. Use at your own risk.

## 🆘 Support

For issues or questions:
1. Check the logs in `arbitrage_bot.log`
2. Review the troubleshooting section
3. Verify your configuration in `.env`

## 🚀 Future Enhancements

Potential improvements:
- Machine learning for better market matching
- Advanced position sizing (Kelly Criterion)
- Multi-leg arbitrage (3+ platforms)
- Historical backtesting
- Web dashboard for monitoring
- Telegram/email alerts
- Database storage for trades
- API rate limit optimization

---

**Happy Trading! 🎲💰**

*Remember: Arbitrage opportunities are rare and fleeting. This bot helps you catch them when they appear.*
