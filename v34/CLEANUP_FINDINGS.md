# Code Cleanup Findings - v34

**Generated:** 2025-11-17  
**Purpose:** Identify unused code, outdated functions, and oddities before GitHub publication

---

## 🔴 HIGH PRIORITY - Unused/Dead Code

### 1. **llm.py - Unused Chat Endpoint Functions**
The following functions are **never called** in the active codebase (only in disabled test files):

- `build_llama_full_chat()` (line 616) - Old LLaMA chat format builder
- `build_chat_messages()` (line 642) - Chat endpoint message builder
- `build_chat_payload()` (line 680) - Chat endpoint payload builder
- `test_chat_endpoint()` (line 696) - Test function for chat endpoint

**Reason:** The project switched from `/api/chat` to `/api/generate` endpoint (see `config.USE_CHAT_ENDPOINT = False`)

**Recommendation:** 
- ✅ Keep for now (may be useful for future endpoint switching)
- 🔧 Add deprecation comments
- 📝 Document that these are for the disabled chat endpoint

---

### 2. **llm.py - Unused LLM-based Metadata/Summary Functions**

These functions are **replaced by faster alternatives** but still present:

- `generate_summary()` (line 127) - **Replaced by** `fast_generate_summary()` (T5-based)
- `generate_metadata()` (line 159) - **Replaced by** `fast_generate_metadata()` (GLiClass-based)

**Current Usage:**
- ✅ `fast_generate_summary()` - Used in `memory.py:89`
- ✅ `fast_generate_metadata()` - Used in `app.py:124`
- ❌ `generate_metadata()` - Only used as fallback in `memory.py:133` (when metadata is None)
- ❌ `generate_summary()` - **NEVER USED**

**Recommendation:**
- 🗑️ **Remove** `generate_summary()` - completely unused
- ⚠️ **Keep** `generate_metadata()` - used as fallback, but consider removing if GLiClass is stable

---

### 3. **llm.py - Unused System Prompt**

- `SYSTEM` (line 47-80) - Large JSON-formatted system prompt **never used**
- Only `SYSTEM_CHAT` (line 36) is actively used

**Recommendation:**
- 🗑️ **Remove** `SYSTEM` constant - it's from an older iteration

---

### 4. **llm.py - Helper Functions Status**

- `format_llama_conversation_history()` (line 741) - **ACTIVELY USED** by `build_megaprompt()` (line 644)
- `build_persona_system_prompt()` (line 756) - **ACTIVELY USED** by `build_baseline_prompt()`

**Recommendation:**
- ✅ **Keep** `format_llama_conversation_history()` - required for megaprompt building
- ✅ **Keep** `build_persona_system_prompt()` - actively used

**Note:** Initially marked for removal but testing revealed it's essential for the megaprompt strategy.

---

### 5. **config.py - Unused/Misleading Settings**

```python
USE_CHAT_ENDPOINT = False  # DISABLED: Using generate endpoint with megaprompt strategy
OLLAMA_CHAT_API_URL = "http://windows-host:11434/api/chat"  # Only used in dead test
```

**Recommendation:**
- 🔧 Keep `USE_CHAT_ENDPOINT` but add better documentation
- ⚠️ Keep `OLLAMA_CHAT_API_URL` (used in test files)

---

### 6. **app.py - Commented-Out Model Name**

```python
#MODEL_NAME = "llava:7b"  # Line 21 in config.py
```

**Recommendation:**
- 🗑️ Remove commented-out model name or move to a config comment section

---

### 7. **llm.py - Unused Import**

```python
# import urllib3 # This is no longer needed  (line 12)
```

**Recommendation:**
- 🗑️ Remove the commented-out import

---

## 🟡 MEDIUM PRIORITY - Oddities & Code Smells

### 1. **app.py - Misleading Comment (line 31)**

```python
# Maintain per-session KV contexts for Ollama generate() caching (legacy; no longer used for outbound requests)
SESSION_CONTEXTS: dict[str, list[int]] = {}
```

**Issue:** Comment says "no longer used" but it IS used (lines 218, 232)

**Recommendation:**
- 🔧 Update comment to reflect actual usage

---

### 2. **app.py - Version Comment Mismatch**

```python
# v18/app.py  (line 1)
```

**Issue:** File is in v34 directory but header says v18

**Recommendation:**
- 🔧 Update to `# v34/app.py` or remove version comment

---

### 3. **llm.py - Duplicate Imports**

```python
from transformers import AutoTokenizer  # Line 4 in gliclass_source/test_gliclass.py (appears twice)
```

**Recommendation:**
- 🔧 Check for and remove duplicate imports

---

### 4. **memory.py - Fallback to Slow Function**

```python
chunk_metadata = metadata or llm.generate_metadata(chunk_text)  # Line 133
```

**Issue:** Falls back to slow LLM-based metadata generation if metadata is None

**Recommendation:**
- 🔧 Consider always using `fast_generate_metadata()` instead
- 📝 Document why the fallback exists

---

### 5. **vision_state.py - Complex Fallback Config**

Lines 17-39 have a complex fallback config class when `config` import fails.

**Recommendation:**
- ✅ Keep as-is (good defensive programming)
- 📝 Add comment explaining it's for standalone testing

---

### 6. **app.py - Hardcoded Cutoff Time**

```python
cutoff_time = "2025-07-28 16:30:00"  # Line 415
```

**Issue:** Hardcoded date in cleanup function

