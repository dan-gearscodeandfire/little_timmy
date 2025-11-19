#!/bin/bash
echo "Testing webhook endpoint..."
curl -X POST http://localhost:5000/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "test message from script"}' \
  -w "\nHTTP Status: %{http_code}\n"

