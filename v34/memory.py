# v34/memory.py
# adding fast_generate_metadata with a classifier

# --- SQL Commands for Parent Document Retrieval ---
# You must run these commands against your PostgreSQL database to enable this feature.
#
# -- 1. Create the new parent_documents table
# CREATE TABLE parent_documents (
#     id SERIAL PRIMARY KEY,
#     session_id VARCHAR(255),
#     speaker VARCHAR(50),
#     full_text TEXT NOT NULL,
#     summary TEXT,
#     summary_embedding VECTOR(384),
#     timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
# );
#
# -- 2. Add an index for faster lookups on summary embeddings
# CREATE INDEX ON parent_documents USING HNSW (summary_embedding vector_l2_ops);
#
# -- 3. Add a column to memory_chunks to link back to the parent
# ALTER TABLE memory_chunks ADD COLUMN parent_id INTEGER;
#
# -- 4. Add a foreign key constraint
# ALTER TABLE memory_chunks
# ADD CONSTRAINT fk_parent_document
# FOREIGN KEY (parent_id) REFERENCES parent_documents(id)
# ON DELETE CASCADE;
#
# -- 5. Add an index for the new foreign key column
# CREATE INDEX ON memory_chunks (parent_id);
# ---

from psycopg2 import pool
import numpy as np
import difflib
import nltk

import config
import utils
import llm

# --- Database Pool Management ---

db_pool = None

def init_db_pool():
    """Initializes the database connection pool."""
    global db_pool
    if not db_pool:
        utils.debug_print("*** Debug: Initializing database connection pool.")
        db_pool = pool.SimpleConnectionPool(1, 20, **config.DB_CONFIG)

def close_db_pool():
    """Closes all connections in the pool."""
    global db_pool
    if db_pool:
        utils.debug_print("*** Debug: Closing database connection pool.")
        db_pool.closeall()
        db_pool = None

# --- Memory Chunking and Storage ---

def insert_parent_document(full_text, summary, summary_embedding, role, session_id):
    """Inserts a parent document and returns its new ID."""
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO parent_documents (full_text, summary, summary_embedding, speaker, session_id)
                VALUES (%s, %s, %s, %s, %s) RETURNING id;
            """, (full_text, summary, summary_embedding.tolist(), role, session_id))
            parent_id = cur.fetchone()[0]
        conn.commit()
        return parent_id
    finally:
        if conn:
            db_pool.putconn(conn)

def chunk_and_store_text(text: str, role: str, metadata=None, session_id=None):
    """
    Summarizes text, stores the parent document, then splits the text into
    semantically coherent, overlapping chunks and stores them linked to the parent.
    """
    utils.debug_print(f"*** Debug: Parent Document Ingestion for role={role}...")

    # 1. Generate summary and its embedding
    summary = llm.fast_generate_summary(text)
    summary_embedding = utils.get_embed_model().encode([summary])[0]

    # 2. Store the parent document and get its ID
    parent_id = insert_parent_document(
        full_text=text,
        summary=summary,
        summary_embedding=summary_embedding,
        role=role,
        session_id=session_id
    )
    utils.debug_print(f"*** Debug: Stored parent document with ID: {parent_id}")

    # 3. Chunk the original text
    sentences = nltk.sent_tokenize(text)
    if not sentences:
        return

    chunks = []
    current_chunk_sentences = []
    current_length = 0
    i = 0
    while i < len(sentences):
        sentence = sentences[i]
        if current_length + len(sentence) <= config.MAX_CHUNK_SIZE:
            current_chunk_sentences.append(sentence)
            current_length += len(sentence)
            i += 1
        else:
            chunks.append(" ".join(current_chunk_sentences))
            if len(current_chunk_sentences) > config.OVERLAP_SENTENCES:
                 i = i - config.OVERLAP_SENTENCES
            current_chunk_sentences = []
            current_length = 0

    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))

    if not chunks:
        return

    # 4. Embed chunks and store them with the parent ID
    embeddings = utils.get_embed_model().encode(chunks)
    for chunk_text, emb in zip(chunks, embeddings):
        # Use fast classifier-based metadata generation (fallback if metadata not provided)
        chunk_metadata = metadata or llm.fast_generate_metadata(chunk_text)
        insert_chunk_to_postgres(
            text=chunk_text, role=role, embedding=np.array(emb),
            topic=chunk_metadata.get("topic"), importance=chunk_metadata.get("importance", 0),
            tags=chunk_metadata.get("tags", []), session_id=session_id,
            parent_id=parent_id
        )
    utils.debug_print(f"*** Debug: Stored {len(chunks)} chunks linked to parent {parent_id}.")

def insert_chunk_to_postgres(text, role, embedding, topic, importance, tags, session_id, parent_id):
    """Inserts a single memory chunk into the database, linked to a parent."""
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO memory_chunks (embedding, content, speaker, topic, importance, tags, session_id, parent_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, (embedding.tolist(), text, role, topic, importance, tags, session_id, parent_id))
        conn.commit()
    finally:
        if conn:
            db_pool.putconn(conn)

# --- Memory Retrieval ---

def retrieve_similar_chunks(query_text, k=config.NUM_RETRIEVED_CHUNKS):
    """Retrieves chunks based on a hybrid score of semantic similarity and recency."""
    query_embedding = utils.get_embed_model().encode([query_text])[0]
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
            results = cur.fetchall()
        
        return [{
            "text": row[0], "role": row[1], "topic": row[2], "importance": row[3],
            "tags": row[4], "session_id": row[5], "timestamp": row[6],
            "distance": row[7], "hybrid_score": row[8]
        } for row in results]
    finally:
        if conn:
            db_pool.putconn(conn)

def retrieve_relevant_parent_ids(query_embedding, k=5):
    """Retrieves the IDs of the most relevant parent documents based on summary similarity."""
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM parent_documents
                ORDER BY summary_embedding <-> %s::vector ASC
                LIMIT %s;
            """, (query_embedding.tolist(), k))
            return [row[0] for row in cur.fetchall()]
    finally:
        if conn:
            db_pool.putconn(conn)

