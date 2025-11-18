# Cleanup Checklist - v34 Codebase

**Print this and check off items as you complete them!**

---

## Phase 1: Safe Removals ⏱️ 30 minutes

### app.py
- [ ] Line 9: Remove `import re`
- [ ] Line 1: Update `# v18/app.py` to `# v34/app.py`

### llm.py
- [ ] Line 1: Update `# v18/llm.py` to `# v34/llm.py`
- [ ] Line 12: Delete `# import urllib3 # This is no longer needed`
- [ ] Lines 47-80: Remove entire `SYSTEM = """..."""` constant
- [ ] Lines 127-157: Remove `def generate_summary(text: str) -> str:`
- [ ] Lines 616-640: Remove `def build_llama_full_chat(history, context_text=""):`
- [ ] Lines 642-678: Remove `def build_chat_messages(history, context_text=""):`
- [ ] Lines 680-694: Remove `def build_chat_payload(history, context_text=""):`
- [ ] Lines 696-737: Remove `def test_chat_endpoint(test_message="Hello, this is a test"):`
- [x] ~~Lines 741-754: Remove `def format_llama_conversation_history(history):`~~ **KEEP - actively used**

### memory.py
- [ ] Line 1: Update `# v18/memory.py` to `# v34/memory.py`

### config.py
- [ ] Line 1: Update `# v18/config.py` to `# v34/config.py`

### utils.py
- [ ] Line 1: Update `# v18/utils.py` to `# v34/utils.py`

### Test After Phase 1
- [ ] Run `python app.py` and verify it starts without errors
- [ ] Test a basic chat interaction
- [ ] Check that memory retrieval still works

---

## Phase 2: Comment Fixes ⏱️ 15 minutes

### app.py
- [ ] Line 31: Update misleading comment about SESSION_CONTEXTS
  ```python
  # OLD:
  # Maintain per-session KV contexts for Ollama generate() caching (legacy; no longer used for outbound requests)
  
  # NEW:
  # Maintain per-session KV contexts for Ollama generate() caching
  # Used to preserve conversation state across turns
  ```

### config.py
- [ ] Lines 6-7: Improve USE_CHAT_ENDPOINT documentation
  ```python
  # OLD:
  USE_CHAT_ENDPOINT = False  # DISABLED: Using generate endpoint with megaprompt strategy
  
  # NEW:
  # Endpoint selection: False = /api/generate (current), True = /api/chat (legacy)
  # The generate endpoint is used with the megaprompt strategy for better memory integration
  USE_CHAT_ENDPOINT = False
  ```

---

## Phase 3: Code Improvements ⏱️ 15 minutes

### memory.py
- [ ] Line 133: Update to use fast_generate_metadata
  ```python
  # OLD:
  chunk_metadata = metadata or llm.generate_metadata(chunk_text)
  
  # NEW:
  chunk_metadata = metadata or llm.fast_generate_metadata(chunk_text)
  ```

### startup.sh
- [ ] Line 14: Fix venv path
  ```bash
  # OLD:
  VENV_PATH="$SCRIPT_DIR/venv"
  
  # NEW:
  VENV_PATH="$HOME/timmy-backend/aiortc/.venv"
  ```

### app.py (Optional)
- [ ] Line 415: Make cutoff_time configurable
  ```python
  # OLD:
  cutoff_time = "2025-07-28 16:30:00"
  
  # NEW:
  cutoff_time = getattr(config, "MEMORY_CLEANUP_CUTOFF", "2025-07-28 16:30:00")
  ```

### Test After Phase 3
- [ ] Run full system test
- [ ] Verify memory storage and retrieval
- [ ] Check that startup.sh works (if you use it)

---

## Phase 4: Documentation ⏱️ 2 hours

### Create README.md
- [ ] Project title and description
- [ ] Features list
- [ ] Architecture overview
- [ ] Prerequisites
- [ ] Installation instructions
- [ ] Configuration guide
- [ ] Usage examples
- [ ] Troubleshooting section
- [ ] Note about gliclass_source

