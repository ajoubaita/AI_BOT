"""
Kalshi Trade Execution Module
Handles authentication and order placement for Kalshi API
"""

import os
import time
import uuid
import logging
import base64
import hashlib
from typing import Dict, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import aiohttp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class KalshiTrader:
    """Handles Kalshi API authentication and trading operations"""

    def __init__(self):
        self.base_url = os.getenv('KALSHI_API_BASE', 'https://api.elections.kalshi.com/trade-api/v2')
        self.api_key = os.getenv('KALSHI_API_KEY')
        self.private_key_path = os.getenv('KALSHI_PRIVATE_KEY_PATH')
        self.email = os.getenv('KALSHI_EMAIL')
        self.password = os.getenv('KALSHI_PASSWORD')

        self.session: Optional[aiohttp.ClientSession] = None
        self.access_token: Optional[str] = None
        self.private_key = None

        # Load RSA private key if path is provided
        if self.private_key_path and os.path.exists(self.private_key_path):
            self._load_private_key()

    def _load_private_key(self):
        """Load RSA private key from file"""
        try:
            with open(self.private_key_path, 'rb') as key_file:
                self.private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None,
                    backend=default_backend()
                )
            logger.info("Loaded RSA private key for Kalshi authentication")
        except Exception as e:
            logger.error(f"Failed to load RSA private key: {e}")

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _generate_signature(self, method: str, path: str, body: str = "") -> str:
        """
        Generate RSA-PSS-SHA256 signature for Kalshi API request

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            body: Request body (JSON string)

        Returns:
            Base64-encoded signature
        """
        if not self.private_key:
            raise ValueError("Private key not loaded")

        # Create timestamp (milliseconds)
        timestamp = str(int(time.time() * 1000))

        # Create signature message: timestamp + method + path + body
        message = f"{timestamp}{method}{path}{body}"

        # Sign with RSA-PSS-SHA256
        signature = self.private_key.sign(
            message.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        # Base64 encode
        signature_b64 = base64.b64encode(signature).decode('utf-8')

        return signature_b64, timestamp

    def _get_auth_headers(self, method: str, path: str, body: str = "") -> Dict:
        """
        Generate authentication headers for Kalshi API

        Args:
            method: HTTP method
            path: API endpoint path
            body: Request body

        Returns:
            Headers dictionary
        """
        headers = {
            'Content-Type': 'application/json',
        }

        # If we have access token, use it
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'

        # If we have private key, add signature
        if self.private_key:
            signature, timestamp = self._generate_signature(method, path, body)
            headers['KALSHI-ACCESS-KEY'] = self.api_key
            headers['KALSHI-ACCESS-SIGNATURE'] = signature
            headers['KALSHI-ACCESS-TIMESTAMP'] = timestamp

        return headers

    async def authenticate(self) -> bool:
        """
        Authenticate with Kalshi API using email/password
        Falls back to API key if credentials not available

        Returns:
            True if authentication successful
        """
        try:
            # Try login with email/password
            if self.email and self.password:
                url = f"{self.base_url}/login"
                payload = {
                    'email': self.email,
                    'password': self.password
                }

                async with self.session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.access_token = data.get('token')
                        logger.info("Successfully authenticated with Kalshi")
                        return True
                    else:
                        logger.error(f"Kalshi authentication failed: {response.status}")

            # If we have API key and private key, we can use those for requests
            if self.api_key and self.private_key:
                logger.info("Using API key authentication for Kalshi")
                return True

            logger.warning("No valid Kalshi authentication method available")
            return False

        except Exception as e:
            logger.error(f"Error authenticating with Kalshi: {e}")
            return False

    async def get_balance(self) -> Dict:
        """Get account balance"""
        try:
            url = f"{self.base_url}/portfolio/balance"
            headers = self._get_auth_headers('GET', '/portfolio/balance')

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Kalshi balance: ${data.get('balance', 0) / 100:.2f}")
                    return data
                else:
                    logger.error(f"Failed to get balance: {response.status}")
                    return {}

        except Exception as e:
            logger.error(f"Error getting Kalshi balance: {e}")
            return {}

    async def place_order(
        self,
        ticker: str,
        action: str,  # 'buy' or 'sell'
        side: str,  # 'yes' or 'no'
        count: int,
        price: Optional[float] = None,  # None for market orders
        order_type: str = 'limit'  # 'limit' or 'market'
    ) -> Dict:
        """
        Place an order on Kalshi

        Args:
            ticker: Market ticker symbol
            action: 'buy' or 'sell'
            side: 'yes' or 'no'
            count: Number of contracts
            price: Limit price in dollars (None for market orders)
            order_type: 'limit' or 'market'

        Returns:
            Order response data
        """
        try:
            url = f"{self.base_url}/portfolio/orders"
            client_order_id = str(uuid.uuid4())

            # Build order payload
            payload = {
                'ticker': ticker,
                'action': action,
                'side': side,
                'count': count,
                'type': order_type,
                'client_order_id': client_order_id
            }

            # Add price for limit orders (convert to cents)
            if order_type == 'limit' and price is not None:
                if side == 'yes':
                    payload['yes_price'] = int(price * 100)
                else:
                    payload['no_price'] = int(price * 100)

            # Generate signature
            import json
            body = json.dumps(payload)
            headers = self._get_auth_headers('POST', '/portfolio/orders', body)

            logger.info(f"Placing Kalshi order: {action} {count} {ticker} {side} @ ${price}")

            async with self.session.post(url, json=payload, headers=headers) as response:
                response_data = await response.json()

                if response.status in [200, 201]:
                    order_id = response_data.get('order', {}).get('order_id')
                    logger.info(f"Order placed successfully: {order_id}")

                    return {
                        'success': True,
                        'order_id': order_id,
                        'client_order_id': client_order_id,
                        'status': response_data.get('order', {}).get('status'),
                        'data': response_data
                    }
                else:
                    logger.error(f"Order failed: {response.status} - {response_data}")
                    return {
                        'success': False,
                        'error': response_data.get('error', 'Unknown error'),
                        'status_code': response.status
                    }

        except Exception as e:
            logger.error(f"Error placing Kalshi order: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def buy_yes(self, ticker: str, count: int, price: Optional[float] = None) -> Dict:
        """Buy YES contracts"""
        return await self.place_order(ticker, 'buy', 'yes', count, price)

    async def buy_no(self, ticker: str, count: int, price: Optional[float] = None) -> Dict:
        """Buy NO contracts"""
        return await self.place_order(ticker, 'buy', 'no', count, price)

    async def sell_yes(self, ticker: str, count: int, price: Optional[float] = None) -> Dict:
        """Sell YES contracts"""
        return await self.place_order(ticker, 'sell', 'yes', count, price)

    async def sell_no(self, ticker: str, count: int, price: Optional[float] = None) -> Dict:
        """Sell NO contracts"""
        return await self.place_order(ticker, 'sell', 'no', count, price)

    async def get_order_status(self, order_id: str) -> Dict:
        """Get status of an order"""
        try:
            url = f"{self.base_url}/portfolio/orders/{order_id}"
            headers = self._get_auth_headers('GET', f'/portfolio/orders/{order_id}')

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get order status: {response.status}")
                    return {}

        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {}

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order"""
        try:
            url = f"{self.base_url}/portfolio/orders/{order_id}"
            headers = self._get_auth_headers('DELETE', f'/portfolio/orders/{order_id}')

            async with self.session.delete(url, headers=headers) as response:
                if response.status in [200, 204]:
                    logger.info(f"Order {order_id} cancelled successfully")
                    return True
                else:
                    logger.error(f"Failed to cancel order: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False

    async def get_positions(self) -> Dict:
        """Get current positions"""
        try:
            url = f"{self.base_url}/portfolio/positions"
            headers = self._get_auth_headers('GET', '/portfolio/positions')

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get positions: {response.status}")
                    return {}

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {}


async def main():
    """Example usage"""
    logging.basicConfig(level=logging.INFO)

    async with KalshiTrader() as trader:
        # Get balance
        balance = await trader.get_balance()
        print(f"Balance: {balance}")

        # Get positions
        positions = await trader.get_positions()
        print(f"Positions: {positions}")

        # Example: Place a limit order (commented out for safety)
        # result = await trader.buy_yes('TICKER-23', 1, 0.55)
        # print(f"Order result: {result}")


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
