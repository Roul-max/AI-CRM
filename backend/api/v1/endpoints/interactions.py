import json
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.schemas.interaction import InteractionCreate, InteractionRead
from backend.models.interaction import Interaction
from backend.models.hcp import HCP
from backend.models.user import User
from backend.models.product import Product
from backend.models.competitor import Competitor
from backend.models.followup import FollowUp
from backend.db.session import get_db
from backend.core.logging import db_logger

router = APIRouter()

_SYSTEM_USER_EMAIL = "system@hcp-crm.internal"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_system_user(db: Session) -> int:
    """Return the id of the system user, creating it if it doesn't exist."""
    user = db.query(User).filter(User.email == _SYSTEM_USER_EMAIL).first()
    if not user:
        db_logger.info("seeding system user")
        user = User(
            email=_SYSTEM_USER_EMAIL,
            name="System",
            hashed_password="__system__",
            is_active=True,
        )
        db.add(user)
        db.flush()
    return user.id


def _upsert_hcp(db: Session, name: str, specialization: str | None, hospital: str | None = None) -> HCP:
    hcp = db.query(HCP).filter(HCP.name.ilike(name.strip())).first()
    if not hcp:
        db_logger.info(f"creating HCP name={name}")
        hcp = HCP(name=name.strip(), specialty=specialization, hospital=hospital)
        db.add(hcp)
        db.flush()
    else:
        if specialization and not hcp.specialty:
            hcp.specialty = specialization
        if hospital and not hcp.hospital:
            hcp.hospital = hospital
    return hcp


def _upsert_product(db: Session, name: str) -> Product:
    name = name.strip()
    obj = db.query(Product).filter(Product.name.ilike(name)).first()
    if not obj:
        obj = Product(name=name)
        db.add(obj)
        db.flush()
    return obj


def _upsert_competitor(db: Session, name: str) -> Competitor:
    name = name.strip()
    obj = db.query(Competitor).filter(Competitor.name.ilike(name)).first()
    if not obj:
        obj = Competitor(name=name)
        db.add(obj)
        db.flush()
    return obj


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/", response_model=InteractionRead, status_code=201)
def create_interaction(
    *,
    db: Session = Depends(get_db),
    interaction_in: InteractionCreate,
):
    """
    Persist a complete AI-extracted interaction.

    - Upserts the HCP by name (creates if new).
    - Writes all scalar extracted fields to the interactions row.
    - Links products and competitors via junction tables (upserts each by name).
    - Creates a FollowUp row when a follow_up_date is present.
    - Uses a seeded system user so user_id is never null or broken.
    """
    system_user_id = _ensure_system_user(db)

    # 1. Resolve HCP
    hcp = _upsert_hcp(db, interaction_in.hcp_name, interaction_in.hcp_specialization, interaction_in.hcp_hospital)

    # 2. Build the Interaction row with every extracted scalar field
    db_interaction = Interaction(
        hcp_id=hcp.id,
        user_id=system_user_id,
        notes=interaction_in.notes,
        summary=interaction_in.summary,
        outcomes=interaction_in.outcomes,
        sentiment=interaction_in.sentiment,
        risk_level=interaction_in.risk_level,
        interaction_type=interaction_in.interaction_type,
        duration=interaction_in.duration,
        brochure_shared=interaction_in.brochure_shared,
        samples_requested=interaction_in.samples_requested,
        # action_items stored as a JSON array string so it survives round-trips
        action_items=json.dumps(interaction_in.action_items) if interaction_in.action_items else None,
    )

    parsed_date = _parse_date(interaction_in.interaction_date)
    if parsed_date:
        db_interaction.interaction_date = parsed_date

    db.add(db_interaction)
    db.flush()  # assigns db_interaction.id before linking M2M rows

    # 3. Link products (many-to-many)
    for name in interaction_in.products_discussed:
        if name and name.strip():
            product = _upsert_product(db, name)
            if product not in db_interaction.products:
                db_interaction.products.append(product)

    # 4. Link competitors (many-to-many)
    for name in interaction_in.competitors_mentioned:
        if name and name.strip():
            competitor = _upsert_competitor(db, name)
            if competitor not in db_interaction.competitors:
                db_interaction.competitors.append(competitor)

    # 5. Create FollowUp row when a follow-up date was extracted
    follow_up_dt = _parse_date(interaction_in.follow_up_date)
    if follow_up_dt:
        follow_up = FollowUp(
            interaction_id=db_interaction.id,
            due_date=follow_up_dt,
            status="pending",
            notes=interaction_in.follow_up_notes,
        )
        db.add(follow_up)

    db.commit()
    db.refresh(db_interaction)
    db_logger.info(
        f"create_interaction: saved id={db_interaction.id} "
        f"hcp={hcp.name} products={len(interaction_in.products_discussed)} "
        f"competitors={len(interaction_in.competitors_mentioned)} "
        f"follow_up={'yes' if follow_up_dt else 'no'}"
    )
    return db_interaction
