# Strong memory tier — Supabase Postgres + pgvector for signed-in users.
from datetime import datetime, timedelta, timezone
from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, MEMORY_FACTS_TOP_K, STALE_DAYS_THRESHOLD

_supabase = None


# Lazily initialize the Supabase client.
def _get_client():
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _supabase


# Get user profile dict.
def get_profile(user_id):
    client = _get_client()
    result = client.table("profiles").select("*").eq("user_id", user_id).execute()
    return result.data[0] if result.data else None


# Update profile fields.
def update_profile(user_id, updates):
    client = _get_client()
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    client.table("profiles").update(updates).eq("user_id", user_id).execute()


# Create or update profile entry.
def upsert_profile(user_id, data=None):
    profile = get_profile(user_id)
    if profile is None:
        insert_data = {"user_id": user_id}
        if data:
            insert_data.update(data)
        _get_client().table("profiles").insert(insert_data).execute()
    elif data:
        update_profile(user_id, data)


# Get medical conditions for a user.
def get_conditions(user_id):
    result = _get_client().table("medical_conditions").select("*").eq("user_id", user_id).order("last_checked", desc=True).execute()
    return result.data


# Create or update a medical condition entry.
def upsert_condition(user_id, name, status="ongoing"):
    client = _get_client()
    existing = client.table("medical_conditions").select("id").eq("user_id", user_id).ilike("name", name).execute()
    now = datetime.now(timezone.utc).isoformat()
    if existing.data:
        client.table("medical_conditions").update({"status": status, "last_checked": now}).eq("id", existing.data[0]["id"]).execute()
    else:
        client.table("medical_conditions").insert({"user_id": user_id, "name": name, "status": status, "first_mentioned": now, "last_checked": now}).execute()


# Delete a medical condition by ID.
def delete_condition(user_id, condition_id):
    _get_client().table("medical_conditions").delete().eq("id", condition_id).eq("user_id", user_id).execute()


# Get symptoms for a user.
def get_symptoms(user_id):
    result = _get_client().table("symptom_log").select("*").eq("user_id", user_id).order("last_checked", desc=True).execute()
    return result.data


# Create or update a symptom entry.
def upsert_symptom(user_id, symptom, status="ongoing"):
    client = _get_client()
    existing = client.table("symptom_log").select("id").eq("user_id", user_id).ilike("symptom", symptom).execute()
    now = datetime.now(timezone.utc).isoformat()
    if existing.data:
        client.table("symptom_log").update({"status": status, "last_checked": now}).eq("id", existing.data[0]["id"]).execute()
    else:
        client.table("symptom_log").insert({"user_id": user_id, "symptom": symptom, "status": status, "first_mentioned": now, "last_checked": now}).execute()


# Delete a symptom entry by ID.
def delete_symptom(user_id, symptom_id):
    _get_client().table("symptom_log").delete().eq("id", symptom_id).eq("user_id", user_id).execute()


# Retrieve relevant memory facts via vector similarity.
def get_relevant_facts(user_id, query_embedding, top_k=None):
    if top_k is None:
        top_k = MEMORY_FACTS_TOP_K
    client = _get_client()
    try:
        result = client.rpc("match_memory_facts", {"query_embedding": query_embedding, "match_user_id": user_id, "match_count": top_k}).execute()
        return result.data if result.data else []
    except Exception:
        result = client.table("memory_facts").select("id, fact, confidence, created_at").eq("user_id", user_id).order("created_at", desc=True).limit(top_k * 2).execute()
        return result.data if result.data else []


# Add a memory fact with vector embedding.
def add_memory_fact(user_id, fact, embedding, confidence=0.8, source_message_id=None):
    data = {"user_id": user_id, "fact": fact, "embedding": embedding, "confidence": confidence}
    if source_message_id:
        data["source_message_id"] = source_message_id
    _get_client().table("memory_facts").insert(data).execute()


