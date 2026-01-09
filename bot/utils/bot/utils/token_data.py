# bot/utils/token_data.py
import asyncio
import logging
from typing import Dict, Any

import aiohttp
from cachetools import TTLCache  # or your hybrid cache

from core.config import settings

logger = logging.getLogger(__name__)

# Your cache (example with TTL 5 minutes)
hybrid_token_data_cache = TTLCache(maxsize=500, ttl=300)

DEXSCREENER_API_BASE_URL = "https://api.dexscreener.com/latest/dex"

async def get_sol_price() -> float:
    """Simple SOL price fetch - cache or use better source in production"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://price.jup.ag/v4/price?ids=SOL") as resp:
                data = await resp.json()
                return float(data['data']['SOL']['price'])
    except Exception:
        return 138.0  # fallback


async def fetch_token_data(contract_address: str) -> Dict[str, Any]:
    """
    Fetch token data primarily from DexScreener
    Returns enriched token info for trading display
    """
    cache_key = contract_address.lower()
    if cached := hybrid_token_data_cache.get(cache_key):
        return cached

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{DEXSCREENER_API_BASE_URL}/search?q={contract_address}"
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    raise ValueError(f"DexScreener returned {resp.status}")

                data = await resp.json()

                if not data.get("pairs"):
                    raise ValueError("No pairs found")

                # Pick best pair (highest liquidity usually)
                pair = sorted(
                    data["pairs"],
                    key=lambda p: float(p.get("liquidity", {}).get("usd", 0)),
                    reverse=True
                )[0]

                is_base = pair["baseToken"]["address"].lower() == contract_address.lower()
                token_info = pair["baseToken"] if is_base else pair["quoteToken"]

                sol_price = await get_sol_price()
                price_usd = float(pair.get("priceUsd", 0))
                tokens_per_sol = sol_price / price_usd if price_usd > 0 else 0

                result = {
                    "address": contract_address,
                    "name": token_info.get("name", "Unknown"),
                    "symbol": token_info.get("symbol", "???"),
                    "decimals": token_info.get("decimals", 9),
                    "dex": pair["dexId"],
                    "price_usd": price_usd,
                    "price_change_h24": float(pair.get("priceChange", {}).get("h24", 0)),
                    "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0)),
                    "volume_h24": float(pair.get("volume", {}).get("h24", 0)),
                    "market_cap": float(pair.get("marketCap", 0)),
                    "fdv": float(pair.get("fdv", 0)),
                    "buy_1_sol_tokens": round(tokens_per_sol, 4),
                    "dexscreener_url": pair["url"],
                    "solscan_url": f"https://solscan.io/token/{contract_address}",
                }

                hybrid_token_data_cache[cache_key] = result
                return result

    except Exception as e:
        logger.error(f"Failed to fetch token {contract_address}: {e}")
        return {
            "address": contract_address,
            "name": "Unknown",
            "symbol": "???",
            "price_usd": 0,
            "liquidity_usd": 0,
            "volume_h24": 0,
            "warning": "Data unavailable - check manually on DexScreener"
        }
