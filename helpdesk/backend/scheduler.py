"""
Scheduler de tarefas em background.
Jobs:
  - sla_check (a cada 5 min): verifica SLA, escala automaticamente, envia notificações
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import SessionLocal
from models.ticket import Ticket
from models.analyst import Analyst
from services.sla_service import update_sla_status
from services.escalation_service import check_and_escalate
from services.notification_service import (
    notify_sla_breach,
    notify_sla_warning,
)

logger = logging.getLogger(__name__)
_scheduler = BackgroundScheduler(timezone="UTC")

# Rastreia quais tickets já receberam o aviso de 70% (evita spam)
_warned_70: set[int] = set()


def _run_sla_check() -> None:
    db = SessionLocal()
    try:
        active_tickets = (
            db.query(Ticket)
            .filter(Ticket.status.in_(["Aberto", "Em andamento", "Pendente", "Reaberto"]))
            .all()
        )

        newly_breached: list[Ticket] = []
        newly_warned: list[Ticket] = []
        escalated: list[Ticket] = []

        for ticket in active_tickets:
            was_breached = ticket.sla_breached
            update_sla_status(db, ticket)

            # SLA violado — nova violação detectada
            if ticket.sla_breached and not was_breached:
                newly_breached.append(ticket)
                _warned_70.discard(ticket.id)  # reset aviso

            # Aviso de 70% — apenas uma vez por chamado
            elif (
                ticket.sla_percentage >= 70
                and not ticket.sla_breached
                and ticket.id not in _warned_70
            ):
                newly_warned.append(ticket)
                _warned_70.add(ticket.id)

            # Auto-escalação por tempo
            if check_and_escalate(db, ticket):
                escalated.append(ticket)

        if active_tickets:
            db.commit()

        # ── Notificações de violação ──
        for ticket in newly_breached:
            emails: list[str] = []
            if ticket.analyst and ticket.analyst.email:
                emails.append(ticket.analyst.email)
            # Notificar gestores também em violações críticas
            if ticket.priority == "Crítica":
                managers = (
                    db.query(Analyst)
                    .filter(Analyst.role.in_(["manager", "admin"]), Analyst.active == True)
                    .all()
                )
                emails += [m.email for m in managers if m.email]
            if emails:
                notify_sla_breach(ticket, list(set(emails)))
            logger.warning("SLA violado: %s (%s)", ticket.ticket_number, ticket.priority)

        # ── Notificações de alerta 70% ──
        for ticket in newly_warned:
            if ticket.analyst and ticket.analyst.email:
                notify_sla_warning(ticket, ticket.analyst.email)
            logger.info("SLA 70%%: %s (%s)", ticket.ticket_number, ticket.priority)

        # ── Log de escalações ──
        for ticket in escalated:
            logger.info("Auto-escalada: %s → %s", ticket.ticket_number, ticket.level)

        if active_tickets:
            logger.debug(
                "SLA check concluído: %d chamados | %d violações | %d alertas | %d escaladas",
                len(active_tickets),
                len(newly_breached),
                len(newly_warned),
                len(escalated),
            )
    except Exception as exc:
        logger.error("Erro no job de SLA: %s", exc, exc_info=True)
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> None:
    _scheduler.add_job(
        _run_sla_check,
        trigger=IntervalTrigger(minutes=5),
        id="sla_check",
        replace_existing=True,
        misfire_grace_time=60,
    )
    _scheduler.start()
    logger.info("Scheduler iniciado — verificação de SLA a cada 5 minutos")


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler encerrado")
