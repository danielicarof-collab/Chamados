from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class TicketTimeline(Base):
    __tablename__ = "ticket_timeline"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    type = Column(String(30))  # open|comment|escalate|assign|status|priority|resolve|ai
    action = Column(String(300), nullable=False)
    note = Column(Text)
    by_analyst = Column(Integer, ForeignKey("analysts.id"), nullable=True)
    by_name = Column(String(100))
    icon = Column(String(50))
    icon_color = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="timeline")
    analyst = relationship("Analyst", back_populates="timeline_entries")
