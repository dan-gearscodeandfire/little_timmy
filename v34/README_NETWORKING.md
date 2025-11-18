# WSL Preprocessor Networking Setup

This guide provides comprehensive instructions for setting up reliable networking for the WSL2 Ubuntu preprocessor application.

## Overview

The preprocessor needs to communicate with several services:
- **Ollama LLM Server**: Windows host on port 11434
- **STT Server**: Windows host on port 8888
- **TTS Server**: External server at 192.168.1.139:5000
- **Motor Controller**: Raspberry Pi at 192.168.1.110:8080
- **PostgreSQL Database**: Local WSL on port 5433

## Files Created

### 1. `wsl-network-setup.ps1` (Windows PowerShell Script)
**Location**: Save on Windows host (e.g., `C:\Scripts\wsl-network-setup.ps1`)
**Purpose**: Configures Windows port forwarding, firewall rules, and WSL networking

### 2. `startup.sh` (WSL Bash Script)
**Location**: WSL project directory (`/home/gearscodeandfire/timmy-backend/v19/startup.sh`)
**Purpose**: Complete startup script for the preprocessor with networking setup

### 3. `test_connectivity.py` (Python Test Script)
**Location**: WSL project directory (`/home/gearscodeandfire/timmy-backend/v19/test_connectivity.py`)
**Purpose**: Tests connectivity to all required services

### 4. `config.py` (Updated Configuration)
**Location**: WSL project directory (`/home/gearscodeandfire/timmy-backend/v19/config.py`)
**Purpose**: Updated to use hostname-based URLs instead of hardcoded IPs

## Setup Instructions

### Step 1: Windows Host Setup

1. **Save the PowerShell script** on your Windows 11 host:
   ```powershell
   # Create directory
   mkdir C:\Scripts
   
   # Save wsl-network-setup.ps1 in C:\Scripts\
   ```

2. **Run the setup script as Administrator**:
   ```powershell
   # Open PowerShell as Administrator
   cd C:\Scripts
   .\wsl-network-setup.ps1 -Setup
   ```

3. **For automatic startup** (optional):
   ```powershell
   # This creates a scheduled task to run on login
   .\wsl-network-setup.ps1 -Auto
   ```

### Step 2: WSL Environment Setup

1. **Make scripts executable**:
   ```bash
   chmod +x startup.sh
   chmod +x test_connectivity.py
   ```

2. **Test connectivity**:
   ```bash
   ./test_connectivity.py
   ```

3. **Start the preprocessor**:
   ```bash
   ./startup.sh
   ```

## Usage

### PowerShell Script Commands

```powershell
# Setup networking (requires Administrator)
.\wsl-network-setup.ps1 -Setup

# Setup with auto-start configuration
.\wsl-network-setup.ps1 -Auto

# Check current status
.\wsl-network-setup.ps1 -Status

# Clean up (removes all rules)
.\wsl-network-setup.ps1 -Cleanup
```

### WSL Startup Script

```bash
# Standard startup
./startup.sh

# Debug mode
./startup.sh --debug
```

### Connectivity Testing

```bash
# Test all services in parallel
./test_connectivity.py

# Test sequentially
./test_connectivity.py --sequential

# Export detailed report
./test_connectivity.py --export
```

## What the Scripts Do

### PowerShell Script (`wsl-network-setup.ps1`)

1. **Detects WSL IP address** automatically
2. **Creates port forwarding rules**:
   - 5000 → WSL (Preprocessor)
   - 8888 → WSL (STT Server)
   - 11434 → WSL (Ollama LLM)
3. **Configures Windows Firewall** rules
4. **Creates WSL network configuration script** at `/usr/local/bin/wsl-network-config.sh`
5. **Updates WSL `/etc/hosts`** with hostname mappings:
   - `windows-host` → Dynamic gateway IP
   - `windows-host-lan` → 192.168.1.157
   - `tts-server` → 192.168.1.139
   - `motor-raspi` → 192.168.1.110
6. **Adds persistence** to `~/.bashrc` for automatic network configuration

### Startup Script (`startup.sh`)

1. **Checks prerequisites** (Python, pip, required files)
2. **Sets up virtual environment** if needed
3. **Installs dependencies** from requirements.txt
4. **Configures network** using the network configuration script
5. **Tests service connectivity**
6. **Starts the Flask application**

### Test Script (`test_connectivity.py`)

1. **Tests TCP connections** to all required services
2. **Tests HTTP endpoints** where available
3. **Tests specific APIs** (Ollama, database)
4. **Provides detailed reports** with colored output
5. **Exports JSON reports** for analysis

## Network Configuration Details

### Hostname Mappings

The scripts automatically configure these hostname mappings in WSL:

```
# In /etc/hosts
<gateway-ip> windows-host          # Dynamic IP for Windows host
192.168.1.157 windows-host-lan     # Static LAN IP
192.168.1.139 tts-server           # TTS server
192.168.1.110 motor-raspi          # Motor controller
```

### Port Forwarding Rules

Windows automatically forwards these ports to WSL:

```
Listen Port  → WSL Port  │ Purpose
5000        → 5000       │ Preprocessor web interface
8888        → 8888       │ STT server
11434       → 11434      │ Ollama LLM server
```

## Troubleshooting

### Common Issues

1. **WSL IP changes**: The scripts automatically detect and update IP addresses
2. **Firewall blocking**: Scripts configure Windows Firewall automatically
3. **Service not reachable**: Use `test_connectivity.py` to diagnose issues
4. **Permission errors**: Ensure PowerShell script runs as Administrator

### Manual Diagnostics

```bash
# Check current network configuration
cat /etc/hosts | grep "WSL Network Config" -A 5

# Test individual services
ping windows-host
ping tts-server
ping motor-raspi

# Check port availability
nc -zv windows-host 11434
nc -zv tts-server 5000
nc -zv motor-raspi 8080
```

### Reset Network Configuration

```powershell
# On Windows (as Administrator)
.\wsl-network-setup.ps1 -Cleanup
.\wsl-network-setup.ps1 -Setup
```

## Persistence

The setup includes persistence across reboots:

1. **Windows**: Scheduled task automatically runs setup on login (with `-Auto` flag)
2. **WSL**: Network configuration added to `~/.bashrc` for automatic setup
3. **Virtual Environment**: Created once and reused
4. **Dependencies**: Installed once and maintained

## Service URLs

After setup, services are accessible via:

- **Preprocessor Web UI**: `http://192.168.1.157:5000`
- **Ollama API**: `http://windows-host:11434/api/generate`
- **STT Server**: `http://windows-host:8888/`
- **TTS Server**: `http://tts-server:5000/`
- **Motor Controller**: `http://motor-raspi:8080/`

## Security Considerations

1. **Firewall Rules**: Only necessary ports are opened
2. **IP Restrictions**: Services bind to specific interfaces
3. **Authentication**: Database uses password authentication
4. **Network Isolation**: WSL operates in isolated network namespace

## Monitoring

Use the status and test commands regularly:

```bash
# Daily health check
./test_connectivity.py

# Weekly network status
# On Windows:
.\wsl-network-setup.ps1 -Status
```

This setup provides a robust, persistent networking solution for your WSL2 preprocessor application. 