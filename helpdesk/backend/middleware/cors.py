from fastapi.middleware.cors import CORSMiddleware
from config import settings


def setup_cors(app) -> None:
    # Em produção, o Nginx serve frontend e API na mesma origem (sem CORS).
    # Esta configuração cobre acesso direto à porta 8000 e ambientes de dev.
    origins = [
        settings.FRONTEND_URL,
        # Dev local
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5500",
        # Live Server (VSCode)
        "http://127.0.0.1:8080",
    ]

    # Em dev, permite qualquer origem para facilitar testes
    if settings.APP_ENV != "production":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
