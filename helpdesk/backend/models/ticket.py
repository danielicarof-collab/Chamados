from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(10), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    priority = Column(String(20), nullable=False)
    priority_source = Column(String(10), default="ai")
    status = Column(String(20), default="Aberto")
    level = Column(String(2), default="N1")
    impact = Column(String(50))
    equipment = Column(String(100))
    user_id = Column(Integer, ForeignKey("users.id"))
    analyst_id = Column(Integer, ForeignKey("analysts.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"))
    ai_analysis = Column(JSONB)
    sla_deadline = Column(DateTime(timezone=True))
    sla_response_deadline = Column(DateTime(timezone=True))
    sla_responded_at = Column(DateTime(timezone=True))
    sla_percentage = Column(Integer, default=0)
    sla_breached = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    resolved_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))

    category = relationship("Category", back_populates="tickets")
    user = relationship("User", back_populates="tickets")
    analyst = relationship("Analyst", back_populates="tickets")
    department = relationship("Department", back_populates="tickets")
    timeline = relationship(
        "TicketTimeline",
        back_populates="ticket",
        order_by="TicketTimeline.created_at",
    )
    survey = relationship("TicketSurvey", back_populates="ticket", uselist=False)
