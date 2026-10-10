"""Coinbase public Exchange ticker adapter."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx

from marketpulse.domain.errors import ProviderFailure
from marketpulse.domain.ports import PriceQuote


class CoinbasePriceProvider:
    def __init__(self, timeout_seconds: float = 8.0):
        self._client = httpx.Client(base_url="https://api.exchange.coinbase.com", timeout=timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def get_price(self, product_id: str, quote_currency: str) -> PriceQuote:
        try:
            response = self._client.get(f"/products/{product_id}/ticker")
            response.raise_for_status()
            payload = response.json()
            price = Decimal(payload["price"])
            if not price.is_finite() or price <= 0:
                raise ValueError("invalid price")
            trade_time = datetime.fromisoformat(payload["time"].replace("Z", "+00:00"))
            return PriceQuote(price, quote_currency, datetime.now(timezone.utc), trade_time)
        except httpx.TimeoutException as exc:
            raise ProviderFailure("provider_timeout") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            category = "provider_rate_limited" if status == 429 else "provider_market_unavailable"
            raise ProviderFailure(category) from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError, InvalidOperation) as exc:
            raise ProviderFailure("provider_error") from exc
