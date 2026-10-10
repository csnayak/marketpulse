# MarketPulse technical guide

**Purpose:** Current architecture, implementation status, and the next build steps. Feature behavior lives in the linked specs; this guide does not repeat their full acceptance criteria.

## Current status

- **Selected stack:** React + TypeScript + Vite, FastAPI + Pydantic, PostgreSQL + SQLAlchemy/psycopg.
- **Implemented:** PostgreSQL schema initialized by the Terraform-managed container; Coinbase market seeding script; one Coinbase price worker; FastAPI health and product CRUD routes; a simple React product CRUD screen.
- **Next:** Run the stack locally and refine the UI from feedback; add catalog search and manual price refresh afterward.
- **Not implemented:** Coinbase catalog API and manual refresh endpoint.

## Architecture

Use a small modular monolith. Keep UI, HTTP API, application rules, domain types, and infrastructure in separate components.

The flow is: React UI → FastAPI API → application use cases → domain ports → PostgreSQL repositories and Coinbase adapter. The scheduled worker calls the same refresh use case as the API.

- **UI:** Render data and collect user actions. Use a typed API client; never call PostgreSQL or Coinbase.
- **Presentation:** FastAPI routes and Pydantic schemas. Handle HTTP validation and response mapping only.
- **Application:** Product, dashboard, and refresh use cases. Coordinate domain ports and transaction boundaries.
- **Domain:** Product/quote rules and interfaces. No FastAPI, SQLAlchemy, HTTPX, or Coinbase response types.
- **Infrastructure:** SQLAlchemy repositories, Coinbase HTTPX adapter, scheduler, and dependency wiring.

Apply SOLID at this scale: one responsibility per component, small focused interfaces, depend on abstractions, and inject adapters at the composition root. Avoid layers or abstractions with no current use.

## Data and API contract

PostgreSQL is the source of truth. The tracked_products table contains the saved market list; latest_quotes stores one current decimal quote and last-attempt state per product. Use Python Decimal and PostgreSQL NUMERIC; return prices to the browser as strings. Failed requests preserve the last successful quote.

Use versioned REST/JSON routes:

| Method | Route | Purpose |
|---|---|---|
| GET | /api/v1/products | List products with latest quote and freshness state. |
| POST | /api/v1/products | Add a tracked product. |
| GET | /api/v1/products/{id} | Read one product. |
| PATCH | /api/v1/products/{id} | Update editable product fields. |
| DELETE | /api/v1/products/{id} | Delete product and current quote. |
| GET | /api/v1/coinbase/products?search= | Search eligible, untracked Coinbase markets. |
| GET | /api/v1/bootstrap | Read initial seed status. |
| POST | /api/v1/bootstrap/retry | Retry incomplete initial seed. |
| POST | /api/v1/prices/refresh | Request an immediate refresh. |
| GET | /api/v1/health/live | Process liveness. |
| GET | /api/v1/health/ready | API and PostgreSQL readiness. |

The browser reads saved quotes through the product API and polls every 15 seconds while visible. The independent worker polls Coinbase every 60 seconds. Manual and scheduled refresh use the same application use case.

## Frontend shape

Use a feature-based React structure: app shell; dashboard feature; product workflows; shared accessible components; and a typed API service.

Start with DashboardPage, ProductTable, ProductRow, QuoteStatus, ProductForm, DeleteDialog, and RefreshButton. Keep components focused. Use API response types as the boundary; do not duplicate business rules in the browser. Keep prices as strings and do not use JavaScript Number for arithmetic.

## Implementation order

1. **Backend API:** Add settings, database session lifecycle, health routes, product list/detail/CRUD, and catalog/bootstrap endpoints. Keep SQL and business rules out of route handlers.
2. **Dashboard UI:** Build the product list and quote states against the API, then add create/edit/delete and manual refresh.
3. **Polish:** Verify responsive behavior, keyboard and screen-reader support, loading/error states, and polling.

## Local development

Use the [database guide](../database/README.md) for PostgreSQL startup and market seeding. Start the worker with `terraform -chdir=terraform apply`; the deployment runs one worker instance. Schema initialization runs only when PostgreSQL initializes a fresh data volume. Never commit credentials, local tfvars, or Terraform state.

## Quality rules

- Keep normal tests deterministic and independent of live Coinbase; fake provider/API responses.
- Use isolated PostgreSQL state for persistence tests.
- Verify decimal precision, freshness states, and per-product refresh failures.
- Test UI with mocked API responses, keyboard operation, and narrow layouts.
- Defer authentication and deployment infrastructure while the app remains a local single-user tool; revisit before public exposure.

## Source documents

- [Project requirements](00_PROJECT_OVERVIEW.md)
- [Technical foundation](01_TECHNICAL_FOUNDATION.md)
- [Coinbase integration](02_COINBASE_PRICE_INTEGRATION.md)
- [Product CRUD](03_PRODUCT_CRUD.md)
- [Price refresh](04_PRICE_REFRESH.md)
- [Dashboard UI](05_DASHBOARD_UI.md)
- [Docker local development](06_DOCKER_LOCAL_DEV.md)
- [Test strategy](07_TEST_STRATEGY.md)
- [Selected design](DESIGN_TECHNOLOGY_OPTIONS.md)
