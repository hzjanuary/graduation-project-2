#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"

cd "${REPO_ROOT}"

if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
elif docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
else
  echo "Docker Compose is required but was not found." >&2
  exit 1
fi

echo "==> Validating local Docker Compose configuration"
"${COMPOSE[@]}" config

echo "==> Validating production-demo Docker Compose configuration"
"${COMPOSE[@]}" -f docker-compose.prod.yml --env-file docs/deployment/.env.production.example config

echo "Compose gate passed."
