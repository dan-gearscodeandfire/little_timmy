#!/usr/bin/env python3
import requests
import json

url = "http://localhost:5000/api/webhook"
payload = {"text": "Hey little Timmy, test message"}

print("Testing webhook...")
try:
    response = requests.post(url, json=payload, timeout=10)
    print(f"✅ Status: {response.status_code}")
    print(f"✅ Response: {response.json()}")
except Exception as e:
    print(f"❌ Error: {e}")

