"""
extraction.py — Pydantic schema for AI-extracted HCP interaction data.

Design principles
-----------------
- Every Field description is written as a prompt fragment: it must be specific
  enough that Groq's structured-output mode fills the field correctly even from
  terse, informal sales-rep notes.
- Validators run in `mode="before"` so they normalise raw LLM output before
  Pydantic's own type coercion runs.
- No field silently drops data: unknown values are mapped to the closest
  canonical value rather than None.
"""

import json as _json
import re
from datetime import date, timedelta
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

_MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12,
}


def _parse_fuzzy_date(value: Any) -> Optional[date]:
    """Convert LLM natural-language date strings to a Python date.

    Handles:
      - None / null                    → None
      - already a date object          → returned as-is
      - ISO string "2024-07-10"        → date(2024, 7, 10)
      - "today" / "now"                → date.today()
      - "yesterday"                    → date.today() - 1 day
      - "tomorrow"                     → date.today() + 1 day
      - "next <weekday>" / "this <weekday>"
      - "next week"                    → date.today() + 7 days
      - "in <N> days"                  → date.today() + N days
      - "in <N> weeks"                 → date.today() + N*7 days
      - "in <N> months"                → approximate: + N*30 days
      - "end of month" / "end of week"
      - "<Month> <D>" / "<D> <Month>"  → current or next year
      - "<Month> <D>, <YYYY>"
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None

    s = value.strip().lower()

    # ── exact keywords ──────────────────────────────────────────────────────
    if s in ("today", "now"):
        return date.today()
    if s == "yesterday":
        return date.today() - timedelta(days=1)
    if s == "tomorrow":
        return date.today() + timedelta(days=1)
    if s == "next week":
        return date.today() + timedelta(weeks=1)
    if s in ("end of month", "end of the month"):
        today = date.today()
        # last day of current month
        if today.month == 12:
            return date(today.year, 12, 31)
        return date(today.year, today.month + 1, 1) - timedelta(days=1)
    if s in ("end of week", "end of the week"):
        today = date.today()
        return today + timedelta(days=(6 - today.weekday()))

    # ── "next <weekday>" / "this <weekday>" ─────────────────────────────────
    for prefix in ("next ", "this "):
        if s.startswith(prefix):
            day_name = s[len(prefix):].strip()
            if day_name in _WEEKDAYS:
                today = date.today()
                target_wd = _WEEKDAYS[day_name]
                days_ahead = (target_wd - today.weekday() + 7) % 7 or 7
                return today + timedelta(days=days_ahead)

    # ── "in N days / weeks / months" ────────────────────────────────────────
    m = re.match(r"in\s+(\d+)\s+(day|days|week|weeks|month|months)", s)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if "day" in unit:
            return date.today() + timedelta(days=n)
        if "week" in unit:
            return date.today() + timedelta(weeks=n)
        if "month" in unit:
            return date.today() + timedelta(days=n * 30)

    # ── ISO format ───────────────────────────────────────────────────────────
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass

    # ── "July 10" / "10 July" / "July 10, 2025" / "10th July 2025" ─────────
    # strip ordinal suffixes: 1st → 1, 2nd → 2, etc.
    s_clean = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s)

    # "Month D YYYY" or "Month D, YYYY"
    m = re.match(
        r"([a-z]+)\s+(\d{1,2})[,\s]+(\d{4})", s_clean
    )
    if m and m.group(1) in _MONTH_NAMES:
        try:
            return date(int(m.group(3)), _MONTH_NAMES[m.group(1)], int(m.group(2)))
        except ValueError:
            pass

    # "D Month YYYY"
    m = re.match(r"(\d{1,2})\s+([a-z]+)[,\s]+(\d{4})", s_clean)
    if m and m.group(2) in _MONTH_NAMES:
        try:
            return date(int(m.group(3)), _MONTH_NAMES[m.group(2)], int(m.group(1)))
        except ValueError:
            pass

    # "Month D" (no year — use current year, or next year if already past)
    m = re.match(r"([a-z]+)\s+(\d{1,2})$", s_clean)
    if m and m.group(1) in _MONTH_NAMES:
        today = date.today()
        try:
            candidate = date(today.year, _MONTH_NAMES[m.group(1)], int(m.group(2)))
            if candidate < today:
                candidate = date(today.year + 1, _MONTH_NAMES[m.group(1)], int(m.group(2)))
            return candidate
        except ValueError:
            pass

    # "D Month"
    m = re.match(r"(\d{1,2})\s+([a-z]+)$", s_clean)
    if m and m.group(2) in _MONTH_NAMES:
        today = date.today()
        try:
            candidate = date(today.year, _MONTH_NAMES[m.group(2)], int(m.group(1)))
            if candidate < today:
                candidate = date(today.year + 1, _MONTH_NAMES[m.group(2)], int(m.group(1)))
            return candidate
        except ValueError:
            pass

    return None


# ---------------------------------------------------------------------------
# List coercion helper
# ---------------------------------------------------------------------------

def _coerce_str_list(value: Any) -> Optional[List[str]]:
    """Normalise any LLM list output to List[str] or None.

    Handles:
    - None / ""                     → None
    - "CardioX"                     → ["CardioX"]
    - '["CardioX", "MetaboPlus"]'   → ["CardioX", "MetaboPlus"]
    - ["CardioX", "MetaboPlus"]     → ["CardioX", "MetaboPlus"]
    - comma or semicolon separated  → split accordingly
    """
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        # JSON-array string
        if stripped.startswith("["):
            try:
                parsed = _json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(v).strip() for v in parsed if v is not None and str(v).strip()] or None
            except _json.JSONDecodeError:
                pass
        # Semicolon-separated
        if ";" in stripped:
            parts = [p.strip() for p in stripped.split(";") if p.strip()]
            return parts or None
        # Comma-separated plain string
        if "," in stripped:
            parts = [p.strip() for p in stripped.split(",") if p.strip()]
            return parts or None
        return [stripped]
    if isinstance(value, list):
        result: List[str] = []
        for v in value:
            if v is None:
                continue
            s = str(v).strip()
            if s.startswith("["):
                try:
                    inner = _json.loads(s)
                    if isinstance(inner, list):
                        result.extend(str(x).strip() for x in inner if x is not None and str(x).strip())
                        continue
                except _json.JSONDecodeError:
                    pass
            if s:
                result.append(s)
        return result or None
    return None


# ---------------------------------------------------------------------------
# Value normalisers
# ---------------------------------------------------------------------------

# Phrases that indicate the value is NOT an HCP name
_NOT_A_NAME = re.compile(
    r"^(n/?a|none|unknown|not mentioned|not stated|not provided|null|na)$", re.I
)


def _normalise_hcp_name(value: Any) -> Optional[str]:
    """Strip whitespace; title-case only if the name is all-lower or all-upper.
    Rejects placeholder strings like 'N/A', 'None', 'Unknown'.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s or _NOT_A_NAME.match(s):
        return None
    if s == s.lower() or s == s.upper():
        return s.title()
    return s


