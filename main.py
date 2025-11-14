"""
Main Orchestrator for Arbitrage Trading Bot
Coordinates market discovery, WebSocket streaming, and arbitrage execution
"""

import os
import sys
import asyncio
import logging
import signal
from datetime import datetime, time, timedelta
from typing import Optional
from dotenv import load_dotenv

from market_discovery import MarketDiscovery
from websocket_streamer import PriceStore, WebSocketManager
from kalshi_trader import KalshiTrader
from polymarket_trader import PolymarketTrader
from arbitrage_engine import ArbitrageEngine

load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'arbitrage_bot.log')

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class ArbitrageBotSupervisor:
    """Main supervisor for the arbitrage trading bot"""

    def __init__(self):
        self.test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'

        # Core components
        self.price_store = PriceStore()
        self.market_discovery: Optional[MarketDiscovery] = None
        self.ws_manager: Optional[WebSocketManager] = None
        self.kalshi_trader: Optional[KalshiTrader] = None
        self.polymarket_trader: Optional[PolymarketTrader] = None
        self.arbitrage_engine: Optional[ArbitrageEngine] = None

        # State
        self.running = False
        self.market_mappings = []
        self.scan_interval = 1.0  # Scan for opportunities every second

        # Statistics
        self.start_time = None
        self.opportunities_found = 0
        self.opportunities_executed = 0

    async def initialize(self):
        """Initialize all components"""
        logger.info("🚀 Initializing Arbitrage Trading Bot")
        logger.info(f"   Test Mode: {self.test_mode}")

        try:
            # Initialize traders
            logger.info("Initializing trading clients...")
            self.kalshi_trader = KalshiTrader()
            self.polymarket_trader = PolymarketTrader()

            # Use context managers
            await self.kalshi_trader.__aenter__()
            await self.polymarket_trader.__aenter__()

            # Initialize arbitrage engine
            self.arbitrage_engine = ArbitrageEngine(
                self.price_store,
                self.kalshi_trader,
                self.polymarket_trader
            )

            # Initialize market discovery
            self.market_discovery = MarketDiscovery()
            await self.market_discovery.__aenter__()

            # Initialize WebSocket manager
            self.ws_manager = WebSocketManager(self.price_store)

            logger.info("✅ All components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize: {e}")
            return False

    async def discover_markets(self):
        """Discover and map markets from both platforms"""
        logger.info("🔍 Discovering markets across platforms...")

        try:
            # Fetch all markets
            markets = await self.market_discovery.discover_all_markets()

            if not markets:
                logger.warning("No markets discovered!")
                return False

            # Find matching markets for cross-platform arbitrage
            self.market_mappings = self.market_discovery.find_matching_markets(
                markets,
                similarity_threshold=0.7
            )

            logger.info(f"📊 Market Discovery Summary:")
            logger.info(f"   Total markets: {len(markets)}")
            logger.info(f"   Kalshi markets: {len([m for m in markets if m['platform'] == 'kalshi'])}")
            logger.info(f"   Polymarket markets: {len([m for m in markets if m['platform'] == 'polymarket'])}")
            logger.info(f"   Matched pairs: {len(self.market_mappings)}")

            # Set mappings in arbitrage engine
            self.arbitrage_engine.set_market_mappings(self.market_mappings)

            # Print top matches
            logger.info("\n📈 Top Market Matches:")
            for i, match in enumerate(self.market_mappings[:5]):
                logger.info(f"   {i+1}. Similarity: {match['similarity']:.2%}")
                logger.info(f"      Kalshi: {match['kalshi_market']['title'][:60]}")
                logger.info(f"      Polymarket: {match['polymarket_market']['title'][:60]}")

            return True

        except Exception as e:
            logger.error(f"Error discovering markets: {e}")
            return False

    async def start_websocket_streams(self):
        """Start WebSocket streams for live price updates"""
        logger.info("📡 Starting WebSocket streams...")

        try:
            # Collect tickers and token IDs to subscribe to
            kalshi_tickers = set()
            polymarket_tokens = set()

            # Add from market mappings
            for mapping in self.market_mappings:
                kalshi_tickers.add(mapping['kalshi_market']['market_id'])
                polymarket_tokens.add(mapping['polymarket_market']['ticker_or_token_id'])

            kalshi_tickers = list(kalshi_tickers)[:50]  # Limit to avoid overwhelming
            polymarket_tokens = list(polymarket_tokens)[:50]

            logger.info(f"   Subscribing to {len(kalshi_tickers)} Kalshi markets")
            logger.info(f"   Subscribing to {len(polymarket_tokens)} Polymarket markets")

            # Only start WebSocket manager if we have markets to monitor
            if kalshi_tickers or polymarket_tokens:
                # Start WebSocket manager in background
                self.ws_task = asyncio.create_task(
                    self.ws_manager.start(kalshi_tickers, polymarket_tokens)
                )

                # Wait a bit for initial data
                await asyncio.sleep(5)

                logger.info("✅ WebSocket streams started")
            else:
                logger.warning("⚠️ No markets to monitor - WebSocket streams not started")
                logger.info("   Bot will continue scanning for intra-platform arbitrage")

            return True

        except Exception as e:
            logger.error(f"Error starting WebSocket streams: {e}")
            return False

    async def arbitrage_loop(self):
        """Main arbitrage detection and execution loop"""
        logger.info("🔄 Starting arbitrage loop...")

        scan_count = 0

        while self.running:
            try:
                scan_count += 1

                # Scan for opportunities
                opportunities = await self.arbitrage_engine.scan_for_opportunities()

                if opportunities:
                    self.opportunities_found += len(opportunities)

                    logger.info(f"💰 Found {len(opportunities)} arbitrage opportunities!")

                    # Execute opportunities
                    for opp in opportunities:
                        if not self.running:
                            break

                        logger.info(f"   Executing: {opp}")

                        result = await self.arbitrage_engine.execute_opportunity(
                            opp,
                            test_mode=self.test_mode
                        )

                        if result['success']:
                            self.opportunities_executed += 1

                # Print status every 60 scans (~1 minute)
                if scan_count % 60 == 0:
                    self.print_status()

                # Wait before next scan
                await asyncio.sleep(self.scan_interval)

            except Exception as e:
                logger.error(f"Error in arbitrage loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    def print_status(self):
        """Print current status"""
        stats = self.arbitrage_engine.get_stats()
        uptime = datetime.now() - self.start_time if self.start_time else None

        logger.info("\n" + "="*60)
        logger.info("📊 ARBITRAGE BOT STATUS")
        logger.info("="*60)
        logger.info(f"Uptime: {uptime}")
        logger.info(f"Opportunities Found: {self.opportunities_found}")
        logger.info(f"Opportunities Executed: {self.opportunities_executed}")
        logger.info(f"Trades Executed: {stats['trades_executed']}")
        logger.info(f"Daily PnL: ${stats['daily_pnl']:.2f}")
        logger.info(f"Total PnL: ${stats['total_pnl']:.2f}")
        logger.info(f"Circuit Breaker: {'TRIGGERED' if stats['circuit_breaker_triggered'] else 'OK'}")

        # Price store status
        prices = self.price_store.get_all()
        logger.info(f"Live Markets: {len(prices)}")
        logger.info("="*60 + "\n")

    async def daily_reset(self):
        """Perform daily reset tasks"""
        while self.running:
            try:
                # Wait until midnight
                now = datetime.now()
                midnight = datetime.combine(now.date(), time(0, 0))
                if now >= midnight:
                    midnight = datetime.combine(
                        now.date() + timedelta(days=1),
                        time(0, 0)
                    )

                sleep_seconds = (midnight - now).total_seconds()
                await asyncio.sleep(sleep_seconds)

                # Reset daily stats
                logger.info("🌅 Performing daily reset...")
                self.arbitrage_engine.reset_daily_stats()

                # Rediscover markets
                await self.discover_markets()

            except Exception as e:
                logger.error(f"Error in daily reset: {e}")
                await asyncio.sleep(3600)  # Try again in an hour

    async def websocket_watchdog(self):
        """Monitor WebSocket health and restart if needed"""
        logger.info("🔍 WebSocket watchdog started")

        check_interval = 60  # Check every minute
        last_price_count = 0
        stale_count = 0

        while self.running:
            try:
                await asyncio.sleep(check_interval)

                if not self.ws_manager:
                    continue

                # Check if we're receiving price updates
                current_price_count = len(self.price_store.get_all())

                # If price count hasn't changed in 5 checks, WebSocket might be stale
                if current_price_count == last_price_count and current_price_count == 0:
                    stale_count += 1
                    logger.warning(f"⚠️ WebSocket appears stale (no price data) - stale count: {stale_count}/5")

                    if stale_count >= 5:
                        logger.error("❌ WebSocket appears dead - attempting restart...")
                        try:
                            # Stop current WebSocket
                            await self.ws_manager.stop()
                            await asyncio.sleep(5)

                            # Restart WebSocket streams
                            await self.start_websocket_streams()
                            stale_count = 0
                            logger.info("✅ WebSocket restarted successfully")
                        except Exception as e:
                            logger.error(f"❌ Failed to restart WebSocket: {e}")
                            logger.info("   Bot will continue without live prices")
                else:
                    stale_count = 0

                last_price_count = current_price_count

            except Exception as e:
                logger.error(f"Error in WebSocket watchdog: {e}")
                await asyncio.sleep(60)

    async def run(self):
        """Main run loop with resilient startup and recovery"""
        self.running = True
        self.start_time = datetime.now()

        logger.info("\n" + "="*60)
        logger.info("🤖 ARBITRAGE TRADING BOT STARTED")
        logger.info("="*60 + "\n")

        # Retry initialization up to 5 times
        init_retries = 5
        for attempt in range(init_retries):
            try:
                # Initialize components
                if await self.initialize():
                    logger.info("✅ Initialization successful")
                    break
                else:
                    logger.warning(f"⚠️ Initialization failed (attempt {attempt + 1}/{init_retries})")
                    if attempt < init_retries - 1:
                        await asyncio.sleep(10 * (attempt + 1))  # Exponential backoff
            except Exception as e:
                logger.error(f"❌ Initialization error (attempt {attempt + 1}/{init_retries}): {e}")
                if attempt < init_retries - 1:
                    await asyncio.sleep(10 * (attempt + 1))
        else:
            logger.error("Failed to initialize after 5 attempts - exiting")
            return

        # Retry market discovery up to 3 times
        discovery_retries = 3
        for attempt in range(discovery_retries):
            try:
                if await self.discover_markets():
                    logger.info("✅ Market discovery successful")
                    break
                else:
                    logger.warning(f"⚠️ Market discovery failed (attempt {attempt + 1}/{discovery_retries})")
                    if attempt < discovery_retries - 1:
                        await asyncio.sleep(5 * (attempt + 1))
            except Exception as e:
                logger.error(f"❌ Market discovery error (attempt {attempt + 1}/{discovery_retries}): {e}")
                if attempt < discovery_retries - 1:
                    await asyncio.sleep(5 * (attempt + 1))
        else:
            logger.error("Failed to discover markets after 3 attempts - exiting")
            return

        # Start WebSocket streams (non-fatal if fails - bot can still do intra-platform arb)
        try:
            if not await self.start_websocket_streams():
                logger.warning("⚠️ WebSocket streams failed to start - continuing without live prices")
                logger.info("   Bot will operate using API polling only")
        except Exception as e:
            logger.error(f"❌ WebSocket startup error: {e} - continuing without live prices")

        try:
            # Start background tasks
            logger.info("🚀 Starting main arbitrage loop...")
            tasks = [
                asyncio.create_task(self.arbitrage_loop()),
                asyncio.create_task(self.daily_reset()),
                asyncio.create_task(self.websocket_watchdog()),  # New watchdog task
            ]

            # Wait for tasks (if any task crashes, others continue)
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log any task failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Task {i} failed with error: {result}")

        except Exception as e:
            logger.error(f"Error in main run loop: {e}")

        finally:
            await self.shutdown()

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("\n🛑 Shutting down arbitrage bot...")

        self.running = False

        try:
            # Stop WebSocket streams
            if self.ws_manager:
                await self.ws_manager.stop()

            # Close trading clients
            if self.kalshi_trader:
                await self.kalshi_trader.__aexit__(None, None, None)

            if self.polymarket_trader:
                await self.polymarket_trader.__aexit__(None, None, None)

            # Close market discovery
            if self.market_discovery:
                await self.market_discovery.__aexit__(None, None, None)

            # Print final stats
            logger.info("\n📈 Final Statistics:")
            self.print_status()

            logger.info("✅ Shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global supervisor instance for signal handling
supervisor: Optional[ArbitrageBotSupervisor] = None


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"\nReceived signal {signum}")
    if supervisor:
        supervisor.running = False


async def main():
    """Main entry point"""
    global supervisor

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run supervisor
    supervisor = ArbitrageBotSupervisor()

    try:
        await supervisor.run()
    except KeyboardInterrupt:
        logger.info("\nKeyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        if supervisor:
            await supervisor.shutdown()


if __name__ == '__main__':
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nExiting...")
