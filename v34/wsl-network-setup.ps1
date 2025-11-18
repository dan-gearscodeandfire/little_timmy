# ===============================================================================
# WSL Network Setup Script - ADVANCED VERSION with Auto-Start Capability
# ===============================================================================
#
# PURPOSE:
#   Automatically configures WSL2 networking for the preprocessor application
#   This is the ADVANCED version with scheduled task auto-start functionality
#
# WHAT IT DOES:
#   1. Sets up Windows port forwarding (5000, 8888, 8080, 11434)
#   2. Configures Windows Firewall rules
#   3. Updates WSL /etc/hosts with hostname mappings
#   4. OPTIONALLY creates Windows scheduled task for auto-start on login
#
# WHEN TO USE:
#   - Use wsl-network-simple.ps1 for manual runs (recommended for most cases)
#   - Use THIS script if you want automatic network setup on Windows login
#
# USAGE:
#   .\wsl-network-setup.ps1 -Setup         # One-time setup
#   .\wsl-network-setup.ps1 -Auto          # Setup + create auto-start task
#   .\wsl-network-setup.ps1 -Status        # Show current status
#   .\wsl-network-setup.ps1 -Cleanup       # Remove all rules and tasks
#
# REQUIREMENTS:
#   - Run as Administrator
#   - WSL2 with Ubuntu-20.04 running
#
# ===============================================================================

param(
    [switch]$Setup,
    [switch]$Cleanup,
    [switch]$Status,
    [switch]$Auto
)

# Configuration
$WSL_DISTRO = "Ubuntu-20.04"
$REQUIRED_PORTS = @(5000, 8888, 8080, 11434)

