from sqlalchemy import Column, Integer, String, Boolean
from database import Base


class SLARule(Base):
    __tablename__ = "sla_rules"

    id = Column(Integer, primary_key=True, index=True)
    priority = Column(String(20), unique=True, nullable=False)
    response_hours = Column(Integer, nullable=False)
    resolution_hours = Column(Integer, nullable=False)
    escalation_n1_hours = Column(Integer)
    escalation_n2_hours = Column(Integer)
    color = Column(String(7))
    active = Column(Boolean, default=True)
