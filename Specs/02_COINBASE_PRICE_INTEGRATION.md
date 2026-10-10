# Spec 02 — Coinbase spot price integration

**Status:** Price ticker adapter implemented; catalog adapter and integration coverage remain  
**Priority:** P0  
**Depends on:** 01 Technical foundation  
**Enables:** Refresh orchestration and price display

## Objective

Implement a small Coinbase market-data adapter that retrieves a defensible current spot price for a configured product ID, validates the provider response, and exposes typed success/failure results to application code.

## Meaning of “price”

For v1, show Coinbase's **last traded price** for the specified spot product, not an average, executable quote, or guaranteed mark. The GUI must label it “Last price” and identify Coinbase as the source. A refresh timestamp is the time the application successfully retrieved/accepted the value; do not imply this is the exchange trade timestamp unless the chosen endpoint provides and the application displays that separately.

## Endpoint decision and source

For the initial implementation, use Coinbase Exchange public market-data REST endpoints:

- Product discovery: `GET https://api.exchange.coinbase.com/products`. Filter `status == "online"`, quote currency `USD`, and `trading_disabled != true`; exclude fiat base currencies. Coinbase documents product IDs, base/quote currencies, display names, and status in its [Get all known trading pairs reference](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-all-known-trading-pairs).
- Latest price: `GET https://api.exchange.coinbase.com/products/{product_id}/ticker`. Use its decimal-string `price` as the last traded price and `time` as provider trade time. Coinbase documents this response in [Get product ticker](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-ticker).

These are public GET market-data calls and the bootstrap script uses no API key. Confirm endpoint reachability in the target deployment when first running the script. Do not mix Exchange product IDs with Advanced Trade API product identifiers. Keep HTTP transport injectable for tests and the production host fixed to Coinbase.

## Product catalog discovery

The integration exposes the product list and ticker operations behind a Coinbase adapter. The selected endpoints and response fields are documented above. The catalog operation returns product ID, base currency, quote currency, display name, and status; market eligibility is derived from those fields and Coinbase trading status. Do not infer market availability from a guessed product-ID pattern.

Catalog behavior:
- Fetch and validate the provider catalog using a bounded timeout and safe error handling.
- Filter to eligible online USD crypto markets supported by the selected ticker endpoint; reject known fiat base currencies and non-spot products when product type is provided.
- Return a normalized, deterministically sorted list; never rely on provider array order.
- Cache catalog metadata for a short configurable duration (default 15 minutes) to support UI search without a Coinbase request on every keystroke. A catalog outage should return a safe stale-cache result if available; otherwise report provider unavailable.
- Catalog metadata is not the user-maintained tracked product list. Refreshing catalog metadata must not mutate tracked product records.

## Adapter contract

Application code depends on a provider interface, not raw HTTP. Suggested operation:

`get_last_price(product_id) -> QuoteResult`

Success result contains:
- canonical `product_id`
- positive decimal `price` (string or arbitrary precision decimal)
- `quote_currency`
- optional provider `trade_time` if the endpoint supplies it
- `retrieved_at` in UTC, assigned by application after a valid response
- source label, e.g. `Coinbase`

Failure result contains a stable category (`not_found`, `rate_limited`, `timeout`, `unavailable`, `invalid_response`, `unauthorized`, or `unknown`) and safe user-facing message. Do not leak raw response bodies, credentials, or stack traces.

## HTTP and parsing behavior

- Use HTTPS, bounded connect/read timeout (default total budget 5 seconds), JSON accept header, and an identifiable user agent if practical.
- Never use floating-point representation for a price. Parse exact decimal strings. Reject empty, malformed, non-finite, zero, or negative prices.
- Confirm product ID in response when available; reject mismatches.
- For latest-trades endpoint, select the newest valid trade according to provider ordering or explicit timestamp comparison; do not trust array ordering without documenting/verifying it. Empty trade list is a valid provider result with no quote, not a zero price.
- Distinguish 404/unsupported market from provider outage. Treat 429 as rate limiting. Retry only bounded transient cases (timeouts, selected 5xx) with exponential backoff and jitter; respect `Retry-After` if present. Do not retry ordinary 4xx or invalid payloads.
- Limit concurrent requests globally and per refresh batch. Do not call a provider once per UI render.
- Enforce response size/time limits and handle malformed JSON safely.
- If a refresh fails, do not overwrite a previously successful price with zero/null. Report failure separately and let status policy decide whether retained data is stale or unavailable.

## Quote persistence contract

Persist at most the latest quote per product in v1:

| Field | Rule |
|---|---|
| `product_id` | FK to product, unique per product |
| `price` | Exact decimal storage/string; positive |
| `quote_currency` | Required |
| `retrieved_at` | UTC timestamp of successful retrieval |
| `provider_trade_time` | Optional UTC timestamp if source provides it |
| `last_error_category` | Optional, separate from last-success quote |
| `last_attempt_at` | Optional UTC timestamp, updated for each attempt |

A successful fetch atomically replaces the last quote and clears current error category. A failed fetch updates attempt/error metadata but preserves last quote. Do not build historical price retention in this story.

## Configuration

- `COINBASE_BASE_URL` (normally fixed to the verified official API host; allow test override only if safe).
- `COINBASE_REQUEST_TIMEOUT_SECONDS` default `5`.
- `COINBASE_MAX_CONCURRENCY` default `3` (tune based on documented API limits).
- `COINBASE_MAX_RETRIES` default `2` for retryable errors only.
- `PRICE_STALE_AFTER_SECONDS` default `180`.

Validate configuration at startup and log effective non-secret settings.

## Acceptance criteria

1. Catalog adapter returns normalized market metadata and excludes non-spot/offline/fiat-only entries.
2. Catalog output order is deterministic regardless of provider response ordering.
3. Catalog timeout/error is distinct from an empty valid catalog response.
4. Catalog cache prevents per-keystroke upstream calls and can serve cached data during provider outage.
5. Price adapter returns exact decimal last-price results for each tracked Coinbase product.
6. A valid mocked Coinbase response produces exact price and correct quote currency.
7. A value with many decimal places retains its exact value through parsing and persistence.
8. Empty/malformed/non-positive values and mismatched product data are rejected.
9. 404, 429, timeout, 5xx, invalid JSON, and empty market data map to distinct safe result categories.
10. Transient errors retry only within the configured bounded policy; non-retryable errors are not retried.
11. Existing quote is preserved when a later fetch fails.
12. Multiple product refresh requests obey the concurrency limit.
13. Default tests use a fake HTTP transport and never depend on public network state.
14. Endpoint semantics, authentication requirements, and source URL are documented in README.

## Required tests

- Unit: decimal parser, price response/product consistency, newest trade selection, catalog filtering/sorting, error mapping, retry classification.
- Adapter integration: mocked HTTP 200/404/429/5xx/timeout/bad JSON/empty response; verify URL encoding and request timeout.
- Persistence integration: atomic success update, failure metadata update without quote loss.
- Optional manual smoke test: one known product against Coinbase, excluded from default CI.
