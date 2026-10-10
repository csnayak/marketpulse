# Spec 01 — Technical foundation and application skeleton

**Status:** First implementation step  
**Priority:** P0  
**Depends on:** 00 Project overview  
**Enables:** 02 Coinbase integration, 03 product management, and all later components

## Objective

Create the smallest runnable application foundation before implementing market behavior: select and document the stack, establish configuration and persistence conventions, define shared API behavior, and provide a healthy application skeleton. Use PostgreSQL with SQLAlchemy 2 and psycopg for persistence. The selected application stack is Python/FastAPI with a React/TypeScript frontend.

## Decisions to record before implementation

PostgreSQL is selected for local development and deployment, using Terraform-managed Docker volumes for local persistence. Use SQLAlchemy 2 and psycopg for data access. The database schema is defined in `database/schema.sql` and mounted by Terraform into PostgreSQL's first-run initialization directory. Keep the backend a modular monolith and avoid distributed services until required.

Define the Coinbase product and price provider interfaces in spec 02 before consumers are implemented. Provider calls must be injectable so tests can use deterministic fakes.

## Scope

### Repository and service skeleton
- Establish the project structure with clear boundaries for UI, application/use-case logic, persistence, provider adapters, and configuration.
- Add a minimal application entry point that starts locally and serves a placeholder page/API.
- Add dependency/runtime version constraints and standard formatter/linter configuration appropriate to the chosen stack.
- Use environment-driven configuration with typed parsing, safe defaults, and startup validation. Do not commit secrets.

### Persistence baseline
- Configure the chosen database and its connection lifecycle.
- Define and apply the database schema before creating business tables. Product and latest quote schemas are specified in specs 03 and 02 respectively; create those tables in their owning work items rather than duplicating schema definitions here.
- Define transaction and repository conventions so product CRUD and quote updates can be atomic.
- Configure the PostgreSQL connection through `DATABASE_URL`; use a durable named Docker volume for local PostgreSQL data.

### Shared HTTP/API conventions
- Establish JSON serialization, request validation error format, and a consistent error envelope:

```json
{"error":{"code":"stable_code","message":"Safe user-facing message","field_errors":{}}}
```

- Use UTC ISO 8601 timestamps at API boundaries.
- Reserve `/api/v1/health/live` for process liveness and `/api/v1/health/ready` for configuration/database readiness. Provider availability must not control readiness.
- Do not expose stack traces, database details, secrets, or raw provider response bodies to clients.

### Operational baseline
- Log structured startup/shutdown events to stdout/stderr.
- Handle graceful shutdown and close database/client resources.
- Provide a local run command and document required environment variables.
- Keep UI and API accessible without Coinbase connectivity.

## Out of scope

Product table, product CRUD, bootstrap of 10 markets, Coinbase HTTP calls, refresh scheduler, final dashboard, and Docker image are delivered in later numbered specs. Authentication, user accounts, queues, microservices, and production cloud deployment are out of scope.

## Acceptance criteria

1. A clean checkout can install dependencies using documented commands and start the skeleton application.
2. Stack and key technical choices are documented with brief rationale.
3. Configuration is parsed and invalid values fail startup with a safe actionable message.
4. `/api/v1/health/live` reports process liveness; `/api/v1/health/ready` reflects database/config readiness and does not call Coinbase.
5. Shared error responses and UTC timestamp conventions are documented and exercised by a representative endpoint.
6. PostgreSQL initialization creates the schema for an empty data volume; later starts preserve the initialized database.
7. Tests can substitute persistence and external provider dependencies without live network calls.
8. Shutdown closes resources without losing committed data.

## Required tests

- Unit tests for configuration parsing, defaults, and invalid values.
- API tests for health/readiness and the common error envelope.
- Schema setup smoke test against an isolated PostgreSQL database.
- No live Coinbase calls are required in this foundation step.
