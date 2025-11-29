# pgvector Optimization - Restore Point

**Created:** November 28, 2025  
**Git Commit:** `006f731` - "Start pgvector optimization project"  
**Purpose:** Checkpoint before implementing pgvector optimizations

---

## How to Restore

If optimizations cause issues, restore to this state:

### Quick Rollback (Keep new code, use old behavior)

```python
# In v34/config.py, add:
USE_OPTIMIZED_RETRIEVAL = False  # Toggle to revert to old retrieval method
```

### Full Rollback (Revert all changes)

```bash
cd ~/timmy-backend/little-timmy
git reset --hard 006f731
git push origin main --force  # Only if already pushed problematic changes
```

---

## System State at Checkpoint

### Performance Metrics (Baseline)

**Total Processing Time:** 2.4s average (excluding audio playback)

**Breakdown:**
- STT Finalization: 5-6ms
- HTTP (STT→v34): 6ms
- Classification: 32-36ms
- **Vector Retrieval: 400-500ms** ← Target for optimization
- Ollama LLM: 600-850ms
- TTS Synthesis: 650-700ms
- Other: ~300ms

**Vector Retrieval Detail (estimated):**
- Embedding computation: 50-100ms
- PostgreSQL query: 300-400ms
  - Vector search: 50-100ms
  - Hybrid scoring: 100-150ms
  - Overhead: 100-200ms

### File Versions

**Key Files Before Optimization:**

#### `v34/memory.py` (Line count: ~620 lines)
- `retrieve_similar_chunks()` - Current implementation
- Uses single complex SQL query with hybrid scoring
- No caching of embeddings or results
- Connection pool: SimpleConnectionPool(1, 20)

#### `v34/config.py`
```python
RECENCY_WEIGHT = 0.75
NUM_RETRIEVED_CHUNKS = 5
```

#### `v34/utils.py`
```python
embed_model = None
dimension = 384
# Model: sentence-transformers/all-MiniLM-L6-v2
```

#### `v34/app.py`
- `process_user_message()` calls `memory.retrieve_similar_chunks()`
- Latency tracking integrated

---

## Database State

### PostgreSQL Configuration
**Location:** `/etc/postgresql/*/main/postgresql.conf` (exact path may vary)

**Default Settings (before tuning):**
```ini
shared_buffers = 128MB
effective_cache_size = 4GB
work_mem = 4MB
maintenance_work_mem = 64MB
max_connections = 100
```

### Current Indexes

```sql
-- Check with:
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'memory_chunks';
```

**Expected Output:**
- `memory_chunks_embedding_idx` using HNSW

### Table Schema

```sql
-- memory_chunks table
CREATE TABLE memory_chunks (
    id SERIAL PRIMARY KEY,
    content TEXT,
    speaker VARCHAR(50),
    embedding VECTOR(384),
    topic TEXT,
    importance INTEGER,
    tags TEXT[],
    session_id VARCHAR(255),
    timestamp TIMESTAMPTZ,
    parent_id INTEGER
);
```

---

## Optimization Changes Made

### Phase 1: Measurement & Baseline (Current Phase)

**Status:** 🚧 In Progress

**Changes:**
- Added detailed timing to `memory.py`
- Added timing events to `latency_tracker.py`

**Files Modified:**
- `v34/memory.py` - Added timing instrumentation
- `shared/latency_tracker.py` - Added retrieval timing events

**Rollback:** These are measurement-only changes, safe to keep

---

### Phase 2: Embedding Cache (Not Yet Started)

**Status:** 🔲 Not Started

**Planned Changes:**
- Add `EmbeddingCache` class to `memory.py`
- Wrap embedding calls with cache

**Rollback:** Set `USE_EMBEDDING_CACHE = False` in config

---

### Phase 3: Query Simplification (Not Yet Started)

**Status:** 🔲 Not Started

**Planned Changes:**
- Add `retrieve_similar_chunks_optimized()` function
- Split complex query into vector search + Python scoring

**Rollback:** Set `USE_OPTIMIZED_RETRIEVAL = False` in config

---

### Phase 4: Connection Pool (Not Yet Started)

**Status:** 🔲 Not Started

**Planned Changes:**
- Upgrade to ThreadedConnectionPool
- Increase max connections to 50

**Rollback:** Revert to SimpleConnectionPool(1, 20)

---

### Phase 5: PostgreSQL Tuning (Not Yet Started)

