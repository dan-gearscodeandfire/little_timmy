# STT Server v17

Speech-to-Text server using faster-whisper for real-time transcription.

## Features

- Real-time audio transcription using faster-whisper
- Web interface for viewing live transcripts
- Integration with LLM preprocessor for AI responses
- GPU acceleration with automatic CPU fallback
- Echo cancellation during TTS playback
- WebSocket support for live updates

## Installation & Setup

### Prerequisites
- Python 3.11 or higher
- Windows OS (for GPU acceleration with CUDA)
- Microphone for audio input

### Virtual Environment Setup

This project uses a **shared virtual environment** located at:
```
C:\Users\dsm27\whisper\.venv
```

**If setting up for the first time:**

1. Create the virtual environment (if it doesn't exist):
```bash
python -m venv C:\Users\dsm27\whisper\.venv
```

2. Activate the virtual environment:
```bash
C:\Users\dsm27\whisper\.venv\Scripts\activate.bat
```

3. Install dependencies:
```bash
cd C:\Users\dsm27\little_timmy\stt-server-v17
pip install -r requirements.txt
```

4. Install PyTorch with CUDA support (for GPU acceleration):
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Custom Whisper Models

This server uses custom faster-whisper models optimized for performance:
- **Location**: `C:\Users\dsm27\whisper\WhisperLive\`
- **tiny_dan_ct2** - Fast, smaller model (40MB)
- **small_dan_ct2** - Better accuracy, larger model (248MB) **[Default]**

These models should already be present if you've used the original setup.

## Configuration

### Network Endpoints

- **STT Web Interface**: `http://localhost:8888` (this server)
- **LLM Preprocessor**: `http://localhost:5000/api/webhook` (WSL)
- **TTS Server**: `http://192.168.1.154:5051` (separate machine)
- **Eye LCD Display**: `https://192.168.1.110:8080` (ESP32 device)

### Models

Two custom models available:
- `tiny_dan_ct2` - Fast, smaller model (40MB)
- `small_dan_ct2` - Better accuracy, larger model (248MB) **[Default]**

Change model in `timmy_hears.py` line 56.

## Usage

### Quick Start (Windows)

**AI Mode with LLM (Recommended):**
- Double-click: `START_STT_SERVER.bat`
- Sends transcripts to LLM preprocessor for intelligent responses

**TTS Mode (Direct Text-to-Speech):**
- Double-click: `START_STT_TTS_MODE.bat`
- Sends transcripts directly to TTS server

### Manual Start

**TTS Mode:**
```bash
C:\Users\dsm27\whisper\.venv\Scripts\activate.bat
python timmy_hears.py
```

**AI Mode with LLM:**
```bash
C:\Users\dsm27\whisper\.venv\Scripts\activate.bat
python timmy_hears.py --ai
```

### Command Line Options
- `--flask-port` - Web server port (default: 8888)
- `--lang` - Language code (default: en)
- `--model` - Model path or name
- `--gpu-device` - GPU device index (default: 0)
- `--ai` - Send transcripts to LLM instead of TTS

## Dependencies

See `requirements.txt` for full list. Key dependencies:
- **faster-whisper** - Speech recognition engine
- **Flask** & **Flask-SocketIO** - Web server and real-time updates
- **PyAudio** - Audio capture from microphone
- **numpy** - Audio data processing
- **requests** - HTTP communication with LLM/TTS servers
- **PyTorch** (with CUDA) - GPU acceleration for transcription

## Network Configuration

The server connects to the LLM preprocessor on `localhost:5000`, which works via WSL2's automatic port forwarding when the preprocessor runs in WSL and STT runs on Windows.

## Recent Changes

- **v17 Network Fix**: Changed LLM endpoint from LAN IP `192.168.1.157` to `localhost:5000`
- Increased timeout from 10s to 30s for LLM preprocessing
- Improved error handling with specific timeout and connection messages

