from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class ChatbotSession(Base):
    """Sessão de conversa do chatbot — armazena estado e histórico completo."""
    __tablename__ = "chatbot_sessions"

    id = Column(Integer, primary_key=True, index=True)
    # UUID gerado pelo cliente — permite retomada da conversa
    session_id = Column(String(36), unique=True, nullable=False, index=True)
    channel = Column(String(20), default="web")    # web | teams | email
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Estado da conversa + histórico de mensagens
    # Estrutura: { "state": str, "user_email": str, "user_name": str, "description": str,
    #              "impact": str, "equipment": str, "history": [...] }
    context = Column(JSONB, default=dict)

    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    ticket = relationship("Ticket")
