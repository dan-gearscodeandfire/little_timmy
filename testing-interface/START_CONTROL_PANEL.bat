@echo off
@echo off
REM Timmy Service Control Panel - Startup Script
REM Double-click this file to launch the control panel
REM 
REM Working Directory: \\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\testing-interface
REM Note: This runs from WSL filesystem using Windows Python

echo ================================================
echo   Timmy Service Control Panel
echo ================================================
echo.
echo Repository Location: WSL (little-timmy)
echo Starting control panel...
echo.
echo Once started, open your browser to:
echo   http://localhost:5555
echo.
echo Services managed:
echo   - TTS Server (Port 5051)
echo   - STT Server (Port 8888) 
echo   - Ollama Server (Port 11434)
echo   - v34 LLM Preprocessor (Port 5000)
echo.
echo Press Ctrl+C to stop the control panel
echo (This will also stop all services)
echo.
echo ================================================
echo.

REM Use system Python (should have Flask, Flask-SocketIO, psutil)
python "%~dp0control_panel.py"

pause

