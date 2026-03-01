# STT API - Additional Audio Tests
# Tests 2 more audio samples with behavioral and leadership questions

$ErrorActionPreference = "Continue"
$baseUrl = "http://localhost:8001"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  STT API - ADDITIONAL AUDIO TESTS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Additional test audio files
$audioFiles = @(
    @{
        name = "Behavioral Question"
        file = Join-Path $scriptDir "test_behavioral.mp3"
        context = "Describe a time when you faced a difficult challenge"
        session_id = "additional_test_1"
    },
    @{
        name = "Leadership Experience"
        file = Join-Path $scriptDir "test_leadership.mp3"
        context = "Tell me about your leadership experience"
        session_id = "additional_test_2"
    }
)

# Check files exist
Write-Host "[SETUP] Checking audio files..." -ForegroundColor Yellow
$allFilesExist = $true
foreach ($audio in $audioFiles) {
    if (Test-Path $audio.file) {
        $fileSize = (Get-Item $audio.file).Length
        $fileSizeKB = [math]::Round($fileSize/1024, 2)
        Write-Host "  [OK] $($audio.file) - $fileSize bytes" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $($audio.file)" -ForegroundColor Red
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-Host ""
    Write-Host "[ERROR] Some audio files are missing!" -ForegroundColor Red
    Write-Host "Run: python generate_additional_audio.py" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host ""

# Test each audio file
$testResults = @()
$testNumber = 1

foreach ($audio in $audioFiles) {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  TEST $testNumber : $($audio.name)" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "[INFO] File: $($audio.file)" -ForegroundColor Gray
    Write-Host "[INFO] Context: $($audio.context)" -ForegroundColor Gray
    Write-Host ""
    
    try {
        # Read and encode audio
        Write-Host "[PROCESS] Reading audio file... ($($audio.file))" -ForegroundColor Yellow
        $audioBytes = [System.IO.File]::ReadAllBytes($audio.file)
        $audioBase64 = [Convert]::ToBase64String($audioBytes)
        
        $fileSizeKB = [math]::Round($audioBytes.Length/1024, 2)
        Write-Host "[OK] Audio loaded: $($audioBytes.Length) bytes ($fileSizeKB KB)" -ForegroundColor Green
        Write-Host "[OK] Base64 encoded: $($audioBase64.Length) characters" -ForegroundColor Green
        Write-Host ""
        
        # Prepare request
        $timestamp = Get-Date -Format "yyyyMMddHHmmss"
        $sessionId = "$($audio.session_id)_$timestamp"
        
        $body = @{
            audio_data = $audioBase64
            audio_format = "mp3"
            session_id = $sessionId
            interview_id = "additional_test_001"
            question_context = $audio.context
            language = "en"
        } | ConvertTo-Json
        
        # Send request
        Write-Host "[PROCESS] Sending to Groq Whisper API..." -ForegroundColor Yellow
        Write-Host "  Session ID: $sessionId" -ForegroundColor Gray
        
        $startTime = Get-Date
        $response = Invoke-RestMethod -Uri "$baseUrl/api/stt/transcribe" -Method POST -ContentType "application/json" -Body $body
        $elapsed = ((Get-Date) - $startTime).TotalMilliseconds
        
        Write-Host "[OK] Response received in $([math]::Round($elapsed, 0))ms" -ForegroundColor Green
        Write-Host ""
        
        if ($response.success) {
            Write-Host "================================================" -ForegroundColor Green
            Write-Host "  TRANSCRIPTION SUCCESSFUL" -ForegroundColor Green
            Write-Host "================================================" -ForegroundColor Green
            Write-Host ""
            
            $data = $response.data
            
            # Display results
            Write-Host "RAW TRANSCRIPTION:" -ForegroundColor Cyan
            Write-Host "   $($data.raw_transcription)" -ForegroundColor White
            Write-Host ""
            
            Write-Host "CLEANED TRANSCRIPTION:" -ForegroundColor Cyan
            Write-Host "   $($data.cleaned_transcription)" -ForegroundColor White
            Write-Host ""
            
            Write-Host "ANALYSIS:" -ForegroundColor Cyan
            Write-Host "  Confidence Score: $($data.confidence_score)" -ForegroundColor Gray
            Write-Host "  Language: $($data.language_detected)" -ForegroundColor Gray
            Write-Host "  Sentiment: $($data.sentiment)" -ForegroundColor Gray
            Write-Host "  Speaker: $($data.speaker_detected)" -ForegroundColor Gray
            Write-Host ""
            
            if ($data.key_points -and $data.key_points.Count -gt 0) {
                Write-Host "KEY POINTS:" -ForegroundColor Cyan
                foreach ($point in $data.key_points) {
                    Write-Host "  - $point" -ForegroundColor Gray
                }
                Write-Host ""
            }
            
            if ($data.technical_terms -and $data.technical_terms.Count -gt 0) {
                Write-Host "TECHNICAL TERMS:" -ForegroundColor Cyan
                foreach ($term in $data.technical_terms) {
                    Write-Host "  - $term" -ForegroundColor Gray
                }
                Write-Host ""
            }
            
            Write-Host "PROCESSING DETAILS:" -ForegroundColor Cyan
            Write-Host "  Model: $($data.model)" -ForegroundColor Gray
            Write-Host "  Workflow: $($data.workflow)" -ForegroundColor Gray
            Write-Host "  MCP Optimized: $($data.mcp_optimized)" -ForegroundColor Gray
            Write-Host "  Processing Time: $($data.processing_time_ms)ms" -ForegroundColor Gray
            Write-Host "  API Response Time: $([math]::Round($elapsed, 0))ms" -ForegroundColor Gray
            Write-Host "  Chunk ID: $($data.chunk_id)" -ForegroundColor Gray
            Write-Host ""
            
            $testResults += @{
                name = $audio.name
                status = "PASS"
                transcription = $data.cleaned_transcription
                confidence = $data.confidence_score
                sentiment = $data.sentiment
                processing_time = $elapsed
            }
            
        } else {
            Write-Host "================================================" -ForegroundColor Red
            Write-Host "  TRANSCRIPTION FAILED" -ForegroundColor Red
            Write-Host "================================================" -ForegroundColor Red
            Write-Host ""
            Write-Host "Error Code: $($response.error.code)" -ForegroundColor Yellow
            Write-Host "Message: $($response.error.message)" -ForegroundColor Yellow
            Write-Host ""
            
            $testResults += @{
                name = $audio.name
                status = "FAIL"
                error = $response.error.message
            }
        }
        
    } catch {
        Write-Host "================================================" -ForegroundColor Red
        Write-Host "  REQUEST FAILED" -ForegroundColor Red
        Write-Host "================================================" -ForegroundColor Red
        Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        
        $testResults += @{
            name = $audio.name
            status = "FAIL"
            error = $_.Exception.Message
        }
    }
    
    $testNumber++
}

# Summary
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  TEST SUMMARY" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$passCount = ($testResults | Where-Object { $_.status -eq "PASS" }).Count
$totalCount = $testResults.Count

Write-Host "Results: $passCount/$totalCount tests passed" -ForegroundColor $(if ($passCount -eq $totalCount) { "Green" } else { "Yellow" })
Write-Host ""

foreach ($result in $testResults) {
    if ($result.status -eq "PASS") {
        Write-Host "[PASS] $($result.name)" -ForegroundColor Green
        $transcriptPreview = if ($result.transcription.Length -gt 80) { 
            $result.transcription.Substring(0, 80) + "..." 
        } else { 
            $result.transcription 
        }
        Write-Host "  Transcription: $transcriptPreview" -ForegroundColor Gray
        Write-Host "  Confidence: $($result.confidence)" -ForegroundColor Gray
        Write-Host "  Sentiment: $($result.sentiment)" -ForegroundColor Gray
        Write-Host "  Processing Time: $([math]::Round($result.processing_time, 0))ms" -ForegroundColor Gray
    } else {
        Write-Host "[FAIL] $($result.name)" -ForegroundColor Red
        Write-Host "  Error: $($result.error)" -ForegroundColor Yellow
    }
    Write-Host ""
}

Write-Host "============================================================" -ForegroundColor Cyan
if ($passCount -eq $totalCount) {
    Write-Host "  ALL TESTS PASSED!" -ForegroundColor Green
    Write-Host "  Additional STT tests successful!" -ForegroundColor Green
} else {
    Write-Host "  SOME TESTS FAILED" -ForegroundColor Yellow
    Write-Host "  Check errors above for details" -ForegroundColor Yellow
}
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Total Tests: $totalCount" -ForegroundColor Cyan
Write-Host "Passed: $passCount" -ForegroundColor Green
Write-Host "Failed: $($totalCount - $passCount)" -ForegroundColor $(if (($totalCount - $passCount) -gt 0) { "Red" } else { "Green" })
Write-Host ""
