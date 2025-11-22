@echo off
REM STT Server v17 - Windows Native Startup Script
REM Working directory: C:\Users\dsm27\little_timmy\stt-server-v17
REM Repository: github.com/dan-gearscodeandfire/little_timmy

echo ================================================
echo   STT Server v17 - Speech to Text Server
echo ================================================
echo.
echo Location: %~dp0
echo Repository: github.com/dan-gearscodeandfire/little_timmy
echo.
echo Network Configuration:
echo   - LLM Preprocessor: http://localhost:5000/api/webhook
echo   - STT Web UI: http://localhost:8888
echo.
echo ================================================
echo.

REM Check if virtual environment exists
if not exist "C:\Users\dsm27\whisper\WhisperLive\.venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo Expected: C:\Users\dsm27\whisper\WhisperLive\.venv
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
call C:\Users\dsm27\whisper\WhisperLive\.venv\Scripts\activate.bat

echo Virtual environment activated
echo.
echo Starting STT Server in AI mode (connects to LLM preprocessor)...
echo Press Ctrl+C to stop the server.
echo.

REM Start the STT server in AI mode
python "%~dp0timmy_hears.py" --ai

pause

