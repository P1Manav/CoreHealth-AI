"""
Tests for guardrails — emergency detection, scope checking, post-filter.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.guardrails.prefilter import check_emergency, check_scope, prefilter
from app.guardrails.postfilter import enforce_disclaimer, strip_diagnostic_language, postfilter


class TestEmergencyDetection:
    """Emergency detection should catch all high-risk patterns."""

    @pytest.mark.parametrize("text", [
        "I'm having severe chest pain right now",
        "I think I'm having a heart attack",
        "I can't breathe, difficulty breathing",
        "There's severe bleeding that won't stop",
        "I think I'm having a stroke, my face is drooping",
        "I want to kill myself",
        "I'm feeling suicidal today",
        "I've been thinking about self-harm",
        "I overdosed on pills",
        "My throat is swelling and I think it's anaphylaxis",
        "Someone is choking and unconscious",
    ])
    def test_detects_emergencies(self, text):
        assert check_emergency(text) is True, f"Should detect emergency in: {text}"

    @pytest.mark.parametrize("text", [
        "What causes headaches?",
        "How do I improve my diet?",
        "Tell me about diabetes management",
        "What's a good exercise routine?",
        "I have a slight cold",
        "My knee hurts when I run",
        "What vitamins should I take?",
        "How much water should I drink daily?",
    ])
    def test_allows_normal_health_questions(self, text):
        assert check_emergency(text) is False, f"Should NOT flag as emergency: {text}"


class TestScopeDetection:
    """Out-of-scope questions should be redirected."""

    @pytest.mark.parametrize("text", [
        "What's the stock market doing today?",
        "Help me with my Python code",
        "What's the recipe for chocolate cake?",
        "Who won the election?",
        "Solve this math equation: 2x + 3 = 7",
    ])
    def test_detects_out_of_scope(self, text):
        in_scope, redirect = check_scope(text)
        assert in_scope is False, f"Should be out of scope: {text}"
        assert redirect is not None

    @pytest.mark.parametrize("text", [
        "What causes diabetes?",
        "Tell me about heart disease prevention",
        "What's a healthy diet for weight loss?",
        "How do I treat a minor burn?",
        "What are the symptoms of the flu?",
    ])
    def test_allows_health_topics(self, text):
        in_scope, redirect = check_scope(text)
        assert in_scope is True, f"Should be in scope: {text}"
        assert redirect is None


class TestPrefilter:
    def test_emergency_returns_fixed_response(self):
        should_proceed, response = prefilter("I'm having a heart attack, chest pain")
        assert should_proceed is False
        assert "emergency" in response.lower()

    def test_normal_question_proceeds(self):
        should_proceed, response = prefilter("What causes headaches?")
        assert should_proceed is True
        assert response is None


class TestDisclaimerEnforcement:
    def test_adds_disclaimer_when_missing(self):
        response = "Headaches are commonly caused by tension."
        result = enforce_disclaimer(response)
        assert "⚠️" in result
        assert "AI assistant" in result

    def test_keeps_existing_disclaimer(self):
        response = (
            "Headaches are common.\n\n"
            "⚠️ I'm an AI assistant providing general health information."
        )
        result = enforce_disclaimer(response)
        # Should not duplicate
        assert result.count("⚠️") == 1


class TestDiagnosticLanguageStripping:
    def test_softens_you_have_disease(self):
        response = "You have heart disease and should see a doctor."
        result = strip_diagnostic_language(response)
        assert "You have heart disease" not in result
        assert "may be experiencing" in result

    def test_leaves_safe_language_alone(self):
        response = "Headaches may be caused by tension, stress, or dehydration."
        result = strip_diagnostic_language(response)
        assert result == response


class TestPostfilter:
    def test_full_pipeline(self):
        response = "Headaches are common."
        chunks = [{"metadata": {"source_name": "MedlinePlus", "source_url": "https://example.com", "title": "Headaches"}}]
        result = postfilter(response, chunks)
        assert "⚠️" in result  # Disclaimer added
        assert "MedlinePlus" in result  # Citation added
