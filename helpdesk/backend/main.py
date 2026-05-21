import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from middleware.cors import setup_cors
from scheduler import start_scheduler, stop_scheduler
from routes import auth, tickets, users, analysts, departments, categories, sla, reports, ai
from routes import chatbot, survey, portal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="TI HelpDesk API",
    description=(
        "Sistema de chamados de TI com priorização automática por IA, "
        "chatbot de autoatendimento, notificações Teams e pesquisa CSAT."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

setup_cors(app)

PREFIX = "/api/v1"

# ── Rotas principais ──────────────────────────────────────────────────────────
app.include_router(auth.router,        prefix=PREFIX)
app.include_router(tickets.router,     prefix=PREFIX)
app.include_router(users.router,       prefix=PREFIX)
app.include_router(analysts.router,    prefix=PREFIX)
app.include_router(departments.router, prefix=PREFIX)
app.include_router(categories.router,  prefix=PREFIX)
app.include_router(sla.router,         prefix=PREFIX)
app.include_router(reports.router,     prefix=PREFIX)
app.include_router(ai.router,          prefix=PREFIX)

# ── Novas rotas ───────────────────────────────────────────────────────────────
app.include_router(chatbot.router,     prefix=PREFIX)   # POST /api/v1/chatbot/message
app.include_router(survey.router,      prefix=PREFIX)   # GET/POST /api/v1/survey/{token}
app.include_router(portal.router,      prefix=PREFIX)   # GET/POST /api/v1/portal/tickets


@app.get("/health", tags=["infra"])
def health():
    return {"status": "ok", "version": "2.0.0"}


# ── Frontend estático ─────────────────────────────────────────────────────────
# Monta o frontend APÓS todas as rotas de API (para não sobrescrever rotas).
# Em produção o Nginx serve o frontend diretamente, mas isso garante fallback.
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")


# ── Handler de exceções não tratadas ─────────────────────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception(request, exc):
    logger.error("Erro não tratado: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"},
    )
