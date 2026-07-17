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

cleanup() {
  if [[ "${BACKEND_GATE_CLEANUP:-0}" == "1" ]]; then
    echo "==> Cleaning up backend gate Compose services"
    "${COMPOSE[@]}" down --remove-orphans
  fi
}
trap cleanup EXIT

echo "==> Building backend-test image"
"${COMPOSE[@]}" build backend-test

echo "==> Starting backend test dependencies"
"${COMPOSE[@]}" up -d postgres redis qdrant minio

echo "==> Applying database migrations"
"${COMPOSE[@]}" run --rm backend-test alembic upgrade head

echo "==> Running backend pytest"
"${COMPOSE[@]}" run --rm backend-test pytest

echo "==> Running Ruff"
"${COMPOSE[@]}" run --rm backend-test ruff check .

echo "==> Running Black check"
"${COMPOSE[@]}" run --rm backend-test black --check .

echo "==> Running MyPy"
"${COMPOSE[@]}" run --rm backend-test mypy app

echo "==> Running demo seed dry-run JSON check"
"${COMPOSE[@]}" run --rm backend-test python -m app.demo.seed --confirm-local-demo --dry-run --json

echo "==> Running knowledge ingestion dry-run JSON check"
"${COMPOSE[@]}" run --rm backend-test python -m app.knowledge.ingest_demo --confirm-local-demo --dry-run --json

echo "Backend gate passed."
