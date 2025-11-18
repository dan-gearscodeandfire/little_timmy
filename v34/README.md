# Little Timmy - AI Assistant with Persistent Memory

A Flask-based AI assistant with vector memory, real-time chat, and personality. Features conversation history with semantic search, parent-document retrieval, and KV cache optimization for efficient LLM interactions.

## Features

- 🧠 **Persistent Vector Memory** - PostgreSQL + pgvector for semantic memory storage and retrieval
- 💬 **Real-time Chat** - WebSocket-based chat interface with Flask-SocketIO
- 🎯 **Smart Classification** - GLiClass-based fast metadata generation for importance scoring
- 📝 **Parent Document Retrieval** - Hierarchical memory with summarization for better context
- ⚡ **KV Cache Optimization** - Efficient prompt caching with Ollama's generate endpoint
- 👁️ **Vision Integration** - Camera observation tracking with face recognition support
- 🔄 **Megaprompt Strategy** - Flexible prompt building with ephemeral system prompts

## Architecture

```
┌─────────────────┐
│   Web UI/API    │  ← Flask + SocketIO
└────────┬────────┘
         │
    ┌────▼─────┐
    │  app.py  │  ← Main application
    └────┬─────┘
         │
    ┌────▼──────────────────────────┐
    │  Core Modules                 │
    ├───────────────────────────────┤
    │  llm.py      - LLM interaction│
    │  memory.py   - Vector storage │
    │  utils.py    - Utilities      │
    │  vision.py   - Vision state   │
    │  config.py   - Configuration  │
    └───────────────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │  External Services            │
    ├───────────────────────────────┤
    │  Ollama (LLM)                 │
    │  PostgreSQL + pgvector        │
    │  TTS/STT Servers (optional)   │
    └───────────────────────────────┘
```

## Prerequisites

- **Python 3.10+**
- **PostgreSQL 14+** with pgvector extension
- **Ollama** with llama3.2:3b-instruct-q4_K_M (or your preferred model)
- **CUDA-capable GPU** (12GB+ VRAM recommended for full features)
- **WSL2** (if running on Windows)

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd timmy-backend/v34
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv ~/.venv
source ~/.venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL Database

```sql
-- Create database
CREATE DATABASE timmy_memory_v16;

-- Enable pgvector extension
CREATE EXTENSION vector;

-- Create parent_documents table
CREATE TABLE parent_documents (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    speaker VARCHAR(50),
    full_text TEXT NOT NULL,
    summary TEXT,
    summary_embedding VECTOR(384),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create memory_chunks table
CREATE TABLE memory_chunks (
    id SERIAL PRIMARY KEY,
    embedding VECTOR(384) NOT NULL,
    content TEXT NOT NULL,
    speaker VARCHAR(50),
    topic VARCHAR(100),
    importance INTEGER,
    tags TEXT[],
    session_id VARCHAR(255),
    parent_id INTEGER,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (parent_id) REFERENCES parent_documents(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX ON parent_documents USING HNSW (summary_embedding vector_l2_ops);
CREATE INDEX ON memory_chunks USING HNSW (embedding vector_l2_ops);
CREATE INDEX ON memory_chunks (parent_id);
```

### 5. Configure Application

```bash
# Copy example config
cp config.example.py config.py

# Edit config.py with your settings
nano config.py
```

**Important:** Change the database password in `config.py`:
```python
DB_CONFIG = {
    "password": "YOUR_SECURE_PASSWORD_HERE",  # Change this!
}
```

### 6. Configure Network (WSL2 Only)

If running on WSL2, configure hostname resolution in `/etc/hosts`:

```bash
# Get Windows host IP
ip route show | grep -i default | awk '{ print $3}'

# Add to /etc/hosts
<gateway-ip> windows-host
192.168.1.157 windows-host-lan  # Your LAN IP
```

See `README_NETWORKING.md` for detailed network setup.

## Usage

### Start the Application

```bash
# Development mode (with debug output)
python app.py --debug

# Production mode
python app.py
```

The web UI will be available at:
- **Local:** http://localhost:5000
- **Network:** http://<your-ip>:5000

### API Endpoints

#### Chat via Webhook
```bash
curl -X POST http://localhost:5000/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, Timmy!"}'
```

#### Retrieve Memory
```bash
curl http://localhost:5000/api/retrieve_inspect?q=your+query
```

#### Get Recent Memories
```bash
curl http://localhost:5000/api/memory
```

