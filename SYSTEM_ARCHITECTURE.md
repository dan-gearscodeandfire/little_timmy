# Little Timmy - System Architecture

Complete documentation for the Little Timmy AI Assistant system.

## 🏗️ System Overview

Little Timmy is a multi-component AI assistant system featuring:
- Voice-to-voice conversation capability
- Vector memory with RAG (Retrieval Augmented Generation)
- GPU-accelerated speech recognition and synthesis
- Zero-shot classification for intelligent memory tagging
- Real-time service coordination

## 📊 Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LITTLE TIMMY SYSTEM                          │
└─────────────────────────────────────────────────────────────────┘

    🎤 Microphone                                    🔊 Speakers
         │                                                │
         ▼                                                ▼
┌─────────────────┐       ┌─────────────────┐    ┌─────────────────┐
│  STT Server     │       │  LLM Processor  │    │  TTS Server     │
│  Port: 8888     │──────▶│  Port: 5000     │───▶│  Port: 5051     │
│  (Windows)      │ HTTP  │  (WSL)          │HTTP│  (Windows)      │
└─────────────────┘ text  └────────┬────────┘text└────────┬────────┘
         ▲                         │                       │
         │                         ▼                       │
         │                  ┌──────────────┐              │
         │                  │   Ollama     │              │
         │                  │ Port: 11434  │              │
         │                  │  (Windows)   │              │
         │                  └──────────────┘              │
         │                         │                       │
         └─────────────────────────┴───────────────────────┘
                      HTTP pause/resume coordination
