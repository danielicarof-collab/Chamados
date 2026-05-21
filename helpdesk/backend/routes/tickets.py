"""
Rotas de chamados com integração completa de notificações,
pesquisa CSAT e Teams (notificações síncronas para confiabilidade).
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.ticket import Ticket
from models.timeline import TicketTimeline
from models.analyst import Analyst
from schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketOut,
    PaginatedTickets,
    EscalateRequest,
    AssignRequest,
    CommentRequest,
    ResolveRequest,
    ChangePriorityRequest,
)
from services.sla_service import calculate_sla_deadlines
from services.escalation_service import manual_escalate
from services.notification_service import (
    notify_ticket_created,
    notify_ticket_assigned,
    notify_ticket_commented,
    notify_ticket_escalated,
)
from services.survey_service import create_and_send_survey
from middleware.auth import get_current_analyst

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tickets", tags=["tickets"])


def _next_ticket_number(db: Session) -> str:
    count = db.query(Ticket).count()
    return f"TI-{count + 1:04d}"


def _get_ticket_or_404(ticket_id: int, db: Session) -> Ticket:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    return ticket


def _try_teams(ticket, event: str) -> None:
    """Dispara Teams notification de forma não-bloqueante (ignora erros)."""
    try:
        import asyncio
        from services.teams_service import send_teams_notification
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(send_teams_notification(ticket, event))
    except Exception as exc:
        logger.debug("Teams notification falhou silenciosamente: %s", exc)


def _get_level_emails(level: str, db: Session) -> list[str]:
    """Retorna e-mails dos analistas ativos do nível especificado."""
    analysts = db.query(Analyst).filter(
        Analyst.level == level, Analyst.active == True
    ).all()
    return [a.email for a in analysts if a.email]


# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedTickets)
def list_tickets(
    status: Optional[str] = None,
    level: Optional[str] = None,
    priority: Optional[str] = None,
    analyst_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    q = db.query(Ticket)
    if status:
        q = q.filter(Ticket.status == status)
    if level:
        q = q.filter(Ticket.level == level)
    if priority:
        q = q.filter(Ticket.priority == priority)
    if analyst_id:
        q = q.filter(Ticket.analyst_id == analyst_id)
    if search:
        q = q.filter(
            Ticket.title.ilike(f"%{search}%") | Ticket.ticket_number.ilike(f"%{search}%")
        )

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


@router.post("", response_model=TicketOut, status_code=201)
def create_ticket(
    data: TicketCreate,
    db: Session = Depends(get_db),
    current: Analyst = Depends(get_current_analyst),
):
    ticket = Ticket(
        ticket_number=_next_ticket_number(db),
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        priority=data.priority,
        priority_source=data.priority_source,
        status="Aberto",
        level=data.level,
        impact=data.impact,
        equipment=data.equipment,
        user_id=data.user_id,
        department_id=data.department_id,
        ai_analysis=data.ai_analysis,
    )
    db.add(ticket)
    db.flush()

    calculate_sla_deadlines(db, ticket)

    # Crítica sempre escala para N2 automaticamente
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
        action=f"Chamado {ticket.ticket_number} aberto por {current.name}",
        by_analyst=current.id,
        by_name=current.name,
        icon="ticket",
        icon_color="blue",
    ))

    if data.ai_analysis and data.priority_source == "ai":
        justification = (
            data.ai_analysis.get("justification", "")
            if isinstance(data.ai_analysis, dict)
            else ""
        )
        db.add(TicketTimeline(
            ticket_id=ticket.id,
            type="ai",
            action=f"Prioridade '{ticket.priority}' definida pela IA",
            note=justification,
            by_name="IA",
            icon="robot",
            icon_color="purple",
        ))

    db.commit()
    db.refresh(ticket)

    try:
        notify_ticket_created(ticket, db)
    except Exception as exc:
        logger.error("Falha ao notificar criação de chamado: %s", exc)

    _try_teams(ticket, "created")
    return ticket


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    return _get_ticket_or_404(ticket_id, db)


@router.put("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: Session = Depends(get_db),
    current: Analyst = Depends(get_current_analyst),
):
    ticket = _get_ticket_or_404(ticket_id, db)

    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(ticket, field, value)

    ticket.updated_at = datetime.now(timezone.utc)

    if "status" in changes:
        db.add(TicketTimeline(
            ticket_id=ticket.id,
            type="status",
            action=f"Status alterado para '{data.status}'",
            by_analyst=current.id,
            by_name=current.name,
            icon="refresh",
            icon_color="blue",
        ))

    db.commit()
    db.refresh(ticket)
    return ticket


@router.delete("/{ticket_id}", status_code=204)
def cancel_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current: Analyst = Depends(get_current_analyst),
):
    ticket = _get_ticket_or_404(ticket_id, db)
    ticket.status = "Cancelado"
    ticket.updated_at = datetime.now(timezone.utc)

    db.add(TicketTimeline(
        ticket_id=ticket.id,
        type="status",
        action="Chamado cancelado",
        by_analyst=current.id,
        by_name=current.name,
        icon="x",
        icon_color="red",
    ))
    db.commit()


@router.post("/{ticket_id}/escalate", response_model=TicketOut)
def escalate_ticket(
    ticket_id: int,
    data: EscalateRequest,
    db: Session = Depends(get_db),
    current: Analyst = Depends(get_current_analyst),
):
    ticket = _get_ticket_or_404(ticket_id, db)
    try:
        manual_escalate(db, ticket, data.nivel, data.reason, current.name, current.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db.commit()
    db.refresh(ticket)

    try:
        target_emails = _get_level_emails(ticket.level, db)
        if target_emails:
            notify_ticket_escalated(ticket, target_emails)
    except Exception as exc:
        logger.error("Falha ao notificar escalação: %s", exc)

    _try_teams(ticket, "escalated")
    return ticket


@router.post("/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(
    ticket_id: int,
    data: AssignRequest,
    db: Session = Depends(get_db),
    current: Analyst = Depends(get_current_analyst),
):
    ticket = _get_ticket_or_404(ticket_id, db)
    analyst = db.query(Analyst).filter(
        Analyst.id == data.analyst_id, Analyst.active == True
    ).first()
    if not analyst:
        raise HTTPException(status_code=404, detail="Analista não encontrado")

    ticket.analyst_id = data.analyst_id
    if ticket.status == "Aberto":
        ticket.status = "Em andamento"
    ticket.updated_at = datetime.now(timezone.utc)

    db.add(TicketTimeline(
        ticket_id=ticket.id,
        type="assign",
        action=f"Atribuído para {analyst.name}",
        by_analyst=current.id,
        by_name=current.name,
        icon="user",
        icon_color="blue",
    ))
    db.commit()
    db.refresh(ticket)

    try:
        notify_ticket_assigned(ticket, analyst.email, analyst.name)
    except Exception as exc:
        logger.error("Falha ao notificar atribuição: %s", exc)

    _try_teams(ticket, "assigned")
    return ticket


@router.post("/{ticket_id}/comment", response_model=TicketOut)
def add_comment(
    ticket_id: int,
    data: CommentRequest,
    db: Session = Depends(get_db),
    current: Analyst = Depends(get_current_analyst),
):
    ticket = _get_ticket_or_404(ticket_id, db)

    if not ticket.sla_responded_at:
        ticket.sla_responded_at = datetime.now(timezone.utc)
    ticket.updated_at = datetime.now(timezone.utc)

    db.add(TicketTimeline(
        ticket_id=ticket.id,
        type=data.type,
        action=f"Atualização de {current.name}",
        note=data.note,
        by_analyst=current.id,
        by_name=current.name,
        icon="message",
        icon_color="blue",
    ))
    db.commit()
    db.refresh(ticket)

    if data.note and data.type != "internal":
        try:
            notify_ticket_commented(ticket, data.note)
        except Exception as exc:
            logger.error("Falha ao notificar comentário: %s", exc)

    _try_teams(ticket, "commented")
    return ticket


@router.post("/{ticket_id}/resolve", response_model=TicketOut)
def resolve_ticket(
    ticket_id: int,
    data: ResolveRequest,
    db: Session = Depends(get_db),
    current: Analyst = Depends(get_current_analyst),
):
    ticket = _get_ticket_or_404(ticket_id, db)
    now = datetime.now(timezone.utc)

    ticket.status = "Resolvido"
    ticket.resolved_at = now
    ticket.updated_at = now
    if not ticket.sla_responded_at:
        ticket.sla_responded_at = now

    db.add(TicketTimeline(
        ticket_id=ticket.id,
        type="resolve",
        action=f"Chamado resolvido por {current.name}",
        note=data.note,
        by_analyst=current.id,
        by_name=current.name,
        icon="check",
        icon_color="green",
    ))

    # Cria pesquisa CSAT e envia e-mail de resolução
    survey = create_and_send_survey(ticket, db)

    db.commit()
    db.refresh(ticket)

    _try_teams(ticket, "resolved")
    return ticket


@router.post("/{ticket_id}/change-priority", response_model=TicketOut)
def change_priority(
    ticket_id: int,
    data: ChangePriorityRequest,
    db: Session = Depends(get_db),
    current: Analyst = Depends(get_current_analyst),
):
    ticket = _get_ticket_or_404(ticket_id, db)
    old_priority = ticket.priority

    ticket.priority = data.priority
    ticket.priority_source = "manual"
    ticket.updated_at = datetime.now(timezone.utc)

    calculate_sla_deadlines(db, ticket)

    db.add(TicketTimeline(
        ticket_id=ticket.id,
        type="priority",
        action=f"Prioridade alterada de '{old_priority}' para '{data.priority}'",
        note=data.reason,
        by_analyst=current.id,
        by_name=current.name,
        icon="flag",
        icon_color="amber",
    ))
    db.commit()
    db.refresh(ticket)
    return ticket
