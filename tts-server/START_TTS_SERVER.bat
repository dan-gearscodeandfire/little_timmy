@echo off
REM TTS Server - Windows Native Startup Script
REM Working directory: C:\Users\dsm27\little_timmy\tts-server
REM Repository: github.com/dan-gearscodeandfire/little_timmy

echo ================================================
echo   TTS Server - Text to Speech with Piper
echo ================================================
echo.
echo Location: %~dp0
echo Repository: github.com/dan-gearscodeandfire/little_timmy
echo.
echo Network Configuration:
echo   - TTS Server: http://localhost:5051 (this server)
echo   - STT Server: http://localhost:8888
echo   - ESP32 Display: https://192.168.1.110:8080
echo.
echo ================================================
echo.

REM Check if virtual environment exists
if not exist "C:\Users\dsm27\piper\.venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo Expected: C:\Users\dsm27\piper\.venv
    echo.
    echo Please create the virtual environment:
    echo   python -m venv C:\Users\dsm27\piper\.venv
    echo   C:\Users\dsm27\piper\.venv\Scripts\activate.bat
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
call C:\Users\dsm27\piper\.venv\Scripts\activate.bat

echo Virtual environment activated
echo.
echo Starting TTS Server with CUDA acceleration...
echo Press Ctrl+C to stop the server.
echo.

REM Start the TTS server
python "%~dp0timmy_speaks_cuda.py"

pause

