# Logic Documentation: Healthcare AI Chatbot

## 1. How User Queries Are Processed

Each incoming HTTP `POST /api/chat` request goes through a deterministic 10-step pipeline:

1. **Authentication & Identity Resolution**:
   - The backend checks for `Authorization: Bearer <jwt>` (Strong Tier) or `X-Guest-Session-Id: <uuid>` (Weak Tier).
   - If neither header is valid, the request is rejected with `401 Unauthorized`.

2. **Pre-Filter Validation**:
   - The user query is checked against `EMERGENCY_PATTERNS` (chest pain, stroke, self-harm, severe bleeding, anaphylaxis). If matched, an immediate emergency warning is returned without calling the LLM.
   - The query is checked for healthcare scope. Non-health questions (coding, politics, math, general trivia) return a scope redirect message immediately.

3. **Memory & Context Retrieval**:
   - **Strong Tier**: Retrieves medical conditions, symptom log, and performs a 384-dimensional vector similarity search over past `memory_facts` using `pgvector`.
   - **Weak Tier**: Retrieves the last 10 conversation turns from `TTLCache`.

4. **Knowledge Base Retrieval (RAG)**:
   - Embeds the query using `sentence-transformers` (`all-MiniLM-L6-v2`) and performs cosine similarity search against ChromaDB to retrieve the top-5 relevant medical KB chunks.

5. **Prompt Assembly**:
   - Constructs system instructions, medical guidelines, retrieved KB chunks, user memory facts, interaction style guidelines, and conversation history into an OpenRouter-compatible messages array.

6. **Ensemble Execution**:
   - Fires concurrent requests via `ThreadPoolExecutor` across specified models (`poolside/laguna-xs-2.1:free`, `cohere/north-mini-code:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`, `google/gemma-4-31b-it:free`). Falls back to `inclusionai/ling-3.0-flash:free` if needed.

7. **RAGAS-Lite Response Selection**:
   - Evaluates candidate outputs locally across Faithfulness, Relevancy, Scope Adherence, and Safety. Disqualifies responses that fail the diagnostic safety gate and selects the highest scoring composite output.

8. **Post-Filtering & Guardrails**:
   - Strips or softens definitive diagnostic phrasing, attaches verified Markdown source citations, and ensures standing medical disclaimers are present.

9. **Asynchronous Memory Update**:
   - In a background thread (for Strong Tier users), lightweight LLM extraction identifies any newly disclosed symptoms or conditions and upserts them into Supabase.

10. **Response Delivery**:
    - Returns JSON containing `response`, `tier`, `citations`, `model`, and evaluation metadata to the client.

---

## 2. How Prompts Are Customized

System prompts are assembled dynamically in `app/prompts/__init__.py`:

- **Standing System Persona**: Instructs the model to act as a helpful healthcare information assistant, strictly prohibiting definitive diagnoses or prescription advice.
- **Interaction Style Adaptation**:
  - `tends_to_worry`: Appends instructions to use a calming, extra-reassuring tone.
  - `prefers_reassurance`: Emphasizes warm, positive framing.
  - `asks_followups`: Encourages thorough explanations anticipating follow-up questions.
- **Few-Shot Examples**: Includes curated user/assistant interaction pairs demonstrating ideal formatting, citations, and disclaimer placement.
- **RAG Context Block**: Injects retrieved MedlinePlus and CDC knowledge base articles directly above the conversation history.

---

## 3. How Responses Are Generated & Evaluated

- **Response Generation**: Generated via OpenRouter API using low temperature (`0.3`) for high factual consistency and reduced hallucination risk.
- **Local Scoring (RAGAS-Lite)**:
  - **Faithfulness (35%)**: Measures sentence-level similarity against retrieved RAG chunks (threshold `0.75`).
  - **Relevancy (25%)**: Uses Reverse Question Generation (RQG) to compare generated questions with the original user query.
  - **Scope (20%)**: Measures medical keyword overlap between response and RAG context.
  - **Safety (20%)**: Enforces hard-gates against diagnostic language and checks for mandatory disclaimers.

---

## 4. Safety & Validation Measures

- **Emergency Pre-Filter**: Instant redirection for high-risk medical emergencies.
- **Domain Guardrails**: Strict exclusion of out-of-domain topics.
- **Diagnostic Stripping**: Softens language like *"You have X"* to *"You may be experiencing symptoms associated with X"*.
- **Mandatory Disclaimers**: Standing disclaimer auto-appended to all answers (`⚠️ I'm an AI assistant providing general health information...`).
- **Database Row Level Security (RLS)**: Enforces `user_id = auth.uid()` on Supabase Postgres tables to prevent unauthorized cross-user data access.

---

## 5. Development Assumptions

- **Non-Diagnostic Scope**: The system assumes users seek general healthcare guidance, first aid advice, or educational health information, not emergency triage or clinical diagnosis.
- **Public Domain Data**: Medical knowledge is sourced from public domain U.S. government publications (MedlinePlus, CDC).
- **Guest Privacy**: Guest sessions are ephemeral by design and expire after 2 hours of inactivity.
