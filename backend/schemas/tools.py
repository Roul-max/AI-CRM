from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime


class HCPSearchResult(BaseModel):
    """Structured result for an HCP search."""

    id: int
    name: str
    specialty: Optional[str]
    hospital: Optional[str]

    class InteractionSummary(BaseModel):
        id: int
        interaction_date: Optional[datetime]
        interaction_type: Optional[str]
        duration_minutes: Optional[int]
        summary: Optional[str]
        outcomes: Optional[str]
        sentiment: Optional[str]
        products_discussed: List[str] = Field(default_factory=list)
        competitors_mentioned: List[str] = Field(default_factory=list)
        brochure_shared: Optional[bool]
        samples_requested: Optional[bool]
        action_items: Optional[str]

    class FollowUpSummary(BaseModel):
        id: int
        due_date: datetime
        status: str
        notes: Optional[str]

    interactions: List[InteractionSummary] = Field(
        default_factory=list,
        description="Full history of past interactions with this HCP, most recent first.",
    )
    follow_ups: List[FollowUpSummary] = Field(
        default_factory=list,
        description="All follow-ups (pending and completed) for this HCP, sorted by due date.",
    )


class MeetingSummary(BaseModel):
    """Structured summary of a pharmaceutical sales meeting."""

    hcp: str = Field(
        description=(
            "Full name and title of the Healthcare Professional met. "
            "Include specialty and hospital/clinic if mentioned. "
            "E.g. 'Dr. Amit Sharma, Cardiologist, Apollo Hospital Bandra'."
        )
    )
    objective: str = Field(
        description=(
            "The primary goal or purpose of this visit in one sentence. "
            "E.g. 'Introduce CardioX 10mg and assess prescribing intent for high-risk patients.'"
        )
    )
    discussion_points: List[str] = Field(
        description=(
            "Bulleted list of every topic discussed during the meeting. "
            "Each item should be a concise, standalone sentence. "
            "Include clinical data shared, questions raised, objections, and any off-topic conversation."
        )
    )
    products_discussed: List[str] = Field(
        description=(
            "List of ALL pharmaceutical products, drugs, devices, or formulations mentioned — "
            "both the rep's own portfolio AND competitor products. "
            "Use exact brand/generic names as stated. E.g. ['CardioX 10mg', 'Metformin 500mg', 'Jardiance']."
        )
    )
    concerns_raised: List[str] = Field(
        default_factory=list,
        description=(
            "Specific objections, hesitations, or concerns expressed by the HCP. "
            "E.g. 'Concerned about renal side effects in elderly patients', "
            "'Prefers generic alternatives due to patient cost sensitivity'. "
            "Leave empty list if no concerns were raised."
        )
    )
    outcomes: str = Field(
        description=(
            "What was agreed, decided, or achieved by the end of the meeting. "
            "1–3 concise sentences. "
            "E.g. 'Doctor agreed to trial CardioX for 5 high-risk patients next month. "
            "Requested Phase III clinical trial reprint before prescribing.'"
        )
    )
    action_items: List[str] = Field(
        description=(
            "Specific tasks the sales rep must complete after this meeting. "
            "Short imperative sentences. "
            "E.g. ['Send Phase III trial PDF to Dr. Sharma by Friday', "
            "'Arrange sample delivery for 10 units of CardioX 10mg', "
            "'Follow up call in 2 weeks to confirm prescribing decision']."
        )
    )
    follow_up: Optional[str] = Field(
        None,
        description=(
            "The next planned contact: date, channel, and purpose. "
            "E.g. 'In-person visit on 2025-08-15 to review trial patient outcomes.' "
            "Leave null if no follow-up was discussed."
        )
    )


class FollowUpRecommendation(BaseModel):
    """Structured follow-up recommendation for a pharmaceutical sales rep."""

    priority: str = Field(
        description=(
            "Urgency of this follow-up. Must be exactly one of: 'High', 'Medium', 'Low'. "
            "High: HCP showed strong interest, agreed to trial, or has a pending commitment. "
            "High also if HCP is at risk of switching to a competitor. "
            "Medium: HCP was neutral, asked for more information, or has an open question. "
            "Low: HCP was uninterested, no commitments made, or relationship is stable."
        )
    )
    suggested_follow_up_date: date = Field(
        description=(
            "Recommended date for the next contact. "
            "Base this on any follow-up timeline mentioned in the notes "
            "(e.g. 'follow up in 2 weeks', 'call next month'). "
            "If no timeline is mentioned, recommend: "
            "High priority → within 7 days, Medium → within 14 days, Low → within 30 days. "
            "Output as YYYY-MM-DD."
        )
    )
    risk_level: str = Field(
        description=(
            "Risk to the sales relationship or prescribing intent. "
            "Must be exactly one of: 'High', 'Medium', 'Low'. "
            "High: competitor preference expressed, strong objections, refused samples, very negative sentiment. "
            "Low: positive sentiment, agreed to prescribe, no objections raised. "
            "Medium: mixed signals, some hesitation, requested more evidence."
        )
    )
    discussion_topics: List[str] = Field(
        description=(
            "Specific clinical or commercial topics to address in the next meeting. "
            "Derive from: unresolved objections, questions the HCP asked, data they requested, "
            "competitor products they mentioned, or outcomes from this visit. "
            "Each item is a short imperative phrase. "
            "E.g. ['Present Phase III efficacy data for CardioX', "
            "'Address renal safety concern in elderly patients', "
            "'Compare CardioX vs Jardiance on cost-effectiveness']. "
            "Minimum 2 items."
        )
    )
    materials_to_send: List[str] = Field(
        default_factory=list,
        description=(
            "Documents, studies, or resources the rep should send or bring to the next visit. "
            "Derive from: what the HCP asked for, what was promised, what objections need evidence. "
            "E.g. ['Phase III clinical trial reprint', 'Dosage titration guide', "
            "'Patient affordability programme brochure', 'Comparative efficacy chart vs Jardiance']. "
            "Empty list [] if nothing specific is needed."
        )
    )
    samples_required: bool = Field(
        description=(
            "True if product samples should be brought or arranged for the next visit. "
            "Set true if: HCP requested samples, samples were promised, HCP agreed to trial the product, "
            "or the previous visit involved sample distribution. "
            "False if HCP declined samples or no sample discussion occurred."
        )
    )
    reasoning: str = Field(
        description=(
            "2-3 sentence justification for this recommendation. "
            "Reference specific signals from the notes: HCP's sentiment, commitments made, "
            "objections raised, competitor risk, or pending action items. "
            "E.g. 'Dr. Sharma agreed to trial CardioX for 5 patients but requested Phase III data first. "
            "The 2-week follow-up ensures the rep delivers the study before the HCP's next prescribing cycle. "
            "Competitor Jardiance was mentioned, making timely follow-up critical to prevent switching.'"
        )
    )
