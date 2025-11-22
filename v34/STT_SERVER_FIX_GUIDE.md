# STT Server Connection Fix Guide

**For use in a separate session with your STT codebase**

---

## 🚨 **The Problem:**

**Current Error:**
```
Error sending to LLM preprocessor: HTTPConnectionPool(host='192.168.1.157', port=5000): 
Max retries exceeded with url: /api/webhook 
(Caused by ConnectTimeoutError(...'Connection to 192.168.1.157 timed out'))
```

**Root Cause:** STT server is trying to connect to LAN IP, but preprocessor is in WSL on a different network.

---

## 🎯 **The Fix:**

### **Change STT Server Configuration:**

**FROM:**
```python
LLM_PREPROCESSOR_URL = "http://192.168.1.157:5000/api/webhook"
```

**TO:**
```python
LLM_PREPROCESSOR_URL = "http://localhost:5000/api/webhook"
```

**Why:** Since both STT and preprocessor run on the same Windows machine (STT on Windows, preprocessor in WSL), `localhost` will work via WSL2's automatic port forwarding.

---

## 📋 **What to Look For in STT Codebase:**

### **1. Configuration File:**
Look for files like:
- `config.py`
- `settings.py`
- `.env`
- `config.json`

Search for:
- `192.168.1.157`
- `preprocessor`
- `webhook`
- `llm`
- Port `5000`

### **2. Code That Sends to Preprocessor:**
Look for:
```python
requests.post(url, json={"text": transcribed_text})
```

Or similar HTTP POST calls.

---

## 🔧 **Specific Changes Needed:**

### **Change 1: Update URL**

**Find:**
```python
PREPROCESSOR_URL = "http://192.168.1.157:5000/api/webhook"
# or
preprocessor_url = "http://192.168.1.157:5000/api/webhook"
```

**Replace with:**
```python
PREPROCESSOR_URL = "http://localhost:5000/api/webhook"
```

---

### **Change 2: Update Timeout (Optional)**

**If you have:**
```python
requests.post(url, json=data, timeout=10)
```

**Consider increasing:**
```python
requests.post(url, json=data, timeout=30)  # Preprocessor can take 1-2s
```

**Why:** The preprocessor does classification, retrieval, and LLM generation (0.5-2 seconds total).

---

### **Change 3: Better Error Handling (Optional)**

**Current (probably):**
```python
try:
    response = requests.post(url, json={"text": text})
except Exception as e:
    print(f"Error sending to LLM preprocessor: {e}")
```

**Improved:**
```python
try:
    response = requests.post(url, json={"text": text}, timeout=30)
    response.raise_for_status()
    result = response.json()
    print(f"✅ LLM Response: {result.get('response', 'No response')}")
except requests.exceptions.Timeout:
    print("⏱️  LLM preprocessor timeout (taking too long)")
except requests.exceptions.ConnectionError as e:
    print(f"🔌 Cannot connect to preprocessor: {e}")
    print("   Make sure preprocessor is running: cd ~/timmy-backend/little-timmy/v34 && python app.py")
except Exception as e:
    print(f"❌ Error: {e}")
```

---

## 🧪 **Testing After Changes:**

### **1. Verify Preprocessor is Running:**
```bash
curl http://localhost:5000/
# Should return HTML
```

### **2. Test Webhook:**
```bash
curl -X POST http://localhost:5000/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "test message"}'
```

**Expected response:**
```json
{
  "status": "success",
  "response": "Test received and acknowledged..."
}
```

### **3. Test from STT:**
Run your STT server and speak a test phrase.

---

## 📝 **Checklist for STT Codebase Session:**

- [ ] Find configuration file (config.py, .env, etc.)
- [ ] Locate preprocessor URL setting
- [ ] Change `192.168.1.157:5000` to `localhost:5000`
- [ ] Check timeout setting (increase to 30s if needed)
- [ ] Improve error handling (optional)
- [ ] Test connection
- [ ] Commit changes

---

## 🔍 **Common STT Server Patterns:**

### **Pattern 1: Config File**
```python
# config.py or settings.py
PREPROCESSOR_URL = "http://192.168.1.157:5000/api/webhook"  # ← Change this
TIMEOUT = 10  # ← Maybe increase to 30
```

### **Pattern 2: Environment Variable**
```bash
# .env file
LLM_PREPROCESSOR_URL=http://192.168.1.157:5000/api/webhook  # ← Change this
```

### **Pattern 3: Hardcoded**
```python
# In the main STT script
response = requests.post(
    "http://192.168.1.157:5000/api/webhook",  # ← Change this
    json={"text": transcribed_text}
)
```

---

## 🎯 **Expected Behavior After Fix:**

**Before:**
```
🤖 Sending to LLM: Hello
Error: Connection to 192.168.1.157 timed out
```

**After:**
```
🤖 Sending to LLM: Hello
✅ LLM Response: Oh, you're back. What catastrophe needs my attention now?
```

---

## 🛠️ **Alternative: If localhost Doesn't Work**

**Use WSL IP directly:**
```python
PREPROCESSOR_URL = "http://172.21.130.102:5000/api/webhook"
```

**Note:** This IP can change on reboot. Better to use localhost or set up port forwarding.

---

## 📞 **Preprocessor Status Check:**

**Before starting STT, verify preprocessor is running:**
```bash
# In WSL:
cd ~/timmy-backend/little-timmy/v34
source ~/timmy-backend/.venv/bin/activate
python app.py

# In another terminal:
curl http://localhost:5000/
# Should return HTML
```

---

## 💡 **Quick Reference:**

| What | Where | Port |
|------|-------|------|
| STT Server | Windows | 8888 |
| Preprocessor | WSL | 5000 |
| Ollama | Windows | 11434 |

**STT → Preprocessor:** Use `localhost:5000` (same machine, different environments)

---

## 🎓 **Why localhost Works:**

WSL2 has automatic port forwarding:
- WSL app listens on `:5000`
- Windows can access via `localhost:5000`
- No manual forwarding needed!

---

**Use this guide in your next session to fix the STT server!** 📝✨

