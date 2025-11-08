"""
Test Script for Arbitrage Bot
Demonstrates bot functionality with mock data
"""

import asyncio
import logging
from websocket_streamer import PriceStore
from arbitrage_engine import ArbitrageEngine
from kalshi_trader import KalshiTrader
from polymarket_trader import PolymarketTrader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_arbitrage_detection():
    """Test arbitrage detection with mock data"""

    logger.info("🧪 Testing Arbitrage Detection\n")

    # Create price store
    price_store = PriceStore()

    # Mock traders (won't actually execute in test)
    kalshi_trader = KalshiTrader()
    polymarket_trader = PolymarketTrader()

    # Create arbitrage engine
    engine = ArbitrageEngine(price_store, kalshi_trader, polymarket_trader)

    # Set test configuration
    engine.min_profit_threshold = 0.01
    engine.max_position_size = 10

    # Test Case 1: Cross-platform arbitrage
    logger.info("Test Case 1: Cross-Platform Arbitrage")
    logger.info("-" * 50)

    # Mock market mapping
    market_mapping = {
        'kalshi_market': {
            'market_id': 'PRES2024-TEST',
            'title': 'Will Candidate A win 2024 election?'
        },
        'polymarket_market': {
            'ticker_or_token_id': 'TOKEN-123',
            'title': 'Will Candidate A win 2024 election?'
        }
    }

    # Mock prices - Kalshi more expensive, Polymarket cheaper
    price_store.update('kalshi', 'PRES2024-TEST', {
        'yes_bid': 0.60,  # Kalshi willing to buy YES at $0.60
        'yes_ask': 0.62,  # Kalshi selling YES at $0.62
        'no_bid': 0.38,
        'no_ask': 0.40
    })

    price_store.update('polymarket', 'TOKEN-123', {
        'best_bid': 0.56,  # Polymarket buying at $0.56
        'best_ask': 0.58,  # Polymarket selling at $0.58
        'price': 0.57
    })

    engine.set_market_mappings([market_mapping])

    # Scan for opportunities
    opportunities = await engine.scan_for_opportunities()

    if opportunities:
        for opp in opportunities:
            logger.info(f"✅ Found: {opp}")
            logger.info(f"   Strategy: Buy Polymarket @ $0.58, Sell Kalshi @ $0.60")
            logger.info(f"   Profit per contract: $0.02")
            logger.info(f"   Expected total profit: ${opp.expected_profit:.4f}\n")
    else:
        logger.info("❌ No cross-platform arbitrage found\n")

    # Test Case 2: Intra-platform arbitrage
    logger.info("Test Case 2: Intra-Platform Arbitrage (Kalshi)")
    logger.info("-" * 50)

    # Mock prices where YES + NO < 1.00
    price_store.update('kalshi', 'MARKET-ARB', {
        'yes_ask': 0.45,  # Can buy YES at $0.45
        'no_ask': 0.50,   # Can buy NO at $0.50
        'yes_bid': 0.43,
        'no_bid': 0.48
    })

    # Scan for opportunities
    opportunities = await engine.scan_for_opportunities()

    intra_opps = [o for o in opportunities if o.opportunity_type == 'intra_platform']

    if intra_opps:
        for opp in intra_opps:
            logger.info(f"✅ Found: {opp}")
            logger.info(f"   Strategy: Buy YES @ $0.45 + NO @ $0.50 = $0.95")
            logger.info(f"   Payout: $1.00")
            logger.info(f"   Profit per contract: $0.05")
            logger.info(f"   Expected total profit: ${opp.expected_profit:.4f}\n")
    else:
        logger.info("❌ No intra-platform arbitrage found\n")

    # Test Case 3: No arbitrage opportunity
    logger.info("Test Case 3: No Arbitrage (Efficient Market)")
    logger.info("-" * 50)

    # Mock efficient prices
    price_store.update('kalshi', 'EFFICIENT-MARKET', {
        'yes_ask': 0.51,
        'no_ask': 0.50,  # Total = 1.01 (normal spread)
        'yes_bid': 0.49,
        'no_bid': 0.48
    })

    opportunities = await engine.scan_for_opportunities()

    efficient_opps = [o for o in opportunities
                     if 'EFFICIENT-MARKET' in str(o.legs)]

    if not efficient_opps:
        logger.info("✅ Correctly detected no arbitrage opportunity")
        logger.info("   YES ask ($0.51) + NO ask ($0.50) = $1.01 (normal)")
        logger.info("   No profit after fees\n")
    else:
        logger.info("❌ False positive detected\n")

    # Test Case 4: Circuit breaker
    logger.info("Test Case 4: Circuit Breaker")
    logger.info("-" * 50)

    # Simulate losses
    engine.daily_pnl = -600  # Exceeds circuit breaker threshold

    engine._check_circuit_breaker()

    if engine.circuit_breaker_triggered:
        logger.info("✅ Circuit breaker triggered correctly")
        logger.info(f"   Daily PnL: ${engine.daily_pnl:.2f}")
        logger.info(f"   Threshold: ${-engine.circuit_breaker_loss:.2f}\n")

    # Print final stats
    logger.info("\n" + "=" * 50)
    logger.info("📊 Test Summary")
    logger.info("=" * 50)
    stats = engine.get_stats()
    logger.info(f"Total opportunities tested: 4")
    logger.info(f"Circuit breaker status: {'TRIGGERED' if stats['circuit_breaker_triggered'] else 'OK'}")
    logger.info(f"Configuration:")
    logger.info(f"  Min profit threshold: ${stats['config']['min_profit_threshold']:.2f}")
    logger.info(f"  Max position size: {stats['config']['max_position_size']}")
    logger.info("=" * 50 + "\n")


async def test_market_discovery():
    """Test market discovery (requires API access)"""
    from market_discovery import MarketDiscovery

    logger.info("\n🧪 Testing Market Discovery")
    logger.info("Note: This test requires API access and may take a while\n")

    try:
        async with MarketDiscovery() as discovery:
            # Fetch a small sample
            logger.info("Fetching markets from both platforms...")

            markets = await discovery.discover_all_markets()

            logger.info(f"✅ Discovered {len(markets)} total markets")
            logger.info(f"   Kalshi: {len([m for m in markets if m['platform'] == 'kalshi'])}")
            logger.info(f"   Polymarket: {len([m for m in markets if m['platform'] == 'polymarket'])}")

            if markets:
                logger.info("\nSample markets:")
                for i, market in enumerate(markets[:3]):
                    logger.info(f"\n{i+1}. {market['title'][:60]}")
                    logger.info(f"   Platform: {market['platform']}")
                    logger.info(f"   Yes price: ${market['yes_price']:.2f}")
                    logger.info(f"   Volume: {market['volume']}")

    except Exception as e:
        logger.error(f"❌ Market discovery test failed: {e}")
        logger.info("   This is expected if API credentials are not configured")


async def main():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("🤖 ARBITRAGE BOT TEST SUITE")
    logger.info("=" * 60 + "\n")

    # Test 1: Arbitrage detection (always works)
    await test_arbitrage_detection()

    # Test 2: Market discovery (requires API credentials)
    # Uncomment to test with real API:
    # await test_market_discovery()

    logger.info("\n✅ All tests completed!\n")


if __name__ == '__main__':
    asyncio.run(main())
