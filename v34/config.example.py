# config.example.py
# Copy this file to config.py and update with your actual values

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
# Configure these hostnames in your /etc/hosts file (see README_NETWORKING.md)
OLLAMA_API_URL = "http://windows-host:11434/api/generate"
OLLAMA_CHAT_API_URL = "http://windows-host:11434/api/chat"
MODEL_NAME = "llama3.2:3b-instruct-q4_K_M"

# Increase context window – tested on 3B Q4 model with 12 GB VRAM. Adjust if memory errors occur.
LLM_CONTEXT_SIZE = 8000

# --- Retrieval/Injection Controls ---
# When False, the app will NOT inject vector-retrieved memories into prompts (useful for KV/session-only tests)
RETRIEVAL_ENABLED = True

# --- Ollama session handling ---
# Use a fixed session so the server keeps conversation context/K-V cache.
# If you want to reset the context, change this string.
OLLAMA_SESSION_ID = "timmy_default_session"

# --- External Services ---
TTS_API_URL = "http://windows-host:5051/"
STT_API_URL = "http://windows-host:8888/"  # STT server on Windows host
MOTOR_API_URL = "http://motor-raspi:8080/"  # Motor controller on Raspberry Pi

# --- Database Configuration ---
# IMPORTANT: Change the password from the default!
DB_CONFIG = {
    "dbname": "timmy_memory_v16",
    "user": "postgres",
    "password": "CHANGE_THIS_PASSWORD",  # ⚠️ Change this!
    "host": "localhost",
    "port": 5433
}

# --- Memory and Retrieval Tuning ---
MAX_CHUNK_SIZE = 512
OVERLAP_SENTENCES = 1
RECENCY_WEIGHT = 0.75  # Weight for recent memories (higher = stronger recency bias)
NUM_RETRIEVED_CHUNKS = 5

