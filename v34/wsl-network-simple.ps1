# Smart WSL Network Setup with Problem Anticipation
# Run as Administrator - Only updates what's needed

Write-Host "WSL Network Setup - Enhanced Smart Version" -ForegroundColor Cyan

# Configuration based on lessons learned
# Only forward port 5000 (preprocessor LAN access) and 8080 (motor controller routing)
# DO NOT forward 8888 (STT runs on Windows host) or 11434 (Ollama runs on Windows host)
$RequiredPorts = @(5000, 8080)

# Functions
function Get-WSLDistroIP {
    try {
        $ip = wsl -- hostname -I | ForEach-Object { $_.Trim().Split()[0] }
        return $ip
    } catch {
        Write-Host "Error: Could not get WSL IP. Make sure WSL is running." -ForegroundColor Red
        return $null
    }
}

function Test-ProcessRunning {
    param($ProcessName)
    try {
        $process = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
        return $process -ne $null
    } catch {
        return $false
    }
}

function Test-PortInUse {
    param($Port)
    try {
        $connections = netstat -an | Select-String ":$Port "
        return $connections -ne $null
    } catch {
        return $false
    }
}

function Show-ProcessDiagnostics {
    Write-Host "`nProcess Diagnostics:" -ForegroundColor Cyan
    
    # Check STT Server (should be on Windows host, not WSL)
    if (Test-ProcessRunning "python") {
        $pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
        foreach ($proc in $pythonProcesses) {
            if ($proc.CommandLine -like "*8888*") {
                Write-Host "  [OK] STT Server (python) detected on Windows host" -ForegroundColor Green
            }
        }
    }
    
    # Check Ollama (should be on Windows host)
    if (Test-ProcessRunning "ollama") {
        Write-Host "  [OK] Ollama process detected on Windows host" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] Ollama process not detected. Start it with: ollama serve" -ForegroundColor Yellow
    }
    
    # Check port usage
    if (Test-PortInUse 8888) {
        Write-Host "  [OK] Port 8888 in use (STT Server)" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] Port 8888 not in use. STT Server may not be running." -ForegroundColor Yellow
    }
    
    if (Test-PortInUse 11434) {
        Write-Host "  [OK] Port 11434 in use (Ollama)" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] Port 11434 not in use. Ollama may not be running." -ForegroundColor Yellow
    }
}

function Set-OllamaFirewallRule {
    Write-Host "Configuring Ollama firewall rule..." -ForegroundColor Yellow
    
    # Remove existing rule if it exists
    netsh advfirewall firewall delete rule name="Ollama from WSL" 2>$null | Out-Null
    
    # Add new rule allowing WSL subnet to access Ollama on Windows host
    $result = netsh advfirewall firewall add rule name="Ollama from WSL" dir=in action=allow protocol=TCP localport=11434 remoteip=172.21.0.0/16
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Ollama firewall rule configured" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Failed to configure Ollama firewall rule" -ForegroundColor Red
    }
}

function Remove-ProblematicPortForwarding {
    Write-Host "Removing problematic port forwarding rules..." -ForegroundColor Yellow
    
    # Remove port 8888 (STT) and 11434 (Ollama) forwarding if they exist
    # These cause conflicts because the services run on Windows host, not WSL
    $problematicPorts = @(8888, 11434)
    
    foreach ($port in $problematicPorts) {
        $result = netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [FIXED] Removed problematic port $port forwarding" -ForegroundColor Green
        }
    }
}

function Get-ExistingPortForwarding {
    try {
        $output = netsh interface portproxy show v4tov4
        $rules = @{}
        
        if ($output -and $output.Count -gt 0) {
            foreach ($line in $output) {
                if ($line -match "^\s*(\d+)\s+0\.0\.0\.0\s+(\d+)\s+([\d\.]+)") {
                    $listenPort = [int]$matches[1]
                    $connectPort = [int]$matches[2]
                    $connectAddress = $matches[3]
                    $rules[$listenPort] = @{
                        ConnectPort = $connectPort
                        ConnectAddress = $connectAddress
                    }
                }
            }
        }
        return $rules
    } catch {
        return @{}
    }
}

