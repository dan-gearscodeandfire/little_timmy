#!/bin/bash
# Network diagnostics for Little Timmy preprocessor

echo "=========================================="
echo "LITTLE TIMMY NETWORK DIAGNOSTICS"
echo "=========================================="

echo ""
echo "1. WSL IP Addresses:"
hostname -I

echo ""
echo "2. Preprocessor Status:"
if pgrep -f "python app.py" > /dev/null; then
    echo "   ✅ Preprocessor is running"
    pgrep -f "python app.py" | head -1 | xargs -I {} echo "   PID: {}"
else
    echo "   ❌ Preprocessor is NOT running"
fi

echo ""
echo "3. Port 5000 Status:"
if ss -tuln | grep -q ":5000"; then
    echo "   ✅ Port 5000 is listening"
    ss -tuln | grep ":5000" | head -1
else
    echo "   ❌ Port 5000 is NOT listening"
fi

echo ""
echo "4. Test Local Connection:"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ | grep -q "200"; then
    echo "   ✅ localhost:5000 responds"
else
    echo "   ❌ localhost:5000 does NOT respond"
fi

echo ""
echo "5. Test WSL IP Connection:"
WSL_IP=$(hostname -I | awk '{print $1}')
if curl -s -o /dev/null -w "%{http_code}" http://$WSL_IP:5000/ --connect-timeout 2 | grep -q "200"; then
    echo "   ✅ $WSL_IP:5000 responds"
else
    echo "   ❌ $WSL_IP:5000 does NOT respond"
fi

echo ""
echo "6. Windows Host Connectivity:"
if ping -c 1 -W 1 windows-host > /dev/null 2>&1; then
    echo "   ✅ Can reach windows-host"
else
    echo "   ❌ Cannot reach windows-host"
fi

echo ""
echo "=========================================="
echo "RECOMMENDATIONS:"
echo "=========================================="
echo ""
echo "Your STT server should connect to:"
echo "  Option 1 (Best): http://localhost:5000/api/webhook"
echo "  Option 2: http://$WSL_IP:5000/api/webhook"
echo ""
echo "If neither works, you need port forwarding."
echo "Run: ./wsl-network-simple.ps1 (from Windows PowerShell as Admin)"
echo ""

