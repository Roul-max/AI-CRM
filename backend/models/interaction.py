from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, String, Table, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.db.database import Base

interaction_product_table = Table(
    "interaction_product",
    Base.metadata,
    Column("interaction_id", Integer, ForeignKey("interactions.id"), primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
)

interaction_competitor_table = Table(
    "interaction_competitor",
    Base.metadata,
    Column("interaction_id", Integer, ForeignKey("interactions.id"), primary_key=True),
    Column("competitor_id", Integer, ForeignKey("competitors.id"), primary_key=True),
)


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, default=1)
    interaction_date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    outcomes = Column(Text, nullable=True)
    action_items = Column(Text, nullable=True)   # stored as JSON array string
    sentiment = Column(String, nullable=True)
    risk_level = Column(String, nullable=True)
    interaction_type = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)    # minutes
    brochure_shared = Column(Boolean, nullable=True, default=False)
    samples_requested = Column(Boolean, nullable=True, default=False)

    hcp = relationship("HCP", back_populates="interactions")
    follow_ups = relationship("FollowUp", back_populates="interaction")
    user = relationship("User", back_populates="interactions")
    products = relationship("Product", secondary=interaction_product_table, back_populates="interactions")
    competitors = relationship("Competitor", secondary=interaction_competitor_table, back_populates="interactions")