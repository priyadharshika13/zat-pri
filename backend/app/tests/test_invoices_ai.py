import os
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from hypothesis import given, settings, strategies as st

# Change this if your app import path differs
from app.main import create_application

APP = create_application()

BASE_URL = "http://test"

def token_headers():
    """
    Put a real token in env for local tests:
      set ZATCA_TEST_TOKEN=eyJ...
    """
    token = os.getenv("ZATCA_TEST_TOKEN")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}

def make_invoice_payload(invoice_date: datetime):
    # Minimal realistic payload (edit fields to match your schema)
    return {
        "invoice_number": "INV-1001",
        "invoice_date": invoice_date.isoformat(),
        "seller": {
            "name": "Demo Seller",
            "vat_number": "300000000000003",
            "address": "Riyadh"
        },
        "buyer": {
            "name": "Demo Buyer",
            "vat_number": "300000000000003",
            "address": "Riyadh"
        },
        "currency": "SAR",
        "line_items": [
            {
                "name": "Item A",
                "quantity": 2,
                "unit_price": 100,
                "discount": 0,
                "tax_rate": 15,
                "tax_category": "STANDARD"
            }
        ]
    }

@pytest.mark.asyncio
async def test_invoice_requires_auth_or_returns_401():
    async with AsyncClient(app=APP, base_url=BASE_URL) as ac:
        payload = make_invoice_payload(datetime.now(timezone.utc) - timedelta(minutes=1))
        r = await ac.post("/api/v1/invoices", json=payload)  # no auth
        assert r.status_code in (401, 403)

@pytest.mark.asyncio
async def test_invoice_create_success_with_token():
    async with AsyncClient(app=APP, base_url=BASE_URL, headers=token_headers()) as ac:
        payload = make_invoice_payload(datetime.now(timezone.utc) - timedelta(minutes=1))
        r = await ac.post("/api/v1/invoices", json=payload)

        # If no token provided, skip (so tests still runnable)
        if not token_headers():
            pytest.skip("Set ZATCA_TEST_TOKEN env to run authenticated test")

        assert r.status_code == 201, r.text
        data = r.json()

        # Basic ZATCA-like expectations
        assert "uuid" in data and data["uuid"]
        assert "hash" in data and data["hash"]
        assert "invoice_number" in data

@pytest.mark.asyncio
async def test_invoice_future_date_rejected():
    async with AsyncClient(app=APP, base_url=BASE_URL, headers=token_headers()) as ac:
        if not token_headers():
            pytest.skip("Set ZATCA_TEST_TOKEN env to run authenticated test")

        future_dt = datetime.now(timezone.utc) + timedelta(days=1)
        payload = make_invoice_payload(future_dt)
        r = await ac.post("/api/v1/invoices", json=payload)

        # Should be validation error (your validator should return 422)
        assert r.status_code in (400, 422), r.text

# -----------------------------
# "AI-like" fuzz/property tests
# -----------------------------

# generate quantities/unit_prices/tax_rates automatically
qtys = st.floats(min_value=0.01, max_value=100, allow_nan=False, allow_infinity=False)
prices = st.floats(min_value=0.0, max_value=1_000_000, allow_nan=False, allow_infinity=False)
tax_rates = st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
discounts = st.floats(min_value=0.0, max_value=1_000_000, allow_nan=False, allow_infinity=False)

@settings(max_examples=35)
@given(q=qtys, p=prices, t=tax_rates, d=discounts)
@pytest.mark.asyncio
async def test_fuzz_line_item_never_crashes(q, p, t, d):
    """
    This is the core "AI test": Hypothesis generates many edge cases.
    Goal: your API should NEVER 500. It can return 4xx if invalid.
    """
    async with AsyncClient(app=APP, base_url=BASE_URL, headers=token_headers()) as ac:
        if not token_headers():
            pytest.skip("Set ZATCA_TEST_TOKEN env to run authenticated test")

        dt = datetime.now(timezone.utc) - timedelta(minutes=1)
        payload = make_invoice_payload(dt)
        payload["line_items"] = [{
            "name": "Fuzz Item",
            "quantity": float(q),
            "unit_price": float(p),
            "discount": float(d),
            "tax_rate": float(t),
            "tax_category": "STANDARD"
        }]

        r = await ac.post("/api/v1/invoices", json=payload)

        # HARD RULE: never 500
        assert r.status_code != 500, r.text
