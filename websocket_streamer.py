"""
WebSocket Streaming Module
Maintains live order books from Kalshi and Polymarket via WebSocket streams
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Callable
from threading import Lock
import websockets
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class PriceStore:
    """Thread-safe in-memory store for live prices"""

    def __init__(self):
        self.prices: Dict[tuple, Dict] = {}  # Key: (platform, market_id)
        self.lock = Lock()

    def update(self, platform: str, market_id: str, data: Dict):
        """Update price data for a market"""
        with self.lock:
            key = (platform, market_id)
            self.prices[key] = {
                **data,
                'platform': platform,
                'market_id': market_id
            }

    def get(self, platform: str, market_id: str) -> Optional[Dict]:
        """Get price data for a market"""
        with self.lock:
            return self.prices.get((platform, market_id))

    def get_all(self) -> Dict:
        """Get all price data"""
        with self.lock:
            return dict(self.prices)

    def clear(self):
        """Clear all price data"""
        with self.lock:
            self.prices.clear()


class KalshiWebSocketStreamer:
    """Handles Kalshi WebSocket connection and orderbook updates"""

    def __init__(self, price_store: PriceStore, tickers: List[str]):
        self.ws_url = os.getenv('KALSHI_WS_URL', 'wss://api.elections.kalshi.com/trade-api/ws/v2')
        self.price_store = price_store
        self.tickers = tickers
        self.websocket = None
        self.running = False

    async def connect(self):
        """Connect to Kalshi WebSocket"""
        try:
            logger.info("Connecting to Kalshi WebSocket...")
            self.websocket = await websockets.connect(self.ws_url)
            logger.info("Connected to Kalshi WebSocket")
            self.running = True

            # Subscribe to markets
            await self.subscribe()

            return True

        except Exception as e:
            logger.error(f"Error connecting to Kalshi WebSocket: {e}")
            return False

    async def subscribe(self):
        """Subscribe to orderbook and ticker updates"""
        if not self.websocket:
            return

        try:
            # Subscribe to orderbook deltas
            for ticker in self.tickers:
                subscribe_msg = {
                    'id': 1,
                    'cmd': 'subscribe',
                    'params': {
                        'channels': ['orderbook_delta', 'ticker'],
                        'market_ticker': ticker
                    }
                }
                await self.websocket.send(json.dumps(subscribe_msg))
                logger.info(f"Subscribed to Kalshi market: {ticker}")

        except Exception as e:
            logger.error(f"Error subscribing to Kalshi markets: {e}")

    async def listen(self):
        """Listen for WebSocket messages and update price store"""
        if not self.websocket:
            return

        try:
            while self.running:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=30.0
                    )
                    await self.handle_message(message)

                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await self.websocket.ping()

        except websockets.exceptions.ConnectionClosed:
            logger.warning("Kalshi WebSocket connection closed")
            self.running = False

        except Exception as e:
            logger.error(f"Error in Kalshi WebSocket listener: {e}")
            self.running = False

    async def handle_message(self, message: str):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)

            msg_type = data.get('type')

            if msg_type == 'orderbook_delta':
                await self.handle_orderbook_update(data)
            elif msg_type == 'ticker':
                await self.handle_ticker_update(data)

        except Exception as e:
            logger.error(f"Error handling Kalshi message: {e}")

    async def handle_orderbook_update(self, data: Dict):
        """Process orderbook delta update"""
        try:
            ticker = data.get('msg', {}).get('market_ticker')
            if not ticker:
                return

            # Extract best bid/ask from orderbook
            yes_bids = data.get('msg', {}).get('yes', {}).get('bids', [])
            yes_asks = data.get('msg', {}).get('yes', {}).get('asks', [])
            no_bids = data.get('msg', {}).get('no', {}).get('bids', [])
            no_asks = data.get('msg', {}).get('no', {}).get('asks', [])

            price_data = {
                'yes_bid': float(yes_bids[0][0]) / 100 if yes_bids else 0,
                'yes_ask': float(yes_asks[0][0]) / 100 if yes_asks else 0,
                'no_bid': float(no_bids[0][0]) / 100 if no_bids else 0,
                'no_ask': float(no_asks[0][0]) / 100 if no_asks else 0,
                'timestamp': data.get('msg', {}).get('ts', 0)
            }

            self.price_store.update('kalshi', ticker, price_data)

        except Exception as e:
            logger.error(f"Error processing Kalshi orderbook update: {e}")

    async def handle_ticker_update(self, data: Dict):
        """Process ticker update"""
        try:
            ticker = data.get('msg', {}).get('market_ticker')
            if not ticker:
                return

            price_data = {
                'yes_price': float(data.get('msg', {}).get('yes_price', 0)) / 100,
                'no_price': float(data.get('msg', {}).get('no_price', 0)) / 100,
                'volume': data.get('msg', {}).get('volume', 0),
                'timestamp': data.get('msg', {}).get('ts', 0)
            }

            # Update existing data or create new entry
            existing = self.price_store.get('kalshi', ticker)
            if existing:
                price_data = {**existing, **price_data}

            self.price_store.update('kalshi', ticker, price_data)

        except Exception as e:
            logger.error(f"Error processing Kalshi ticker update: {e}")

    async def close(self):
        """Close WebSocket connection"""
        self.running = False
        if self.websocket:
            await self.websocket.close()


class PolymarketWebSocketStreamer:
    """Handles Polymarket WebSocket connection and market updates"""

    def __init__(self, price_store: PriceStore, token_ids: List[str]):
        self.ws_url = os.getenv('POLYMARKET_WS_URL', 'wss://ws-subscriptions-clob.polymarket.com/ws/market')
        self.price_store = price_store
        self.token_ids = token_ids
        self.websocket = None
        self.running = False
        self.ping_task = None

    async def connect(self):
        """Connect to Polymarket WebSocket"""
        try:
            logger.info("Connecting to Polymarket WebSocket...")
            self.websocket = await websockets.connect(self.ws_url)
            logger.info("Connected to Polymarket WebSocket")
            self.running = True

            # Subscribe to markets
            await self.subscribe()

            # Start ping task
            self.ping_task = asyncio.create_task(self.ping_loop())

            return True

        except Exception as e:
            logger.error(f"Error connecting to Polymarket WebSocket: {e}")
            return False

    async def subscribe(self):
        """Subscribe to market updates for token IDs"""
        if not self.websocket:
            return

        try:
            for token_id in self.token_ids:
                subscribe_msg = {
                    'type': 'subscribe',
                    'channel': 'market',
                    'market': token_id
                }
                await self.websocket.send(json.dumps(subscribe_msg))
                logger.info(f"Subscribed to Polymarket token: {token_id}")

        except Exception as e:
            logger.error(f"Error subscribing to Polymarket markets: {e}")

    async def ping_loop(self):
        """Send PING messages every 10 seconds to keep connection alive"""
        while self.running:
            try:
                await asyncio.sleep(10)
                if self.websocket and self.running:
                    ping_msg = {'type': 'PING'}
                    await self.websocket.send(json.dumps(ping_msg))
            except Exception as e:
                logger.error(f"Error sending ping: {e}")

    async def listen(self):
        """Listen for WebSocket messages and update price store"""
        if not self.websocket:
            return

        try:
            while self.running:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=30.0
                    )
                    await self.handle_message(message)

                except asyncio.TimeoutError:
                    logger.warning("Polymarket WebSocket timeout - connection may be stale")

        except websockets.exceptions.ConnectionClosed:
            logger.warning("Polymarket WebSocket connection closed")
            self.running = False

        except Exception as e:
            logger.error(f"Error in Polymarket WebSocket listener: {e}")
            self.running = False

    async def handle_message(self, message: str):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)

            msg_type = data.get('type')

            if msg_type == 'PONG':
                # Response to PING
                return

            elif msg_type == 'market':
                await self.handle_market_update(data)

            elif msg_type == 'book':
                await self.handle_orderbook_update(data)

        except Exception as e:
            logger.error(f"Error handling Polymarket message: {e}")

    async def handle_market_update(self, data: Dict):
        """Process market update"""
        try:
            market_data = data.get('data', {})
            token_id = market_data.get('asset_id')

            if not token_id:
                return

            price_data = {
                'price': float(market_data.get('price', 0)),
                'best_bid': float(market_data.get('best_bid', 0)),
                'best_ask': float(market_data.get('best_ask', 0)),
                'timestamp': market_data.get('timestamp', 0)
            }

            self.price_store.update('polymarket', token_id, price_data)

        except Exception as e:
            logger.error(f"Error processing Polymarket market update: {e}")

    async def handle_orderbook_update(self, data: Dict):
        """Process orderbook update"""
        try:
            book_data = data.get('data', {})
            token_id = book_data.get('asset_id')

            if not token_id:
                return

            bids = book_data.get('bids', [])
            asks = book_data.get('asks', [])

            price_data = {
                'best_bid': float(bids[0]['price']) if bids else 0,
                'best_ask': float(asks[0]['price']) if asks else 0,
                'bid_size': float(bids[0]['size']) if bids else 0,
                'ask_size': float(asks[0]['size']) if asks else 0,
                'timestamp': book_data.get('timestamp', 0)
            }

            # Update existing data
            existing = self.price_store.get('polymarket', token_id)
            if existing:
                price_data = {**existing, **price_data}

            self.price_store.update('polymarket', token_id, price_data)

        except Exception as e:
            logger.error(f"Error processing Polymarket orderbook update: {e}")

    async def close(self):
        """Close WebSocket connection"""
        self.running = False
        if self.ping_task:
            self.ping_task.cancel()
        if self.websocket:
            await self.websocket.close()


class WebSocketManager:
    """Manages WebSocket connections for both platforms"""

    def __init__(self, price_store: PriceStore):
        self.price_store = price_store
        self.kalshi_streamer: Optional[KalshiWebSocketStreamer] = None
        self.polymarket_streamer: Optional[PolymarketWebSocketStreamer] = None
        self.running = False

    async def start(self, kalshi_tickers: List[str], polymarket_tokens: List[str]):
        """Start WebSocket connections for both platforms"""
        self.running = True

        # Initialize streamers
        self.kalshi_streamer = KalshiWebSocketStreamer(self.price_store, kalshi_tickers)
        self.polymarket_streamer = PolymarketWebSocketStreamer(self.price_store, polymarket_tokens)

        # Connect to both platforms
        tasks = []

        if kalshi_tickers:
            tasks.append(self.run_kalshi())

        if polymarket_tokens:
            tasks.append(self.run_polymarket())

        # Run both streamers concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

    async def run_kalshi(self):
        """Run Kalshi streamer with reconnection logic"""
        while self.running:
            try:
                if await self.kalshi_streamer.connect():
                    await self.kalshi_streamer.listen()

                if self.running:
                    logger.info("Reconnecting to Kalshi WebSocket in 5 seconds...")
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in Kalshi streamer: {e}")
                await asyncio.sleep(5)

    async def run_polymarket(self):
        """Run Polymarket streamer with reconnection logic"""
        while self.running:
            try:
                if await self.polymarket_streamer.connect():
                    await self.polymarket_streamer.listen()

                if self.running:
                    logger.info("Reconnecting to Polymarket WebSocket in 5 seconds...")
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in Polymarket streamer: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        """Stop all WebSocket connections"""
        self.running = False

        if self.kalshi_streamer:
            await self.kalshi_streamer.close()

        if self.polymarket_streamer:
            await self.polymarket_streamer.close()


async def main():
    """Example usage"""
    logging.basicConfig(level=logging.INFO)

    price_store = PriceStore()

    # Example tickers/tokens
    kalshi_tickers = ['INXD-23DEC29-B4500']  # Example
    polymarket_tokens = ['TOKEN_ID_HERE']  # Example

    manager = WebSocketManager(price_store)

    try:
        # Start streaming
        stream_task = asyncio.create_task(
            manager.start(kalshi_tickers, polymarket_tokens)
        )

        # Monitor prices for 30 seconds
        for _ in range(30):
            await asyncio.sleep(1)
            prices = price_store.get_all()
            print(f"Live prices: {len(prices)} markets")

        # Stop streaming
        await manager.stop()

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await manager.stop()


if __name__ == '__main__':
    asyncio.run(main())
