Write-Host "Stopping Legal Metrology background servers..."

$processes = Get-NetTCPConnection -LocalPort 8088,5188 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique

if ($processes) {
    foreach ($proc in $processes) {
        Write-Host "Killing process ID: $proc"
        Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Servers stopped successfully."
} else {
    Write-Host "No servers are currently running on ports 8088 or 5188."
}

Start-Sleep -Seconds 3
