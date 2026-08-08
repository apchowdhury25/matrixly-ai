#!/usr/bin/env bash
# Apply Document Intelligence SQL migration against DATABASE_URL (psql style).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${DATABASE_ADMIN_URL:=postgresql://postgres:postgres@localhost:5432/matrixly}"

echo "Applying migrations to ${DATABASE_ADMIN_URL}"
psql "${DATABASE_ADMIN_URL}" -v ON_ERROR_STOP=1 -f "${ROOT}/migrations/001_document_intelligence.sql"
echo "Done."
