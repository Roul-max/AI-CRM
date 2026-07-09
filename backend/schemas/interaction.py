import re
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Any, Optional, List


class InteractionCreate(BaseModel):
    # HCP identity — backend upserts by name
    hcp_name: str
    hcp_specialization: Optional[str] = None
    hcp_hospital: Optional[str] = None

    # Scalar interaction fields
    notes: Optional[str] = None
    summary: Optional[str] = None
    outcomes: Optional[str] = None
    sentiment: Optional[str] = None
    risk_level: Optional[str] = None
    interaction_type: Optional[str] = None
    interaction_date: Optional[str] = None   # YYYY-MM-DD from frontend date input
    duration: Optional[int] = None

    @field_validator("duration", mode="before")
    @classmethod
    def _coerce_duration(cls, v: Any) -> Optional[int]:
        """Accept int, float, or strings like '30 min', '1 hour', '45 minutes'."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return int(v)
        s = str(v).strip().lower()
        if not s:
            return None
        # "X hours Y mins"
        m = re.match(r"(\d+(?:\.\d+)?)\s*hours?\s*(?:and\s*)?(\d+)?\s*(?:min(?:ute)?s?)?", s)
        if m and m.group(0):  # only accept if something matched
            hours = float(m.group(1))
            mins = int(m.group(2) or 0)
            result = int(hours * 60) + mins
            if result > 0:
                return result
        # "X mins / minutes / min"
        m = re.match(r"(\d+)\s*(?:min(?:ute)?s?|m\b)", s)
        if m:
            return int(m.group(1))
        # plain numeric string
        try:
            return int(float(s))
        except ValueError:
            return None

    brochure_shared: bool = False
    samples_requested: bool = False

    # Follow-up
    follow_up_date: Optional[str] = None     # YYYY-MM-DD
    follow_up_notes: Optional[str] = None

    # List fields — action_items stored as JSON string; others resolve to DB rows
    action_items: List[str] = []
    products_discussed: List[str] = []
    competitors_mentioned: List[str] = []
    shared_materials: List[str] = []
    attendees: List[str] = []


class InteractionRead(BaseModel):
    id: int
    hcp_id: int
    interaction_date: datetime
    notes: Optional[str] = None
    summary: Optional[str] = None
    outcomes: Optional[str] = None
    sentiment: Optional[str] = None
    risk_level: Optional[str] = None
    interaction_type: Optional[str] = None
    duration: Optional[int] = None
    brochure_shared: Optional[bool] = None
    samples_requested: Optional[bool] = None
    action_items: Optional[str] = None
    user_id: Optional[int] = None

    class Config:
        from_attributes = True
