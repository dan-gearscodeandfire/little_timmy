# STT Server v17

Speech-to-Text server using faster-whisper for real-time transcription.

## Features

- Real-time audio transcription using faster-whisper
- Web interface for viewing live transcripts
- Integration with LLM preprocessor for AI responses
- GPU acceleration with automatic CPU fallback
- Echo cancellation during TTS playback
- WebSocket support for live updates

## Configuration

### Endpoints

- **LLM Preprocessor**: `http://localhost:5000/api/webhook`
- **TTS Server**: `http://192.168.1.157:5051`
- **STT Web Interface**: `http://localhost:8888`

### Models

Two custom models available:
- `tiny_dan_ct2` - Fast, smaller model (40MB)
- `small_dan_ct2` - Better accuracy, larger model (248MB) **[Default]**

Change model in `timmy_hears.py` line 56.

## Usage

### Start Server (TTS Mode)
```bash
python timmy_hears.py
```

### Start Server (AI Mode with LLM)
```bash
python timmy_hears.py --ai
```

### Command Line Options
- `--flask-port` - Web server port (default: 8888)
- `--lang` - Language code (default: en)
- `--model` - Model path or name
- `--gpu-device` - GPU device index (default: 0)
- `--ai` - Send transcripts to LLM instead of TTS

## Requirements

- Python 3.11+
- faster-whisper
- Flask
- Flask-SocketIO
- PyAudio
- numpy
- requests

## Network Configuration

The server connects to the LLM preprocessor on `localhost:5000`, which works via WSL2's automatic port forwarding when the preprocessor runs in WSL and STT runs on Windows.

## Recent Changes

- **v17 Network Fix**: Changed LLM endpoint from LAN IP `192.168.1.157` to `localhost:5000`
- Increased timeout from 10s to 30s for LLM preprocessing
- Improved error handling with specific timeout and connection messages

