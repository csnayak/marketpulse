# Spec 03 — Tracked product CRUD and persistence

**Status:** Ready for implementation on the finalized Option B stack  
**Priority:** P0  
**Depends on:** 01 Technical foundation and 02 Coinbase catalog integration  
**Enables:** 04 price refresh and 05 dashboard

## Objective

On first run, initialize 10 supported Coinbase crypto spot markets, then let the single local user inspect, edit, activate/deactivate, add, and delete the application-owned tracked records. Product records must survive application and container restarts.

## User stories

- As a user, I can add a market with a friendly name and Coinbase product ID.
- As a user, I can inspect all saved markets and their current active state.
- As a user, I can correct a name, market ID, or active state.
- As a user, I can remove a market I no longer follow.

## Scope and rules

### Initial 10-product bootstrap

- When the product table is empty and has never completed bootstrap, fetch Coinbase's product catalog and seed exactly 10 eligible crypto spot markets.
- Eligibility: spot market, online/tradable for public market data, quote currency `USD`, and a product ID accepted by the selected price endpoint. Exclude derivatives and fiat-to-fiat pairs.
- Use a configurable preferred ordering of common markets (initial defaults may include `BTC-USD`, `ETH-USD`, `SOL-USD`, `XRP-USD`, `ADA-USD`, `DOGE-USD`, `AVAX-USD`, `LINK-USD`, `LTC-USD`, `BCH-USD`). These IDs are preferences only: verify each against the live Coinbase catalog. Fill missing slots from remaining eligible products sorted by canonical product ID. Never select based on unstable API response order.
- Coinbase metadata supplies product ID and base/quote currency; initialize the editable name to the base currency symbol (for example `BTC`) and retain Coinbase display name in the catalog cache. The resulting product is an ordinary application record and follows the same CRUD rules as user-created products.
- Bootstrap must be idempotent and run only for a genuinely new/empty product store. It must never restore a product the user deliberately deleted, duplicate products, or overwrite user-edited names. Persist a bootstrap-completed marker, including partial/error status, separately from product rows.
- If Coinbase is unreachable or fewer than 10 eligible products are returned, do not fabricate records or block startup/CRUD. Seed any eligible products available, report how many were seeded and why fewer than 10, and provide an explicit retry action. The completion marker must permit retry until 10 have been seeded, while protecting deliberate user deletions after bootstrap is complete.
- Once bootstrap reaches 10, later catalog refreshes do not auto-add or auto-delete tracked records. A user adds replacements through catalog search/selection.


### Product record

Persist at minimum:

| Field | Rule |
|---|---|
| `id` | Application generated, immutable primary key |
| `name` | Required, trimmed, 1–80 Unicode characters |
| `coinbase_product_id` | Required, trimmed, canonical uppercase `BASE-QUOTE` form; max 32 characters |
| `quote_currency` | Derived from product ID where possible; otherwise required and must match the suffix |
| `is_active` | Boolean, defaults to `true` |
| `created_at`, `updated_at` | UTC timestamps; `updated_at` changes only on successful mutation |

Add a unique database constraint on canonical `coinbase_product_id` (or on the product ID plus quote currency if the selected Coinbase model permits the same ID to imply only one quote). Application validation improves error messages, but the database constraint is the final concurrency-safe guard. The first release stores one record per market; aliases are not supported.

The product CRUD layer validates syntax and invariants. Coinbase integration is responsible for verifying that the market actually exists. Product creation should not depend on external network availability: allow syntactically valid records to be saved; show an unavailable/not-fetched price state until a provider refresh verifies it. An implementation may add optional market verification, but it must not make CRUD unavailable during a Coinbase outage.

### Mutations
- Create: all user fields required except `is_active`; default active.
- Update: support partial updates or full replacement consistently; omitted fields must not be cleared accidentally. Reject empty patch bodies.
- Delete: permanent in v1. Delete the associated latest quote/status atomically or by cascade. No historical record is retained.
- Deactivation: retain the record and its last quote, but exclude it from automatic and manual bulk refresh. Its quote age continues to advance and the UI must mark it inactive.
- Re-activation: include it in the next refresh cycle; do not present its retained quote as fresh.

### Validation and errors
- Normalize whitespace around name and ID. Uppercase ID using locale-independent rules.
- Reject malformed IDs, missing name/ID, overlength values, and quote currency mismatch with field-level errors.
- Duplicate ID: `409 Conflict`, stable code `product_already_exists`.
- Missing record: `404 Not Found`, stable code `product_not_found`.
- Invalid input: `422 Unprocessable Entity`, stable code `validation_error`, with `field_errors` map.
- Do not expose SQL/database exceptions to the caller.
- Create/update must be atomic: validation or persistence failure leaves the old state untouched.

