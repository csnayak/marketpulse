# PostgreSQL database setup

PostgreSQL is the application database for local development and deployment. The canonical schema is `database/schema.sql`; Terraform mounts it into PostgreSQL's first-run initialization directory. `database/scripts/bootstrap_db.py` seeds Coinbase markets after the schema exists.

For a detailed explanation of the script's options, selection rules, database writes, and rerun behavior, see [Database bootstrap script](BOOTSTRAP_DB.md).

The schema contains:

- `tracked_products`: application-owned Coinbase markets maintained through CRUD.
- `coinbase_market_catalog`: cached Coinbase catalog metadata used for product discovery.
- `latest_market_stats`: the current 24h snapshot and last-attempt/error state for each tracked product.
- `quote_history`: append-only snapshot history for trend and scoring work.
- `bootstrap_state`: progress for the initial 10-market bootstrap.

Prices use PostgreSQL `NUMERIC` and Python `Decimal`. Timestamps use `TIMESTAMPTZ` and are stored in UTC. A failed fetch must not replace a previous successful price.

## Start PostgreSQL

From the repository root:

```sh
terraform -chdir=terraform init
terraform -chdir=terraform apply
docker ps --filter name=marketpulse
```

The local Terraform defaults are for development only. Do not reuse them in a shared or public deployment. PostgreSQL data is stored in the `marketpulse_postgres_data` Docker volume.
Terraform mounts `database/schema.sql` into the PostgreSQL container. The official PostgreSQL image runs that SQL file when it initializes an empty data volume, before the database health check passes and dependent containers start. The bootstrap command below then seeds Coinbase markets.

## View PostgreSQL in a browser with pgAdmin

After applying the schema and seeding products, use pgAdmin to inspect the data.

1. Ensure the services are running: `terraform -chdir=terraform apply`.
2. Open [http://localhost:5050](http://localhost:5050).
3. Sign in with `pgadmin_email` and `pgadmin_password` from `terraform/terraform.tfvars` (the defaults are `admin@marketpulse.dev` and `pgadmin_local`).
4. In pgAdmin, right-click **Servers** and choose **Register → Server**.
5. On **General**, enter `MarketPulse Local` as the name.
6. On **Connection**, enter:
   - **Host name/address:** `postgres`
   - **Port:** `5432`
   - **Maintenance database:** `marketpulse`
   - **Username:** `marketpulse`
   - **Password:** the `postgres_password` value from tfvars
   - Optionally enable **Save password** for this local development instance.
7. Save, expand **Servers → MarketPulse Local → Databases → marketpulse → Schemas → public → Tables**. Right-click a table and choose **View/Edit Data → All Rows**, or use **Tools → Query Tool** to run SQL.

Example Query Tool SQL:

```sql
SELECT id, coinbase_product_id, name, is_active
FROM public.tracked_products
ORDER BY name;

SELECT p.coinbase_product_id, q.last_price, q.retrieved_at
FROM public.tracked_products AS p
LEFT JOIN public.latest_market_stats AS q ON q.product_id = p.id
ORDER BY p.name;
```

The pgAdmin port is bound to `127.0.0.1`, so this browser UI is for the local machine and is not exposed to your LAN. Keep local tfvars and Terraform state private. pgAdmin server registrations/settings are persisted in the `marketpulse_pgadmin_data` volume.

Dozzle's container logs dashboard is available at [http://localhost:8080](http://localhost:8080). It is also bound to localhost and its settings persist in `marketpulse_dozzle_data`. Dozzle can access the Docker API through the mounted socket; keep it local unless you configure authentication and protected access.

## Install database utility dependencies

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

## Seed 10 products

With PostgreSQL running, run:

```sh
python database/scripts/bootstrap_db.py
```

The command reads `DATABASE_URL` from the process environment; a `.env` file is not automatically loaded by Python. Pass the connection string explicitly (as below), or export it before running the command:

```sh
python database/scripts/bootstrap_db.py --database-url 'postgresql://marketpulse:marketpulse_local@localhost:5432/marketpulse'
```

Alternatively, export the values from `.env` in Bash before invoking the command:

```sh
set -a
. ./.env
set +a
python database/scripts/bootstrap_db.py
```

The bootstrap command fetches Coinbase's public Exchange product catalog, filters eligible online USD markets, verifies candidate tickers, and seeds up to 10 products. It can be re-run after partial bootstrap; it does not overwrite or restore products after bootstrap is complete. Coinbase access is only needed for seeding, not to start PostgreSQL or the application services. The database schema must already exist; Terraform configures PostgreSQL to initialize it when the data volume is empty.

PostgreSQL's initialization scripts run only when its data directory is empty. Changes to `database/schema.sql` will not be applied to an existing initialized volume; those require a deliberate SQL change or a fresh database volume. Destroying the Terraform-managed PostgreSQL volume deletes its data.

## Connect with psql

```sh
docker exec -it marketpulse-postgres psql -U marketpulse -d marketpulse
```

Example queries:

```sql
SELECT id, coinbase_product_id, name, is_active FROM tracked_products ORDER BY name;
SELECT p.coinbase_product_id, q.last_price, q.retrieved_at
FROM tracked_products AS p
LEFT JOIN latest_market_stats AS q ON q.product_id = p.id
ORDER BY p.name;
```

Stopping the containers keeps their volumes. **`terraform -chdir=terraform destroy` deletes PostgreSQL data and the saved settings for pgAdmin and Dozzle because Terraform manages these volumes.**

Official container instructions: [pgAdmin container deployment](https://www.pgadmin.org/docs/pgadmin4/latest/container_deployment.html).
