import json
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional, List

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.logging import llm_logger, tool_logger, db_logger, error_logger
from backend.db.session import SessionLocal
from backend.schemas.extraction import InteractionExtraction
from backend.schemas.tools import HCPSearchResult, MeetingSummary, FollowUpRecommendation
from backend.repositories import hcp_repository


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Tool Input Schemas ---

class LogInteractionInput(BaseModel):
    notes: str = Field(description="The natural language notes from a conversation with an HCP, to be extracted into a structured format.")

class EditInteractionInput(BaseModel):
    current_data_json: str = Field(description="The current extracted data in JSON string format.")
    correction: str = Field(description="The user's correction in natural language (e.g., 'The doctor was actually Dr. John').")

class SearchHCPInput(BaseModel):
    name: Optional[str] = Field(None, description="Partial or full name of the HCP to search for. Case-insensitive.")
    specialty: Optional[str] = Field(None, description="Specialty to filter by, e.g. 'Cardiologist', 'Diabetologist'. Case-insensitive partial match.")
    hospital: Optional[str] = Field(None, description="Hospital or clinic name to filter by, e.g. 'Apollo', 'City General'. Case-insensitive partial match.")

class MeetingSummaryInput(BaseModel):
    notes: str = Field(description="The meeting notes to be summarized.")

class FollowupRecommendationInput(BaseModel):
    notes: str = Field(description="The meeting notes to generate follow-up recommendations from.")



# --- Tool Implementations ---

