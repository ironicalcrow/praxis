from datetime import datetime

from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship

from app.core.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)  # value supplied by Supabase auth
    name = Column(String(255))
    username = Column(String(255), unique=True)
    email = Column(String(255), unique=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resumes = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    applications = relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"
