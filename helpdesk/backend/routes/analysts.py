from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import Optional

from database import get_db
from models.analyst import Analyst
from schemas.analyst import AnalystCreate, AnalystUpdate, AnalystOut
from middleware.auth import get_current_analyst, require_admin

router = APIRouter(prefix="/analysts", tags=["analysts"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("", response_model=list[AnalystOut])
def list_analysts(
    active: Optional[bool] = None,
    level: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    q = db.query(Analyst)
    if active is not None:
        q = q.filter(Analyst.active == active)
    if level:
        q = q.filter(Analyst.level == level)
    return q.order_by(Analyst.name).offset((page - 1) * per_page).limit(per_page).all()


@router.post("", response_model=AnalystOut, status_code=201)
def create_analyst(
    data: AnalystCreate,
    db: Session = Depends(get_db),
    _: Analyst = Depends(require_admin),
):
    if db.query(Analyst).filter(Analyst.email == data.email).first():
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")

    payload = data.model_dump()
    payload["password"] = pwd_context.hash(payload["password"])
    analyst = Analyst(**payload)
    db.add(analyst)
    db.commit()
    db.refresh(analyst)
    return analyst


@router.get("/{analyst_id}", response_model=AnalystOut)
def get_analyst(
    analyst_id: int,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    analyst = db.query(Analyst).filter(Analyst.id == analyst_id).first()
    if not analyst:
        raise HTTPException(status_code=404, detail="Analista não encontrado")
    return analyst


@router.put("/{analyst_id}", response_model=AnalystOut)
def update_analyst(
    analyst_id: int,
    data: AnalystUpdate,
    db: Session = Depends(get_db),
    _: Analyst = Depends(require_admin),
):
    analyst = db.query(Analyst).filter(Analyst.id == analyst_id).first()
    if not analyst:
        raise HTTPException(status_code=404, detail="Analista não encontrado")

    changes = data.model_dump(exclude_unset=True)
    if "password" in changes and changes["password"]:
        changes["password"] = pwd_context.hash(changes["password"])

    for field, value in changes.items():
        setattr(analyst, field, value)

    db.commit()
    db.refresh(analyst)
    return analyst


@router.delete("/{analyst_id}", status_code=204)
def delete_analyst(
    analyst_id: int,
    db: Session = Depends(get_db),
    _: Analyst = Depends(require_admin),
):
    analyst = db.query(Analyst).filter(Analyst.id == analyst_id).first()
    if not analyst:
        raise HTTPException(status_code=404, detail="Analista não encontrado")
    analyst.active = False
    db.commit()
