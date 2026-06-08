from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text

from app.core.session import Base
from app.core.utils import generate_uuid


class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)

    content = Column(Text, nullable=False)
    tone = Column(String(50), nullable=False, default="professional")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
