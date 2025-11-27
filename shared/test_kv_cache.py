#!/usr/bin/env python3
"""
Test script to verify Ollama KV cache behavior.
Tests different configurations to find what works.
"""

import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b-instruct-q4_K_M"

def test_with_raw_mode():
    """Test 1: Using raw=True (current implementation)"""
    print("\n" + "="*80)
    print("TEST 1: raw=True mode (current implementation)")
    print("="*80)
    
    payload = {
        "model": MODEL,
        "prompt": "Say 'Hello' and nothing else.",
        "raw": True,
        "stream": False,  # Non-streaming for simplicity
        "options": {"num_ctx": 8000}
    }
    
    print(f"Sending: {json.dumps(payload, indent=2)}")
    
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        print(f"\nResponse keys: {list(result.keys())}")
        print(f"Context present: {'context' in result}")
        if 'context' in result:
            ctx = result['context']
            print(f"Context type: {type(ctx)}")
            print(f"Context length: {len(ctx) if ctx else 0}")
        else:
            print("❌ NO CONTEXT FIELD IN RESPONSE")
        
        print(f"\nPrompt eval count: {result.get('prompt_eval_count', 'N/A')}")
        print(f"Response: {result.get('response', 'N/A')[:100]}")
        
        return result.get('context')
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_without_raw_mode():
    """Test 2: Without raw=True"""
    print("\n" + "="*80)
    print("TEST 2: Without raw mode")
    print("="*80)
    
    payload = {
        "model": MODEL,
        "prompt": "Say 'Hello' and nothing else.",
        "stream": False,
        "options": {"num_ctx": 8000}
    }
    
    print(f"Sending: {json.dumps(payload, indent=2)}")
    
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        print(f"\nResponse keys: {list(result.keys())}")
        print(f"Context present: {'context' in result}")
        if 'context' in result:
            ctx = result['context']
            print(f"Context type: {type(ctx)}")
            print(f"Context length: {len(ctx) if ctx else 0}")
        else:
            print("❌ NO CONTEXT FIELD IN RESPONSE")
        
        print(f"\nPrompt eval count: {result.get('prompt_eval_count', 'N/A')}")
        print(f"Response: {result.get('response', 'N/A')[:100]}")
        
        return result.get('context')
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_with_streaming():
    """Test 3: Streaming mode (current implementation)"""
    print("\n" + "="*80)
    print("TEST 3: Streaming with raw=True (exact current implementation)")
    print("="*80)
    
    payload = {
        "model": MODEL,
        "prompt": "Say 'Hello' and nothing else.",
        "raw": True,
        "stream": True,
        "options": {"num_ctx": 8000}
    }
    
    print(f"Sending: {json.dumps(payload, indent=2)}")
    
    try:
        with requests.post(OLLAMA_URL, json=payload, timeout=30, stream=True) as resp:
            resp.raise_for_status()
            
            for line in resp.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line.decode('utf-8'))
                
                if chunk.get('done'):
                    print(f"\nDone chunk keys: {list(chunk.keys())}")
                    print(f"Context present: {'context' in chunk}")
                    
                    if 'context' in chunk:
                        ctx = chunk.get('context')
                        print(f"Context type: {type(ctx)}")
                        print(f"Context length: {len(ctx) if ctx else 0}")
                        print(f"✅ CONTEXT RETURNED!")
                        return ctx
                    else:
                        print("❌ NO CONTEXT IN DONE CHUNK")
                        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_with_context_reuse(previous_context):
    """Test 4: Reusing context from previous call"""
    if not previous_context:
        print("\n⚠️ Skipping Test 4: No context from previous tests")
        return
    
    print("\n" + "="*80)
    print("TEST 4: Reusing context array")
    print("="*80)
    
    payload = {
        "model": MODEL,
        "prompt": "Now say 'Goodbye'.",
        "raw": True,
        "stream": False,
        "context": previous_context,
        "options": {"num_ctx": 8000}
    }
    
    print(f"Context length being sent: {len(previous_context)}")
    
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        print(f"\nPrompt eval count: {result.get('prompt_eval_count', 'N/A')}")
        print(f"Eval count: {result.get('eval_count', 'N/A')}")
        
        if result.get('prompt_eval_count', 1) == 0:
            print("✅ KV CACHE WORKING! prompt_eval_count = 0")
        else:
            print(f"⚠️ KV cache partial: evaluated {result.get('prompt_eval_count')} tokens")
        
        print(f"Response: {result.get('response', 'N/A')[:100]}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("="*80)
    print("OLLAMA KV CACHE DIAGNOSTIC TEST")
    print("="*80)
    print(f"Testing against: {OLLAMA_URL}")
    print(f"Model: {MODEL}")
    print("\nThis will run 4 tests to determine why KV cache isn't working.\n")
    
    # Test different configurations
    ctx1 = test_with_raw_mode()
    ctx2 = test_without_raw_mode()
    ctx3 = test_with_streaming()
    
    # Test context reuse with whichever worked
    context_to_reuse = ctx1 or ctx2 or ctx3
    if context_to_reuse:
        test_with_context_reuse(context_to_reuse)
    
    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)
    
    if ctx1:
        print("✅ raw=True (non-streaming) returns context")
    if ctx2:
        print("✅ Without raw (non-streaming) returns context")
    if ctx3:
        print("✅ Streaming with raw=True returns context")
    
    if not (ctx1 or ctx2 or ctx3):
        print("\n❌ NONE OF THE TESTS RETURNED CONTEXT!")
        print("\nPossible issues:")
        print("1. Ollama version doesn't support context arrays")
        print("2. Model doesn't support context")
        print("3. API configuration issue")
        print("\nTry: ollama pull llama3.2:3b-instruct-q4_K_M")
        print("Or upgrade Ollama: curl https://ollama.ai/install.sh | sh")

if __name__ == "__main__":
    main()

