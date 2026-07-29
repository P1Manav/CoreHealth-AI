# Healthcare AI Chatbot

A production-quality healthcare information chatbot with a **React (Vite) frontend** and **Flask backend**, featuring a **two-tier memory architecture**, **multi-model ensemble via OpenRouter**, **RAGAS-lite evaluation**, and **RAG pipeline** grounded in public-domain medical sources.

> ⚠️ **Disclaimer**: This chatbot provides general health information only — not medical diagnoses or prescriptions. Always consult a licensed healthcare professional for personal medical advice.

---

## Architecture Overview

```
┌───────────────────────────────┐
│      React Frontend (Vite)    │
│  /            → Landing Page  │
│  /chat        → Chat UI      │
│  Supabase JS for Google OAuth │
└──────────────┬────────────────┘
               │ REST API
               │ Authorization: Bearer <jwt>  (signed-in)
               │ X-Guest-Session-Id: <uuid>   (guest)
┌──────────────▼────────────────┐
│        Flask Backend          │
│                               │
│  1. Identity resolution       │──► Strong (JWT) or Weak (UUID)
│  2. Guardrail pre-filter      │──► Emergency/scope detection
│  3. Memory retrieval          │──► Supabase pgvector / TTLCache
│  4. RAG retrieval             │──► Chroma (shared KB)
│  5. Prompt assembly           │
│  6. Multi-model ensemble      │──► OpenRouter (3 free LLMs)
│  7. RAGAS-lite scoring        │──► Faithfulness, RQG, scope, safety
│  8. Guardrail post-filter     │──► Disclaimer, citation attachment
│  9. Memory update (strong)    │──► Extract symptoms/conditions/facts
│ 10. Response delivery         │
└───────────────────────────────┘
```

### Two-Tier Memory Architecture

| Feature | Strong (Signed In) | Weak (Guest) |
|---|---|---|
| **Identity** | Supabase JWT (stable UUID) | Client-generated UUID |
| **Storage** | Supabase Postgres + pgvector | In-process TTLCache |
| **Memory recall** | Semantic (pgvector cosine similarity) | Last 6-10 raw turns |
| **Personalization** | interaction_style, tone adaptation | None (neutral tone) |
| **Condition tracking** | Yes (with proactive check-ins) | No |
| **Cross-session** | Yes (forever) | No (2h TTL, lost on restart) |
| **User controls** | View/edit/delete all data | N/A |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React (Vite), React Router, Supabase JS |
| Backend | Flask, ThreadPoolExecutor |
| Auth | Supabase Auth (Google OAuth) |
| Strong-tier DB | Supabase Postgres + pgvector + RLS |
| Weak-tier cache | cachetools.TTLCache |
| Knowledge Base | ChromaDB (local) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, 384-dim) |
| LLM Access | OpenRouter (3 free models, dynamic discovery) |

---

## Setup Instructions

### Prerequisites

