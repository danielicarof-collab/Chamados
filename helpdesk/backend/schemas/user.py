from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    active: bool = True


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class DepartmentOut(DepartmentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Usuário ────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    extension: Optional[str] = None
    department_id: Optional[int] = None
    active: bool = True


class UserCreate(UserBase):
    """Criação de usuário via painel administrativo — senha opcional."""
    password: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    extension: Optional[str] = None
    department_id: Optional[int] = None
    active: Optional[bool] = None
    password: Optional[str] = None  # permite redefinição de senha


class UserOut(UserBase):
    id: int
    created_at: datetime
    department: Optional[DepartmentOut] = None

    class Config:
        from_attributes = True


# ── Auth do Portal ─────────────────────────────────────────────────────────────

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserToken(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


class UserSetPassword(BaseModel):
    """Usuário define/altera própria senha."""
    current_password: Optional[str] = None
    new_password: str
