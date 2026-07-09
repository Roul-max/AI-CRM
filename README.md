# AI HCP CRM

An AI-first CRM module for pharmaceutical sales representatives to log, manage, and analyse interactions with Healthcare Professionals (HCPs). The application uses a conversational AI interface powered by LangGraph and Groq to automatically extract structured data from natural language notes, populate a live form, and persist everything to PostgreSQL.

---

## Features

- **Conversational AI chat** — describe a meeting in plain English; the AI extracts all details automatically
- **Auto-filled interaction form** — 18 fields populated instantly from free-text notes via Groq LLM
- **Live form editing** — every AI-extracted field is editable before saving
- **One-click save** — persists the full interaction to PostgreSQL including products, competitors, and follow-ups
- **Edit via chat** — correct any field conversationally ("Change the date to yesterday", "Products were CardioX and Lipitor")
- **HCP search** — search by partial name, specialty, or hospital; returns full meeting history and follow-ups
- **Meeting summary** — structured 8-section summary: HCP, Objective, Discussion, Products, Concerns, Outcomes, Actions, Follow-up
- **Follow-up recommendations** — AI-generated priority, risk level, discussion topics, materials to send, and samples required
- **Real-time streaming** — SSE stream with thinking/tool/extracting phase indicators and skeleton loading
- **Toast notifications** — success/error feedback on extraction and save events

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, TailwindCSS, Redux Toolkit |
| Backend | FastAPI, Python 3.11 |
| AI Orchestration | LangGraph (StateGraph) |
| LLM Inference | Groq API (`llama-3.1-8b-instant`) |
| Database | PostgreSQL, SQLAlchemy ORM, Alembic |
| Streaming | Server-Sent Events (SSE) via FastAPI `StreamingResponse` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     React Frontend                       │
│  InteractionForm (Redux)  ←→  Chat (useChatStream hook) │
└────────────────────┬────────────────────────────────────┘
                     │  POST /api/v1/chat/stream  (SSE)
                     │  POST /api/v1/interactions/
┌────────────────────▼────────────────────────────────────┐
│                    FastAPI Backend                        │
│  /chat/stream  →  LangGraph Agent  →  Groq LLM          │
│  /interactions/  →  SQLAlchemy  →  PostgreSQL            │
└─────────────────────────────────────────────────────────┘
```

**N-tier layers:**
- `api/v1/endpoints/` — FastAPI routers (HTTP boundary)
- `agents/` + `tools/` — LangGraph orchestration and tool implementations
- `schemas/` — Pydantic models for validation and structured LLM output
- `repositories/` — database access layer (SQLAlchemy queries)
- `models/` — SQLAlchemy ORM models

---

## LangGraph Workflow

```
User Message
     │
     ▼
 intent_node  ──── no tool call ──→  END
     │
  tool call
     │
     ▼
  tool_node
     │
  ┌──┴──────────────────────────────────────────┐
  │  data extraction tool?                       │
  │  (log/edit/search/summary/recommendation)    │
  └──┬──────────────────────────────────────────┘
     │ yes                    │ no
     ▼                        ▼
    END               intent_node (loop)
```

- `intent_node` — invokes Groq LLM with system prompt + conversation history; decides which tool to call
- `tool_node` — executes the selected tool; wraps result as `AIMessage` for data-extraction tools
- `router_node` — routes to `tool_node` if tool calls present, else `END`
- `after_tool_router` — data-extraction tools short-circuit to `END`; others loop back to `intent_node`

---

## Five AI Tools

| Tool | Trigger | Description |
|---|---|---|
| `log_interaction` | Rep describes a meeting | Extracts 18 fields from free-text notes using Groq structured output |
| `edit_interaction` | Rep corrects extracted data | Applies natural language corrections while preserving all other fields |
| `search_hcp` | Rep asks about an HCP | Searches by partial name / specialty / hospital; returns full meeting history |
| `meeting_summary` | Rep asks for a summary | Generates 8-section structured summary: HCP, Objective, Discussion, Products, Concerns, Outcomes, Actions, Follow-up |
| `follow_up_recommendation` | Rep asks for next steps | Generates priority, risk level, suggested date, discussion topics, materials to send, samples required |

---

## Database Schema

```
Users ──────────────────────────────────────────────────────────────────┐
                                                                         │
HCPs  1 ──────────────────────────────────────────────────────────────* │
                                                                         │
Interactions *──────────────────────────────────────────────────────── 1┘
     │
     ├── *──── interaction_product ────* Products
     ├── *──── interaction_competitor ─* Competitors
     └── 1 ──────────────────────────* FollowUps
```

**Interactions table columns:** `id`, `hcp_id`, `user_id`, `interaction_date`, `notes`, `summary`, `outcomes`, `action_items`, `sentiment`, `risk_level`, `interaction_type`, `duration`, `brochure_shared`, `samples_requested`

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+

### Clone

```bash
git clone <repo-url>
cd ai-hcp-crm
```

### Backend

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Frontend

```bash
# from project root
npm install
```

---

## Environment Variables

Create `backend/.env`:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/hcp_crm
GROQ_API_KEY=gsk_your_groq_api_key_here
PRIMARY_MODEL=llama-3.1-8b-instant
ENVIRONMENT=development
```

