"""
Timmy Service Control Panel
A web-based interface to start/stop all Timmy services with real-time log streaming.
"""

import os
import sys
import subprocess
import threading
import time
import signal
import atexit
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import psutil

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Service configuration
SERVICES = {
    'tts': {
        'name': 'TTS Server',
        'command': r'C:\Users\dsm27\piper\.venv\Scripts\python.exe',
        'args': [r'\\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\tts-server\timmy_speaks_cuda.py'],
        'cwd': r'\\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\tts-server',
        'log_file': 'logs/tts.log',
        'process': None,
        'log_thread': None,
    },
    'stt': {
        'name': 'STT Server',
        'command': r'C:\Users\dsm27\whisper\.venv\Scripts\python.exe',
        'args': [r'\\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\stt-server-v17\timmy_hears.py', '--ai'],
        'cwd': r'\\wsl.localhost\Ubuntu-20.04\home\gearscodeandfire\timmy-backend\little-timmy\stt-server-v17',
        'log_file': 'logs/stt.log',
        'process': None,
        'log_thread': None,
    },
    'ollama': {
        'name': 'Ollama Server',
        'command': 'ollama',
        'args': ['serve'],
        'cwd': None,
        'log_file': 'logs/ollama.log',
        'process': None,
        'log_thread': None,
    },
    'v34': {
        'name': 'LLM Preprocessor (v34)',
        'command': 'wsl',
        'args': ['bash', '-c', 
                 'cd ~/timmy-backend/little-timmy/v34 && source ~/timmy-backend/.venv/bin/activate && python app.py --debug'],
        'cwd': None,
        'log_file': 'logs/v34.log',
        'process': None,
        'log_thread': None,
    },
}

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

def log_reader_thread(service_id):
    """Thread that reads service output and emits to websocket clients."""
    service = SERVICES[service_id]
    process = service['process']
    
    if not process:
        return
    
    try:
        # Read both stdout and stderr
        for line in iter(process.stdout.readline, b''):
            if not line:
                break
            try:
                decoded = line.decode('utf-8', errors='ignore').rstrip()
                if decoded:
                    # Write to log file
                    with open(service['log_file'], 'a', encoding='utf-8') as f:
                        f.write(decoded + '\n')
                    # Emit to websocket
                    socketio.emit('log_output', {
                        'service': service_id,
                        'line': decoded
                    })
            except Exception as e:
                print(f"Error reading line from {service_id}: {e}")
    except Exception as e:
        print(f"Log reader thread error for {service_id}: {e}")
    finally:
        print(f"Log reader thread stopped for {service_id}")

def start_service(service_id):
    """Start a service and begin log streaming."""
    service = SERVICES.get(service_id)
    if not service:
        return {'success': False, 'error': 'Unknown service'}
    
    if service['process'] and service['process'].poll() is None:
        return {'success': False, 'error': 'Service already running'}
    
    try:
        # Clear old log file
        log_path = Path(service['log_file'])
        if log_path.exists():
            log_path.unlink()
        
        # Start process
        print(f"Starting {service_id}: {service['command']} {' '.join(service['args'])}")
        
        process = subprocess.Popen(
            [service['command']] + service['args'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=service['cwd'],
            bufsize=1,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )
        
        service['process'] = process
        
        # Start log reader thread
        log_thread = threading.Thread(target=log_reader_thread, args=(service_id,), daemon=True)
        log_thread.start()
        service['log_thread'] = log_thread
        
        time.sleep(0.5)  # Give it a moment to start
        
        if process.poll() is not None:
            return {'success': False, 'error': 'Process terminated immediately'}
        
        return {'success': True, 'pid': process.pid}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def stop_service(service_id):
    """Stop a running service."""
    service = SERVICES.get(service_id)
    if not service:
        return {'success': False, 'error': 'Unknown service'}
    
    process = service['process']
    if not process or process.poll() is not None:
        service['process'] = None
        return {'success': False, 'error': 'Service not running'}
    
    try:
        # Special handling for Ollama
        if service_id == 'ollama':
            # Try graceful ollama quit first
            try:
                subprocess.run(['ollama', 'quit'], timeout=3, capture_output=True)
            except Exception:
                pass
        
        # Kill process tree
        try:
            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)
            
            # Terminate children first
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            
            # Terminate parent
            parent.terminate()
            
            # Wait for termination
            gone, alive = psutil.wait_procs([parent] + children, timeout=3)
            
            # Force kill if still alive
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            print(f"Error stopping {service_id}: {e}")
        
        service['process'] = None
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_service_status(service_id):
    """Get the current status of a service."""
    service = SERVICES.get(service_id)
    if not service:
        return {'running': False, 'error': 'Unknown service'}
    
    process = service['process']
    if not process:
        return {'running': False, 'pid': None}
    
    if process.poll() is not None:
        service['process'] = None
        return {'running': False, 'pid': None}
    
    return {'running': True, 'pid': process.pid}

@app.route('/')
def index():
    """Render the control panel."""
    return render_template('index.html')

@app.route('/api/services')
def list_services():
    """List all services and their status."""
    result = {}
    for service_id, service in SERVICES.items():
        status = get_service_status(service_id)
        result[service_id] = {
            'name': service['name'],
            'running': status['running'],
            'pid': status.get('pid')
        }
    return jsonify(result)

@app.route('/api/start/<service_id>', methods=['POST'])
def api_start_service(service_id):
    """Start a service."""
    result = start_service(service_id)
    return jsonify(result)

@app.route('/api/stop/<service_id>', methods=['POST'])
def api_stop_service(service_id):
    """Stop a service."""
    result = stop_service(service_id)
    return jsonify(result)

@app.route('/api/logs/<service_id>')
def get_logs(service_id):
    """Get recent logs for a service."""
    service = SERVICES.get(service_id)
    if not service:
        return jsonify({'error': 'Unknown service'}), 404
    
    log_file = Path(service['log_file'])
    if not log_file.exists():
        return jsonify({'lines': []})
    
    try:
        # Get last 100 lines
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            recent = lines[-100:] if len(lines) > 100 else lines
            return jsonify({'lines': [line.rstrip() for line in recent]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def cleanup_services():
    """Stop all running services on exit."""
    print("\n*** Stopping all services...")
    for service_id in SERVICES:
        try:
            stop_service(service_id)
        except Exception as e:
            print(f"Error stopping {service_id}: {e}")
    print("*** All services stopped")

# Register cleanup on exit
atexit.register(cleanup_services)

if __name__ == '__main__':
    print("=" * 60)
    print("Timmy Service Control Panel")
    print("=" * 60)
    print(f"\nControl Panel URL: http://localhost:5555")
    print("\nConfigured Services:")
    for service_id, service in SERVICES.items():
        print(f"  - {service['name']}")
    print("\n" + "=" * 60)
    print("Press Ctrl+C to stop the control panel and all services")
    print("=" * 60 + "\n")
    
    try:
        socketio.run(app, host='0.0.0.0', port=5555, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n*** Keyboard interrupt received")
    finally:
        cleanup_services()

