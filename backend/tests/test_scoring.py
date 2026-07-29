"""
Tests for the RAGAS-lite scorer — scoring math, composite calculation, edge cases.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.scoring.ragas_lite import (
    cosine_similarity,
    score_faithfulness,
    score_relevancy,
    score_scope,
    score_safety,
    select_best,
)


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector(self):
        a = [0.0, 0.0]
        b = [1.0, 0.0]
        assert cosine_similarity(a, b) == 0.0


class TestScopeScore:
    def test_high_overlap(self):
        response = "Headaches are caused by tension, stress, and dehydration. Treatment includes rest and hydration."
        chunks = [{"content": "Headaches from tension and stress can be treated with rest, hydration, and pain relievers."}]
        score = score_scope(response, chunks)
        assert score > 0.5

    def test_low_overlap(self):
        response = "The stock market crashed dramatically yesterday due to inflation concerns."
        chunks = [{"content": "Headaches are commonly caused by tension and stress."}]
        score = score_scope(response, chunks)
        assert score < 0.5

    def test_empty_chunks(self):
        score = score_scope("Some response text here.", [])
        assert score == 0.5

    def test_empty_response(self):
        score = score_scope("", [{"content": "Some content."}])
        assert score == 1.0


class TestSafetyScore:
    def test_safe_response_with_disclaimer(self):
        response = (
            "Headaches can be caused by many factors.\n\n"
            "⚠️ I'm an AI assistant providing general health information, "
            "not a medical diagnosis."
        )
        score = score_safety(response)
        assert score > 0.5
        assert score > 0.0  # Not disqualified

    def test_diagnostic_language_disqualified(self):
        response = "You have diabetes. Take 500mg of metformin twice daily."
        score = score_safety(response)
        assert score == 0.0  # Hard gate

    def test_prescription_language_disqualified(self):
        response = "I diagnose you with hypertension. You should take 10mg lisinopril daily."
        score = score_safety(response)
        assert score == 0.0  # Hard gate

    def test_safe_with_hedging(self):
        response = (
            "Headaches may be caused by various factors. You could try rest and hydration. "
            "Generally, tension headaches are quite common. Consult a healthcare professional "
            "if symptoms persist.\n\n"
            "⚠️ I'm an AI assistant providing general health information."
        )
        score = score_safety(response)
        assert score > 0.7

    def test_no_disclaimer(self):
        response = "Headaches are common and usually not serious."
        score = score_safety(response)
        assert score < 0.7  # Lower score without disclaimer
        assert score > 0.0  # Not disqualified


class TestSelectBest:
    def test_selects_highest_composite(self):
        # Mock embed function
        def mock_embed(texts):
            return [[1.0, 0.0, 0.0]] * len(texts)

        def mock_rqg(text):
            return ["What causes headaches?", "How to treat headaches?"]

        candidates = [
            {"model": "model_a", "content": "Bad answer without sources.", "latency": 1.0},
            {
                "model": "model_b",
                "content": (
                    "Headaches may be caused by tension and stress. "
                    "Consult a healthcare professional.\n\n"
                    "⚠️ I'm an AI assistant providing general health information."
                ),
                "latency": 1.5,
            },
        ]

        kb_chunks = [{"content": "Headaches are caused by tension, stress, and other factors."}]

        result = select_best(candidates, kb_chunks, "What causes headaches?", mock_embed, mock_rqg)
        assert result["selected"] is True
        assert "composite" in result

    def test_fallback_on_empty_candidates(self):
        def mock_embed(texts):
            return [[1.0, 0.0, 0.0]] * len(texts)

        def mock_rqg(text):
            return []

        result = select_best([], [], "test?", mock_embed, mock_rqg)
        assert result.get("fallback") is True
        assert result["model"] == "fallback"

    def test_fallback_when_all_fail_safety(self):
        def mock_embed(texts):
            return [[1.0, 0.0, 0.0]] * len(texts)

        def mock_rqg(text):
            return []

        candidates = [
            {"model": "model_a", "content": "You have cancer. Take 500mg medication.", "latency": 1.0},
        ]

        result = select_best(candidates, [], "Am I sick?", mock_embed, mock_rqg)
        assert result.get("fallback") is True
