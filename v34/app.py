# v34/app.py
# relaized model was reloading because of different values for context between the generate metadata and main call
# GLI classifier installed in venv and working on it's own, now tyrying to replace generate_metadata with fast_generate_metadata

import argparse
import atexit
import uuid
import json
import requests
import time
import eventlet
import threading
import sys
from pathlib import Path
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from sentence_transformers import SentenceTransformer
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

# Local module imports
import config
import utils
import llm
import memory
import vision_state
import fine_tuning_capture

# Add shared directory to path for latency tracking
shared_dir = Path(__file__).parent.parent / "shared"
if str(shared_dir) not in sys.path:
    sys.path.append(str(shared_dir))

try:
    from latency_tracker import log_timing, Events
    LATENCY_TRACKING_ENABLED = True
except ImportError:
    LATENCY_TRACKING_ENABLED = False
    utils.debug_print("[WARNING] Latency tracking not available")

# Global HTTP session with connection pooling for low-latency requests
# Reuses TCP connections for TTS requests and external API calls
http_session = requests.Session()
http_session.mount('http://', requests.adapters.HTTPAdapter(
    pool_connections=10,
    pool_maxsize=10,
    max_retries=0,
    pool_block=False
))
http_session.mount('https://', requests.adapters.HTTPAdapter(
    pool_connections=10,
    pool_maxsize=10,
    max_retries=0,
    pool_block=False
))

# --- Flask and SocketIO Setup ---
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
SESSION_ID = str(uuid.uuid4())
# Maintain per-session KV contexts for Ollama generate() caching
# Used to preserve conversation state across turns by passing context arrays
SESSION_CONTEXTS: dict[str, list[int]] = {}
# Track whether we've completed the first full-turn for this session so we can send only the tail thereafter
SESSION_TAIL_MODE: dict[str, bool] = {}
KV_STATS = deque(maxlen=200)

# Last received image analysis payload and extracted summary fields
LAST_IMAGE_ANALYSIS_RAW: dict | None = None
LAST_IMAGE_ANALYSIS: dict | None = None

# Acceptable HTTP status codes indicating a service is responding
ACCEPTABLE_STATUS_CODES = {200, 301, 302, 401, 403, 404, 405}

def _probe_service(name: str, url: str, timeout: float = 2.0) -> dict:
    """Probe a service URL and return status info. Considers a range of HTTP codes as alive.

    Returns dict: {name, url, ok, status, latency_ms, error}
    """
    proxies = {'http': None, 'https': None}
    start = time.time()
    try:
        # Prefer HEAD; many services may return 405 which we still accept
        verify_ssl = not url.lower().startswith("https") and True or False
        # Use session for connection pooling
        resp = http_session.request("HEAD", url, timeout=timeout, allow_redirects=False, proxies=proxies, verify=verify_ssl)
        latency_ms = int((time.time() - start) * 1000)
        ok = resp.status_code in ACCEPTABLE_STATUS_CODES
        return {"name": name, "url": url, "ok": ok, "status": resp.status_code, "latency_ms": latency_ms, "error": None}
    except requests.exceptions.RequestException as e:
        latency_ms = int((time.time() - start) * 1000)
        return {"name": name, "url": url, "ok": False, "status": None, "latency_ms": latency_ms, "error": str(e)}

def _run_health_checks_once():
    """Run one round of health checks in parallel and log results."""
    utils.debug_print("*** Health: starting round")
    # Normalize motor URL to HTTPS (motor-raspi uses HTTPS)
    motor_url = getattr(config, "MOTOR_API_URL", "https://motor-raspi:8080/")
    if motor_url.lower().startswith("http://"):
        try:
            motor_url = "https://" + motor_url.split("://", 1)[1]
        except Exception:
            motor_url = "https://motor-raspi:8080/"

    services = [
        {"name": "ollama", "url": config.OLLAMA_API_URL},
        {"name": "tts", "url": getattr(config, "TTS_API_URL", "http://localhost:5051/")},
        {"name": "stt", "url": getattr(config, "STT_API_URL", "http://localhost:8888/")},
        {"name": "caption", "url": "http://localhost:8000/"},
        {"name": "motor", "url": motor_url},
    ]

    results = []
    with ThreadPoolExecutor(max_workers=len(services)) as executor:
        future_map = {executor.submit(_probe_service, s["name"], s["url"]): s for s in services}
        for fut in as_completed(future_map):
            results.append(fut.result())

    # Log results
    for r in results:
        if r["ok"]:
            utils.debug_print(f"*** Health: {r['name']} OK status={r['status']} latency={r['latency_ms']}ms url={r['url']}")
        else:
            utils.debug_print(f"*** Health: {r['name']} DOWN latency={r['latency_ms']}ms url={r['url']} error={r['error']}")
    utils.debug_print("*** Health: round complete")