### Create LICENSE
- [ ] Choose license (MIT, Apache 2.0, GPL, etc.)
- [ ] Add LICENSE file with your name and year

### Create CONTRIBUTING.md (Optional)
- [ ] How to report bugs
- [ ] How to suggest features
- [ ] Code style guidelines
- [ ] Pull request process

### Update Existing Docs
- [ ] Update megaprompt_strategy.md with current version info
- [ ] Add note to historical docs that they're from older versions

### Add Docstrings
- [ ] app.py: Add docstrings to route handlers
- [ ] llm.py: Add docstrings to public functions
- [ ] memory.py: Add docstrings to database functions
- [ ] utils.py: Add docstrings to utility functions

---

## Phase 5: Final Checks ⏱️ 30 minutes

### Code Quality
- [ ] Run linter (if available)
- [ ] Check for any remaining TODO comments
- [ ] Verify all imports are used
- [ ] Check for any print() statements (should use debug_print)

### Security
- [ ] Review config.py for any hardcoded secrets
- [ ] Check that database credentials are documented as "change these"
- [ ] Verify no API keys are committed

### Git Preparation
- [ ] Create .gitignore if not present
  ```
  __pycache__/
  *.pyc
  *.pyo
  *.log
  .venv/
  venv/
  *.db
  .env
  payloads.txt
  app_debug.log
  server.log
  debug.txt
  ```
- [ ] Review what files should/shouldn't be committed
- [ ] Consider adding .env.example for configuration

### Final Testing
- [ ] Fresh install test (new venv, install requirements)
- [ ] Test all main features:
  - [ ] Chat via web UI
  - [ ] Chat via webhook
  - [ ] Memory storage
  - [ ] Memory retrieval
  - [ ] Vision state (if applicable)
  - [ ] Health checks
- [ ] Check logs for any warnings or errors

---

## Phase 6: GitHub Preparation ⏱️ 30 minutes

### Repository Setup
- [ ] Create GitHub repository
- [ ] Add description and topics
- [ ] Enable issues
- [ ] Add .github/ISSUE_TEMPLATE.md (optional)

### Initial Commit
- [ ] Review all files to be committed
- [ ] Write good commit message
- [ ] Push to GitHub

### Repository Polish
- [ ] Add repository description
- [ ] Add topics/tags (python, flask, llm, memory, etc.)
- [ ] Pin important issues (if any)
- [ ] Add repository social preview image (optional)

### Documentation Links
- [ ] Verify all links in README work
- [ ] Check that code examples are correct
- [ ] Verify installation instructions

---

## Verification Checklist

### Before Publishing
- [ ] All tests pass (or are documented as broken)
- [ ] README is complete and accurate
- [ ] LICENSE file is present
- [ ] No secrets or credentials in code
- [ ] .gitignore is properly configured
- [ ] All dead code is removed
- [ ] Version comments are updated

### After Publishing
- [ ] Repository is public (or private if intended)
- [ ] README renders correctly on GitHub
- [ ] Clone repository to fresh location and test
- [ ] Installation instructions work
- [ ] Links in documentation work

---

## Estimated Total Time

| Phase | Time | Completed |
|-------|------|-----------|
| Phase 1: Safe Removals | 30 min | [ ] |
| Phase 2: Comment Fixes | 15 min | [ ] |
| Phase 3: Code Improvements | 15 min | [ ] |
| Phase 4: Documentation | 2 hours | [ ] |
| Phase 5: Final Checks | 30 min | [ ] |
| Phase 6: GitHub Prep | 30 min | [ ] |
| **TOTAL** | **~4 hours** | [ ] |

---

## Notes Section

Use this space for notes during cleanup:

```
Date Started: _______________
Date Completed: _______________

Issues Found:
-
-
-

Additional Changes Made:
-
-
-

Testing Notes:
-
-
-
```

---

## 🎉 Completion

When all items are checked:
- [ ] Review this checklist one more time
- [ ] Commit all changes
- [ ] Push to GitHub
- [ ] Share the repository!
- [ ] Celebrate! 🎊

**You did it! Your code is now GitHub-ready! 🚀**