function Test-PortForwardingCurrent {
    param($CurrentIP)
    
    $existingRules = Get-ExistingPortForwarding
    $needsUpdate = $false
    $missingPorts = @()
    $wrongIPPorts = @()
    
    foreach ($port in $RequiredPorts) {
        if ($existingRules.ContainsKey($port)) {
            if ($existingRules[$port].ConnectAddress -ne $CurrentIP) {
                $wrongIPPorts += $port
                $needsUpdate = $true
            }
        } else {
            $missingPorts += $port
            $needsUpdate = $true
        }
    }
    
    return @{
        NeedsUpdate = $needsUpdate
        MissingPorts = $missingPorts
        WrongIPPorts = $wrongIPPorts
        ExistingRules = $existingRules
    }
}

function Show-CurrentStatus {
    param($WSLip, $Analysis)
    
    Write-Host "`nCurrent Status:" -ForegroundColor Cyan
    Write-Host "WSL IP: $WSLip" -ForegroundColor Green
    
    $existingRules = $Analysis.ExistingRules
    if ($existingRules.Count -eq 0) {
        Write-Host "Port Forwarding: None configured" -ForegroundColor Yellow
    } else {
        Write-Host "Port Forwarding Rules:" -ForegroundColor White
        foreach ($port in $RequiredPorts) {
            if ($existingRules.ContainsKey($port)) {
                $rule = $existingRules[$port]
                $status = if ($rule.ConnectAddress -eq $WSLip) { "[OK]" } else { "[BAD]" }
                $color = if ($rule.ConnectAddress -eq $WSLip) { "Green" } else { "Red" }
                Write-Host "  $status Port $port -> $($rule.ConnectAddress):$($rule.ConnectPort)" -ForegroundColor $color
            } else {
                Write-Host "  [MISSING] Port $port -> Not configured" -ForegroundColor Red
            }
        }
    }
    
    # Show problematic ports if they exist
    $problematicPorts = @(8888, 11434)
    foreach ($port in $problematicPorts) {
        if ($existingRules.ContainsKey($port)) {
            Write-Host "  [PROBLEM] Port $port -> $($existingRules[$port].ConnectAddress):$($existingRules[$port].ConnectPort) (Should be removed)" -ForegroundColor Red
        }
    }
}

function Test-ServiceConnectivity {
    param($WSLip)
    
    Write-Host "`nTesting Service Connectivity:" -ForegroundColor Cyan
    
    # Test WSL preprocessor
    try {
        $response = Invoke-WebRequest -Uri "http://$WSLip:5000" -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  [OK] WSL Preprocessor accessible" -ForegroundColor Green
    } catch {
        Write-Host "  [WARNING] WSL Preprocessor not responding on port 5000" -ForegroundColor Yellow
    }
    
    # Test STT Server on Windows host
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8888" -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  [OK] STT Server accessible on Windows host" -ForegroundColor Green
    } catch {
        Write-Host "  [WARNING] STT Server not responding on port 8888" -ForegroundColor Yellow
    }
    
    # Test Ollama on Windows host  
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434" -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  [OK] Ollama accessible on Windows host" -ForegroundColor Green
    } catch {
        Write-Host "  [WARNING] Ollama not responding on port 11434" -ForegroundColor Yellow
    }
}

# Main execution
Write-Host "Starting enhanced network setup with problem anticipation..." -ForegroundColor Yellow

$wslIP = Get-WSLDistroIP
if (-not $wslIP) {
    exit 1
}

# Show process diagnostics
Show-ProcessDiagnostics

# Remove problematic port forwarding that causes conflicts
Remove-ProblematicPortForwarding

# Set up Ollama firewall rule for WSL access
Set-OllamaFirewallRule

# Analyze current state
$analysis = Test-PortForwardingCurrent -CurrentIP $wslIP
Show-CurrentStatus -WSLip $wslIP -Analysis $analysis