```

## 🎛️ Service Control Panel

**Location:** `testing-interface/`  
**Port:** 5555  
**Purpose:** Web-based control panel to start/stop all services

**Launch:**
```
\\wsl.localhost\...\little-timmy\testing-interface\START_CONTROL_PANEL.bat
```

**Features:**
- One-click start/stop for all services
- Real-time log streaming
- Status monitoring
- Automatic cleanup on exit

## 🎤 STT Server (Speech-to-Text)

**Location:** `stt-server-v17/`  
**Port:** 8888  
**Engine:** faster-whisper with CUDA  
**Platform:** Windows (native audio access)

**Key Features:**
- Real-time audio transcription
- GPU-accelerated with CUDA
- Custom whisper models (tiny_dan_ct2, small_dan_ct2)
- Echo cancellation during TTS playback
- Pause/resume coordination with TTS
- WebSocket updates for live transcription

**Virtual Environment:** `C:\Users\dsm27\whisper\.venv`

**Endpoints:**
- `GET /transcript` - Current transcription state
- `POST /pause-listening` - Pause audio processing (called by TTS)
- `POST /resume-listening` - Resume audio processing (called by TTS)

**Start Command:**
```bash
C:\Users\dsm27\whisper\.venv\Scripts\python.exe \\wsl.localhost\...\stt-server-v17\timmy_hears.py --ai
```

## 🔊 TTS Server (Text-to-Speech)

**Location:** `tts-server/`  
**Port:** 5051  
**Engine:** Piper with CUDA/ONNX Runtime  
**Platform:** Windows (native audio access)

**Key Features:**
- GPU-accelerated synthesis with CUDA
- Custom voice model (skeletor_v1)
- Automatic STT coordination (pause before speaking)
- ESP32 LCD status integration
- Fast synthesis (~2-4x real-time)

**Virtual Environment:** `C:\Users\dsm27\piper\.venv`

**Endpoints:**
- `GET|POST /` or `/tts` or `/speak` - Synthesize text
- `GET /health` - Health check
- `GET /metrics` - Performance metrics

**Start Command:**
```bash
C:\Users\dsm27\piper\.venv\Scripts\python.exe \\wsl.localhost\...\tts-server\timmy_speaks_cuda.py
```

**Echo Prevention:**
1. TTS sends `POST /pause-listening` to STT
2. TTS waits 200ms for STT to pause
3. TTS plays audio through speakers
4. TTS waits 300ms for audio to finish
5. TTS sends `POST /resume-listening` to STT

## 🧠 LLM Preprocessor (v34)

**Location:** `v34/`  
**Port:** 5000  
**Engine:** Ollama + GLiClass + PostgreSQL  
**Platform:** WSL/Linux

**Key Features:**
- Smart classification with GLiClass zero-shot model
- Vector memory with pgvector (PostgreSQL)
- Parent-document retrieval strategy
- KV cache optimization for fast responses
- Fine-tuning capture for excellent exchanges
- Vision state integration

**Virtual Environment:** `~/timmy-backend/.venv` (WSL)

**Dependencies:**
- Ollama LLM (llama3.2:3b-instruct-q4_K_M)
- PostgreSQL with pgvector extension
- GLiClass for fast metadata generation
- Sentence-transformers for embeddings

**Start Command:**
```bash
wsl bash -c "cd ~/timmy-backend/little-timmy/v34 && source ~/timmy-backend/.venv/bin/activate && python app.py --debug"
```

## 🤖 Ollama Server

**Port:** 11434  
**Platform:** Windows  
**Model:** llama3.2:3b-instruct-q4_K_M

**Purpose:** LLM inference backend for v34 preprocessor

**Start Command:**
```bash
ollama serve
```

## 🔄 Data Flow

### Voice Conversation Flow:

1. **User speaks** → Microphone
2. **STT captures** → Transcribes with faster-whisper → Sends text to v34
3. **v34 processes**:
   - Classifies message importance (GLiClass)
   - Retrieves relevant memories (vector search)
   - Builds megaprompt with context
   - Generates response (Ollama)
   - Sends response to TTS
4. **TTS synthesizes**:
   - Sends pause to STT
   - Generates audio (Piper + CUDA)
   - Plays through speakers
   - Sends resume to STT
5. **Loop continues**

### Web Chat Flow (Alternative):

1. **User types** → v34 web UI (localhost:5000)
2. **v34 processes** → (same as above)
3. **TTS speaks** → (same as above)
4. **Response shown** → Web UI

## 🌐 Network Configuration

**All services run on 192.168.1.154 (this machine)**

| Service | Internal Port | External Access | Protocol |
|---------|---------------|-----------------|----------|
| Control Panel | 5555 | localhost:5555 | HTTP |
| v34 LLM | 5000 | localhost:5000 | HTTP + WebSocket |
| TTS | 5051 | 192.168.1.154:5051 | HTTP |
| STT | 8888 | 192.168.1.154:8888 | HTTP + WebSocket |
| Ollama | 11434 | localhost:11434 | HTTP |
| PostgreSQL | 5433 | localhost:5433 | PostgreSQL |
| ESP32 Display | - | 192.168.1.110:8080 | HTTPS |

## 💾 Data Storage

### **Vector Memory (PostgreSQL)**
- **Database:** `timmy_memory_v16`
- **Host:** localhost:5433
- **Schema:** memory_chunks, parent_documents
- **Extension:** pgvector for similarity search

### **Conversation History**
- Stored in-memory during session
- Important messages embedded in vector database
- Parent-document retrieval for context

### **Fine-Tuning Examples**
- Captured in `v34/fine_tuning_best_case_interchanges.md`
- Triggered by praise detection

## 🔧 Virtual Environment Setup

### **TTS (C:\Users\dsm27\piper\.venv)**
```bash
python -m venv C:\Users\dsm27\piper\.venv
C:\Users\dsm27\piper\.venv\Scripts\activate.bat
pip install -r tts-server/requirements.txt
pip install onnxruntime-gpu  # For CUDA
```

**Key Dependencies:** piper-tts, onnxruntime-gpu, Flask, sounddevice

### **STT (C:\Users\dsm27\whisper\.venv)**
```bash
python -m venv C:\Users\dsm27\whisper\.venv
C:\Users\dsm27\whisper\.venv\Scripts\activate.bat
pip install -r stt-server-v17/requirements.txt
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**Key Dependencies:** faster-whisper, Flask-SocketIO, PyAudio, PyTorch

### **v34 LLM (~/timmy-backend/.venv - WSL)**
```bash
python3 -m venv ~/timmy-backend/.venv
source ~/timmy-backend/.venv/bin/activate
pip install -r v34/requirements.txt
```

**Key Dependencies:** Flask, sentence-transformers, psycopg2, GLiClass

## 🎯 Why This Architecture?

### **Windows for Audio I/O**
- ✅ Direct hardware access (microphone + speakers)
- ✅ No PulseAudio/ALSA/WSL audio driver issues
- ✅ PyAudio and sounddevice work reliably
- ✅ CUDA GPU acceleration available

### **WSL for LLM Processing**
- ✅ Better Linux package compatibility
- ✅ PostgreSQL with pgvector
- ✅ Python ML libraries work well
- ✅ No audio hardware needed

