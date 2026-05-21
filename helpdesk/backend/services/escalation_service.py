from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.ticket import Ticket
from models.sla import SLARule
from models.timeline import TicketTimeline
import logging

logger = logging.getLogger(__name__)

_LEVEL_ORDER = {"N1": 1, "N2": 2, "N3": 3}


def check_and_escalate(db: Session, ticket: Ticket) -> bool:
    if ticket.status in ("Resolvido", "Cancelado"):
        return False

    rule = db.query(SLARule).filter(SLARule.priority == ticket.priority).first()
    if not rule:
        return False

    created = ticket.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    elapsed_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600

    if ticket.level == "N1" and rule.escalation_n1_hours and elapsed_hours >= rule.escalation_n1_hours:
        _apply_escalation(db, ticket, "N2", "Escalada automaticamente por limite de SLA N1")
        return True

    if ticket.level == "N2" and rule.escalation_n2_hours and elapsed_hours >= rule.escalation_n2_hours:
        _apply_escalation(db, ticket, "N3", "Escalada automaticamente por limite de SLA N2")
        return True

    return False


def _apply_escalation(db: Session, ticket: Ticket, new_level: str, reason: str) -> None:
    old_level = ticket.level
    ticket.level = new_level
    ticket.updated_at = datetime.now(timezone.utc)

    db.add(
        TicketTimeline(
            ticket_id=ticket.id,
            type="escalate",
            action=f"Escalado de {old_level} para {new_level}",
            note=reason,
            by_name="Sistema",
            icon="arrow-up",
            icon_color="amber",
        )
    )
    logger.info("Ticket %s escalado de %s para %s", ticket.ticket_number, old_level, new_level)


def manual_escalate(
    db: Session,
    ticket: Ticket,
    new_level: str,
    reason: str,
    analyst_name: str,
    analyst_id: int,
) -> None:
    if _LEVEL_ORDER.get(new_level, 0) <= _LEVEL_ORDER.get(ticket.level, 0):
        raise ValueError(
            f"Nível destino '{new_level}' deve ser superior ao nível atual '{ticket.level}'"
        )

    old_level = ticket.level
    ticket.level = new_level
    ticket.updated_at = datetime.now(timezone.utc)

    db.add(
        TicketTimeline(
            ticket_id=ticket.id,
            type="escalate",
            action=f"Escalado de {old_level} para {new_level} por {analyst_name}",
            note=reason,
            by_analyst=analyst_id,
            by_name=analyst_name,
            icon="arrow-up",
            icon_color="amber",
        )
    )
