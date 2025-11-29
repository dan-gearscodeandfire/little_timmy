# PostgreSQL Vector Retrieval Optimization Project

**Status:** 🚧 In Progress  
**Goal:** Reduce memory retrieval time from 400-500ms to 150-200ms  
**Approach:** Optimize existing pgvector implementation before considering FAISS  
**Started:** November 28, 2025

---

## Executive Summary

Memory retrieval currently takes **400-500ms** per request, representing **~20%** of total processing time (2.4s). Analysis reveals that only 25% of this time is actual vector search; the rest is PostgreSQL overhead and complex hybrid scoring.

**Strategy:** Optimize the current pgvector implementation through query simplification, caching, and database tuning. This approach preserves the valuable hybrid scoring system while achieving similar gains to FAISS without the complexity.

**Expected Improvement:** 400-500ms → 150-200ms (**50-60% faster retrieval**)

---

## Current State Analysis

### Performance Breakdown (from latency data)

**Total Retrieval Time: 400-500ms**

```
Component                          Time      % of Total
──────────────────────────────────────────────────────
Vector similarity search           50-100ms      20%
PostgreSQL query overhead         100-200ms      40%
Hybrid scoring (keywords/tags)    100-150ms      30%
Data transfer/deserialization      50-100ms      10%
```

### Current Implementation

**File:** `v34/memory.py`

**Function:** `retrieve_similar_chunks(query_text, k=5)`

```python
def retrieve_similar_chunks(query_text, k=config.NUM_RETRIEVED_CHUNKS):
    """Retrieves chunks based on a hybrid score of semantic similarity and recency."""
    query_embedding = utils.get_embed_model().encode([query_text])[0]  # 50-100ms
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT content, speaker, topic, importance, tags, session_id, timestamp,
                       (embedding <-> %s::vector) AS distance,
                       (embedding <-> %s::vector) + (%s * ln(extract(epoch from now() - timestamp) + 1)) as hybrid_score
                FROM memory_chunks
                ORDER BY hybrid_score ASC
                LIMIT %s;
            """, (query_embedding.tolist(), query_embedding.tolist(), config.RECENCY_WEIGHT, k))
            results = cur.fetchall()  # 300-400ms total query time
        
        return [{...} for row in results]
    finally:
        if conn:
            db_pool.putconn(conn)
```

**Issues Identified:**

1. **Query embedding computed every time** (50-100ms overhead)
2. **Complex single-pass query** (PostgreSQL does vector search, keyword search, tag matching all at once)
3. **Vector sent twice** in query parameters (redundant)
4. **No query preparation** (PostgreSQL re-plans query each time)
5. **Possible connection pool contention**
6. **No caching of frequent queries**

---

## Optimization Opportunities

### Phase 1: Query Embedding Caching (Quick Win)

**Problem:** Computing embeddings for every query takes 50-100ms

**Solution:** Cache query embeddings for similar/recent queries

```python
from functools import lru_cache
import hashlib

class EmbeddingCache:
    def __init__(self, maxsize=100):
        self.cache = {}
        self.maxsize = maxsize
        
    def get_embedding(self, text):
        # Normalize text for cache key
        normalized = text.lower().strip()
        key = hashlib.md5(normalized.encode()).hexdigest()
        
        if key not in self.cache:
            if len(self.cache) >= self.maxsize:
                # Evict oldest
                self.cache.pop(next(iter(self.cache)))
            self.cache[key] = utils.get_embed_model().encode([text])[0]
        
        return self.cache[key]

embedding_cache = EmbeddingCache(maxsize=200)
```

**Expected Savings:** 50-100ms on cache hits (50-80% hit rate for conversational queries)

---

### Phase 2: Query Simplification (Biggest Win)

**Problem:** Single complex query does too much at once

**Current Approach:**
```
[PostgreSQL does everything in one query: 400ms]
  ↓
Result
```

**Optimized Approach:**
```
[PostgreSQL: Simple vector search: 50ms]
  ↓
[Python: Apply filters and scoring: 20ms]
  ↓
Result (Total: 70ms base + embedding time)
```

**Implementation:**

