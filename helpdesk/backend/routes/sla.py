from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.sla import SLARule
from models.ticket import Ticket
from models.analyst import Analyst
from schemas.ticket import SLARuleOut, SLARuleUpdate
from middleware.auth import get_current_analyst, require_manager

router = APIRouter(prefix="/sla", tags=["sla"])


@router.get("/rules", response_model=list[SLARuleOut])
def list_sla_rules(
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    return db.query(SLARule).order_by(SLARule.id).all()


@router.put("/rules/{priority}", response_model=SLARuleOut)
def update_sla_rule(
    priority: str,
    data: SLARuleUpdate,
    db: Session = Depends(get_db),
    _: Analyst = Depends(require_manager),
):
    rule = db.query(SLARule).filter(SLARule.priority == priority).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Regra de SLA não encontrada")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/breaches")
def sla_breaches(
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    tickets = (
        db.query(Ticket)
        .filter(Ticket.sla_breached == True, Ticket.status.notin_(["Resolvido", "Cancelado"]))
        .order_by(Ticket.priority, Ticket.created_at)
        .all()
    )
    return [
        {
            "id": t.id,
            "ticket_number": t.ticket_number,
            "title": t.title,
            "priority": t.priority,
            "level": t.level,
            "status": t.status,
            "sla_percentage": t.sla_percentage,
            "sla_deadline": t.sla_deadline,
            "created_at": t.created_at,
        }
        for t in tickets
    ]


@router.get("/at-risk")
def sla_at_risk(
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    tickets = (
        db.query(Ticket)
        .filter(
            Ticket.sla_percentage >= 70,
            Ticket.sla_breached == False,
            Ticket.status.notin_(["Resolvido", "Cancelado"]),
        )
        .order_by(Ticket.sla_percentage.desc())
        .all()
    )
    return [
        {
            "id": t.id,
            "ticket_number": t.ticket_number,
            "title": t.title,
            "priority": t.priority,
            "level": t.level,
            "status": t.status,
            "sla_percentage": t.sla_percentage,
            "sla_deadline": t.sla_deadline,
            "created_at": t.created_at,
        }
        for t in tickets
    ]