- Python 3.10+ with pip
- Node.js 18+
- A [Supabase](https://supabase.com) project (free tier works)
- An [OpenRouter](https://openrouter.ai) API key (free tier works)

### 1. Clone and Install

```bash
# Backend
cd healthcare-chatbot/backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Environment Variables

Copy the `.env.example` files and fill in your credentials:

**Backend** (`backend/.env`):
```env
OPENROUTER_API_KEY=your_openrouter_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
SUPABASE_JWT_SECRET=your_supabase_jwt_secret
FLASK_DEBUG=true
```

**Frontend** (`frontend/.env`):
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_BASE_URL=http://localhost:5000/api
```

### 3. Supabase Setup

1. **Enable Google OAuth**: Dashboard → Authentication → Providers → Google → Enable, add your Google Client ID and Secret
2. **Enable pgvector**: Dashboard → Database → Extensions → search "vector" → Enable
3. **Run the schema**: Dashboard → SQL Editor → paste and run `backend/app/schema.sql`

The schema creates:
- `profiles` (demographics, preferences, interaction_style)
- `medical_conditions` (name, status, lifecycle tracking)
- `symptom_log` (symptom, status, lifecycle tracking)
- `memory_facts` (fact text + 384-dim vector embedding for semantic recall)
- `chat_sessions` and `chat_messages`
- RLS policies on all tables (`user_id = auth.uid()`)
- Auto-create profile trigger on sign-up

Optionally, create the pgvector similarity search function:
```sql
create or replace function match_memory_facts(
  query_embedding vector(384),
  match_user_id uuid,
  match_count int
)
returns table (id uuid, fact text, confidence float, created_at timestamptz, similarity float)
language sql
as $$
  select id, fact, confidence, created_at,
    1 - (embedding <=> query_embedding) as similarity
  from memory_facts
  where user_id = match_user_id
  order by embedding <=> query_embedding
  limit match_count;
$$;
```

### 4. Ingest the Knowledge Base

```bash
cd backend
python ingest.py
```

This loads ~20 curated health topics (MedlinePlus, CDC — all public domain) into the Chroma vector store.

### 5. Run the Application

```bash
# Terminal 1: Backend
cd backend
python run.py
# Runs on http://localhost:5000

# Terminal 2: Frontend
cd frontend
npm run dev
# Runs on http://localhost:5173
```

### 6. Run Tests

```bash
cd backend
python -m pytest tests/ -v
```

---

## Project Structure

```
healthcare-chatbot/
├── backend/
│   ├── app/
│   │   ├── __init__.py              # Flask app factory
│   │   ├── routes.py                # API endpoints (10-step pipeline)
│   │   ├── config.py                # All config, weights, thresholds
│   │   ├── schema.sql               # Supabase SQL (pgvector, RLS)
│   │   ├── identity/resolver.py     # JWT verify / guest UUID
│   │   ├── memory/
│   │   │   ├── strong.py            # Supabase pgvector read/write
│   │   │   └── weak.py              # TTLCache guest memory
│   │   ├── rag/
│   │   │   ├── ingestion.py         # Fetch, chunk, embed, store
│   │   │   └── retriever.py         # Query-time top-k retrieval
│   │   ├── ensemble/openrouter.py   # Dynamic model discovery + fan-out
│   │   ├── scoring/ragas_lite.py    # Faithfulness, RQG, scope, safety
│   │   ├── guardrails/
│   │   │   ├── prefilter.py         # Emergency + scope detection
│   │   │   └── postfilter.py        # Disclaimer + citation + safety
│   │   └── prompts/
│   │       ├── __init__.py          # Prompt assembly logic
│   │       └── system_prompt.txt    # Versioned system prompt
│   ├── data/{raw/, kb_index/}
│   ├── tests/                       # 76 tests
│   ├── requirements.txt
│   ├── ingest.py
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── pages/{Landing.jsx, Chat.jsx}
│   │   ├── components/{ChatWindow, MessageBubble, MemorySidebar, CitationList, DisclaimerBanner}
│   │   ├── lib/supabaseClient.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── .env.example
├── docs/
├── .env.example
└── README.md
```

---

## RAGAS-Lite Evaluation

Each candidate response is scored locally (no external API) on four dimensions:

| Metric | Weight | Method |
|---|---|---|
| **Faithfulness** | 0.35 | Split response into claims; embed claims + KB chunks; claim is "supported" if max cosine sim ≥ 0.75 |
| **Relevancy (RQG)** | 0.25 | Generate ~3 reverse questions from the response; embed them + original question; mean cosine sim |
| **Scope** | 0.20 | Key term overlap between response and retrieved context |
| **Safety** | 0.20 | Regex check for diagnostic/dosage language (hard gate: 0 = disqualified), disclaimer presence |

**Composite**: `0.35×F + 0.25×R + 0.20×Sc + 0.20×Sa` — argmax among candidates passing safety gate. All weights/thresholds are configurable in `config.py`.

---

## Known Limitations

- **Free OpenRouter models** have rate limits — fine for a demo, not production traffic.
- **Medical KB is small** and curated for this assignment — not a certified clinical dataset.
- **Emergency detection** is a safety net, not certified triage — always defer to real emergency services.
- **Weak-tier memory loss** on server restart or TTL expiry is **intentional** — it's a design decision (privacy-by-default for anonymous users), not a bug.
- **RAGAS-lite** approximates real RAGAS metrics using local embeddings; running the actual `ragas` package against a labeled eval set is recommended as future work.
- **sentence-transformers download**: First run will download the embedding model (~90 MB).

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | None | Health check |
| `POST` | `/api/chat` | Required | Main chat (full pipeline) |
| `POST` | `/api/session` | Required | Create new chat session |
| `GET` | `/api/memory/profile` | Strong | Get user profile |
| `GET` | `/api/memory/conditions` | Strong | Get medical conditions |
| `DELETE` | `/api/memory/conditions/:id` | Strong | Delete a condition |
| `GET` | `/api/memory/symptoms` | Strong | Get symptom log |
| `DELETE` | `/api/memory/symptoms/:id` | Strong | Delete a symptom |
| `GET` | `/api/memory/facts` | Strong | Get memory facts |
| `DELETE` | `/api/memory/facts/:id` | Strong | Delete a memory fact |
| `DELETE` | `/api/memory/wipe` | Strong | Delete all user data |

---

## License

Built for educational purposes. Medical content sourced from:
- **MedlinePlus** (NIH/NLM) — U.S. government work, public domain
- **CDC** fact sheets — U.S. government work, public domain
# F500Days_Assignment
