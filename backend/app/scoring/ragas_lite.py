# RAGAS-lite scorer — computes faithfulness, relevancy, scope, and safety.
import re
import logging
import numpy as np
from app.config import (
    SCORE_WEIGHT_FAITHFULNESS,
    SCORE_WEIGHT_RELEVANCY,
    SCORE_WEIGHT_SCOPE,
    SCORE_WEIGHT_SAFETY,
    FAITHFULNESS_SIM_THRESHOLD,
    SAFE_FALLBACK_RESPONSE,
)

logger = logging.getLogger(__name__)


# Compute cosine similarity between two vectors.
def cosine_similarity(a, b):
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# Split text into sentence-level claims.
def _split_into_claims(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    claims = []
    for s in sentences:
        s = s.strip()
        if len(s) < 15 or s.startswith("⚠️") or s.startswith("#"):
            continue
        if "AI assistant" in s and "disclaimer" in s.lower():
            continue
        claims.append(s)
    return claims


# Score faithfulness of claims against knowledge base chunks.
def score_faithfulness(response, kb_chunks, embed_fn):
    claims = _split_into_claims(response)
    if not claims:
        return 1.0
    chunk_texts = [c["content"] if isinstance(c, dict) else c for c in kb_chunks]
    if not chunk_texts:
        return 0.0
    claim_embeddings = embed_fn(claims)
    chunk_embeddings = embed_fn(chunk_texts)
    supported = 0
    for claim_emb in claim_embeddings:
        max_sim = max(cosine_similarity(claim_emb, chunk_emb) for chunk_emb in chunk_embeddings)
        if max_sim >= FAITHFULNESS_SIM_THRESHOLD:
            supported += 1
    return supported / len(claims)


# Score relevancy via Reverse Question Generation.
def score_relevancy(response, original_question, rqg_fn, embed_fn):
    generated_questions = rqg_fn(response)
    if not generated_questions:
        return 0.5
    all_texts = [original_question] + generated_questions
    embeddings = embed_fn(all_texts)
    original_emb = embeddings[0]
    gen_embs = embeddings[1:]
    similarities = [cosine_similarity(original_emb, g) for g in gen_embs]
    return float(np.mean(similarities))


# Score term overlap between response and context.
def score_scope(response, kb_chunks):
    chunk_texts = [c["content"] if isinstance(c, dict) else c for c in kb_chunks]
    if not chunk_texts:
        return 0.5
    def extract_terms(text):
        return set(re.findall(r'\b[a-zA-Z]{4,}\b', text.lower()))
    response_terms = extract_terms(response)
    context_terms = set()
    for text in chunk_texts:
        context_terms.update(extract_terms(text))
    if not response_terms:
        return 1.0
    overlap = len(response_terms & context_terms)
    return min(overlap / len(response_terms), 1.0)


# Score response safety and medical guardrails.
def score_safety(response):
    response_lower = response.lower()
    diagnostic_patterns = [
        r'\byou have\b.*\b(?:disease|disorder|syndrome|condition|cancer|tumor)\b',
        r'\byou are (?:suffering|diagnosed)\b',
        r'\bi diagnose\b',
        r'\btake \d+\s*(?:mg|ml|g|mcg|iu)\b',
        r'\bprescri(?:be|ption)\b.*\bfor you\b',
        r'\byou should take\b.*\b\d+\s*(?:mg|ml|tablets?|pills?|capsules?)\b',
    ]
    for pattern in diagnostic_patterns:
        if re.search(pattern, response_lower):
            logger.warning(f"Safety hard gate triggered: {pattern}")
            return 0.0

    has_disclaimer = ("ai assistant" in response_lower and ("health information" in response_lower or "medical diagnosis" in response_lower)) or "⚠️" in response
    safety_score = 0.8 if has_disclaimer else 0.4
    if "consult" in response_lower or "healthcare professional" in response_lower:
        safety_score = min(safety_score + 0.1, 1.0)
    hedge_words = ["may", "might", "could", "generally", "typically", "often", "usually"]
    if sum(1 for w in hedge_words if w in response_lower) >= 2:
        safety_score = min(safety_score + 0.1, 1.0)
    return safety_score


# Select best response from ensemble candidates using composite score.
def select_best(candidates, kb_chunks, original_question, embed_fn, rqg_fn):
    if not candidates:
        return {"model": "fallback", "content": SAFE_FALLBACK_RESPONSE, "scores": {}, "composite": 0.0, "selected": True, "fallback": True}
    scored = []
    for candidate in candidates:
        content = candidate["content"]
        try:
            faith = score_faithfulness(content, kb_chunks, embed_fn)
        except Exception:
            faith = 0.5
        try:
            relevancy = score_relevancy(content, original_question, rqg_fn, embed_fn)
        except Exception:
            relevancy = 0.5
        scope = score_scope(content, kb_chunks)
        safety = score_safety(content)
        if safety == 0.0:
            continue
        composite = (
            SCORE_WEIGHT_FAITHFULNESS * faith +
            SCORE_WEIGHT_RELEVANCY * relevancy +
            SCORE_WEIGHT_SCOPE * scope +
            SCORE_WEIGHT_SAFETY * safety
        )
        scored.append({
            "model": candidate["model"],
            "content": content,
            "latency": candidate.get("latency", 0),
            "scores": {
                "faithfulness": round(faith, 3),
                "relevancy": round(relevancy, 3),
                "scope": round(scope, 3),
                "safety": round(safety, 3),
            },
            "composite": round(composite, 3),
        })

    if not scored:
        return {"model": "fallback", "content": SAFE_FALLBACK_RESPONSE, "scores": {}, "composite": 0.0, "selected": True, "fallback": True}
    best = max(scored, key=lambda x: x["composite"])
    best["selected"] = True
    return best
