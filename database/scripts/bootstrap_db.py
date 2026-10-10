#!/usr/bin/env python3
"""Seed 10 Coinbase USD crypto products into an initialized PostgreSQL database."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import psycopg
from psycopg.rows import dict_row

DEFAULT_DATABASE_URL = "postgresql://marketpulse:marketpulse_local@localhost:5432/marketpulse"
COINBASE_BASE_URL = "https://api.exchange.coinbase.com"
REQUEST_TIMEOUT_SECONDS = 8
PREFERRED_PRODUCTS = (
    "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
    "DOGE-USD", "AVAX-USD", "LINK-USD", "LTC-USD", "BCH-USD",
)
FIAT_CURRENCIES = {
    "USD", "EUR", "GBP", "CAD", "AUD", "NZD", "CHF", "JPY", "CNY",
    "HKD", "SGD", "KRW", "INR", "BRL", "MXN", "ARS", "TRY", "ZAR",
    "PLN", "SEK", "NOK", "DKK", "CZK", "HUF", "ILS", "AED", "SAR",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def request_json(path: str) -> Any:
    request = Request(
        f"{COINBASE_BASE_URL}{path}",
        headers={"Accept": "application/json", "User-Agent": "marketpulse/0.1"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise RuntimeError(f"Coinbase returned HTTP {response.status}")
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Coinbase returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Coinbase: {exc.reason}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Coinbase returned invalid JSON") from exc


def fetch_catalog() -> list[dict[str, Any]]:
    payload = request_json("/products")
    if not isinstance(payload, list):
        raise RuntimeError("Coinbase product catalog response was not a list")
    return [item for item in payload if isinstance(item, dict)]


def is_eligible(market: dict[str, Any]) -> bool:
    product_id = market.get("id")
    base = market.get("base_currency")
    quote_currency = market.get("quote_currency")
    if not all(isinstance(v, str) and v for v in (product_id, base, quote_currency)):
        return False
    base, quote_currency = base.upper(), quote_currency.upper()
    return (
        product_id.upper() == f"{base}-{quote_currency}"
        and quote_currency == "USD"
        and base not in FIAT_CURRENCIES
        and market.get("status") == "online"
        and not bool(market.get("trading_disabled", False))
    )


def ordered_candidates(catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible = {item["id"].upper(): item for item in catalog if is_eligible(item)}
    ordered: list[dict[str, Any]] = []
    used: set[str] = set()
    for product_id in PREFERRED_PRODUCTS:
        if product_id in eligible:
            ordered.append(eligible[product_id])
            used.add(product_id)
    ordered.extend(eligible[key] for key in sorted(eligible) if key not in used)
    return ordered


def parse_ticker(product_id: str) -> tuple[Decimal, datetime | None]:
    payload = request_json(f"/products/{quote(product_id, safe='-')}/ticker")
    if not isinstance(payload, dict) or not isinstance(payload.get("price"), str):
        raise RuntimeError(f"Ticker response for {product_id} had no decimal price")
    try:
        price = Decimal(payload["price"])
    except InvalidOperation as exc:
        raise RuntimeError(f"Ticker response for {product_id} had an invalid price") from exc
    if not price.is_finite() or price <= 0:
        raise RuntimeError(f"Ticker response for {product_id} did not contain a positive price")
    trade_time = payload.get("time")
    parsed_time = None
    if isinstance(trade_time, str):
        try:
            parsed_time = datetime.fromisoformat(trade_time.replace("Z", "+00:00"))
        except ValueError:
            pass
    return price, parsed_time


def save_catalog(conn: psycopg.Connection, catalog: list[dict[str, Any]]) -> None:
    now = utc_now()
    rows = []
    for market in catalog:
        product_id = market.get("id")
        base_value = market.get("base_currency")
        quote_value = market.get("quote_currency")
        if not all(isinstance(v, str) and v for v in (product_id, base_value, quote_value)):
            continue
        base, quote_currency, product_id = base_value.upper(), quote_value.upper(), product_id.upper()
        rows.append((
            product_id, base, quote_currency,
            str(market.get("display_name") or f"{base}/{quote_currency}"),
            str(market.get("status") or "unknown"),
            bool(market.get("trading_disabled", False)), is_eligible(market), now,
        ))
    if not rows:
        return
    with conn.transaction():
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO coinbase_market_catalog (
                coinbase_product_id, base_currency, quote_currency, display_name,
                market_status, trading_disabled, is_eligible, last_seen_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (coinbase_product_id) DO UPDATE SET
                    base_currency=excluded.base_currency,
                    quote_currency=excluded.quote_currency,
                    display_name=excluded.display_name,
                    market_status=excluded.market_status,
                    trading_disabled=excluded.trading_disabled,
                    is_eligible=excluded.is_eligible,
                    last_seen_at=excluded.last_seen_at
            """, rows)


