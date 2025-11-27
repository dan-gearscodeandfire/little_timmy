# Development Guide - Little Timmy

## 📍 Primary Working Location

**All development should be done in the WSL repository:**

```
\\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\
```

**Or from WSL terminal:**
```bash
~/timmy-backend/little-timmy/
```

## 🏗️ Repository Structure

```
little-timmy/  (GitHub: dan-gearscodeandfire/little_timmy)
├── stt-server-v17/          # Speech-to-Text Server
├── tts-server/              # Text-to-Speech Server  
├── v34/                     # LLM Preprocessor
├── testing-interface/       # Service Control Panel
└── esp32_phoneme_to_jaw_openness/
```

## 🔧 Virtual Environments

**Location (Outside Repository):**
```
TTS:  C:\Users\dsm27\piper\.venv
STT:  C:\Users\dsm27\whisper\.venv
v34:  ~/timmy-backend/.venv (WSL)
```

**Note:** Virtual environments are stored separately from the repository to avoid conflicts.

## 🚀 Running Services

### **Method 1: Control Panel (Recommended)**

**From Windows:**
```
\\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\testing-interface\START_CONTROL_PANEL.bat
```

Double-click the batch file, then open http://localhost:5555

### **Method 2: Individual Scripts**

All scripts should reference WSL paths but run from Windows terminal:

```bash
# STT Server
C:\Users\dsm27\whisper\.venv\Scripts\python.exe \\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\stt-server-v17\timmy_hears.py --ai

# TTS Server
C:\Users\dsm27\piper\.venv\Scripts\python.exe \\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\tts-server\timmy_speaks_cuda.py

# v34 LLM (runs in WSL)
wsl bash -c "cd ~/timmy-backend/little-timmy/v34 && source ~/timmy-backend/.venv/bin/activate && python app.py --debug"
```

## 📝 Git Workflow

### **Making Changes**

**Edit files in WSL location:**
```
\\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\
```

**Or open WSL terminal:**
```bash
cd ~/timmy-backend/little-timmy
code .  # Opens in VS Code
```

### **Committing Changes**

**From Windows terminal:**
```bash
wsl bash -c "cd ~/timmy-backend/little-timmy && git add . && git commit -m 'Your message' && git push origin main"
```

**Or from WSL terminal:**
```bash
cd ~/timmy-backend/little-timmy
git add .
git commit -m "Your message"
git push origin main
```

## 🗂️ What About C:\Users\dsm27\little_timmy?

### **Current Status:**
The Windows copy at `C:\Users\dsm27\little_timmy` is a **duplicate** that's no longer needed.

### **Options:**

**Option A: Delete it** (Recommended)
```bash
Remove-Item -Recurse -Force C:\Users\dsm27\little_timmy
```

**Option B: Archive it**
```bash
Rename-Item C:\Users\dsm27\little_timmy C:\Users\dsm27\little_timmy.backup
```

**Option C: Keep for reference**
Leave it but never commit from there

## 🎯 Single Source of Truth

**Going forward:**

✅ **Primary Repository:**
```
\\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\
```

✅ **Access from Windows:**
- File Explorer: `\\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\`
- VS Code: Can open WSL paths directly
- Git operations: Commit from WSL

✅ **Virtual Environments:** 
- Remain on Windows (C:\Users\dsm27\piper\.venv, C:\Users\dsm27\whisper\.venv)
- These are NOT duplicated, they're external dependencies

## 🔄 Updated Control Panel

I've already updated the control panel to use WSL paths, so you're all set!

**Would you like me to:**
1. Delete `C:\Users\dsm27\little_timmy` for you?
2. Create a quick commit script for the WSL workflow?
3. Update any remaining documentation that references C:\ paths?
