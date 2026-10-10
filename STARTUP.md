# MarketPulse: end-to-end local startup

This guide starts PostgreSQL, the API, price worker, React frontend, pgAdmin, and Dozzle. Run commands from the repository root unless noted. Requires Docker Engine, Terraform 1.5+, Python 3, and Node.js/npm for database bootstrap and optional frontend development mode.

## First-time setup

1. Review local configuration. The checked-in Terraform defaults are for local development. To customize them, copy `terraform/terraform.tfvars.example` to `terraform/terraform.tfvars` and edit the values. Keep that file private; Terraform state also contains container environment values and is ignored by Git.

2. Create and start the Docker resources:

   ```sh
   terraform -chdir=terraform init
   terraform -chdir=terraform apply
   docker ps --filter name=marketpulse
   ```

   Terraform builds the frontend and backend images, starts PostgreSQL, and waits for its health check before creating the dependent containers. The frontend is served at **http://localhost:5173**. Database files persist in the `marketpulse_postgres_data` Docker volume.

3. Create the Python environment and install database bootstrap dependencies:

   ```sh
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```

4. Terraform initializes the PostgreSQL schema when it creates a fresh database volume. Seed up to 10 eligible Coinbase USD markets, including initial quotes. Use values matching `terraform/terraform.tfvars` (or these local defaults):

   ```sh
   DATABASE_URL='postgresql://marketpulse:marketpulse_local@localhost:5432/marketpulse' \
     .venv/bin/python database/scripts/bootstrap_db.py
   ```

   This step contacts Coinbase. If bootstrap is interrupted, rerun it; it is designed to resume. Coinbase access is needed for seeding, not for PostgreSQL or API startup.

## Optional frontend development mode

The Terraform-managed frontend uses a production Nginx image. To work with Vite's development server instead, install frontend packages and run:

   ```sh
   cd frontend
   npm install
   npm run dev -- --host 0.0.0.0 --port 5174
   ```

Keep this terminal open while using the app. Vite serves **http://localhost:5174** and proxies API requests to the local backend. The Terraform-managed production frontend remains available on port 5173.

## Subsequent starts

Terraform creates containers with `restart = unless-stopped`. If you stopped them manually, apply Terraform to start them again in dependency order:

```sh
terraform -chdir=terraform apply
```

## Useful local URLs and commands

- App: http://localhost:5173
- API documentation: http://localhost:8000/docs
- API readiness: http://localhost:8000/api/v1/health/ready
- pgAdmin: http://localhost:5050
- Container logs dashboard (Dozzle): http://localhost:8080
- Database shell: `docker exec -it marketpulse-postgres psql -U marketpulse -d marketpulse`
- Service status: `docker ps --filter name=marketpulse`
- API logs: `docker logs -f marketpulse-api`
- Worker logs: `docker logs -f marketpulse-coinbase-worker`
- Stop containers while retaining data: `docker stop marketpulse-frontend marketpulse-api marketpulse-coinbase-worker marketpulse-pgadmin marketpulse-postgres marketpulse-dozzle`
- Apply configuration changes: `terraform -chdir=terraform apply`

The sample pgAdmin login is `admin@marketpulse.dev` / `pgadmin_local`. In pgAdmin, register a server using host `postgres`, port `5432`, database/user `marketpulse`, and the `postgres_password` from your local tfvars.

Dozzle shows logs and status for Docker containers through the Docker socket. Its UI is bound to localhost and its settings persist in the `marketpulse_dozzle_data` volume. The socket grants Docker API access to the host, so keep Dozzle local unless you configure authentication and a protected access path.

**Destructive reset:** `terraform -chdir=terraform destroy` deletes the containers and Terraform-managed volumes, including PostgreSQL data, pgAdmin settings, and Dozzle settings. Use it only when you intend to erase that data.

## If Docker is not installed

On Ubuntu, the repository includes `scripts/install_docker_engine_ubuntu.sh` to install Docker Engine. Run it according to your machine's setup and restart the shell/session if needed, then follow First-time setup.

