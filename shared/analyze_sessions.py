#!/usr/bin/env python3
"""
Session-based Latency Analysis for Little Timmy
Shows how latency changes within sessions and correlates with payload size.
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def parse_log(log_file):
    """Parse log and group by session_id."""
    sessions = defaultdict(lambda: defaultdict(list))
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    request_id = entry.get('request_id')
                    session_id = entry.get('metadata', {}).get('session_id')
                    
                    if request_id:
                        sessions[session_id or 'unknown'][request_id].append(entry)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print(f"Error: Log file not found: {log_file}")
        return {}
    
    return sessions

def extract_ollama_stats(events):
    """Extract Ollama-specific stats from a request's events."""
    for event in events:
        if event['event'] == 'v34_ollama_received':
            meta = event.get('metadata', {})
            return {
                'prompt_eval_count': meta.get('prompt_eval_count', 0),
                'eval_count': meta.get('eval_count', 0),
                'prompt_eval_duration_ms': meta.get('prompt_eval_duration_ms', 0),
                'eval_duration_ms': meta.get('eval_duration_ms', 0),
            }
    return None

def extract_prompt_size(events):
    """Extract prompt size from events."""
    for event in events:
        if event['event'] == 'v34_prompt_built':
            meta = event.get('metadata', {})
            return {
                'prompt_chars': meta.get('prompt_chars', 0),
                'prompt_tokens_est': meta.get('prompt_tokens_est', 0),
                'tail_mode': meta.get('tail_mode', False),
            }
    return {'prompt_chars': 0, 'prompt_tokens_est': 0, 'tail_mode': False}

def get_ollama_duration(events):
    """Calculate time spent in Ollama."""
    sent_time = None
    received_time = None
    
    for event in events:
        if event['event'] == 'v34_ollama_sent':
            sent_time = event['timestamp']
        elif event['event'] == 'v34_ollama_received':
            received_time = event['timestamp']
    
    if sent_time and received_time:
        return received_time - sent_time
    return None

def get_total_duration(events):
    """Get end-to-end duration."""
    if len(events) < 2:
        return None
    sorted_events = sorted(events, key=lambda e: e['timestamp'])
    return sorted_events[-1]['timestamp'] - sorted_events[0]['timestamp']

def format_time(seconds):
    """Format time in seconds."""
    if seconds is None:
        return "N/A"
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    else:
        return f"{seconds:.2f}s"

def analyze_session(session_id, requests):
    """Analyze all requests in a session."""
    print(f"\n{'='*100}")
    print(f"SESSION: {session_id}")
    print(f"Total Requests: {len(requests)}")
    print(f"{'='*100}\n")
    
    print(f"{'Req#':>4} | {'Request ID':10} | {'Total':>8} | {'Ollama':>8} | {'Prompt':>8} | {'KV':>6} | {'Eval':>7} | {'Tail':5}")
    print("-" * 100)
    
    request_list = sorted(requests.items(), key=lambda x: min(e['timestamp'] for e in x[1]))
    
    for idx, (request_id, events) in enumerate(request_list, 1):
        total_dur = get_total_duration(events)
        ollama_dur = get_ollama_duration(events)
        prompt_info = extract_prompt_size(events)
        ollama_stats = extract_ollama_stats(events)
        
        # Get KV cache info
        kv_info = "NO"
        eval_tokens = "N/A"
        if ollama_stats:
            eval_tokens = str(ollama_stats.get('prompt_eval_count', 0))
            if ollama_stats.get('prompt_eval_count', 0) == 0:
                kv_info = "YES"  # If prompt_eval_count is 0, KV cache was fully used
        
        tail_mode = "Yes" if prompt_info.get('tail_mode') else "No"
        prompt_tokens = prompt_info.get('prompt_tokens_est', 0)
        
        print(f"{idx:>4} | {request_id:10} | {format_time(total_dur):>8} | {format_time(ollama_dur):>8} | "
              f"{prompt_tokens:>7}t | {kv_info:>6} | {eval_tokens:>7} | {tail_mode:5}")
    
    # Calculate trends
    print("\n" + "="*100)
    print("SESSION ANALYSIS:")
    print("="*100)
    
    ollama_times = []
    prompt_sizes = []
    
    for request_id, events in requests.items():
        ollama_dur = get_ollama_duration(events)
        prompt_info = extract_prompt_size(events)
        if ollama_dur:
            ollama_times.append(ollama_dur)
            prompt_sizes.append(prompt_info.get('prompt_tokens_est', 0))
    
    if ollama_times:
        print(f"\nOllama Processing Times:")
        print(f"  First request:  {format_time(ollama_times[0])}")
        if len(ollama_times) > 1:
            print(f"  Last request:   {format_time(ollama_times[-1])}")
            print(f"  Average:        {format_time(sum(ollama_times) / len(ollama_times))}")
            print(f"  Min:            {format_time(min(ollama_times))}")
            print(f"  Max:            {format_time(max(ollama_times))}")
        
        print(f"\nPrompt Sizes:")
        print(f"  First request:  {prompt_sizes[0]} tokens (est)")
        if len(prompt_sizes) > 1:
            print(f"  Last request:   {prompt_sizes[-1]} tokens (est)")
            print(f"  Average:        {sum(prompt_sizes) // len(prompt_sizes)} tokens (est)")
        
        # Check for KV cache effectiveness
        with_kv = [t for i, t in enumerate(ollama_times) if i > 0]  # Requests after first
        if with_kv:
            print(f"\nKV Cache Impact:")
            print(f"  First request (no cache):  {format_time(ollama_times[0])}")
            print(f"  Avg with cache:            {format_time(sum(with_kv) / len(with_kv))}")
            speedup = ollama_times[0] / (sum(with_kv) / len(with_kv)) if with_kv else 1
            print(f"  Speedup factor:            {speedup:.2f}x")

def main():
    log_file = Path(__file__).parent / "latency.log"
    
    if not log_file.exists():
        print(f"No timing data found: {log_file}")
        return
    
    sessions = parse_log(log_file)
    
    if not sessions:
        print("No session data found in latency log")
        return
    
    print(f"\n{'='*100}")
    print("LITTLE TIMMY - SESSION LATENCY ANALYSIS")
    print(f"{'='*100}")
    print(f"Total Sessions Found: {len(sessions)}")
    
    # Analyze each session
    for session_id, requests in sessions.items():
        analyze_session(session_id, requests)
    
    print("\n" + "="*100)
    print("ANALYSIS COMPLETE")
    print("="*100)
    print("\n💡 Key Insights:")
    print("  - Compare 'Ollama' times across requests in same session")
    print("  - 'KV: YES' means cache was used (faster)")
    print("  - 'Prompt' shows estimated tokens sent to Ollama")
    print("  - 'Eval' shows how many tokens Ollama actually processed")
    print("  - Watch for prompt size growth affecting Ollama time")
    print("\n")

if __name__ == "__main__":
    main()

