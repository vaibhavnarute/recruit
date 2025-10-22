# PowerShell script to restart FastAPI server

Write-Host "🔄 Restarting FastAPI server..." -ForegroundColor Cyan

# Stop any running Python processes in venv311
Write-Host "🛑 Stopping existing server..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.Path -like "*venv311*"} | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2

# Start the server
Write-Host "🚀 Starting server on http://localhost:8001..." -ForegroundColor Green
python main.py
