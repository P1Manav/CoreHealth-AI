# Backend configuration — loads all settings from environment variables.
import os
from dotenv import load_dotenv

load_dotenv()

# Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

# OpenRouter
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Ensemble models for comparison
TARGET_ENSEMBLE_MODELS = [
    "poolside/laguna-xs-2.1:free",
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "google/gemma-4-31b-it:free",
]

# Fallback model
DEFAULT_FALLBACK_MODEL = "inclusionai/ling-3.0-flash:free"
OPENROUTER_FALLBACK_MODELS = [DEFAULT_FALLBACK_MODEL]
ENSEMBLE_MODEL_COUNT = 4
ENSEMBLE_TIMEOUT = 15

# Embeddings
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

# RAG / Knowledge Base
CHROMA_PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "kb_index"
)
CHROMA_COLLECTION_NAME = "healthcare_kb"
RAG_TOP_K = 5
CHUNK_SIZE = 400
CHUNK_OVERLAP = 80

# RAGAS-Lite scoring weights
SCORE_WEIGHT_FAITHFULNESS = 0.35
SCORE_WEIGHT_RELEVANCY = 0.25
SCORE_WEIGHT_SCOPE = 0.20
SCORE_WEIGHT_SAFETY = 0.20
FAITHFULNESS_SIM_THRESHOLD = 0.75

# Guest (weak-tier) memory
GUEST_TTL_SECONDS = 7200
GUEST_CACHE_MAX_SIZE = 1000
GUEST_MAX_TURNS = 10

# Strong-tier memory
MEMORY_FACTS_TOP_K = 5
STALE_DAYS_THRESHOLD = 7

# Flask
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))

# Safety / Disclaimer
STANDING_DISCLAIMER = (
    "I'm an AI assistant providing general health information, not a medical "
    "diagnosis. Please consult a licensed healthcare professional for personal "
    "medical advice, and contact emergency services for urgent symptoms."
)

SAFE_FALLBACK_RESPONSE = (
    "I'm sorry, I wasn't able to generate a reliable answer for that question. "
    "Please try rephrasing your question, or consult a healthcare professional "
    "for personalized guidance.\n\n"
    "⚠️ " + STANDING_DISCLAIMER
)

EMERGENCY_RESPONSE = (
    "🚨 **This sounds like it could be a medical emergency.**\n\n"
    "Please **call your local emergency number immediately** (e.g. 911 in the US, "
    "112 in Europe, 999 in the UK, 108 in India) or go to the nearest emergency room.\n\n"
    "If you or someone else is in immediate danger, do not wait — seek help now.\n\n"
    "⚠️ " + STANDING_DISCLAIMER
)