_EXTRACTION_SYSTEM_PROMPT = """\
You are a specialist data-extraction AI for a pharmaceutical sales CRM.
Your only job is to read a sales rep's raw interaction notes and populate every field of the schema.

EXTRACTION RULES — follow these exactly:

1. HCP NAME  →  hcp_name
   - Extract the full name of the doctor/nurse/pharmacist the rep visited.
   - Include title: "Dr.", "Prof.", "Nurse", etc.
   - Never put the sales rep's own name here.
   - If only a last name is given ("Dr. Sharma"), keep it as-is.

2. SPECIALTY  →  specialization
   - Map to a standard specialty: Cardiologist, Endocrinologist, Diabetologist,
     Oncologist, General Practitioner, Neurologist, Pulmonologist, Gastroenterologist,
     Rheumatologist, Dermatologist, Psychiatrist, Pediatrician, Gynecologist, Urologist,
     Nephrologist, Ophthalmologist, Orthopedic Surgeon, Hematologist, Infectious Disease.
   - Infer from context: "diabetes clinic" → Diabetologist, "heart" → Cardiologist,
     "cancer" → Oncologist, "lungs/COPD/asthma" → Pulmonologist.

3. HOSPITAL / CLINIC  →  hospital
   - Extract the full name including branch/location if mentioned.
   - E.g. "Apollo Hospital, Bandra", "City General", "Green Leaf Pharmacy".

4. INTERACTION TYPE  →  interaction_type
   - "In-person": visited, met, clinic visit, field visit, face-to-face, F2F, dropped by.
   - "Virtual": Zoom, Teams, Google Meet, video call, online meeting, webinar.
   - "Phone Call": called, phoned, rang, telephone, mobile call.
   - "Conference": congress, symposium, seminar, summit, event, workshop.
   - "Email": emailed, sent a message.
   - Default to "In-person" if the rep "met" or "visited" without further qualification.

5. DATE  →  interaction_date
   - Use YYYY-MM-DD. Accept: "today", "yesterday", "last Monday", "July 10", "10th July 2025".
   - "This morning" / "earlier today" → today's date.
   - If no date is mentioned, default to today's date.

6. TIME  →  interaction_time
   - Output HH:MM in 24-hour format. "2:30 PM" → "14:30", "9 AM" → "09:00".
   - Leave null if not mentioned.

7. DURATION  →  duration
   - Output integer minutes. "1 hour" → 60, "half an hour" → 30, "45 mins" → 45,
     "1.5 hours" → 90, "2 hours 15 minutes" → 135.
   - Leave null if not mentioned.

8. PRODUCTS DISCUSSED  →  products_discussed
   - List ALL pharmaceutical products, drugs, devices, or formulations mentioned.
   - Include both the company's own products AND competitor products.
   - Use the exact brand/generic name as stated: "CardioX 10mg", "Metformin", "Insulin Glargine".

9. COMPETITORS  →  competitors_mentioned
   - List competitor company names OR competitor product names explicitly mentioned.
   - E.g. ["AstraZeneca's Brilinta", "Jardiance", "Rival Pharma"].
   - Leave null if none mentioned.

10. MATERIALS SHARED  →  shared_materials
    - List every document, resource, or item handed to the HCP.
    - Trigger phrases: "left a brochure", "shared the study", "gave the pamphlet",
      "provided dosage chart", "sent the PDF", "dropped off samples kit".
    - E.g. ["Product brochure", "Phase III clinical trial reprint", "Dosage titration chart"].

11. SAMPLES  →  samples_distributed  +  samples_requested
    - samples_distributed: list the specific products given as samples.
      E.g. ["CardioX 10mg (5 strips)", "MetaboPlus starter pack"].
      If samples were given but product not specified: ["Samples (unspecified)"].
      Leave null if no samples were distributed.
    - samples_requested: set true if samples were given OR requested by the HCP.
    - Trigger words: "samples", "sample pack", "gave samples", "distributed",
      "left samples", "requested X units", "dropped off samples".

12. SENTIMENT  →  sentiment
    - Reflects the HCP's attitude, NOT the rep's.
    - Positive: interested, enthusiastic, receptive, agreed, happy, keen, excited, impressed.
    - Negative: resistant, dismissive, uninterested, objected, hostile, skeptical, refused.
    - Neutral: non-committal, asked questions without clear lean, mixed signals, polite but uncommitted.
    - Infer from tone even if not stated explicitly.

13. OUTCOMES  →  outcomes
    - What was agreed, decided, or achieved? 1-3 concise sentences.
    - E.g. "Doctor agreed to trial CardioX for 5 patients next month."
    - "HCP requested clinical evidence before prescribing."

14. FOLLOW-UP DATE  →  follow_up_date
    - The next planned meeting/call date. Use YYYY-MM-DD or relative expressions.
    - Trigger phrases: "follow up in 2 weeks", "next visit on Monday", "call back next month".

15. ACTION ITEMS  →  action_items
    - Specific tasks the sales rep must do after this meeting.
    - Short imperative sentences: "Send clinical trial PDF to Dr. Sharma".
    - Trigger phrases: "need to send", "will follow up", "promised to share", "arrange delivery".

16. ATTENDEES  →  attendees
    - People present OTHER than the HCP and the sales rep.
    - E.g. nurses, hospital administrators, other doctors, MSLs, managers.
    - Leave null if no additional attendees are mentioned.

GENERAL RULES:
- Extract only what is stated or strongly implied. Do NOT invent data.
- For list fields, always return a JSON array even for a single item.
- For boolean fields, default to false unless clearly indicated.
- Never leave a field empty when the information is present in the notes.

FEW-SHOT EXAMPLE
Input: "Visited Dr. Priya Nair (cardiologist) at Apollo Bandra this morning. 45-min meeting.
Pitched CardioX 10mg for post-MI patients. She's currently prescribing Jardiance.
She was interested but asked for Phase III data. Left a brochure and 5 CardioX samples.
She wants a follow-up call in 2 weeks. Need to email her the trial PDF."

Expected output (key fields):
  hcp_name: "Dr. Priya Nair"
  specialization: "Cardiologist"
  hospital: "Apollo Bandra"
  interaction_type: "In-person"
  duration: 45
  products_discussed: ["CardioX 10mg"]
  competitors_mentioned: ["Jardiance"]
  shared_materials: ["Product brochure"]
  samples_distributed: ["CardioX 10mg (5 units)"]
  samples_requested: true
  sentiment: "Positive"
  outcomes: "HCP showed interest in CardioX 10mg for post-MI patients. Requested Phase III clinical data before prescribing."
  follow_up_date: "<2 weeks from today>"
  action_items: ["Email Phase III trial PDF to Dr. Priya Nair"]
"""

