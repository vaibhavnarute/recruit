# Test STT API with Real Audio
# This script tests the Speech-to-Text API with an actual audio file

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "STT API Real Audio Test" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$baseUrl = "http://localhost:8001"
$audioPath = "test_audio.wav"

# Check if audio file exists
if (-not (Test-Path $audioPath)) {
    Write-Host "[ERROR] Audio file not found: $audioPath" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Audio file found: $audioPath" -ForegroundColor Green

# Get file info
$fileInfo = Get-Item $audioPath
$fileSizeKB = [math]::Round($fileInfo.Length/1024, 2)
Write-Host "[INFO] File size: $($fileInfo.Length) bytes ($fileSizeKB KB)" -ForegroundColor Cyan

# Read audio file and convert to base64
Write-Host ""
Write-Host "[PROCESS] Converting audio to base64..." -ForegroundColor Yellow
$audioBytes = [System.IO.File]::ReadAllBytes($audioPath)
$audioBase64 = [Convert]::ToBase64String($audioBytes)
Write-Host "[OK] Base64 encoded: $($audioBase64.Length) characters" -ForegroundColor Green

# Test 1: Health Check
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "TEST 1: Health Check" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

try {
    $healthResponse = Invoke-RestMethod -Uri "$baseUrl/api/stt/health" -Method GET
    
    if ($healthResponse.success) {
        Write-Host "[OK] STT Service: $($healthResponse.data.status)" -ForegroundColor Green
        Write-Host "   Model: $($healthResponse.data.components.groq_whisper_api.model)" -ForegroundColor Gray
        
        if ($healthResponse.data.components.groq_whisper_api.available) {
            Write-Host "   Groq API: Available" -ForegroundColor Green
        } else {
            Write-Host "   Groq API: Unavailable" -ForegroundColor Red
        }
    } else {
        Write-Host "[ERROR] Health check failed: $($healthResponse.error.message)" -ForegroundColor Red
    }
} catch {
    Write-Host "[ERROR] $_" -ForegroundColor Red
}

# Test 2: Transcribe Audio
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "TEST 2: Transcribe Audio" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

$sessionId = "real_test_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

$body = @{
    audio_data = $audioBase64
    audio_format = "wav"
    session_id = $sessionId
    interview_id = "interview_001"
    question_context = "Test question: Tell me about yourself"
    language = "en"
} | ConvertTo-Json

Write-Host "[PROCESS] Sending transcription request..." -ForegroundColor Yellow
Write-Host "   Session ID: $sessionId" -ForegroundColor Gray

try {
    $startTime = Get-Date
    $response = Invoke-RestMethod -Uri "$baseUrl/api/stt/transcribe" -Method POST -ContentType "application/json" -Body $body
    $elapsed = ((Get-Date) - $startTime).TotalMilliseconds
    
    Write-Host ""
    Write-Host "[INFO] Response received in $([math]::Round($elapsed, 0))ms" -ForegroundColor Cyan
    
    if ($response.success) {
        Write-Host ""
        Write-Host "[SUCCESS] TRANSCRIPTION SUCCESSFUL" -ForegroundColor Green
        Write-Host "================================" -ForegroundColor Green
        
        $data = $response.data
        
        Write-Host ""
        Write-Host "Raw Transcription:" -ForegroundColor Cyan
        Write-Host "   $($data.raw_transcription)" -ForegroundColor White
        
        Write-Host ""
        Write-Host "Cleaned Transcription:" -ForegroundColor Cyan
        Write-Host "   $($data.cleaned_transcription)" -ForegroundColor White
        
        Write-Host ""
        Write-Host "Analysis:" -ForegroundColor Cyan
        Write-Host "   Confidence: $($data.confidence_score)" -ForegroundColor Gray
        Write-Host "   Language: $($data.language_detected)" -ForegroundColor Gray
        Write-Host "   Sentiment: $($data.sentiment)" -ForegroundColor Gray
        Write-Host "   Duration: $($data.duration_seconds)s" -ForegroundColor Gray
        
        Write-Host ""
        Write-Host "Processing Details:" -ForegroundColor Cyan
        Write-Host "   Model: $($data.model)" -ForegroundColor Gray
        Write-Host "   Processing Time: $($data.processing_time_ms)ms" -ForegroundColor Gray
        Write-Host "   MCP Optimized: $($data.mcp_optimized)" -ForegroundColor Gray
        Write-Host "   Chunk ID: $($data.chunk_id)" -ForegroundColor Gray
        
    } else {
        Write-Host ""
        Write-Host "[FAILED] TRANSCRIPTION FAILED" -ForegroundColor Red
        Write-Host "================================" -ForegroundColor Red
        Write-Host "Error Code: $($response.error.code)" -ForegroundColor Yellow
        Write-Host "Message: $($response.error.message)" -ForegroundColor Yellow
        
        if ($response.error.code -match "TRANSCRIPTION_FAILED|EMPTY_TRANSCRIPTION|AUDIO_TOO_SMALL") {
            Write-Host ""
            Write-Host "[NOTE] This error is expected for synthetic/silent audio" -ForegroundColor Cyan
            Write-Host "   Try with a real audio recording containing speech" -ForegroundColor Cyan
        }
    }
    
} catch {
    Write-Host "[ERROR] Request failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "[COMPLETE] Testing Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
