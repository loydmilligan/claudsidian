# PowerShell script to open Windows Firewall for Claudsidian server
# Run this in PowerShell as Administrator

$port = 8765
$ruleName = "Claudsidian Server"

# Check if rule already exists
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "Firewall rule '$ruleName' already exists."
} else {
    # Create inbound rule for TCP
    New-NetFirewallRule -DisplayName $ruleName `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort $port `
        -Action Allow `
        -Profile Private,Domain

    Write-Host "Created firewall rule for port $port"
}

# Get WSL IP address
$wslIp = wsl hostname -I
Write-Host ""
Write-Host "WSL IP address: $wslIp"
Write-Host ""
Write-Host "To connect from your phone, use: http://$($wslIp.Trim()):$port"
Write-Host ""
Write-Host "Make sure the Claudsidian server is running with:"
Write-Host "  claudsidian serve --host 0.0.0.0 --port $port"
