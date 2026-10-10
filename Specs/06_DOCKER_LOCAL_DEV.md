# Spec 06 — Terraform-managed Docker and local developer experience

**Status:** Ready for implementation once runtime/port are selected  
**Priority:** P0  
**Depends on:** 01 foundation, 02 provider configuration, 03 persistence path, 04 lifecycle behavior, 05 application runtime

## Objective

Make the application reproducible for a developer with Docker installed, and ensure product/quote state survives normal container recreation.

## Deliverables

- `Dockerfile` with pinned/constrained base runtime, production start command, and non-root user where practical.
- Terraform configuration using the Docker provider for PostgreSQL, localhost-only pgAdmin and Dozzle, API, refresh-worker, and built React frontend containers; configure environment, named volumes, restart policy, network, and health checks.
- `.dockerignore` excluding `.git`, local caches/venvs, test output, secrets, and generated artifacts.
- `.env.example` with safe defaults and comments; no credentials or personal data.
- README containing prerequisites, start/stop/logs/rebuild/test commands, configuration, health URL, data path, and explicit volume deletion warning.

## Runtime requirements

- App binds `0.0.0.0` inside the container and reads `PORT` (default may be 8080).
- Persist PostgreSQL data in the `postgres_data` named volume. The API connects using `DATABASE_URL`; do not write durable state to an ephemeral container layer.
- Do not require Coinbase connectivity for container startup, health, CRUD, or readiness. Provider outage should be visible in quote status only.
- Liveness verifies process is serving. Readiness verifies required configuration and persistence access. Readiness must not depend on Coinbase availability.
- Health check uses an in-container HTTP check or available runtime tool and has realistic start period, interval, timeout, and retries.
- Log to stdout/stderr so `docker logs` works. Handle SIGTERM, stop scheduler, and close persistence cleanly.
- Do not bake `.env`, secrets, local database, or credentials into image layers.
- Keep image build context small and use multi-stage build if the selected stack benefits.

## Local workflow

README must show Terraform commands equivalent to:

```sh
terraform -chdir=terraform init
terraform -chdir=terraform apply
# Browse to the documented local URL
docker logs -f marketpulse-api
docker stop marketpulse-api marketpulse-coinbase-worker marketpulse-pgadmin marketpulse-postgres
```

Explain that stopping the containers retains named volume data. Mark `terraform -chdir=terraform destroy` as destructive because it removes the Terraform-managed volumes and all saved data.

## Configuration

Document defaults and validation for at least `PORT`, `DATABASE_URL` and PostgreSQL service credentials/port, `PRICE_REFRESH_INTERVAL_SECONDS` (60), `PRICE_STALE_AFTER_SECONDS` (180), Coinbase request timeout (8), max concurrency, retries, and log level. Terraform should pass these through explicitly. Do not commit local tfvars or Terraform state because sensitive container environment values are stored in state.

## Build and startup behavior

- Image builds from a clean checkout without host-generated artifacts.
- PostgreSQL health must pass before dependent services start. Initialize the schema from the PostgreSQL container's first-run SQL hook, then apply any later schema changes explicitly; fail readiness safely if the database is unavailable.
- Dozzle binds to localhost, persists its settings in a named volume, and starts after the application containers. Document that its Docker socket access grants Docker API privileges on the host.
- Build the React production bundle into an Nginx image, serve the single-page app with history fallback, and proxy `/api/` to the API container on the Terraform network.
- First-run product bootstrap attempts to seed 10 supported Coinbase markets after database initialization. Coinbase failure or a partial catalog must not prevent the container from becoming ready; expose bootstrap state and allow retry from the UI.
- Startup may continue when Coinbase is offline; first refresh reports unavailable state.
- App process should be PID 1 or use an init strategy that forwards signals and reaps children.
- Do not use development reload mode in the production container command.

## Acceptance criteria

1. `terraform -chdir=terraform apply` from clean checkout builds and starts the containers.
2. Configured host ports serve the frontend GUI and API.
3. Health check reports healthy after initialization.
4. Products and quotes survive container recreation while named volumes are retained.
5. Rebuilding containers does not erase PostgreSQL data in the named volume.
6. Destroying the Terraform-managed volumes removes the data and is clearly documented as destructive.
7. First startup seeds 10 supported markets when available; partial bootstrap or provider outage is visible and does not block CRUD/readiness.
8. App remains usable for CRUD during Coinbase outage.
9. Logs contain startup, refresh summary, and shutdown information without secrets.
10. Container runs as non-root where feasible and no credentials are present in image.
11. Dozzle reports container logs and health on its documented localhost URL.

## Required verification

- Build and start from clean context.
- Inspect health status.
- Create product, restart/recreate container, verify it remains.
- Simulate provider failure and verify startup/CRUD remain healthy.
- Verify graceful stop and inspect logs.
