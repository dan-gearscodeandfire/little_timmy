@echo off
REM STT Server v17 - TTS Mode (No LLM)
REM Working directory: C:\Users\dsm27\little_timmy\stt-server-v17
REM Repository: github.com/dan-gearscodeandfire/little_timmy

echo ================================================
echo   STT Server v17 - TTS Mode
echo ================================================
echo.
echo Location: %~dp0
echo.
echo Network Configuration:
echo   - TTS Server: http://192.168.1.157:5051
echo   - STT Web UI: http://localhost:8888
echo.
echo ================================================
echo.

REM Activate virtual environment
call C:\Users\dsm27\whisper\WhisperLive\.venv\Scripts\activate.bat

echo Starting STT Server in TTS mode (no LLM)...
echo Press Ctrl+C to stop the server.
echo.

REM Start the STT server in TTS mode (default)
python "%~dp0timmy_hears.py"

pause

