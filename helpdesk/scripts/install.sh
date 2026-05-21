#!/bin/bash
set -euo pipefail

APP_DIR="/var/www/helpdesk"
DB_NAME="helpdesk_db"
DB_USER="helpdesk_user"
DB_PASS="senha_forte"

echo "=== TI HelpDesk — Instalação automática (Ubuntu 22.04) ==="

# 1. Atualizar sistema e instalar dependências
echo "[1/8] Atualizando pacotes..."
sudo apt update -q && sudo apt upgrade -y -q
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql nginx

# 2. Configurar PostgreSQL
echo "[2/8] Configurando PostgreSQL..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename='${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

# 3. Criar diretório e copiar arquivos
echo "[3/8] Instalando arquivos..."
sudo mkdir -p "${APP_DIR}"
sudo chown -R www-data:www-data "${APP_DIR}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
sudo cp -r "${PROJECT_DIR}"/* "${APP_DIR}/"

# 4. Configurar variáveis de ambiente
echo "[4/8] Configurando .env..."
if [ ! -f "${APP_DIR}/.env" ]; then
    sudo cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
    sudo sed -i "s/senha_forte/${DB_PASS}/g" "${APP_DIR}/.env"
    echo "  ⚠ ATENÇÃO: edite ${APP_DIR}/.env com suas chaves (ANTHROPIC_API_KEY, SECRET_KEY)"
fi

# 5. Criar virtualenv e instalar dependências Python
echo "[5/8] Instalando dependências Python..."
sudo -u www-data python3.11 -m venv "${APP_DIR}/venv"
sudo "${APP_DIR}/venv/bin/pip" install --quiet --upgrade pip
sudo "${APP_DIR}/venv/bin/pip" install --quiet -r "${APP_DIR}/backend/requirements.txt"

# 6. Rodar migrações e seed
echo "[6/8] Criando banco de dados..."
cd "${APP_DIR}/backend"
sudo -u www-data bash -c "
    cd ${APP_DIR}
    source .env 2>/dev/null || true
    export PYTHONPATH=${APP_DIR}/backend
    ${APP_DIR}/venv/bin/python -c 'from database import Base, engine; from models import *; Base.metadata.create_all(bind=engine)'
    ${APP_DIR}/venv/bin/python seed.py
"

# 7. Configurar systemd
echo "[7/8] Configurando serviço systemd..."
sudo cp "${APP_DIR}/systemd/helpdesk.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable helpdesk
sudo systemctl start helpdesk

# 8. Configurar Nginx
echo "[8/8] Configurando Nginx..."
sudo cp "${APP_DIR}/nginx/helpdesk.conf" /etc/nginx/sites-available/helpdesk
sudo ln -sf /etc/nginx/sites-available/helpdesk /etc/nginx/sites-enabled/helpdesk
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "✅ HelpDesk instalado com sucesso!"
echo ""
echo "   API:      http://localhost:8000"
echo "   Swagger:  http://localhost:8000/docs"
echo "   Frontend: http://localhost"
echo ""
echo "   Login admin: admin@empresa.com / Admin@123"
echo ""
echo "   ⚠ Lembre-se de editar ${APP_DIR}/.env com:"
echo "     - ANTHROPIC_API_KEY"
echo "     - SECRET_KEY (chave aleatória longa)"
echo "     - FRONTEND_URL (domínio real)"
echo ""
echo "   Logs: sudo journalctl -u helpdesk -f"