# Delete a memory fact by ID.
def delete_memory_fact(user_id, fact_id):
    _get_client().table("memory_facts").delete().eq("id", fact_id).eq("user_id", user_id).execute()


# Get all memory facts for a user.
def get_all_facts(user_id):
    result = _get_client().table("memory_facts").select("id, fact, confidence, created_at").eq("user_id", user_id).order("created_at", desc=True).execute()
    return result.data if result.data else []


# Delete empty orphan chat sessions.
def cleanup_empty_sessions(user_id):
    client = _get_client()
    try:
        sessions = get_sessions(user_id, limit=100)
        for s in sessions:
            msg_check = client.table("chat_messages").select("id").eq("session_id", s["id"]).limit(1).execute()
            if not msg_check.data:
                client.table("chat_sessions").delete().eq("id", s["id"]).execute()
    except Exception:
        pass


# Create a new chat session.
def create_session(user_id, title=None):
    data = {"user_id": user_id}
    if title:
        data["title"] = title
    result = _get_client().table("chat_sessions").insert(data).execute()
    return result.data[0]["id"] if result.data else None


# Update session title.
def update_session_title(session_id, title):
    _get_client().table("chat_sessions").update({"title": title}).eq("id", session_id).execute()


# Get user's chat sessions.
def get_sessions(user_id, limit=10):
    result = _get_client().table("chat_sessions").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
    return result.data if result.data else []


# Save a chat message.
def save_chat_message(session_id, role, content):
    _get_client().table("chat_messages").insert({"session_id": session_id, "role": role, "content": content}).execute()


# Get messages for a session.
def get_session_messages(session_id, limit=20):
    result = _get_client().table("chat_messages").select("*").eq("session_id", session_id).order("created_at").limit(limit).execute()
    return result.data if result.data else []


# Get stale ongoing conditions and symptoms for proactive check-in.
def get_stale_items(user_id, days_threshold=None):
    if days_threshold is None:
        days_threshold = STALE_DAYS_THRESHOLD
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_threshold)).isoformat()
    client = _get_client()
    stale_conditions = client.table("medical_conditions").select("id, name, status, last_checked").eq("user_id", user_id).eq("status", "ongoing").lt("last_checked", cutoff).execute()
    stale_symptoms = client.table("symptom_log").select("id, symptom, status, last_checked").eq("user_id", user_id).eq("status", "ongoing").lt("last_checked", cutoff).execute()
    return {"conditions": stale_conditions.data or [], "symptoms": stale_symptoms.data or []}


# Update user interaction style heuristics.
def update_interaction_style(user_id, user_message):
    profile = get_profile(user_id)
    if not profile:
        return
    style = profile.get("interaction_style") or {}
    worry_phrases = ["is this serious", "should i worry", "am i going to", "is it dangerous", "could this be cancer", "am i dying", "is this normal", "should i be concerned"]
    msg_lower = user_message.lower()
    if any(phrase in msg_lower for phrase in worry_phrases):
        style["tends_to_worry"] = True
    if msg_lower.strip().endswith("?"):
        style["asks_followups"] = True
    if style.get("tends_to_worry"):
        style["prefers_reassurance"] = True
    update_profile(user_id, {"interaction_style": style})


# Delete all data for a user.
def wipe_user_data(user_id):
    client = _get_client()
    sessions = client.table("chat_sessions").select("id").eq("user_id", user_id).execute()
    if sessions.data:
        for sid in [s["id"] for s in sessions.data]:
            client.table("chat_messages").delete().eq("session_id", sid).execute()
    client.table("chat_sessions").delete().eq("user_id", user_id).execute()
    client.table("memory_facts").delete().eq("user_id", user_id).execute()
    client.table("symptom_log").delete().eq("user_id", user_id).execute()
    client.table("medical_conditions").delete().eq("user_id", user_id).execute()
    client.table("profiles").delete().eq("user_id", user_id).execute()
