import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from schemas.chatbot import ChatbotMessageIn, ChatbotMessageOut
from services.chatbot_service import process_message

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


@router.post("/message", response_model=ChatbotMessageOut, summary="Enviar mensagem ao chatbot")
async def chatbot_message(
    data: ChatbotMessageIn,
    db: Session = Depends(get_db),
):
    """
    Endpoint unificado do chatbot.

    Aceita mensagens de qualquer canal (web, teams) e retorna a resposta do assistente.
    O `session_id` identifica a conversa — gere um UUID no cliente e reutilize-o.

    **Fluxo:**
    1. `greeting` — solicita e-mail do usuário
    2. `collecting_description` — solicita descrição do problema
    3. `collecting_impact` — solicita nível de impacto
    4. `collecting_equipment` — solicita equipamento/sistema afetado
    5. `confirming` — apresenta resumo e aguarda confirmação
    6. `done` — chamado criado com sucesso
    """
    result = await process_message(
        session_id=data.session_id,
        message=data.message,
        channel=data.channel,
        db=db,
        user_email=data.user_email,
        user_name=data.user_name,
    )
    return result


@router.get("/session/{session_id}", summary="Histórico da sessão do chatbot")
def get_session(session_id: str, db: Session = Depends(get_db)):
    """Retorna o contexto completo de uma sessão (para debug e auditoria)."""
    from models.chatbot import ChatbotSession
    session = db.query(ChatbotSession).filter(
        ChatbotSession.session_id == session_id
    ).first()
    if not session:
        return {"session_id": session_id, "context": None}
    return {
        "session_id": session_id,
        "channel": session.channel,
        "ticket_id": session.ticket_id,
        "context": session.context,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }
