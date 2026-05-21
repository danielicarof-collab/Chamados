#!/bin/bash
set -euo pipefail

APP_DIR="/var/www/helpdesk"
cd "${APP_DIR}"

echo "Rodando migrações Alembic..."
source .env 2>/dev/null || true

PYTHONPATH="${APP_DIR}/backend" \
    "${APP_DIR}/venv/bin/alembic" \
    -c "${APP_DIR}/alembic/alembic.ini" \
    upgrade head

echo "✅ Migrações aplicadas com sucesso"
