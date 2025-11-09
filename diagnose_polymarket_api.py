#!/usr/bin/env python3
"""
Diagnostic script to inspect raw Polymarket Gamma API response
"""

import asyncio
import aiohttp
import json

async def inspect_api():
    """Fetch and print raw API response"""

    url = "https://gamma-api.polymarket.com/events"
    params = {
        'order': 'id',
        'ascending': 'false',
        'closed': 'false',
        'limit': 3  # Just get 3 events
    }

    headers = {
        'User-Agent': 'arb-bot/1.0',
        'Accept': 'application/json'
    }

    print("Fetching from Gamma API...")
    print(f"URL: {url}")
    print(f"Params: {params}\n")

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as response:
            print(f"Status: {response.status}\n")

            data = await response.json()

            print(f"Received {len(data)} events\n")
            print("=" * 80)

            for i, event in enumerate(data):
                print(f"\nEVENT {i+1}:")
                print(f"  Title: {event.get('title', 'N/A')}")
                print(f"  ID: {event.get('id', 'N/A')}")
                print(f"  Closed: {event.get('closed', 'N/A')}")
                print(f"  EnableOrderBook: {event.get('enableOrderBook', 'N/A')}")

                markets = event.get('markets', [])
                print(f"  Markets: {len(markets)}")

                if markets:
                    print(f"\n  First Market:")
                    market = markets[0]

                    # Print all keys
                    print(f"    Keys: {list(market.keys())}")

                    # Print important fields
                    print(f"    ID: {market.get('id', 'N/A')}")
                    print(f"    Question: {market.get('question', 'N/A')}")
                    print(f"    Closed: {market.get('closed', 'N/A')}")
                    print(f"    Active: {market.get('active', 'N/A')}")
                    print(f"    Accepting Orders: {market.get('acceptingOrders', 'N/A')}")

                    # Token information
                    print(f"    Tokens: {market.get('tokens', 'N/A')}")
                    print(f"    ClobTokenIds: {market.get('clobTokenIds', 'N/A')}")
                    print(f"    Outcomes: {market.get('outcomes', 'N/A')}")
                    print(f"    Outcome Prices: {market.get('outcomePrices', 'N/A')}")

                    print(f"\n  Full Market JSON:")
                    print(f"    {json.dumps(market, indent=6)[:500]}...")

                print("\n" + "-" * 80)

if __name__ == '__main__':
    asyncio.run(inspect_api())
