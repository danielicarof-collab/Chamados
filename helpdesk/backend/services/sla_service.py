from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from models.ticket import Ticket
from models.sla import SLARule
import logging

logger = logging.getLogger(__name__)


def _utc(dt: datetime) -> datetime:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def calculate_sla_deadlines(db: Session, ticket: Ticket) -> None:
    rule = (
        db.query(SLARule)
        .filter(SLARule.priority == ticket.priority, SLARule.active == True)
        .first()
    )
    if not rule:
        logger.warning("Sem regra de SLA para prioridade '%s'", ticket.priority)
        return

    now = datetime.now(timezone.utc)
    ticket.sla_deadline = now + timedelta(hours=rule.resolution_hours)
    ticket.sla_response_deadline = now + timedelta(hours=rule.response_hours)


def calculate_sla_percentage(ticket: Ticket) -> int:
    if not ticket.sla_deadline or not ticket.created_at:
        return 0

    created = _utc(ticket.created_at)
    deadline = _utc(ticket.sla_deadline)
    now = datetime.now(timezone.utc)

    total = (deadline - created).total_seconds()
    elapsed = (now - created).total_seconds()

    if total <= 0:
        return 100
    return min(int((elapsed / total) * 100), 100)


def update_sla_status(db: Session, ticket: Ticket) -> None:
    if ticket.status in ("Resolvido", "Cancelado"):
        return

    ticket.sla_percentage = calculate_sla_percentage(ticket)

    deadline = _utc(ticket.sla_deadline)
    if deadline and datetime.now(timezone.utc) > deadline:
        ticket.sla_breached = True