**Recommendation:**
- 🔧 Make this configurable or remove if one-time cleanup

---

### 7. **llm.py - Visual Mode Detection Heuristics**

The `is_visual_question()` function (line 761) has hardcoded phrase lists.

**Recommendation:**
- ✅ Keep as-is (heuristics are fine for this use case)
- 📝 Consider moving phrases to config.py for easier tuning

---

## 🟢 LOW PRIORITY - Documentation & Style

### 1. **Missing Docstrings**

Many functions lack docstrings, especially in:
- `app.py` - Route handlers
- `memory.py` - Database functions
- `utils.py` - Utility functions

**Recommendation:**
- 📝 Add docstrings before GitHub publication

---

### 2. **Debug Print Statements**

Heavy use of `utils.debug_print()` throughout codebase.

**Recommendation:**
- ✅ Keep (useful for debugging)
- 🔧 Consider using proper logging module instead

---

### 3. **Magic Numbers**

Various magic numbers throughout:
- `max_age_seconds=10` in vision state
- `threshold=0.8` in duplicate detection
- `alpha = 0.5` in EMA calculations

**Recommendation:**
- 🔧 Move to config.py or add inline comments explaining values

---

## 📊 Summary Statistics

### Functions by Usage Status:

**llm.py (23 functions total):**
- ✅ **Actively Used:** 11 functions
- ⚠️ **Fallback Only:** 1 function (`generate_metadata`)
- ❌ **Unused/Dead:** 5 functions (chat endpoint related + `generate_summary`)
- 🔧 **Helper Functions:** 6 functions (some used, some not)

### Unused Imports:
- ❌ `re` in app.py (line 9) - **NEVER USED** (can be safely removed)
- ❌ Commented urllib3 in llm.py (line 12) - Already commented, should be deleted

---

## 🎯 Recommended Action Plan

### Phase 1: Safe Removals (No Risk)
1. Remove `generate_summary()` from llm.py
2. Remove `SYSTEM` constant from llm.py
3. Remove commented-out urllib3 import
4. Update version comments (v18 → v34)

### Phase 2: Conditional Removals (Low Risk)
1. Remove chat endpoint functions if no plans to re-enable
2. ~~Remove `format_llama_conversation_history()`~~ **KEEP - actively used by build_megaprompt()**
3. Clean up hardcoded cutoff_time in cleanup function

### Phase 3: Improvements (Medium Effort)
1. Fix misleading comments (SESSION_CONTEXTS)
2. Replace `generate_metadata()` fallback with `fast_generate_metadata()`
3. Add docstrings to public functions
4. Move magic numbers to config

### Phase 4: Documentation (Before GitHub)
1. Add README.md with setup instructions
2. Add CONTRIBUTING.md
3. Add LICENSE file
4. Document gliclass_source dependency
5. Add architecture diagram

---

## 🔍 Files Analyzed

- ✅ `app.py` (545 lines)
- ✅ `llm.py` (1071 lines)
- ✅ `memory.py` (381 lines)
- ✅ `config.py` (52 lines)
- ✅ `utils.py` (127 lines)
- ✅ `vision_state.py` (367 lines)
- ✅ `classifier.py` (49 lines)

**Total:** ~2,592 lines of core application code (excluding gliclass_source and tests)

---

## 🔧 Additional Oddities Found

### 1. **startup.sh - Wrong Virtual Environment Path**
```bash
VENV_PATH="$SCRIPT_DIR/venv"  # Line 14
```
**Issue:** Script creates/activates `venv` in v34 directory, but user specified using `~/timmy-backend/aiortc/.venv`

**Recommendation:**
- 🔧 Update to use correct venv path or document that this script is outdated

### 2. **app.py - Unused `re` Import**
```python
import re  # Line 9 - NEVER USED
```

**Recommendation:**
- 🗑️ Remove this import

### 3. **Multiple Version Comments**
Files have inconsistent version headers:
- `app.py` says "v18/app.py" (line 1)
- `llm.py` says "v18/llm.py" (line 1)
- `memory.py` says "v18/memory.py" (line 1)
- `utils.py` says "v18/utils.py" (line 1)
- `config.py` says "v18/config.py" (line 1)

**Recommendation:**
- 🔧 Update all to v34 or remove version comments entirely

### 4. **classifier.py - Standalone Test Script**
This file appears to be a standalone test/demo script (not imported by main app).

**Recommendation:**
- 🔧 Move to `tests/` directory or add comment that it's a demo script

### 5. **kv_cache_test.py - Test Script in Root**
Another test script in the root directory.

**Recommendation:**
- 🔧 Move to `tests/` directory

### 6. **Hardcoded Database Credentials in startup.sh**
```bash
PGPASSWORD="timmy_postgres_pwd" psql -h localhost -p 5433 -U postgres -d timmy_memory_v16
```

**Recommendation:**
- ⚠️ Add note in README about changing default credentials
- 🔧 Consider using environment variables

### 7. **Global Caches in llm.py**
```python
_classifier_cache = {...}  # Line 19
_t5_summarizer_cache = {...}  # Line 27
```

**Recommendation:**
- ✅ Good pattern for lazy loading
- 📝 Add docstring explaining these are module-level singletons

---

## ⚠️ Notes

- **gliclass_source/**: Left untouched per user request (189 files)
- **Test files**: Moved to `tests/` subdirectory with warning note
- **Historical docs**: Left in place per user request (will update later)
- **Startup script**: References wrong venv path and has hardcoded credentials

