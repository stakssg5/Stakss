from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .services.cards import generate_cards, CARD_SPECS
from .services.card_store import CardStore

from .services.prices import PriceService
from .services.balances import BalanceService
from .services.auth import AuthService

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
CARDS_DB_PATH = BASE_DIR / "cards.db"
CARD_STORE = CardStore(CARDS_DB_PATH)

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


auth_service = AuthService()


class LoginRequest(BaseModel):
    email: str
    cvv: str


@app.post("/api/auth/login")
def login(req: LoginRequest) -> Dict[str, Any]:
    user = auth_service.authenticate(email=req.email, cvv=req.cvv)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth_service.create_session(user)
    return {
        "token": token,
        "user": {"id": user.id, "full_name": user.full_name, "email": user.email},
    }


@app.get("/api/auth/me")
def me(authorization: str | None = Header(default=None)) -> Dict[str, Any]:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    user = auth_service.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"user": {"id": user.id, "full_name": user.full_name, "email": user.email}}


@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None)) -> Dict[str, str]:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        auth_service.revoke(token)
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


# ----- Test credit card generator (sandbox) -----
@app.get("/api/cards/brands")
def get_card_brands() -> Dict[str, List[Dict[str, str]]]:
    brands = [{"key": k, "label": v.brand} for k, v in CARD_SPECS.items()]
    brands.sort(key=lambda x: x["label"])  # stable order for UI
    return {"brands": brands}


@app.get("/api/cards")
def get_cards(count: int = 1, brand: Optional[str] = None, source: str = "gen") -> Dict[str, Any]:
    if count < 1 or count > 20:
        raise HTTPException(status_code=400, detail="count must be between 1 and 20")
    source_key = (source or "gen").lower()
    if source_key not in ("gen", "db"):
        raise HTTPException(status_code=400, detail="source must be 'gen' or 'db'")
    try:
        if source_key == "db":
            # Seed if the table is empty, then fetch
            CARD_STORE.seed_if_empty(target_total=60)
            cards = CARD_STORE.fetch_cards(count=count, brand=brand)
        else:
            cards = generate_cards(count=count, brand=brand)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "cards": cards,
        "note": "Sandbox test numbers for development and QA only; not valid for payments.",
        "source": source_key,
    }


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

# ----- Stripe Checkout (safe, PCI-compliant via Stripe-hosted UI) -----
try:
    import stripe  # type: ignore
except Exception:
    stripe = None  # defer import errors until used


def _require_stripe() -> Any:
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe library not installed")
    if not os.getenv("STRIPE_SECRET_KEY"):
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY not set")
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    return stripe


@app.post("/api/stripe/checkout")
def create_checkout_session() -> Dict[str, Any]:
    s = _require_stripe()
    session = s.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": "Pro Plan"},
                "unit_amount": 5000,
            },
            "quantity": 1,
        }],
        success_url=os.getenv("STRIPE_SUCCESS_URL", "http://localhost:8000/?paid=1"),
        cancel_url=os.getenv("STRIPE_CANCEL_URL", "http://localhost:8000/?canceled=1"),
        automatic_tax={"enabled": False},
    )
    return {"url": session.url}


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request) -> JSONResponse:
    s = _require_stripe()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not endpoint_secret:
        return JSONResponse({"received": True}, status_code=200)
    try:
        event = s.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=endpoint_secret)
    except Exception:
        return JSONResponse({"error": "Invalid signature"}, status_code=400)
    # Minimal handler
    if event["type"] == "checkout.session.completed":
        pass
    return JSONResponse({"received": True}, status_code=200)
