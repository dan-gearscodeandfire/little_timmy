# Windows Native Workflow - TTS Server

## 📍 Your Working Directory

```
C:\Users\dsm27\little_timmy\tts-server\
```

This is your **main working directory** for the TTS server, connected to GitHub.

---

## 🚀 Quick Start

### **Start TTS Server**
Double-click: `START_TTS_SERVER.bat`

This will:
1. Activate the virtual environment
2. Start the TTS server on port 5051
3. Enable CUDA GPU acceleration
4. Wait for text-to-speech requests

---

## 📝 Making Changes

### 1. Edit Files
Work directly in this directory:
- `timmy_speaks_cuda.py` - Main TTS server code
- `config.py` - Configuration settings
- `requirements.txt` - Python dependencies
- Utility scripts (`list_devices.py`, `send_speech.py`, etc.)

### 2. Commit Changes
```bash
cd C:\Users\dsm27\little_timmy
git add tts-server/
git commit -m "Your commit message"
git push origin main
```

### 3. Pull Latest Changes
```bash
cd C:\Users\dsm27\little_timmy
git pull origin main
```

---

## 🔄 Setup from Scratch

If you're setting up on a new machine or fresh install:

### 1. Clone Repository
```bash
cd C:\Users\dsm27
git clone https://github.com/dan-gearscodeandfire/little_timmy.git
cd little_timmy\tts-server
```

### 2. Create Virtual Environment
```bash
python -m venv C:\Users\dsm27\piper\.venv
```

### 3. Activate Virtual Environment
```bash
C:\Users\dsm27\piper\.venv\Scripts\activate.bat
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Install CUDA Support (GPU Acceleration)
```bash
pip install onnxruntime-gpu
```

This will automatically install:
- nvidia-cudnn-cu12
- nvidia-cuda-runtime-cu12
- nvidia-cublas-cu12
- Other CUDA toolkit components

### 6. Get Voice Models

Models are **not in the repository** (too large).

**Option A: Use Existing Models**
If you have models already:
```bash
# Copy from your existing piper installation
mkdir models
copy C:\Users\dsm27\piper\models\*.onnx models\
copy C:\Users\dsm27\piper\models\*.json models\
```

**Option B: Download Models**
Download Piper voice models from:
- Official Piper TTS sources
- Place `*.onnx` and `*.onnx.json` files in `models/` directory

---

## 📂 Directory Structure

```
C:\Users\dsm27\
├── little_timmy\                 ← Git repository root
│   ├── tts-server\               ← YOUR WORKING DIRECTORY
│   │   ├── START_TTS_SERVER.bat  ← Double-click to run
│   │   ├── timmy_speaks_cuda.py  ← Main server
│   │   ├── config.py             ← Configuration
│   │   ├── requirements.txt      ← Dependencies
│   │   ├── send_speech.py        ← Test utility
│   │   ├── list_devices.py       ← Audio device utility
│   │   ├── convert_to_fp16.py    ← Model conversion utility
│   │   ├── models\               ← Voice models (not in git)
│   │   │   ├── skeletor_v1.onnx
│   │   │   └── skeletor_v1.onnx.json
│   │   ├── README.md
│   │   └── WINDOWS_WORKFLOW.md   ← This file
│   ├── stt-server-v17\           ← STT server
│   ├── v34\                      ← LLM preprocessor
│   └── .git\                     ← Git repository data
└── piper\
    └── .venv\                    ← Virtual environment (shared)
```

---

## 🌐 Network Configuration

- **TTS Server (This)**: http://localhost:5051 or http://192.168.1.154:5051
- **STT Server**: http://localhost:8888
- **LLM Preprocessor**: http://localhost:5000 (WSL)
- **ESP32 Display**: https://192.168.1.110:8080

---

## ⚙️ Virtual Environment

The TTS server uses a **dedicated virtual environment**:
```
C:\Users\dsm27\piper\.venv
```

### Manual Activation
If you need to manually activate:
```bash
C:\Users\dsm27\piper\.venv\Scripts\activate.bat
```

### Why Separate from STT?
- Different dependencies (piper-tts vs faster-whisper)
- Avoids version conflicts
- Each can be updated independently
- Cleaner dependency management

---

## 🎯 Configuration

### Edit Settings
Open `config.py` and modify:

```python
# STT Server endpoint
HEARING_SERVER_URL = "http://localhost:8888"

# ESP32 LCD display
SKULL_EYE_ENDPOINT = "https://192.168.1.110:8080/esp32/write"

# Server settings
TTS_PORT = 5051
DEFAULT_SPEECH_SPEED = 0.6  # Lower = faster
```

### Command-Line Overrides
You can also override settings when starting:
```bash
python timmy_speaks_cuda.py --port 5052 --length-scale 0.8
```

---

## 🧪 Testing

### Test Audio Output
```bash
python list_devices.py
```

### Test TTS Server
```bash
# Start the server first (in one terminal)
START_TTS_SERVER.bat

# Then in another terminal, send test speech
python send_speech.py
```

### Test via HTTP
```bash
curl "http://localhost:5051/?text=Hello%20world"
```

---

## 🔧 Troubleshooting

### Server Won't Start
1. Check virtual environment exists:
   ```bash
   dir C:\Users\dsm27\piper\.venv
   ```
2. Verify dependencies installed:
   ```bash
   C:\Users\dsm27\piper\.venv\Scripts\python.exe -m pip list
   ```

### CUDA Not Working
1. Check if CUDA provider is available:
   ```bash
   C:\Users\dsm27\piper\.venv\Scripts\python.exe
   >>> import onnxruntime as ort
   >>> ort.get_available_providers()
   # Should include 'CUDAExecutionProvider'
   ```

2. Update NVIDIA drivers
3. Reinstall onnxruntime-gpu:
   ```bash
   pip uninstall onnxruntime-gpu
   pip install onnxruntime-gpu
   ```

### No Audio Output
1. List audio devices:
   ```bash
   python list_devices.py
   ```
2. Check Windows sound settings
3. Verify default output device is correct

### Models Not Found
1. Check models directory exists and contains:
   - `skeletor_v1.onnx`
   - `skeletor_v1.onnx.json`
2. Or specify model path:
   ```bash
   python timmy_speaks_cuda.py -m "C:\path\to\your\model.onnx"
   ```

---

## 📊 Performance

### Expected Performance (RTX 3060)
- Synthesis: 2-4x real-time
- Latency: <500ms for short phrases
- GPU Memory: ~1-2GB during synthesis

### Monitor Performance
```bash
# Check last synthesis metrics
curl http://localhost:5051/metrics
```

---

## 🎓 Benefits of This Setup

✅ **Native Windows Performance** - Direct GPU access, no WSL overhead  
✅ **Git Integrated** - Push/pull changes to GitHub easily  
✅ **Isolated Dependencies** - Separate venv prevents conflicts  
✅ **Well Documented** - Clear setup and troubleshooting guides  
✅ **Production Ready** - CUDA acceleration for fast synthesis

---

## 📌 Related Documentation

- **Main README**: `README.md` - Full API documentation
- **STT Server**: `../stt-server-v17/WINDOWS_WORKFLOW.md`
- **LLM Preprocessor**: `../v34/` (runs in WSL)