## Coinbase catalog API

Expose discovery separately from tracked product CRUD:

- `GET /api/v1/coinbase/products?search={query}` — return eligible Coinbase spot products, with product ID, base currency, quote currency, and display name; omit already-tracked markets or mark them `already_tracked` so the UI can disable adding them.
- `GET /api/v1/bootstrap` — return bootstrap state (`not_started`, `complete`, or `partial`), eligible/seeded counts, and safe last failure category.
- `POST /api/v1/bootstrap/retry` — explicitly retry bootstrap when fewer than 10 products were seeded. Return seeded count and bootstrap status. This operation is idempotent and must not overwrite user edits.

The catalog result is a provider-backed view/cache, not a second user-editable CRUD table. Users maintain products through `/api/v1/products`.

## API contract

Unless the selected framework has a strong equivalent convention, expose:

- `GET /api/v1/products` — return all products sorted by name then ID; include quote/status fields when available, otherwise `null` and `not_fetched`.
- `POST /api/v1/products` — accept `{name, coinbase_product_id, quote_currency?, is_active?}`; return `201` and the created representation.
- `GET /api/v1/products/{id}` — return one product or `404`.
- `PATCH /api/v1/products/{id}` — mutate supplied editable fields and return the updated representation.
- `DELETE /api/v1/products/{id}` — return `204`; repeated delete returns `404`.

Example create request:

```json
{"name":"Bitcoin","coinbase_product_id":"BTC-USD","is_active":true}
```

Example product representation:

```json
{
  "id":"generated-id",
  "name":"Bitcoin",
  "coinbase_product_id":"BTC-USD",
  "quote_currency":"USD",
  "is_active":true,
  "created_at":"2026-10-09T10:00:00Z",
  "updated_at":"2026-10-09T10:00:00Z",
  "price":null,
  "price_as_of":null,
  "price_status":"not_fetched"
}
```

Use a consistent error envelope such as `{ "error": { "code": "...", "message": "...", "field_errors": {} } }`.

## Persistence and schema setup

The PostgreSQL schema is defined in `database/schema.sql` and initialized by Terraform through the PostgreSQL container's first-run SQL hook. Seed initial markets with `database/scripts/bootstrap_db.py`. See [`database/README.md`](../database/README.md) for setup and schema behavior.


- PostgreSQL is the selected store for local and deployed environments. Terraform mounts `database/schema.sql` for initialization of a new database volume; seed initial products with the bootstrap utility.
- Enforce ID uniqueness, required fields, and boolean validity in schema as well as service validation.
- Persist PostgreSQL data in a Terraform-managed Docker volume locally; production deployments must use durable PostgreSQL storage and backups.
- Connection and transaction handling must be safe for the selected server concurrency model.

## Acceptance criteria

1. First run with a mocked catalog containing at least 10 eligible markets creates exactly 10 tracked product records.
2. Preferred product IDs are selected when eligible; missing preferences are filled deterministically from sorted eligible catalog entries.
3. Derivatives, offline products, fiat-only pairs, and unsupported products are excluded.
4. Re-running startup/bootstrap does not duplicate products, overwrite display names, or restore a user-deleted record after bootstrap is complete.
5. Catalog failure or fewer than 10 eligible products does not block app startup/CRUD; status reports the partial count and permits retry.
6. A user can search the Coinbase catalog and add a new eligible product; already tracked markets cannot be added twice.
7. Deleting a tracked product only deletes the local record/current quote, not Coinbase catalog data.

1. A new database returns an empty product list.
2. A valid product can be created and immediately appears in list/read responses.
3. Name and product ID normalization is deterministic.
4. Invalid fields return actionable field-specific errors and create no row.
5. A duplicate market is rejected, including two near-simultaneous creates.
6. Updates change only intended fields and invalid updates preserve the old record.
7. Delete removes the product and latest quote; unknown IDs return 404.
8. Inactive products remain readable and are excluded from the refresh candidate query.
9. Product data survives app restart when the same persistent database is mounted.
10. Schema setup on an empty database succeeds and can run repeatedly without corrupting data.

## Required tests

- Unit: normalization, field limits, ID format, quote suffix consistency, partial update behavior.
- Integration: create/list/read/update/delete, duplicate constraint, invalid requests, cascade behavior, restart persistence, schema setup.
- Concurrency: unique constraint under concurrent create attempts (where test tooling permits).