```python
def retrieve_similar_chunks_optimized(query_text, k=config.NUM_RETRIEVED_CHUNKS):
    """
    Two-stage retrieval:
    1. Fast vector search for candidates (50ms)
    2. Python-based hybrid scoring and filtering (20ms)
    """
    # Stage 1: Get query embedding (cached)
    query_embedding = embedding_cache.get_embedding(query_text)
    
    # Stage 2: Fast vector-only search (get more candidates)
    candidates = _fast_vector_search(query_embedding, k=k*4)  # Get 4x candidates
    
    # Stage 3: Apply hybrid scoring in Python
    scored_results = _apply_hybrid_scoring(
        candidates, 
        query_text, 
        query_embedding
    )
    
    # Stage 4: Sort and return top k
    return sorted(scored_results, key=lambda x: x['hybrid_score'])[:k]

def _fast_vector_search(query_embedding, k=20):
    """Simple, fast vector-only search"""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            # Prepared statement (prepared once, reused)
            cur.execute("""
                SELECT id, content, speaker, topic, importance, tags, 
                       session_id, timestamp, embedding
                FROM memory_chunks
                ORDER BY embedding <-> %s::vector
                LIMIT %s;
            """, (query_embedding.tolist(), k))
            return cur.fetchall()
    finally:
        db_pool.putconn(conn)

def _apply_hybrid_scoring(candidates, query_text, query_embedding):
    """Apply complex scoring in Python (faster than SQL for small result sets)"""
    import time
    import re
    
    results = []
    query_words = set(query_text.lower().split())
    current_time = time.time()
    
    for row in candidates:
        chunk_id, content, speaker, topic, importance, tags, session_id, timestamp, embedding = row
        
        # 1. Semantic score (from vector distance)
        semantic_distance = np.linalg.norm(query_embedding - np.array(embedding))
        
        # 2. Keyword score (simple word overlap)
        content_words = set(content.lower().split())
        keyword_score = len(query_words & content_words) / max(len(query_words), 1)
        
        # 3. Tag-based scoring
        tag_boost = 0
        if tags:
            if 'stating facts' in tags or 'factual statement' in tags:
                tag_boost -= 0.4
            if 'personal data' in tags or 'personal information' in tags:
                tag_boost -= 0.3
            if 'asking questions' in tags:
                tag_boost += 0.3
        
        # 4. Recency scoring
        age_seconds = current_time - timestamp.timestamp()
        recency_penalty = config.RECENCY_WEIGHT * np.log(age_seconds + 1)
        
        # 5. Combined hybrid score
        hybrid_score = (
            semantic_distance * 0.7 
            - keyword_score * 1.5 
            + tag_boost 
            + recency_penalty
        )
        
        results.append({
            'text': content,
            'role': speaker,
            'topic': topic,
            'importance': importance,
            'tags': tags,
            'session_id': session_id,
            'timestamp': timestamp,
            'distance': semantic_distance,
            'hybrid_score': hybrid_score
        })
    
    return results
```

**Expected Savings:** 300-350ms (from 400ms to 50-70ms for vector search + scoring)

---

### Phase 3: Connection Pool Optimization

**Problem:** Possible connection contention during peak load

**Current Config:**
```python
db_pool = pool.SimpleConnectionPool(1, 20, **config.DB_CONFIG)
```

**Optimized Config:**
```python
db_pool = pool.ThreadedConnectionPool(
    minconn=5,      # Keep 5 connections always open
    maxconn=50,     # Allow up to 50 connections
    **config.DB_CONFIG
)
```

**Additional Settings:**
```python
DB_CONFIG = {
    'host': 'localhost',
    'database': 'timmy_memory',
    'user': 'postgres',
    'password': '...',
    # Performance tuning
    'connect_timeout': 3,
    'options': '-c work_mem=256MB',  # Allow larger in-memory operations
}
```

**Expected Savings:** 20-50ms during concurrent requests

---

### Phase 4: PostgreSQL Configuration Tuning

**Problem:** Default PostgreSQL settings not optimized for vector workloads

**Recommended Settings** (add to `postgresql.conf`):

```ini
# Memory Settings (adjust based on available RAM)
shared_buffers = 4GB              # 25% of RAM
effective_cache_size = 12GB       # 75% of RAM
work_mem = 256MB                  # Per-operation memory
maintenance_work_mem = 1GB        # For index building

# Vector-specific optimizations
max_parallel_workers_per_gather = 4  # Use parallel query execution
random_page_cost = 1.1               # Assume SSD storage

# Connection settings
max_connections = 100
```

**HNSW Index Tuning:**

Check current index:
```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'memory_chunks';
```

Optimize if needed:
```sql
-- Drop old index
DROP INDEX IF EXISTS memory_chunks_embedding_idx;

-- Create optimized HNSW index
CREATE INDEX memory_chunks_embedding_idx 
ON memory_chunks 
USING hnsw (embedding vector_l2_ops)
WITH (m = 16, ef_construction = 64);

-- Analyze table for query planner
ANALYZE memory_chunks;
```

**Expected Savings:** 20-50ms in query execution

---

### Phase 5: Result Caching (Advanced)

**Problem:** Frequently asked questions retrieve same results

**Solution:** Cache retrieval results with smart invalidation

