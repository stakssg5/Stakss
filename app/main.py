from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from .services.prices import PriceService
from .services.balances import BalanceService

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Crypto PR+ API")

# Allow Telegram webview origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/ping")
def ping() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/check")
async def check_balances(address: str, chain: str = "btc") -> Dict[str, Any]:
    try:
        balances = await BalanceService().get_balance(chain=chain, address=address)
        prices = await PriceService().get_prices(symbols=[balances["symbol"]])
        result = {
            "chain": chain,
            "address": address,
            "symbol": balances["symbol"],
            "balance": balances["balance"],
            "balance_usd": float(balances["balance"]) * float(prices[balances["symbol"]]),
            "price_usd": prices[balances["symbol"]],
        }
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----- Mock transfer endpoint for safe demo -----
class TransferRequest(BaseModel):
    account_from: str
    account_to: str
    amount: float = Field(gt=0, description="Amount to transfer in USD (demo)")


@app.post("/api/mock/transfer")
def mock_transfer(req: TransferRequest, authorization: str | None = Header(default=None)) -> Dict[str, Any]:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    # This is a no-op demo endpoint: nothing is transferred.
    transfer_id = str(uuid.uuid4())
    processed_at = datetime.now(tz=timezone.utc).isoformat()
    return {
        "status": "ok",
        "transfer_id": transfer_id,
        "processed_at": processed_at,
        "echo": {
            "account_from": req.account_from,
            "account_to": req.account_to,
            "amount": req.amount,
        },
    }


# Mount static frontend (Telegram Mini App)
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