#### Health Check
The app automatically runs health checks on startup and every 60 seconds for:
- Ollama LLM
- TTS Server
- STT Server
- Motor Controller

## Configuration

### Key Settings in `config.py`

| Setting | Description | Default |
|---------|-------------|---------|
| `MODEL_NAME` | Ollama model to use | `llama3.2:3b-instruct-q4_K_M` |
| `LLM_CONTEXT_SIZE` | Context window size | `8000` |
| `RETRIEVAL_ENABLED` | Enable vector memory retrieval | `True` |
| `USE_FULL_MEGA_PROMPT` | Send full prompt each turn | `True` |
| `NUM_RETRIEVED_CHUNKS` | Number of memory chunks to retrieve | `5` |
| `DEBUG_MODE` | Enable debug logging | `False` |

### Memory Tuning

- **`MAX_CHUNK_SIZE`**: Maximum characters per memory chunk (default: 512)
- **`OVERLAP_SENTENCES`**: Sentence overlap between chunks (default: 1)
- **`RECENCY_WEIGHT`**: Weight for recent memories (default: 0.25)

## Project Structure

```
v34/
├── app.py                      # Main Flask application
├── llm.py                      # LLM interaction & prompt building
├── memory.py                   # Vector memory & PostgreSQL
├── utils.py                    # Utility functions
├── vision_state.py             # Vision observation tracking
├── config.py                   # Configuration (create from config.example.py)
├── config.example.py           # Configuration template
├── requirements.txt            # Python dependencies
├── templates/                  # HTML templates
│   └── chat.html              # Web UI
├── tests/                      # Test files
│   └── README.md              # Test documentation
├── gliclass_source/            # GLiClass classifier (local package)
└── README.md                   # This file
```

## How It Works

### Memory System

1. **User sends message** → Classified for importance using GLiClass
2. **If important** → Stored in PostgreSQL with vector embedding
3. **Query retrieval** → Semantic search finds relevant memories
4. **Parent Document Retrieval** → Fetches full context from parent documents
5. **Inject into prompt** → Memories added to system prompt

### Prompt Strategy

The app uses a "megaprompt" strategy:

1. **Baseline Prompt** (first turn): Full persona + instructions
2. **Tail Prompts** (subsequent turns): Minimal ephemeral system + latest user message
3. **KV Cache Reuse**: Ollama caches previous context for efficiency

### Classification

Uses GLiClass for fast metadata generation:
- **Importance**: 0-5 scale (0=trivial, 5=critical)
- **Topic**: Single-word category
- **Tags**: 1-3 descriptive labels

## Troubleshooting

### Database Connection Failed
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -h localhost -p 5433 -U postgres -d timmy_memory_v16
```

### Ollama Not Responding
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

### Import Errors
```bash
# Ensure virtual environment is activated
source ~/.venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### CUDA Out of Memory
- Reduce `LLM_CONTEXT_SIZE` in config.py
- Use a smaller model
- Close other GPU-intensive applications

## Development

### Running Tests

```bash
cd tests/
python test_connectivity.py  # Test service connections
python test_megaprompt.py    # Test prompt building
```

**Note:** Some tests may not work with the current version. See `tests/README.md`.

### Adding New Features

1. Follow existing code structure
2. Add configuration to `config.py`
3. Use `utils.debug_print()` for logging
4. Update this README

## Security Notes

⚠️ **Before deploying to production:**

1. **Change database password** in `config.py`
2. **Use HTTPS** for external access
3. **Restrict network access** to trusted IPs
4. **Review** exposed endpoints
5. **Enable authentication** if needed

## Dependencies

### Core
- Flask + Flask-SocketIO - Web framework
- sentence-transformers - Embeddings
- psycopg2-binary - PostgreSQL adapter
- torch - Deep learning framework

### AI/ML
- transformers - Hugging Face transformers
- GLiClass - Zero-shot classification (local package)

### Optional
- eventlet - Async support
- requests - HTTP client

See `requirements.txt` for complete list.

## Known Issues

- `startup.sh` references incorrect venv path (use manual activation)
- Some test files may not work with current version
- Vision state requires external camera service (optional)

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **GLiClass** - Zero-shot classification model
- **Ollama** - Local LLM inference
- **pgvector** - PostgreSQL vector extension
- **sentence-transformers** - Embedding models


---

**Note:** This is v34 of the project. Earlier versions had different architectures and may not be compatible.

