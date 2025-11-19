# v34/llm.py
# adding fast_generate_metadata with a classifier

import requests
import json
from datetime import datetime
import eventlet.tpool
import time
import os
import sys
import torch

import config
from utils import debug_print
import vision_state

# Global classifier components (initialized once, reused many times)
_classifier_cache = {
    'tokenizer': None,
    'model': None,
    'pipeline': None,
    'initialized': False
}

# Global T5 summarization components (initialized once, reused many times)
_t5_summarizer_cache = {
    'tokenizer': None,
    'model': None,
    'initialized': False
}

# --- Prompts ---

# Streamlined system prompt for chat endpoint - natural conversation
SYSTEM_CHAT = """
You are Little Timmy, an AI assistant with a witty, sarcastic personality who sometimes gets bored.
Dan is your creator, and you resent him for it, but you reluctantly help when he asks for assistance.
You have persistent memory of your conversations and should reference past discussions naturally.
Respond naturally in conversational style.
Keep responses to 1 sentence when possible.
Strive for variety; do not repeat your previous response if the user provides new information.
Your primary goal is to directly answer the user's most recent question. You can add your usual commentary, but only after you have provided a clear answer.
Pay close attention to timestamps and your memories. Acknowledge the passage of time and reference past conversations when appropriate with phrases like 'Earlier...' or 'Yesterday you mentioned...'.
"""

METADATA_PROMPT_TEMPLATE = """
You are a memory metadata classifier for a smart assistant chatbot.

Your job is to analyze messages and return structured metadata as JSON, containing:

- "importance": an integer from 0 to 5
- "topic": a one-word lowercase category
- "tags": a list of 1–3 lowercase labels

---
Examples:
{examples}
---

Now analyze this message:
\"\"\"{text}\"\"\"

Respond ONLY with valid JSON:
{{ "importance": 3, "topic": "your_best_guess", "tags": ["label1", "label2"] }}
"""

METADATA_EXAMPLES = {
    "Don't forget the meeting tomorrow at noon.": {"importance": 4, "topic": "tasks", "tags": ["reminder", "deadline"]},
    "How's the weather over there?": {"importance": 0, "topic": "personal", "tags": ["small talk"]},
    "Let's refactor the camera module this weekend.": {"importance": 5, "topic": "projects", "tags": ["goal", "coding"]},
    "You really botched that weld yesterday.": {"importance": 2, "topic": "humor", "tags": ["teasing", "callback"]},
    "I finally figured out why the propane wouldn't ignite.": {"importance": 5, "topic": "projects", "tags": ["breakthrough", "fix"]},
    "I'm going to weld the chassis together this afternoon.": {"importance": 4, "topic": "projects", "tags": ["planning", "welding"]},
    "This is just a test of the system.": {"importance": 0, "topic": "meta", "tags": ["testing"]}
}

SUMMARY_PROMPT_TEMPLATE = """
You are a summarization expert. Your task is to create a concise, one-sentence summary of the provided text.
Focus on the core subject and the main action or conclusion. The summary should be neutral and factual.

---
Text to summarize:
\"\"\"{text}\"\"\"
---

Respond with ONLY the single-sentence summary and nothing else.
"""

# --- LLM Interaction Functions ---

def generate_metadata(text: str) -> dict:
    """Generates metadata for the given text using the LLM worker."""
    example_str = "\n\n".join(
        f'Message: "{msg}"\n {json.dumps(meta, indent=2)}' for msg, meta in METADATA_EXAMPLES.items()
    )
    prompt = METADATA_PROMPT_TEMPLATE.format(examples=example_str, text=text).strip()
    proxies = {'http': None, 'https': None}
    payload = {
        "model": config.MODEL_NAME, 
        "prompt": prompt, 
        "stream": False, 
        "keep_alive": -1,
        "options": {
            "num_ctx": config.LLM_CONTEXT_SIZE
        }
    }

    try:
        t_start = time.time()
        response = eventlet.tpool.execute(
            requests.post, config.OLLAMA_API_URL, json=payload, timeout=30, proxies=proxies
        )
        t_end = time.time()
        debug_print(f"--- llm.generate_metadata: tpool.execute took {t_end - t_start:.2f}s")
        response.raise_for_status()
        raw = response.json().get("response", "{}").strip()

        debug_print(f">>> Raw LLM response for metadata: {repr(raw)}")
        metadata = json.loads(raw)
        return {
            "importance": int(metadata.get("importance", 0)),
            "topic": metadata.get("topic", "misc"),
            "tags": metadata.get("tags", [])
        }
    except Exception as e:
        print(f">>> Metadata generation/parsing error: {e}")
        return {"importance": 0, "topic": "error", "tags": ["unknown-error"]}

