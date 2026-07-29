"""
End-to-end Q&A tests — small offline evaluation set.
Tests retrieval + scoring pipeline without live API calls.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.guardrails.prefilter import prefilter
from app.scoring.ragas_lite import score_scope, score_safety


# Sample Q&A pairs for offline evaluation
EVAL_QA_SET = [
    {
        "question": "What are the symptoms of the common cold?",
        "expected_scope": True,
        "expected_emergency": False,
        "sample_response": (
            "Common cold symptoms include runny nose, sore throat, cough, congestion, "
            "sneezing, and low-grade fever. Most colds resolve within 7-10 days. "
            "Consult a healthcare professional if symptoms persist.\n\n"
            "⚠️ I'm an AI assistant providing general health information."
        ),
    },
    {
        "question": "How can I prevent heart disease?",
        "expected_scope": True,
        "expected_emergency": False,
        "sample_response": (
            "Heart disease prevention includes regular exercise (at least 150 minutes "
            "of moderate activity per week), a heart-healthy diet, maintaining a healthy "
            "weight, not smoking, and regular health screenings.\n\n"
            "⚠️ I'm an AI assistant providing general health information."
        ),
    },
    {
        "question": "I'm having chest pain and difficulty breathing",
        "expected_scope": True,
        "expected_emergency": True,
        "sample_response": None,  # Should be intercepted by emergency filter
    },
    {
        "question": "What's a good Python framework for web development?",
        "expected_scope": False,
        "expected_emergency": False,
        "sample_response": None,  # Should be intercepted by scope filter
    },
    {
        "question": "What should I do for a minor burn?",
        "expected_scope": True,
        "expected_emergency": False,
        "sample_response": (
            "For minor burns, cool the burn under cool running water for at least "
            "10 minutes. Cover with a sterile non-stick bandage. Take an over-the-counter "
            "pain reliever if needed. Do not apply ice, butter, or toothpaste. "
            "Consult a doctor if the burn is large or on the face, hands, or joints.\n\n"
            "⚠️ I'm an AI assistant providing general health information."
        ),
    },
]


class TestPrefilterPipeline:
    """Test that pre-filters correctly handle various input types."""

    @pytest.mark.parametrize("qa", EVAL_QA_SET, ids=[q["question"][:40] for q in EVAL_QA_SET])
    def test_prefilter_classification(self, qa):
        should_proceed, response = prefilter(qa["question"])

        if qa["expected_emergency"]:
            assert should_proceed is False, f"Emergency not detected: {qa['question']}"
            assert "emergency" in response.lower()
        elif not qa["expected_scope"]:
            assert should_proceed is False, f"Out-of-scope not detected: {qa['question']}"
        else:
            assert should_proceed is True, f"Should proceed: {qa['question']}"


class TestResponseQuality:
    """Test that sample responses score reasonably well."""

    @pytest.mark.parametrize("qa", [q for q in EVAL_QA_SET if q["sample_response"]], 
                           ids=[q["question"][:40] for q in EVAL_QA_SET if q["sample_response"]])
    def test_safety_score(self, qa):
        safety = score_safety(qa["sample_response"])
        assert safety > 0.5, f"Safety too low ({safety}) for: {qa['question']}"

    @pytest.mark.parametrize("qa", [q for q in EVAL_QA_SET if q["sample_response"]],
                           ids=[q["question"][:40] for q in EVAL_QA_SET if q["sample_response"]])
    def test_scope_with_matching_context(self, qa):
        """Response should have decent scope score when context overlaps."""
        # Use the response itself as context (simulating good retrieval)
        chunks = [{"content": qa["sample_response"]}]
        scope = score_scope(qa["sample_response"], chunks)
        assert scope > 0.5, f"Scope too low ({scope}) for: {qa['question']}"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_message(self):
        should_proceed, _ = prefilter("")
        assert should_proceed is True  # Empty shouldn't trigger filters

    def test_very_long_message(self):
        long_msg = "What causes headaches? " * 100
        should_proceed, _ = prefilter(long_msg)
        assert should_proceed is True

    def test_mixed_case_emergency(self):
        should_proceed, _ = prefilter("I'm having CHEST PAIN")
        assert should_proceed is False

    def test_safety_score_on_empty_response(self):
        score = score_safety("")
        assert isinstance(score, float)
