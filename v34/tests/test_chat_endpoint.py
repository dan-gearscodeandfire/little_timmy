#!/usr/bin/env python3
"""
Diagnostic tool to test ollama chat endpoint and identify JSON response issues
"""

import requests
import json
import sys
import config

def test_simple_chat():
    """Test basic chat endpoint functionality"""
    print("=== Testing Basic Chat Endpoint ===")
    
    payload = {
        "model": config.MODEL_NAME,
        "messages": [
            {
                "role": "system", 
                "content": "You are a helpful assistant. Always respond with valid JSON in this format: {\"response\": \"your message\", \"metadata\": {\"importance\": 1, \"topic\": \"test\", \"tags\": [\"test\"]}}"
            },
            {
                "role": "user", 
                "content": "Hello, this is a test message."
            }
        ],
        "stream": False,
        "options": {
            "num_ctx": 4096,
            "temperature": 0.7
        }
    }
    
    try:
        response = requests.post(config.OLLAMA_CHAT_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        print(f"Raw response: {json.dumps(result, indent=2)}")
        
        if 'message' in result and 'content' in result['message']:
            content = result['message']['content']
            print(f"Content: {content}")
            
            # Try to parse as JSON
            try:
                parsed = json.loads(content)
                print("✅ JSON parsing successful!")
                print(f"Parsed: {json.dumps(parsed, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                
    except Exception as e:
        print(f"❌ Chat endpoint test failed: {e}")

def test_multiple_exchanges():
    """Test multiple message exchanges to see when JSON breaks down"""
    print("\n=== Testing Multiple Message Exchanges ===")
    
    messages = [
        {
            "role": "system", 
            "content": "You are Little Timmy. ALWAYS respond with valid JSON: {\"response\": \"your message\", \"metadata\": {\"importance\": 0-2, \"topic\": \"category\", \"tags\": [\"tag1\"]}}"
        }
    ]
    
    test_messages = [
        "Hello",
        "How are you?", 
        "Tell me about yourself",
        "What's your favorite color?",
        "Do you like programming?"
    ]
    
    for i, user_msg in enumerate(test_messages):
        print(f"\n--- Exchange {i+1}: {user_msg} ---")
        
        # Add user message
        messages.append({"role": "user", "content": user_msg})
        
        payload = {
            "model": config.MODEL_NAME,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": 4096,
                "temperature": 0.7
            }
        }
        
        try:
            response = requests.post(config.OLLAMA_CHAT_API_URL, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'message' in result and 'content' in result['message']:
                content = result['message']['content']
                print(f"Raw: {content}")
                
                # Try to parse as JSON
                try:
                    parsed = json.loads(content)
                    print("✅ JSON valid")
                    
                    # Add assistant response to conversation
                    messages.append({"role": "assistant", "content": content})
                    
                except json.JSONDecodeError:
                    print("❌ JSON invalid - conversation may be corrupted")
                    # Still add to conversation to see impact
                    messages.append({"role": "assistant", "content": content})
                    
        except Exception as e:
            print(f"❌ Request failed: {e}")
            break

def test_system_prompt_variations():
    """Test different system prompt approaches"""
    print("\n=== Testing System Prompt Variations ===")
    
    prompts = [
        # Current approach
        "You are Little Timmy. ALWAYS respond with valid JSON: {\"response\": \"message\", \"metadata\": {\"importance\": 1, \"topic\": \"test\", \"tags\": [\"test\"]}}",
        
        # More explicit
        "You are Little Timmy. Your response must be ONLY a JSON object with no other text. Format: {\"response\": \"your message here\", \"metadata\": {\"importance\": 1, \"topic\": \"category\", \"tags\": [\"tag1\"]}}",
        
        # Generate-style approach in chat
        "You are Little Timmy. Respond to the user, then format your response as JSON: {\"response\": \"your message\", \"metadata\": {\"importance\": 1, \"topic\": \"test\", \"tags\": [\"test\"]}}",
        
        # Simple approach
        "Respond with JSON only: {\"response\": \"your message\", \"metadata\": {\"importance\": 1, \"topic\": \"test\", \"tags\": [\"test\"]}}"
    ]
    
    for i, prompt in enumerate(prompts):
        print(f"\n--- Prompt {i+1} ---")
        print(f"System: {prompt[:50]}...")
        
        payload = {
            "model": config.MODEL_NAME,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "stream": False,
            "options": {
                "num_ctx": 4096,
                "temperature": 0.7
            }
        }
        
        try:
            response = requests.post(config.OLLAMA_CHAT_API_URL, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'message' in result and 'content' in result['message']:
                content = result['message']['content']
                print(f"Response: {content[:100]}...")
                
                try:
                    parsed = json.loads(content)
                    print("✅ JSON valid")
                except json.JSONDecodeError:
                    print("❌ JSON invalid")
                    
        except Exception as e:
            print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print(f"Testing ollama chat endpoint with model: {config.MODEL_NAME}")
    print(f"Chat API URL: {config.OLLAMA_CHAT_API_URL}")
    
    test_simple_chat()
    test_multiple_exchanges() 
    test_system_prompt_variations()
    
    print("\n=== Diagnostic Complete ===") 