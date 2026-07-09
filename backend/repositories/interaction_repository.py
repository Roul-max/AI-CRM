from sqlalchemy.orm import Session
from backend.models.interaction import Interaction
from backend.models.hcp import HCP
from backend.core.logging import db_logger
from typing import List


def create_interaction(db: Session, hcp_id: int, notes: str) -> Interaction:
    db_hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if not db_hcp:
        raise ValueError(f"HCP with id {hcp_id} not found")
    db_logger.info(f"create_interaction: hcp_id={hcp_id}")
    db_interaction = Interaction(hcp_id=hcp_id, notes=notes, user_id=1)
    db.add(db_interaction)
    db.commit()
    db.refresh(db_interaction)
    return db_interaction


def update_interaction(db: Session, interaction_id: int, notes: str) -> Interaction | None:
    db_interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if db_interaction:
        db_logger.info(f"update_interaction: id={interaction_id}")
        db_interaction.notes = notes
        db.commit()
        db.refresh(db_interaction)
    return db_interaction


def get_interactions_by_hcp_id(db: Session, hcp_id: int) -> List[Interaction]:
    db_logger.info(f"get_interactions_by_hcp_id: hcp_id={hcp_id}")
    return db.query(Interaction).filter(Interaction.hcp_id == hcp_id).order_by(Interaction.interaction_date.desc()).all()