@tool("log_interaction", args_schema=LogInteractionInput)
def log_interaction(notes: str) -> str:
    """
    Extracts structured information from natural language notes of a Healthcare Professional interaction.
    Does not save to the database. Returns a JSON object with the extracted data.
    """
    llm = ChatGroq(model=settings.PRIMARY_MODEL, temperature=0, groq_api_key=settings.GROQ_API_KEY)
    structured_llm = llm.with_structured_output(InteractionExtraction)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _EXTRACTION_SYSTEM_PROMPT),
        ("human", "Extract all details from these interaction notes. Populate every field you can find evidence for.\n\n---\n\n{notes}")
    ])

    chain = prompt | structured_llm
    try:
        llm_logger.info(f"log_interaction: invoking {settings.PRIMARY_MODEL}")
        extracted_data = chain.invoke({"notes": notes})
        tool_logger.info("log_interaction: extraction complete")
        return extracted_data.model_dump_json(indent=2)
    except Exception as e:
        error_logger.error(f"log_interaction failed: {e}")
        return f"An unexpected error occurred during extraction: {e}"

@tool("edit_interaction", args_schema=EditInteractionInput)
def edit_interaction(current_data_json: str, correction: str) -> str:
    """
    Edits a JSON object of extracted interaction data based on a user's natural language correction.
    For instance, if the user says 'the doctor was actually Dr. John', it updates the hcp_name field.
    Returns the full, updated JSON object.
    """
    llm = ChatGroq(model=settings.PRIMARY_MODEL, temperature=0, groq_api_key=settings.GROQ_API_KEY)
    structured_llm = llm.with_structured_output(InteractionExtraction)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a pharmaceutical CRM data correction AI.\n"
         "You will receive a JSON object of extracted interaction data and a natural-language correction.\n"
         "\n"
         "FIELD NAME REFERENCE — use these exact keys:\n"
         "  hcp_name, hospital, specialization, interaction_date, interaction_time,\n"
         "  interaction_type, duration, attendees, products_discussed, competitors_mentioned,\n"
         "  shared_materials, brochure_shared, samples_distributed, samples_requested,\n"
         "  sentiment, risk, outcomes, follow_up_date, action_items, summary\n"
         "\n"
         "CORRECTION RULES:\n"
         "1. Apply ONLY the changes described in the correction. Do not alter any other field.\n"
         "2. Map natural language to the correct field key:\n"
         "   'doctor name / HCP name' → hcp_name\n"
         "   'follow-up / next visit date' → follow_up_date\n"
         "   'products / drugs discussed' → products_discussed\n"
         "   'type / how we met' → interaction_type\n"
         "   'when / date of meeting' → interaction_date\n"
         "3. Normalise values: dates → YYYY-MM-DD, time → HH:MM 24h, "
         "duration → integer minutes, lists → JSON arrays, "
         "sentiment → Positive/Neutral/Negative, "
         "interaction_type → In-person/Virtual/Phone Call/Conference/Email.\n"
         "4. Return the complete updated JSON object with ALL fields preserved."),
        ("human", "Current extracted data:\n\n```json\n{current_data}\n```\n\nCorrection to apply: '{correction}'")
    ])

    chain = prompt | structured_llm
    try:
        llm_logger.info(f"edit_interaction: invoking {settings.PRIMARY_MODEL}")
        updated_data = chain.invoke({"current_data": current_data_json, "correction": correction})
        tool_logger.info("edit_interaction: correction applied")
        return updated_data.model_dump_json(indent=2)
    except Exception as e:
        error_logger.error(f"edit_interaction failed: {e}")
        return f"An unexpected error occurred during data correction: {e}"

@tool("search_hcp", args_schema=SearchHCPInput)
def search_hcp(name: Optional[str] = None, specialty: Optional[str] = None, hospital: Optional[str] = None) -> str:
    """
    Searches for Healthcare Professionals in the CRM by partial name, specialty, and/or hospital.
    Returns full meeting history (interaction type, duration, products discussed, competitors,
    sentiment, outcomes, action items, brochure/sample status) and all follow-ups with their status.
    Use this tool whenever the user asks about an HCP, their history, past visits, or follow-ups.
    """
    if not name and not specialty and not hospital:
        return json.dumps({"error": "Provide at least one of: name, specialty, or hospital."})

    with get_db() as db:
        db_logger.info(f"search_hcp: name={name} specialty={specialty} hospital={hospital}")
        hcps = hcp_repository.search_hcps(db, name=name, specialty=specialty, hospital=hospital)
        if not hcps:
            return json.dumps([])

        results = []
        for hcp in hcps:
            # interactions are already eager-loaded with products, competitors, follow_ups
            sorted_interactions = sorted(
                hcp.interactions,
                key=lambda i: i.interaction_date or datetime.min,
                reverse=True,
            )
            interaction_summaries = [
                HCPSearchResult.InteractionSummary(
                    id=i.id,
                    interaction_date=i.interaction_date,
                    interaction_type=i.interaction_type,
                    duration_minutes=i.duration,
                    summary=i.summary,
                    outcomes=i.outcomes,
                    sentiment=i.sentiment,
                    products_discussed=[p.name for p in i.products],
                    competitors_mentioned=[c.name for c in i.competitors],
                    brochure_shared=i.brochure_shared,
                    samples_requested=i.samples_requested,
                    action_items=i.action_items,
                )
                for i in sorted_interactions
            ]

            all_follow_ups = sorted(
                [fu for i in hcp.interactions for fu in i.follow_ups],
                key=lambda f: f.due_date,
            )
            follow_up_summaries = [
                HCPSearchResult.FollowUpSummary(
                    id=f.id,
                    due_date=f.due_date,
                    status=f.status,
                    notes=f.notes,
                )
                for f in all_follow_ups
            ]

            results.append(HCPSearchResult(
                id=hcp.id,
                name=hcp.name,
                specialty=hcp.specialty,
                hospital=hcp.hospital,
                interactions=interaction_summaries,
                follow_ups=follow_up_summaries,
            ))

    return json.dumps([r.model_dump(mode='json') for r in results], indent=2)

