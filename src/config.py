import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5")  # "gpt-4o-mini" possible
PORT = int(os.getenv("PORT", "8080"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "86400"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_MAX_TOKENS = int(os.getenv("RAG_MAX_TOKENS", "9000"))
USE_STUB_OPENAI = os.getenv("USE_STUB_OPENAI", "false").lower() in ("1","true","yes")
MODEL_TEMPERATURE = os.getenv("MODEL_TEMPERATURE")
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1")
APP_NAME = os.getenv("APP_NAME", "dreamai")
CACHE_SHARDS = int(os.getenv("CACHE_SHARDS", "1"))
PROMPT_PREFIX_PATH = os.getenv("PROMPT_PREFIX_PATH", "prompts/dream_prefix_v1.txt")
