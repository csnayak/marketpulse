"""Single-process scheduled worker; run exactly one replica."""

import logging
import os
import signal
import time

from marketpulse.application.refresh_prices import RefreshPrices
from marketpulse.infrastructure.coinbase import CoinbasePriceProvider
from marketpulse.infrastructure.database import PostgresProductRepository, PostgresQuoteRepository, make_engine


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    interval = int(os.getenv("PRICE_REFRESH_INTERVAL_SECONDS", "60"))
    if interval < 15:
        raise ValueError("PRICE_REFRESH_INTERVAL_SECONDS must be at least 15")

    engine = make_engine()
    products = PostgresProductRepository(engine)
    quotes = PostgresQuoteRepository(engine)
    provider = CoinbasePriceProvider(float(os.getenv("COINBASE_REQUEST_TIMEOUT_SECONDS", "8")))
    stop = False

    def request_stop(*_args: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        while not stop:
            started = time.monotonic()
            try:
                results = RefreshPrices(products, quotes, provider).execute()
                logging.info("Coinbase refresh complete", extra={"updated": sum(r.outcome == "updated" for r in results),
                    "failed": sum(r.outcome == "failed" for r in results)})
            except Exception:
                logging.exception("Coinbase refresh cycle failed")
            remaining = max(0, interval - (time.monotonic() - started))
            deadline = time.monotonic() + remaining
            while not stop and time.monotonic() < deadline:
                time.sleep(min(1, deadline - time.monotonic()))
    finally:
        provider.close()
        engine.dispose()


if __name__ == "__main__":
    main()
