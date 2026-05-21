from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import get_db
from models.analyst import Analyst
from models.user import User
from schemas.analyst import LoginRequest, Token, AnalystOut
from schemas.user import UserLogin, UserToken, UserOut
from middleware.auth import create_access_token, get_current_analyst, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Analistas ──────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token, summary="Login de analista/admin")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    analyst = (
        db.query(Analyst)
        .filter(Analyst.email == data.email, Analyst.active == True)
        .first()
    )
    if not analyst or not pwd_context.verify(data.password, analyst.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )
    analyst.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(analyst)

    token = create_access_token({"sub": str(analyst.id), "type": "analyst"})
    return {"access_token": token, "token_type": "bearer", "analyst": analyst}


@router.post("/refresh", response_model=Token, summary="Renovar token de analista")
def refresh_token(current: Analyst = Depends(get_current_analyst)):
    token = create_access_token({"sub": str(current.id), "type": "analyst"})
    return {"access_token": token, "token_type": "bearer", "analyst": current}


@router.get("/me", response_model=AnalystOut, summary="Dados do analista autenticado")
def me(current: Analyst = Depends(get_current_analyst)):
    return current


# ── Usuários (Portal Self-Service) ────────────────────────────────────────────

@router.post("/user/login", response_model=UserToken, summary="Login de usuário no portal")
def user_login(data: UserLogin, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.email == data.email, User.active == True)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail não encontrado ou usuário inativo",
        )
    if not user.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Senha não configurada. Solicite ao administrador de TI.",
        )
    if not pwd_context.verify(data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Senha incorreta",
        )
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "type": "user"})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/user/me", response_model=UserOut, summary="Dados do usuário autenticado")
def user_me(current: User = Depends(get_current_user)):
    return current
