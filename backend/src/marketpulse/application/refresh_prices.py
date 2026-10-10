"""Application use case for refreshing all active tracked products."""

from dataclasses import dataclass
from datetime import datetime, timezone

from marketpulse.domain.errors import ProviderFailure
from marketpulse.domain.ports import PriceProvider, ProductRepository, QuoteRepository


@dataclass(frozen=True)
class RefreshResult:
    product_id: str
    outcome: str
    error_category: str | None = None


class RefreshPrices:
    def __init__(self, products: ProductRepository, quotes: QuoteRepository, provider: PriceProvider):
        self._products = products
        self._quotes = quotes
        self._provider = provider

    def execute(self) -> list[RefreshResult]:
        results = []
        for product in self._products.active_products():
            try:
                quote = self._provider.get_price(product.coinbase_product_id, product.quote_currency)
            except ProviderFailure as exc:
                self._quotes.record_failure(product, datetime.now(timezone.utc), exc.category)
                results.append(RefreshResult(product.coinbase_product_id, "failed", exc.category))
                continue
            self._quotes.save_quote(product, quote)
            results.append(RefreshResult(product.coinbase_product_id, "updated"))
        return results