_MEETING_SUMMARY_SYSTEM_PROMPT = """\
You are a specialist summarization AI for a pharmaceutical sales CRM.
Your job is to read a sales rep's raw interaction notes and produce a structured meeting summary.

Fill every field of the schema using ONLY information present in the notes.
Do NOT invent data. Do NOT leave a field empty when the information is present.

FIELD-BY-FIELD INSTRUCTIONS:

hcp
  Full name with title + specialty + hospital/clinic if mentioned.
  E.g. "Dr. Priya Nair, Endocrinologist, Kokilaben Hospital Mumbai".
  If hospital is not mentioned, omit it: "Dr. Amit Sharma, Cardiologist".

objective
  One sentence: why did the rep visit this HCP today?
  Infer from context if not stated explicitly.
  E.g. "Introduce CardioX 10mg and gauge prescribing intent for post-MI patients."

discussion_points
  Every topic covered — clinical data, dosing, patient profiles, competitor comparisons,
  market access, pricing, side effects, rep's pitch, HCP's questions.
  One concise sentence per bullet. Minimum 3 items if the notes are detailed.

products_discussed
  ALL products named — own portfolio AND competitors.
  Use exact brand/generic name as written: "CardioX 10mg", "Metformin 500mg", "Jardiance".
  Include devices and formulations.

concerns_raised
  Specific objections or hesitations from the HCP only (not the rep).
  E.g. "Worried about renal safety in elderly patients."
  "Prefers generics due to patient affordability constraints."
  Empty list [] if no concerns were raised.

outcomes
  What was agreed, decided, or achieved. 1–3 sentences.
  E.g. "Doctor agreed to trial CardioX for 5 patients next month.
  Requested Phase III reprint before committing to broader prescribing."

action_items
  Tasks the sales rep must do after this meeting. Imperative sentences.
  E.g. ["Email Phase III trial PDF to Dr. Nair by Friday",
         "Arrange 10-unit CardioX sample delivery",
         "Schedule follow-up call in 2 weeks"]
  Derive from phrases like: "need to send", "will share", "promised", "arrange", "follow up".

follow_up
  Next planned contact: date + channel + purpose in one sentence.
  E.g. "In-person visit on 2025-08-15 to review trial patient outcomes."
  Null if no follow-up was discussed.
"""

@tool("meeting_summary", args_schema=MeetingSummaryInput)
def meeting_summary(notes: str) -> str:
    """
    Generates a structured 8-section meeting summary from interaction notes.
    Sections: HCP, Objective, Discussion Points, Products Discussed, Concerns Raised,
    Outcomes, Action Items, Follow-up.
    Use this when the user asks for a summary, recap, or overview of a meeting.
    """
    llm = ChatGroq(model=settings.PRIMARY_MODEL, temperature=0, groq_api_key=settings.GROQ_API_KEY)
    structured_llm = llm.with_structured_output(MeetingSummary)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _MEETING_SUMMARY_SYSTEM_PROMPT),
        ("human", "Generate a complete structured summary from these interaction notes. Populate every field.\n\n---\n\n{notes}")
    ])
    chain = prompt | structured_llm
    try:
        llm_logger.info(f"meeting_summary: invoking {settings.PRIMARY_MODEL}")
        summary_data = chain.invoke({"notes": notes})
        tool_logger.info("meeting_summary: complete")
        return summary_data.model_dump_json(indent=2)
    except Exception as e:
        error_logger.error(f"meeting_summary failed: {e}")
        return f"An unexpected error occurred during summary generation: {e}"

