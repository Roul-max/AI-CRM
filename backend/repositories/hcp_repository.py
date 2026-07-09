from sqlalchemy.orm import Session, selectinload
from backend.models.hcp import HCP
from backend.models.interaction import Interaction
from backend.models.followup import FollowUp
from backend.core.logging import db_logger


def search_hcps(
    db: Session,
    name: str | None = None,
    specialty: str | None = None,
    hospital: str | None = None,
) -> list[HCP]:
    db_logger.info(f"search_hcps: name={name} specialty={specialty} hospital={hospital}")
    query = db.query(HCP).options(
        selectinload(HCP.interactions).selectinload(Interaction.products),
        selectinload(HCP.interactions).selectinload(Interaction.competitors),
        selectinload(HCP.interactions).selectinload(Interaction.follow_ups),
    )
    if name:
        query = query.filter(HCP.name.ilike(f"%{name}%"))
    if specialty:
        query = query.filter(HCP.specialty.ilike(f"%{specialty}%"))
    if hospital:
        query = query.filter(HCP.hospital.ilike(f"%{hospital}%"))
    return query.all()
