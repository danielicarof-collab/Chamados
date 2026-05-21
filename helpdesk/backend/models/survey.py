import uuid
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class TicketSurvey(Base):
    """Pesquisa de satisfação enviada após resolução do chamado (CSAT)."""
    __tablename__ = "ticket_surveys"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, unique=True)
    token = Column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    # Resposta do solicitante
    score = Column(Integer, nullable=True)               # 1 (péssimo) – 5 (excelente)
    comment = Column(Text, nullable=True)
    resolved_confirmed = Column(Boolean, nullable=True)  # True = resolvido / False = reabre

    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    answered_at = Column(DateTime(timezone=True), nullable=True)

    ticket = relationship("Ticket", back_populates="survey")
