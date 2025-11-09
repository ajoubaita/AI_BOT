"""
Market Discovery Module
Fetches and normalizes market data from Kalshi and Polymarket APIs
"""

import os
import logging
import asyncio
from typing import List, Dict, Optional
import aiohttp
from dotenv import load_dotenv
from market_discovery_polymarket import PolymarketMarketDiscovery

load_dotenv()

logger = logging.getLogger(__name__)


class MarketDiscovery:
    """Discovers and normalizes markets from Kalshi and Polymarket"""

    def __init__(self):
        self.kalshi_base_url = os.getenv('KALSHI_API_BASE', 'https://api.elections.kalshi.com/trade-api/v2')
        self.polymarket_gamma_url = os.getenv('POLYMARKET_GAMMA_URL', 'https://gamma-api.polymarket.com')
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_kalshi_markets(self) -> List[Dict]:
        """
        Fetch all open markets from Kalshi API with pagination

        Returns:
            List of normalized market dictionaries
        """
        markets = []
        cursor = None
        limit = 100  # Max allowed by Kalshi

        try:
            while True:
                url = f"{self.kalshi_base_url}/markets"
                params = {
                    'limit': limit,
                    'status': 'open'
                }
                if cursor:
                    params['cursor'] = cursor

                logger.info(f"Fetching Kalshi markets (cursor: {cursor})")

                async with self.session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Kalshi API error: {response.status}")
                        break

                    data = await response.json()

                    if 'markets' not in data:
                        break

                    batch = data['markets']

                    # Normalize each market
                    for market in batch:
                        try:
                            normalized = self._normalize_kalshi_market(market)
                            if normalized:
                                markets.append(normalized)
                        except Exception as e:
                            logger.warning(f"Error normalizing Kalshi market: {e}")

                    # Check for next page
                    cursor = data.get('cursor')
                    if not cursor or len(batch) < limit:
                        break

            logger.info(f"Fetched {len(markets)} Kalshi markets")
            return markets

        except Exception as e:
            logger.error(f"Error fetching Kalshi markets: {e}")
            return markets

    def _normalize_kalshi_market(self, market: Dict) -> Optional[Dict]:
        """Normalize Kalshi market to standard schema"""
        try:
            # Extract yes/no prices (convert cents to dollars)
            yes_price = market.get('yes_bid', 0) / 100.0
            no_price = market.get('no_bid', 0) / 100.0

            # If bid prices aren't available, try ask prices
            if yes_price == 0:
                yes_price = market.get('yes_ask', 0) / 100.0
            if no_price == 0:
                no_price = market.get('no_ask', 0) / 100.0

            return {
                'platform': 'kalshi',
                'market_id': market.get('ticker', ''),
                'title': market.get('title', ''),
                'yes_price': yes_price,
                'no_price': no_price,
                'volume': market.get('volume', 0),
                'ticker_or_token_id': market.get('ticker', ''),
                'yes_ask': market.get('yes_ask', 0) / 100.0,
                'yes_bid': market.get('yes_bid', 0) / 100.0,
                'no_ask': market.get('no_ask', 0) / 100.0,
                'no_bid': market.get('no_bid', 0) / 100.0,
                'raw_data': market
            }
        except Exception as e:
            logger.warning(f"Error normalizing Kalshi market: {e}")
            return None

    async def fetch_polymarket_markets_legacy(self) -> List[Dict]:
        """
        Fetch all open markets from Polymarket Gamma API with pagination

        Returns:
            List of normalized market dictionaries
        """
        markets = []
        offset = 0
        limit = 100

        try:
            while True:
                url = f"{self.polymarket_gamma_url}/events"
                params = {
                    'closed': 'false',
                    'limit': limit,
                    'offset': offset
                }

                logger.info(f"Fetching Polymarket markets (offset: {offset})")

                async with self.session.get(url, params=params, timeout=30) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Polymarket API error: {response.status} - {error_text[:200]}")
                        logger.error(f"Request URL: {url}")
                        logger.error(f"Request params: {params}")
                        break

                    try:
                        data = await response.json()
                    except Exception as json_error:
                        response_text = await response.text()
                        logger.error(f"Failed to parse Polymarket JSON: {json_error}")
                        logger.error(f"Response text (first 500 chars): {response_text[:500]}")
                        break

                    # Check if data is valid
                    if data is None:
                        logger.warning("Polymarket returned null/empty response")
                        break

                    if not isinstance(data, list):
                        # Try to handle if it's wrapped in an object
                        if isinstance(data, dict):
                            logger.info(f"Polymarket response is dict with keys: {list(data.keys())}")
                            # Try common wrapper keys
                            if 'data' in data:
                                data = data['data']
                            elif 'events' in data:
                                data = data['events']
                            elif 'results' in data:
                                data = data['results']
                            else:
                                logger.warning(f"Polymarket returned dict but no known wrapper key: {list(data.keys())}")
                                break

                    if not isinstance(data, list):
                        logger.warning(f"Polymarket returned unexpected data format: {type(data)}")
                        break

                    if len(data) == 0:
                        logger.info("Polymarket returned empty list (no more markets)")
                        break

                    # Normalize each event and its markets
                    for event in data:
                        try:
                            event_markets = self._normalize_polymarket_event(event)
                            markets.extend(event_markets)
                        except Exception as e:
                            logger.warning(f"Error normalizing Polymarket event: {e}")

                    # Check if we got fewer results than requested (last page)
                    if len(data) < limit:
                        break

                    offset += limit

            logger.info(f"Fetched {len(markets)} Polymarket markets")
            return markets

        except Exception as e:
            logger.error(f"Error fetching Polymarket markets: {e}")
            return markets

    def _normalize_polymarket_event(self, event: Dict) -> List[Dict]:
        """
        Normalize Polymarket event to standard schema
        Each event can have multiple markets (binary outcomes)
        """
        normalized_markets = []

        try:
            markets = event.get('markets', [])

            for market in markets:
                # Polymarket uses token IDs for outcomes
                # Usually has "Yes" and "No" tokens
                outcomes = market.get('outcomes', [])

                # For binary markets, find Yes and No tokens
                yes_token = None
                no_token = None

                for outcome in outcomes:
                    outcome_name = outcome.get('outcome', '').lower()
                    if 'yes' in outcome_name:
                        yes_token = outcome
                    elif 'no' in outcome_name:
                        no_token = outcome

                if yes_token:
                    # Get best bid/ask from orderbook
                    yes_price = float(yes_token.get('price', 0))

                    # Calculate no price (complement)
                    no_price = 1.0 - yes_price if yes_token else 0.0

                    normalized = {
                        'platform': 'polymarket',
                        'market_id': market.get('id', ''),
                        'title': f"{event.get('title', '')} - {market.get('question', '')}",
                        'yes_price': yes_price,
                        'no_price': no_price,
                        'volume': float(market.get('volume', 0)),
                        'ticker_or_token_id': yes_token.get('token_id', ''),
                        'yes_token_id': yes_token.get('token_id', ''),
                        'no_token_id': no_token.get('token_id', '') if no_token else '',
                        'condition_id': market.get('condition_id', ''),
                        'raw_data': market
                    }
                    normalized_markets.append(normalized)

        except Exception as e:
            logger.warning(f"Error normalizing Polymarket event: {e}")

        return normalized_markets

    async def fetch_polymarket_markets(self) -> List[Dict]:
        """
        Fetch Polymarket markets using the robust Gamma API implementation

        Returns:
            List of normalized market dictionaries with token IDs
        """
        try:
            async with PolymarketMarketDiscovery() as poly_discovery:
                # Run health check first
                healthy = await poly_discovery.health_check()
                if not healthy:
                    logger.error("Polymarket health check failed")
                    return []

                # Fetch markets
                markets = await poly_discovery.fetch_markets()
                return markets

        except Exception as e:
            logger.error(f"Error in Polymarket discovery: {e}")
            return []

    async def discover_all_markets(self) -> List[Dict]:
        """
        Fetch markets from both platforms concurrently

        Returns:
            Combined list of normalized markets
        """
        logger.info("Starting market discovery across both platforms")

        # Fetch from both platforms concurrently
        kalshi_task = asyncio.create_task(self.fetch_kalshi_markets())
        polymarket_task = asyncio.create_task(self.fetch_polymarket_markets())

        kalshi_markets, polymarket_markets = await asyncio.gather(
            kalshi_task,
            polymarket_task,
            return_exceptions=True
        )

        # Handle exceptions
        if isinstance(kalshi_markets, Exception):
            logger.error(f"Kalshi fetch failed: {kalshi_markets}")
            kalshi_markets = []

        if isinstance(polymarket_markets, Exception):
            logger.error(f"Polymarket fetch failed: {polymarket_markets}")
            polymarket_markets = []

        # Log detailed results
        logger.info(f"Kalshi markets: {len(kalshi_markets)}")
        logger.info(f"Polymarket markets: {len(polymarket_markets)}")

        if len(polymarket_markets) == 0:
            logger.warning("⚠️ Polymarket returned 0 markets - API may be down or changed")
            logger.warning("   Bot will continue with Kalshi intra-platform arbitrage only")

        all_markets = kalshi_markets + polymarket_markets
        logger.info(f"Total markets discovered: {len(all_markets)}")

        return all_markets

    def find_matching_markets(self, markets: List[Dict], similarity_threshold: float = 0.7) -> List[Dict]:
        """
        Find potentially matching markets across platforms for arbitrage
        Uses simple keyword matching (can be enhanced with ML)

        Args:
            markets: List of all markets
            similarity_threshold: Minimum similarity score for matching

        Returns:
            List of market pairs with their similarity scores
        """
        kalshi_markets = [m for m in markets if m['platform'] == 'kalshi']
        polymarket_markets = [m for m in markets if m['platform'] == 'polymarket']

        matches = []

        for k_market in kalshi_markets:
            for p_market in polymarket_markets:
                similarity = self._calculate_title_similarity(
                    k_market['title'],
                    p_market['title']
                )

                if similarity >= similarity_threshold:
                    matches.append({
                        'kalshi_market': k_market,
                        'polymarket_market': p_market,
                        'similarity': similarity
                    })

        logger.info(f"Found {len(matches)} matching market pairs")
        return sorted(matches, key=lambda x: x['similarity'], reverse=True)

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two market titles
        Simple keyword-based approach (can be enhanced)
        """
        # Convert to lowercase and split into words
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        # Remove common stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        words1 = words1 - stopwords
        words2 = words2 - stopwords

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0


async def main():
    """Example usage"""
    logging.basicConfig(level=logging.INFO)

    async with MarketDiscovery() as discovery:
        markets = await discovery.discover_all_markets()

        print(f"\nDiscovered {len(markets)} total markets:")
        print(f"  Kalshi: {len([m for m in markets if m['platform'] == 'kalshi'])}")
        print(f"  Polymarket: {len([m for m in markets if m['platform'] == 'polymarket'])}")

        # Find matching markets
        matches = discovery.find_matching_markets(markets)
        print(f"\nFound {len(matches)} potential arbitrage pairs")

        # Show top 5 matches
        for i, match in enumerate(matches[:5]):
            print(f"\n{i+1}. Similarity: {match['similarity']:.2f}")
            print(f"   Kalshi: {match['kalshi_market']['title']}")
            print(f"   Polymarket: {match['polymarket_market']['title']}")


if __name__ == '__main__':
    asyncio.run(main())
