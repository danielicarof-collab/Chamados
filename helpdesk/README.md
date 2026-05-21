# TI HelpDesk — Sistema de Chamados

Sistema completo de abertura, gestão e resolução de chamados de TI com priorização automática por IA (Claude).

## Funcionalidades

- Abertura de chamados com análise automática de prioridade via IA
- Fluxo de escalada N1 → N2 → N3 (manual e automático por SLA)
- SLA configurável por prioridade com alertas
- Dashboard com KPIs em tempo real
- Relatórios gerenciais e exportação CSV
- Autenticação JWT com perfis (analyst / manager / admin)

## Stack

| Componente | Tecnologia |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Banco de dados | PostgreSQL 14+ |
| ORM | SQLAlchemy 2.0 |
| IA | Anthropic Claude (claude-sonnet-4-20250514) |
| Agendador | APScheduler |
| Frontend | HTML/JS puro (dark theme) |
| Servidor web | Nginx + Uvicorn |

---

## Instalação (Ubuntu 22.04 LTS)

### Pré-requisitos

```bash
# Python 3.11, PostgreSQL e Nginx são instalados automaticamente pelo script
```

### 1. Clonar/copiar o projeto

```bash
git clone <seu-repo> /var/www/helpdesk
# ou transferir os arquivos para o servidor
```

### 2. Instalar automaticamente

```bash
chmod +x scripts/install.sh
sudo bash scripts/install.sh
```

O script realiza:
1. Atualiza pacotes do sistema
2. Instala Python 3.11, PostgreSQL e Nginx
3. Cria o banco de dados e usuário
4. Cria virtualenv e instala dependências
5. Cria as tabelas e insere dados iniciais
6. Configura e inicia serviço systemd
7. Configura Nginx como reverse proxy

### 3. Configurar variáveis de ambiente

```bash
sudo nano /var/www/helpdesk/.env
```

Obrigatórias:
```env
ANTHROPIC_API_KEY=sk-ant-...          # Sua chave da API Anthropic
SECRET_KEY=chave-aleatoria-longa      # python -c "import secrets; print(secrets.token_hex(32))"
DATABASE_URL=postgresql://helpdesk_user:SENHA@localhost:5432/helpdesk_db
FRONTEND_URL=http://seu-dominio.com
```

### 4. Reiniciar serviço

```bash
sudo systemctl restart helpdesk
sudo systemctl status helpdesk
```

---

## Instalação para desenvolvimento

```bash
# 1. Criar virtualenv
cd helpdesk/backend
python3.11 -m venv ../venv
source ../venv/bin/activate      # Linux/Mac
# ..\venv\Scripts\activate       # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar .env
cp ../.env.example ../.env
# editar .env com suas configurações

# 4. Criar banco
createdb helpdesk_db

# 5. Criar tabelas e dados iniciais
python seed.py

# 6. Iniciar servidor
uvicorn main:app --reload --port 8000
```

Acesse:
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Frontend: abra `frontend/index.html` no navegador

---

## Login inicial

| E-mail | Senha | Nível | Papel |
|---|---|---|---|
| admin@empresa.com | Admin@123 | N1 | admin |
| joao@empresa.com | Senha@123 | N1 | analyst |
| maria@empresa.com | Senha@123 | N2 | analyst |
| pedro@empresa.com | Senha@123 | N3 | manager |

---

## Endpoints principais

```
POST   /api/v1/auth/login
GET    /api/v1/tickets
POST   /api/v1/tickets
GET    /api/v1/tickets/{id}
POST   /api/v1/tickets/{id}/escalate
POST   /api/v1/tickets/{id}/resolve
POST   /api/v1/ai/analyze
GET    /api/v1/reports/kpis
GET    /api/v1/reports/export
```

Documentação completa: http://localhost:8000/docs

---

## Gerenciamento

```bash
# Ver logs em tempo real
sudo journalctl -u helpdesk -f

# Reiniciar API
sudo systemctl restart helpdesk

# Backup do banco
sudo bash scripts/backup.sh

# Aplicar migrações após atualização
sudo bash scripts/migrate.sh

# Atualizar dependências Python
source /var/www/helpdesk/venv/bin/activate
pip install -r /var/www/helpdesk/backend/requirements.txt
sudo systemctl restart helpdesk
```

---

## Estrutura do projeto

```
helpdesk/
├── backend/
│   ├── main.py              # Entry point FastAPI
│   ├── config.py            # Configurações (.env)
│   ├── database.py          # Conexão SQLAlchemy
│   ├── scheduler.py         # Jobs automáticos (SLA a cada 5 min)
│   ├── seed.py              # Dados iniciais
│   ├── models/              # Modelos SQLAlchemy
│   ├── schemas/             # Schemas Pydantic
│   ├── routes/              # Endpoints FastAPI
│   ├── services/            # Lógica de negócio (IA, SLA, escalada)
│   └── middleware/          # JWT, CORS
├── frontend/
│   └── modules/api.js       # Módulo de integração REST
├── alembic/                 # Migrações de banco
├── nginx/helpdesk.conf      # Configuração Nginx
├── systemd/helpdesk.service # Serviço systemd
├── scripts/                 # install.sh, backup.sh, migrate.sh
└── .env.example
```

---

## SLA padrão

| Prioridade | 1ª Resposta | Resolução | Esc. N1→N2 | Esc. N2→N3 |
|---|---|---|---|---|
| Crítica | 1h | 4h | 2h | 3h |
| Alta | 4h | 8h | 6h | 7h |
| Média | 8h | 24h | 20h | 23h |
| Baixa | 24h | 72h | 68h | 71h |
