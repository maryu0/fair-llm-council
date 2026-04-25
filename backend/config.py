"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# Free-tier API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# OpenRouter API key (legacy fallback)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - free-tier provider/model configs
COUNCIL_MODELS = [
    {"provider": "gemini", "model": "gemini-2.5-flash"},
    {"provider": "groq", "model": "llama-3.1-8b-instant"},
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "gemini-2.5-flash"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
