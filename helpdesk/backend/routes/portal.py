"""
Portal de autoatendimento para solicitantes (usuários finais).
Autenticação via token de usuário (type=user).
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import Optional

from database import get_db
from models.ticket import Ticket
from models.timeline import TicketTimeline
from models.user import User
from models.category import Category
from schemas.ticket import TicketOut, PaginatedTickets
from services.sla_service import calculate_sla_deadlines
from services.ai_service import analyze_ticket
from services.notification_service import notify_ticket_created
from services.teams_service import send_teams_notification
from middleware.auth import get_current_user

router = APIRouter(prefix="/portal", tags=["portal"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _next_ticket_number(db: Session) -> str:
    count = db.query(Ticket).count()
    return f"TI-{count + 1:04d}"


@router.get("/tickets", response_model=PaginatedTickets, summary="Meus chamados")
def list_my_tickets(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista os chamados do usuário autenticado, do mais recente ao mais antigo."""
    q = db.query(Ticket).filter(Ticket.user_id == current_user.id)
    if status:
        q = q.filter(Ticket.status == status)

    total = q.count()
    items = (
        q.order_by(Ticket.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


@router.get("/tickets/{ticket_id}", response_model=TicketOut, summary="Detalhes do chamado")
def get_my_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.user_id == current_user.id,
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    return ticket


@router.post("/tickets", response_model=TicketOut, status_code=201, summary="Abrir chamado")
async def create_my_ticket(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Abre um chamado diretamente pelo portal.
    A IA classifica prioridade e nível automaticamente.
    """
    title       = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    impact      = str(data.get("impact", "")).strip()
    equipment   = str(data.get("equipment", "")).strip()
    category_id = data.get("category_id")

    if not title or not description:
        raise HTTPException(status_code=422, detail="Título e descrição são obrigatórios")

    # Buscar categoria para contexto
    category_name = ""
    if category_id:
        cat = db.query(Category).filter(Category.id == category_id).first()
        if cat:
            category_name = cat.name

    # Classificação por IA
    try:
        ai_result = await analyze_ticket(
            title=title,
            description=description,
            category=category_name,
            impact=impact,
        )
    except Exception:
        ai_result = {
            "priority": "Média", "level": "N1",
            "justification": "Análise automática", "confidence": 0.5,
        }

    ticket_num = _next_ticket_number(db)
    ticket = Ticket(
        ticket_number=ticket_num,
        title=title,
        description=description,
        category_id=category_id,
        priority=ai_result.get("priority", "Média"),
        priority_source="ai",
        status="Aberto",
        level=ai_result.get("level", "N1"),
        impact=impact,
        equipment=equipment,
        user_id=current_user.id,
        department_id=current_user.department_id,
        ai_analysis=ai_result,
    )
    db.add(ticket)
    db.flush()

    calculate_sla_deadlines(db, ticket)

    if ticket.priority == "Crítica" and ticket.level == "N1":
        ticket.level = "N2"
        db.add(TicketTimeline(
            ticket_id=ticket.id,
            type="escalate",
            action="Escalado automaticamente para N2 (prioridade Crítica)",
            by_name="Sistema",
            icon="arrow-up",
            icon_color="red",
        ))

    db.add(TicketTimeline(
        ticket_id=ticket.id,
        type="open",
        action=f"Chamado {ticket_num} aberto pelo portal por {current_user.name}",
        by_name=current_user.name,
        icon="ticket",
        icon_color="blue",
    ))
    db.add(TicketTimeline(
        ticket_id=ticket.id,
        type="ai",
        action=f"Prioridade '{ticket.priority}' definida pela IA",
        note=ai_result.get("justification", ""),
        by_name="IA",
        icon="robot",
        icon_color="purple",
    ))

    db.commit()
    db.refresh(ticket)

    # Notificações (e-mail + Teams opcional)
    try:
        notify_ticket_created(ticket, db)
    except Exception:
        pass
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(send_teams_notification(ticket, "created"))
    except Exception:
        pass

    return ticket


@router.put("/profile/password", summary="Alterar própria senha")
def change_password(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_pw = data.get("current_password", "")
    new_pw     = data.get("new_password", "")

    if not new_pw or len(new_pw) < 8:
        raise HTTPException(status_code=422, detail="A nova senha deve ter pelo menos 8 caracteres")

    if current_user.password:
        if not pwd_context.verify(current_pw, current_user.password):
            raise HTTPException(status_code=401, detail="Senha atual incorreta")

    current_user.password = pwd_context.hash(new_pw)
    db.commit()
    return {"message": "Senha alterada com sucesso"}
