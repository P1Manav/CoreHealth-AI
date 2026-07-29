# API routes for the Healthcare AI Chatbot backend.
import logging
import json
import threading
from flask import Blueprint, request, jsonify, g
from app.identity.resolver import require_identity, get_identity
from app.guardrails.prefilter import prefilter
from app.guardrails.postfilter import postfilter
from app.config import SAFE_FALLBACK_RESPONSE

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__)


# Simple health check endpoint.
@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Healthcare Chatbot API is running"})


# Main chat endpoint handling guardrails, RAG retrieval, ensemble querying, and memory updates.
@api_bp.route("/chat", methods=["POST"])
@require_identity
def chat():
    data = request.get_json()
    if not data or not data.get("message"):
        return jsonify({"error": "Missing 'message' in request body"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    identity = get_identity()
    tier = identity["tier"]
    user_id = identity["user_id"]

    should_proceed, prefilter_response = prefilter(user_message)
    if not should_proceed:
        _save_turn(tier, user_id, user_message, prefilter_response, data.get("session_id"))
        return jsonify({
            "response": prefilter_response,
            "tier": tier,
            "citations": [],
            "prefiltered": True,
        })

    recent_turns, memory_facts, conditions, symptoms = [], [], [], []
    stale_items, interaction_style = None, None

    if tier == "strong":
        try:
            from app.memory import strong as strong_memory
            from app.rag.retriever import embed_text
            profile = strong_memory.get_profile(user_id)
            if profile:
                interaction_style = profile.get("interaction_style")
            query_emb = embed_text(user_message)
            memory_facts = strong_memory.get_relevant_facts(user_id, query_emb)
            conditions = strong_memory.get_conditions(user_id)
            symptoms = strong_memory.get_symptoms(user_id)
            if not data.get("session_id"):
                stale_items = strong_memory.get_stale_items(user_id)
            sessions = strong_memory.get_sessions(user_id, limit=1)
            if sessions:
                raw_turns = strong_memory.get_session_messages(sessions[0]["id"], limit=10)
                recent_turns = [{"role": t["role"], "content": t["content"]} for t in raw_turns]
        except Exception as e:
            logger.error(f"Strong memory retrieval error: {e}")
    else:
        try:
            from app.memory import weak as weak_memory
            recent_turns = weak_memory.get_context(user_id)
        except Exception as e:
            logger.error(f"Weak memory retrieval error: {e}")

    kb_chunks = []
    try:
        from app.rag.retriever import retrieve
        kb_chunks = retrieve(user_message)
    except Exception as e:
        logger.error(f"RAG retrieval error: {e}")

    from app.prompts import assemble_prompt
    messages = assemble_prompt(
        kb_chunks=kb_chunks,
        recent_turns=recent_turns,
        user_question=user_message,
        interaction_style=interaction_style,
        memory_facts=memory_facts,
        conditions=conditions,
        symptoms=symptoms,
        stale_items=stale_items,
    )

    candidates = []
    try:
        from app.ensemble.openrouter import query_ensemble
        candidates = query_ensemble(messages)
    except Exception as e:
        logger.error(f"Ensemble error: {e}")

    if not candidates:
        _save_turn(tier, user_id, user_message, SAFE_FALLBACK_RESPONSE, data.get("session_id"))
        return jsonify({
            "response": SAFE_FALLBACK_RESPONSE,
            "tier": tier,
            "citations": [],
            "error": "No model responses received",
        })

    best = {
        "model": candidates[0]["model"],
        "content": candidates[0]["content"],
        "scores": {},
        "composite": 1.0,
        "selected": True,
    }
    response_text = postfilter(best.get("content", SAFE_FALLBACK_RESPONSE), kb_chunks)

    if tier == "strong":
        threading.Thread(
            target=_update_strong_memory,
            args=(user_id, user_message, response_text, data.get("session_id")),
            daemon=True,
        ).start()

    _save_turn(tier, user_id, user_message, response_text, data.get("session_id"))

    if tier == "strong" and data.get("session_id"):
        def _auto_title():
            try:
                from app.memory import strong as strong_memory
                session_id = data.get("session_id")
                msgs = strong_memory.get_session_messages(session_id, limit=2)
                if len(msgs) <= 2:
                    title = user_message[:60] + ("..." if len(user_message) > 60 else "")
                    strong_memory.update_session_title(session_id, title)
            except Exception:
                pass
        threading.Thread(target=_auto_title, daemon=True).start()

    citations = _extract_citations(kb_chunks, response_text)
    return jsonify({
        "response": response_text,
        "tier": tier,
        "citations": citations,
        "model": best.get("model", "unknown"),
        "scores": best.get("scores", {}),
        "composite": best.get("composite", 0),
    })


# Save chat message turn to session storage.
def _save_turn(tier, user_id, user_message, response, session_id=None):
    try:
        if tier == "weak":
            from app.memory import weak as weak_memory
            weak_memory.add_turn(user_id, "user", user_message)
            weak_memory.add_turn(user_id, "assistant", response)
        elif tier == "strong" and session_id:
            from app.memory import strong as strong_memory
            strong_memory.save_chat_message(session_id, "user", user_message)
            strong_memory.save_chat_message(session_id, "assistant", response)
    except Exception as e:
        logger.error(f"Error saving turn: {e}")


# Background task to extract symptoms, conditions, and facts for strong memory.
def _update_strong_memory(user_id, user_message, response, session_id):
    try:
        from app.memory import strong as strong_memory
        from app.ensemble.openrouter import _call_model, get_selected_models
        from app.rag.retriever import embed_text

        strong_memory.update_interaction_style(user_id, user_message)
        models = get_selected_models()
        extraction_model = models[-1] if models else None
        if not extraction_model:
            return

        extraction_prompt = [
            {
                "role": "system",
                "content": (
                    "You are a medical information extractor. Given a user message in a health chat, "
                    "extract any newly disclosed health information. Return a JSON object with these fields "
                    "(use empty arrays if nothing found):\n"
                    '{"conditions": [{"name": "...", "status": "ongoing|resolved|unknown"}], '
                    '"symptoms": [{"symptom": "...", "status": "ongoing|resolved|unknown"}], '
                    '"facts": ["fact1", "fact2"]}\n'
                    "Only extract clearly stated health information. Do not infer or assume."
                ),
            },
            {"role": "user", "content": user_message},
        ]
        result = _call_model(extraction_model, extraction_prompt, timeout=15)
        if result["error"] or not result["content"]:
            return

        try:
            content = result["content"].strip()
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', content)
            if json_match:
                content = json_match.group(1).strip()
            else:
                brace_match = re.search(r'(\{[\s\S]+\})', content)
                if brace_match:
                    content = brace_match.group(1).strip()
            extracted = json.loads(content)
        except Exception:
            return

        for condition in extracted.get("conditions", []):
            if condition.get("name"):
                strong_memory.upsert_condition(user_id, condition["name"], condition.get("status", "ongoing"))

        for symptom in extracted.get("symptoms", []):
            if symptom.get("symptom"):
                strong_memory.upsert_symptom(user_id, symptom["symptom"], symptom.get("status", "ongoing"))

        for fact in extracted.get("facts", []):
            if fact and len(fact) > 5:
                embedding = embed_text(fact)
                strong_memory.add_memory_fact(user_id, fact, embedding)
    except Exception as e:
        logger.error(f"Memory update error: {e}")


# Extract deduplicated citation info from relevant KB chunks.
def _extract_citations(kb_chunks, response_text=None):
    citations = []
    seen = set()
    response_lower = (response_text or "").lower()
    for chunk in kb_chunks:
        if not isinstance(chunk, dict) or chunk.get("distance", 0.0) > 0.55:
            continue
        meta = chunk.get("metadata", {})
        url = meta.get("source_url", "")
        title = meta.get("title", "")
        if response_lower and title:
            title_words = [w for w in title.lower().split() if len(w) > 3]
            if title_words and not any(w in response_lower for w in title_words):
                continue
        if url and url not in seen:
            seen.add(url)
            citations.append({
                "source_name": meta.get("source_name", "Unknown"),
                "source_url": url,
                "title": title,
            })
    return citations


# Create a new chat session.
@api_bp.route("/session", methods=["POST"])
@require_identity
def create_session():
    identity = get_identity()
    if identity["tier"] != "strong":
        return jsonify({"session_id": None, "tier": "weak"})
    try:
        from app.memory import strong as strong_memory
        threading.Thread(target=strong_memory.cleanup_empty_sessions, args=(identity["user_id"],), daemon=True).start()
        session_id = strong_memory.create_session(identity["user_id"])
        stale = strong_memory.get_stale_items(identity["user_id"])
        checkin_message = None
        if stale["conditions"] or stale["symptoms"]:
            items = [f"'{c['name']}'" for c in stale["conditions"]] + [f"'{s['symptom']}'" for s in stale["symptoms"]]
            checkin_message = f"Welcome back! Last time you mentioned {', '.join(items)}. How have things been going with that?"
        return jsonify({"session_id": session_id, "tier": "strong", "checkin_message": checkin_message})
    except Exception as e:
        logger.error(f"Session creation error: {e}")
        return jsonify({"error": str(e)}), 500


# List all chat sessions for the user.
@api_bp.route("/sessions", methods=["GET"])
@require_identity
def list_sessions():
    identity = get_identity()
    if identity["tier"] != "strong":
        return jsonify({"sessions": []})
    try:
        from app.memory import strong as strong_memory
        sessions = strong_memory.get_sessions(identity["user_id"], limit=30)
        return jsonify({"sessions": sessions})
    except Exception as e:
        logger.error(f"List sessions error: {e}")
        return jsonify({"sessions": []})


# Get messages from a specific session.
@api_bp.route("/sessions/<session_id>/messages", methods=["GET"])
@require_identity
def get_session_messages_endpoint(session_id):
    identity = get_identity()
    if identity["tier"] != "strong":
        return jsonify({"messages": []}), 403
    try:
        from app.memory import strong as strong_memory
        sessions = strong_memory.get_sessions(identity["user_id"], limit=100)
        if session_id not in {s["id"] for s in sessions}:
            return jsonify({"error": "Session not found"}), 404
        messages = strong_memory.get_session_messages(session_id, limit=100)
        return jsonify({"messages": messages})
    except Exception as e:
        logger.error(f"Get session messages error: {e}")
        return jsonify({"messages": []})


# Delete a chat session.
@api_bp.route("/sessions/<session_id>", methods=["DELETE"])
@require_identity
def delete_session(session_id):
    identity = get_identity()
    if identity["tier"] != "strong":
        return jsonify({"error": "Auth required"}), 403
    try:
        from app.memory import strong as strong_memory
        sessions = strong_memory.get_sessions(identity["user_id"], limit=100)
        if session_id not in {s["id"] for s in sessions}:
            return jsonify({"error": "Session not found"}), 404
        client = strong_memory._get_client()
        client.table("chat_messages").delete().eq("session_id", session_id).execute()
        client.table("chat_sessions").delete().eq("id", session_id).execute()
        return jsonify({"deleted": True})
    except Exception as e:
        logger.error(f"Delete session error: {e}")
        return jsonify({"error": str(e)}), 500


# Get user profile.
@api_bp.route("/memory/profile", methods=["GET"])
@require_identity
def get_memory_profile():
    identity = get_identity()
    if identity["tier"] != "strong":
        return jsonify({"error": "Memory features require sign-in"}), 403
    from app.memory import strong as strong_memory
    profile = strong_memory.get_profile(identity["user_id"])
    return jsonify({"profile": profile})


# Get user's medical conditions.
@api_bp.route("/memory/conditions", methods=["GET"])
@require_identity
def get_memory_conditions():
    identity = get_identity()
    if identity["tier"] != "strong":
        return jsonify({"error": "Memory features require sign-in"}), 403
    from app.memory import strong as strong_memory
    conditions = strong_memory.get_conditions(identity["user_id"])
    return jsonify({"conditions": conditions})


# Delete a medical condition.
@api_bp.route("/memory/conditions/<condition_id>", methods=["DELETE"])
@require_identity
def delete_memory_condition(condition_id):
    identity = get_identity()
    if identity["tier"] != "strong":
        return jsonify({"error": "Memory features require sign-in"}), 403
    from app.memory import strong as strong_memory
    strong_memory.delete_condition(identity["user_id"], condition_id)
    return jsonify({"deleted": True})


# Get user's symptom log.
@api_bp.route("/memory/symptoms", methods=["GET"])
@require_identity
def get_memory_symptoms():
    identity = get_identity()
    if identity["tier"] != "strong":
        return jsonify({"error": "Memory features require sign-in"}), 403
    from app.memory import strong as strong_memory
    symptoms = strong_memory.get_symptoms(identity["user_id"])
    return jsonify({"symptoms": symptoms})


# Delete a symptom entry.
@api_bp.route("/memory/symptoms/<symptom_id>", methods=["DELETE"])
@require_identity
def delete_memory_symptom(symptom_id):
    identity = get_identity()
    if identity["tier"] != "strong":
        return jsonify({"error": "Memory features require sign-in"}), 403
    from app.memory import strong as strong_memory
    strong_memory.delete_symptom(identity["user_id"], symptom_id)
    return jsonify({"deleted": True})


# Get user's memory facts.
@api_bp.route("/memory/facts", methods=["GET"])
@require_identity
def get_memory_facts():
    identity = get_identity()
    if identity["tier"] != "strong":
        return jsonify({"error": "Memory features require sign-in"}), 403
    from app.memory import strong as strong_memory
    facts = strong_memory.get_all_facts(identity["user_id"])
    return jsonify({"facts": facts})


# Delete a memory fact.
@api_bp.route("/memory/facts/<fact_id>", methods=["DELETE"])
@require_identity
def delete_memory_fact(fact_id):
    identity = get_identity()
    if identity["tier"] != "strong":
        return jsonify({"error": "Memory features require sign-in"}), 403
    from app.memory import strong as strong_memory
    strong_memory.delete_memory_fact(identity["user_id"], fact_id)
    return jsonify({"deleted": True})


# Wipe all data for user.
@api_bp.route("/memory/wipe", methods=["DELETE"])
@require_identity
def wipe_user_data():
    identity = get_identity()
    if identity["tier"] != "strong":
        return jsonify({"error": "Memory features require sign-in"}), 403
    from app.memory import strong as strong_memory
    strong_memory.wipe_user_data(identity["user_id"])
    return jsonify({"wiped": True})
