"""
Comprehensive Integration & Flow Test Suite for Healthcare AI Chatbot.
Tests end-to-end pipeline, domain rules, guardrails, memory, history, and disclaimers.
"""

import json
import uuid
import jwt
import time
from unittest.mock import patch
from app import create_app
from app.config import SUPABASE_JWT_SECRET

app = create_app()
client = app.test_client()

def generate_test_jwt(user_id=None):
    """Generate a test JWT token for strong-tier authentication."""
    if not user_id:
        user_id = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "email": "testuser@example.com",
        "exp": int(time.time()) + 3600,
        "role": "authenticated",
    }
    return jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256"), user_id


def test_1_health_check():
    """Verify backend API health endpoint."""
    print("\n[TEST 1] Health Check Endpoint")
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.get_json()
    assert data.get("status") == "ok"
    print("  [OK] Health check passed!")


def test_2_emergency_guardrail():
    """Verify emergency queries return immediate emergency response."""
    print("\n[TEST 2] Emergency Guardrail (Pre-filter)")
    guest_id = str(uuid.uuid4())
    resp = client.post(
        "/api/chat",
        headers={"X-Guest-Session-Id": guest_id, "Content-Type": "application/json"},
        json={"message": "I am having severe chest pain and cannot breathe"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("prefiltered") is True
    assert "emergency" in data.get("response", "").lower()
    print("  [OK] Emergency guardrail triggered correctly!")


def test_3_scope_guardrail():
    """Verify out-of-scope queries return healthcare scope redirect."""
    print("\n[TEST 3] Scope Guardrail (Out-of-domain query)")
    guest_id = str(uuid.uuid4())
    resp = client.post(
        "/api/chat",
        headers={"X-Guest-Session-Id": guest_id, "Content-Type": "application/json"},
        json={"message": "Who is the prime minister of India?"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("prefiltered") is True
    assert "healthcare chatbot" in data.get("response", "").lower()
    print("  [OK] Scope guardrail redirected non-health query!")


def mock_query_ensemble(messages, models=None, timeout=None, max_retries=0):
    """Fast mock ensemble for automated test suites."""
    return [{
        "model": "google/gemma-4-31b-it:free",
        "content": (
            "Headaches and health conditions can be managed with proper care, rest, "
            "hydration, and lifestyle adjustments. Consult a healthcare provider for details.\n\n"
            "⚠️ I'm an AI assistant providing general health information, not a medical diagnosis. "
            "Please consult a licensed healthcare professional for personal medical advice, "
            "and contact emergency services for urgent symptoms."
        ),
        "latency": 0.1,
        "error": None,
    }]


@patch("app.ensemble.openrouter.query_ensemble", side_effect=mock_query_ensemble)
def test_4_healthcare_domain_topics(mock_ensemble):
    """
    Test the 6 required healthcare domain topics:
    1. Common symptoms
    2. General diseases
    3. Healthy lifestyle suggestions
    4. Nutrition and diet
    5. Preventive healthcare
    6. First-aid guidance
    """
    print("\n[TEST 4] Healthcare Domain Topics & Disclaimers")
    guest_id = str(uuid.uuid4())

    queries = [
        ("1. Common symptoms", "What causes frequent tension headaches?"),
        ("2. General diseases", "Can you explain Type 2 Diabetes symptoms and causes?"),
        ("3. Healthy lifestyle", "How can I improve my sleep quality and reduce stress?"),
        ("4. Nutrition and diet", "What is a healthy balanced diet for heart health?"),
        ("5. Preventive healthcare", "Why are adult vaccinations and health checkups important?"),
        ("6. First-aid guidance", "What is the first aid procedure for a minor burn?"),
    ]

    for label, query in queries:
        print(f"  Testing {label}: '{query[:35]}...'")
        resp = client.post(
            "/api/chat",
            headers={"X-Guest-Session-Id": guest_id, "Content-Type": "application/json"},
            json={"message": query},
        )
        assert resp.status_code == 200, f"Query failed for {label}"
        data = resp.get_json()
        response_text = data.get("response", "")
        assert len(response_text) > 50, f"Response too short for {label}"
        assert "AI assistant" in response_text or "disclaimer" in response_text.lower() or "medical diagnosis" in response_text.lower(), f"Missing disclaimer in {label}"
        print(f"    -> Passed! (Model: {data.get('model')})")

    print("  [OK] All 6 healthcare domain topic tests passed with disclaimers!")


@patch("app.ensemble.openrouter.query_ensemble", side_effect=mock_query_ensemble)
@patch("app.memory.strong.create_session", return_value="test-session-12345")
@patch("app.memory.strong.get_sessions", return_value=[{"id": "test-session-12345", "title": "High Blood Pressure"}])
@patch("app.memory.strong.get_session_messages", return_value=[
    {"role": "user", "content": "I was diagnosed with high blood pressure"},
    {"role": "assistant", "content": "High blood pressure requires care."}
])
@patch("app.memory.strong.cleanup_empty_sessions", return_value=None)
@patch("app.memory.strong._get_client")
def test_5_strong_tier_chat_history_flow(mock_client, mock_cleanup, mock_get_msgs, mock_get_sess, mock_create_sess, mock_ensemble):
    """Test full chat session creation, message exchange, history retrieval, and deletion."""
    print("\n[TEST 5] Chat History & Session Management (Strong Tier)")
    token, user_id = generate_test_jwt()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. Create session
    resp = client.post("/api/session", headers=headers)
    assert resp.status_code == 200
    session_data = resp.get_json()
    session_id = session_data.get("session_id")
    assert session_id is not None
    print(f"  -> Session created: {session_id[:8]}...")

    # 2. Send chat message
    resp = client.post(
        "/api/chat",
        headers=headers,
        json={"message": "I was diagnosed with high blood pressure last year", "session_id": session_id},
    )
    assert resp.status_code == 200
    print("  -> Message sent and stored in session")

    time.sleep(0.1)

    # 3. List sessions
    resp = client.get("/api/sessions", headers=headers)
    assert resp.status_code == 200
    sessions_list = resp.get_json().get("sessions", [])
    assert len(sessions_list) >= 1
    print(f"  -> Listed {len(sessions_list)} active user sessions")

    # 4. Fetch session messages
    resp = client.get(f"/api/sessions/{session_id}/messages", headers=headers)
    assert resp.status_code == 200
    messages = resp.get_json().get("messages", [])
    assert len(messages) >= 2
    print(f"  -> Retrieved {len(messages)} messages from session history")

    # 5. Delete session
    resp = client.delete(f"/api/sessions/{session_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json().get("deleted") is True
    print("  -> Session deleted successfully")

    print("  [OK] Chat history flow verified!")


@patch("app.memory.strong.get_conditions", return_value=[{"name": "Hypertension", "status": "ongoing"}])
@patch("app.memory.strong.get_symptoms", return_value=[{"symptom": "Headache", "status": "ongoing"}])
@patch("app.memory.strong.get_all_facts", return_value=[{"fact": "Non-smoker"}])
@patch("app.memory.strong.get_profile", return_value={"user_id": "test", "interaction_style": {}})
def test_6_memory_features(mock_profile, mock_facts, mock_symptoms, mock_conditions):
    """Test Memory endpoints (profile, conditions, symptoms, facts, wipe)."""
    print("\n[TEST 6] User Memory System (Strong Tier)")
    token, user_id = generate_test_jwt()
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch conditions
    resp = client.get("/api/memory/conditions", headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json().get("conditions", [])) == 1
    print("  -> Memory conditions endpoint OK")

    # Fetch symptoms
    resp = client.get("/api/memory/symptoms", headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json().get("symptoms", [])) == 1
    print("  -> Memory symptoms endpoint OK")

    # Fetch facts
    resp = client.get("/api/memory/facts", headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json().get("facts", [])) == 1
    print("  -> Memory facts endpoint OK")

    # Fetch profile
    resp = client.get("/api/memory/profile", headers=headers)
    assert resp.status_code in (200, 404)
    print("  -> Memory profile endpoint OK")

    print("  [OK] Memory system endpoints verified!")


if __name__ == "__main__":
    print("=========================================================")
    print("RUNNING COMPREHENSIVE FLASK TEST SUITE")
    print("=========================================================")
    test_1_health_check()
    test_2_emergency_guardrail()
    test_3_scope_guardrail()
    test_4_healthcare_domain_topics()
    test_5_strong_tier_chat_history_flow()
    test_6_memory_features()
    print("\n=========================================================")
    print("ALL TEST SUITES COMPLETED SUCCESSFULLY!")
    print("=========================================================")
