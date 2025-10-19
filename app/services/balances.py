from __future__ import annotations

from typing import Any, Dict

import httpx


class BalanceService:
    async def get_balance(self, chain: str, address: str) -> Dict[str, Any]:
        chain_l = chain.lower()
        if chain_l == "btc":
            return await self._get_btc_balance(address)
        # Placeholders for other chains
        if chain_l in {"eth", "bsc", "sol", "avax", "ltc", "op", "matic", "ton", "trx"}:
            return {"symbol": chain_l.upper(), "balance": 0.0}
        raise ValueError(f"Unsupported chain: {chain}")

    async def _get_btc_balance(self, address: str) -> Dict[str, Any]:
        # Use Blockstream API for simplicity
        url = f"https://blockstream.info/api/address/{address}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                raise ValueError("Invalid BTC address")
            resp.raise_for_status()
            data = resp.json()
        # final balance in sats = chain_stats.funded_txo_sum - spent
        chain_stats = data.get("chain_stats", {})
        mempool_stats = data.get("mempool_stats", {})
        received = int(chain_stats.get("funded_txo_sum", 0)) + int(mempool_stats.get("funded_txo_sum", 0))
        sent = int(chain_stats.get("spent_txo_sum", 0)) + int(mempool_stats.get("spent_txo_sum", 0))
        sats = max(received - sent, 0)
        btc = sats / 1e8
        return {"symbol": "BTC", "balance": btc}