### **Separate Virtual Environments**
- ✅ Avoids dependency conflicts
- ✅ Each component can be updated independently
- ✅ Clear separation of concerns
- ✅ Easier troubleshooting

## 🚀 Performance

**Typical Response Times (CUDA enabled):**
- STT transcription: 2-4 seconds (includes 1s pause threshold)
- v34 classification: <1 second (GLiClass)
- v34 retrieval: <1 second (vector search)
- v34 LLM generation: 1-3 seconds (Ollama with KV cache)
- TTS synthesis: <1 second (Piper CUDA)
- **Total latency:** ~5-9 seconds (voice to voice)

## 🔍 Troubleshooting

### **Echo Issues (Timmy hearing himself)**
- Check STT logs for `[PAUSE]` and `[RESUME]` messages
- Verify TTS is calling `localhost:8888/pause-listening`
- Current timing: 200ms pause delay, 300ms resume delay
- Adjust in `tts-server/timmy_speaks_cuda.py` if needed

### **No Audio Output from TTS**
- Check TTS logs for "Opening audio stream"
- Verify audio device is not in use by another app
- Run `python tts-server/list_devices.py` to check devices
- Check Windows sound settings (default output)

### **STT Not Recognizing Speech**
- Check microphone levels in Windows
- Look for "Recording started..." in STT logs
- Check RMS levels in debug output (should be >0.001 when speaking)
- Verify VAD (Voice Activity Detection) isn't filtering too aggressively

### **v34 LLM Slow or Timing Out**
- Check Ollama is running: `curl localhost:11434`
- Verify PostgreSQL is running on port 5433
- Check KV cache stats via `/api/kv_stats`
- Consider smaller model if 3b is too slow

### **Control Panel Services Won't Stop**
- Use "Stop All Services" button in web UI
- Or use "Shutdown Control Panel" button
- Or manually: Kill processes via Task Manager/`ps`

## 📝 Development Workflow

**Primary working location:**
```
\\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\
```

**Git operations (from WSL terminal):**
```bash
cd ~/timmy-backend/little-timmy
git add .
git commit -m "Your changes"
git push origin main
```

**Or from Windows terminal:**
```bash
wsl bash -c "cd ~/timmy-backend/little-timmy && git add . && git commit -m 'Your message' && git push origin main"
```

## 🔐 Security Notes

- Control panel has no authentication (localhost only)
- ESP32 endpoint uses self-signed cert (verify=False)
- PostgreSQL uses fixed password (not for production)
- All services bind to 0.0.0.0 (LAN accessible)

## 📚 Related Documentation

- `DEVELOPMENT_GUIDE.md` - Development workflow
- `stt-server-v17/README.md` - STT setup and usage
- `tts-server/README.md` - TTS setup and usage
- `v34/README.md` - LLM preprocessor details
- `testing-interface/README.md` - Control panel guide

## 🎓 Technologies Used

- **Speech Recognition:** faster-whisper (OpenAI Whisper optimized)
- **Text-to-Speech:** Piper TTS with ONNX Runtime
- **LLM:** Ollama (llama3.2:3b-instruct)
- **Classification:** GLiClass (zero-shot classification)
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **Vector DB:** PostgreSQL with pgvector extension
- **Web Framework:** Flask + Flask-SocketIO
- **Audio:** PyAudio (input), sounddevice (output)
- **GPU Acceleration:** CUDA 12.x with cuDNN

## 🏆 Key Achievements

✅ **Sub-10 second voice response latency**  
✅ **Zero echo - Timmy doesn't hear himself**  
✅ **GPU-accelerated on both STT and TTS**  
✅ **Smart memory with importance-based retrieval**  
✅ **Unified control panel for all services**  
✅ **Cross-platform architecture (Windows + WSL)**  
✅ **Production-ready with proper error handling**  

## 📌 Version History

- **v34** - Current production version with GLiClass
- **v17-v33** - Archived development iterations (deleted)
- **TTS v2** - CUDA-accelerated Piper implementation
- **STT v17** - faster-whisper with echo cancellation

## 🔗 Repository

**GitHub:** https://github.com/dan-gearscodeandfire/little_timmy  
**Branch:** main  
**License:** MIT

---

**Last Updated:** November 27, 2025  
**Status:** ✅ Production Ready

