"""Ports used by the price refresh use case."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class TrackedProduct:
    id: int
    coinbase_product_id: str
    quote_currency: str
    is_active: bool


@dataclass(frozen=True)
class PriceQuote:
    price: Decimal
    quote_currency: str
    retrieved_at: datetime
    provider_trade_time: datetime | None = None


class ProductRepository(Protocol):
    def active_products(self) -> list[TrackedProduct]: ...


class QuoteRepository(Protocol):
    def save_quote(self, product: TrackedProduct, quote: PriceQuote) -> None: ...

    def record_failure(self, product: TrackedProduct, attempted_at: datetime, category: str) -> None: ...


class PriceProvider(Protocol):
    def get_price(self, product_id: str, quote_currency: str) -> PriceQuote: ...
