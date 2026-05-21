from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from database import get_db
from models.analyst import Analyst
from models.user import User
from config import settings

# Analistas usam /api/v1/auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _decode_token(token: str) -> dict:
    """Decodifica o JWT e retorna o payload. Lança HTTP 401 em caso de falha."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise exc
    return payload


# ── Analistas ──────────────────────────────────────────────────────────────────

def get_current_analyst(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Analyst:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(token)

    # Aceita tokens antigos (sem claim "type") como analista para retrocompatibilidade
    token_type = payload.get("type", "analyst")
    if token_type != "analyst":
        raise HTTPException(status_code=403, detail="Token não é de analista")

    analyst_id = payload.get("sub")
    if analyst_id is None:
        raise HTTPException(status_code=401, detail="Token inválido")

    analyst = (
        db.query(Analyst)
        .filter(Analyst.id == int(analyst_id), Analyst.active == True)
        .first()
    )
    if analyst is None:
        raise HTTPException(status_code=401, detail="Analista não encontrado ou inativo")
    return analyst


def require_coordinator(analyst: Analyst = Depends(get_current_analyst)) -> Analyst:
    """Permite: coordinator, manager, admin."""
    if analyst.role not in ("coordinator", "manager", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Acesso restrito a coordenadores, gestores e administradores",
        )
    return analyst


def require_manager(analyst: Analyst = Depends(get_current_analyst)) -> Analyst:
    """Permite: manager, admin."""
    if analyst.role not in ("manager", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Acesso restrito a gestores e administradores",
        )
    return analyst


def require_admin(analyst: Analyst = Depends(get_current_analyst)) -> Analyst:
    if analyst.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return analyst


# ── Usuários (portal self-service) ────────────────────────────────────────────

# Usuários usam /api/v1/auth/user/login
oauth2_user_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/user/login", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_user_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(token)

    token_type = payload.get("type")
    if token_type != "user":
        raise HTTPException(status_code=403, detail="Token não é de usuário")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = (
        db.query(User)
        .filter(User.id == int(user_id), User.active == True)
        .first()
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")
    return user
