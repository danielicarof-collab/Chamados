#!/bin/bash
set -euo pipefail

BACKUP_DIR="/var/backups/helpdesk"
DB_NAME="helpdesk_db"
DB_USER="helpdesk_user"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/helpdesk_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "Iniciando backup: ${BACKUP_FILE}"
sudo -u postgres pg_dump "${DB_NAME}" | gzip > "${BACKUP_FILE}"

# Remover backups antigos
find "${BACKUP_DIR}" -name "helpdesk_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

echo "✅ Backup concluído: ${BACKUP_FILE}"
echo "   Tamanho: $(du -sh "${BACKUP_FILE}" | cut -f1)"
