from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, String
from sqlalchemy.orm import relationship

from backend.db.database import Base

class FollowUp(Base):
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id"), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="pending")  # e.g., pending, completed
    notes = Column(Text, nullable=True)

    interaction = relationship("Interaction", back_populates="follow_ups")