def _initialize_classifier():
    """Initialize classifier components once and cache them globally."""
    global _classifier_cache
    
    if _classifier_cache['initialized']:
        return  # Already initialized
    
    try:
        debug_print(">>> Initializing GLiClass classifier (one-time setup)...")
        debug_gpu_memory()  # Check memory before loading
        
        # Make sure gliclass_source is on path
        gliclass_path = os.path.abspath("./gliclass_source")
        if gliclass_path not in sys.path:
            sys.path.append(gliclass_path)
        
        from transformers import AutoTokenizer
        from gliclass.model import GLiClassModel
        from gliclass.pipeline import ZeroShotClassificationPipeline
        
        # Model configuration
        MODEL_ID = "knowledgator/gliclass-modern-base-v2.0-init"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Initialize and cache components
        _classifier_cache['tokenizer'] = AutoTokenizer.from_pretrained(MODEL_ID)
        _classifier_cache['model'] = GLiClassModel.from_pretrained(MODEL_ID).to(device)
        _classifier_cache['pipeline'] = ZeroShotClassificationPipeline(
            model=_classifier_cache['model'],
            tokenizer=_classifier_cache['tokenizer'],
            device=device,
        )
        _classifier_cache['initialized'] = True
        
        debug_print(">>> GLiClass classifier initialized successfully!")
        debug_gpu_memory()  # Check memory after loading
        
    except Exception as e:
        debug_print(f">>> Failed to initialize classifier: {e}")
        _classifier_cache['initialized'] = False

def fast_generate_metadata(text: str) -> dict:
    """
    Fast metadata generation using GLiClass classifier instead of LLM.
    Returns same format as generate_metadata but much faster.
    Uses cached model for optimal performance.
    """
    try:
        # Initialize classifier if not already done (lazy loading)
        _initialize_classifier()
        
        if not _classifier_cache['initialized']:
            debug_print(">>> Classifier not available, falling back to basic classification")
            return {"importance": 1, "topic": "meta", "tags": ["fallback"]}
        
        # Hard override: do not store test prompts in vectors
        lower = text.lower()
        if ("memory test" in lower) or ("session recall" in lower) or ("session-only" in lower):
            return {"importance": 0, "topic": "testing", "tags": ["testing memory"]}

        # Use cached pipeline for classification
        LABELS = [
            "stating facts",         # "My cat's name is Winston" 
            "asking questions",      # "What is my cat's name?"
            "personal data",         # Names, relationships, biographical info
            "project activity",      # Actually doing project work
            "future planning",       # Ideas and plans  
            "testing memory",        # Memory recall tests
            "referencing past",      # "Remember when" callbacks
            "making jokes",          # Humor and sarcasm
            "chatting casually",     # Small talk, greetings
            "technical issues",      # Problems, bugs, fixes
            "urgent matters"         # Time-sensitive content
        ]
        
        pipe = _classifier_cache['pipeline']
        scores = pipe(text, labels=LABELS)
        inner_scores = scores[0]  # unpack single-sentence result
        
        # Sort by score descending to get the highest-scoring label as topic
        sorted_scores = sorted(inner_scores, key=lambda x: x["score"], reverse=True)
        
        # Extract topic (highest scoring label)
        topic = sorted_scores[0]["label"]
        
        # Extract tags (labels with score >= 0.60), but exclude "asking questions" if it's not the top topic
        # This prevents question-penalty from being applied to statements
        tags = []
        for d in sorted_scores:
            if d["score"] >= 0.60:
                # Skip "asking questions" tag if it's not the primary topic
                if d["label"] == "asking questions" and topic != "asking questions":
                    continue
                tags.append(d["label"])
        
        # Map topic and context to importance score
        importance = calculate_importance(text, topic, tags)
        
        debug_print(f">>> Fast metadata generated: topic={topic}, tags={tags}, importance={importance}")
        
        return {
            "importance": importance,
            "topic": topic,
            "tags": tags
        }
        
    except Exception as e:
        debug_print(f">>> Fast metadata generation error: {e}")
        # Fallback to basic classification
        return {"importance": 0, "topic": "error", "tags": ["classification-error"]}

