#!/usr/bin/env python3
"""
Latency Analysis Tool for Little Timmy
Analyzes the centralized latency log and shows timing breakdown.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def parse_log(log_file):
    """Parse the latency log file and group by request_id."""
    requests = defaultdict(list)
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    request_id = entry.get('request_id')
                    if request_id:
                        requests[request_id].append(entry)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print(f"Error: Log file not found: {log_file}")
        return {}
    
    return requests

def analyze_request(events):
    """Analyze timing for a single request."""
    if not events:
        return None
    
    # Sort by timestamp
    events = sorted(events, key=lambda e: e['timestamp'])
    
    # Build timeline
    timeline = []
    for event in events:
        timeline.append({
            'timestamp': event['timestamp'],
            'service': event['service'],
            'event': event['event'],
            'metadata': event.get('metadata', {})
        })
    
    # Calculate deltas
    if len(timeline) < 2:
        return {'events': timeline, 'deltas': {}, 'total': 0}
    
    start_time = timeline[0]['timestamp']
    deltas = {}
    
    for i in range(1, len(timeline)):
        prev = timeline[i-1]
        curr = timeline[i]
        delta = curr['timestamp'] - prev['timestamp']
        delta_name = f"{prev['event']} → {curr['event']}"
        deltas[delta_name] = delta
    
    total_time = timeline[-1]['timestamp'] - start_time
    
    return {
        'events': timeline,
        'deltas': deltas,
        'total': total_time,
        'start_time': datetime.fromtimestamp(start_time).strftime('%H:%M:%S')
    }

def format_time(seconds):
    """Format time in seconds to readable string."""
    if seconds < 0.001:
        return f"{seconds * 1000000:6.0f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:6.0f}ms"
    else:
        return f"{seconds:6.2f}s "

def print_analysis(request_id, analysis):
    """Print formatted analysis for a single request."""
    print(f"\n{'='*80}")
    print(f"Request ID: {request_id}")
    print(f"Start Time: {analysis['start_time']}")
    print(f"Total Duration: {format_time(analysis['total'])}")
    print(f"{'='*80}")
    
    print("\nTIMELINE:")
    print(f"{'Time':>8} | {'Service':10} | {'Event':40}")
    print("-" * 80)
    
    start = analysis['events'][0]['timestamp']
    for event in analysis['events']:
        elapsed = event['timestamp'] - start
        print(f"{format_time(elapsed)} | {event['service']:10} | {event['event']:40}")
    
    print("\nDELTAS (Time between events):")
    print(f"{'Duration':>8} | {'Transition':60}")
    print("-" * 80)
    
    for delta_name, delta_value in analysis['deltas'].items():
        print(f"{format_time(delta_value)} | {delta_name[:58]}")
    
    print(f"\n{'TOTAL':>8} | {format_time(analysis['total'])}")

def print_summary(all_analyses):
    """Print summary statistics across all requests."""
    if not all_analyses:
        return
    
    total_times = [a['total'] for a in all_analyses.values() if a]
    
    print(f"\n{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}")
    print(f"Total Requests Analyzed: {len(total_times)}")
    
    if total_times:
        avg_time = sum(total_times) / len(total_times)
        min_time = min(total_times)
        max_time = max(total_times)
        
        print(f"\nEnd-to-End Latency:")
        print(f"  Average: {format_time(avg_time)}")
        print(f"  Minimum: {format_time(min_time)}")
        print(f"  Maximum: {format_time(max_time)}")
        
        # Calculate average for common deltas
        all_deltas = defaultdict(list)
        for analysis in all_analyses.values():
            if analysis:
                for delta_name, delta_value in analysis.get('deltas', {}).items():
                    all_deltas[delta_name].append(delta_value)
        
        if all_deltas:
            print(f"\nAverage Step Times:")
            for delta_name, values in sorted(all_deltas.items()):
                avg = sum(values) / len(values)
                print(f"  {format_time(avg)} | {delta_name[:60]}")

def main():
    log_file = Path(__file__).parent / "latency.log"
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--clear':
            # Clear the log file
            try:
                log_file.unlink()
                print(f"Cleared latency log: {log_file}")
                return
            except FileNotFoundError:
                print("Log file doesn't exist, nothing to clear")
                return
        elif sys.argv[1] == '--tail':
            # Show only last N requests
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            requests = parse_log(log_file)
            request_ids = sorted(requests.keys())[-n:]
        elif sys.argv[1] == '--request':
            # Show specific request ID
            target_id = sys.argv[2]
            requests = parse_log(log_file)
            request_ids = [target_id] if target_id in requests else []
        else:
            print("Usage:")
            print("  python analyze_latency.py              # Analyze all requests")
            print("  python analyze_latency.py --tail [N]   # Show last N requests (default 5)")
            print("  python analyze_latency.py --request ID # Show specific request")
            print("  python analyze_latency.py --clear      # Clear log file")
            return
    else:
        # Analyze all
        requests = parse_log(log_file)
        request_ids = sorted(requests.keys())
    
    if not request_ids:
        print("No timing data found in latency log")
        print(f"Log file: {log_file}")
        return
    
    # Analyze each request
    analyses = {}
    for request_id in request_ids:
        events = requests[request_id]
        analysis = analyze_request(events)
        if analysis:
            analyses[request_id] = analysis
            print_analysis(request_id, analysis)
    
    # Print summary if multiple requests
    if len(analyses) > 1:
        print_summary(analyses)

if __name__ == "__main__":
    main()

