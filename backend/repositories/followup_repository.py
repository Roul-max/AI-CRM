from sqlalchemy.orm import Session
from typing import List
from backend.models.followup import FollowUp
from backend.core.logging import db_logger


def get_followups_by_interaction_ids(db: Session, interaction_ids: List[int]) -> List[FollowUp]:
    if not interaction_ids:
        return []
    db_logger.info(f"get_followups_by_interaction_ids: ids={interaction_ids}")
    return db.query(FollowUp).filter(FollowUp.interaction_id.in_(interaction_ids)).all()