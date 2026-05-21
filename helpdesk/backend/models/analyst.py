from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Analyst(Base):
    __tablename__ = "analysts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    level = Column(String(2), nullable=False)      # N1, N2, N3
    role = Column(String(20), default="analyst")   # analyst | coordinator | manager | admin
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    tickets = relationship("Ticket", back_populates="analyst")
    timeline_entries = relationship("TicketTimeline", back_populates="analyst")