# Functions
function Write-Message {
    param($Text, $Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Test-IsAdmin {
    return ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-WSLDistroIP {
    try {
        $ip = wsl -d $WSL_DISTRO -- hostname -I | ForEach-Object { $_.Trim().Split()[0] }
        return $ip
    } catch {
        Write-Message "Error: Could not get WSL IP. Make sure WSL is running." "Red"
        return $null
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
    
    foreach ($port in $REQUIRED_PORTS) {
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
    
    Write-Message "`nCurrent Status:" "Cyan"
    Write-Message "WSL IP: $WSLip" "Green"
    
    $existingRules = $Analysis.ExistingRules
    if ($existingRules.Count -eq 0) {
        Write-Message "Port Forwarding: None configured" "Yellow"
    } else {
        Write-Message "Port Forwarding Rules:" "White"
        foreach ($port in $REQUIRED_PORTS) {
            if ($existingRules.ContainsKey($port)) {
                $rule = $existingRules[$port]
                $status = if ($rule.ConnectAddress -eq $WSLip) { "[OK]" } else { "[BAD]" }
                $color = if ($rule.ConnectAddress -eq $WSLip) { "Green" } else { "Red" }
                Write-Message "  $status Port $port -> $($rule.ConnectAddress):$($rule.ConnectPort)" $color
            } else {
                Write-Message "  [MISSING] Port $port -> Not configured" "Red"
            }
        }
    }
}

function Setup-Network {
    param($WSLip)
    
    Write-Message "Setting up WSL network..." "Yellow"
    
    # Analyze current state
    $analysis = Test-PortForwardingCurrent -CurrentIP $WSLip
    Show-CurrentStatus -WSLip $WSLip -Analysis $analysis
    
    if (-not $analysis.NeedsUpdate) {
        Write-Message "`nAll port forwarding rules are up to date!" "Green"
        return $true
    } else {
        Write-Message "`nPort forwarding needs updates:" "Yellow"
        
        if ($analysis.MissingPorts.Count -gt 0) {
            Write-Message "  Missing ports: $($analysis.MissingPorts -join ', ')" "Yellow"
        }
        
        if ($analysis.WrongIPPorts.Count -gt 0) {
            Write-Message "  Wrong IP ports: $($analysis.WrongIPPorts -join ', ')" "Yellow"
        }
        
        Write-Message "`nUpdating port forwarding..." "Yellow"
        
        # Remove existing rules for ports that need updating
        $portsToUpdate = $analysis.MissingPorts + $analysis.WrongIPPorts
        foreach ($port in $portsToUpdate) {
            netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null
        }
        
        # Add new rules
        foreach ($port in $portsToUpdate) {
            netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$WSLip
        }
        
        # Setup firewall (only if we updated port forwarding)
        Write-Message "Checking firewall rules..." "Yellow"
        foreach ($port in $portsToUpdate) {
            $ruleName = "WSL Port $port"
            # Remove existing rule if it exists
            netsh advfirewall firewall delete rule name=$ruleName 2>$null | Out-Null
            # Add new rule
            netsh advfirewall firewall add rule name=$ruleName dir=in action=allow protocol=TCP localport=$port | Out-Null
        }
        
        Write-Message "Port forwarding updated successfully!" "Green"
    }
    
    # Always ensure WSL hosts are configured (this is quick)
    Write-Message "`nEnsuring WSL hosts configuration..." "Yellow"
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

    $hostsScript | wsl -d $WSL_DISTRO -- sudo tee /usr/local/bin/wsl-network-config.sh > $null
    wsl -d $WSL_DISTRO -- sudo chmod +x /usr/local/bin/wsl-network-config.sh
    wsl -d $WSL_DISTRO -- /usr/local/bin/wsl-network-config.sh
    
    Write-Message "Network setup completed!" "Green"
    return $true
}

function Remove-Network {
    Write-Message "Cleaning up network configuration..." "Yellow"
    
    foreach ($port in $REQUIRED_PORTS) {
        netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null
        netsh advfirewall firewall delete rule name="WSL Port $port" 2>$null
    }
    
    # Remove scheduled task
    $taskName = "WSL-Network-Setup"
    $taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($taskExists) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Message "Removed scheduled task: $taskName" "Green"
    }
    
    wsl -d $WSL_DISTRO -- sed -i '/wsl-network-config.sh/d' ~/.bashrc 2>$null
    
    Write-Message "Cleanup completed!" "Green"
}

function Show-NetworkStatus {
    Write-Message "=== WSL Network Status ===" "Cyan"
    
    $wslIP = Get-WSLDistroIP
    if ($wslIP) {
        $analysis = Test-PortForwardingCurrent -CurrentIP $wslIP
        Show-CurrentStatus -WSLip $wslIP -Analysis $analysis
    } else {
        Write-Message "WSL IP: Could not determine" "Red"
    }
    
    Write-Message "`nPort Forwarding Rules:" "Cyan"
    $rules = netsh interface portproxy show v4tov4
    if ($rules) {
        $rules
    } else {
        Write-Message "No port forwarding rules found" "Yellow"
    }
    
    Write-Message "`nScheduled Task Status:" "Cyan"
    $taskName = "WSL-Network-Setup"
    $taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($taskExists) {
        Write-Message "[OK] Auto-start scheduled task exists" "Green"
    } else {
        Write-Message "[NONE] No auto-start scheduled task" "Yellow"
    }
}

function Setup-AutoStart {
    Write-Message "Setting up auto-start..." "Yellow"
    
    # Create scheduled task for automatic setup
    $taskName = "WSL-Network-Setup"
    $taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    
    if ($taskExists) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
    
    $scriptPath = $MyInvocation.MyCommand.Path
    $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$scriptPath`" -Setup"
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null
    
    Write-Message "Auto-start configured! Network will setup automatically on Windows login." "Green"
}

# ===============================================================================
# MAIN EXECUTION
# ===============================================================================

if (-not $Setup -and -not $Cleanup -and -not $Status -and -not $Auto) {
    Write-Message "WSL Network Setup Tool - ADVANCED VERSION" "Cyan"
    Write-Message "==========================================" "Cyan"
    Write-Message ""
    Write-Message "USAGE:" "Yellow"
    Write-Message "  .\wsl-network-setup.ps1 -Setup    # Configure WSL networking" "White"
    Write-Message "  .\wsl-network-setup.ps1 -Auto     # Setup + create auto-start task" "White"
    Write-Message "  .\wsl-network-setup.ps1 -Status   # Show current status" "White"
    Write-Message "  .\wsl-network-setup.ps1 -Cleanup  # Remove all rules and tasks" "White"
    Write-Message ""
    Write-Message "FEATURES:" "Yellow"
    Write-Message "  • Smart conditional updates (only changes what's needed)" "Green"
    Write-Message "  • Auto-start scheduled task creation (-Auto flag)" "Green"
    Write-Message "  • Comprehensive status reporting" "Green"
    Write-Message "  • Complete cleanup functionality" "Green"
    Write-Message ""
    Write-Message "NOTE: For simple manual runs, use wsl-network-simple.ps1 instead" "Yellow"
    Write-Message "      This version is for advanced users who want auto-start" "Yellow"
    Write-Message ""
    Write-Message "REQUIRES: Run as Administrator" "Red"
    exit 0
}

if ($Setup -or $Auto) {
    if (-not (Test-IsAdmin)) {
        Write-Message "ERROR: This script must be run as Administrator" "Red"
        Write-Message "Please run PowerShell as Administrator and try again" "Yellow"
        exit 1
    }
    
    Write-Message "Starting WSL network configuration..." "Cyan"
    
    $wslIP = Get-WSLDistroIP
    if (-not $wslIP) {
        exit 1
    }
    
    if (Setup-Network -WSLip $wslIP) {
        if ($Auto) {
            Setup-AutoStart
        }
        Write-Message "`nSetup completed successfully!" "Green"
        Write-Message "Your preprocessor should now be accessible on the LAN at port 5000" "Green"
        
        # Show final status
        Write-Message "`nFinal Status:" "Cyan"
        netsh interface portproxy show v4tov4
    } else {
        Write-Message "Setup failed" "Red"
        exit 1
    }
} elseif ($Cleanup) {
    if (-not (Test-IsAdmin)) {
        Write-Message "ERROR: This script must be run as Administrator" "Red"
        exit 1
    }
    Remove-Network
} elseif ($Status) {
    Show-NetworkStatus
} 