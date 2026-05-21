from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    extension = Column(String(10))
    department_id = Column(Integer, ForeignKey("departments.id"))
    # Hash bcrypt — opcional: usuários podem ter senha para acessar o portal
    password = Column(String(255), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    department = relationship("Department", back_populates="users")
    tickets = relationship("Ticket", back_populates="user")
