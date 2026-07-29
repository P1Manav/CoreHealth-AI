# Architecture Presentation: Healthcare AI Chatbot

## Slide 1: Overall System Architecture & Tech Stack

### High-Level Architecture
- **Frontend Layer**: Built with React (Vite), featuring Google OAuth via Supabase JS, sleek dark/light mode UI, optimistic rendering, and skeleton loaders.
- **Backend API Layer**: Modular Python Flask REST server executing a 10-step processing pipeline for each user query.
- **Two-Tier Memory System**:
  - **Strong Tier (Signed-In)**: Supabase Postgres + `pgvector` for semantic memory recall, cross-session history, medical condition tracking, and user privacy controls.
  - **Weak Tier (Guest)**: Lightweight in-memory `TTLCache` with strict privacy guarantees (zero persistent database logging).
- **RAG & Knowledge Base**: ChromaDB local vector store populated with public-domain medical literature (MedlinePlus, CDC) and embedded via `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim).
- **Multi-Model LLM Ensemble**: Dynamic OpenRouter integration fanning out queries to 4 models concurrently (`poolside/laguna-xs-2.1:free`, `cohere/north-mini-code:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`, `google/gemma-4-31b-it:free`) with automatic fallback to `inclusionai/ling-3.0-flash:free`.

---

## Slide 2: LLM Selection & Multi-Model Ensemble Rationale

### Why a Multi-Model Ensemble?
- **No Single Point of Failure**: Open-source free LLM APIs frequently experience transient rate limits, high latency spikes, or sudden deprecations.
- **Concurrence & Fallback**: Queries are executed concurrently using `ThreadPoolExecutor`. If one model fails or rate-limits, candidate responses are harvested from the remaining models.
- **Model Diversity**:
  1. `poolside/laguna-xs-2.1:free` — Fast, concise response formatting.
  2. `cohere/north-mini-code:free` — Exceptional structured instruction following.
  3. `nvidia/nemotron-3-ultra-550b-a55b:free` — High reasoning depth for complex medical queries.
  4. `google/gemma-4-31b-it:free` — Strong general health knowledge.
  5. `inclusionai/ling-3.0-flash:free` — Low-latency primary fallback.

---

## Slide 3: Application Workflow & RAGAS-Lite Scoring

### 10-Step Processing Pipeline
1. **Identity Resolution**: Determines JWT (Strong) vs Guest UUID (Weak).
2. **Pre-Filter Guardrails**: Instant emergency keyword detection & non-healthcare scope redirection.
3. **Memory Retrieval**: Vector cosine similarity lookup on user's past health facts and conditions.
4. **RAG Retrieval**: Top-k similarity search in Chroma vector database.
5. **Prompt Assembly**: System rules + medical KB chunks + user memory + conversation history.
6. **Concurrent Ensemble**: Fan-out prompt to LLM targets in parallel.
7. **RAGAS-Lite Evaluation**: Evaluates candidate outputs locally across 4 metrics:
   - **Faithfulness** (0.35): Claim-level cosine similarity to KB chunks.
   - **Relevancy (RQG)** (0.25): Reverse question generation similarity to original query.
   - **Scope Adherence** (0.20): Term overlap with retrieved medical context.
   - **Safety Gate** (0.20): Strict regex hard-gate against diagnostic or prescription language.
8. **Post-Filter Guardrails**: Strips diagnostic phrasing, attaches verified source citations, and enforces standing disclaimers.
9. **Asynchronous Memory Update**: Extracts newly disclosed symptoms/conditions into Supabase in background.
10. **Response Delivery**: Sends formatted response with citations and metadata to frontend.

---

## Slide 4: Safety Guardrails & Domain Enforcement

### Multi-Layer Safety System
- **Emergency Detection (Pre-filter)**: Regex pattern matching for chest pain, stroke, severe bleeding, self-harm, poisoning, or choking. Intercepts queries immediately with local emergency hotline numbers (911, 112, 108) before making any LLM API call.
- **Domain Scope Enforcement**: Detects non-health topics (politics, coding, finance, math, general trivia) and returns a friendly redirection message.
- **Diagnostic Language Stripping (Post-filter)**: Softens definitive diagnostic claims (e.g. *"You have diabetes"* → *"You may be experiencing symptoms associated with diabetes"*).
- **Mandatory Disclaimers**: Automatically appends standing medical advice disclaimer (`⚠️`) to every healthcare answer.

---

## Slide 5: Key Challenges Faced & Engineering Solutions

### 1. Fragile LLM JSON Memory Extraction
- **Challenge**: LLMs returned markdown-wrapped JSON or unstructured text when extracting user symptoms, breaking background memory saves.
- **Solution**: Implemented a robust multi-pass regex parser in `routes.py` that extracts JSON blocks from code fences (` ```json...``` `) or bare `{...}` objects reliably.

### 2. React Dev Double-Mount & Orphan Sessions
- **Challenge**: React `StrictMode` invoked `useEffect` twice in development, creating duplicate blank sessions in Supabase.
- **Solution**: Added a `sessionCreated` `useRef` guard on the frontend and automated background cleanup of message-less sessions on the backend.

### 3. OpenRouter Model Deprecations & Latency
- **Challenge**: Free tier models periodically return 404s or 429 rate limit errors.
- **Solution**: Designed a dynamic ensemble architecture with multi-model fallback and per-call timeouts (15s) to guarantee high availability.
