# TI HelpDesk v2.0 — Guia de Instalação Completo

**Sistema:** Ubuntu 22.04 LTS  
**Tempo estimado:** 25–35 minutos  
**Acesso necessário:** root ou sudo

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Transferir os arquivos para o servidor](#2-transferir-os-arquivos-para-o-servidor)
3. [Instalar dependências do sistema](#3-instalar-dependências-do-sistema)
4. [Configurar o PostgreSQL](#4-configurar-o-postgresql)
5. [Instalar o projeto](#5-instalar-o-projeto)
6. [Configurar variáveis de ambiente (.env)](#6-configurar-variáveis-de-ambiente-env)
7. [Criar banco de dados e dados iniciais](#7-criar-banco-de-dados-e-dados-iniciais)
8. [Configurar o serviço systemd](#8-configurar-o-serviço-systemd)
9. [Configurar o Nginx](#9-configurar-o-nginx)
10. [Primeiro acesso](#10-primeiro-acesso)
11. [Verificações pós-instalação](#11-verificações-pós-instalação)
12. [Solução de problemas](#12-solução-de-problemas)
13. [Configuração HTTPS](#13-configuração-https-recomendado)
14. [Comandos do dia a dia](#14-comandos-do-dia-a-dia)

---

## 1. Pré-requisitos

### Servidor mínimo recomendado
| Recurso | Mínimo | Recomendado (900–1.200 usuários) |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 2 GB | 4 GB |
| Disco | 20 GB | 40 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Portas que precisam estar abertas no firewall
| Porta | Protocolo | Uso |
|---|---|---|
| 22 | TCP | SSH |
| 80 | TCP | HTTP (frontend + API via Nginx) |
| 443 | TCP | HTTPS (opcional, mas recomendado) |

> ⚠ **A porta 8000 (API) NÃO deve ficar exposta publicamente** — o Nginx fará o proxy internamente.

### O que você precisará ter em mãos
- IP do servidor ou domínio DNS configurado
- Chave da API Anthropic: https://console.anthropic.com
- Arquivo `helpdesk.zip`
- (Opcional) Conta de e-mail para SMTP — Gmail com App Password é o mais simples
- (Opcional) URL do Teams Incoming Webhook

---

## 2. Transferir os arquivos para o servidor

### Opção A — Via SCP (Windows PowerShell / macOS / Linux)
```bash
# No seu computador local
scp helpdesk.zip usuario@IP_DO_SERVIDOR:/tmp/
```

### Opção B — Via SFTP (FileZilla, WinSCP)
- Host: `IP_DO_SERVIDOR`
- Usuário/senha: suas credenciais SSH
- Destino no servidor: `/tmp/helpdesk.zip`

### Opção C — Via wget (se o arquivo estiver numa URL)
```bash
# Já conectado ao servidor via SSH
wget -O /tmp/helpdesk.zip "URL_DO_ARQUIVO"
```

---

## 3. Instalar dependências do sistema

Conecte ao servidor via SSH e execute:

```bash
# ── Atualizar o sistema ───────────────────────────────────────────────────────
sudo apt update && sudo apt upgrade -y

# ── Instalar todas as dependências ───────────────────────────────────────────
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nginx \
    unzip \
    curl \
    git \
    ufw

# ── Verificar as instalações ─────────────────────────────────────────────────
python3.11 --version    # deve mostrar Python 3.11.x
psql --version          # deve mostrar psql 14.x ou 16.x
nginx -v                # deve mostrar nginx/1.x.x
```

### Configurar o firewall (UFW)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

**Saída esperada:**
```
Status: active

To                         Action      From
--                         ------      ----
OpenSSH                    ALLOW       Anywhere
Nginx Full                 ALLOW       Anywhere
```

---

## 4. Configurar o PostgreSQL

```bash
# ── Iniciar e habilitar o serviço ─────────────────────────────────────────────
sudo systemctl start postgresql
sudo systemctl enable postgresql

# ── Acessar o shell do PostgreSQL como superusuário ──────────────────────────
sudo -u postgres psql
```

Dentro do shell `psql`, execute os 4 comandos abaixo e depois saia:

```sql
CREATE USER helpdesk_user WITH PASSWORD 'HelpDesk@2024!';
CREATE DATABASE helpdesk_db OWNER helpdesk_user;
GRANT ALL PRIVILEGES ON DATABASE helpdesk_db TO helpdesk_user;
\q
```

> ⚠ **Anote bem a senha** — você vai precisar dela no `.env` na próxima etapa.
> Em produção, use uma senha mais forte e única para cada instalação.

**Testar a conexão:**
```bash
psql -U helpdesk_user -d helpdesk_db -h localhost -c "SELECT 1 AS teste;"
# Digite a senha quando solicitado
# Resultado esperado: teste = 1
```

---

## 5. Instalar o projeto

```bash
# ── Extrair o ZIP ─────────────────────────────────────────────────────────────
cd /tmp
unzip helpdesk.zip -d helpdesk_extracted

# ── Verificar o que foi extraído ─────────────────────────────────────────────
ls /tmp/helpdesk_extracted/
# Deve mostrar: backend/  frontend/  nginx/  systemd/  scripts/  .env.example ...
# (se mostrar uma subpasta "helpdesk", os arquivos estão em helpdesk_extracted/helpdesk/)

# ── Criar o diretório de instalação ──────────────────────────────────────────
sudo mkdir -p /var/www/helpdesk

# ── Copiar os arquivos (use UMA das opções abaixo) ────────────────────────────

# Opção A: se ls mostrou os arquivos diretamente em helpdesk_extracted/
sudo cp -r /tmp/helpdesk_extracted/* /var/www/helpdesk/

# Opção B: se ls mostrou uma subpasta helpdesk/ dentro de helpdesk_extracted/
# sudo cp -r /tmp/helpdesk_extracted/helpdesk/* /var/www/helpdesk/

# ── Verificar se está correto ─────────────────────────────────────────────────
ls /var/www/helpdesk/
# Deve mostrar: backend/  frontend/  nginx/  systemd/  scripts/  .env.example

# ── Definir proprietário ─────────────────────────────────────────────────────
sudo chown -R www-data:www-data /var/www/helpdesk

# ── Corrigir line endings CRLF → LF (necessário se o ZIP veio do Windows) ────
sudo find /var/www/helpdesk/scripts -name "*.sh" -exec sed -i 's/\r$//' {} \;
sudo find /var/www/helpdesk/systemd -name "*.service" -exec sed -i 's/\r$//' {} \;
sudo find /var/www/helpdesk/nginx -name "*.conf" -exec sed -i 's/\r$//' {} \;
sudo chmod +x /var/www/helpdesk/scripts/*.sh

# ── Criar o ambiente virtual Python ──────────────────────────────────────────
sudo -u www-data python3.11 -m venv /var/www/helpdesk/venv

# ── Instalar dependências Python ─────────────────────────────────────────────
sudo /var/www/helpdesk/venv/bin/pip install --upgrade pip
sudo /var/www/helpdesk/venv/bin/pip install -r /var/www/helpdesk/backend/requirements.txt
```

> ⏱ A instalação das dependências Python leva 3–6 minutos. Aguarde a conclusão.

**Verificar se funcionou:**
```bash
sudo /var/www/helpdesk/venv/bin/python -c "import fastapi; print('FastAPI OK:', fastapi.__version__)"
sudo /var/www/helpdesk/venv/bin/python -c "import anthropic; print('Anthropic OK')"
```

---

## 6. Configurar variáveis de ambiente (.env)

```bash
# ── Copiar o template ─────────────────────────────────────────────────────────
sudo cp /var/www/helpdesk/.env.example /var/www/helpdesk/.env

# ── Gerar a SECRET_KEY antes de editar ───────────────────────────────────────
python3 -c "import secrets; print(secrets.token_hex(32))"
# Copie o resultado de 64 caracteres — você vai usar em seguida

# ── Editar o arquivo ─────────────────────────────────────────────────────────
sudo nano /var/www/helpdesk/.env
```

**Preencha cada campo conforme abaixo — substitua os valores marcados com ⚠:**

```env
# ── Banco de dados ──────────────────────────────────────────────────────────
# ⚠ Use a senha que você definiu no passo 4
DATABASE_URL=postgresql://helpdesk_user:HelpDesk@2024!@localhost:5432/helpdesk_db

# ── JWT ─────────────────────────────────────────────────────────────────────
# ⚠ Cole a chave gerada pelo comando acima
SECRET_KEY=a1b2c3d4e5f6...64caracteres...
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# ── Anthropic IA ─────────────────────────────────────────────────────────────
# ⚠ Obtenha em: https://console.anthropic.com/settings/keys
ANTHROPIC_API_KEY=sk-ant-api03-...

# ── Aplicação ────────────────────────────────────────────────────────────────
APP_HOST=0.0.0.0
APP_PORT=8000
APP_ENV=production

# ⚠ IP do servidor ou domínio (sem barra no final)
FRONTEND_URL=http://192.168.1.100
BASE_URL=http://192.168.1.100

# Nome da empresa (aparece nos e-mails e no portal)
COMPANY_NAME=Minha Empresa

# ── E-mail (opcional — deixe SMTP_USER em branco para desativar) ────────────
# Para Gmail: use uma "App Password" (não a senha normal)
# Crie em: https://myaccount.google.com/apppasswords
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=ti@empresa.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_FROM=TI HelpDesk <ti@empresa.com>

# E-mail da fila de TI (recebe alerta de cada novo chamado)
TEAM_EMAIL=fila-ti@empresa.com

# ── Microsoft Teams (opcional) ───────────────────────────────────────────────
# Deixe em branco para desativar
# Como obter: Teams → Canal → ... → Conectores → Incoming Webhook → Configurar
TEAMS_WEBHOOK_URL=
```

**Salvar e fechar:** `Ctrl+X` → `Y` → `Enter`

**Proteger o arquivo:**
```bash
sudo chmod 640 /var/www/helpdesk/.env
sudo chown www-data:www-data /var/www/helpdesk/.env
```

**Confirmar que ficou correto:**
```bash
sudo grep -v '^#' /var/www/helpdesk/.env | grep -v '^$'
```

---

## 7. Criar banco de dados e dados iniciais

```bash
sudo -u www-data bash -c "
  cd /var/www/helpdesk/backend
  export \$(grep -v '^#' /var/www/helpdesk/.env | grep -v '^$' | xargs)
  /var/www/helpdesk/venv/bin/python seed.py
"
```

**Saída esperada (completa):**
```
  SLA rules criadas (ITIL 4)
  Departamentos criados
  Categorias criadas
  Analistas criados (incluindo coordenador)
  Login admin: admin@empresa.com / Admin@123
  Usuários criados com senha de portal (Senha@123)
  Chamados de exemplo criados
✅ Seed concluído com sucesso!
```

> **Se aparecer erro de conexão:** verifique a `DATABASE_URL` no `.env`.  
> **Se aparecer `already exists`:** os dados já estão inseridos — isso é normal.

**Confirmar os dados:**
```bash
sudo -u postgres psql helpdesk_db -c "
  SELECT 'analistas'  AS tabela, COUNT(*) AS qtd FROM analysts
  UNION ALL
  SELECT 'usuarios',  COUNT(*) FROM users
  UNION ALL
  SELECT 'chamados',  COUNT(*) FROM tickets
  UNION ALL
  SELECT 'sla_rules', COUNT(*) FROM sla_rules
  UNION ALL
  SELECT 'categorias',COUNT(*) FROM categories;"
```

Esperado: analistas=**5**, usuarios=**4**, chamados=**4**, sla_rules=**4**, categorias=**11**.

---

## 8. Configurar o serviço systemd

```bash
# ── Copiar o arquivo de serviço ───────────────────────────────────────────────
sudo cp /var/www/helpdesk/systemd/helpdesk.service /etc/systemd/system/

# ── Corrigir line endings ────────────────────────────────────────────────────
sudo sed -i 's/\r$//' /etc/systemd/system/helpdesk.service

# ── Verificar o conteúdo ─────────────────────────────────────────────────────
sudo cat /etc/systemd/system/helpdesk.service
```

O arquivo deve conter:
```ini
[Unit]
Description=TI HelpDesk API
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/helpdesk/backend
EnvironmentFile=/var/www/helpdesk/.env
ExecStart=/var/www/helpdesk/venv/bin/uvicorn main:app \
    --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Se o arquivo não existir ou estiver diferente, crie manualmente:
```bash
sudo tee /etc/systemd/system/helpdesk.service > /dev/null << 'EOF'
[Unit]
Description=TI HelpDesk API
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/helpdesk/backend
EnvironmentFile=/var/www/helpdesk/.env
ExecStart=/var/www/helpdesk/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

```bash
# ── Habilitar e iniciar ───────────────────────────────────────────────────────
sudo systemctl daemon-reload
sudo systemctl enable helpdesk
sudo systemctl start helpdesk

# ── Verificar status (deve mostrar "active (running)") ───────────────────────
sudo systemctl status helpdesk
```

**Saída esperada:**
```
● helpdesk.service - TI HelpDesk API
     Loaded: loaded (/etc/systemd/system/helpdesk.service; enabled)
     Active: active (running) since Tue 2025-xx-xx xx:xx:xx UTC
   Main PID: 12345 (uvicorn)
```

**Testar a API:**
```bash
curl -s http://localhost:8000/health
# Esperado: {"status":"ok","version":"2.0.0"}
```

Se não iniciar, veja os logs:
```bash
sudo journalctl -u helpdesk -n 50 --no-pager
```

---

## 9. Configurar o Nginx

```bash
# ── Copiar a configuração ─────────────────────────────────────────────────────
sudo cp /var/www/helpdesk/nginx/helpdesk.conf /etc/nginx/sites-available/helpdesk
sudo sed -i 's/\r$//' /etc/nginx/sites-available/helpdesk

# ── Editar o server_name ──────────────────────────────────────────────────────
sudo nano /etc/nginx/sites-available/helpdesk
```

Localize a linha `server_name` e substitua pelo seu IP ou domínio:
```nginx
# Altere de:
server_name seu-dominio.com;

# Para (exemplo com IP):
server_name 192.168.1.100;

# OU para domínio:
server_name helpdesk.empresa.com;
```

Salve: `Ctrl+X → Y → Enter`

```bash
# ── Ativar o site e desabilitar o default ────────────────────────────────────
sudo ln -sf /etc/nginx/sites-available/helpdesk /etc/nginx/sites-enabled/helpdesk
sudo rm -f /etc/nginx/sites-enabled/default

# ── Testar a configuração ─────────────────────────────────────────────────────
sudo nginx -t
```

**Saída esperada:**
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

```bash
# ── Aplicar ───────────────────────────────────────────────────────────────────
sudo systemctl restart nginx
sudo systemctl enable nginx
sudo systemctl status nginx

# ── Testar acesso ─────────────────────────────────────────────────────────────
curl -I http://localhost/
# Esperado: HTTP/1.1 200 OK

curl -s http://localhost/health
# Esperado: {"status":"ok","version":"2.0.0"}
```

---

## 10. Primeiro acesso

Abra o navegador e acesse `http://IP_DO_SERVIDOR`

### 10.1 — Painel da Equipe de TI

| Tela | URL |
|---|---|
| Login analistas | `http://IP/` |
| Painel TI (com chatbot 💬) | `http://IP/mockup.html` |

| Usuário | E-mail | Senha | Nível | Role |
|---|---|---|---|---|
| **Administrador** | admin@empresa.com | Admin@123 | N3 | admin |
| João Silva | joao@empresa.com | Senha@123 | N1 | analyst |
| Maria Santos | maria@empresa.com | Senha@123 | N2 | analyst |
| **Carlos Oliveira** | carlos.ti@empresa.com | Senha@123 | N2 | **coordinator** |
| Pedro Costa | pedro@empresa.com | Senha@123 | N3 | manager |

### 10.2 — Portal de Usuários / Solicitantes

| Tela | URL |
|---|---|
| Portal self-service | `http://IP/portal.html` |

| Usuário | E-mail | Senha |
|---|---|---|
| Ana Lima | ana@empresa.com | Senha@123 |
| Fernando Rocha | fernanda@empresa.com | Senha@123 |
| Rafael Mendes | rafael@empresa.com | Senha@123 |
| Beatriz Souza | beatriz@empresa.com | Senha@123 |

### 10.3 — Outras URLs

| URL | Descrição |
|---|---|
| `http://IP/survey.html?token=TOKEN` | Pesquisa CSAT (link enviado por e-mail) |
| `http://IP/docs` | Swagger UI — documentação e teste da API |
| `http://IP/redoc` | ReDoc — documentação alternativa |
| `http://IP/health` | Health check da API |

### ⚠ Troque TODAS as senhas imediatamente após o primeiro acesso!

---

## 11. Verificações pós-instalação

Execute todos estes testes para confirmar que o sistema está funcionando completamente:

```bash
# ── 1. API respondendo ────────────────────────────────────────────────────────
curl -s http://localhost:8000/health
# ✅ {"status":"ok","version":"2.0.0"}

# ── 2. Login de analista (painel TI) ─────────────────────────────────────────
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@empresa.com","password":"Admin@123"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('Token:', d['access_token'][:30]+'...', '| Analista:', d['analyst']['name'])"
# ✅ Token: eyJhbGci... | Analista: Administrador

# ── 3. Login de usuário (portal self-service) ─────────────────────────────────
curl -s -X POST http://localhost:8000/api/v1/auth/user/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ana@empresa.com","password":"Senha@123"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('Token OK | Usuário:', d['user']['name'])"
# ✅ Token OK | Usuário: Ana Lima

# ── 4. Chatbot respondendo ───────────────────────────────────────────────────
curl -s -X POST http://localhost:8000/api/v1/chatbot/message \
  -H "Content-Type: application/json" \
  -d '{"session_id":"teste-123","message":"olá","channel":"web"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('Chatbot:', d['state'], '|', d['response'][:60]+'...')"
# ✅ Chatbot: greeting | Olá! 👋 Sou o assistente de TI...

# ── 5. Banco com dados corretos ───────────────────────────────────────────────
sudo -u postgres psql helpdesk_db -c "
  SELECT 'analistas'       AS tabela, COUNT(*) AS qtd FROM analysts
  UNION ALL SELECT 'usuarios',        COUNT(*) FROM users
  UNION ALL SELECT 'chamados',        COUNT(*) FROM tickets
  UNION ALL SELECT 'sla_rules',       COUNT(*) FROM sla_rules
  UNION ALL SELECT 'ticket_surveys',  COUNT(*) FROM ticket_surveys
  UNION ALL SELECT 'chatbot_sessions',COUNT(*) FROM chatbot_sessions;"
# ✅ analistas=5, usuarios=4, chamados=4, sla_rules=4, surveys=0, sessions=0

# ── 6. Nginx servindo o frontend ──────────────────────────────────────────────
curl -I http://localhost/
# ✅ HTTP/1.1 200 OK

curl -I http://localhost/portal.html
# ✅ HTTP/1.1 200 OK

curl -I http://localhost/survey.html
# ✅ HTTP/1.1 200 OK

# ── 7. Todos os serviços ativos ───────────────────────────────────────────────
sudo systemctl is-active helpdesk nginx postgresql
# ✅ active / active / active
```

---

## 12. Solução de problemas

### API não inicia — status: failed

```bash
# Ver os últimos logs com contexto
sudo journalctl -u helpdesk -n 100 --no-pager

# Verificar se o .env existe e tem conteúdo
ls -la /var/www/helpdesk/.env
sudo grep -c '.' /var/www/helpdesk/.env   # deve ser > 10

# Testar importação do Python manualmente
sudo -u www-data bash -c "
  cd /var/www/helpdesk/backend
  export \$(grep -v '^#' /var/www/helpdesk/.env | grep -v '^$' | xargs)
  /var/www/helpdesk/venv/bin/python -c 'import main; print(\"Import OK\")'
"

# Verificar se a porta 8000 já está em uso
sudo ss -tlnp | grep 8000
# Se estiver, matar o processo:
# sudo kill -9 $(sudo lsof -ti:8000)
```

### ModuleNotFoundError

```bash
# Reinstalar as dependências Python
sudo /var/www/helpdesk/venv/bin/pip install --upgrade \
  -r /var/www/helpdesk/backend/requirements.txt

# Identificar o módulo que está faltando
sudo journalctl -u helpdesk -n 20 --no-pager | grep "ModuleNotFoundError"
```

### Erro de conexão com o PostgreSQL

```bash
# 1. Verificar se o PostgreSQL está rodando
sudo systemctl status postgresql

# 2. Testar conexão manualmente
psql -U helpdesk_user -d helpdesk_db -h localhost
# (Digite a senha configurada no .env)

# 3. Se der "authentication failed" — redefinir a senha no banco:
sudo -u postgres psql -c "ALTER USER helpdesk_user WITH PASSWORD 'nova_senha';"
# E atualizar também no .env:
sudo nano /var/www/helpdesk/.env
# Altere o DATABASE_URL com a nova senha
sudo systemctl restart helpdesk
```

### Nginx retorna 502 Bad Gateway

```bash
# A API não está rodando — verificar e reiniciar
sudo systemctl status helpdesk
sudo systemctl restart helpdesk

# Ver logs de erro do Nginx
sudo tail -50 /var/log/nginx/helpdesk_error.log 2>/dev/null || \
  sudo tail -50 /var/log/nginx/error.log

# Verificar se a API está respondendo na porta 8000
curl -s http://127.0.0.1:8000/health
```

### Nginx retorna 403 Forbidden

```bash
# Problema de permissões nos arquivos estáticos
sudo chown -R www-data:www-data /var/www/helpdesk/frontend
sudo chmod -R 755 /var/www/helpdesk/frontend
sudo systemctl reload nginx
```

### Permissões negadas em geral

```bash
# Reaplica permissões corretas em todos os arquivos
sudo chown -R www-data:www-data /var/www/helpdesk
sudo chmod -R 750 /var/www/helpdesk
sudo chmod -R 755 /var/www/helpdesk/frontend  # frontend precisa ser legível pelo Nginx
sudo chmod 640 /var/www/helpdesk/.env
sudo systemctl restart helpdesk nginx
```

### Seed falha com erro "already exists"

```bash
# Os dados já foram inseridos — é seguro ignorar.
# Se precisar recriar o banco do ZERO (⚠ APAGA TODOS OS DADOS):
sudo -u postgres psql -c "DROP DATABASE IF EXISTS helpdesk_db;"
sudo -u postgres psql -c "CREATE DATABASE helpdesk_db OWNER helpdesk_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE helpdesk_db TO helpdesk_user;"

sudo -u www-data bash -c "
  cd /var/www/helpdesk/backend
  export \$(grep -v '^#' /var/www/helpdesk/.env | grep -v '^$' | xargs)
  /var/www/helpdesk/venv/bin/python seed.py
"
```

### E-mails não estão sendo enviados

```bash
# 1. Verificar configuração SMTP
sudo grep SMTP /var/www/helpdesk/.env

# 2. Testar envio manualmente
sudo -u www-data bash -c "
  cd /var/www/helpdesk/backend
  export \$(grep -v '^#' /var/www/helpdesk/.env | grep -v '^$' | xargs)
  /var/www/helpdesk/venv/bin/python -c \"
from services.notification_service import send_email
ok = send_email('seu@email.com', 'Teste HelpDesk', '<h1>Funciona!</h1>')
print('Resultado:', ok)
\""

# 3. Para Gmail — use App Password, não a senha da conta
# Gere em: https://myaccount.google.com/apppasswords
# Habilite autenticação em 2 etapas antes

# 4. Para o Office 365 / Exchange
# SMTP_HOST=smtp.office365.com
# SMTP_PORT=587
# SMTP_USER=ti@empresa.com (UPN completo)
# SMTP_PASSWORD=senha_da_conta
```

### Chatbot retorna erro / IA não funciona

```bash
# 1. Verificar chave da Anthropic
sudo grep ANTHROPIC /var/www/helpdesk/.env
# A chave deve começar com sk-ant-api03-...

# 2. Testar a IA diretamente
sudo -u www-data bash -c "
  cd /var/www/helpdesk/backend
  export \$(grep -v '^#' /var/www/helpdesk/.env | grep -v '^$' | xargs)
  /var/www/helpdesk/venv/bin/python -c \"
import asyncio
from services.ai_service import analyze_ticket
r = asyncio.run(analyze_ticket('Impressora não imprime', 'Impressora HP sem papel na fila'))
print('IA OK:', r)
\""
# ✅ Esperado: {'priority': 'Baixa', 'level': 'N1', ...}
```

---

## 13. Configuração HTTPS (recomendado)

HTTPS é **essencial** em produção. Use Certbot com Let's Encrypt (gratuito).

> ⚠ Você precisa de um **domínio** com DNS apontando para o IP do servidor.
> Exemplo: `helpdesk.empresa.com` → `IP_DO_SERVIDOR`

```bash
# ── Instalar Certbot ──────────────────────────────────────────────────────────
sudo apt install -y certbot python3-certbot-nginx

# ── Obter e instalar o certificado SSL ───────────────────────────────────────
# Substitua pelo seu domínio real:
sudo certbot --nginx -d helpdesk.empresa.com

# O Certbot vai:
#  1. Perguntar seu e-mail (para notificações de renovação)
#  2. Pedir aceite dos termos
#  3. Configurar automaticamente o Nginx para HTTPS
#  4. Criar redirecionamento automático HTTP → HTTPS

# ── Testar renovação automática ───────────────────────────────────────────────
sudo certbot renew --dry-run
# ✅ "Congratulations, all simulated renewals succeeded"
```

**Após instalar o SSL, atualize o `.env`:**
```bash
sudo nano /var/www/helpdesk/.env
# Altere as duas linhas:
#   FRONTEND_URL=https://helpdesk.empresa.com
#   BASE_URL=https://helpdesk.empresa.com

# Reiniciar para aplicar
sudo systemctl restart helpdesk
```

A renovação do certificado é automática (o Certbot registra um timer no systemd).

---

## 14. Comandos do dia a dia

### Monitoramento

```bash
# Logs em tempo real (Ctrl+C para sair)
sudo journalctl -u helpdesk -f

# Apenas erros
sudo journalctl -u helpdesk -p err -n 50 --no-pager

# Status de todos os serviços
sudo systemctl status helpdesk nginx postgresql

# Uso de recursos em tempo real
htop

# Espaço em disco
df -h /var/www/helpdesk

# Conexões ativas no banco
sudo -u postgres psql -c \
  "SELECT count(*) AS conexoes FROM pg_stat_activity WHERE datname='helpdesk_db';"
```

### Gerenciamento do serviço

```bash
# Reiniciar a API (obrigatório após alterar .env ou atualizar código)
sudo systemctl restart helpdesk

# Recarregar Nginx (após alterar configuração do Nginx)
sudo systemctl reload nginx

# Parar temporariamente (manutenção)
sudo systemctl stop helpdesk

# Ver detalhes do processo
sudo systemctl show helpdesk --property=MainPID,ActiveState,MemoryCurrent
```

### Backup do banco de dados

```bash
# Backup manual com timestamp
BKDATE=$(date +%Y%m%d_%H%M)
sudo mkdir -p /var/backups/helpdesk
sudo -u postgres pg_dump helpdesk_db | gzip > /var/backups/helpdesk/backup_${BKDATE}.sql.gz
echo "✅ Backup salvo em: /var/backups/helpdesk/backup_${BKDATE}.sql.gz"

# Listar backups existentes
ls -lh /var/backups/helpdesk/

# Restaurar um backup
# sudo gunzip -c /var/backups/helpdesk/backup_YYYYMMDD_HHMM.sql.gz | sudo -u postgres psql helpdesk_db
```

### Backup automático (cron diário às 2h)

```bash
# Criar script de backup se não existir
sudo tee /var/www/helpdesk/scripts/backup.sh > /dev/null << 'EOF'
#!/bin/bash
BKDIR=/var/backups/helpdesk
mkdir -p $BKDIR
pg_dump helpdesk_db | gzip > $BKDIR/backup_$(date +%Y%m%d_%H%M).sql.gz
# Manter apenas os últimos 30 backups
ls -t $BKDIR/backup_*.sql.gz | tail -n +31 | xargs rm -f
echo "Backup concluído: $(date)"
EOF
sudo chmod +x /var/www/helpdesk/scripts/backup.sh

# Agendar via cron (como usuário postgres)
(sudo crontab -u postgres -l 2>/dev/null; echo "0 2 * * * /var/www/helpdesk/scripts/backup.sh >> /var/log/helpdesk_backup.log 2>&1") | sudo crontab -u postgres -
echo "✅ Backup automático configurado para 02:00 diariamente"
```

### Resetar senha de um usuário do portal

```bash
# Via API — precisa de token de admin
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@empresa.com","password":"Admin@123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Descobrir o ID do usuário pelo e-mail
curl -s "http://localhost:8000/api/v1/users?search=ana" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; [print(u['id'], u['name'], u['email']) for u in json.load(sys.stdin)]"

# Definir nova senha (substitua 1 pelo ID correto)
curl -s -X POST http://localhost:8000/api/v1/users/1/set-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password":"NovaSenha@456"}'
```

### Atualizar o sistema para nova versão

```bash
# 1. Fazer backup antes de qualquer atualização
sudo -u postgres pg_dump helpdesk_db | gzip > /var/backups/helpdesk/pre-update-$(date +%Y%m%d).sql.gz

# 2. Enviar novo helpdesk.zip para o servidor
# (via SCP no seu computador local)

# 3. Extrair e copiar os novos arquivos
cd /tmp
unzip -o /tmp/helpdesk_novo.zip -d helpdesk_novo
sudo cp -r /tmp/helpdesk_novo/* /var/www/helpdesk/
sudo chown -R www-data:www-data /var/www/helpdesk

# 4. Atualizar dependências Python se necessário
sudo /var/www/helpdesk/venv/bin/pip install -r /var/www/helpdesk/backend/requirements.txt

# 5. Aplicar migrações de banco se houver
# sudo -u www-data bash -c "cd /var/www/helpdesk/backend && /var/www/helpdesk/venv/bin/python seed.py"

# 6. Reiniciar
sudo systemctl restart helpdesk
curl -s http://localhost:8000/health
```

---

## Arquitetura do sistema

```
                    Internet
                        │
                        ▼
              ┌─── Nginx :80 / :443 ────────────────────────────┐
              │                                                  │
              │  /              → frontend/index.html           │
              │  /mockup.html   → painel TI (+ chatbot 💬)      │
              │  /portal.html   → portal self-service            │
              │  /survey.html   → pesquisa CSAT                  │
              │  /api/v1/*      → proxy → :8000                  │
              │  /docs          → Swagger UI                     │
              └──────────────────────────────────────────────────┘
                                    │
                                    ▼
                          FastAPI uvicorn :8000
                         (2 workers, systemd)
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              PostgreSQL     Anthropic API    Scheduler
              helpdesk_db   claude-sonnet    (APScheduler)
                            (IA + chatbot)   SLA check 5min
                                    │               │
                              ┌─────┘         ┌────┘
                              ▼               ▼
                          opcional:       E-mails (SMTP)
                        Teams Webhook   + Teams Adaptive Cards
```

---

*TI HelpDesk v2.0 — Sistema de chamados com IA, chatbot, notificações Teams e CSAT*  
*Projetado para empresas de 900 a 1.200 funcionários*