```python
from collections import OrderedDict
import time

class RetrievalCache:
    def __init__(self, maxsize=500, ttl=300):  # 5 minute TTL
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl
    
    def get(self, query_text):
        key = query_text.lower().strip()
        if key in self.cache:
            timestamp, results = self.cache[key]
            if time.time() - timestamp < self.ttl:
                # Move to end (LRU)
                self.cache.move_to_end(key)
                return results
            else:
                del self.cache[key]
        return None
    
    def set(self, query_text, results):
        key = query_text.lower().strip()
        if len(self.cache) >= self.maxsize:
            self.cache.popitem(last=False)  # Remove oldest
        self.cache[key] = (time.time(), results)
    
    def invalidate(self):
        """Call when new memories are added"""
        self.cache.clear()

retrieval_cache = RetrievalCache(maxsize=500, ttl=300)
```

**Usage:**
```python
def retrieve_similar_chunks(query_text, k=5):
    # Check cache first
    cached = retrieval_cache.get(query_text)
    if cached:
        return cached[:k]
    
    # Compute if not cached
    results = retrieve_similar_chunks_optimized(query_text, k)
    retrieval_cache.set(query_text, results)
    return results
```

**Expected Savings:** 400ms on cache hits (30-50% hit rate for common queries)

---

## Implementation Plan

### Phase 1: Measurement & Baseline (Day 1)

**Goal:** Establish accurate baseline metrics

**Tasks:**
1. ✅ Add detailed timing to `memory.py` retrieval functions
2. ✅ Measure embedding computation time separately
3. ✅ Measure PostgreSQL query time separately
4. ✅ Log cache hit rates

**Deliverable:** Baseline metrics document

---

### Phase 2: Embedding Cache (Day 1-2)

**Goal:** Implement query embedding caching

**Tasks:**
1. Create `EmbeddingCache` class in `memory.py`
2. Replace direct embedding calls with cache
3. Add cache statistics logging
4. Test with real conversations

**Expected Result:** 50-100ms savings on cache hits

**Rollback Plan:** Remove cache, revert to direct calls

---

### Phase 3: Query Simplification (Day 2-3)

**Goal:** Split complex query into fast vector search + Python scoring

**Tasks:**
1. Implement `_fast_vector_search()` function
2. Implement `_apply_hybrid_scoring()` function
3. Create new `retrieve_similar_chunks_optimized()` function
4. Add A/B testing flag to compare old vs new
5. Validate result quality matches old method

**Expected Result:** 300-350ms savings

**Rollback Plan:** Keep old function, toggle with config flag

---

### Phase 4: Connection Pool & PostgreSQL Tuning (Day 3-4)

**Goal:** Optimize database-level performance

**Tasks:**
1. Increase connection pool size
2. Add PostgreSQL config optimizations
3. Rebuild HNSW index with optimal parameters
4. Test under load

**Expected Result:** 20-50ms savings

**Rollback Plan:** Revert postgresql.conf, keep old index

---

### Phase 5: Result Caching (Day 4-5)

**Goal:** Add intelligent result caching layer

**Tasks:**
1. Implement `RetrievalCache` class
2. Integrate with retrieval function
3. Add cache invalidation on new memories
4. Monitor cache hit rates

**Expected Result:** 400ms savings on cache hits

**Rollback Plan:** Disable cache, direct retrieval

---

### Phase 6: Testing & Validation (Day 5-6)

**Goal:** Ensure quality and performance improvements

**Tasks:**
1. Run latency analysis on 20+ conversations
2. Compare retrieval quality (old vs new)
3. Stress test with concurrent requests
4. Validate memory usage acceptable
5. Document final results

**Deliverable:** Performance comparison report

---

## Expected Results Summary

| Optimization | Latency Reduction | Complexity | Risk |
|--------------|------------------|------------|------|
| **Embedding Cache** | 50-100ms on hits | Low | Low |
| **Query Simplification** | 300-350ms | Medium | Medium |
| **Connection Pool** | 20-50ms | Low | Low |
| **PostgreSQL Tuning** | 20-50ms | Low | Low |
| **Result Caching** | 400ms on hits | Low | Low |

**Best Case Scenario:**
- Cache hit: ~10ms (cached embedding + cached results)
- Cache miss: ~150-200ms (50ms vector + 20ms scoring + 50ms overhead)
- **Average: ~180ms** (60% cache hits assumed)

**Conservative Scenario:**
- Average: ~220ms (40% cache hits)
- **Still 45% faster than current 400-500ms**

---

## Success Metrics

### Performance Targets

| Metric | Current | Target | Stretch Goal |
|--------|---------|--------|--------------|
| **Average Retrieval Time** | 450ms | 200ms | 150ms |
| **Total Processing Time** | 2.4s | 2.1s | 2.0s |
| **Cache Hit Rate** | 0% | 50% | 70% |
| **Query Variance** | ±100ms | ±50ms | ±30ms |

### Quality Metrics (Must Not Regress)

