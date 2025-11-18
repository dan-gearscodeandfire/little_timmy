#not sure how this works in v17 implementation or v16, it was for debugging purposes
import requests
import json
import re
import os
import time

# --- This function attempts to find the Windows Host IP from inside WSL ---
def get_windows_host_ip():
    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                if "nameserver" in line:
                    # This is the IP of the WSL virtual DNS server, which is the host.
                    return line.split()[1]
    except FileNotFoundError:
        return None
    return None

# --- Configuration ---
MODEL_NAME = "llama3.2:3b-instruct-q4_K_M"
WSL_URL = "http://localhost:11434/api/generate"

windows_host_ip = get_windows_host_ip()
WINDOWS_URL = f"http://{windows_host_ip}:11434/api/generate" if windows_host_ip else None

PAYLOAD = {
    "model": MODEL_NAME,
    "prompt": "Hi",
    "stream": False
}

# --- Test 1: Connect to localhost (inside WSL) ---
print(f"--- [TEST 1: WSL Communication] ---")
print(f"Attempting to connect to the Ollama server inside WSL at: {WSL_URL}")
try:
    start_time = time.time()
    response_wsl = requests.post(WSL_URL, json=PAYLOAD, timeout=5)
    end_time = time.time()
    print(f"SUCCESS: Received status code {response_wsl.status_code} from {WSL_URL} in {end_time - start_time:.3f}s")
    if response_wsl.status_code != 200:
        print(f"NOTE: The server responded with an error: {response_wsl.text}")

except requests.exceptions.RequestException as e:
    print(f"FAILED: Could not connect to {WSL_URL}. Error: {e}")
    print("This likely means the Ollama server is not running inside WSL.")

print("\n" + "="*50 + "\n")


# --- Test 2: Connect to Windows Host (test forwarding theory) ---
print(f"--- [TEST 2: Windows Port Forwarding] ---")
if WINDOWS_URL:
    print(f"Attempting to connect to a potential Ollama server on the Windows host at: {WINDOWS_URL}")
    print("This tests your theory that localhost:11434 is being forwarded to Windows.")
    try:
        start_time = time.time()
        response_win = requests.post(WINDOWS_URL, json=PAYLOAD, timeout=5)
        end_time = time.time()
        print(f"SUCCESS: Received status code {response_win.status_code} from {WINDOWS_URL} in {end_time - start_time:.3f}s")
        print("\nThis means a service (likely the Windows version of Ollama) is running on your Windows host and is reachable from WSL.")
        print("If Test 1 ALSO succeeded, it means you may have TWO Ollama servers running (one in Windows, one in WSL).")
        print("Please ensure the Windows Ollama service is stopped to avoid conflicts.")


    except requests.exceptions.RequestException as e:
        print(f"FAILED: Could not connect to {WINDOWS_URL}. Error: {e}")
        print("\nThis result suggests that either the Windows Ollama server is not running, or that there is no port forwarding from WSL to Windows on port 11434.")
else:
    print("Could not determine Windows host IP from /etc/resolv.conf. Skipping Test 2.") 