**Status:** 🔲 Not Started

**Planned Changes:**
- Modify `postgresql.conf`
- Rebuild HNSW index with optimal parameters

**Rollback:** Restore postgresql.conf, rebuild index with old params

---

### Phase 6: Result Caching (Not Yet Started)

**Status:** 🔲 Not Started

**Planned Changes:**
- Add `RetrievalCache` class
- Cache query results

**Rollback:** Set `USE_RESULT_CACHE = False` in config

---

## Testing Checklist Before Each Phase

Before implementing each optimization phase:

- [ ] Current system is stable and working
- [ ] Baseline metrics are documented
- [ ] Backup of files to be modified exists
- [ ] Rollback plan is clear
- [ ] Testing strategy is defined

After implementing each optimization phase:

- [ ] Code changes are committed to git
- [ ] Performance improvement is measured
- [ ] Quality validation passes (retrieval results are correct)
- [ ] No regressions in other components
- [ ] Documentation is updated

---

## Quality Validation Tests

Run these tests to ensure retrieval quality hasn't degraded:

### Test 1: Exact Match Query
```
Query: "Winston"
Expected: Should return chunks mentioning cat named Winston
```

### Test 2: Semantic Query
```
Query: "What pet does Dan have?"
Expected: Should return chunks about Winston (cat)
```

### Test 3: Recent Memory Priority
```
Query: Recent conversation topic
Expected: Should prioritize recent chunks over old ones
```

### Test 4: Keyword Emphasis
```
Query: Specific technical term (e.g., "GLiClass")
Expected: Should find chunks with exact keyword matches
```

### Test 5: Tag-Based Filtering
```
Query: Factual question
Expected: Should prioritize chunks tagged as 'stating facts'
```

---

## Performance Regression Criteria

Abort optimization if any of these occur:

1. **Total processing time increases** (currently 2.4s)
2. **Retrieval quality degrades** (wrong results returned)
3. **System becomes unstable** (crashes, errors)
4. **Memory usage exceeds** 2GB for v34 process
5. **Database connection issues** emerge

---

## Contact & Escalation

If issues arise:

1. **Immediate:** Set rollback flags in `config.py`
2. **Short-term:** Revert to this git commit
3. **Long-term:** Review `PGVECTOR_OPTIMIZATION.md` for detailed troubleshooting

---

## Version Information

**Python:** 3.x (in WSL venv: ~/timmy-backend/.venv)  
**PostgreSQL:** 12+ with pgvector extension  
**Sentence Transformers:** all-MiniLM-L6-v2 (384 dimensions)  
**Dependencies:** See `requirements.txt`

---

## Backup Files

Before modifying files, create backups:

```bash
cd ~/timmy-backend/little-timmy/v34
cp memory.py memory.py.backup_20251128
cp config.py config.py.backup_20251128
cp app.py app.py.backup_20251128
```

Restore if needed:
```bash
cp memory.py.backup_20251128 memory.py
```

---

## Git History

**Pre-optimization commits:**
- `2734b05` - Document complete latency optimization (HTTP pooling)
- `a0ab906` - Add connection pooling to TTS and v34
- `4354103` - Optimize HTTP latency with connection pooling (STT)
- `bc0d4dc` - Fix UnboundLocalError in transcribe_audio
- Previous commits... (see git log)

**Restore point:**
- `006f731` - Start pgvector optimization project ← **YOU ARE HERE**

---

## System Dependencies

Ensure these are installed and working:

```bash
# PostgreSQL with pgvector
psql --version  # Should show 12+
psql -c "SELECT * FROM pg_extension WHERE extname='vector';"  # Should show pgvector

# Python packages (in venv)
source ~/timmy-backend/.venv/bin/activate
pip list | grep -E "psycopg2|sentence-transformers|numpy"
```

---

## Success Criteria for Completion

Optimization is successful when:

1. ✅ **Performance:** Retrieval time reduced from 450ms to <200ms
2. ✅ **Quality:** All validation tests pass with correct results
3. ✅ **Stability:** System runs for 24 hours without issues
4. ✅ **Documentation:** All changes documented in code and markdown
5. ✅ **Rollback:** Tested rollback procedure works correctly

---

**Note:** This restore point is valid until the next major architectural change. Update this document if system architecture changes significantly.

**Last Updated:** November 28, 2025  
**Status:** ✅ Safe restore point established

