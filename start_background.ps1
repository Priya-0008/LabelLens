$dir = $PSScriptRoot

Write-Host "Stopping any existing instances..."
Get-NetTCPConnection -LocalPort 8088,5188 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { 
    Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue 
}

Start-Sleep -Seconds 2

Write-Host "Starting Backend on Port 8088 (Hidden/Detached)..."
Start-Process -FilePath "python" -ArgumentList "backend/run_backend.py" -WorkingDirectory $dir -WindowStyle Hidden

Write-Host "Starting Frontend on Port 5188 (Hidden/Detached)..."
Start-Process -FilePath "python" -ArgumentList "frontend/serve_frontend.py" -WorkingDirectory $dir -WindowStyle Hidden

Write-Host "Servers started successfully in the background!"
Write-Host "They will remain running in the background."
Write-Host "Dashboard: http://localhost:5188"