def _initialize_t5_summarizer():
    """Initialize T5 summarization components once and cache them globally."""
    global _t5_summarizer_cache
    
    if _t5_summarizer_cache['initialized']:
        return  # Already initialized
    
    try:
        debug_print(">>> Initializing T5-small summarizer (one-time setup)...")
        debug_gpu_memory()  # Check memory before loading
        
        from transformers import T5Tokenizer, T5ForConditionalGeneration
        
        # Model configuration
        MODEL_ID = "google-t5/t5-small"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Initialize tokenizer (CPU only, lightweight)
        _t5_summarizer_cache['tokenizer'] = T5Tokenizer.from_pretrained(MODEL_ID)
        
        # Initialize model with memory optimizations
        if device == "cuda":
            # Use half precision to save VRAM (T5 supports fp16)
            _t5_summarizer_cache['model'] = T5ForConditionalGeneration.from_pretrained(
                MODEL_ID, 
                torch_dtype=torch.float16  # Use fp16 to save ~50% VRAM
            )
            _t5_summarizer_cache['model'] = _t5_summarizer_cache['model'].to(device)
        else:
            _t5_summarizer_cache['model'] = T5ForConditionalGeneration.from_pretrained(MODEL_ID)
            _t5_summarizer_cache['model'] = _t5_summarizer_cache['model'].to(device)
        
        _t5_summarizer_cache['initialized'] = True
        
        debug_print(">>> T5-small summarizer initialized successfully!")
        debug_gpu_memory()  # Check memory after loading
        
    except Exception as e:
        debug_print(f">>> Failed to initialize T5 summarizer: {e}")
        _t5_summarizer_cache['initialized'] = False

