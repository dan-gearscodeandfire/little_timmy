#v17/test_request.py - not sure how this works in v17 implementation or v16, it was for debugging purposes

import requests
import time

# Use the same model name as your config
# Make sure this is correct
MODEL_NAME = "llama3.2:3b-instruct-q4_K_M" 
OLLAMA_API_URL = "http://localhost:11434/api/generate"

payload = {
    "model": MODEL_NAME,
    "prompt": "Hi",
    "stream": False
}

print("Making a single, clean request to Ollama...")

try:
    # First request might be slow due to model loading
    print("Sending warm-up request...")
    requests.post(OLLAMA_API_URL, json=payload, timeout=5)
    print("Warm-up complete.")
    
    time.sleep(1) # Small delay

    # Now we time the second request
    start_time = time.time()
    
    response = requests.post(OLLAMA_API_URL, json=payload, timeout=5)
    response.raise_for_status() # Check for HTTP errors
    
    end_time = time.time()
    
    print("\n--- TEST RESULT ---")
    print(f"Time taken for the timed request: {end_time - start_time:.3f} seconds")
    print("-------------------\n")
    # print("Response from server:")
    # print(response.text)

except requests.exceptions.RequestException as e:
    print(f"\nAn error occurred: {e}") 