from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    default_sla = Column(String(10))   # Crítica, Alta, Média, Baixa
    default_level = Column(String(2))  # N1, N2, N3
    active = Column(Boolean, default=True)

    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent")
    tickets = relationship("Ticket", back_populates="category")