_SPECIALTY_MAP = {
    "cardio": "Cardiologist", "heart": "Cardiologist", "cardiac": "Cardiologist",
    "endocrin": "Endocrinologist",
    "diabet": "Diabetologist",
    "oncol": "Oncologist", "cancer": "Oncologist",
    "neurol": "Neurologist",
    "pulmon": "Pulmonologist", "respirat": "Pulmonologist",
    "copd": "Pulmonologist", "asthma": "Pulmonologist",
    "gastro": "Gastroenterologist",
    "rheuma": "Rheumatologist",
    "dermat": "Dermatologist", "skin": "Dermatologist",
    "psychiat": "Psychiatrist", "mental health": "Psychiatrist",
    "pediat": "Pediatrician", "paediat": "Pediatrician",
    "gynec": "Gynecologist", "gynaec": "Gynecologist", "obstet": "Gynecologist",
    "urol": "Urologist",
    "nephrol": "Nephrologist", "kidney": "Nephrologist",
    "ophthal": "Ophthalmologist", "eye doctor": "Ophthalmologist",
    "orthop": "Orthopedic Surgeon", "orthopaed": "Orthopedic Surgeon",
    "hemat": "Hematologist", "blood": "Hematologist",
    "infect": "Infectious Disease Specialist",
    "general pract": "General Practitioner", "family": "General Practitioner",
    "primary care": "General Practitioner", "\bgp\b": "General Practitioner",
}


