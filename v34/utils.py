# v34/utils.py
# adding fast_generate_metadata with a classifier

from sentence_transformers import SentenceTransformer
from datetime import datetime
import nltk
import config

# --- Shared State & Models ---

# A simple in-memory conversation store, shared across modules
conversation_history = []

# The embedding model will be loaded lazily to avoid blocking server startup.
embed_model = None
dimension = 384 # Hardcoded for sentence-transformers/all-MiniLM-L6-v2

def get_embed_model():
    """Lazily initializes and returns the sentence transformer model."""
    global embed_model
    if embed_model is None:
        print("*** Debug: Initializing embed_model for the first time...")
        embed_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        print("*** Debug: Embed model initialized.")
    return embed_model

# --- Utility Functions ---

def debug_print(*args, **kwargs):
    """Only prints if DEBUG_MODE is True."""
    if config.DEBUG_MODE:
        print(*args, **kwargs)

def time_ago(dt: datetime) -> str:
    """Converts a naive datetime object to a human-readable 'time ago' string."""
    now = datetime.now()
    if dt.tzinfo:
        dt = dt.replace(tzinfo=None)
    diff = now - dt
    
    seconds = diff.total_seconds()
    if seconds < 10: return "just now"
    if seconds < 60: return f"{int(seconds)} seconds ago"
    minutes = seconds / 60
    if minutes < 60: return f"{int(minutes)} minute{'s' if int(minutes) > 1 else ''} ago"
    hours = minutes / 60
    if hours < 24: return f"{int(hours)} hour{'s' if int(hours) > 1 else ''} ago"
    days = hours / 24
    if days < 7: return f"{int(days)} day{'s' if int(days) > 1 else ''} ago"
    weeks = days / 7
    if weeks < 4.345: return f"{int(weeks)} week{'s' if int(weeks) > 1 else ''} ago"
    months = days / 30.437
    if months < 12: return f"{int(months)} month{'s' if int(months) > 1 else ''} ago"
    years = days / 365.25
    return f"{int(years)} year{'s' if int(years) > 1 else ''} ago"

def approximate_token_count(text: str) -> int:
    """Naive approach: estimate tokens by dividing character count by 4."""
    return len(text) // config.APPROX_CHARS_PER_TOKEN

def trim_history_if_needed():
    """Trims the global conversation_history if it exceeds the token limit."""
    debug_print("*** Debug: trim_history_if_needed called.")
    while True:
        text = "\n".join(h["content"] for h in conversation_history)
        token_estimate = approximate_token_count(text)
        debug_print(f"*** Debug: Current token estimate={token_estimate}, MAX_TOKENS={config.MAX_TOKENS}")

        if token_estimate <= config.MAX_TOKENS:
            break
        removed = conversation_history.pop(0)
        debug_print(f"*** Debug: Removed old entry to reduce token count: {removed}")

def nltk_data_check():
    """Ensures the required NLTK data models for tokenization are available."""
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        print(">>> First-time setup: Downloading NLTK models ('punkt', 'punkt_tab')...")
        nltk.download('punkt')
        nltk.download('punkt_tab')
        print(">>> Download complete.")

def estimate_tokens(megaprompt: str) -> int:
    """
    Estimates token count for a megaprompt using word-based calculation.
    More accurate than character-based estimation for performance monitoring.
    
    Args:
        megaprompt: The complete prompt text to estimate tokens for
        
    Returns:
        Estimated number of tokens (int)
    """
    if not megaprompt:
        return 0
    
    # Word-based estimation: ~1.3 tokens per word for English text
    word_count = len(megaprompt.split())
    estimated_tokens = int(word_count * 1.3)
    
    debug_print(f"*** Debug: Token estimation - Words: {word_count}, Estimated tokens: {estimated_tokens}")
    return estimated_tokens

def repair_json(json_str: str) -> str:
    """
    Attempts to repair common JSON formatting issues.
    Returns repaired JSON string or None if repair fails.
    """
    try:
        # Common issue: missing closing braces
        # Count opening and closing braces to see if we need to add some
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        
        if open_braces > close_braces:
            # Add missing closing braces
            missing_braces = open_braces - close_braces
            repaired = json_str + ('}' * missing_braces)
            debug_print(f"*** Debug: Added {missing_braces} closing braces to repair JSON")
            return repaired
        
        # Could add more repair logic here for other common issues
        return None
    except Exception:
        return None 