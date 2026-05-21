from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import datetime

# Roles disponíveis para analistas
AnalystRole = Literal["analyst", "coordinator", "manager", "admin"]
AnalystLevel = Literal["N1", "N2", "N3"]


class AnalystBase(BaseModel):
    name: str
    email: EmailStr
    level: AnalystLevel                  # N1 | N2 | N3
    role: AnalystRole = "analyst"        # analyst | coordinator | manager | admin
    active: bool = True


class AnalystCreate(AnalystBase):
    password: str


class AnalystUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    level: Optional[AnalystLevel] = None
    role: Optional[AnalystRole] = None
    active: Optional[bool] = None
    password: Optional[str] = None


class AnalystOut(AnalystBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    analyst: AnalystOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
