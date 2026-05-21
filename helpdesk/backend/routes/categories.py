from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.category import Category
from models.analyst import Analyst
from schemas.ticket import CategoryCreate, CategoryUpdate, CategoryOut
from middleware.auth import get_current_analyst

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    return db.query(Category).filter(Category.active == True).order_by(Category.name).all()


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    if db.query(Category).filter(Category.name == data.name).first():
        raise HTTPException(status_code=409, detail="Categoria já existe")
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/{cat_id}", response_model=CategoryOut)
def get_category(
    cat_id: int,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    category = db.query(Category).filter(Category.id == cat_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    return category


@router.put("/{cat_id}", response_model=CategoryOut)
def update_category(
    cat_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    category = db.query(Category).filter(Category.id == cat_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{cat_id}", status_code=204)
def delete_category(
    cat_id: int,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    category = db.query(Category).filter(Category.id == cat_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    category.active = False
    db.commit()