> The backend will **refuse to start** if `DATABASE_URL` points to SQLite or if `GROQ_API_KEY` is missing.

---

## PostgreSQL Setup

```sql
-- Run in psql or pgAdmin
CREATE DATABASE hcp_crm;
```

```bash
# Run Alembic migrations (from project root)
alembic upgrade head
```

This applies all 3 migrations:
- `0001` — base schema (users, hcps, interactions, products, competitors, followups)
- `0002` — adds interaction columns (outcomes, interaction_type, duration, brochure_shared, samples_requested)
- `0003` — adds `hcps.hospital` column

---

## Backend Commands

```bash
# From project root (with venv active)

# Start the FastAPI server
uvicorn backend.main:app --reload --port 8000

# Run Alembic migrations
alembic upgrade head

# Check migration status
alembic current

# Health check
curl http://localhost:8000/health
```

---

## Frontend Commands

```bash
# From project root

# Start the React dev server (proxies /api to localhost:8000)
npm run dev

# Build for production
npm run build
```

---

## Screenshots

> Add screenshots here before submission.

| Screen | Description |
|---|---|
| `screenshots/chat-extraction.png` | Chat panel after logging an interaction — form auto-filled |
| `screenshots/form-populated.png` | InteractionForm with all 18 fields populated by AI |
| `screenshots/save-success.png` | Toast notification after saving to PostgreSQL |
| `screenshots/search-hcp.png` | HCP search result with meeting history |
| `screenshots/meeting-summary.png` | 8-section meeting summary in chat |
| `screenshots/followup-recommendation.png` | Follow-up recommendation with priority and risk |

---

## Demo Video

> Add demo video link here before submission.

**Suggested demo flow (matches assignment video requirements):**

1. Type a meeting note → form auto-fills via `log_interaction`
2. Correct a field via chat → `edit_interaction` updates only that field
3. Search for an HCP by name → `search_hcp` returns history
4. Ask for a meeting summary → `meeting_summary` returns 8 sections
5. Ask for follow-up recommendations → `follow_up_recommendation` returns priority + actions
6. Click "Save Interaction" → data persisted to PostgreSQL

---

## Folder Structure

```
├── backend/
│   ├── agents/
│   │   └── graph.py                  # LangGraph StateGraph — intent → tool → END
│   ├── alembic/
│   │   └── versions/
│   │       ├── 0001_initial.py
│   │       ├── 0002_add_interaction_columns.py
│   │       └── 0003_add_hcp_hospital.py
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── chat.py           # SSE streaming endpoint
│   │           └── interactions.py   # Save interaction endpoint
│   ├── core/
│   │   ├── config.py                 # Settings, env validation
│   │   └── logging.py                # Structured loggers
│   ├── db/
│   │   ├── database.py               # SQLAlchemy engine + Base
│   │   └── session.py                # Session factory
│   ├── models/
│   │   ├── hcp.py                    # HCP ORM model
│   │   ├── interaction.py            # Interaction ORM model (+ M2M tables)
│   │   ├── followup.py               # FollowUp ORM model
│   │   ├── product.py                # Product ORM model
│   │   ├── competitor.py             # Competitor ORM model
│   │   └── user.py                   # User ORM model
│   ├── repositories/
│   │   ├── hcp_repository.py         # HCP search with selectinload
│   │   ├── interaction_repository.py
│   │   └── followup_repository.py
│   ├── schemas/
│   │   ├── extraction.py             # InteractionExtraction — 18-field Pydantic schema
│   │   ├── interaction.py            # InteractionCreate / InteractionRead
│   │   └── tools.py                  # HCPSearchResult, MeetingSummary, FollowUpRecommendation
│   ├── tools/
│   │   └── crm_tools.py              # 5 LangChain @tool implementations
│   └── main.py                       # FastAPI app entry point
│
├── src/
│   ├── components/
│   │   ├── Layout.tsx                # App shell with ToastContainer
│   │   └── ui/
│   │       ├── ToastContainer.tsx    # Slide-in toast notifications
│   │       └── skeleton.tsx          # Skeleton loading component
│   ├── features/
│   │   ├── chat/
│   │   │   └── Chat.tsx              # Chat panel — messages + input
│   │   ├── interactions/
│   │   │   └── InteractionForm.tsx   # 18-field AI-populated form
│   │   └── dashboard/
│   │       └── Dashboard.tsx         # Main layout (Chat + Form side-by-side)
│   ├── hooks/
│   │   └── useChatStream.ts          # SSE stream hook with StreamPhase
│   ├── store/
│   │   ├── index.ts                  # Redux store (interaction + chat + ui)
│   │   ├── interactionSlice.ts       # Interaction state + saveInteraction thunk
│   │   └── slices/
│   │       ├── chatSlice.ts          # Chat message state
│   │       └── uiSlice.ts            # Toast + isExtracting state
│   └── App.tsx                       # Root component
│
├── alembic.ini
├── package.json
├── vite.config.ts
└── README.md
```
