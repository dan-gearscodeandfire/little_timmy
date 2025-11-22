@echo off
setlocal

rem Launch the listener in a new Windows Terminal tab (non-blocking, leaves output running)
rem - Opens a new tab
rem - Activates C:\Users\dsm27\whisper\.venv
rem - Navigates to C:\Users\dsm27\whisper\WhisperLive\v17
rem - Runs: python timmy_hears.py --ai
where wt >nul 2>nul
if %ERRORLEVEL%==0 (
    wt -w 0 new-tab -d "C:\Users\dsm27\whisper" cmd /k "call C:\Users\dsm27\whisper\.venv\Scripts\activate.bat && cd /d C:\Users\dsm27\whisper\WhisperLive\v17 && python timmy_hears.py --ai"
    rem Launch the speaker in another Windows Terminal tab
    wt -w 0 new-tab -d "C:\Users\dsm27\piper" cmd /k "call .venv\Scripts\activate.bat && python timmy_speaks_cuda.py"
    rem Launch Ollama server in another Windows Terminal tab
    wt -w 0 new-tab -d "C:\Users\dsm27" cmd /k "ollama serve"
    rem Launch WSL2 Ubuntu-20.04 backend in another Windows Terminal tab
    rem Use bash -lc with explicit home path; double-quoted command for reliable parsing
    rem Launch WSL2 Ubuntu-20.04, wait briefly, then echo password, and keep shell open
    rem Use WT command terminator (--) so semicolons aren't parsed by WT
    wt -w 0 new-tab -- wsl.exe -d Ubuntu-20.04 bash -lc "sleep 2; echo 'Raistlin89' | sudo -S -v; cd /home/gearscodeandfire/timmy-backend && . .venv/bin/activate && cd v33 && python app.py --debug; bash -l"
) else (
    rem Fallback: open a new window if Windows Terminal is unavailable
    start "timmy_hears" cmd /k "cd /d C:\Users\dsm27\whisper && call .venv\Scripts\activate.bat && cd /d C:\Users\dsm27\whisper\WhisperLive\v17 && python timmy_hears.py --ai"
    start "timmy_speaks" cmd /k "cd /d C:\Users\dsm27\piper && call .venv\Scripts\activate.bat && python timmy_speaks_cuda.py"
    start "ollama" cmd /k "ollama serve"
    start "wsl_backend" wsl.exe -d Ubuntu-20.04 bash -lc "sleep 2; echo 'Raistlin89' | sudo -S -v; bash -l"
)

endlocal
exit /b

