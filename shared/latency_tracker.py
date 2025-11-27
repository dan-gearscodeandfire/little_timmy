"""
Shared latency tracking utility for Little Timmy services.
Logs timing events to a centralized log file for end-to-end latency analysis.
"""

import time
import json
from pathlib import Path
from datetime import datetime
import uuid
import threading

# Centralized log file path
LOG_FILE = Path(__file__).parent / "latency.log"
_log_lock = threading.Lock()

def generate_request_id():
    """Generate a unique request ID for tracking through the pipeline."""
    return str(uuid.uuid4())[:8]  # Short UUID for readability

def log_timing(request_id, service, event, metadata=None):
    """
    Log a timing event to the centralized latency log.
    
    Args:
        request_id: Unique identifier for this request
        service: Service name (stt, v34, tts)
        event: Event name (received, classification_start, ollama_sent, etc.)
        metadata: Optional dict with additional context
    """
    timestamp = time.time()
    iso_time = datetime.now().isoformat()
    
    log_entry = {
        "timestamp": timestamp,
        "iso_time": iso_time,
        "request_id": request_id,
        "service": service,
        "event": event,
        "metadata": metadata or {}
    }
    
    try:
        with _log_lock:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        # Fail silently - don't break service if logging fails
        print(f"[LATENCY] Warning: Could not write to latency log: {e}")

# Event name constants for consistency
class Events:
    # STT events
    STT_TRANSCRIPT_FINALIZED = "stt_transcript_finalized"
    STT_SENDING_TO_V34 = "stt_sending_to_v34"
    
    # v34 events
    V34_WEBHOOK_RECEIVED = "v34_webhook_received"
    V34_CLASSIFICATION_START = "v34_classification_start"
    V34_CLASSIFICATION_COMPLETE = "v34_classification_complete"
    V34_RETRIEVAL_START = "v34_retrieval_start"
    V34_RETRIEVAL_COMPLETE = "v34_retrieval_complete"
    V34_PROMPT_BUILT = "v34_prompt_built"
    V34_OLLAMA_SENT = "v34_ollama_sent"
    V34_OLLAMA_RECEIVED = "v34_ollama_received"
    V34_SENDING_TO_TTS = "v34_sending_to_tts"
    
    # TTS events
    TTS_REQUEST_RECEIVED = "tts_request_received"
    TTS_PAUSE_SENT = "tts_pause_sent"
    TTS_SYNTHESIS_START = "tts_synthesis_start"
    TTS_AUDIO_PLAYBACK_START = "tts_audio_playback_start"
    TTS_AUDIO_PLAYBACK_COMPLETE = "tts_audio_playback_complete"
    TTS_RESUME_SENT = "tts_resume_sent"

def format_duration(seconds):
    """Format duration in seconds to human-readable string."""
    if seconds < 0.001:
        return f"{seconds * 1000000:.0f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    else:
        return f"{seconds:.2f}s"