def _normalise_specialization(value: Any) -> Optional[str]:
    """Map free-text specialty to a canonical specialty name."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    sl = s.lower()
    for key, canonical in _SPECIALTY_MAP.items():
        if key in sl:
            return canonical
    return s.title()


def _normalise_sentiment(value: Any) -> Optional[str]:
    """Map any LLM sentiment string to Positive | Neutral | Negative."""
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s:
        return None
    _POS = (
        "positive", "good", "great", "excellent", "enthusiastic", "receptive",
        "interested", "keen", "excited", "impressed", "agreed", "happy",
        "supportive", "willing", "open",
    )
    _NEG = (
        "negative", "bad", "poor", "hostile", "resistant", "dismissive",
        "uninterested", "cold", "skeptical", "sceptical", "refused",
        "objected", "reluctant", "unhappy", "dissatisfied",
    )
    if any(kw in s for kw in _POS):
        return "Positive"
    if any(kw in s for kw in _NEG):
        return "Negative"
    return "Neutral"


def _normalise_risk(value: Any) -> Optional[str]:
    """Map any LLM risk string to Low | Medium | High."""
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("high", "critical", "severe", "very high"):
        return "High"
    if s in ("low", "minimal", "none", "very low", "no risk"):
        return "Low"
    if s:
        return "Medium"
    return None


def _normalise_interaction_type(value: Any) -> Optional[str]:
    """Map free-text interaction type to the canonical frontend set."""
    if value is None:
        return None
    s = str(value).strip().lower()
    if any(k in s for k in ("in-person", "in person", "face", "f2f", "visit",
                             "clinic", "office", "on-site", "onsite", "field")):
        return "In-person"
    if any(k in s for k in ("virtual", "video", "zoom", "teams", "meet",
                             "webinar", "online", "remote")):
        return "Virtual"
    if any(k in s for k in ("phone", "call", "telephone", "mobile", "ring")):
        return "Phone Call"
    if any(k in s for k in ("conference", "congress", "symposium", "summit",
                             "event", "seminar", "workshop")):
        return "Conference"
    if any(k in s for k in ("email", "mail", "message", "text", "whatsapp")):
        return "Email"
    # Return title-cased original rather than None so the value isn't lost
    return str(value).strip().title()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class InteractionExtraction(BaseModel):
    """
    Structured data extracted from a pharmaceutical sales rep's HCP interaction notes.

    EXTRACTION RULES (read carefully before filling each field):
    - Extract only what is explicitly stated or strongly implied. Do not invent.
    - For list fields, always return a JSON array even if there is only one item.
    - For boolean fields, default to false unless the notes clearly indicate true.
    - For date fields, use YYYY-MM-DD. Relative expressions like 'next Monday' or
      'in two weeks' are also accepted.
    - Sentiment reflects the HCP's attitude, not the rep's. Infer from tone words
      like 'interested', 'hesitant', 'enthusiastic', 'resistant'.
    - Risk reflects the likelihood of losing this HCP to a competitor or losing
      the sale. Infer from objections, competitor mentions, or negative sentiment.
    """

    hcp_name: Optional[str] = Field(
        None,
        description=(
            "Full name of the Healthcare Professional (doctor, nurse, pharmacist, etc.) "
            "that the sales rep visited or spoke with. "
            "Trigger phrases: 'met with', 'visited', 'spoke to', 'called', 'meeting with', "
            "'appointment with', 'saw Dr.', 'with Dr.'. "
            "Include title if present: 'Dr. Priya Sharma', 'Prof. James Lee', 'Nurse Anita'. "
            "Do NOT include the sales rep's own name. "
            "If only a last name is given ('Dr. Sharma'), keep it as-is. "
            "Do NOT return 'N/A', 'Unknown', or 'None' — leave null instead."
        ),
    )

    hospital: Optional[str] = Field(
        None,
        description=(
            "Name of the hospital, clinic, pharmacy, or medical centre where the meeting took place "
            "or where the HCP is based. "
            "Trigger phrases: 'at', 'based at', 'works at', 'from', 'located at', 'clinic at'. "
            "Include branch/location if mentioned: 'Apollo Hospital, Bandra', 'City General', "
            "'Green Leaf Pharmacy, MG Road'. "
            "Do NOT return 'N/A', 'Unknown', or 'None' — leave null instead."
        ),
    )

    specialization: Optional[str] = Field(
        None,
        description=(
            "Medical specialty of the HCP. Use standard specialty names: "
            "'Cardiologist', 'Endocrinologist', 'Diabetologist', 'Oncologist', "
            "'General Practitioner', 'Neurologist', 'Pulmonologist', 'Gastroenterologist', "
            "'Rheumatologist', 'Dermatologist', 'Psychiatrist', 'Pediatrician', "
            "'Gynecologist', 'Urologist', 'Nephrologist', 'Ophthalmologist', "
            "'Orthopedic Surgeon', 'Hematologist', 'Infectious Disease Specialist'. "
            "Infer from context if not stated explicitly: "
            "'diabetes clinic' → 'Diabetologist', 'heart' → 'Cardiologist', "
            "'cancer' → 'Oncologist', 'lungs/COPD/asthma' → 'Pulmonologist', "
            "'kidney' → 'Nephrologist', 'GP/family doctor' → 'General Practitioner'. "
            "Do NOT return 'N/A', 'Unknown', or 'None' — leave null instead."
        ),
    )

    interaction_date: Optional[Union[date, str]] = Field(
        None,
        description=(
            "Date of the interaction. Prefer YYYY-MM-DD. Also accepts: "
            "'today', 'yesterday', 'last Monday', 'July 10', '10th July 2025'. "
            "'This morning', 'earlier today', 'just now' → today's date. "
            "'Last week' → approximate date 7 days ago. "
            "Leave null only if absolutely no date reference exists in the notes."
        ),
    )

    interaction_time: Optional[str] = Field(
        None,
        description=(
            "Time of the interaction in HH:MM (24-hour) format if mentioned. "
            "Convert 12-hour to 24-hour: '2:30 PM' → '14:30', '9 AM' → '09:00'. "
            "Leave null if no time is mentioned."
        ),
    )

    interaction_type: Optional[str] = Field(
        None,
        description=(
            "Type of interaction. Choose the best match from: "
            "'In-person' (clinic visit, field visit, face-to-face, F2F), "
            "'Virtual' (Zoom, Teams, video call, online meeting), "
            "'Phone Call' (telephone, mobile call), "
            "'Conference' (congress, symposium, seminar, event), "
            "'Email'. "
            "If the rep 'visited' or 'met' the doctor, use 'In-person'."
        ),
    )

    duration: Optional[int] = Field(
        None,
        description=(
            "Duration of the meeting in minutes as an integer. "
            "Convert if needed: '1 hour' → 60, 'half an hour' → 30, '45 mins' → 45, "
            "'1.5 hours' → 90. Leave null if not mentioned."
        ),
    )

    attendees: Optional[Union[List[str], str]] = Field(
        None,
        description=(
            "List of people who attended the meeting OTHER than the primary HCP and the sales rep. "
            "Include: nurses, hospital administrators, other doctors, MSLs, managers, residents, interns. "
            "Trigger phrases: 'along with', 'also present', 'joined by', 'accompanied by', "
            "'with the nurse', 'and his/her colleague', 'the HOD was there'. "
            "Return as a JSON array: [\"Nurse Anita\", \"Dr. Kapoor (HOD)\", \"MSL Ravi\"]. "
            "Leave null if no additional attendees are mentioned."
        ),
    )

    products_discussed: Optional[Union[List[str], str]] = Field(
        None,
        description=(
            "Brand or generic names of ALL pharmaceutical products, drugs, formulations, or medical devices "
            "discussed during the meeting. Return as a JSON array: [\"CardioX 10mg\", \"Metformin 500mg\"]. "
            "Include both the company's own products AND competitor products. "
            "Trigger phrases: 'discussed', 'presented', 'talked about', 'mentioned', 'promoted', "
            "'showed data on', 'pitched', 'detailed'. "
            "Use the exact name as stated in the notes."
        ),
    )

    competitors_mentioned: Optional[Union[List[str], str]] = Field(
        None,
        description=(
            "Names of competitor companies or competitor products explicitly mentioned in the notes. "
            "Return as a JSON array: [\"AstraZeneca's Brilinta\", \"Jardiance\", \"Rival Pharma\"]. "
            "Trigger phrases: 'competitor', 'rival', 'currently using', 'already on', "
            "'switched to', 'prefers', 'compared to', 'instead of', 'vs'. "
            "Leave null if no competitors are mentioned."
        ),
    )

    shared_materials: Optional[Union[List[str], str]] = Field(
        None,
        description=(
            "List of ALL materials, documents, or resources shared with or left for the HCP. "
            "Return as a JSON array: [\"Product brochure\", \"Phase III clinical trial reprint\", \"Dosage chart\"]. "
            "Trigger phrases: 'left a brochure', 'shared the study', 'gave the pamphlet', "
            "'provided dosage chart', 'sent the PDF', 'dropped off', 'handed over', "
            "'gave a copy of', 'shared data', 'left literature', 'gave samples kit'. "
            "Include: brochures, pamphlets, flyers, clinical trial reprints, dosage charts, "
            "patient leaflets, product monographs, visual aids, PDFs, sample kits."
        ),
    )

    brochure_shared: bool = Field(
        False,
        description=(
            "True if any printed or digital brochure, pamphlet, flyer, or product literature "
            "was shared with the HCP. Also set true if shared_materials contains a brochure."
        ),
    )

    samples_distributed: Optional[Union[List[str], str]] = Field(
        None,
        description=(
            "List of specific product samples distributed or given to the HCP. "
            "Return as a JSON array: [\"CardioX 10mg (5 strips)\", \"MetaboPlus starter pack\"]. "
            "Trigger phrases: 'gave samples of', 'distributed X samples', 'left Y packs of', "
            "'dropped off samples', 'provided sample of', 'handed over samples'. "
            "If samples were given but product not specified, return [\"Samples (unspecified)\"]. "
            "Leave null if no samples were distributed."
        ),
    )

    samples_requested: bool = Field(
        False,
        description=(
            "True if the HCP requested product samples, OR if samples were distributed/given to the HCP. "
            "Trigger words: 'samples', 'sample request', 'gave samples', 'distributed samples', "
            "'requested X units', 'left samples', 'dropped off samples', 'provided samples'. "
            "Also set true if samples_distributed is non-empty."
        ),
    )

    sentiment: Optional[str] = Field(
        None,
        description=(
            "Overall sentiment/attitude of the HCP during the meeting. "
            "Must be exactly one of: 'Positive', 'Neutral', 'Negative'. "
            "Positive: interested, enthusiastic, receptive, agreed, happy, keen. "
            "Negative: resistant, dismissive, uninterested, objected strongly, hostile. "
            "Neutral: non-committal, asked questions without clear lean, mixed signals. "
            "Infer from the tone of the notes if not stated explicitly."
        ),
    )

    risk: Optional[str] = Field(
        None,
        description=(
            "Risk level for this HCP relationship or sale. "
            "Must be exactly one of: 'Low', 'Medium', 'High'. "
            "High: strong objections, competitor preference, refused samples, very negative. "
            "Low: positive sentiment, agreed to prescribe, no objections. "
            "Medium: mixed signals, some objections but open, requested more evidence."
        ),
    )

    outcomes: Optional[str] = Field(
        None,
        description=(
            "Key outcomes or results from this meeting. What was agreed, decided, or achieved? "
            "Trigger phrases: 'agreed to', 'will prescribe', 'committed to', 'decided to', "
            "'requested', 'asked for', 'wants more', 'will consider', 'not interested', "
            "'will try', 'open to', 'prescription given', 'objected to'. "
            "E.g. 'Doctor agreed to trial CardioX for 5 patients next month. "
            "HCP requested clinical evidence before prescribing MetaboPlus.' "
            "Write as 1-3 concise sentences. Do not leave null if any outcome is discernible."
        ),
    )

    follow_up_date: Optional[Union[date, str]] = Field(
        None,
        description=(
            "Date of the next planned follow-up with this HCP. "
            "Use YYYY-MM-DD or relative expressions: 'next Monday', 'in 2 weeks', 'next month'. "
            "Leave null if no follow-up date is mentioned."
        ),
    )

    action_items: Optional[Union[List[str], str]] = Field(
        None,
        description=(
            "Specific action items the sales rep must complete after this meeting. "
            "Return as a JSON array of short imperative sentences: "
            "[\"Send clinical trial PDF to Dr. Sharma\", \"Arrange sample delivery by Friday\", "
            "\"Schedule follow-up call for next week\"]. "
            "Trigger phrases: 'need to send', 'will follow up', 'promised to share', "
            "'arrange delivery', 'book appointment', 'send across', 'get approval for', "
            "'check with manager', 'will call back', 'to share', 'to send', 'to arrange'. "
            "Each item should be a single actionable task starting with a verb."
        ),
    )

    summary: Optional[str] = Field(
        None,
        description=(
            "A concise 2-4 sentence summary of the entire interaction covering: "
            "who was met, where, what was discussed, the HCP's reaction, and what happens next. "
            "Write in third person: 'The rep met Dr. X at Y hospital...'"
        ),
    )

    competitor_mentioned: Optional[str] = Field(
        None,
        description=(
            "Primary competitor product or company mentioned (single string for backward compatibility). "
            "If multiple competitors were mentioned, list the most prominent one here "
            "and put all of them in competitors_mentioned."
        ),
    )

    # ------------------------------------------------------------------
    # Field-level validators (mode="before" — run before type coercion)
    # ------------------------------------------------------------------

    @field_validator("hcp_name", mode="before")
    @classmethod
    def _norm_hcp_name(cls, v: Any) -> Optional[str]:
        return _normalise_hcp_name(v)

    @field_validator("specialization", mode="before")
    @classmethod
    def _norm_specialization(cls, v: Any) -> Optional[str]:
        return _normalise_specialization(v)

    @field_validator("interaction_date", "follow_up_date", mode="before")
    @classmethod
    def _parse_dates(cls, v: Any) -> Optional[date]:
        return _parse_fuzzy_date(v)

    @field_validator(
        "products_discussed", "action_items", "shared_materials",
        "attendees", "competitors_mentioned", "samples_distributed",
        mode="before",
    )
    @classmethod
    def _coerce_lists(cls, v: Any) -> Optional[List[str]]:
        return _coerce_str_list(v)

    @field_validator("sentiment", mode="before")
    @classmethod
    def _norm_sentiment(cls, v: Any) -> Optional[str]:
        return _normalise_sentiment(v)

    @field_validator("risk", mode="before")
    @classmethod
    def _norm_risk(cls, v: Any) -> Optional[str]:
        return _normalise_risk(v)

    @field_validator("interaction_type", mode="before")
    @classmethod
    def _norm_interaction_type(cls, v: Any) -> Optional[str]:
        return _normalise_interaction_type(v)

    @field_validator("interaction_time", mode="before")
    @classmethod
    def _norm_time(cls, v: Any) -> Optional[str]:
        """Normalise time strings to HH:MM 24-hour format."""
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        # Already HH:MM or HH:MM:SS
        m = re.match(r"^(\d{1,2}):(\d{2})(?::\d{2})?$", s)
        if m:
            return f"{int(m.group(1)):02d}:{m.group(2)}"
        # 12-hour: "2:30 PM", "9AM", "9 am"
        m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", s.lower())
        if m:
            h, mins, period = int(m.group(1)), int(m.group(2) or 0), m.group(3)
            if period == "pm" and h != 12:
                h += 12
            if period == "am" and h == 12:
                h = 0
            return f"{h:02d}:{mins:02d}"
        return s  # return as-is if unrecognised; validator won't crash

    @field_validator("duration", mode="before")
    @classmethod
    def _norm_duration(cls, v: Any) -> Optional[int]:
        """Convert duration strings like '1 hour', '45 mins', '1.5 hours' to int minutes."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return int(v)
        s = str(v).strip().lower()
        # "X hours Y mins"
        m = re.match(r"(\d+(?:\.\d+)?)\s*hours?\s*(?:and\s*)?(\d+)?\s*(?:min(?:ute)?s?)?", s)
        if m:
            hours = float(m.group(1))
            mins = int(m.group(2) or 0)
            return int(hours * 60) + mins
        # "X mins"
        m = re.match(r"(\d+)\s*(?:min(?:ute)?s?|m\b)", s)
        if m:
            return int(m.group(1))
        # plain integer string
        try:
            return int(float(s))
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Model-level validator — cross-field logic after all fields are set
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _apply_defaults_and_cross_field(self) -> "InteractionExtraction":
        # Default interaction_date to today if not extracted
        if self.interaction_date is None:
            self.interaction_date = date.today()

        # Sync brochure_shared: if shared_materials mentions a brochure, set True
        if not self.brochure_shared and self.shared_materials:
            brochure_keywords = ("brochure", "pamphlet", "flyer", "leaflet", "literature",
                                  "visual aid", "monograph", "detail aid")
            if any(
                any(kw in item.lower() for kw in brochure_keywords)
                for item in self.shared_materials
            ):
                self.brochure_shared = True

        # Sync samples_requested ↔ samples_distributed
        if not self.samples_requested and self.samples_distributed:
            self.samples_requested = True

        # Sync competitor_mentioned ↔ competitors_mentioned
        if not self.competitor_mentioned and self.competitors_mentioned:
            self.competitor_mentioned = self.competitors_mentioned[0]
        elif self.competitor_mentioned and not self.competitors_mentioned:
            self.competitors_mentioned = [self.competitor_mentioned]

        # Infer risk from sentiment if risk is missing
        if self.risk is None and self.sentiment is not None:
            self.risk = {
                "Positive": "Low",
                "Neutral": "Medium",
                "Negative": "High",
            }.get(self.sentiment)

        return self