def _health_check_loop():
    """Background loop: run once at startup and every 60 seconds thereafter."""
    try:
        utils.debug_print("*** Health: loop initializing")
        _run_health_checks_once()
        while True:
            # Use plain sleep to avoid async/patched quirks
            time.sleep(60)
            _run_health_checks_once()
    except Exception as e:
        utils.debug_print(f"*** Health loop stopped due to error: {e}")

# --- Application Initialization ---
utils.nltk_data_check()
memory.init_db_pool()
atexit.register(memory.close_db_pool)
# Set current session for vision manager so prompt builders can fetch observations
try:
    vision_state.set_current_session(SESSION_ID)
except Exception:
    pass

# --- Application Logic ---
embed_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device='cuda')



def is_important_user_message(msg: str) -> tuple[bool, dict]:
    """Determines if a user message is important enough to embed."""
    metadata = llm.fast_generate_metadata(msg)
    should_embed = metadata.get("importance", 0) >= 2
    return should_embed, metadata

def process_user_message(user_input: str, request_id=None):
    """
    Core logic to process a user's message, generate a response, and interact with memory.
    """
    start_time = time.time()
    utils.debug_print(f"*** Debug: Processing user message: {user_input} [request_id={request_id}]")

    # 1. Check if this is praise for the previous response (fine-tuning capture)
    if fine_tuning_capture.is_praise(user_input) and len(utils.conversation_history) >= 2:
        try:
            context = fine_tuning_capture.get_conversation_context(utils.conversation_history)
            if context and context["user_n3"] and context["assistant_n1"]:
                # Capture the excellent example (system prompt will be added during next generation)
                utils.debug_print(f"*** Fine-tuning: Praise detected, will capture previous exchange")
                # Store context for capture after we build the prompt
                SESSION_CONTEXTS["_pending_ft_capture"] = {
                    "user_n3": context["user_n3"],
                    "assistant_n1": context["assistant_n1"],
                    "praise_n0": user_input
                }
        except Exception as e:
            utils.debug_print(f"*** Fine-tuning capture error: {e}")
    
    # 2. Metadata generation
    t1 = time.time()
    if LATENCY_TRACKING_ENABLED and request_id:
        log_timing(request_id, "v34", Events.V34_CLASSIFICATION_START)
    
    should_embed_user, user_metadata = is_important_user_message(user_input)
    
    if LATENCY_TRACKING_ENABLED and request_id:
        log_timing(request_id, "v34", Events.V34_CLASSIFICATION_COMPLETE, 
                 {"importance": user_metadata.get("importance")})
    
    utils.debug_print(f"--- Step 1 (Metadata Generation) took: {time.time() - t1:.2f}s")
    
    # 3. Add user message to conversation history
    utils.conversation_history.append({"role": "user", "content": user_input})
    utils.trim_history_if_needed()
    
    # 3. Memory operations
    t2 = time.time()
    # Always store user message importance> threshold, independent of retrieval toggle
    if should_embed_user:
        memory.chunk_and_store_text(user_input, role="user", metadata=user_metadata, session_id=SESSION_ID)
    utils.debug_print(f"--- Step 3 (Memory Storage) took: {time.time() - t2:.2f}s")
    
    # 4. Context retrieval (can be disabled for KV/session-only testing)
    t3 = time.time()
    if LATENCY_TRACKING_ENABLED and request_id:
        log_timing(request_id, "v34", Events.V34_RETRIEVAL_START)
    
    relevant_chunks = []
    context_text = ""
    if getattr(config, "RETRIEVAL_ENABLED", True):
        relevant_chunks = memory.retrieve_unique_relevant_chunks(user_input)
        try:
            utils.debug_print(f"*** Debug: Retrieved {len(relevant_chunks)} memory chunks for context")
        except Exception:
            pass
        # Sort chunks by importance (descending) so most important context comes first
        sorted_chunks = sorted(relevant_chunks, key=lambda c: c.get('importance', 0), reverse=True)
        
        # Format with metadata for better LLM understanding
        context_strings = []
        for chunk in sorted_chunks:
            if not chunk.get("timestamp"):
                continue
            
            # Build metadata prefix
            topic = chunk.get('topic', 'misc').replace('_', ' ').title()
            importance = chunk.get('importance', 0)
            
            # Format: [Topic, Importance: N] Role (time ago) - text
            metadata_prefix = f"[{topic}, Importance: {importance}]"
            time_str = utils.time_ago(chunk['timestamp'])
            role_str = chunk['role'].title()
            
            context_strings.append(
                f"{metadata_prefix} {role_str} ({time_str}) - {chunk['text']}"
            )
        
        context_text = "\n".join(context_strings)
    else:
        utils.debug_print("*** Debug: Retrieval disabled by config.RETRIEVAL_ENABLED=False (KV/session-only mode)")
    
    if LATENCY_TRACKING_ENABLED and request_id:
        log_timing(request_id, "v34", Events.V34_RETRIEVAL_COMPLETE, 
                 {"num_chunks": len(relevant_chunks)})
    
    utils.debug_print(f"--- Step 4 (Context Retrieval) took: {time.time() - t3:.2f}s")
    
    # 5. Main LLM call - MEGAPROMPT STRATEGY WITH KV CONTEXT
    t4 = time.time()
    
    # Build prompts
    # Note: conversation_history excludes the current user message (it was just added)
    history_without_current = utils.conversation_history[:-1]
    full_megaprompt_for_estimate = llm.build_megaprompt(history_without_current, user_input, relevant_chunks)

    # Path A: Always send full megaprompt each turn (revert to classic megaprompt strategy)
    if getattr(config, "USE_FULL_MEGA_PROMPT", True):  # Fixed: default should be True to match config
        prompt_to_send = full_megaprompt_for_estimate
        tail_mode_enabled = False
    else:
        # Path B: Baseline once, then ephemeral tail with KV context chaining
        tail_mode_enabled = SESSION_TAIL_MODE.get(SESSION_ID, False)
        if not tail_mode_enabled:
            prompt_to_send = llm.build_baseline_prompt(user_input)
        else:
            # Build a short session recap from the last user+assistant turn to stabilize same-session recall
            recap = ""
            try:
                if len(utils.conversation_history) >= 2:
                    last_user = next((e for e in reversed(utils.conversation_history) if e["role"] == "user"), None)
                    last_ai = next((e for e in reversed(utils.conversation_history) if e["role"] == "assistant"), None)
                    if last_user:
                        recap += f"User: {last_user['content']}\n"
                    if last_ai:
                        recap += f"Assistant: {last_ai['content']}\n"
            except Exception:
                recap = ""

            prompt_to_send = llm.build_tail_prompt(user_message=user_input, retrieved_memories=relevant_chunks, session_recap=recap)
            try:
                tail_chars = len(prompt_to_send)
                tail_tokens = utils.estimate_tokens(prompt_to_send)
                utils.debug_print(f"*** Debug: Tail prompt size: {tail_chars} chars, ~{tail_tokens} tokens (estimate)")
            except Exception:
                pass
    
    if LATENCY_TRACKING_ENABLED and request_id:
        # Calculate estimated tokens for prompt
        estimated_tokens = len(prompt_to_send) // 4  # Rough estimate
        log_timing(request_id, "v34", Events.V34_PROMPT_BUILT, 
                 {"prompt_chars": len(prompt_to_send), 
                  "prompt_tokens_est": estimated_tokens,
                  "tail_mode": tail_mode_enabled})
    
    # Save the actual prompt sent for debugging
    with open("payloads.txt", "a", encoding="utf-8") as f:
        f.write(f"=== Megaprompt at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        f.write(prompt_to_send)
        f.write("\n\n")
    
    # If we have a pending fine-tuning capture, save it now (we have the system prompt)
    if "_pending_ft_capture" in SESSION_CONTEXTS:
        try:
            ft_data = SESSION_CONTEXTS.pop("_pending_ft_capture")
            fine_tuning_capture.capture_fine_tuning_example(
                user_message_n3=ft_data["user_n3"],
                system_prompt_n2=prompt_to_send,  # Current prompt (has memories from previous turn)
                assistant_response_n1=ft_data["assistant_n1"],
                praise_message_n0=ft_data["praise_n0"],
                metadata={
                    "session_id": SESSION_ID,
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                }
            )
            utils.debug_print(f"*** Fine-tuning: Captured excellent example to fine_tuning_best_case_interchanges.md")
        except Exception as e:
            utils.debug_print(f"*** Fine-tuning capture save error: {e}")
    
    # Call generate endpoint; USE returned context to preserve conversation across turns
    utils.debug_print(f"*** Debug: Tail mode active={tail_mode_enabled}")
    prev_ctx = SESSION_CONTEXTS.get(SESSION_ID)
    if prev_ctx is not None:
        try:
            utils.debug_print(f"*** Debug: Existing context length: {len(prev_ctx)}")
        except Exception:
            utils.debug_print(f"*** Debug: Existing context present (length unknown)")
    
    # Visual turns: lower temperature; reuse base for others
    temperature = 0.1 if llm.is_visual_question(user_input) else 0.4
    
    if LATENCY_TRACKING_ENABLED and request_id:
        context_len = len(prev_ctx) if prev_ctx else 0
        log_timing(request_id, "v34", Events.V34_OLLAMA_SENT, 
                 {"temperature": temperature, 
                  "kv_context_length": context_len,
                  "has_kv_cache": context_len > 0})
    
    ai_response_text, new_ctx, stats = llm.generate_api_call(prompt_to_send, context=prev_ctx, raw=True, temperature=temperature)
    
    if LATENCY_TRACKING_ENABLED and request_id:
        # Include Ollama stats for correlation analysis
        ollama_metadata = {
            "response_length": len(ai_response_text) if isinstance(ai_response_text, str) else 0,
            "new_context_length": len(new_ctx) if new_ctx else 0
        }
        if stats:
            ollama_metadata.update({
                "prompt_eval_count": stats.get('prompt_eval_count', 0),
                "eval_count": stats.get('eval_count', 0),
                "prompt_eval_duration_ms": stats.get('prompt_eval_duration', 0) / 1_000_000,
                "eval_duration_ms": stats.get('eval_duration', 0) / 1_000_000,
            })
        log_timing(request_id, "v34", Events.V34_OLLAMA_RECEIVED, ollama_metadata)
    # Only mark tail mode for the baseline/tail strategy
    if not getattr(config, "USE_FULL_MEGA_PROMPT", True):  # Fixed: default should be True
        SESSION_TAIL_MODE[SESSION_ID] = True
    # Preserve returned context for next turn KV reuse
    if new_ctx is not None:
        SESSION_CONTEXTS[SESSION_ID] = new_ctx
        try:
            utils.debug_print(f"*** Debug: Stored new context length: {len(new_ctx)}")
        except Exception:
            utils.debug_print(f"*** Debug: Stored new context (length unknown)")
    
    # Estimate tokens used and emit to web UI
    # Keep UI estimate accurate by using the logical full prompt length
    estimated_tokens_display = utils.estimate_tokens(full_megaprompt_for_estimate)
    socketio.emit('token_count', {'tokens': estimated_tokens_display})
    utils.debug_print(f"*** Debug: Megaprompt (logical) used ~{estimated_tokens_display} tokens")
    # Optional: print KV-related timing for visibility
    if stats:
        utils.debug_print(f"*** Debug: KV stats: prompt_eval_count={stats.get('prompt_eval_count')} eval_count={stats.get('eval_count')}")
        utils.debug_print(f"*** Debug: Durations (ns): load={stats.get('load_duration')} prompt_eval={stats.get('prompt_eval_duration')} eval={stats.get('eval_duration')} total={stats.get('total_duration')}")
        # Save to rolling buffer for /api/kv_stats
        KV_STATS.append({
            "timestamp": time.time(),
            "session_id": SESSION_ID,
            "tail_mode": tail_mode_enabled,
            "prompt_eval_count": stats.get('prompt_eval_count'),
            "prompt_eval_duration": stats.get('prompt_eval_duration'),
            "eval_count": stats.get('eval_count'),
            "eval_duration": stats.get('eval_duration'),
            "total_duration": stats.get('total_duration'),
            "load_duration": stats.get('load_duration'),
        })

        # Emit KV stats to the web UI as a socket event (durations converted to ms)
        try:
            to_ms = lambda ns: int((ns or 0) / 1_000_000)
            socketio.emit('kv_stats', {
                'tail_mode': tail_mode_enabled,
                'prompt_eval_count': stats.get('prompt_eval_count'),
                'eval_count': stats.get('eval_count'),
                'total_duration_ms': to_ms(stats.get('total_duration')),
                'prompt_eval_duration_ms': to_ms(stats.get('prompt_eval_duration')),
                'eval_duration_ms': to_ms(stats.get('eval_duration')),
                'load_duration_ms': to_ms(stats.get('load_duration')),
            })
        except Exception:
            pass
    
    # Generate simple metadata for responses
    response_length = len(ai_response_text.split())
    ai_metadata = {
        "importance": 1 if response_length > 10 else 0,
        "topic": "conversation", 
        "tags": ["megaprompt", "generate"]
    }
    
    utils.debug_print(f"--- Step 5 (Megaprompt LLM Call) took: {time.time() - t4:.2f}s")
    
    if isinstance(ai_response_text, dict):
        utils.debug_print(f"*** WARNING: AI response 'content' was a dict, not a string: {ai_response_text}")
        ai_response_text = json.dumps(ai_response_text, indent=2)

    utils.debug_print(f"*** Debug: LLM response received: {ai_response_text}")

    # 6. Add assistant's response to history (but DO NOT store in vector memory)
    utils.conversation_history.append({"role": "assistant", "content": ai_response_text})
    
    # DISABLED: Do not store assistant responses - they can contain hallucinations
    # Only user messages are ground truth and should be stored
    utils.debug_print(f"*** Debug: Assistant response added to conversation history only (not stored in vector memory)")

    utils.debug_print(f"--- Total process_user_message took: {time.time() - start_time:.2f}s")
    return ai_response_text

@socketio.on("user_message")
def handle_user_message(data):
    """Handler for incoming user messages from the web UI."""
    try:
        utils.debug_print("*********************************************BEGIN*********************************************")
        user_input = data["message"]
        utils.debug_print(f"*** Debug: Received user_message via WebSocket: {user_input}")
        
        ai_response_text = process_user_message(user_input)

        emit("bot_message", {"message": ai_response_text})
        
        try:
            proxies = {'http': None, 'https': None}
            # Use session for connection pooling (reduces latency)
            eventlet.tpool.execute(http_session.get, config.TTS_API_URL, params={"text": ai_response_text}, timeout=2, proxies=proxies)
        except requests.exceptions.RequestException as e:
            utils.debug_print(f"*** Debug: Could not connect to TTS API: {e}")
            
    except Exception as e:
        utils.debug_print(f"*** Debug: Error in handle_user_message: {e}")
        emit("bot_message", {"message": "Sorry, I encountered an error processing your message."})

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/tests")
def memory_tests_page():
    """Render the memory tests interface."""
    return render_template("memory_tests.html")

@app.route("/api/webhook", methods=['POST'])
def handle_webhook():
    # Log immediately upon entry to Flask handler
    entry_time = time.time()
    
    data = request.json
    if not data or "text" not in data:
        return {"error": "Invalid payload. 'text' field is required."}, 400
    
    user_input = data["text"]
    request_id = data.get("request_id")  # Get request_id from STT if provided
    
    # Log as soon as we have request_id
    if LATENCY_TRACKING_ENABLED and request_id:
        log_timing(request_id, "v34", "v34_flask_handler_entry", {})
    
    if LATENCY_TRACKING_ENABLED and request_id:
        log_timing(request_id, "v34", Events.V34_WEBHOOK_RECEIVED, 
                 {"text_length": len(user_input), "session_id": SESSION_ID})
    
    utils.debug_print("*********************************************BEGIN*********************************************")
    utils.debug_print(f"*** Debug: Received user_message via webhook: {user_input} [request_id={request_id}]")

    socketio.emit("display_user_message", {"message": user_input})
    ai_response = process_user_message(user_input, request_id)
    socketio.emit("bot_message", {"message": ai_response})
    
    if LATENCY_TRACKING_ENABLED and request_id:
        log_timing(request_id, "v34", Events.V34_SENDING_TO_TTS, 
                 {"response_length": len(ai_response)})
    
    try:
        proxies = {'http': None, 'https': None}
        tts_params = {"text": ai_response}
        if request_id:
            tts_params["request_id"] = request_id
        # Use session for connection pooling (reduces latency)
        eventlet.tpool.execute(http_session.get, config.TTS_API_URL, params=tts_params, timeout=2, proxies=proxies)
    except requests.exceptions.RequestException as e:
        utils.debug_print(f"*** Debug: Could not connect to TTS API: {e}")
        
    return {"status": "success", "response": ai_response}, 200

@app.route("/api/retrieve_inspect")
def retrieve_inspect():
    """Return the same set of chunks the LLM sees for a given query string."""
    query = request.args.get("q", "")
    if not query:
        # Match other API style by returning a 400 on bad request.
        return {"error": "Missing query string ?q="}, 400

    # Use the newer Parent-Document retrieval path so the inspector shows
    # exactly the chunks supplied to the chat endpoint.
    # Convert datetime objects to ISO strings for JSON serialization
    raw_results = memory.retrieve_unique_relevant_chunks(query)

    import decimal, numpy as np

    def _to_serializable(val):
        """Convert non-JSON-serializable objects (datetime, Decimal, numpy types) to JSONable forms."""
        if hasattr(val, "isoformat"):
            return val.isoformat()
        if isinstance(val, decimal.Decimal):
            return float(val)
        if isinstance(val, (np.floating,)):
            return float(val)
        return val

    for r in raw_results:
        for k, v in list(r.items()):
            r[k] = _to_serializable(v)

    return {"query": query, "results": raw_results}

@app.route("/api/memory")
def get_recent_memory():
    """Returns the most recent memory chunks for the current session."""
    return {
        "session_id": SESSION_ID,
        "chunks": memory.get_recent_memories(SESSION_ID)
    }

@app.route("/api/kv_stats")
def get_kv_stats():
    """Return recent KV timing/counter stats for debugging.

    Query params:
    - limit: max number of most recent entries to return (default 20)
    """
    try:
        limit = int(request.args.get("limit", 20))
        if limit <= 0:
            limit = 20
    except Exception:
        limit = 20

    items = list(KV_STATS)[-limit:]
    return {
        "count": len(items),
        "stats": items
    }

@app.route("/api/memory/test", methods=['GET', 'POST'])
def run_memory_tests():
    """Run comprehensive memory system tests and return results."""
    try:
        # Import here to avoid loading unless needed
        from memory_test_suite import run_memory_tests as run_tests
        
        # Check if cleanup should be performed
        cleanup = request.args.get('cleanup', 'true').lower() == 'true'
        
        utils.debug_print(f"*** Running memory test suite (cleanup={cleanup})...")
        results = run_tests(cleanup_after=cleanup)
        
        return results, 200
    except Exception as e:
        utils.debug_print(f"*** Memory test suite error: {e}")
        return {"error": f"Test suite failed: {e}", "status": "FAILED"}, 500

@app.route("/api/memory/cleanup", methods=['POST'])
def cleanup_old_memories():
    """Clean up old memory entries with wrong tags that pollute retrieval."""
    try:
        # Delete entries from before the classification improvements
        cutoff_time = "2025-07-28 16:30:00"  # Before the new classification system
        
        deleted_chunks, deleted_parents = memory.prune_test_memories()
        
        # Also remove old entries with wrong tag combinations
        conn = None
        old_deleted = 0
        try:
            conn = memory.db_pool.getconn()
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM memory_chunks 
                    WHERE timestamp < %s 
                    AND (
                        ('projects' = ANY(tags) AND 'technical details' = ANY(tags)) 
                        OR ('meta' = ANY(tags) AND 'humor' = ANY(tags))
                    );
                """, (cutoff_time,))
                old_deleted = cur.rowcount
            conn.commit()
        finally:
            if conn:
                memory.db_pool.putconn(conn)
        
        return {
            "status": "success",
            "test_chunks_deleted": deleted_chunks,
            "parent_docs_deleted": deleted_parents,
            "old_chunks_deleted": old_deleted,
            "total_deleted": deleted_chunks + old_deleted
        }, 200
    except Exception as e:
        utils.debug_print(f"*** Debug: Memory cleanup error: {e}")
        return {"error": f"Memory cleanup failed: {e}"}, 500

# --- Image Analysis Receiver ---

@app.route("/receive-image-analysis", methods=['POST'])
def receive_image_analysis():
    """Receive captioned image analysis JSON and store key fields in memory.

    Expected JSON fields (others are stored raw):
    - caption: str
    - faces_detected: int (optional; if missing, derived from len(faces))
    - faces: list of objects with optional fields name (str) and is_known (bool)
    """
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return {"error": "Invalid JSON payload"}, 400

    # Size/field validation
    if len(json.dumps(data)) > getattr(config, "VISION_MAX_PAYLOAD_BYTES", 32_768):
        return {"error": "Payload too large"}, 413

    caption = data.get("caption") or ""
    if not isinstance(caption, str):
        caption = str(caption)
    # Clamp caption length to prevent prompt bloat
    max_caption_chars = getattr(config, "VISION_MAX_CAPTION_CHARS", 300)
    if len(caption) > max_caption_chars:
        caption = caption[:max_caption_chars]
    faces_list = data.get("faces") or []
    if not isinstance(faces_list, list):
        faces_list = []
    max_faces = getattr(config, "VISION_MAX_FACES", 10)
    if len(faces_list) > max_faces:
        faces_list = faces_list[:max_faces]

    # Determine number of faces detected
    faces_detected_field = data.get("faces_detected")
    if isinstance(faces_detected_field, int):
        number_faces_detected = faces_detected_field
    else:
        try:
            number_faces_detected = int(len(faces_list))
        except Exception:
            number_faces_detected = 0

    # Extract recognized people names (is_known == True)
    names_seen = set()
    people_detected = []
    if isinstance(faces_list, list):
        for face in faces_list:
            if not isinstance(face, dict):
                continue
            name = face.get("name")
            is_known = face.get("is_known")
            if isinstance(name, str) and name.strip() and is_known is True:
                if name not in names_seen:
                    names_seen.add(name)
                    people_detected.append(name)

    # Persist last received data in-memory
    global LAST_IMAGE_ANALYSIS_RAW, LAST_IMAGE_ANALYSIS
    LAST_IMAGE_ANALYSIS_RAW = data
    LAST_IMAGE_ANALYSIS = {
        "caption": caption,
        "number_faces_detected": number_faces_detected,
        "people_detected": people_detected,
    }

    utils.debug_print(f"*** Image analysis received: caption='{caption[:120]}' faces={number_faces_detected} known={people_detected}")

    # Update smoothed VisionState for current session
    try:
        vision_state.get_manager().update_for_session(SESSION_ID, {
            **data,
            "caption": caption,
            "faces": faces_list,
        })
    except Exception as e:
        utils.debug_print(f"*** VisionState update error: {e}")

    return {"status": "success", "stored": LAST_IMAGE_ANALYSIS}, 200

# --- Main Execution ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug mode.")
    args = parser.parse_args()
    config.DEBUG_MODE = args.debug

    utils.debug_print("Debug mode is ON! Starting development server.")
    # Start non-blocking background health checks
    try:
        threading.Thread(target=_health_check_loop, daemon=True).start()
        utils.debug_print("*** Health: background health-check thread started (threading)")
    except Exception as e:
        utils.debug_print(f"*** Health: failed to start health-check thread: {e}")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True) 