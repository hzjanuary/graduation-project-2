# Deployment Documentation

SPEC-014 tracks production-demo deployment and observability work. This folder
contains environment planning artifacts only; it does not add deployment
infrastructure by itself.

Use these files when preparing a deployable demo stack:

- `ENVIRONMENT.md` explains the `local-demo`, `ci-test`, and
  `production-demo` environment profiles.
- `.env.production.example` is a placeholder-only production-demo template for
  backend and frontend environment injection.
- `.env.ci.example` is a no-key CI/test template for deterministic validation.
- `../../docker-compose.prod.yml` defines the additive production-demo Compose
  stack for backend, frontend, Postgres, Redis, Qdrant, and MinIO.

Do not commit real `.env` files, provider API keys, JWT secrets, database
passwords, object storage credentials, or cloud credentials.

## Production-Demo Compose

Validate the production-demo Compose file without starting services:

```bash
docker-compose -f docker-compose.prod.yml --env-file docs/deployment/.env.production.example config
```

Build the production-demo application images:

```bash
docker-compose -f docker-compose.prod.yml --env-file docs/deployment/.env.production.example build backend frontend
```

The production-demo stack is additive. It does not replace the local
`docker-compose.yml` developer stack and it does not run demo seeding or
knowledge ingestion automatically.

By default, only the frontend and backend ports are published. Postgres, Redis,
Qdrant, and MinIO stay on the internal Compose network. Do not expose stateful
service ports publicly without explicit network and credential hardening.