def record_failure(conn: psycopg.Connection, message: str) -> None:
    with conn.transaction():
        conn.execute("""
            UPDATE bootstrap_state SET state='partial', last_attempt_at=%s, last_error=%s
            WHERE id=1 AND state <> 'complete'
        """, (utc_now(), message[:500]))


def bootstrap(conn: psycopg.Connection) -> int:
    state = conn.execute("SELECT state, target_count FROM bootstrap_state WHERE id=1").fetchone()
    if state is None:
        raise RuntimeError("bootstrap_state row is missing; initialize PostgreSQL with database/schema.sql first")
    if state["state"] == "complete":
        count = conn.execute("SELECT count(*) FROM tracked_products").fetchone()["count"]
        print(f"Bootstrap already completed; {count} tracked products currently remain.")
        return 0
    try:
        catalog = fetch_catalog()
        save_catalog(conn, catalog)
    except RuntimeError as exc:
        record_failure(conn, str(exc))
        raise

    target = state["target_count"]
    existing = conn.execute("SELECT count(*) FROM tracked_products").fetchone()["count"]
    needed = max(0, target - existing)
    inserted, checked, rejected = 0, 0, []
    for market in ordered_candidates(catalog):
        if inserted >= needed or checked >= 50:
            break
        product_id = market["id"].upper()
        if conn.execute("SELECT 1 FROM tracked_products WHERE coinbase_product_id=%s", (product_id,)).fetchone():
            continue
        checked += 1
        try:
            price, trade_time = parse_ticker(product_id)
        except RuntimeError as exc:
            rejected.append(f"{product_id}: {exc}")
            continue
        now = utc_now()
        base, quote_currency = market["base_currency"].upper(), market["quote_currency"].upper()
        with conn.transaction():
            row = conn.execute("""
                INSERT INTO tracked_products (coinbase_product_id, base_currency, quote_currency, name, source)
                VALUES (%s,%s,%s,%s,'bootstrap')
                ON CONFLICT (coinbase_product_id) DO NOTHING
                RETURNING id
            """, (product_id, base, quote_currency, str(market.get("base_name") or base))).fetchone()
            if row:
                conn.execute("""
                    INSERT INTO latest_quotes (
                        product_id, price, quote_currency, retrieved_at,
                        provider_trade_time, last_attempt_at
                    ) VALUES (%s,%s,%s,%s,%s,%s)
                """, (row["id"], price, quote_currency, now, trade_time, now))
                inserted += 1

    total = conn.execute("SELECT count(*) FROM tracked_products").fetchone()["count"]
    complete = total >= target
    error_text = None if complete else "; ".join(rejected[:8]) or "Fewer than 10 eligible Coinbase markets were available"
    now = utc_now()
    with conn.transaction():
        conn.execute("""
            UPDATE bootstrap_state
            SET state=%s, seeded_count=%s, last_attempt_at=%s, completed_at=%s, last_error=%s
            WHERE id=1
        """, ("complete" if complete else "partial", total, now, now if complete else None,
              error_text[:500] if error_text else None))
    print(f"Coinbase catalog contains {len(catalog)} products.")
    print(f"Added {inserted} tracked markets with verified ticker prices; {total}/{target} total tracked.")
    if rejected:
        print("Markets skipped because ticker verification failed:")
        for reason in rejected[:10]:
            print(f"  - {reason}")
    if not complete:
        if checked >= 50:
            print("Stopped after checking 50 ticker candidates to keep bootstrap bounded.")
        print("Bootstrap is partial. Re-run this command after connectivity/market availability is restored.")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
                        help="PostgreSQL URL (default: DATABASE_URL or local Terraform default)")
    args = parser.parse_args()
    try:
        with psycopg.connect(args.database_url, autocommit=True, row_factory=dict_row) as conn:
            return bootstrap(conn)
    except (OSError, psycopg.Error, RuntimeError) as exc:
        print(f"PostgreSQL bootstrap failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
