from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.department import Department
from models.analyst import Analyst
from schemas.user import DepartmentCreate, DepartmentUpdate, DepartmentOut
from middleware.auth import get_current_analyst

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentOut])
def list_departments(
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    return db.query(Department).order_by(Department.name).all()


@router.post("", response_model=DepartmentOut, status_code=201)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    if db.query(Department).filter(Department.name == data.name).first():
        raise HTTPException(status_code=409, detail="Departamento já existe")
    dept = Department(**data.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/{dept_id}", response_model=DepartmentOut)
def get_department(
    dept_id: int,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Departamento não encontrado")
    return dept


@router.put("/{dept_id}", response_model=DepartmentOut)
def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Departamento não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(dept, field, value)
    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/{dept_id}", status_code=204)
def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Departamento não encontrado")
    dept.active = False
    db.commit()
