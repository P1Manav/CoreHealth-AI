# Prompt assembly — builds full prompt context for LLM ensemble.
import os

_PROMPT_DIR = os.path.dirname(__file__)
_SYSTEM_PROMPT_PATH = os.path.join(_PROMPT_DIR, "system_prompt.txt")

with open(_SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT_TEMPLATE = f.read()

DEFAULT_INTERACTION_STYLE = (
    "Use a balanced, neutral, and friendly tone. Be concise and clear. "
    "Avoid overly technical medical jargon unless the user demonstrates medical knowledge."
)

STYLE_TEMPLATES = {
    "tends_to_worry": "Be extra reassuring and calm. Acknowledge concern before providing info.",
    "prefers_reassurance": "Start with reassurance when appropriate. Use a warm, calming tone.",
    "asks_followups": "Be thorough and anticipate follow-up questions.",
}

FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": "What causes headaches?"
    },
    {
        "role": "assistant",
        "content": (
            "## Common Causes of Headaches\n\n"
            "Headaches can be caused by many factors:\n\n"
            "**Primary headaches**:\n"
            "- **Tension headaches**: Stress, poor posture, muscle tension\n"
            "- **Migraines**: Throbbing pain, light sensitivity\n\n"
            "**Common triggers**: Dehydration, poor sleep, stress, screen time.\n\n"
            "⚠️ I'm an AI assistant providing general health information, not a medical diagnosis."
        ),
    },
]


# Build tone instruction string from interaction style dict.
def _build_interaction_style_text(interaction_style):
    if not interaction_style:
        return DEFAULT_INTERACTION_STYLE
    parts = [DEFAULT_INTERACTION_STYLE]
    for key, template in STYLE_TEMPLATES.items():
        if interaction_style.get(key):
            parts.append(template)
    return " ".join(parts)


# Format retrieved KB chunks into system prompt block.
def _format_kb_chunks(kb_chunks):
    if not kb_chunks:
        return "No relevant knowledge base content was found for this query."
    lines = ["## Retrieved Knowledge Base Content\n"]
    for i, chunk in enumerate(kb_chunks, 1):
        meta = chunk.get("metadata", {})
        lines.append(f"### Source {i}: {meta.get('title', '')} [{meta.get('source_name', 'Unknown')}]({meta.get('source_url', '')})")
        lines.append(chunk["content"])
        lines.append("")
    return "\n".join(lines)


# Format user memory facts, conditions, and symptoms for prompt context.
def _format_memory_context(memory_facts, conditions, symptoms, stale_items=None):
    parts = []
    if conditions:
        parts.append("## User's Known Medical Conditions")
        for c in conditions:
            parts.append(f"- {c['name']} (status: {c['status']})")
        parts.append("")
    if symptoms:
        parts.append("## User's Reported Symptoms")
        for s in symptoms:
            parts.append(f"- {s['symptom']} (status: {s['status']})")
        parts.append("")
    if memory_facts:
        parts.append("## Relevant User Memory")
        for f in memory_facts:
            parts.append(f"- {f['fact']}")
        parts.append("")
    return "\n".join(parts) if parts else ""


# Assemble system instructions, memory context, and message history into LLM prompt list.
def assemble_prompt(
    kb_chunks,
    recent_turns,
    user_question,
    interaction_style=None,
    memory_facts=None,
    conditions=None,
    symptoms=None,
    stale_items=None,
):
    style_text = _build_interaction_style_text(interaction_style)
    system_content = SYSTEM_PROMPT_TEMPLATE.replace("{interaction_style}", style_text)
    messages = [{"role": "system", "content": system_content}]
    messages.extend(FEW_SHOT_EXAMPLES)
    messages.append({"role": "system", "content": _format_kb_chunks(kb_chunks)})

    if any([memory_facts, conditions, symptoms, stale_items]):
        mem_ctx = _format_memory_context(memory_facts or [], conditions or [], symptoms or [], stale_items)
        if mem_ctx:
            messages.append({"role": "system", "content": mem_ctx})

    if recent_turns:
        for turn in recent_turns:
            messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": user_question})
    return messages
