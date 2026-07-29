# Post-filter guardrails — disclaimer enforcement, diagnostic stripping, and citations.
import re
from app.config import STANDING_DISCLAIMER


# Auto-append standing medical disclaimer if missing.
def enforce_disclaimer(response):
    has_disclaimer = (
        "AI assistant" in response and
        ("health information" in response or "medical diagnosis" in response)
    ) or "⚠️" in response
    if not has_disclaimer:
        response = response.rstrip() + "\n\n⚠️ " + STANDING_DISCLAIMER
    return response


# Soften definitive diagnostic or dosage claims.
def strip_diagnostic_language(response):
    replacements = [
        (r'\bYou have\b\s+([\w\s]+(?:disease|disorder|syndrome|condition))', r'You may be experiencing symptoms associated with \1'),
        (r'\b[Tt]ake\s+(\d+\s*(?:mg|ml|g|mcg|IU))\b', r'A healthcare provider might recommend \1'),
        (r'\bI diagnose\b.*?[.!]', 'Please consult a healthcare professional for a proper diagnosis.'),
        (r'\b[Yy]ou should take\b\s+([\w\s]+)', r'A doctor might consider \1'),
    ]
    for pattern, replacement in replacements:
        response = re.sub(pattern, replacement, response)
    return response


# Format and attach source citations for relevant knowledge chunks.
def attach_citations(response, used_chunks):
    if not used_chunks:
        return response
    response_lower = response.lower()
    seen_urls = set()
    citations = []

    for chunk in used_chunks:
        if not isinstance(chunk, dict) or chunk.get("distance", 0.0) > 0.55:
            continue
        meta = chunk.get("metadata", {})
        url = meta.get("source_url", "")
        name = meta.get("source_name", "Unknown Source")
        title = meta.get("title", "")
        if title:
            title_words = [w for w in title.lower().split() if len(w) > 3]
            if title_words and not any(w in response_lower for w in title_words):
                continue
        if url and url not in seen_urls:
            seen_urls.add(url)
            label = f"{title} — {name}" if title else name
            citations.append(f"- [{label}]({url})")

    if citations and "**Sources:**" not in response and "## Sources" not in response:
        response = response.rstrip() + "\n\n**Sources:**\n" + "\n".join(citations)

    return response


# Run all post-filters on the final response.
def postfilter(response, used_chunks=None):
    response = strip_diagnostic_language(response)
    if used_chunks:
        response = attach_citations(response, used_chunks)
    response = enforce_disclaimer(response)
    return response
