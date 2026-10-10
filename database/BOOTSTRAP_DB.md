# Database bootstrap script

This guide documents [`scripts/bootstrap_db.py`](scripts/bootstrap_db.py). The script initializes the tracked market list and its first prices from Coinbase Exchange. It does not create tables; Terraform configures PostgreSQL to run [`schema.sql`](schema.sql) when PostgreSQL initializes an empty data volume.

It is a one-time/manual seed utility. Terraform creates the PostgreSQL container and mounts the schema file, but does not run this script. Run it after PostgreSQL is accepting connections and before expecting initial markets and quotes to be present.

## What the script does

In normal mode, the script:

1. Reads the PostgreSQL connection URL from `--database-url`, `DATABASE_URL`, or its local default.
2. Connects to PostgreSQL and checks `bootstrap_state`. If it says bootstrap is complete, prints the current tracked-product count and exits without contacting Coinbase.
3. Fetches Coinbase's public product catalog and updates the local catalog cache.
4. Selects eligible USD crypto markets, preferring the configured major-market list.
5. Requests live ticker prices for missing tracked markets and inserts up to the target count, along with their initial quote rows.
6. Records whether bootstrap is complete or partial and prints a summary.

The script only uses Coinbase's public HTTP endpoints. It does not need an API key, modify Coinbase data, start Docker, create the PostgreSQL database, or create its tables. PostgreSQL must already be running, the named database must exist, and the schema must already be initialized.

## Requirements

- Python 3 and the project dependencies from `requirements.txt`, including `psycopg[binary]`.
- A reachable initialized PostgreSQL database with permission to read and write bootstrap tables.
- Outbound HTTPS access to `api.exchange.coinbase.com`.

For the Terraform local setup, run `terraform -chdir=terraform apply` first. Terraform mounts the schema into PostgreSQL's initialization directory, and the PostgreSQL image runs it when initializing an empty data volume. Then install dependencies and run the script from the repository root. See [`README.md`](README.md) for setup commands.

## Command line

### Seed markets

```sh
python database/scripts/bootstrap_db.py
```

This is the default. It uses `DATABASE_URL` if set, or this local default:

```text
postgresql://marketpulse:marketpulse_local@localhost:5432/marketpulse
```

Pass a different connection URL directly:

```sh
python database/scripts/bootstrap_db.py \
  --database-url 'postgresql://marketpulse:password@localhost:5432/marketpulse'
```

The command-line URL takes precedence over `DATABASE_URL`, which takes precedence over the built-in default. The script does not load `.env` files automatically.

## How Terraform initializes the schema

The schema source of truth is [`schema.sql`](schema.sql). In [`terraform/postgres.tf`](../terraform/postgres.tf), Terraform bind-mounts this file as `/docker-entrypoint-initdb.d/001_marketpulse_schema.sql`. The PostgreSQL image runs SQL initialization files only when the data directory is empty. This occurs before PostgreSQL reports healthy, so dependent Terraform-managed containers start after initial schema creation.

