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

echo "==> Running Compose gate"
bash scripts/ci/compose-gate.sh

echo "==> Running backend gate"
bash scripts/ci/backend-gate.sh

echo "==> Running frontend gate"
bash scripts/ci/frontend-gate.sh

echo "==> Building production-demo application images"
"${COMPOSE[@]}" -f docker-compose.prod.yml --env-file docs/deployment/.env.production.example build backend frontend

echo "==> Checking whitespace"
git diff --check

echo "All quality gates passed."
