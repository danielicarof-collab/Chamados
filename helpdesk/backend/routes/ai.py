from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.ticket import Ticket
from models.analyst import Analyst
from services.ai_service import analyze_ticket, suggest_action
from middleware.auth import get_current_analyst

router = APIRouter(prefix="/ai", tags=["ai"])


class AnalyzeRequest(BaseModel):
    title: str
    description: str
    category: Optional[str] = ""
    impact: Optional[str] = ""


@router.post("/analyze")
async def ai_analyze(
    data: AnalyzeRequest,
    _: Analyst = Depends(get_current_analyst),
):
    result = await analyze_ticket(
        title=data.title,
        description=data.description,
        category=data.category or "",
        impact=data.impact or "",
    )
    return result


@router.post("/suggest/{ticket_id}")
async def ai_suggest(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    return await suggest_action(ticket)
