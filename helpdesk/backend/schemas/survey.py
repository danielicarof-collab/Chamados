from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SurveyPublicOut(BaseModel):
    """Dados visíveis ao solicitante na página da pesquisa."""
    token: str
    ticket_number: str
    ticket_title: str
    resolved_at: Optional[datetime] = None
    already_answered: bool = False

    class Config:
        from_attributes = True


class SurveyAnswer(BaseModel):
    score: int = Field(ge=1, le=5, description="Nota de 1 (péssimo) a 5 (excelente)")
    comment: Optional[str] = Field(None, max_length=1000)
    resolved_confirmed: bool = Field(
        description="True = problema resolvido / False = problema não resolvido (reabre chamado)"
    )


class SurveyOut(BaseModel):
    id: int
    ticket_id: int
    token: str
    score: Optional[int] = None
    comment: Optional[str] = None
    resolved_confirmed: Optional[bool] = None
    sent_at: datetime
    answered_at: Optional[datetime] = None

    class Config:
        from_attributes = True
