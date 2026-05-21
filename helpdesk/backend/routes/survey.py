from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.survey import TicketSurvey
from schemas.survey import SurveyPublicOut, SurveyAnswer, SurveyOut
from services.survey_service import process_survey_answer
from middleware.auth import get_current_analyst

router = APIRouter(prefix="/survey", tags=["survey"])


# ── Endpoints públicos (sem autenticação — acessados via link no e-mail) ──────

@router.get("/{token}", response_model=SurveyPublicOut, summary="Dados da pesquisa (público)")
def get_survey(token: str, db: Session = Depends(get_db)):
    """
    Retorna os dados do chamado para exibição na página de pesquisa.
    Acessível via link enviado por e-mail — sem autenticação.
    """
    survey = db.query(TicketSurvey).filter(TicketSurvey.token == token).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Pesquisa não encontrada ou link inválido")

    ticket = survey.ticket
    return SurveyPublicOut(
        token=token,
        ticket_number=ticket.ticket_number,
        ticket_title=ticket.title,
        resolved_at=ticket.resolved_at,
        already_answered=survey.answered_at is not None,
    )


@router.post("/{token}", response_model=SurveyOut, summary="Responder pesquisa (público)")
def answer_survey(
    token: str,
    data: SurveyAnswer,
    db: Session = Depends(get_db),
):
    """
    Registra a resposta do solicitante.
    - Se `resolved_confirmed=false`, o chamado é reaberto automaticamente.
    - Se `resolved_confirmed=true`, o chamado é fechado definitivamente.
    """
    survey = db.query(TicketSurvey).filter(TicketSurvey.token == token).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Pesquisa não encontrada ou link inválido")

    try:
        result = process_survey_answer(
            survey=survey,
            score=data.score,
            comment=data.comment,
            resolved_confirmed=data.resolved_confirmed,
            db=db,
        )
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ── Endpoints internos (para gestores visualizarem respostas) ─────────────────

@router.get("", response_model=list[SurveyOut], summary="Listar pesquisas (analistas)")
def list_surveys(
    answered_only: bool = False,
    db: Session = Depends(get_db),
    _=Depends(get_current_analyst),
):
    q = db.query(TicketSurvey)
    if answered_only:
        q = q.filter(TicketSurvey.answered_at.isnot(None))
    return q.order_by(TicketSurvey.sent_at.desc()).limit(200).all()