def retrieve_similar_chunks_from_parents(query_embedding, parent_ids, k=config.NUM_RETRIEVED_CHUNKS, query_text=""):
    """
    Retrieves chunks from a specific set of parent documents,
    using hybrid semantic + keyword search with recency weighting.
    """
    if not parent_ids:
        return []

    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            # Hybrid search: combine vector similarity + full-text search + recency + tag-based scoring
            cur.execute("""
                SELECT content, speaker, topic, importance, tags, session_id, timestamp,
                       (embedding <-> %s::vector) AS semantic_distance,
                       ts_rank(to_tsvector('english', content), plainto_tsquery('english', %s)) AS keyword_score,
                       (
                         -- Semantic component (lower distance = better)
                         (embedding <-> %s::vector) * 0.7 
                         -- Keyword component (higher rank = better, so subtract from penalty)
                         - (ts_rank(to_tsvector('english', content), plainto_tsquery('english', %s)) * 1.5)
                         -- Tag-based scoring (boost facts, penalize questions)
                         + CASE 
                             WHEN 'stating facts' = ANY(tags) OR 'factual statement' = ANY(tags) THEN -0.4
                             WHEN 'personal data' = ANY(tags) OR 'personal information' = ANY(tags) THEN -0.3  
                             WHEN 'asking questions' = ANY(tags) OR 'question about facts' = ANY(tags) THEN +0.3
                             WHEN 'testing memory' = ANY(tags) OR 'memory test' = ANY(tags) THEN +0.5
                             ELSE 0
                           END
                         -- Recency component  
                         + (%s * ln(extract(epoch from now() - timestamp) + 1))
                       ) as hybrid_score
                FROM memory_chunks
                WHERE parent_id = ANY(%s)
                  AND (
                    (embedding <-> %s::vector) < 1.0  -- Semantic threshold (tightened from 1.5 for better precision)
                    OR 
                    ts_rank(to_tsvector('english', content), plainto_tsquery('english', %s)) > 0  -- Has keyword match
                  )
                ORDER BY hybrid_score ASC
                LIMIT %s;
            """, (
                query_embedding.tolist(), query_text, query_embedding.tolist(), query_text, 
                config.RECENCY_WEIGHT, parent_ids, query_embedding.tolist(), query_text, k
            ))
            results = cur.fetchall()

        return [{
            "text": row[0], "role": row[1], "topic": row[2], "importance": row[3],
            "tags": row[4], "session_id": row[5], "timestamp": row[6],
            "distance": row[7], "keyword_score": row[8], "hybrid_score": row[9]
        } for row in results]
    finally:
        if conn:
            db_pool.putconn(conn)

