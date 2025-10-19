from __future__ import annotations

import httpx
from typing import Dict, List

COINGECKO_SIMPLE_URL = "https://api.coingecko.com/api/v3/simple/price"


class PriceService:
    async def get_prices(self, symbols: List[str]) -> Dict[str, float]:
        # map symbols to coingecko ids
        symbol_to_id = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "BNB": "binancecoin",
            "SOL": "solana",
            "AVAX": "avalanche-2",
            "LTC": "litecoin",
            "OP": "optimism",
            "MATIC": "matic-network",
            "TON": "the-open-network",
            "TRX": "tron",
        }
        ids = [symbol_to_id[s] for s in symbols if s in symbol_to_id]
        if not ids:
            return {s: 0.0 for s in symbols}
        params = {"ids": ",".join(ids), "vs_currencies": "usd"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(COINGECKO_SIMPLE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        id_to_symbol = {v: k for k, v in symbol_to_id.items()}
        prices: Dict[str, float] = {}
        for coin_id, row in data.items():
            symbol = id_to_symbol.get(coin_id)
            if symbol:
                prices[symbol] = float(row.get("usd", 0.0))
        # ensure all requested symbols in result
        for s in symbols:
            prices.setdefault(s, 0.0)
        return prices
