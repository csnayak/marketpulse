# Spec 04 — Periodic and manual price refresh

**Status:** Initial worker implemented; API/manual trigger and UI wiring remain  
**Priority:** P0  
**Depends on:** 02 Coinbase price integration and 03 tracked products  
**Enables:** Dashboard current/stale/unavailable states

## Objective

Use one refresh service for scheduled and user-requested updates. Refresh active tracked products in the background, preserve per-market outcomes, prevent overlapping work, and make price freshness explicit.

## User stories

- As a user, I see prices update without leaving the dashboard open.
- As a user, I can request a refresh immediately.
- As a user, I can distinguish a failed or old price from a fresh one.

## Refresh policy

- Run an initial refresh after persistence and application services are ready.
- Run exactly one server-side worker, with an initial refresh at startup and subsequent cycles every 60 seconds by default. The interval is configurable, with a minimum of 15 seconds. Startup validation must reject invalid intervals rather than silently creating a tight loop.
- Refresh active products only. Empty product set is a successful no-op.
- Use the same application service for scheduled and manual refresh; manual refresh must not bypass provider limits, parsing, or persistence rules.
- Use a single scheduler per application process. For the supported single-instance Terraform-managed Docker deployment, process-local coordination is sufficient. Document that multiple replicas require a distributed lock/leader election before scale-out.
- Prevent overlapping refresh runs. If a run is in progress, manual trigger returns `already_running` (or joins the in-flight run) and does not queue unbounded duplicate work.
- Process product outcomes independently. One bad/unsupported market must not block successful updates for other products.
- The worker reads active products from PostgreSQL and persists each successful latest quote to `latest_quotes`; the browser never calls Coinbase directly.
- Apply global concurrency cap from Coinbase adapter config. Do not create one thread/task per product without a bounded pool.
- On shutdown, stop new cycles and allow in-flight requests a bounded grace period before closing persistence/client resources.

## Status model

Represent quote state with the following rule order:

1. `not_fetched`: no successful quote and no completed provider error yet.
2. `unavailable`: no successful quote exists and the most recent attempt failed or market is unsupported.
3. `current`: a successful quote exists and its age is less than or equal to `PRICE_STALE_AFTER_SECONDS` (default 180).
4. `stale`: a successful quote exists but age exceeds the stale threshold, whether or not the latest attempt failed.

Keep latest attempt error separately from quote status. Include `last_attempt_at`, `last_success_at`/`price_as_of`, and safe error category/message where appropriate. If an error occurs while a quote remains within the freshness window, the displayed state may remain `current` but show a refresh warning; once older than threshold it must be `stale`. Inactive is an independent product state and must be shown in addition to quote freshness.

## Manual refresh API

`POST /api/v1/prices/refresh` refreshes all active products. Suggested response:

```json
{
  "status":"completed",
  "started_at":"2026-10-09T10:00:00Z",
  "completed_at":"2026-10-09T10:00:02Z",
  "results":[
    {"product_id":"BTC-USD","outcome":"updated","price":"65000.12","quote_currency":"USD","price_as_of":"2026-10-09T10:00:02Z"},
    {"product_id":"ETH-USD","outcome":"failed","error_code":"provider_timeout"}
  ]
}
```

For small lists, the endpoint may wait for completion with a strict server deadline. If refresh is asynchronous, return `202 Accepted` and provide a job/status resource. Choose one approach and document it; the UI must not imply completion while work remains. Duplicate in-progress request returns `409` with stable code `refresh_in_progress` (or return the active run ID if joining it). Per-product outcomes must never expose raw provider payloads.

## Scheduling and UI refresh

- The browser may poll `GET /api/v1/products` every 10–30 seconds (default 15) while visible; pause or slow polling when the tab is hidden.
- Server refresh continues regardless of open browser tabs.
- A GUI “Refresh now” button calls the manual endpoint, has an in-progress state, and reports completion/failure. Disable repeated clicks while the request is active.
- Poll results or list state after the refresh completes. Keep each product's independent status visible.

## Observability

Log one cycle start/end, duration, active product count, success/failure counts, and safe failure category. Avoid logging every full provider body or creating high-cardinality labels in metrics. Include product ID in structured logs when useful. Expose scheduler state through health/readiness only if it materially affects service readiness; Coinbase outage must not make CRUD readiness fail.

## Acceptance criteria

1. Startup triggers one refresh once the app is ready.
2. Scheduler runs at configured interval and honors minimum/invalid-value validation.
3. Inactive products are never sent to provider during bulk refresh.
4. A successful result updates exact price and retrieval timestamp.
5. One failed product does not prevent the other products from updating.
6. A failed attempt preserves last successful price and reports an error category.
7. Freshness transitions to stale based on an injectable clock and configured threshold.
8. Concurrent scheduled/manual requests cannot overlap the same run or generate an unbounded queue.
9. Manual response clearly describes run status and per-product results.
10. Shutdown prevents another scheduled cycle and handles in-flight calls within a bounded grace period.

## Current implementation

The initial backend slice is in `backend/src/marketpulse`: `domain/ports.py` defines product, quote, and provider contracts; `application/refresh_prices.py` owns the refresh use case; infrastructure modules implement the Coinbase ticker adapter and PostgreSQL repository; and `worker_main.py` runs one startup refresh followed by a configurable interval (60 seconds by default). Terraform runs one worker container. The FastAPI API, manual refresh route, and React UI are subsequent implementation work.

## Required tests

- Unit: candidate selection, status calculation with fake clock, outcome aggregation, interval configuration.
- Integration: scheduled cycle, manual trigger, no-op empty list, partial success, duplicate run behavior, persisted state after refresh.
- Avoid wall-clock sleeps: inject scheduler/clock abstractions or invoke scheduled callback directly.
