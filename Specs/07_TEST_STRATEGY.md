# Spec 07 — Test strategy and acceptance suite

**Status:** Required throughout implementation  
**Priority:** P0  
**Applies to:** Specs 01–06; begin with unit and database schema setup tests in spec 01 and expand coverage as each component lands

## Objective

Prove CRUD correctness, exact quote handling, refresh reliability, user workflows, and Docker persistence without making the default test suite depend on Coinbase or other live services.

## Test layers

### Unit tests
Run quickly with no database/network/UI browser. Cover:
- product normalization and validation;
- Coinbase catalog filtering, deterministic top-10 selection, and bootstrap idempotency;
- decimal price parsing and invalid values;
- provider response parsing and failure classification;
- quote freshness with an injectable clock;
- active-product selection and refresh outcome aggregation;
- interval and timeout configuration validation.

### Service/API integration tests
Use an isolated temporary database and mocked provider/HTTP transport. Cover CRUD persistence, transaction semantics, duplicate constraints, schema setup, refresh updates, partial failures, health/readiness behavior, and restart/reopen durability.

### UI component and end-to-end tests
Use deterministic API fixtures. Verify visible states and complete user workflows. Avoid real sleeps by controlling timers/clock. Keep at least one keyboard-only journey covering create, edit, refresh, and delete confirmation.

### Docker acceptance checks
Build and run the documented Terraform deployment, probe health, exercise one CRUD operation, restart and verify volume persistence, then check logs/shutdown. The regular automated CI may use a dedicated test service/command; document the canonical command.

### Optional live smoke check
Provide an opt-in command/procedure for one known supported Coinbase market. It must be excluded from ordinary unit/integration CI, clearly report that it requires network access, and never make a live trade or authenticate with trading permissions.

## Test data and determinism

- Use a fake `CoinbasePriceProvider` returning fixed decimal strings, delayed responses, and typed failures.
- Use fixed UTC timestamps or an injected clock. No assertions based on current wall time without tolerance.
- Ensure tests verify exact price strings/decimal values, not rounded floats.
- Reset database state between tests; tests must not share the developer's local data volume.
- Cover API error envelopes and stable codes, not implementation-specific stack text.

## Required acceptance matrix

| Area | Case | Expected result |
|---|---|---|
| Bootstrap | New install with 10+ eligible Coinbase markets | Exactly 10 deterministic tracked products are created |
| Bootstrap | Preferred market missing | Fill slot from sorted eligible catalog without duplicate |
| Bootstrap | Catalog outage or fewer than 10 eligible markets | App starts, partial status is visible, retry remains possible |
| Bootstrap | Repeated startup after user delete/edit | Does not restore deleted product or overwrite edited name |
| Catalog | Search and add | Eligible untracked market can be added; tracked one cannot be duplicated |
| CRUD | Empty list | Empty collection and UI empty state after explicit removals |
| CRUD | Create valid product | `201`, persisted, listed |
| CRUD | Invalid fields | Field-level validation, no persistence |
| CRUD | Duplicate market | `409`, one record only |
| CRUD | Update valid/invalid | Valid mutation persists; invalid mutation is atomic |
| CRUD | Read/delete unknown ID | `404` stable error |
| CRUD | Delete existing | Product and latest quote removed |
| Persistence | Restart | Product/latest quote available after reopen; price freshness recalculated |
| Provider | Valid decimal response | Exact positive price and currency returned |
| Provider | Empty/malformed/nonpositive | Safe `unavailable`/invalid response; never zero price |
| Provider | 404/429/timeout/5xx | Correct error category and bounded retry behavior |
| Provider | Previous quote then failure | Last quote retained; error/age state visible |
| Refresh | Mixed success/failure | Successful rows update; failed row reports error |
| Refresh | Inactive product | No provider call |
| Refresh | Overlap | No unbounded duplicate work |
| Refresh | Stale threshold | Status changes at configured threshold using fake clock |
| UI | CRUD journey | Create/edit/delete works; delete cancel does nothing |
| UI | Manual refresh | Pending/result feedback and refreshed row data |
| UI | Keyboard | Core actions available and focus remains understandable |
| Docker | Healthy startup | Terraform-created container health check passes |
| Docker | Provider outage | CRUD service remains available |
| Docker | Volume persistence | Data survives container recreation |

## Quality gates

- Default test suite performs no external network requests.
- No flaky timing-based tests; use fake clock/scheduler.
- Test names describe behavior, not internal method names.
- Test failures should include useful context while avoiding secrets and full provider payloads.
- Any deferred acceptance case is recorded with reason and owner before release.

## Definition of test completion

1. Unit, integration, and UI suites are documented and pass in a clean environment.
2. Docker acceptance workflow is reproducible from README.
3. Coverage includes success, validation, boundaries, partial failure, and persistence paths.
4. Optional live smoke test is clearly separated from deterministic CI.
