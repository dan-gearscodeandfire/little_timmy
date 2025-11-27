@echo off
REM Timmy Service Control Panel - Startup Script
REM Double-click this file to launch the control panel

echo ================================================
echo   Timmy Service Control Panel
echo ================================================
echo.
echo Starting control panel...
echo.
echo Once started, open your browser to:
echo   http://localhost:5555
echo.
echo Press Ctrl+C to stop the control panel
echo (This will also stop all services)
echo.
echo ================================================
echo.

REM Use system Python (should have Flask, Flask-SocketIO, psutil)
python "%~dp0control_panel.py"

pause

