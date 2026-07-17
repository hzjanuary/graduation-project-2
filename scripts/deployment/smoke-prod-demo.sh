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

BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://localhost:8000}"
FRONTEND_BASE_URL="${FRONTEND_BASE_URL:-http://localhost:3000}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-docs/deployment/.env.production.example}"
SMOKE_TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-10}"

START_STACK=0
INCLUDE_READY=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/deployment/smoke-prod-demo.sh [--start] [--include-ready]

Checks an already-running production-demo stack by default.

Options:
  --start          Start the production-demo Compose stack before checks.
  --include-ready  Check backend /ready in addition to /health and /live.
  -h, --help       Show this help text.

Environment overrides:
  BACKEND_BASE_URL       Default: http://localhost:8000
  FRONTEND_BASE_URL      Default: http://localhost:3000
  COMPOSE_FILE           Default: docker-compose.prod.yml
  COMPOSE_ENV_FILE       Default: docs/deployment/.env.production.example
  SMOKE_TIMEOUT_SECONDS  Default: 10
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --start)
      START_STACK=1
      shift
      ;;
    --include-ready)
      INCLUDE_READY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for production-demo smoke checks." >&2
  exit 1
fi

if [[ "${START_STACK}" == "1" ]]; then
  echo "==> Starting production-demo Compose stack"
  "${COMPOSE[@]}" -f "${COMPOSE_FILE}" --env-file "${COMPOSE_ENV_FILE}" up -d
fi

check_url() {
  local label="$1"
  local url="$2"
  echo "==> Checking ${label}: ${url}"
  curl -fsS --max-time "${SMOKE_TIMEOUT_SECONDS}" "${url}" >/dev/null
}

BACKEND_BASE_URL="${BACKEND_BASE_URL%/}"
FRONTEND_BASE_URL="${FRONTEND_BASE_URL%/}"

check_url "backend /health" "${BACKEND_BASE_URL}/health"
check_url "backend /live" "${BACKEND_BASE_URL}/live"

if [[ "${INCLUDE_READY}" == "1" ]]; then
  check_url "backend /ready" "${BACKEND_BASE_URL}/ready"
fi

check_url "frontend root" "${FRONTEND_BASE_URL}/"

echo "Production-demo smoke checks passed."
