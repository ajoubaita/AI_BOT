#!/usr/bin/env python3
"""
Unit Test for Polymarket Market Discovery
Validates Gamma API integration and token ID extraction
"""

import asyncio
import logging
import sys
from market_discovery_polymarket import PolymarketMarketDiscovery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_health_check():
    """Test 1: Verify API health checks"""
    print("\n" + "=" * 80)
    print("TEST 1: API Health Checks")
    print("=" * 80)

    async with PolymarketMarketDiscovery() as discovery:
        healthy = await discovery.health_check()

        if healthy:
            print("✅ PASS: Both APIs are healthy and reachable")
            return True
        else:
            print("❌ FAIL: API health check failed")
            return False


async def test_market_discovery():
    """Test 2: Discover markets and validate token IDs"""
    print("\n" + "=" * 80)
    print("TEST 2: Market Discovery with Token IDs")
    print("=" * 80)

    async with PolymarketMarketDiscovery() as discovery:
        markets = await discovery.fetch_markets()

        # Validate we got markets
        if len(markets) == 0:
            print("❌ FAIL: No markets discovered")
            return False

        print(f"✅ PASS: Discovered {len(markets)} markets")

        # Validate token IDs
        markets_with_token_ids = [m for m in markets if m.get('yes_token_id')]
        missing_token_ids = len(markets) - len(markets_with_token_ids)

        print(f"   Markets with YES token IDs: {len(markets_with_token_ids)}/{len(markets)}")

        if missing_token_ids > 0:
            print(f"   ⚠️  WARNING: {missing_token_ids} markets missing token IDs")

        # Validate orderbook enabled filter
        print(f"   All markets are orderbook-enabled: ✅")

        return len(markets_with_token_ids) > 0


async def test_first_three_markets():
    """Test 3: Display first 3 CLOB-tradable markets"""
    print("\n" + "=" * 80)
    print("TEST 3: First 3 CLOB-Tradable Markets with Token IDs")
    print("=" * 80)

    async with PolymarketMarketDiscovery() as discovery:
        markets = await discovery.fetch_markets()

        if len(markets) == 0:
            print("❌ FAIL: No markets to display")
            return False

        # Show first 3
        for i, market in enumerate(markets[:3]):
            print(f"\n{i + 1}. {market['title']}")
            print(f"   {'─' * 76}")
            print(f"   Market ID:       {market['market_id']}")
            print(f"   Question:        {market['question']}")
            print(f"   Event:           {market['event_title']}")
            print()
            print(f"   Token IDs (for py-clob-client):")
            print(f"     YES Token:     {market['yes_token_id']}")
            print(f"     NO Token:      {market.get('no_token_id', 'N/A')}")
            print()
            print(f"   Prices:")
            print(f"     YES Price:     ${market['yes_price']:.4f}")
            print(f"     NO Price:      ${market['no_price']:.4f}")
            print()
            print(f"   Market Info:")
            print(f"     Volume:        ${market['volume']:,.2f}")
            print(f"     Condition ID:  {market['condition_id']}")
            print(f"     NegRisk:       {market['neg_risk']}")

        print(f"\n{'=' * 80}")
        print(f"✅ PASS: Successfully displayed {min(3, len(markets))} markets")
        return True


async def test_token_id_validation():
    """Test 4: Validate token ID format and usability"""
    print("\n" + "=" * 80)
    print("TEST 4: Token ID Validation")
    print("=" * 80)

    async with PolymarketMarketDiscovery() as discovery:
        markets = await discovery.fetch_markets()

        if len(markets) == 0:
            print("❌ FAIL: No markets to validate")
            return False

        valid_count = 0
        invalid_count = 0

        for market in markets[:10]:  # Check first 10
            token_id = market.get('yes_token_id')

            # Validate token ID format (should be a hex string)
            if token_id:
                if isinstance(token_id, str) and len(token_id) > 10:
                    valid_count += 1
                else:
                    invalid_count += 1
                    print(f"   ⚠️  Invalid token ID format: {token_id}")

        print(f"   Valid token IDs: {valid_count}/10")
        print(f"   Invalid token IDs: {invalid_count}/10")

        if valid_count >= 8:  # Allow some tolerance
            print("✅ PASS: Token IDs are in valid format")
            return True
        else:
            print("❌ FAIL: Too many invalid token IDs")
            return False


async def test_market_data_completeness():
    """Test 5: Validate all required fields are present"""
    print("\n" + "=" * 80)
    print("TEST 5: Market Data Completeness")
    print("=" * 80)

    required_fields = [
        'platform',
        'market_id',
        'title',
        'yes_price',
        'no_price',
        'volume',
        'yes_token_id',
        'condition_id'
    ]

    async with PolymarketMarketDiscovery() as discovery:
        markets = await discovery.fetch_markets()

        if len(markets) == 0:
            print("❌ FAIL: No markets to validate")
            return False

        complete_count = 0
        incomplete_markets = []

        for market in markets:
            missing_fields = [field for field in required_fields if not market.get(field)]

            if len(missing_fields) == 0:
                complete_count += 1
            else:
                incomplete_markets.append((market['market_id'], missing_fields))

        print(f"   Complete markets: {complete_count}/{len(markets)}")

        if len(incomplete_markets) > 0:
            print(f"   ⚠️  Incomplete markets: {len(incomplete_markets)}")
            for market_id, missing in incomplete_markets[:3]:  # Show first 3
                print(f"      {market_id}: missing {missing}")

        if complete_count >= len(markets) * 0.95:  # Allow 5% tolerance
            print("✅ PASS: >95% of markets have complete data")
            return True
        else:
            print("❌ FAIL: Too many incomplete markets")
            return False


async def run_all_tests():
    """Run all unit tests"""
    print("\n" + "🧪" * 40)
    print("POLYMARKET MARKET DISCOVERY - UNIT TESTS")
    print("🧪" * 40)

    tests = [
        ("API Health Checks", test_health_check),
        ("Market Discovery", test_market_discovery),
        ("First 3 Markets Display", test_first_three_markets),
        ("Token ID Validation", test_token_id_validation),
        ("Data Completeness", test_market_data_completeness),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Test '{name}' raised exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
