from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class CategoryBase(BaseModel):
    name: str
    parent_id: Optional[int] = None
    default_sla: Optional[str] = None
    default_level: Optional[str] = None
    active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    default_sla: Optional[str] = None
    default_level: Optional[str] = None
    active: Optional[bool] = None


class CategoryOut(CategoryBase):
    id: int

    class Config:
        from_attributes = True


class SLARuleBase(BaseModel):
    priority: str
    response_hours: int
    resolution_hours: int
    escalation_n1_hours: Optional[int] = None
    escalation_n2_hours: Optional[int] = None
    color: Optional[str] = None
    active: bool = True


class SLARuleCreate(SLARuleBase):
    pass


class SLARuleUpdate(BaseModel):
    response_hours: Optional[int] = None
    resolution_hours: Optional[int] = None
    escalation_n1_hours: Optional[int] = None
    escalation_n2_hours: Optional[int] = None
    color: Optional[str] = None
    active: Optional[bool] = None


class SLARuleOut(SLARuleBase):
    id: int

    class Config:
        from_attributes = True


class TimelineOut(BaseModel):
    id: int
    ticket_id: int
    type: Optional[str] = None
    action: str
    note: Optional[str] = None
    by_analyst: Optional[int] = None
    by_name: Optional[str] = None
    icon: Optional[str] = None
    icon_color: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Slim nested models to avoid circular imports
class UserSlim(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    extension: Optional[str] = None

    class Config:
        from_attributes = True


class AnalystSlim(BaseModel):
    id: int
    name: str
    email: str
    level: str
    role: str

    class Config:
        from_attributes = True


class DepartmentSlim(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class TicketBase(BaseModel):
    title: str
    description: str
    category_id: Optional[int] = None
    priority: str
    impact: Optional[str] = None
    equipment: Optional[str] = None
    user_id: int
    department_id: Optional[int] = None
    ai_analysis: Optional[Any] = None


class TicketCreate(TicketBase):
    priority_source: str = "ai"
    level: str = "N1"


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    priority: Optional[str] = None
    priority_source: Optional[str] = None
    status: Optional[str] = None
    level: Optional[str] = None
    impact: Optional[str] = None
    equipment: Optional[str] = None
    analyst_id: Optional[int] = None
    department_id: Optional[int] = None


class TicketOut(BaseModel):
    id: int
    ticket_number: str
    title: str
    description: str
    category_id: Optional[int] = None
    priority: str
    priority_source: str
    status: str
    level: str
    impact: Optional[str] = None
    equipment: Optional[str] = None
    user_id: Optional[int] = None
    analyst_id: Optional[int] = None
    department_id: Optional[int] = None
    ai_analysis: Optional[Any] = None
    sla_deadline: Optional[datetime] = None
    sla_response_deadline: Optional[datetime] = None
    sla_responded_at: Optional[datetime] = None
    sla_percentage: int = 0
    sla_breached: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    timeline: List[TimelineOut] = []
    user: Optional[UserSlim] = None
    analyst: Optional[AnalystSlim] = None
    category: Optional[CategoryOut] = None
    department: Optional[DepartmentSlim] = None

    class Config:
        from_attributes = True


class TicketListOut(BaseModel):
    id: int
    ticket_number: str
    title: str
    priority: str
    status: str
    level: str
    user_id: Optional[int] = None
    analyst_id: Optional[int] = None
    department_id: Optional[int] = None
    sla_percentage: int = 0
    sla_breached: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: Optional[UserSlim] = None
    analyst: Optional[AnalystSlim] = None
    category: Optional[CategoryOut] = None

    class Config:
        from_attributes = True


class EscalateRequest(BaseModel):
    nivel: str
    reason: str


class AssignRequest(BaseModel):
    analyst_id: int


class CommentRequest(BaseModel):
    note: str
    type: str = "comment"


class ResolveRequest(BaseModel):
    note: str


class ChangePriorityRequest(BaseModel):
    priority: str
    reason: str


class PaginatedTickets(BaseModel):
    items: List[TicketListOut]
    total: int
    page: int
    per_page: int
    pages: int
