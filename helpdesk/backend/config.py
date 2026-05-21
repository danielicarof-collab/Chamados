from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://helpdesk_user:senha_forte@localhost:5432/helpdesk_db"
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    ANTHROPIC_API_KEY: str = ""

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_ENV: str = "development"
    FRONTEND_URL: str = "http://localhost:8000"

    # Base URL para links nos e-mails e pesquisa CSAT (sem barra no final)
    # Em produção: http://IP_DO_SERVIDOR ou https://seu-dominio.com
    BASE_URL: str = "http://localhost:8000"

    # SMTP — deixe SMTP_USER em branco para desativar envio de e-mails
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "TI HelpDesk <ti@empresa.com>"

    # E-mail da fila de TI — para notificações de novos chamados à equipe
    TEAM_EMAIL: Optional[str] = None

    # Microsoft Teams — Incoming Webhook URL (opcional)
    # Obtenha em: Teams → Canal → Conectores → Incoming Webhook
    TEAMS_WEBHOOK_URL: Optional[str] = None

    # Empresa — aparece nos e-mails e no portal
    COMPANY_NAME: str = "Empresa"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