def get_recent_memories(session_id, limit=20):
    """Retrieves the most recent memory chunks for a given session."""
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT content, speaker, topic, importance, tags, timestamp 
                FROM memory_chunks 
                WHERE session_id = %s 
                ORDER BY timestamp DESC 
                LIMIT %s;
            """, (session_id, limit))
            rows = cur.fetchall()
        return [{
            "text": r[0], "role": r[1], "topic": r[2], "importance": r[3], 
            "tags": r[4], "timestamp": r[5].isoformat() if r[5] else None
        } for r in rows]
    finally:
        if conn:
            db_pool.putconn(conn)

def is_duplicate_chunk(candidate_text: str, history, threshold=0.8):
    """Checks if a candidate chunk is too similar to recent conversation history."""
    for entry in history:
        ratio = difflib.SequenceMatcher(None, candidate_text, entry["content"]).ratio()
        if ratio >= threshold:
            utils.debug_print(f"*** Debug: Skipping duplicate chunk (similarity: {ratio:.2f})")
            return True
    return False

def retrieve_unique_relevant_chunks(query: str, k: int = config.NUM_RETRIEVED_CHUNKS):
    """
    Fetches relevant chunks using the Parent Document Retrieval method.
    1. Find relevant parent documents based on summary similarity.
    2. Find the best chunks within those parent documents.
    3. Filter out chunks that are too similar to recent conversation history.
    """
    utils.debug_print("*** Debug: Retrieving chunks via Parent Document method...")
    query_embedding = utils.get_embed_model().encode([query])[0]

    # Step 1: Find relevant parent documents. Over-fetch to cast a wider net.
    parent_ids = retrieve_relevant_parent_ids(query_embedding, k=k * 2)
    utils.debug_print(f"*** Debug: Found {len(parent_ids)} relevant parent document IDs.")
    if not parent_ids:
        return []

    # Step 2: Retrieve the best chunks from within that set of parents.
    # Over-fetch again to have more candidates for the final uniqueness filter.
    retrieved_chunks = retrieve_similar_chunks_from_parents(query_embedding, parent_ids, k=k * 2, query_text=query)
    utils.debug_print(f"*** Debug: Retrieved {len(retrieved_chunks)} candidate chunks from parents.")

    # Step 3: Filter for uniqueness against recent history AND other retrieved chunks.
    unique_chunks = []
    for chunk in retrieved_chunks:
        # Check against conversation history
        if is_duplicate_chunk(chunk["text"], utils.conversation_history):
            continue
        
        # Check against already-selected chunks (cross-chunk deduplication)
        is_duplicate_of_selected = False
        for selected in unique_chunks:
            ratio = difflib.SequenceMatcher(None, chunk["text"], selected["text"]).ratio()
            if ratio >= 0.75:  # Balanced threshold - catches similar but not semantically different
                utils.debug_print(f"*** Debug: Skipping duplicate chunk (similarity to selected: {ratio:.2f})")
                is_duplicate_of_selected = True
                break
        
        if not is_duplicate_of_selected:
            unique_chunks.append(chunk)

    utils.debug_print(f"*** Debug: Returning {len(unique_chunks[:k])} unique, relevant chunks.")
    return unique_chunks[:k] 

# --- Memory Pruning and Cleanup ---

def prune_test_memories():
    """Remove test, meta, and low-value chunks that pollute retrieval."""
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            # Delete test/meta chunks
            cur.execute("""
                DELETE FROM memory_chunks 
                WHERE 
                    content ILIKE '%test%' 
                    OR content ILIKE '%testing%'
                    OR content ILIKE '%memory%test%'
                    OR content ILIKE '%retrieval%test%'
                    OR topic = 'meta'
                    OR topic = 'testing'
                    OR 'testing' = ANY(tags)
                    OR 'meta' = ANY(tags)
                    OR (importance <= 1 AND topic = 'greetings')  -- Remove low-value greetings
                    OR content IN ('Hello', 'Hi', 'Test', 'test');
            """)
            deleted_chunks = cur.rowcount
            
            # Also clean up parent documents that are now empty or test-related
            cur.execute("""
                DELETE FROM parent_documents 
                WHERE 
                    full_text ILIKE '%test%'
                    OR full_text ILIKE '%testing%'
                    OR summary ILIKE '%test%'
                    OR id NOT IN (SELECT DISTINCT parent_id FROM memory_chunks WHERE parent_id IS NOT NULL);
            """)
            deleted_parents = cur.rowcount
            
        conn.commit()
        utils.debug_print(f"*** Debug: Pruned {deleted_chunks} test chunks and {deleted_parents} parent documents")
        return deleted_chunks, deleted_parents
    finally:
        if conn:
            db_pool.putconn(conn)

def prune_old_low_importance_memories(days_old=30, max_importance=1):
    """Remove old, low-importance chunks to prevent memory bloat."""
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM memory_chunks 
                WHERE 
                    importance <= %s 
                    AND timestamp < NOW() - INTERVAL '%s days'
                    AND topic IN ('greetings', 'small_talk', 'meta');
            """, (max_importance, days_old))
            deleted_count = cur.rowcount
        conn.commit()
        utils.debug_print(f"*** Debug: Pruned {deleted_count} old low-importance chunks")
        return deleted_count
    finally:
        if conn:
            db_pool.putconn(conn) 