# TTS Server (Piper CUDA)

Text-to-Speech server using Piper with CUDA GPU acceleration for real-time speech synthesis.

## Features

- Real-time text-to-speech using Piper TTS with CUDA acceleration
- Custom voice model: Skeletor v1
- GPU-accelerated synthesis with onnxruntime-gpu
- Flask HTTP API for easy integration
- Automatic coordination with STT server (pause/resume listening)
- ESP32 LCD status indicator integration
- High-quality audio output via sounddevice

## Installation & Setup

### Prerequisites
- Python 3.11+
- Windows OS (for CUDA GPU acceleration)
- NVIDIA GPU with CUDA support
- Audio output device (speakers/headphones)

### Virtual Environment Setup

This project uses a **dedicated virtual environment** located at:
```
C:\Users\dsm27\piper\.venv
```

**If setting up for the first time:**

1. Create the virtual environment:
```bash
python -m venv C:\Users\dsm27\piper\.venv
```

2. Activate the virtual environment:
```bash
C:\Users\dsm27\piper\.venv\Scripts\activate.bat
```

3. Install dependencies:
```bash
cd C:\Users\dsm27\little_timmy\tts-server
pip install -r requirements.txt
```

4. Install CUDA dependencies for GPU acceleration:
```bash
pip install onnxruntime-gpu
# CUDA libraries will be automatically installed as dependencies
```

### Voice Models

The TTS server requires Piper voice models (ONNX format).

**Model Location:**
```
C:\Users\dsm27\piper\models\
├── skeletor_v1.onnx          # Main voice model
└── skeletor_v1.onnx.json     # Model configuration
```

**Note:** Models are **not included in the repository** due to large file size (~350MB).

**To obtain models:**
- Download from Piper TTS official sources
- Or use existing models from `C:\Users\dsm27\piper\models\`
- Place in the `models/` directory within this folder

## Usage

### Quick Start (Windows)

**Using the batch script (Recommended):**
- Double-click: `START_TTS_SERVER.bat`

The server will:
1. Activate the virtual environment
2. Start the TTS server on port 5051
3. Enable CUDA GPU acceleration
4. Listen for text-to-speech requests

### Manual Start

```bash
C:\Users\dsm27\piper\.venv\Scripts\activate.bat
cd C:\Users\dsm27\little_timmy\tts-server
python timmy_speaks_cuda.py
```

### Command Line Options

```bash
python timmy_speaks_cuda.py [OPTIONS]

Options:
  --host HOST              Host address (default: 0.0.0.0)
  --port PORT              Port number (default: 5051)
  -m, --model PATH         Path to ONNX model (default: models/skeletor_v1.onnx)
  -c, --config PATH        Path to model config (default: models/skeletor_v1.onnx.json)
  --speaker ID             Speaker ID for multi-speaker models
  --length-scale FLOAT     Speech speed (default: 0.6, lower=faster)
  --noise-scale FLOAT      Voice variance (default: 0.667)
  --noise-w FLOAT          Pronunciation variance (default: 0.8)
  --sentence-silence FLOAT Pause between sentences (default: 0.0)
  --debug                  Enable debug logging
```

### Example - Custom Speech Speed

```bash
# Faster speech (0.5 = 2x faster)
python timmy_speaks_cuda.py --length-scale 0.5

# Slower speech (1.0 = normal)
python timmy_speaks_cuda.py --length-scale 1.0
```

## Configuration

Edit `config.py` to customize:

```python
# STT Server endpoint (for pause/resume coordination)
HEARING_SERVER_URL = "http://localhost:8888"

# ESP32 LCD display endpoint
SKULL_EYE_ENDPOINT = "https://192.168.1.110:8080/esp32/write"

# TTS Server settings
TTS_HOST = "0.0.0.0"
TTS_PORT = 5051

