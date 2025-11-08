"""
Arbitrage Engine
Detects and executes arbitrage opportunities across and within platforms
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

from websocket_streamer import PriceStore
from kalshi_trader import KalshiTrader
from polymarket_trader import PolymarketTrader

load_dotenv()

logger = logging.getLogger(__name__)


class ArbitrageOpportunity:
    """Represents an arbitrage opportunity"""

    def __init__(
        self,
        opportunity_type: str,
        expected_profit: float,
        confidence: float,
        legs: List[Dict]
    ):
        self.opportunity_type = opportunity_type  # 'cross_platform', 'intra_platform'
        self.expected_profit = expected_profit
        self.confidence = confidence
        self.legs = legs  # List of trades to execute
        self.timestamp = datetime.now()

    def __repr__(self):
        return (
            f"ArbitrageOpportunity(type={self.opportunity_type}, "
            f"profit=${self.expected_profit:.4f}, "
            f"confidence={self.confidence:.2%})"
        )


class ArbitrageEngine:
    """Detects and executes arbitrage opportunities"""

    def __init__(
        self,
        price_store: PriceStore,
        kalshi_trader: KalshiTrader,
        polymarket_trader: PolymarketTrader
    ):
        self.price_store = price_store
        self.kalshi_trader = kalshi_trader
        self.polymarket_trader = polymarket_trader

        # Configuration from environment
        self.min_profit_threshold = float(os.getenv('MIN_PROFIT_THRESHOLD', '0.01'))
        self.max_position_size = int(os.getenv('MAX_POSITION_SIZE', '100'))
        self.slippage_tolerance = float(os.getenv('SLIPPAGE_TOLERANCE', '0.005'))
        self.enable_cross_platform = os.getenv('ENABLE_CROSS_PLATFORM_ARB', 'true').lower() == 'true'
        self.enable_intra_platform = os.getenv('ENABLE_INTRA_PLATFORM_ARB', 'true').lower() == 'true'

        # Fee structures (approximate)
        self.kalshi_fee_rate = 0.07  # 7% on profits
        self.polymarket_fee_rate = 0.02  # 2% on trades

        # Risk management
        self.max_daily_loss = float(os.getenv('MAX_DAILY_LOSS', '1000'))
        self.circuit_breaker_loss = float(os.getenv('CIRCUIT_BREAKER_LOSS', '500'))
        self.max_open_orders = int(os.getenv('MAX_OPEN_ORDERS', '10'))

        # Tracking
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.trades_executed = 0
        self.circuit_breaker_triggered = False

        # Market mappings (to be set externally)
        self.market_mappings: List[Dict] = []

    def set_market_mappings(self, mappings: List[Dict]):
        """Set cross-platform market mappings for arbitrage"""
        self.market_mappings = mappings
        logger.info(f"Set {len(mappings)} market mappings for arbitrage")

    async def scan_for_opportunities(self) -> List[ArbitrageOpportunity]:
        """
        Scan for arbitrage opportunities

        Returns:
            List of detected opportunities
        """
        if self.circuit_breaker_triggered:
            logger.warning("Circuit breaker triggered - not scanning for opportunities")
            return []

        opportunities = []

        # Scan for cross-platform arbitrage
        if self.enable_cross_platform:
            cross_platform_opps = await self._scan_cross_platform()
            opportunities.extend(cross_platform_opps)

        # Scan for intra-platform arbitrage
        if self.enable_intra_platform:
            intra_platform_opps = await self._scan_intra_platform()
            opportunities.extend(intra_platform_opps)

        return opportunities

    async def _scan_cross_platform(self) -> List[ArbitrageOpportunity]:
        """Scan for cross-platform arbitrage opportunities"""
        opportunities = []

        for mapping in self.market_mappings:
            try:
                kalshi_market = mapping['kalshi_market']
                polymarket_market = mapping['polymarket_market']

                # Get live prices
                kalshi_prices = self.price_store.get('kalshi', kalshi_market['market_id'])
                polymarket_prices = self.price_store.get('polymarket', polymarket_market['ticker_or_token_id'])

                if not kalshi_prices or not polymarket_prices:
                    continue

                # Check for price discrepancies
                opp = self._check_cross_platform_opportunity(
                    kalshi_market,
                    polymarket_market,
                    kalshi_prices,
                    polymarket_prices
                )

                if opp:
                    opportunities.append(opp)

            except Exception as e:
                logger.error(f"Error scanning cross-platform arbitrage: {e}")

        return opportunities

    def _check_cross_platform_opportunity(
        self,
        kalshi_market: Dict,
        polymarket_market: Dict,
        kalshi_prices: Dict,
        polymarket_prices: Dict
    ) -> Optional[ArbitrageOpportunity]:
        """
        Check for cross-platform arbitrage between Kalshi and Polymarket

        Strategy: Buy low on one platform, sell high on the other
        """
        # Get best prices for YES outcome
        kalshi_yes_bid = kalshi_prices.get('yes_bid', 0)
        kalshi_yes_ask = kalshi_prices.get('yes_ask', 0)
        polymarket_bid = polymarket_prices.get('best_bid', 0)
        polymarket_ask = polymarket_prices.get('best_ask', 0)

        if not all([kalshi_yes_bid, kalshi_yes_ask, polymarket_bid, polymarket_ask]):
            return None

        # Scenario 1: Buy on Polymarket, sell on Kalshi
        # (Polymarket cheaper, Kalshi more expensive)
        profit_1 = kalshi_yes_bid - polymarket_ask

        # Scenario 2: Buy on Kalshi, sell on Polymarket
        # (Kalshi cheaper, Polymarket more expensive)
        profit_2 = polymarket_bid - kalshi_yes_ask

        # Account for fees
        fees = self._calculate_fees(1.0, 'cross_platform')
        net_profit_1 = profit_1 - fees
        net_profit_2 = profit_2 - fees

        # Check if either scenario is profitable
        if net_profit_1 >= self.min_profit_threshold:
            # Buy Polymarket, sell Kalshi
            position_size = min(self.max_position_size, self._calculate_optimal_size(net_profit_1))

            return ArbitrageOpportunity(
                opportunity_type='cross_platform',
                expected_profit=net_profit_1 * position_size,
                confidence=self._calculate_confidence(polymarket_ask, kalshi_yes_bid),
                legs=[
                    {
                        'platform': 'polymarket',
                        'action': 'buy',
                        'token_id': polymarket_market['ticker_or_token_id'],
                        'price': polymarket_ask,
                        'size': position_size
                    },
                    {
                        'platform': 'kalshi',
                        'action': 'sell',
                        'side': 'yes',
                        'ticker': kalshi_market['market_id'],
                        'price': kalshi_yes_bid,
                        'count': position_size
                    }
                ]
            )

        elif net_profit_2 >= self.min_profit_threshold:
            # Buy Kalshi, sell Polymarket
            position_size = min(self.max_position_size, self._calculate_optimal_size(net_profit_2))

            return ArbitrageOpportunity(
                opportunity_type='cross_platform',
                expected_profit=net_profit_2 * position_size,
                confidence=self._calculate_confidence(kalshi_yes_ask, polymarket_bid),
                legs=[
                    {
                        'platform': 'kalshi',
                        'action': 'buy',
                        'side': 'yes',
                        'ticker': kalshi_market['market_id'],
                        'price': kalshi_yes_ask,
                        'count': position_size
                    },
                    {
                        'platform': 'polymarket',
                        'action': 'sell',
                        'token_id': polymarket_market['ticker_or_token_id'],
                        'price': polymarket_bid,
                        'size': position_size
                    }
                ]
            )

        return None

    async def _scan_intra_platform(self) -> List[ArbitrageOpportunity]:
        """
        Scan for intra-platform arbitrage opportunities

        Strategy: Yes + No prices should sum to 1.0
        If Yes + No < 1.0: Buy both, guaranteed profit
        If Yes + No > 1.0: Sell both (if you have positions)
        """
        opportunities = []

        # Check all markets in price store
        all_prices = self.price_store.get_all()

        for (platform, market_id), prices in all_prices.items():
            try:
                if platform == 'kalshi':
                    opp = self._check_kalshi_intra_platform(market_id, prices)
                elif platform == 'polymarket':
                    # Polymarket YES/NO relationship is implicit
                    # NO = 1 - YES, so no arbitrage opportunity
                    continue

                if opp:
                    opportunities.append(opp)

            except Exception as e:
                logger.error(f"Error scanning intra-platform arbitrage: {e}")

        return opportunities

    def _check_kalshi_intra_platform(
        self,
        ticker: str,
        prices: Dict
    ) -> Optional[ArbitrageOpportunity]:
        """
        Check for intra-platform arbitrage on Kalshi

        If yes_ask + no_ask < 1.0, we can buy both and lock in profit
        """
        yes_ask = prices.get('yes_ask', 0)
        no_ask = prices.get('no_ask', 0)

        if not yes_ask or not no_ask:
            return None

        # Calculate total cost
        total_cost = yes_ask + no_ask

        # Payout is always $1.00
        profit = 1.0 - total_cost

        # Account for fees
        fees = self._calculate_fees(total_cost, 'intra_platform')
        net_profit = profit - fees

        if net_profit >= self.min_profit_threshold:
            position_size = min(self.max_position_size, self._calculate_optimal_size(net_profit))

            return ArbitrageOpportunity(
                opportunity_type='intra_platform',
                expected_profit=net_profit * position_size,
                confidence=0.99,  # Very high confidence - guaranteed profit
                legs=[
                    {
                        'platform': 'kalshi',
                        'action': 'buy',
                        'side': 'yes',
                        'ticker': ticker,
                        'price': yes_ask,
                        'count': position_size
                    },
                    {
                        'platform': 'kalshi',
                        'action': 'buy',
                        'side': 'no',
                        'ticker': ticker,
                        'price': no_ask,
                        'count': position_size
                    }
                ]
            )

        return None

    def _calculate_fees(self, trade_value: float, arb_type: str) -> float:
        """Calculate total fees for arbitrage trade"""
        if arb_type == 'cross_platform':
            # Both platforms involved
            return trade_value * (self.kalshi_fee_rate + self.polymarket_fee_rate)
        else:
            # Single platform
            return trade_value * self.kalshi_fee_rate

    def _calculate_optimal_size(self, profit_per_contract: float) -> int:
        """Calculate optimal position size based on profit"""
        # Simple Kelly Criterion approximation
        # In practice, would use more sophisticated position sizing
        if profit_per_contract > 0.05:
            return self.max_position_size
        elif profit_per_contract > 0.02:
            return self.max_position_size // 2
        else:
            return self.max_position_size // 4

    def _calculate_confidence(self, buy_price: float, sell_price: float) -> float:
        """
        Calculate confidence in arbitrage opportunity
        Based on spread width and market conditions
        """
        if buy_price <= 0 or sell_price <= 0:
            return 0.0

        # Wider spread = higher confidence
        spread = sell_price - buy_price
        confidence = min(spread / 0.1, 1.0)  # Normalize to 0-1

        return confidence

    async def execute_opportunity(self, opportunity: ArbitrageOpportunity, test_mode: bool = False) -> Dict:
        """
        Execute an arbitrage opportunity

        Args:
            opportunity: The arbitrage opportunity to execute
            test_mode: If True, simulate execution and track paper trading PnL

        Returns:
            Execution results
        """
        if self.circuit_breaker_triggered:
            logger.warning("Circuit breaker triggered - cannot execute")
            return {'success': False, 'error': 'Circuit breaker triggered'}

        logger.info(f"{'[PAPER TRADE] ' if test_mode else ''}Executing arbitrage: {opportunity}")

        results = {
            'opportunity': opportunity,
            'legs': [],
            'success': False,
            'executed_legs': 0,
            'total_legs': len(opportunity.legs),
            'test_mode': test_mode
        }

        try:
            # In test mode, simulate successful execution
            if test_mode:
                logger.info(f"[PAPER TRADE] Simulating {opportunity.opportunity_type} arbitrage")
                logger.info(f"[PAPER TRADE] Executing {len(opportunity.legs)} legs:")

                # Log each leg of the trade
                for i, leg in enumerate(opportunity.legs):
                    platform = leg.get('platform')
                    action = leg.get('action')

                    if platform == 'kalshi':
                        side = leg.get('side')
                        ticker = leg.get('ticker')
                        price = leg.get('price')
                        count = leg.get('count')
                        logger.info(
                            f"[PAPER TRADE]   Leg {i+1}: {action.upper()} {count} {ticker} "
                            f"{side.upper()} @ ${price:.4f} on Kalshi"
                        )
                    elif platform == 'polymarket':
                        token_id = leg.get('token_id')
                        price = leg.get('price')
                        size = leg.get('size')
                        logger.info(
                            f"[PAPER TRADE]   Leg {i+1}: {action.upper()} {size} contracts "
                            f"@ ${price:.4f} on Polymarket (token: {token_id[:8]}...)"
                        )

                    results['legs'].append({
                        'success': True,
                        'simulated': True,
                        'leg': leg
                    })

                results['executed_legs'] = len(opportunity.legs)
                results['success'] = True

                # Track paper trading PnL
                self.daily_pnl += opportunity.expected_profit
                self.total_pnl += opportunity.expected_profit
                self.trades_executed += 1

                # Log immediate arbitrage profit (locked-in)
                logger.info(
                    f"✅ [PAPER TRADE] IMMEDIATE LOCKED-IN PROFIT: ${opportunity.expected_profit:.4f}"
                )
                logger.info(f"[PAPER TRADE] Strategy: {opportunity.opportunity_type}")
                logger.info(f"[PAPER TRADE] Confidence: {opportunity.confidence:.1%}")

                if opportunity.opportunity_type == 'intra_platform':
                    logger.info(f"[PAPER TRADE] Mechanism: Buy YES+NO < $1.00, guaranteed payout $1.00")
                elif opportunity.opportunity_type == 'cross_platform':
                    logger.info(f"[PAPER TRADE] Mechanism: Buy low on one platform, sell high on other")

                logger.info(
                    f"[PAPER TRADE] Running Total Paper PnL: ${self.total_pnl:.2f} "
                    f"(Daily: ${self.daily_pnl:.2f})"
                )
                logger.info("-" * 70)

                return results
            # Execute all legs concurrently
            leg_tasks = []
            for leg in opportunity.legs:
                task = asyncio.create_task(self._execute_leg(leg))
                leg_tasks.append(task)

            # Wait for all legs to complete
            leg_results = await asyncio.gather(*leg_tasks, return_exceptions=True)

            # Process results
            successful_legs = 0
            for i, result in enumerate(leg_results):
                if isinstance(result, Exception):
                    logger.error(f"Leg {i} failed with exception: {result}")
                    results['legs'].append({'success': False, 'error': str(result)})
                else:
                    results['legs'].append(result)
                    if result.get('success'):
                        successful_legs += 1

            results['executed_legs'] = successful_legs
            results['success'] = successful_legs == len(opportunity.legs)

            # Update PnL tracking
            if results['success']:
                self.daily_pnl += opportunity.expected_profit
                self.total_pnl += opportunity.expected_profit
                self.trades_executed += 1

                logger.info(
                    f"✅ Arbitrage executed successfully! "
                    f"Profit: ${opportunity.expected_profit:.4f}, "
                    f"Total PnL: ${self.total_pnl:.2f}"
                )
            else:
                logger.warning(
                    f"⚠️ Partial execution: {successful_legs}/{len(opportunity.legs)} legs completed"
                )

                # Handle partial fills (risk management)
                await self._handle_partial_fill(opportunity, results)

            # Check circuit breaker
            self._check_circuit_breaker()

        except Exception as e:
            logger.error(f"Error executing arbitrage: {e}")
            results['error'] = str(e)

        return results

    async def _execute_leg(self, leg: Dict) -> Dict:
        """Execute a single leg of the arbitrage"""
        try:
            platform = leg['platform']
            action = leg['action']

            if platform == 'kalshi':
                # Execute Kalshi trade
                side = leg['side']
                ticker = leg['ticker']
                price = leg.get('price')
                count = leg['count']

                if action == 'buy':
                    result = await self.kalshi_trader.place_order(
                        ticker, 'buy', side, count, price
                    )
                else:  # sell
                    result = await self.kalshi_trader.place_order(
                        ticker, 'sell', side, count, price
                    )

            elif platform == 'polymarket':
                # Execute Polymarket trade
                token_id = leg['token_id']
                price = leg['price']
                size = leg['size']

                if action == 'buy':
                    result = await self.polymarket_trader.buy(token_id, size, price)
                else:  # sell
                    result = await self.polymarket_trader.sell(token_id, size, price)

            else:
                result = {'success': False, 'error': f'Unknown platform: {platform}'}

            return result

        except Exception as e:
            logger.error(f"Error executing leg: {e}")
            return {'success': False, 'error': str(e)}

    async def _handle_partial_fill(self, opportunity: ArbitrageOpportunity, results: Dict):
        """
        Handle partial fills to minimize risk

        If only some legs executed, try to reverse or hedge
        """
        logger.warning("Handling partial fill - attempting to minimize risk")

        # Identify which legs succeeded
        successful_legs = []
        for i, leg_result in enumerate(results['legs']):
            if leg_result.get('success'):
                successful_legs.append((i, opportunity.legs[i], leg_result))

        # For each successful leg, try to reverse it
        for i, leg, result in successful_legs:
            try:
                # Create reverse order
                reverse_leg = dict(leg)
                reverse_leg['action'] = 'sell' if leg['action'] == 'buy' else 'buy'

                logger.info(f"Reversing leg {i}: {reverse_leg}")
                await self._execute_leg(reverse_leg)

            except Exception as e:
                logger.error(f"Failed to reverse leg {i}: {e}")

    def _check_circuit_breaker(self):
        """Check if circuit breaker should be triggered"""
        if self.daily_pnl < -self.circuit_breaker_loss:
            logger.critical(
                f"🚨 CIRCUIT BREAKER TRIGGERED! "
                f"Daily loss: ${-self.daily_pnl:.2f} exceeds limit"
            )
            self.circuit_breaker_triggered = True

    def reset_daily_stats(self):
        """Reset daily statistics (call at start of each day)"""
        logger.info(f"Resetting daily stats. Previous PnL: ${self.daily_pnl:.2f}")
        self.daily_pnl = 0.0
        self.circuit_breaker_triggered = False

    def get_stats(self) -> Dict:
        """Get current statistics"""
        return {
            'daily_pnl': self.daily_pnl,
            'total_pnl': self.total_pnl,
            'trades_executed': self.trades_executed,
            'circuit_breaker_triggered': self.circuit_breaker_triggered,
            'config': {
                'min_profit_threshold': self.min_profit_threshold,
                'max_position_size': self.max_position_size,
                'slippage_tolerance': self.slippage_tolerance
            }
        }
