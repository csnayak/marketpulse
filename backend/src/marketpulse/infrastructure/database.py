"""SQLAlchemy implementations for the existing PostgreSQL schema."""

import os
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from marketpulse.domain.ports import PriceQuote, TrackedProduct


def make_engine() -> Engine:
    database_url = os.environ.get("DATABASE_URL", "postgresql://marketpulse:marketpulse_local@localhost:5432/marketpulse")
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(database_url, pool_pre_ping=True)


class PostgresProductRepository:
    def __init__(self, engine: Engine):
        self._engine = engine

    def active_products(self) -> list[TrackedProduct]:
        query = text("""SELECT id, coinbase_product_id, quote_currency, is_active
                       FROM tracked_products WHERE is_active = TRUE
                       ORDER BY id""")
        with self._engine.connect() as connection:
            rows = connection.execute(query).mappings().all()
        return [TrackedProduct(**row) for row in rows]

class PostgresQuoteRepository:
    def __init__(self, engine: Engine):
        self._engine = engine

    def save_quote(self, product: TrackedProduct, quote: PriceQuote) -> None:
        statement = text("""INSERT INTO latest_quotes
            (product_id, price, quote_currency, retrieved_at, provider_trade_time, last_attempt_at, last_error_category)
            VALUES (:id, :price, :currency, :retrieved, :trade_time, :retrieved, NULL)
            ON CONFLICT (product_id) DO UPDATE SET price = EXCLUDED.price,
              quote_currency = EXCLUDED.quote_currency, retrieved_at = EXCLUDED.retrieved_at,
              provider_trade_time = EXCLUDED.provider_trade_time,
              last_attempt_at = EXCLUDED.last_attempt_at, last_error_category = NULL""")
        with self._engine.begin() as connection:
            connection.execute(statement, {"id": product.id, "price": quote.price,
                "currency": quote.quote_currency, "retrieved": quote.retrieved_at,
                "trade_time": quote.provider_trade_time})

    def record_failure(self, product: TrackedProduct, attempted_at: datetime, category: str) -> None:
        statement = text("""INSERT INTO latest_quotes (product_id, quote_currency, last_attempt_at, last_error_category)
            VALUES (:id, :currency, :attempted, :category)
            ON CONFLICT (product_id) DO UPDATE SET last_attempt_at = EXCLUDED.last_attempt_at,
              last_error_category = EXCLUDED.last_error_category""")
        with self._engine.begin() as connection:
            connection.execute(statement, {"id": product.id, "currency": product.quote_currency,
                "attempted": attempted_at, "category": category})
