# v34/config.py
# adding fast_generate_metadata with a classifier

# --- Debugging and Token Management ---
DEBUG_MODE = False

# Endpoint Selection: Choose between /api/chat (legacy) or /api/generate (current)
# False = /api/generate with megaprompt strategy (RECOMMENDED - better memory integration)
# True = /api/chat endpoint (legacy, not actively maintained)
USE_CHAT_ENDPOINT = False

# Megaprompt Strategy: Controls how prompts are constructed for /api/generate
# When True, send the full megaprompt (persona + history + ephemeral system + latest user) every turn.
# When False, use baseline-once + ephemeral tail thereafter with KV context chaining.
USE_FULL_MEGA_PROMPT = True
MAX_TOKENS = 7000
APPROX_CHARS_PER_TOKEN = 4
MAX_CHARS = MAX_TOKENS * APPROX_CHARS_PER_TOKEN

# --- API Endpoints ---
# Using hostname-based URLs for better reliability with WSL2 networking
# However, the actual IP address that tts-server resolves to is not stored in config.py.
# Instead, it's mapped in the WSL /etc/hosts
OLLAMA_API_URL = "http://windows-host:11434/api/generate"
OLLAMA_CHAT_API_URL = "http://windows-host:11434/api/chat"
MODEL_NAME = "llama3.2:3b-instruct-q4_K_M"
#MODEL_NAME = "llava:7b"
# Increase context window – tested on 3B Q4 model with 12 GB VRAM. Adjust if memory errors occur.

LLM_CONTEXT_SIZE = 8000

# --- Retrieval/Injection Controls ---
# When False, the app will NOT inject vector-retrieved memories into prompts (useful for KV/session-only tests)
RETRIEVAL_ENABLED = True

# --- Ollama session handling ---
# Use a fixed session so the server keeps conversation context/K-V cache.
# If you want to reset the context, change this string.
OLLAMA_SESSION_ID = "timmy_default_session"
#TTS_API_URL = "http://tts-server:5000/"
TTS_API_URL = "http://windows-host:5051/"
STT_API_URL = "http://windows-host:8888/"  # STT server on Windows host
MOTOR_API_URL = "http://motor-raspi:8080/"  # Motor controller on Raspberry Pi

# --- Database Configuration ---
DB_CONFIG = {
    "dbname": "timmy_memory_v16",
    "user": "postgres",
    "password": "timmy_postgres_pwd",
    "host": "localhost",
    "port": 5433
}

# --- Memory and Retrieval Tuning ---
MAX_CHUNK_SIZE = 512
OVERLAP_SENTENCES = 1
RECENCY_WEIGHT = 0.25
NUM_RETRIEVED_CHUNKS = 5 