# Start AI Recruiter Server with 4 Workers
# This script stops any existing server and starts a new one with 4 worker processes

Write-Host "🚀 Starting AI Recruiter Server with 4 Workers" -ForegroundColor Green
Write-Host "=" * 70

# Change to backend directory
$BackendDir = "C:\Users\Vaibhav\OneDrive\Desktop\Ai_recruiter\final_ai_rectruter\backend"
Set-Location $BackendDir

Write-Host "`n📍 Current Directory: $BackendDir" -ForegroundColor Cyan

# Check if server is already running
Write-Host "`n🔍 Checking for existing server processes..." -ForegroundColor Yellow

$ExistingProcesses = Get-Process python -ErrorAction SilentlyContinue | 
    Where-Object { $_.CommandLine -like "*uvicorn*main:app*" }

if ($ExistingProcesses) {
    Write-Host "⚠️  Found existing server process(es). Stopping them..." -ForegroundColor Yellow
    $ExistingProcesses | Stop-Process -Force
    Start-Sleep -Seconds 2
    Write-Host "✅ Stopped existing server" -ForegroundColor Green
} else {
    Write-Host "ℹ️  No existing server found" -ForegroundColor Gray
}

# Activate virtual environment
Write-Host "`n🔧 Activating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv311\Scripts\Activate.ps1") {
    & "venv311\Scripts\Activate.ps1"
    Write-Host "✅ Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "⚠️  Virtual environment not found. Using global Python..." -ForegroundColor Yellow
}

# Start server with 4 workers
Write-Host "`n🚀 Starting server with 4 workers..." -ForegroundColor Green
Write-Host "   Host: 0.0.0.0" -ForegroundColor Gray
Write-Host "   Port: 8001" -ForegroundColor Gray
Write-Host "   Workers: 4" -ForegroundColor Gray
Write-Host ""

Write-Host "📊 You should see:" -ForegroundColor Cyan
Write-Host "   ✓ Started parent process [XXXXX]" -ForegroundColor Gray
Write-Host "   ✓ Started server process [YYYYY] (Worker 1)" -ForegroundColor Gray
Write-Host "   ✓ Started server process [ZZZZZ] (Worker 2)" -ForegroundColor Gray
Write-Host "   ✓ Started server process [AAAAA] (Worker 3)" -ForegroundColor Gray
Write-Host "   ✓ Started server process [BBBBB] (Worker 4)" -ForegroundColor Gray
Write-Host ""

Write-Host "💡 To test multi-worker mode:" -ForegroundColor Yellow
Write-Host "   Open a NEW terminal and run:" -ForegroundColor Gray
Write-Host "   python test_performance_4_workers.py" -ForegroundColor White
Write-Host ""

Write-Host "🛑 To stop the server:" -ForegroundColor Red
Write-Host "   Press Ctrl+C" -ForegroundColor White
Write-Host ""
Write-Host "=" * 70
Write-Host ""

# Start uvicorn with 4 workers
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
