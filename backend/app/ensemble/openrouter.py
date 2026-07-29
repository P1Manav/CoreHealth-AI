# OpenRouter client for querying LLM models concurrently.
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from app.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    TARGET_ENSEMBLE_MODELS,
    DEFAULT_FALLBACK_MODEL,
    ENSEMBLE_TIMEOUT,
)

logger = logging.getLogger(__name__)


# Get the list of target comparison models.
def get_selected_models():
    return TARGET_ENSEMBLE_MODELS


# Call a single OpenRouter model with timeout.
def _call_model(model_id, messages, timeout=None):
    if timeout is None:
        timeout = ENSEMBLE_TIMEOUT
    start = time.time()
    try:
        resp = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "Healthcare AI Chatbot",
            },
            json={
                "model": model_id,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.3,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        actual_model = data.get("model") or model_id
        return {
            "model": actual_model,
            "requested_model": model_id,
            "content": content,
            "latency": time.time() - start,
            "error": None,
        }
    except requests.exceptions.Timeout:
        return {
            "model": model_id,
            "content": "",
            "latency": time.time() - start,
            "error": "timeout",
        }
    except Exception as e:
        return {
            "model": model_id,
            "content": "",
            "latency": time.time() - start,
            "error": str(e),
        }


# Query target ensemble models concurrently with automatic fallback.
def query_ensemble(messages, models=None, timeout=None, max_retries=0):
    if models is None:
        models = TARGET_ENSEMBLE_MODELS
    if timeout is None:
        timeout = ENSEMBLE_TIMEOUT

    results = []
    with ThreadPoolExecutor(max_workers=max(len(models), 1)) as executor:
        future_to_model = {
            executor.submit(_call_model, model_id, messages, timeout): model_id
            for model_id in models
        }
        for future in as_completed(future_to_model):
            result = future.result()
            if result["error"] is None and result["content"]:
                results.append(result)
            else:
                logger.warning(f"Model {result['model']} did not respond: {result['error']}")

    if not results:
        logger.info(f"Fallback to default model: {DEFAULT_FALLBACK_MODEL}")
        fallback_res = _call_model(DEFAULT_FALLBACK_MODEL, messages, timeout)
        if fallback_res["error"] is None and fallback_res["content"]:
            results.append(fallback_res)
        if not results:
            logger.info("Secondary fallback to openrouter/free")
            sec_res = _call_model("openrouter/free", messages, timeout)
            if sec_res["error"] is None and sec_res["content"]:
                results.append(sec_res)

    return results


# Generate reverse questions for RAGAS evaluation.
def generate_questions_for_rqg(response_text, model_id=None):
    if model_id is None:
        model_id = DEFAULT_FALLBACK_MODEL
    messages = [
        {
            "role": "system",
            "content": (
                "You are a question generator. Given an answer/response about health, "
                "generate exactly 3 questions that this answer would be responding to. "
                "Return only the questions, one per line, numbered 1-3."
            ),
        },
        {
            "role": "user",
            "content": f"Generate 3 questions for this answer:\n\n{response_text}",
        },
    ]
    result = _call_model(model_id, messages, timeout=20)
    if result["error"] or not result["content"]:
        result = _call_model("openrouter/free", messages, timeout=20)
        if result["error"] or not result["content"]:
            return []
    lines = result["content"].strip().split("\n")
    questions = []
    for line in lines:
        line = line.strip()
        if line and line[0].isdigit():
            line = line.lstrip("0123456789.)").strip()
        if line and len(line) > 10:
            questions.append(line)
    return questions[:3]
