"""
Polymarket Market Discovery via Gamma API
Implements robust market fetching with proper token ID extraction for CLOB trading
"""

import asyncio
import logging
from typing import List, Dict, Optional
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)


class PolymarketMarketDiscovery:
    """
    Discovers tradable markets from Polymarket Gamma API
    Extracts token IDs required for py-clob-client trading
    """

    def __init__(self):
        self.gamma_base_url = "https://gamma-api.polymarket.com"
        self.data_api_url = "https://data-api.polymarket.com"
        self.session: Optional[aiohttp.ClientSession] = None

        # Rate limiting
        self.max_retries = 3
        self.base_backoff = 1.0  # seconds

    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=30, connect=5)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        """Standard headers for all requests"""
        return {
            'User-Agent': 'arb-bot/1.0',
            'Accept': 'application/json'
        }

    async def _resilient_get(
        self,
        url: str,
        params: Optional[Dict] = None,
        timeout: int = 5
    ) -> Dict:
        """
        Resilient HTTP GET with retry logic

        Args:
            url: Target URL
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response

        Raises:
            Exception: On non-recoverable errors with status/body details
        """
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:

                    # Handle rate limiting and service errors with backoff
                    if response.status in [429, 503]:
                        backoff = self.base_backoff * (2 ** attempt)
                        logger.warning(
                            f"HTTP {response.status} from {url}, "
                            f"retrying in {backoff:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(backoff)
                        continue

                    # Success
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Successfully fetched {url}")
                        return data

                    # Non-recoverable error
                    error_body = await response.text()
                    error_msg = (
                        f"HTTP {response.status} from {url}\n"
                        f"Params: {params}\n"
                        f"Response (first 500 chars): {error_body[:500]}"
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg)

            except asyncio.TimeoutError:
                backoff = self.base_backoff * (2 ** attempt)
                logger.warning(
                    f"Timeout fetching {url}, "
                    f"retrying in {backoff:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(backoff)
                continue

            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to fetch {url} after {self.max_retries} attempts: {e}")
                    raise
                backoff = self.base_backoff * (2 ** attempt)
                await asyncio.sleep(backoff)

        raise Exception(f"Failed to fetch {url} after {self.max_retries} attempts")

    async def health_check(self) -> bool:
        """
        Preflight health check for Polymarket APIs

        Returns:
            True if both APIs are reachable and healthy
        """
        logger.info("Running Polymarket API health checks...")

        # Check 1: Gamma Events API
        try:
            events_url = f"{self.gamma_base_url}/events"
            params = {'limit': 1, 'closed': 'false'}

            data = await self._resilient_get(events_url, params, timeout=5)

            if isinstance(data, list) and len(data) > 0:
                first_event = data[0]
                event_title = first_event.get('title', 'Unknown')
                logger.info(f"✅ Gamma Events API healthy - Sample event: '{event_title}'")
            else:
                logger.warning(f"⚠️ Gamma Events API returned unexpected format: {type(data)}")
                return False

        except Exception as e:
            logger.error(f"❌ Gamma Events API health check failed: {e}")
            return False

        # Check 2: Data API
        try:
            data = await self._resilient_get(self.data_api_url, timeout=5)

            if isinstance(data, dict) and data.get('data') == 'OK':
                logger.info("✅ Data API healthy")
            else:
                logger.warning(f"⚠️ Data API returned unexpected response: {data}")
                return False

        except Exception as e:
            logger.error(f"❌ Data API health check failed: {e}")
            return False

        logger.info("✅ All Polymarket API health checks passed")
        return True

    async def fetch_markets(self) -> List[Dict]:
        """
        Fetch all tradable markets from Polymarket Gamma API

        Returns:
            List of normalized market dictionaries with token IDs
        """
        logger.info("Fetching Polymarket markets from Gamma API...")

        all_markets = []
        offset = 0
        limit = 100
        total_events = 0
        orderbook_enabled_events = 0

        try:
            while True:
                url = f"{self.gamma_base_url}/events"
                params = {
                    'order': 'id',
                    'ascending': 'false',
                    'closed': 'false',
                    'limit': limit,
                    'offset': offset
                }

                logger.debug(f"Fetching events at offset {offset}")

                data = await self._resilient_get(url, params)

                # Validate response format
                if not isinstance(data, list):
                    logger.error(f"Unexpected response format: {type(data)}, expected list")
                    break

                if len(data) == 0:
                    logger.info(f"No more events (offset {offset})")
                    break

                total_events += len(data)

                # Process each event
                for event in data:
                    # Filter: only events with orderbook enabled
                    if not event.get('enableOrderBook', False):
                        continue

                    orderbook_enabled_events += 1

                    # Extract markets from this event
                    markets = self._parse_event_markets(event)
                    all_markets.extend(markets)

                # Check for last page (short page indicates end)
                if len(data) < limit:
                    logger.info(f"Reached last page (got {len(data)} < {limit})")
                    break

                offset += limit

                # Rate limiting courtesy delay
                await asyncio.sleep(0.1)

            logger.info(
                f"Fetched {len(all_markets)} tradable markets from "
                f"{orderbook_enabled_events} orderbook-enabled events "
                f"(out of {total_events} total events)"
            )

            if len(all_markets) == 0:
                logger.error(
                    "⚠️ ZERO markets discovered! This is abnormal. "
                    "Check API endpoint, params, or filtering logic."
                )

            return all_markets

        except Exception as e:
            logger.error(f"Error fetching Polymarket markets: {e}")
            # Don't swallow the error - let caller know something went wrong
            raise

    def _parse_event_markets(self, event: Dict) -> List[Dict]:
        """
        Parse markets from a Gamma API event

        Args:
            event: Event data from Gamma API

        Returns:
            List of normalized market dictionaries
        """
        normalized_markets = []

        try:
            event_title = event.get('title', '')
            markets = event.get('markets', [])

            # Debug: Log event structure for first few events
            if len(markets) > 0 and not hasattr(self, '_logged_structure'):
                logger.debug(f"Event structure sample: {list(event.keys())}")
                logger.debug(f"First market keys: {list(markets[0].keys())}")
                self._logged_structure = True

            for market in markets:
                # Extract market data first for logging
                market_id = market.get('id', '')
                question = market.get('question', '')

                # Skip markets that are closed OR not accepting orders
                is_closed = market.get('closed', False)
                accepting_orders = market.get('acceptingOrders', False)
                is_active = market.get('active', False)

                if is_closed:
                    continue

                # Prefer markets that are accepting orders and active
                if not accepting_orders and not is_active:
                    continue

                condition_id = market.get('conditionId', '')

                # Get token IDs for CLOB trading
                # Gamma API may provide tokens in different places
                tokens = market.get('tokens', [])
                outcomes = market.get('outcomes', [])

                # Also check clobTokenIds field (alternative location)
                clob_token_ids = market.get('clobTokenIds', [])

                # Debug first market
                if not hasattr(self, '_logged_tokens'):
                    logger.debug(f"Token structure - tokens: {tokens[:2] if tokens else 'empty'}")
                    logger.debug(f"Token structure - clobTokenIds: {clob_token_ids[:2] if clob_token_ids else 'empty'}")
                    logger.debug(f"Token structure - outcomes: {outcomes[:2] if outcomes else 'empty'}")
                    self._logged_tokens = True

                # Find YES and NO token IDs
                yes_token_id = None
                no_token_id = None

                # Try clobTokenIds first (more reliable)
                if clob_token_ids and len(clob_token_ids) >= 2:
                    yes_token_id = clob_token_ids[0]
                    no_token_id = clob_token_ids[1]

                # Fallback: Check tokens array
                elif len(tokens) >= 2:
                    # Typically tokens[0] is YES, tokens[1] is NO
                    # But verify by checking outcome names
                    for i, outcome_name in enumerate(outcomes):
                        if isinstance(outcome_name, str):
                            if outcome_name.lower() in ['yes', 'true', '1']:
                                yes_token_id = tokens[i] if i < len(tokens) else None
                            elif outcome_name.lower() in ['no', 'false', '0']:
                                no_token_id = tokens[i] if i < len(tokens) else None

                    # If still no match, assume binary order
                    if not yes_token_id and len(tokens) >= 1:
                        yes_token_id = tokens[0]
                    if not no_token_id and len(tokens) >= 2:
                        no_token_id = tokens[1]

                # Last resort: try acceptingOrders or active field
                elif len(tokens) >= 1:
                    yes_token_id = tokens[0]
                    no_token_id = tokens[1] if len(tokens) >= 2 else None

                # Skip if we don't have token IDs (can't trade without them)
                if not yes_token_id:
                    # Only log first few to avoid spam
                    if not hasattr(self, '_skip_count'):
                        self._skip_count = 0
                    if self._skip_count < 3:
                        logger.debug(f"Skipping market {market_id}: no YES token ID found (tokens={tokens}, clob={clob_token_ids})")
                        self._skip_count += 1
                    continue

                # Get prices - handle both string and float formats
                outcome_prices = market.get('outcomePrices', [])
                try:
                    yes_price = float(outcome_prices[0]) if len(outcome_prices) > 0 else 0.0
                    no_price = float(outcome_prices[1]) if len(outcome_prices) > 1 else 1.0 - yes_price
                except (ValueError, TypeError):
                    yes_price = 0.5
                    no_price = 0.5

                # Get volume/liquidity
                volume = float(market.get('liquidityNum', market.get('liquidity', 0)))

                # Check for NegRisk flag (important for CLOB trading)
                neg_risk = market.get('negRisk', False)

                normalized = {
                    'platform': 'polymarket',
                    'market_id': market_id,
                    'title': f"{event_title} - {question}",
                    'question': question,
                    'event_title': event_title,

                    # Prices
                    'yes_price': yes_price,
                    'no_price': no_price,
                    'volume': volume,

                    # CLOB trading essentials
                    'yes_token_id': yes_token_id,
                    'no_token_id': no_token_id,
                    'condition_id': condition_id,
                    'neg_risk': neg_risk,

                    # For compatibility with existing code
                    'ticker_or_token_id': yes_token_id,

                    # Raw data for debugging
                    'raw_data': market
                }

                normalized_markets.append(normalized)

        except Exception as e:
            logger.warning(f"Error parsing event markets: {e}")

        return normalized_markets


async def test_discovery():
    """Test script to validate market discovery"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async with PolymarketMarketDiscovery() as discovery:
        # Run health check
        healthy = await discovery.health_check()
        if not healthy:
            logger.error("Health check failed - aborting")
            return

        # Fetch markets
        markets = await discovery.fetch_markets()

        print(f"\n{'=' * 80}")
        print(f"POLYMARKET MARKET DISCOVERY TEST")
        print(f"{'=' * 80}\n")
        print(f"Total markets discovered: {len(markets)}\n")

        # Show first 3 CLOB-tradable markets with token IDs
        print(f"First 3 CLOB-tradable markets:\n")
        for i, market in enumerate(markets[:3]):
            print(f"{i + 1}. {market['title'][:70]}")
            print(f"   Market ID: {market['market_id']}")
            print(f"   YES Token ID: {market['yes_token_id']}")
            print(f"   NO Token ID:  {market['no_token_id']}")
            print(f"   YES Price: ${market['yes_price']:.4f}")
            print(f"   NO Price:  ${market['no_price']:.4f}")
            print(f"   Volume: ${market['volume']:,.2f}")
            print(f"   NegRisk: {market['neg_risk']}")
            print(f"   Condition ID: {market['condition_id']}")
            print()

        print(f"{'=' * 80}\n")

        # Validate token IDs
        valid_markets = [m for m in markets if m['yes_token_id']]
        print(f"✅ Markets with valid YES token IDs: {len(valid_markets)}/{len(markets)}")

        if len(markets) == 0:
            print("\n❌ WARNING: No markets discovered! Check API connectivity.")
        elif len(valid_markets) < len(markets):
            print(f"\n⚠️ WARNING: {len(markets) - len(valid_markets)} markets missing token IDs")


if __name__ == '__main__':
    asyncio.run(test_discovery())
