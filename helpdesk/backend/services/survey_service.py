"""
Serviço de pesquisa de satisfação (CSAT).
Gerencia criação, envio e processamento das respostas.
"""
import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from models.survey import TicketSurvey
from models.ticket import Ticket
from models.timeline import TicketTimeline
from services.notification_service import notify_ticket_resolved, notify_ticket_reopened

logger = logging.getLogger(__name__)


def create_and_send_survey(ticket: Ticket, db: Session) -> TicketSurvey | None:
    """
    Cria a pesquisa CSAT para o chamado e envia o e-mail de resolução.
    Deve ser chamado imediatamente após a resolução do chamado.
    """
    # Evitar duplicatas
    existing = db.query(TicketSurvey).filter(TicketSurvey.ticket_id == ticket.id).first()
    if existing:
        logger.debug("Pesquisa já existe para chamado %s", ticket.ticket_number)
        return existing

    survey = TicketSurvey(
        ticket_id=ticket.id,
        token=str(uuid.uuid4()),
    )
    db.add(survey)
    db.flush()  # garante que survey.token está disponível

    # Envia e-mail ao solicitante com link da pesquisa
    try:
        notify_ticket_resolved(ticket, survey.token)
    except Exception as exc:
        logger.error("Falha ao enviar e-mail de resolução para %s: %s", ticket.ticket_number, exc)

    logger.info("Pesquisa CSAT criada para %s (token=%s)", ticket.ticket_number, survey.token)
    return survey


def process_survey_answer(
    survey: TicketSurvey,
    score: int,
    comment: str | None,
    resolved_confirmed: bool,
    db: Session,
) -> TicketSurvey:
    """
    Registra a resposta do solicitante.
    Se resolved_confirmed=False, reabre o chamado automaticamente.
    """
    if survey.answered_at is not None:
        raise ValueError("Esta pesquisa já foi respondida.")

    now = datetime.now(timezone.utc)
    survey.score = score
    survey.comment = comment
    survey.resolved_confirmed = resolved_confirmed
    survey.answered_at = now

    ticket: Ticket = survey.ticket
    db.add(survey)

    if not resolved_confirmed:
        # Solicitante informou que o problema não foi resolvido — reabrir chamado
        ticket.status = "Reaberto"
        ticket.resolved_at = None
        ticket.updated_at = now

        db.add(TicketTimeline(
            ticket_id=ticket.id,
            type="status",
            action="Chamado reaberto pelo solicitante via pesquisa de satisfação",
            note=comment or "",
            by_name=ticket.user.name if ticket.user else "Solicitante",
            icon="refresh",
            icon_color="orange",
        ))

        try:
            notify_ticket_reopened(ticket)
        except Exception as exc:
            logger.error("Falha ao notificar reabertura de %s: %s", ticket.ticket_number, exc)
    else:
        # Chamado confirmado como resolvido — fechar
        if ticket.status != "Fechado":
            ticket.status = "Fechado"
            ticket.closed_at = now
            ticket.updated_at = now

            db.add(TicketTimeline(
                ticket_id=ticket.id,
                type="status",
                action=f"Chamado fechado — Solicitante avaliou com nota {score}/5",
                note=comment or "",
                by_name=ticket.user.name if ticket.user else "Solicitante",
                icon="check",
                icon_color="green",
            ))

    db.flush()
    logger.info(
        "Pesquisa respondida — %s | nota=%d | resolvido=%s",
        ticket.ticket_number, score, resolved_confirmed,
    )
    return survey