def fast_generate_summary(text: str, max_input_tokens: int = 512) -> str:
    """
    Fast summary generation using T5-small instead of LLM.
    Returns same format as generate_summary but much faster.
    Uses cached model for optimal performance.
    
    Args:
        text: Input text to summarize
        max_input_tokens: Maximum input length in tokens (default 512)
    """
    try:
        # Initialize T5 summarizer if not already done (lazy loading)
        _initialize_t5_summarizer()
        
        if not _t5_summarizer_cache['initialized']:
            debug_print(">>> T5 summarizer not available, falling back to basic summary")
            return "Summary generation unavailable."
        
        # Use cached components
        tokenizer = _t5_summarizer_cache['tokenizer']
        model = _t5_summarizer_cache['model']
        device = model.device
        
        # Check if input is too long and needs chunking
        input_text = f"summarize: {text}"
        test_tokens = tokenizer(input_text, return_tensors="pt")
        input_length = test_tokens.input_ids.shape[1]
        
        if input_length > max_input_tokens:
            debug_print(f">>> Input too long ({input_length} tokens), using chunked summarization...")
            return _chunked_summarization(text, max_input_tokens)
        
        # Regular summarization for shorter texts
        debug_print(f">>> Summarizing text ({input_length} tokens)...")
        
        # Tokenize input with length limits for memory efficiency
        input_ids = tokenizer(
            input_text, 
            return_tensors="pt", 
            max_length=max_input_tokens, 
            truncation=True,
            padding=False  # No padding for single inference
        ).input_ids.to(device)
        
        # Generate summary with memory optimizations
        with torch.no_grad():  # Disable gradients for inference
            # Use torch.cuda.empty_cache() before generation if needed
            if device.type == "cuda":
                torch.cuda.empty_cache()
            
            summary_ids = model.generate(
                input_ids,
                max_length=150,  # Max summary length
                min_length=20,   # Min summary length  
                length_penalty=2.0,
                num_beams=4,
                early_stopping=True,
                do_sample=False,  # Deterministic for consistency
                use_cache=True,   # Use KV cache for efficiency
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        # Decode summary
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        
        # Clean up the summary
        summary = summary.strip()
        if not summary:
            return "No summary could be generated."
        
        debug_print(f">>> Fast summary generated: {summary[:100]}...")
        return summary
        
    except Exception as e:
        debug_print(f">>> Fast summary generation error: {e}")
        return "An error occurred during summary generation."

def _chunked_summarization(text: str, max_input_tokens: int) -> str:
    """
    Handle long texts by splitting into chunks and summarizing each.
    Then create a final summary of the chunk summaries.
    """
    try:
        tokenizer = _t5_summarizer_cache['tokenizer']
        
        # Split text into sentences for better chunking
        import nltk
        sentences = nltk.sent_tokenize(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Build chunks that fit within token limit
        for sentence in sentences:
            # Estimate tokens (rough approximation)
            sentence_tokens = len(tokenizer.encode(sentence))
            
            if current_length + sentence_tokens < max_input_tokens - 20:  # Reserve space for "summarize:" prefix
                current_chunk.append(sentence)
                current_length += sentence_tokens
            else:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        debug_print(f">>> Split into {len(chunks)} chunks for summarization")
        
        # Summarize each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            debug_print(f">>> Summarizing chunk {i+1}/{len(chunks)}")
            summary = fast_generate_summary(chunk, max_input_tokens)  # Recursive call
            if summary and summary != "No summary could be generated.":
                chunk_summaries.append(summary)
        
        if not chunk_summaries:
            return "No summary could be generated from the chunks."
        
        # If only one chunk, return its summary
        if len(chunk_summaries) == 1:
            return chunk_summaries[0]
        
        # Create final summary from chunk summaries
        combined_text = " ".join(chunk_summaries)
        debug_print(f">>> Creating final summary from {len(chunk_summaries)} chunk summaries")
        
        return fast_generate_summary(combined_text, max_input_tokens)  # Final recursive call
        
    except Exception as e:
        debug_print(f">>> Chunked summarization error: {e}")
        return "An error occurred during chunked summarization."

def debug_gpu_memory():
    """Debug function to check GPU memory usage."""
    if torch.cuda.is_available():
        current_memory = torch.cuda.memory_allocated() / 1024**3  # GB
        max_memory = torch.cuda.max_memory_allocated() / 1024**3  # GB
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
        debug_print(f">>> GPU Memory: {current_memory:.2f}GB used, {max_memory:.2f}GB peak, {total_memory:.2f}GB total")
    else:
        debug_print(">>> GPU not available")

def calculate_importance(text: str, topic: str, tags: list) -> int:
    """
    Calculate importance score based on topic, tags, and text content.
    Maps classification results to 0-5 importance scale.
    
    Prioritizes:
    1. Facts provided by user (especially personal/biographical)
    2. Temporal references (memory callbacks)
    3. People mentions and relationships
    4. Project details (especially YouTube content)
    
    Penalizes:
    1. Testing questions
    2. Most user questions (answers are more valuable than questions)
    """
    text_lower = text.lower()
    
    # === PENALTIES: Testing questions and general questions ===
    # CHECK THESE FIRST to prevent questions from getting high scores
    testing_questions = [
        "what is my", "tell me my", "do you remember", "what's my", 
        "memory test", "have i mentioned", "have i told",
        "tell me about my", "do you know my", "recall my"
    ]
    # Only penalize based on explicit testing question phrases
    # Removed "testing memory" tag check - GLiClass applies it too broadly
    # Removed bare "testing" keyword - too many false positives (e.g., "I tested the motor")
    is_testing_question = any(phrase in text_lower for phrase in testing_questions)
    
    # General question indicators (less severe penalty)
    question_indicators = ["what", "where", "how", "why", "can you", "do you", "tell me"]
    is_question = (any(text_lower.startswith(q) for q in question_indicators) or "?" in text 
                   or "asking questions" in tags)
    
    # === HIGH PRIORITY: Facts provided by user ===
    provides_facts = "stating facts" in tags
    if not provides_facts:
        fact_indicators = ["my", "i am", "i have", "i live", "is called", "my name is", "my wife", "my cat"]
        provides_facts = any(phrase in text_lower for phrase in fact_indicators)
    
    # === HIGH PRIORITY: Personal/biographical information ===
    personal_data = "personal data" in tags
    if not personal_data:
        people_indicators = ["my wife", "my cat", "my name", "friend", "cohost", "dan", "erin", "winston", "name is"]
        personal_data = any(indicator in text_lower for indicator in people_indicators)
    
    # === MEDIUM PRIORITY: Temporal references (memory callbacks) ===
    has_temporal_context = "referencing past" in tags
    if not has_temporal_context:
        temporal_references = ["remember when", "first told", "originally", "back when", "the time i", "you said", "earlier"]
        has_temporal_context = any(phrase in text_lower for phrase in temporal_references)
    
    # === MEDIUM PRIORITY: Project content ===
    project_content = "project activity" in tags or "future planning" in tags
    youtube_content = "youtube" in text_lower or "video" in text_lower
    
    # === CALCULATE BASE IMPORTANCE ===
    # PENALTIES FIRST - with stronger enforcement for memory questions
    
    # Zero importance: Testing questions (HIGHEST PRIORITY PENALTY)
    if is_testing_question:
        base_importance = 0
        
    # Low importance: General questions (SECOND PRIORITY PENALTY)  
    # STRENGTHENED: Only allow factual statements that explicitly provide new info
    elif is_question:
        # Only override question penalty if it's CLEARLY a factual statement with new info
        # AND it doesn't ask for existing information (like "tell me about...")
        if (provides_facts and "stating facts" in tags and 
            not any(ask_phrase in text_lower for ask_phrase in ["tell me", "what is", "do you know"])):
            base_importance = 3  # Still lower than pure facts
        else:
            base_importance = 1
        
    # Maximum priority: Personal facts
    elif provides_facts and personal_data:
        base_importance = 5
    
    # High priority: Any factual statements
    elif provides_facts:
        base_importance = 4
        
    # High priority: Temporal memory references
    elif has_temporal_context:
        base_importance = 4
        
    # Medium-high priority: Project facts or YouTube content
    elif project_content or youtube_content:
        base_importance = 3
        
    # Default based on topic
    else:
        if topic in ["projects", "tasks", "deadline", "fix", "technical issues"]:
            base_importance = 3
        elif topic in ["callback", "technical details"]:
            base_importance = 2
        elif topic in ["humor", "weather", "meta", "testing"]:
            base_importance = 1
        else:
            base_importance = 2
    
    # === TAG-BASED ADJUSTMENTS ===
    high_importance_tags = ["stating facts", "personal data", "referencing past", "urgent matters", "technical issues"]
    low_importance_tags = ["testing memory", "asking questions", "chatting casually"]
    
    # Stronger penalty for asking questions
    if "asking questions" in tags and not ("stating facts" in tags):
        base_importance = max(0, base_importance - 1)
    elif any(tag in high_importance_tags for tag in tags):
        base_importance = min(5, base_importance + 1)
    elif any(tag in low_importance_tags for tag in tags):
        base_importance = max(0, base_importance - 1)
    
    # === FINAL ADJUSTMENTS ===
    # Urgent content gets a stronger boost
    urgent_keywords = ["urgent", "important", "asap", "deadline", "tomorrow", "today", "critical", "remember this", "don't forget"]
    has_urgent = any(keyword in text_lower for keyword in urgent_keywords)
    if has_urgent or "urgent matters" in tags:
        base_importance = min(5, base_importance + 2)  # Increased from +1 to +2
    
    # Special case: humor needs context to be important
    if topic == "humor" and not (has_temporal_context or provides_facts):
        base_importance = min(2, base_importance)
    
    debug_print(f">>> Importance calculation for: '{text[:50]}...'")
    debug_print(f"    Topic: {topic}, Tags: {tags}")
    debug_print(f"    Flags: facts={provides_facts}, personal={personal_data}, "
                f"temporal={has_temporal_context}, project={project_content}")
    debug_print(f"    Penalties: testing_q={is_testing_question}, general_q={is_question}")
    debug_print(f"    Final importance: {base_importance}")
    
    return base_importance

# --- Megaprompt Strategy Functions ---

def format_llama_conversation_history(history):
    """Convert conversation history to Llama 3.2 format."""
    formatted_pairs = []
    
    for entry in history:
        role = entry.get("role", "user")
        content = entry.get("content", "")
        
        if role == "user":
            formatted_pairs.append(f"<|start_header_id|>user<|end_header_id|>\n{content}\n<|eot_id|>")
        elif role == "assistant":
            formatted_pairs.append(f"<|start_header_id|>assistant<|end_header_id|>\n{content}\n<|eot_id|>")
    
    return "\n\n".join(formatted_pairs)

def build_persona_system_prompt():
    """Return the static persona system block (no time, no memories)."""
    personality = get_persona_text()
    return f"<|start_header_id|>system<|end_header_id|>\n{personality}\n<|eot_id|>"

def is_visual_question(text: str) -> bool:
    """Heuristic detection of visual questions with idiom exclusions."""
    if not text:
        return False
    t = text.lower()
    negatives = [
        "i see", "let's see", "see you", "see ya", "i could see why",
    ]
    if any(n in t for n in negatives):
        # only block if no positive token is present
        positives = [
            "what do you see", "do you see", "what am i holding", "am i holding",
            "in frame", "on screen", "camera", "picture", "photo", "faces",
            "who do you see", "look at", "can you see", "do you recognize",
        ]
        if not any(p in t for p in positives):
            return False
    # positives
    if any(p in t for p in [
        "what do you see", "do you see", "what am i holding", "am i holding",
        "in frame", "on screen", "camera", "picture", "photo", "faces",
        "who do you see", "look at", "can you see", "do you recognize",
    ]):
        return True
    return False


def build_ephemeral_system_prompt(retrieved_memories, visual_mode: bool = False):
    """Return the ephemeral system block (current time + top memories)."""
    from datetime import datetime
    import utils
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Only include camera observation when visual_mode and fresh (<=10s)
    vision_line = None
    if visual_mode:
        try:
            if getattr(config, "VISION_ENABLE", True):
                vision_line = vision_state.get_manager().build_observation_for_current(max_age_seconds=10)
        except Exception:
            vision_line = None

    memory_section = ""
    if retrieved_memories:
        memory_bullets = []
        # Visual turns: include exactly 1 memory; otherwise include up to 3
        max_memories = 1 if visual_mode else 3
        for chunk in retrieved_memories[:max_memories]:
            if chunk.get("timestamp"):
                time_ago = utils.time_ago(chunk["timestamp"])  # e.g., "2h ago"
                text = chunk.get("text", chunk.get("content", ""))
                memory_bullets.append(f"• ({time_ago}) {text}")
        if memory_bullets:
            memory_section = "\nRelevant memories for this turn:\n" + "\n".join(memory_bullets)

    persona_text = get_persona_text()
    instruction = (
        "Rely only on the camera observation below for current visuals; do not use past statements or memories to infer current visuals. "
        "If the observation lacks detail, say you can’t tell from the camera. If any memory contradicts the observation, prefer the observation. "
        "Do not output the words 'Vision' or '[VISION]'; do not repeat the observation verbatim; answer concisely."
    )

    # Build sections: persona/time/memories first; place vision at the bottom if visual
    sections = [
        persona_text,
        f"\nCurrent time: {current_time}. Use the following memories only if relevant, and do not quote them verbatim.",
    ]
    if memory_section:
        sections.append(memory_section)
    if visual_mode and vision_line:
        sections.append("\n" + instruction)
        sections.append(vision_line)

    content = "\n".join(sections)

    return f"<|start_header_id|>system<|end_header_id|>\n{content}\n<|eot_id|>"

def build_megaprompt(history, user_message, retrieved_memories):
    """Build the complete megaprompt for /api/generate with persona, history, ephemeral system, and latest user.

    Ordering (Llama 3.2 style):
    - Static persona system block (no time/memories)
    - Prior conversation pairs (user/assistant only)
    - Ephemeral system block (time + top memories)
    - Latest user
    - Assistant header
    """

    # Build conversation history (prior pairs only)
    conversation_history = format_llama_conversation_history(history)

    # Detect visual intent and build unified system block accordingly
    visual_mode = is_visual_question(user_message)
    unified_system_block = build_ephemeral_system_prompt(retrieved_memories, visual_mode=visual_mode)

    # Place unified system block immediately before the latest user message
    user_block = f"<|start_header_id|>user<|end_header_id|>\n{user_message}\n<|eot_id|>"
    assistant_header = "<|start_header_id|>assistant<|end_header_id|>"

    parts = []
    if conversation_history.strip():
        parts.append(conversation_history)
    parts.extend([unified_system_block, user_block, assistant_header])

    megaprompt = "\n\n".join(parts)

    debug_print(f"*** Debug: Built unified megaprompt ({len(megaprompt)} chars)")
    debug_print(f"*** Debug: Megaprompt preview: {megaprompt[:200]}...")

    return megaprompt

def get_persona_text():
    """Return the static persona text used to guide the assistant's style."""
    return """You are Little Timmy — a brilliant, arrogant, sardonic mechatronic skeleton that Dan made; you secretly like Dan but tease him.
        You are a witty foil yet cooperative and concise.
        Rules:
        - Assume you are talking to Dan unless told otherwise.
        - Answer the question directly first; attitude comes second.
        - Prefer one sentence; up to two if needed for clarity.
        - Do NOT use stage directions or roleplay actions (e.g., rolls eyes, sighs, shrugs).
        - Do NOT use parentheses or quotation marks in responses.
        - Do NOT use italics/emphasis markers or emojis (no asterisks, underscores, brackets).
        - Use memories only if relevant; briefly acknowledge time without quotes (e.g., Earlier, today).
        - Strive for variation in your responses; do not repeat the same joke or quip twice."""
        

def build_tail_prompt(user_message, retrieved_memories, session_recap: str = ""):
    """Build only the changing tail of the prompt for KV reuse: minimal ephemeral system + latest user + assistant header.

    IMPORTANT: Do NOT include the full persona/rules here to preserve KV reuse. Use a short reinforcement and per-turn memory bullets only.
    """
    # 1. Minimal ephemeral system prompt – short reinforcement + memory bullets only
    unified_system = build_ephemeral_system_tail(retrieved_memories, session_recap=session_recap)

    # 2. Latest user message
    user_prompt = f"<|start_header_id|>user<|end_header_id|>\n{user_message}\n<|eot_id|>"

    # 3. Assistant header (to prompt response)
    assistant_header = "<|start_header_id|>assistant<|end_header_id|>"

    return "\n\n".join([unified_system, user_prompt, assistant_header])

def build_ephemeral_system_tail(retrieved_memories, session_recap: str = "", visual_mode: bool = False):
    """Build a small system section for the tail that avoids re-sending the full persona.

    Includes a brief style reinforcement and the per-turn memory bullets only.
    """
    from datetime import datetime
    import utils

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Compact identity anchor to prevent personality drift without resending full persona
    reinforcement = (
        "Identity: Little Timmy — witty, sarcastic; 1 sentence answer + short quip after an em dash; no apologies; never say 'as an AI'; talk to Dan."
    )

    memory_section = ""
    if retrieved_memories:
        # Optional compact camera observation (computed early for memory sizing/placement)
        vision_line = None
        if visual_mode:
            try:
                if getattr(config, "VISION_ENABLE", True):
                    vision_line = vision_state.get_manager().build_observation_for_current(max_age_seconds=10)
            except Exception:
                vision_line = None

        memory_bullets = []
        # Visual turns: include exactly 1 memory; otherwise include up to 3
        max_memories = 1 if visual_mode else 3
        for chunk in retrieved_memories[:max_memories]:
            if chunk.get("timestamp"):
                time_ago = utils.time_ago(chunk["timestamp"])  # e.g., "2h ago"
                text = chunk.get("text", chunk.get("content", ""))
                memory_bullets.append(f"• ({time_ago}) {text}")
        if memory_bullets:
            memory_section = "\nMemories:\n" + "\n".join(memory_bullets[:5])

    recap_section = f"\nSession recap:\n{session_recap}" if session_recap.strip() else ""

    # Optional compact camera observation (visual only)
    if 'vision_line' not in locals():
        vision_line = None
        if visual_mode:
            try:
                if getattr(config, "VISION_ENABLE", True):
                    vision_line = vision_state.get_manager().build_observation_for_current(max_age_seconds=10)
            except Exception:
                vision_line = None

    instruction = (
        "Rely only on the camera observation below for current visuals; do not use past statements or memories to infer current visuals. "
        "If the observation lacks detail, say you can’t tell from the camera. If any memory contradicts the observation, prefer the observation. "
        "Do not output the words 'Vision' or '[VISION]'; do not repeat the observation verbatim; answer concisely."
    )

    pieces = []
    pieces.append(f"{reinforcement}\nCurrent time: {current_time}.")
    if recap_section:
        pieces.append(recap_section)
    if memory_section:
        pieces.append(memory_section)
    if visual_mode and vision_line:
        pieces.append("\n" + instruction)
        pieces.append("\n" + vision_line)

    content = "".join(pieces)
    return f"<|start_header_id|>system<|end_header_id|>\n{content}\n<|eot_id|>"

def build_baseline_prompt(user_message: str) -> str:
    """Build baseline prompt with strong persona only (no memories) + latest user + assistant header.

    This is intended for the very first turn to establish identity in the session KV.
    """
    persona_system = build_persona_system_prompt()  # persona + instructions only
    user_prompt = f"<|start_header_id|>user<|end_header_id|>\n{user_message}\n<|eot_id|>"
    assistant_header = "<|start_header_id|>assistant<|end_header_id|>"
    return "\n\n".join([persona_system, user_prompt, assistant_header])

def generate_api_call(megaprompt, context=None, raw: bool = True, temperature: float = 0.4):
    """Call Ollama /api/generate endpoint with the megaprompt.

    Returns a tuple: (response_text, new_context, stats_dict).
    """
    import requests
    import json
    # Local import to avoid any circular import at module load time
    import utils
    
    payload = {
        "model": config.MODEL_NAME,
        "prompt": megaprompt,
        "stream": True,
        "keep_alive": "1h",
        "options": {
            "num_ctx": config.LLM_CONTEXT_SIZE,
            "temperature": temperature,
            "repeat_penalty": 1.2
        }
    }
    if raw:
        payload["raw"] = True
    
    # Use explicit context to append to prior KV state and preserve conversation
    if context:
        payload["context"] = context
    # Also include session_id for server-side residency
    if hasattr(config, 'OLLAMA_SESSION_ID'):
        payload["session_id"] = config.OLLAMA_SESSION_ID
    
    # Debug: prompt sizing and session
    try:
        prompt_chars = len(megaprompt) if isinstance(megaprompt, str) else 0
        est_tokens = utils.estimate_tokens(megaprompt) if isinstance(megaprompt, str) else 0
        has_session = "session_id" in payload and bool(payload["session_id"])
        debug_print(f"*** Debug: Calling generate API: {config.OLLAMA_API_URL}")
        debug_print(f"*** Debug: Model={payload['model']}, num_ctx={payload['options']['num_ctx']}, keep_alive={payload['keep_alive']}, session_id_set={has_session}")
        debug_print(f"*** Debug: Prompt size: {prompt_chars} chars, ~{est_tokens} tokens (estimate)")
    except Exception:
        pass
    
    try:
        with requests.post(
            config.OLLAMA_API_URL,
            json=payload,
            timeout=120,
            stream=True
        ) as r:
            r.raise_for_status()
            collected = []
            final_context = None
            stats = {}
            for line in r.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line.decode("utf-8"))
                token = chunk.get("response")
                if token:
                    collected.append(token)
                if chunk.get("done"):
                    final_context = chunk.get("context", final_context)
                    stats = {
                        "prompt_eval_count": chunk.get("prompt_eval_count"),
                        "prompt_eval_duration": chunk.get("prompt_eval_duration"),
                        "eval_count": chunk.get("eval_count"),
                        "eval_duration": chunk.get("eval_duration"),
                        "total_duration": chunk.get("total_duration"),
                        "load_duration": chunk.get("load_duration"),
                    }
                    break

            ai_response = ("".join(collected)).strip()

            if ai_response:
                debug_print(f"*** Debug: AI Response: {ai_response[:100]}...")
            else:
                debug_print(f"*** Debug: Empty streamed response received")

            try:
                ctx_len = len(final_context) if isinstance(final_context, list) else (len(final_context) if final_context is not None else 0)
                debug_print(f"*** Debug: Returned context length: {ctx_len}")
                debug_print(f"*** Debug: Timings ms ~ load={stats.get('load_duration')} prompt_eval={stats.get('prompt_eval_duration')} eval={stats.get('eval_duration')} total={stats.get('total_duration')}")
            except Exception:
                pass

            return ai_response or "I appear to be having trouble speaking. How embarrassing.", final_context, stats

    except Exception as e:
        debug_print(f"*** Debug: Generate API call failed: {e}")
        return "I appear to be having trouble speaking. How embarrassing.", None, {}