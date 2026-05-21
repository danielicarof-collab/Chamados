from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import Optional

from database import get_db
from models.user import User
from models.analyst import Analyst
from schemas.user import UserCreate, UserUpdate, UserOut
from middleware.auth import get_current_analyst, require_admin

router = APIRouter(prefix="/users", tags=["users"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("", response_model=list[UserOut])
def list_users(
    active: Optional[bool] = None,
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    q = db.query(User)
    if active is not None:
        q = q.filter(User.active == active)
    if department_id:
        q = q.filter(User.department_id == department_id)
    if search:
        q = q.filter(User.name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))
    return q.order_by(User.name).offset((page - 1) * per_page).limit(per_page).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")

    payload = data.model_dump()
    # Hash da senha se fornecida
    if payload.get("password"):
        payload["password"] = pwd_context.hash(payload["password"])

    user = User(**payload)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    changes = data.model_dump(exclude_unset=True)
    if "password" in changes and changes["password"]:
        changes["password"] = pwd_context.hash(changes["password"])

    for field, value in changes.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.active = False
    db.commit()


@router.post("/{user_id}/set-password", summary="Definir senha do usuário (admin)")
def set_user_password(
    user_id: int,
    data: dict,
    db: Session = Depends(get_db),
    _: Analyst = Depends(require_admin),
):
    """Permite que um admin defina ou redefina a senha de um usuário."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    new_pw = data.get("password", "")
    if not new_pw or len(new_pw) < 8:
        raise HTTPException(status_code=422, detail="Senha deve ter pelo menos 8 caracteres")

    user.password = pwd_context.hash(new_pw)
    db.commit()
    return {"message": f"Senha definida para {user.name}"}
