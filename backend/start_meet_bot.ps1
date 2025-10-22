# Google Meet Bot - Quick Start Script
# This script helps you set up and start all required services

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Google Meet Bot - Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (-Not (Test-Path ".env")) {
    Write-Host "⚠️  .env file not found!" -ForegroundColor Yellow
    Write-Host "   Creating .env from template..." -ForegroundColor Yellow
    Copy-Item ".env.template" ".env"
    Write-Host "✅ .env file created. Please edit it with your credentials." -ForegroundColor Green
    Write-Host ""
    Write-Host "Required variables to set:" -ForegroundColor Yellow
    Write-Host "   - GROQ_API_KEY" -ForegroundColor White
    Write-Host "   - MONGODB_URI" -ForegroundColor White
    Write-Host "   - MEET_BOT_EMAIL" -ForegroundColor White
    Write-Host "   - MEET_BOT_PASSWORD" -ForegroundColor White
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

Write-Host "✅ .env file found" -ForegroundColor Green
Write-Host ""

# Check Python
Write-Host "🔍 Checking Python..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Python not found! Please install Python 3.11+" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Check Node.js
Write-Host "🔍 Checking Node.js..." -ForegroundColor Cyan
try {
    $nodeVersion = node --version
    Write-Host "   Node.js $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Node.js not found! Please install Node.js 18+" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Check MongoDB
Write-Host "🔍 Checking MongoDB connection..." -ForegroundColor Cyan
try {
    $mongoCheck = python -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')); client.server_info(); print('✅ MongoDB connected')" 2>&1
    Write-Host "   $mongoCheck" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Could not connect to MongoDB" -ForegroundColor Yellow
    Write-Host "   Make sure MongoDB is running and MONGODB_URI is correct in .env" -ForegroundColor Yellow
}
Write-Host ""

# Install Python dependencies
Write-Host "📦 Checking Python dependencies..." -ForegroundColor Cyan
Write-Host "   Installing/updating packages..." -ForegroundColor White
pip install -r requirements.txt --quiet
pip install websockets --quiet
Write-Host "   ✅ Python dependencies ready" -ForegroundColor Green
Write-Host ""

# Install Node.js dependencies
Write-Host "📦 Checking Node.js dependencies..." -ForegroundColor Cyan
if (-Not (Test-Path "node_modules")) {
    Write-Host "   Installing packages..." -ForegroundColor White
    npm install
    Write-Host "   ✅ Node.js dependencies installed" -ForegroundColor Green
} else {
    Write-Host "   ✅ Node.js dependencies already installed" -ForegroundColor Green
}
Write-Host ""

# Ask user which services to start
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Service Startup Options" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Start ALL services (FastAPI + WebSocket Bridge)" -ForegroundColor White
Write-Host "2. Start FastAPI only" -ForegroundColor White
Write-Host "3. Start WebSocket Bridge only" -ForegroundColor White
Write-Host "4. Run integration tests" -ForegroundColor White
Write-Host "5. Exit" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Enter your choice (1-5)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "🚀 Starting ALL services..." -ForegroundColor Green
        Write-Host ""
        Write-Host "Opening 2 new PowerShell windows:" -ForegroundColor Yellow
        Write-Host "   1. FastAPI Backend (port 8001)" -ForegroundColor White
        Write-Host "   2. WebSocket Bridge (port 8765)" -ForegroundColor White
        Write-Host ""
        Write-Host "📝 Logs will appear in separate windows" -ForegroundColor Yellow
        Write-Host ""
        
        # Start FastAPI in new window
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; Write-Host '🚀 Starting FastAPI Backend...' -ForegroundColor Green; python main.py"
        
        Start-Sleep -Seconds 2
        
        # Start WebSocket Bridge in new window
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; Write-Host '🚀 Starting WebSocket Bridge...' -ForegroundColor Green; python services/websocket_bridge.py"
        
        Write-Host "✅ Services started!" -ForegroundColor Green
        Write-Host ""
        Write-Host "API available at: http://localhost:8001" -ForegroundColor Cyan
        Write-Host "WebSocket at: ws://localhost:8765" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Test the API:" -ForegroundColor Yellow
        Write-Host "   curl http://localhost:8001/health" -ForegroundColor White
        Write-Host ""
    }
    
    "2" {
        Write-Host ""
        Write-Host "🚀 Starting FastAPI Backend..." -ForegroundColor Green
        Write-Host ""
        python main.py
    }
    
    "3" {
        Write-Host ""
        Write-Host "🚀 Starting WebSocket Bridge..." -ForegroundColor Green
        Write-Host ""
        python services/websocket_bridge.py
    }
    
    "4" {
        Write-Host ""
        Write-Host "🧪 Running integration tests..." -ForegroundColor Green
        Write-Host ""
        python test_meet_bot_integration.py
    }
    
    "5" {
        Write-Host ""
        Write-Host "👋 Goodbye!" -ForegroundColor Cyan
        Write-Host ""
        exit 0
    }
    
    default {
        Write-Host ""
        Write-Host "❌ Invalid choice!" -ForegroundColor Red
        Write-Host ""
        exit 1
    }
}