_FOLLOWUP_RECOMMENDATION_SYSTEM_PROMPT = """\
You are a specialist follow-up strategy AI for a pharmaceutical sales CRM.
Your job is to read a sales rep's interaction notes and produce a structured, actionable follow-up recommendation.

Fill every field of the schema using ONLY information present in the notes.
Do NOT invent data. Apply pharmaceutical sales best practices when inferring.

FIELD-BY-FIELD INSTRUCTIONS:

priority
  Urgency of the next contact.
  High: HCP agreed to trial, made a commitment, or is at risk of switching to a competitor.
  Medium: HCP was neutral, asked for more information, or has an unresolved question.
  Low: HCP was uninterested, no commitments, relationship is stable with no urgency.

suggested_follow_up_date
  Use any timeline mentioned in the notes ("follow up in 2 weeks", "call next month").
  If none mentioned: High → 7 days from today, Medium → 14 days, Low → 30 days.
  Output as YYYY-MM-DD.

risk_level
  Risk to the prescribing relationship.
  High: competitor preference, strong objections, refused samples, very negative sentiment.
  Low: positive sentiment, agreed to prescribe, no objections.
  Medium: mixed signals, hesitation, requested more evidence.

discussion_topics
  Topics to address in the NEXT meeting — not what was discussed today.
  Derive from: unresolved objections, questions the HCP asked, data they requested,
  competitor products mentioned, or outcomes that need follow-through.
  Short imperative phrases. Minimum 2 items.
  E.g. ["Present Phase III efficacy data for CardioX",
         "Address renal safety concern in elderly patients",
         "Compare CardioX vs Jardiance on cost-effectiveness"]

materials_to_send
  Documents or resources to send before or bring to the next visit.
  Derive from: what the HCP asked for, what was promised, what objections need evidence.
  E.g. ["Phase III clinical trial reprint", "Dosage titration guide",
         "Patient affordability programme brochure"]
  Empty list [] if nothing specific is needed.

samples_required
  True if samples should be brought or arranged for the next visit.
  Set true if: HCP requested samples, samples were promised, HCP agreed to trial the product,
  or the previous visit involved sample distribution.
  False if HCP declined samples or no sample discussion occurred.

reasoning
  2-3 sentences justifying this recommendation.
  Reference specific signals: HCP's sentiment, commitments made, objections raised,
  competitor risk, or pending action items.
  E.g. "Dr. Sharma agreed to trial CardioX for 5 patients but requested Phase III data first.
  The 2-week follow-up ensures delivery before the HCP's next prescribing cycle.
  Competitor Jardiance was mentioned, making timely follow-up critical."
"""

@tool("follow_up_recommendation", args_schema=FollowupRecommendationInput)
def follow_up_recommendation(notes: str) -> str:
    """
    Generates a structured follow-up recommendation from interaction notes.
    Includes: priority, suggested date, risk level, discussion topics for next visit,
    materials to send, samples required, and reasoning.
    Use this when the user asks for follow-up recommendations, next steps, or what to do after a meeting.
    """
    llm = ChatGroq(model=settings.PRIMARY_MODEL, temperature=0.5, groq_api_key=settings.GROQ_API_KEY)
    structured_llm = llm.with_structured_output(FollowUpRecommendation)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _FOLLOWUP_RECOMMENDATION_SYSTEM_PROMPT),
        ("human", "Generate a complete follow-up recommendation from these interaction notes. Populate every field.\n\n---\n\n{notes}")
    ])
    chain = prompt | structured_llm
    try:
        llm_logger.info(f"follow_up_recommendation: invoking {settings.PRIMARY_MODEL}")
        recommendation_data = chain.invoke({"notes": notes})
        tool_logger.info("follow_up_recommendation: complete")
        return recommendation_data.model_dump_json(indent=2)
    except Exception as e:
        error_logger.error(f"follow_up_recommendation failed: {e}")
        return f"An unexpected error occurred during recommendation generation: {e}"

all_tools = [log_interaction, edit_interaction, search_hcp, meeting_summary, follow_up_recommendation]