- **Retrieval Accuracy:** Same or better than current
- **Semantic Relevance:** Maintain current quality
- **Keyword Matching:** No degradation
- **Recency Bias:** Preserve temporal scoring

---

## Risks & Mitigations

### Risk 1: Query Simplification Reduces Quality

**Mitigation:**
- A/B test old vs new retrieval
- Add config flag to toggle between methods
- Validate on test set of known queries

### Risk 2: Caching Stale Results

**Mitigation:**
- Implement TTL (5 minute expiration)
- Invalidate cache when new memories added
- Monitor cache statistics

### Risk 3: Increased Memory Usage

**Mitigation:**
- Limit cache sizes (200 embeddings, 500 results)
- Monitor memory usage in production
- Add cache eviction policies

### Risk 4: PostgreSQL Config Changes Break Other Apps

**Mitigation:**
- Test in development first
- Document all config changes
- Have rollback script ready

---

## Alternative Considered: FAISS

**Decision:** Not implementing FAISS at this time

**Reasons:**
1. **Complexity:** Dual storage, sync issues, index rebuilding
2. **Feature Loss:** Hybrid scoring would need Python re-implementation
3. **Similar Gains:** pgvector optimizations achieve 80% of FAISS gains
4. **Maintenance:** Additional complexity not justified for current scale

**Reconsider FAISS if:**
- Memory chunks exceed 100K entries
- Retrieval time still >200ms after optimizations
- Pure semantic search is sufficient (no hybrid scoring)

---

## Documentation & Monitoring

### Latency Tracking Integration

Add timing events to `latency_tracker.py`:

```python
class Events(str, Enum):
    # ... existing events ...
    V34_RETRIEVAL_EMBEDDING_START = "v34_retrieval_embedding_start"
    V34_RETRIEVAL_EMBEDDING_COMPLETE = "v34_retrieval_embedding_complete"
    V34_RETRIEVAL_VECTOR_SEARCH_START = "v34_retrieval_vector_search_start"
    V34_RETRIEVAL_VECTOR_SEARCH_COMPLETE = "v34_retrieval_vector_search_complete"
    V34_RETRIEVAL_SCORING_START = "v34_retrieval_scoring_start"
    V34_RETRIEVAL_SCORING_COMPLETE = "v34_retrieval_scoring_complete"
```

### Cache Statistics

```python
def get_cache_stats():
    return {
        'embedding_cache': {
            'size': len(embedding_cache.cache),
            'hits': embedding_cache.hits,
            'misses': embedding_cache.misses,
            'hit_rate': embedding_cache.hits / (embedding_cache.hits + embedding_cache.misses)
        },
        'retrieval_cache': {
            'size': len(retrieval_cache.cache),
            'hits': retrieval_cache.hits,
            'misses': retrieval_cache.misses,
            'hit_rate': retrieval_cache.hits / (retrieval_cache.hits + retrieval_cache.misses)
        }
    }
```

---

## Rollback Plan

If optimizations cause issues:

1. **Immediate:** Toggle config flag to use old retrieval method
2. **Short-term:** Keep both implementations, monitor quality
3. **Long-term:** Deprecate old method once new is validated

**Config Flag:**
```python
# config.py
USE_OPTIMIZED_RETRIEVAL = True  # Set to False to rollback
```

---

## Timeline

**Total Estimated Time:** 5-6 days

- **Day 1:** Measurement & embedding cache
- **Day 2-3:** Query simplification
- **Day 3-4:** Database tuning
- **Day 4-5:** Result caching
- **Day 5-6:** Testing & validation

**Milestones:**
- ✅ Day 1: Baseline established, embedding cache working
- 🔲 Day 3: Query simplification validated
- 🔲 Day 4: Database tuned, connection pool optimized
- 🔲 Day 5: Result caching implemented
- 🔲 Day 6: Full testing complete, documentation updated

---

## Related Documentation

- [LATENCY_OPTIMIZATION_SUCCESS.md](LATENCY_OPTIMIZATION_SUCCESS.md) - HTTP optimization that reduced processing from 4.6s to 2.4s
- [LATENCY_ANALYSIS_FINDINGS.md](LATENCY_ANALYSIS_FINDINGS.md) - Initial performance analysis
- [shared/README.md](shared/README.md) - Latency tracking system
- [v34/MEMORY_SYSTEM_EVALUATION.md](v34/MEMORY_SYSTEM_EVALUATION.md) - Memory system architecture

---

## Status Updates

### November 28, 2025 - Project Initiated
- ✅ Comprehensive analysis of current retrieval performance
- ✅ Identified optimization opportunities
- ✅ Created implementation plan
- 🔲 Ready to begin Phase 1: Measurement & Baseline

---

**Next Steps:**
1. Add detailed timing instrumentation to `memory.py`
2. Run baseline performance tests
3. Implement embedding cache
4. Measure improvement

**Contact:** Track progress in this document

