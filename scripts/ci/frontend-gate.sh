#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"

cd "${REPO_ROOT}/frontend"

echo "==> Installing frontend dependencies"
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi

echo "==> Running frontend lint"
npm run lint

echo "==> Building frontend"
npm run build

echo "==> Running frontend typecheck"
npm run typecheck

echo "==> Running frontend tests"
npm test

echo "Frontend gate passed."
