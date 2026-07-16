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

Do not commit real `.env` files, provider API keys, JWT secrets, database
passwords, object storage credentials, or cloud credentials.
