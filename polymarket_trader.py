"""
Polymarket Trade Execution Module
Handles order placement using py-clob-client SDK
"""

import os
import logging
from typing import Dict, Optional
from decimal import Decimal
from dotenv import load_dotenv

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs, OrderType
    from py_clob_client.constants import POLYGON
except ImportError:
    logging.warning("py-clob-client not installed. Install with: pip install py-clob-client")
    ClobClient = None

load_dotenv()

logger = logging.getLogger(__name__)


class PolymarketTrader:
    """Handles Polymarket trading operations using py-clob-client"""

    def __init__(self):
        self.api_url = os.getenv('POLYMARKET_API_URL', 'https://clob.polymarket.com')
        self.private_key = os.getenv('POLYMARKET_PRIVATE_KEY')
        self.chain_id = int(os.getenv('POLYMARKET_CHAIN_ID', '137'))  # Polygon mainnet

        self.client: Optional[ClobClient] = None
        self.initialized = False

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Cleanup if needed
        pass

    async def initialize(self) -> bool:
        """
        Initialize Polymarket CLOB client with authentication

        Returns:
            True if initialization successful
        """
        if ClobClient is None:
            logger.error("py-clob-client not available")
            return False

        try:
            if not self.private_key:
                logger.error("Polymarket private key not configured")
                return False

            # Remove '0x' prefix if present
            private_key = self.private_key
            if private_key.startswith('0x'):
                private_key = private_key[2:]

            # Initialize CLOB client
            # signature_type=0 for EOA (Externally Owned Account)
            self.client = ClobClient(
                host=self.api_url,
                key=private_key,
                chain_id=self.chain_id,
                signature_type=0  # EOA signature
            )

            # Derive API credentials
            logger.info("Deriving Polymarket API credentials...")
            self.client.set_api_creds(self.client.create_or_derive_api_creds())

            self.initialized = True
            logger.info("Successfully initialized Polymarket trader")

            return True

        except Exception as e:
            logger.error(f"Error initializing Polymarket client: {e}")
            return False

    async def get_balance(self) -> Dict:
        """Get account balance"""
        if not self.initialized or not self.client:
            logger.error("Client not initialized")
            return {}

        try:
            # Get allowance and balance
            allowance = self.client.get_allowance()
            balance = self.client.get_balance()

            logger.info(f"Polymarket balance: ${balance} (allowance: ${allowance})")

            return {
                'balance': balance,
                'allowance': allowance
            }

        except Exception as e:
            logger.error(f"Error getting Polymarket balance: {e}")
            return {}

    async def place_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str,  # 'BUY' or 'SELL'
        order_type: str = 'GTC',  # Good-Til-Cancelled
        neg_risk: bool = False  # NegRisk flag for special markets
    ) -> Dict:
        """
        Place an order on Polymarket

        Args:
            token_id: Token ID for the outcome (from market discovery)
            price: Price per contract (0-1)
            size: Number of contracts
            side: 'BUY' or 'SELL'
            order_type: Order type (default: GTC)
            neg_risk: Set to True for NegRisk markets (check market.neg_risk flag)

        Returns:
            Order response data
        """
        if not self.initialized or not self.client:
            logger.error("Client not initialized")
            return {'success': False, 'error': 'Client not initialized'}

        try:
            # Validate token_id is provided
            if not token_id:
                return {
                    'success': False,
                    'error': 'token_id is required for CLOB trading'
                }

            # Validate price (must be between 0 and 1)
            if not 0 < price < 1:
                return {
                    'success': False,
                    'error': f'Invalid price: {price}. Must be between 0 and 1'
                }

            logger.info(f"Placing Polymarket order: {side} {size} contracts @ ${price} (token: {token_id[:8]}...)")

            # Create order arguments
            # Note: OrderArgs automatically handles NegRisk markets via the client
            order_args = OrderArgs(
                price=price,
                size=size,
                side=side.upper(),
                token_id=token_id
            )

            if neg_risk:
                logger.debug(f"NegRisk market detected for token {token_id[:8]}...")

            # Place order
            if order_type.upper() == 'GTC':
                order_response = self.client.create_order(order_args)
            else:
                # Can implement other order types (FOK, etc.) here
                order_response = self.client.create_order(order_args)

            if order_response:
                logger.info(f"Order placed successfully: {order_response.get('orderID')}")

                return {
                    'success': True,
                    'order_id': order_response.get('orderID'),
                    'status': order_response.get('status'),
                    'data': order_response
                }
            else:
                logger.error("Order placement failed - no response")
                return {
                    'success': False,
                    'error': 'No response from API'
                }

        except Exception as e:
            logger.error(f"Error placing Polymarket order: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def buy(self, token_id: str, size: float, price: float, neg_risk: bool = False) -> Dict:
        """Buy contracts"""
        return await self.place_order(token_id, price, size, 'BUY', neg_risk=neg_risk)

    async def sell(self, token_id: str, size: float, price: float, neg_risk: bool = False) -> Dict:
        """Sell contracts"""
        return await self.place_order(token_id, price, size, 'SELL', neg_risk=neg_risk)

    async def get_order_status(self, order_id: str) -> Dict:
        """Get status of an order"""
        if not self.initialized or not self.client:
            logger.error("Client not initialized")
            return {}

        try:
            order = self.client.get_order(order_id)
            return order if order else {}

        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {}

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order"""
        if not self.initialized or not self.client:
            logger.error("Client not initialized")
            return False

        try:
            result = self.client.cancel(order_id)
            if result:
                logger.info(f"Order {order_id} cancelled successfully")
                return True
            else:
                logger.error(f"Failed to cancel order {order_id}")
                return False

        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False

    async def cancel_all_orders(self) -> bool:
        """Cancel all open orders"""
        if not self.initialized or not self.client:
            logger.error("Client not initialized")
            return False

        try:
            result = self.client.cancel_all()
            logger.info("Cancelled all orders")
            return True

        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return False

    async def get_open_orders(self) -> list:
        """Get all open orders"""
        if not self.initialized or not self.client:
            logger.error("Client not initialized")
            return []

        try:
            orders = self.client.get_orders()
            return orders if orders else []

        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []

    async def get_positions(self) -> Dict:
        """Get current positions"""
        if not self.initialized or not self.client:
            logger.error("Client not initialized")
            return {}

        try:
            # Get positions (if available in API)
            # This may need to be implemented based on Polymarket's API
            logger.info("Fetching Polymarket positions")

            # Get open orders as a proxy
            orders = await self.get_open_orders()

            return {
                'open_orders': len(orders),
                'orders': orders
            }

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {}

    async def get_orderbook(self, token_id: str) -> Dict:
        """
        Get orderbook for a token

        Args:
            token_id: Token ID

        Returns:
            Orderbook data with bids and asks
        """
        if not self.initialized or not self.client:
            logger.error("Client not initialized")
            return {}

        try:
            orderbook = self.client.get_order_book(token_id)

            if orderbook:
                # Parse orderbook
                bids = orderbook.get('bids', [])
                asks = orderbook.get('asks', [])

                best_bid = float(bids[0]['price']) if bids else 0
                best_ask = float(asks[0]['price']) if asks else 0

                return {
                    'token_id': token_id,
                    'best_bid': best_bid,
                    'best_ask': best_ask,
                    'bids': bids,
                    'asks': asks,
                    'spread': best_ask - best_bid if best_ask and best_bid else 0
                }

            return {}

        except Exception as e:
            logger.error(f"Error getting orderbook: {e}")
            return {}

    async def get_market_price(self, token_id: str) -> Optional[float]:
        """Get current market price (mid-point)"""
        orderbook = await self.get_orderbook(token_id)

        if orderbook:
            best_bid = orderbook.get('best_bid', 0)
            best_ask = orderbook.get('best_ask', 0)

            if best_bid and best_ask:
                return (best_bid + best_ask) / 2

        return None


async def main():
    """Example usage"""
    logging.basicConfig(level=logging.INFO)

    async with PolymarketTrader() as trader:
        # Get balance
        balance = await trader.get_balance()
        print(f"Balance: {balance}")

        # Get positions
        positions = await trader.get_positions()
        print(f"Positions: {positions}")

        # Example: Get orderbook (commented out - need valid token ID)
        # orderbook = await trader.get_orderbook('TOKEN_ID_HERE')
        # print(f"Orderbook: {orderbook}")

        # Example: Place order (commented out for safety)
        # result = await trader.buy('TOKEN_ID', 10, 0.55)
        # print(f"Order result: {result}")


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
