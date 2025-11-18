# Megaprompt Strategy for Memory Integration
# This reflects code changes implemented on 7-30-2025 and does not reflect more recent versions, it is here for reference
## Overview
Switch from Ollama `/api/chat` endpoint to `/api/generate` endpoint with ephemeral system prompts for better memory integration and KV cache efficiency.

## Core Problem
- Llama 3.2 3B ignores `"tool"` role messages completely
- Chat endpoint expects persistent conversation but we rebuild context each time
- Memory retrieval works perfectly but LLM ignores the retrieved memories

## Solution: Ephemeral System Prompts
Use `/api/generate` with single megaprompt containing:
1. **Static system prompt** (personality/behavior - SYSTEM_CHAT)
2. **Conversation history** (user/assistant pairs)
3. **Ephemeral system prompt** (time + memories) - ADDED/REMOVED each turn
4. **Latest user message**

## Architecture

### Format (Llama 3.2 style):
```
<|start_header_id|>system<|end_header_id|>
[Static personality prompt from SYSTEM_CHAT]
<|eot_id|>

[Previous conversation pairs in proper format]

<|start_header_id|>system<|end_header_id|>
The current time is 2025-07-28 17:30:15. The following are relevant memories for your response to subsequent user messages, including how long ago those memories were made: (22 minutes) Memory1 (2 hours) Memory2
<|eot_id|>

<|start_header_id|>user<|end_header_id|>
[Latest user message]
<|eot_id|>

<|start_header_id|>assistant<|end_header_id|>
```

### Ephemeral Prompt Lifecycle:
1. **Before generation**: Inject ephemeral system prompt with current time + retrieved memories
2. **Send to LLM**: Full megaprompt via `/api/generate`
3. **After generation**: Remove ephemeral system prompt from conversation history
4. **Store response**: Add assistant response to conversation history
5. **Next turn**: Repeat with new ephemeral prompt

## Key Benefits
- ✅ **KV Cache Efficiency**: Only ephemeral+user messages change, rest stays cached
- ✅ **Memory Integration**: System-level instructions that Llama 3.2 respects
- ✅ **No Token Waste**: Old memory prompts removed, only current relevant memories
- ✅ **Clean Architecture**: Static personality separate from dynamic memory context
- ✅ **No Role Confusion**: Uses system/user/assistant roles properly

## Implementation Requirements

### Configuration:
- Use `OLLAMA_API_URL = "http://windows-host:11434/api/generate"`
- Maintain session ID for potential KV cache benefits
- Use `.venv` at `~/timmy-backend/.venv/bin/activate`

### Memory Format:
```
The current time is YYYY-MM-DD HH:MM:SS. The following are relevant memories for your response to subsequent user messages, including how long ago those memories were made: (X minutes ago) Memory text (Y hours ago) Memory text
```

### Conversation Storage:
- Keep conversation history in RAM (`utils.conversation_history`)
- Strip ephemeral system prompts when building megaprompt
- Each ephemeral prompt is injected once, then removed

### Response Handling:
- Expect raw text response from `/api/generate` (no JSON message structure)
- No tool calls, simpler response parsing

## Files to Modify
1. **llm.py**: New `build_megaprompt()` and `generate_api_call()` functions
2. **app.py**: Update `process_user_message()` to use generate endpoint
3. **config.py**: Update API URL to generate endpoint
4. **utils.py**: Potentially update conversation history management

## Success Criteria
- LLM acknowledges and uses retrieved memories in responses
- Performance improvement from KV cache efficiency
- Clean separation of static personality vs. dynamic memory context
- Elimination of tool role confusion issues

## Future Reference
This approach solves the fundamental architectural mismatch between chat endpoints (designed for persistent conversations) and our use case (stateless memory-augmented responses with full context rebuilding each turn).

---

Addendum (2025-08-17 00:24:05 EDT)

- Name: Megaprompt (Full) with Ephemeral Memory, Retrieval OFF
- Tag/slug: MP-full-ephem-noR
- Notes: Persona+history are re-sent each turn; ephemeral system (time + potential vector memories) is injected per turn and not stored; vector retrieval currently disabled.

Addendum (2025-08-17 00:44:22 EDT)

- Name: Megaprompt (Full) with Ephemeral Memory, Retrieval ON
- Tag/slug: MP-full-ephem-R
- Notes: Persona+history are re-sent each turn; ephemeral system (time + potential vector memories) is injected per turn and stored; vector retrieval enabled.

Addendum (2025-08-17 01:15:16 EDT)

- Current working model
  - USE_FULL_MEGA_PROMPT=True (Full megaprompt)
  - RETRIEVAL_ENABLED=True (Vector retrieval ON)
  - Ephemeral system: time + top retrieved memories injected per turn
  - Returned context: typically empty; residency relies on session_id
  - Observations: strong recall; token heavier; latency acceptable on 3B Q4