if (-not $analysis.NeedsUpdate) {
    Write-Host "`nAll port forwarding rules are up to date!" -ForegroundColor Green
    Write-Host "No changes needed. Your preprocessor should be accessible at: http://192.168.1.157:5000" -ForegroundColor Green
} else {
    Write-Host "`nPort forwarding needs updates:" -ForegroundColor Yellow
    
    if ($analysis.MissingPorts.Count -gt 0) {
        Write-Host "  Missing ports: $($analysis.MissingPorts -join ', ')" -ForegroundColor Yellow
    }
    
    if ($analysis.WrongIPPorts.Count -gt 0) {
        Write-Host "  Wrong IP ports: $($analysis.WrongIPPorts -join ', ')" -ForegroundColor Yellow
    }
    
    Write-Host "`nUpdating port forwarding..." -ForegroundColor Yellow
    
    # Remove existing rules for ports that need updating
    $portsToUpdate = $analysis.MissingPorts + $analysis.WrongIPPorts
    foreach ($port in $portsToUpdate) {
        netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null
    }
    
    # Add new rules
    foreach ($port in $portsToUpdate) {
        $result = netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wslIP
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Port $port forwarding configured" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] Failed to configure port $port forwarding" -ForegroundColor Red
        }
    }
    
    # Setup firewall (only if we updated port forwarding)
    Write-Host "Checking firewall rules..." -ForegroundColor Yellow
    foreach ($port in $portsToUpdate) {
        $ruleName = "WSL Port $port"
        # Remove existing rule if it exists
        netsh advfirewall firewall delete rule name=$ruleName 2>$null | Out-Null
        # Add new rule
        $result = netsh advfirewall firewall add rule name=$ruleName dir=in action=allow protocol=TCP localport=$port
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Firewall rule for port $port configured" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] Failed to configure firewall rule for port $port" -ForegroundColor Red
        }
    }
    
    Write-Host "Port forwarding updated successfully!" -ForegroundColor Green
}

# Always ensure WSL hosts are configured (this is quick)
Write-Host "`nEnsuring WSL hosts configuration..." -ForegroundColor Yellow
$hostsScript = @"
#!/bin/bash
GATEWAY_IP=`$(ip route show default | awk '{print `$3}')
sudo sed -i '/# WSL Network Config/,/# End WSL Network Config/d' /etc/hosts 2>/dev/null
echo "# WSL Network Config" | sudo tee -a /etc/hosts > /dev/null
echo "`$GATEWAY_IP windows-host" | sudo tee -a /etc/hosts > /dev/null
echo "192.168.1.157 windows-host-lan" | sudo tee -a /etc/hosts > /dev/null
echo "192.168.1.139 tts-server" | sudo tee -a /etc/hosts > /dev/null
echo "192.168.1.110 motor-raspi" | sudo tee -a /etc/hosts > /dev/null
echo "# End WSL Network Config" | sudo tee -a /etc/hosts > /dev/null
"@

$hostsScript | wsl -- sudo tee /usr/local/bin/wsl-network-config.sh > $null
wsl -- sudo chmod +x /usr/local/bin/wsl-network-config.sh
wsl -- /usr/local/bin/wsl-network-config.sh

# Test connectivity to all services
Test-ServiceConnectivity -WSLip $wslIP

Write-Host "`nSetup completed!" -ForegroundColor Green
Write-Host "Your preprocessor should be accessible at: http://192.168.1.157:5000" -ForegroundColor Green

# Show final status
Write-Host "`nFinal Status:" -ForegroundColor Cyan
netsh interface portproxy show v4tov4 

Write-Host "`nTroubleshooting Tips:" -ForegroundColor Cyan
Write-Host "- STT Server: Should run on Windows host (port 8888, no forwarding needed)" -ForegroundColor White
Write-Host "- Ollama: Should run on Windows host (port 11434, firewall rule added)" -ForegroundColor White
Write-Host "- TTS Server: Send JSON format {\"text\":\"message\"} to avoid 400/415 errors" -ForegroundColor White
Write-Host "- Preprocessor: WSL port 5000 forwarded to LAN for debugging" -ForegroundColor White 