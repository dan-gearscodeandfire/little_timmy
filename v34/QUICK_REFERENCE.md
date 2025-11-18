# Quick Reference - Cleanup Checklist

**Use this as a quick reference while cleaning up the code.**

---

## 🎯 Quick Stats

- **Total lines analyzed:** 2,592 (core application)
- **Dead code found:** ~350 lines
- **Files with issues:** 6 of 7
- **Test files moved:** 10 files → `tests/`
- **Critical issues:** 0 (no bugs, just cleanup needed)

---

## ✅ Safe Removals (Won't Break Anything)

### app.py
```python
# Line 9 - Remove this:
import re
```

### llm.py
```python
# Line 12 - Delete this:
# import urllib3 # This is no longer needed

# Lines 47-80 - Remove entire SYSTEM constant:
SYSTEM = """..."""

# Lines 127-157 - Remove function:
def generate_summary(text: str) -> str:

# Lines 616-640 - Remove function:
def build_llama_full_chat(history, context_text=""):

# Lines 642-678 - Remove function:
def build_chat_messages(history, context_text=""):

# Lines 680-694 - Remove function:
def build_chat_payload(history, context_text=""):

# Lines 696-737 - Remove function:
def test_chat_endpoint(test_message="Hello, this is a test"):

# Lines 741-754 - KEEP THIS FUNCTION (actively used by build_megaprompt):
# def format_llama_conversation_history(history):
```

**Total removal: ~330 lines** (format_llama_conversation_history kept - actively used)

---

## 🔧 Quick Fixes (Update These)

### All Files - Version Comments
```python
# Change this:
# v18/app.py

# To this:
# v34/app.py
```

**Files to update:** app.py, llm.py, memory.py, utils.py, config.py

### app.py Line 31
```python
# Change this:
# Maintain per-session KV contexts for Ollama generate() caching (legacy; no longer used for outbound requests)

# To this:
# Maintain per-session KV contexts for Ollama generate() caching
# Used to preserve conversation state across turns
```

### memory.py Line 133
```python
# Change this:
chunk_metadata = metadata or llm.generate_metadata(chunk_text)

# To this:
chunk_metadata = metadata or llm.fast_generate_metadata(chunk_text)
```

### startup.sh Line 14
```bash
# Change this:
VENV_PATH="$SCRIPT_DIR/venv"

# To this:
VENV_PATH="$HOME/timmy-backend/aiortc/.venv"
```

---

## 📝 Function Usage Map

### llm.py Functions

| Function | Status | Used By | Action |
|----------|--------|---------|--------|
| `fast_generate_metadata()` | ✅ Active | app.py:124 | Keep |
| `fast_generate_summary()` | ✅ Active | memory.py:89 | Keep |
| `build_megaprompt()` | ✅ Active | app.py:177 | Keep |
| `build_baseline_prompt()` | ✅ Active | app.py:187 | Keep |
| `build_tail_prompt()` | ✅ Active | app.py:202 | Keep |
| `is_visual_question()` | ✅ Active | app.py:225 | Keep |
| `generate_api_call()` | ✅ Active | app.py:226 | Keep |
| `build_ephemeral_system_prompt()` | ✅ Active | llm.py:854 | Keep |
| `build_ephemeral_system_tail()` | ✅ Active | llm.py:893 | Keep |
| `get_persona_text()` | ✅ Active | llm.py:758, 816, 874 | Keep |
| `calculate_importance()` | ✅ Active | llm.py:281 | Keep |
| `_initialize_classifier()` | ✅ Active | llm.py:246 | Keep |
| `_initialize_t5_summarizer()` | ✅ Active | llm.py:349 | Keep |
| `_chunked_summarization()` | ✅ Active | llm.py:367 | Keep |
| `debug_gpu_memory()` | ✅ Active | llm.py:206, 232 | Keep |
| `build_persona_system_prompt()` | ✅ Active | llm.py:976 | Keep |
| `generate_metadata()` | ⚠️ Fallback | memory.py:133 | Consider removing |
| `generate_summary()` | ❌ Dead | Never | **REMOVE** |
| `build_llama_full_chat()` | ❌ Dead | Never | **REMOVE** |
| `build_chat_messages()` | ❌ Dead | Never | **REMOVE** |
| `build_chat_payload()` | ❌ Dead | Never | **REMOVE** |
| `test_chat_endpoint()` | ❌ Dead | Never | **REMOVE** |
| `format_llama_conversation_history()` | ✅ Active | llm.py:644 (build_megaprompt) | Keep |

---

## 🗂️ Files Moved

### To tests/ directory:
- ✅ test_chat_endpoint.py
- ✅ test_connection.py
- ✅ test_connectivity.py
- ✅ test_megaprompt.py
- ✅ test_request.py
- ✅ test_tail_mode.py
- ✅ test_tail_mode_delayed.py
- ✅ test_vision_state.py
- ✅ classifier.py (demo script)
- ✅ kv_cache_test.py (utility)

---

## 📚 Documentation Created

- ✅ `tests/README.md` - Test file inventory
- ✅ `CLEANUP_FINDINGS.md` - Comprehensive analysis (350+ lines)
- ✅ `CODE_ISSUES_DETAILED.md` - Line-by-line reference
- ✅ `CLEANUP_SUMMARY.md` - Executive summary
- ✅ `QUICK_REFERENCE.md` - This file

---

## ⏱️ Time Estimates

| Task | Time | Difficulty |
|------|------|------------|
| Remove dead code | 30 min | Easy |
| Update version comments | 10 min | Easy |
| Fix misleading comments | 10 min | Easy |
| Update memory.py fallback | 5 min | Easy |
| Fix startup.sh | 10 min | Easy |
| Add README.md | 1 hour | Medium |
| Add docstrings | 2 hours | Medium |
| Add LICENSE | 5 min | Easy |
| **TOTAL** | **~4 hours** | **Easy-Medium** |

---

## 🚦 Priority Order

1. **First** - Remove dead code (biggest impact)
2. **Second** - Update version comments (quick win)
3. **Third** - Fix misleading comments (prevents confusion)
4. **Fourth** - Add README.md (essential for GitHub)
5. **Fifth** - Add LICENSE (essential for GitHub)
6. **Last** - Add docstrings (nice to have)

---

## 🎯 One-Line Summary

**Remove ~350 lines of dead chat endpoint code, update version comments, add README/LICENSE, and you're GitHub-ready! 🚀**

