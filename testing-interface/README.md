# Timmy Service Control Panel

A web-based control panel to start, stop, and monitor all Timmy services with real-time log streaming.

## Features

- ✅ **One-Click Start/Stop** - Control all services from a web interface
- ✅ **Real-Time Log Streaming** - See live output from each service
- ✅ **Automatic Cleanup** - All services stop when control panel closes
- ✅ **Status Monitoring** - Visual indicators for running/stopped services
- ✅ **Process Management** - Proper cleanup of service processes

## Services Managed

1. **TTS Server** - Piper CUDA text-to-speech (Port 5051)
2. **STT Server** - Faster-Whisper speech-to-text (Port 8888)
3. **Ollama Server** - LLM backend (Port 11434)
4. **LLM Preprocessor (v34)** - GLiClass + Memory system (Port 5000, WSL)

## Quick Start

### Prerequisites

Ensure Python dependencies are installed:
```bash
pip install -r requirements.txt
```

Required packages:
- Flask
- Flask-SocketIO
- psutil
- python-socketio

### Launch Control Panel

**Double-click:**
```
START_CONTROL_PANEL.bat
```

Or manually:
```bash
python control_panel.py
```

Then open your browser to:
```
http://localhost:5555
```

## Usage

### Starting Services

1. Open the control panel in your browser
2. Click the **Start** button for any service
3. Watch the real-time logs appear below
4. Green status badge indicates service is running

### Stopping Services

1. Click the **Stop** button for any running service
2. Service will terminate gracefully
3. Red status badge indicates service is stopped

### Auto-Cleanup

When you close the control panel (Ctrl+C in terminal):
- All running services automatically stop
- No orphaned processes left behind

## Service Configuration

Service paths and commands are configured in `control_panel.py`:

```python
SERVICES = {
    'tts': {
        'command': r'C:\Users\dsm27\piper\.venv\Scripts\python.exe',
        'args': [r'C:\Users\dsm27\little_timmy\tts-server\timmy_speaks_cuda.py'],
        'cwd': r'C:\Users\dsm27\little_timmy\tts-server',
    },
    # ... other services
}
```

Edit these paths if your installation differs.

## Logs

Service logs are saved to the `logs/` directory:
- `logs/tts.log` - TTS server output
- `logs/stt.log` - STT server output
- `logs/ollama.log` - Ollama server output
- `logs/v34.log` - LLM preprocessor output

Logs are cleared when services restart.

## Architecture

```
┌─────────────────────────────────────────────────┐
│       Control Panel (Port 5555)                 │
│       - Flask Web Server                        │
│       - WebSocket (Socket.IO)                   │
└────────────┬────────────────────────────────────┘
             │
             ├──> TTS Server (Python subprocess)
             ├──> STT Server (Python subprocess)
             ├──> Ollama Server (subprocess)
             └──> v34 LLM (WSL subprocess)
```

## Troubleshooting

### Services Won't Start

Check that paths in `control_panel.py` are correct:
- Virtual environment paths
- Script paths
- Working directories

### Port Already in Use

If port 5555 is taken, edit `control_panel.py`:
```python
socketio.run(app, host='0.0.0.0', port=5555)  # Change 5555 to another port
```

### Ollama Won't Stop

The control panel tries `ollama quit` first, then force kills.
If issues persist, manually run:
```bash
ollama quit
```

### WSL Service (v34) Issues

Ensure WSL is running and paths are correct:
```bash
wsl bash -c "cd ~/timmy-backend/little-timmy/v34 && ls"
```

## Development

### Adding New Services

Edit `control_panel.py` and add to `SERVICES` dict:

```python
'my_service': {
    'name': 'My Service Name',
    'command': 'path/to/executable',
    'args': ['arg1', 'arg2'],
    'cwd': 'working/directory',
    'log_file': 'logs/my_service.log',
    'process': None,
    'log_thread': None,
}
```

Then update `templates/index.html` to add the UI card.

## Safety Features

- **Process Tree Cleanup** - Kills all child processes
- **Graceful Termination** - Tries SIGTERM before SIGKILL
- **Exit Handler** - Cleanup runs even on unexpected exit
- **PID Tracking** - Monitors process status accurately

## Known Limitations

- Windows only (uses Windows-specific process management)
- No authentication (localhost only - do NOT expose publicly)
- Log files not rotated (can grow large)

## Future Enhancements

- [ ] Service auto-restart on crash
- [ ] Configurable service startup order
- [ ] Health check endpoints
- [ ] Log file rotation
- [ ] Service dependencies
- [ ] Authentication/security

---

**Version:** 1.0  
**Author:** Built for Little Timmy AI Assistant  
**License:** MIT