The schema uses `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, and `INSERT ... ON CONFLICT DO NOTHING`. PostgreSQL's initialization scripts do not rerun when Terraform restarts or recreates a container using an already-initialized data volume. Updating `schema.sql` therefore does not alter existing databases; apply any needed SQL alteration deliberately, or initialize a fresh volume. A fresh volume also means a fresh, empty database.

The schema defines:

- `tracked_products`: products tracked by the app, including whether they are active and whether they came from bootstrap or manual entry.
- `coinbase_market_catalog`: cached Coinbase product metadata, including status and eligibility.
- `latest_quotes`: latest quote and retrieval/error metadata for each tracked product.
- `bootstrap_state`: target count, progress status, timestamps, and the most recent bootstrap error.
- Indexes for active product sorting and market catalog lookup.

The initial state row has `id = 1` and a target of 10 tracked products. If that row is missing, the script fails with an error asking for PostgreSQL schema initialization.

## Coinbase market selection

The catalog request is `GET /products`. A market is eligible only when:

- `id`, `base_currency`, and `quote_currency` are non-empty strings.
- The product ID matches `BASE-QUOTE` after comparing uppercase values.
- The quote currency is USD.
- The base currency is not in the script's fiat-currency exclusion list.
- Coinbase reports `status` exactly as `online`.
- `trading_disabled` is false or absent.

The preferred order is BTC-USD, ETH-USD, SOL-USD, XRP-USD, ADA-USD, DOGE-USD, AVAX-USD, LINK-USD, LTC-USD, and BCH-USD. Other eligible markets follow in alphabetic product-ID order.

The target count is read from `bootstrap_state.target_count` (10 in the supplied schema). The script counts all existing rows in `tracked_products` toward this target, including manually created products. It skips a candidate already in `tracked_products` without making a ticker request for it. It checks no more than 50 new candidates in one run.

For each candidate it checks, the script requests `GET /products/{product_id}/ticker`. A ticker is accepted only if the response contains a string price that parses as a finite positive `Decimal`. This avoids converting prices through binary floating-point. The optional ticker `time` is parsed as an ISO timestamp; an invalid/missing time is stored as null, while the local retrieval and attempt times are recorded in UTC.

## Database writes

### Catalog cache

For catalog entries with valid IDs and currency strings, the script upserts into `coinbase_market_catalog`. It uppercases the product and currency IDs, stores display name/status/trading-disabled/eligibility values, and updates `last_seen_at`. Existing catalog records are refreshed on each incomplete bootstrap run.

### Tracked products and initial quotes

For each successfully verified candidate, the script inserts a row in `tracked_products` with `source = 'bootstrap'` and a name from Coinbase's `base_name` field, falling back to the base currency. If the product insert succeeds, it inserts the verified price into `latest_quotes` with its quote currency, local retrieval time, optional Coinbase trade time, and last-attempt time.

An already tracked product is not renamed, replaced, or given a new initial quote by this script. It does not delete any product or quote. Ongoing price refreshes are handled by the separate worker.

### Bootstrap progress

If the total number of tracked products reaches the target, `bootstrap_state.state` becomes `complete`; otherwise it becomes `partial`. The script records the total count in `seeded_count`, sets `last_attempt_at`, and sets `completed_at` only for a complete run. For a partial run, it stores up to eight ticker rejection messages or a general message if fewer than 10 eligible markets were available.

If fetching the catalog fails, the script records the failure and sets the state to `partial`, unless it was already complete. A ticker failure rejects that candidate and the script continues to the next one. Database errors are reported as bootstrap failures; they may stop the run before final progress fields are updated.

## Rerun behavior and limits

- An incomplete run can be rerun. Existing products count toward the target, and newly available/working candidates can fill remaining slots.
- A completed run exits early. It does not refresh the catalog or restore products that someone later deletes, even if fewer than the target remain.
- If there are already at least 10 tracked products while the state is not complete, no additional products are needed and the run marks bootstrap complete.
- Each HTTP request has an 8-second timeout. A normal run makes one catalog request and may make up to 50 ticker requests.
- The script does not periodically refresh quotes; the Coinbase worker does that after setup.

## Exit status and errors

- Exit code `0`: the full bootstrap is complete or was already complete.
- Exit code `1`: a handled operating-system, PostgreSQL, Coinbase, or incomplete-bootstrap error occurred. Details are printed to standard error for fatal errors; partial market/ticker failures are printed in the summary.
- Invalid command-line arguments are handled by Python's `argparse` and exit with its usage-error status.

Fatal errors are prefixed with `PostgreSQL bootstrap failed:`. Common causes include PostgreSQL being stopped, an invalid URL/password, missing/uninitialized database tables, insufficient database permissions, Coinbase connectivity problems, or malformed Coinbase responses.

## Settings in the script

The preferred market IDs, fiat-currency exclusion list, Coinbase base URL, request timeout, and built-in database URL are constants near the top of `scripts/bootstrap_db.py`. The target product count is stored in the database's `bootstrap_state` row, not read from a command-line option.

There is no command-line option to reset progress, change the target count, refresh already-seeded initial prices, or force a rerun after state reaches `complete`. Those actions require deliberate database changes or separate application functionality.
