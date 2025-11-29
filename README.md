# Little Timmy

Voice-enabled AI assistant with persistent vector memory, GPU-accelerated speech processing, and intelligent context retrieval.

**⚡ Professional-grade performance:** 2.4s response time (47% faster after optimization)

## 🎯 For New Agents/Developers - Start Here!

**To understand this project, read these documents in order:**

1. **📖 [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)** - Complete system overview, component diagram, and data flow
2. **🛠️ [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)** - Development workflow, Git operations, and environment setup
3. **📊 Performance & Optimization:** ✅ **All optimizations complete!**
   - [OPTIMIZATION_JOURNEY_COMPLETE.md](OPTIMIZATION_JOURNEY_COMPLETE.md) - 🏆 **Complete optimization story (47% improvement!)**
   - [LATENCY_OPTIMIZATION_SUCCESS.md](LATENCY_OPTIMIZATION_SUCCESS.md) - HTTP connection pooling (99.7% faster!)
   - [PGVECTOR_OPTIMIZATION.md](PGVECTOR_OPTIMIZATION.md) - Memory storage optimization (26% faster)
   - [MYSTERY_GAP_SOLVED.md](MYSTERY_GAP_SOLVED.md) - How we found the real bottleneck
   - [PHASE2A_RESULTS.md](PHASE2A_RESULTS.md) - Final optimization results
   - [WHY_NO_KV_CACHE.md](WHY_NO_KV_CACHE.md) - Why KV cache is incompatible with RAG
   - [shared/README.md](shared/README.md) - Latency tracking system
4. **📂 Component READMEs:**
   - [stt-server-v17/README.md](stt-server-v17/README.md) - Speech-to-Text server
   - [tts-server/README.md](tts-server/README.md) - Text-to-Speech server
   - [v34/README.md](v34/README.md) - LLM preprocessor with memory
   - [testing-interface/README.md](testing-interface/README.md) - Service control panel

**Repository Location:**
```
\\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\
```

## 🚀 Quick Start

### **Launch All Services (Easiest)**

Double-click:
```
testing-interface\START_CONTROL_PANEL.bat
```

Then open http://localhost:5555 and start services.

### **Manual Launch**

See [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) for individual service startup commands.

## ⚡ Performance

**Professional-grade conversational AI response times achieved through comprehensive optimization:**

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Total Response Time** | 4.6s | 2.4s | **47% faster** |
| **HTTP Latency** | 2070ms | 6ms | **99.7% faster** |
| **Memory Storage** | 640ms | 473ms | **26% faster** |
| **Vector Retrieval** | 50ms | 28ms | **Already optimal** |

**Key Achievements:**
- ✅ HTTP connection pooling across all services
- ✅ Optimized memory storage (metadata reuse + batch DB inserts)
- ✅ Discovered vector retrieval already optimal (no FAISS needed!)
- ✅ Complete latency tracking and analysis system

**Read the full story:** [OPTIMIZATION_JOURNEY_COMPLETE.md](OPTIMIZATION_JOURNEY_COMPLETE.md)

## 📦 Repository Structure

```
little-timmy/
├── stt-server-v17/              # Speech-to-Text (faster-whisper + CUDA)
├── tts-server/                  # Text-to-Speech (Piper + CUDA)
├── v34/                         # LLM Preprocessor (GLiClass + Memory)
├── testing-interface/           # Service Control Panel
├── esp32_phoneme_to_jaw_openness/  # Hardware control (Arduino)
├── SYSTEM_ARCHITECTURE.md       # 🎯 START HERE for overview
├── DEVELOPMENT_GUIDE.md         # Development workflow
└── README.md                    # This file
```

## ⚙️ System Components

### **STT Server** (Port 8888)
- Real-time speech recognition with faster-whisper
- GPU-accelerated transcription
- Echo cancellation during TTS playback
- Custom whisper models for accuracy

### **TTS Server** (Port 5051)
- Natural voice synthesis with Piper
- GPU-accelerated with CUDA/ONNX Runtime
- Custom voice model (skeletor_v1)
- Coordinates with STT to prevent echo

### **LLM Preprocessor** (Port 5000)
- Ollama-based conversation AI
- Vector memory with PostgreSQL + pgvector
- GLiClass zero-shot classification
- Smart context retrieval
- Web chat interface

### **Service Control Panel** (Port 5555)
- Web-based management interface
- Start/stop all services
- Real-time log streaming
- Status monitoring

## 🎯 Key Features

✅ **Voice-to-Voice AI** - Speak naturally, hear responses  
✅ **Persistent Memory** - Remembers conversations across sessions  
✅ **Smart Retrieval** - GLiClass classification + vector similarity  
✅ **GPU Accelerated** - Fast transcription and synthesis  
✅ **Zero Echo** - Proper coordination prevents feedback loops  
✅ **Easy Management** - One-click control panel  
✅ **Production Ready** - Error handling, logging, monitoring  

## 🔧 Technical Stack

- **Python 3.11** - Core language
- **CUDA 12.x** - GPU acceleration
- **faster-whisper** - STT engine
- **Piper TTS** - TTS engine
- **Ollama** - LLM backend (llama3.2:3b)
- **GLiClass** - Zero-shot classification
- **PostgreSQL + pgvector** - Vector memory
- **Flask + SocketIO** - Web framework
- **PyAudio + sounddevice** - Audio I/O

## 📊 Performance

- **Voice Response:** ~5-9 seconds end-to-end
- **STT Latency:** 2-4 seconds
- **LLM Generation:** 1-3 seconds  
- **TTS Synthesis:** <1 second
- **GPU Usage:** RTX 3060 or equivalent

## 🌐 Network Topology

All services run on **192.168.1.154** (this machine):
- Windows services: STT, TTS, Ollama, Control Panel
- WSL services: v34 LLM Preprocessor
- External: ESP32 display at 192.168.1.110:8080

Communication via localhost (STT↔TTS, v34↔Ollama) and LAN (v34↔TTS).

## 📝 Common Tasks

### **Starting Everything**
```bash
# Launch control panel
testing-interface\START_CONTROL_PANEL.bat
# Then visit http://localhost:5555
```

### **Making Changes**
```bash
# Edit files in WSL location
cd ~/timmy-backend/little-timmy
# Make your changes
git add .
git commit -m "Your message"
git push origin main
```

### **Debugging**
- Control panel shows real-time logs
- Service logs in `testing-interface/logs/`
- Debug mode flags: `--debug` or `--ai`

## 🐛 Known Issues

- ⚠️ Log file permissions on WSL filesystem (handled gracefully)
- ⚠️ Control panel cleanup requires signal handlers (fixed)
- ⚠️ Old Windows copy at C:\Users\dsm27\little_timmy (TODO: delete)

## 🎓 Learning Resources

- **Piper TTS:** https://github.com/rhasspy/piper
- **faster-whisper:** https://github.com/guillaumekln/faster-whisper
- **GLiClass:** https://github.com/knowledgator/gliclass
- **Ollama:** https://ollama.ai/

## 🤝 Contributing

This is a personal project, but follows standard Git workflow:
1. Make changes in WSL repository
2. Test with control panel
3. Commit and push to GitHub

## 📜 License

MIT License - See v34/LICENSE for details

## 🏆 Project Status

**Status:** ✅ Production Ready  
**Last Updated:** November 27, 2025  
**Version:** v34 (LLM), v17 (STT), v2 (TTS)

---

**Repository:** https://github.com/dan-gearscodeandfire/little_timmy  
**Maintainer:** Dan (gearscodeandfire)
