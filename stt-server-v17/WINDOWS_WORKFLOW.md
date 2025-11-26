# Windows Native Workflow

## 📍 Your Working Directory

```
C:\Users\dsm27\little_timmy\stt-server-v17\
```

This is your **main working directory** for the STT server, connected to GitHub.

---

## 🚀 Quick Start

### **Start STT Server (AI Mode with LLM)**
Double-click: `START_STT_SERVER.bat`

### **Start STT Server (TTS Mode, no LLM)**
Double-click: `START_STT_TTS_MODE.bat`

---

## 📝 Making Changes

### 1. Edit Files
Work directly in this directory:
- `timmy_hears.py` - Main server code
- `transcript_manager.py` - Transcript handling
- `index.html` - Web interface
- etc.

### 2. Commit Changes
```bash
cd C:\Users\dsm27\little_timmy
git add stt-server-v17/
git commit -m "Your commit message"
git push origin main
```

### 3. Pull Latest Changes
```bash
cd C:\Users\dsm27\little_timmy
git pull origin main
```

---

## 🔄 Syncing with WSL

The WSL directory (`~/timmy-backend/little-timmy/stt-server-v17`) will need to be updated:

```bash
# In WSL:
cd ~/timmy-backend/little-timmy
git pull origin main
```

---

## 📂 Directory Structure

```
C:\Users\dsm27\little_timmy\          ← Git repository root
├── stt-server-v17\                   ← YOUR WORKING DIRECTORY
│   ├── START_STT_SERVER.bat          ← Double-click to run (AI mode)
│   ├── START_STT_TTS_MODE.bat        ← Double-click to run (TTS mode)
│   ├── timmy_hears.py                ← Main server (with network fix)
│   ├── transcript_manager.py
│   ├── index.html
│   └── README.md
├── v34\                              ← Other project components
└── .git\                             ← Git repository data
```

---

## 🌐 Network Configuration

- **STT Web Interface**: http://localhost:8888
- **LLM Preprocessor**: http://localhost:5000/api/webhook ✅ (Fixed!)
- **TTS Server**: http://192.168.1.154:5051

---

## ⚙️ Virtual Environment

The startup scripts automatically activate:
```
C:\Users\dsm27\whisper\.venv
```

If you need to manually activate:
```bash
C:\Users\dsm27\whisper\.venv\Scripts\activate.bat
```

---

## 🎯 Benefits of This Setup

✅ **Native Windows Performance** - Run directly on Windows, no WSL overhead for STT
✅ **Git Integrated** - Push/pull changes to GitHub easily  
✅ **Synced Across Environments** - WSL can pull your changes
✅ **Network Fix Applied** - Uses localhost for preprocessor connection

---

## 📌 Old Windows Directory

Your old working directory is still at:
```
C:\Users\dsm27\whisper\WhisperLive\v17\
```

You can keep it for reference or delete it. This new directory is now your primary workspace.