# Speech speed (lower = faster)
DEFAULT_SPEECH_SPEED = 0.6
```

## API Endpoints

### POST/GET `/` or `/tts` or `/speak`
Synthesize and play text

**Request:**
```bash
# GET with query parameter
curl "http://localhost:5051/?text=Hello%20world"

# POST with JSON
curl -X POST http://localhost:5051/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world"}'

# POST with plain text
curl -X POST http://localhost:5051/ \
  -H "Content-Type: text/plain" \
  -d "Hello world"
```

**Response:**
```json
{
  "status": "playing",
  "text": "Hello world"
}
```

### GET `/health`
Health check endpoint

**Response:**
```json
{
  "status": "ok",
  "provider": "CUDA"
}
```

### GET `/metrics`
Get last synthesis performance metrics

**Response:**
```json
{
  "provider": "CUDA",
  "text_chars": 42,
  "duration_seconds": 1.234,
  "started_at": null,
  "finished_at": null
}
```

## Network Architecture

```
┌─────────────────┐     HTTP      ┌─────────────────┐
│  LLM Processor  │──────────────>│   TTS Server    │
│  (port 5000)    │  text payload │  (port 5051)    │
└─────────────────┘               └────────┬────────┘
                                           │
                                           │ HTTP pause/resume
                                           ▼
                                  ┌─────────────────┐
                                  │   STT Server    │
                                  │  (port 8888)    │
                                  └─────────────────┘
```

## Utility Scripts

### `send_speech.py`
Test script that sends Marc Antony's speech from Julius Caesar to the TTS server.

**Usage:**
```bash
python send_speech.py
```

### `list_devices.py`
Lists all available audio output devices.

**Usage:**
```bash
python list_devices.py
```

**Output:**
```json
default: [1, 1]
[[0, "Speakers (Realtek)"], [1, "Headphones"], ...]
```

### `convert_to_fp16.py`
Converts ONNX models from float32 to float16 for smaller file size and faster inference.

**Usage:**
```bash
python convert_to_fp16.py source.onnx destination_fp16.onnx
```

## Dependencies

See `requirements.txt` for full list. Key dependencies:
- **piper-tts** - Core TTS engine
- **onnxruntime-gpu** - CUDA-accelerated inference
- **Flask** - HTTP API server
- **sounddevice** - Audio output
- **numpy** - Audio processing
- **requests** - HTTP client for STT coordination

### CUDA Dependencies (Auto-installed)
The following CUDA libraries are automatically installed:
- nvidia-cudnn-cu12
- nvidia-cuda-runtime-cu12
- nvidia-cublas-cu12
- nvidia-cufft-cu12
- And other CUDA toolkit components

## Performance

With CUDA acceleration:
- **Synthesis Speed:** ~2-4x real-time (depends on text length and GPU)
- **Latency:** <500ms for short phrases
- **GPU Usage:** NVIDIA RTX 3060 or equivalent recommended

## Troubleshooting

### CUDA Not Available
```
RuntimeError: CUDAExecutionProvider not available
```
**Solution:**
- Ensure `onnxruntime-gpu` is installed (not `onnxruntime`)
- Verify NVIDIA GPU drivers are up to date
- Check CUDA toolkit is accessible

### Audio Playback Issues
```
Error opening audio stream
```
**Solution:**
- Run `python list_devices.py` to see available audio devices
- Ensure speakers/headphones are connected and set as default
- Check Windows audio settings

### Model Not Found
```
FileNotFoundError: Model not found
```
**Solution:**
- Place models in `models/` directory
- Or specify model path with `--model` argument

## Recent Changes

- **v2**: Added CUDA GPU acceleration with onnxruntime-gpu
- Added Flask HTTP API with multiple endpoints
- Integrated STT server coordination (pause/resume)
- Added ESP32 LCD status indicator support
- Improved audio streaming with sounddevice

## Related Components

- **STT Server**: `../stt-server-v17/` - Speech-to-text with faster-whisper
- **LLM Preprocessor**: `../v34/` - AI response generation

