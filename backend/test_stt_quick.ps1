# Quick Test Script - Test One Audio File
# Tests the updated sentiment and confidence analysis

$ErrorActionPreference = "Continue"
$baseUrl = "http://localhost:8001"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  QUICK STT TEST - Testing Improved Analysis" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Test with the behavioral audio (has positive outcomes from challenges)
$audioFile = Join-Path $scriptDir "test_behavioral.mp3"

if (-not (Test-Path $audioFile)) {
    Write-Host "[ERROR] Audio file not found: $audioFile" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Testing file: $audioFile" -ForegroundColor Yellow
Write-Host "[INFO] Expected: Sentiment should be 'positive' or 'mixed' (not neutral)" -ForegroundColor Yellow
Write-Host "[INFO] Expected: Confidence should vary based on text quality" -ForegroundColor Yellow
Write-Host ""

try {
    # Read and encode audio
    Write-Host "[PROCESS] Loading audio..." -ForegroundColor Yellow
    $audioBytes = [System.IO.File]::ReadAllBytes($audioFile)
    $audioBase64 = [Convert]::ToBase64String($audioBytes)
    Write-Host "[OK] Audio loaded: $($audioBytes.Length) bytes" -ForegroundColor Green
    Write-Host ""
    
    # Send request
    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $body = @{
        audio_data = $audioBase64
        audio_format = "mp3"
        session_id = "quick_test_$timestamp"
        interview_id = "test_001"
        question_context = "Behavioral question about problem-solving"
        language = "en"
    } | ConvertTo-Json
    
    Write-Host "[PROCESS] Sending to API..." -ForegroundColor Yellow
    $startTime = Get-Date
    $response = Invoke-RestMethod -Uri "$baseUrl/api/stt/transcribe" -Method POST -ContentType "application/json" -Body $body
    $elapsed = ((Get-Date) - $startTime).TotalMilliseconds
    
    Write-Host "[OK] Response received in $([math]::Round($elapsed, 0))ms" -ForegroundColor Green
    Write-Host ""
    
    if ($response.success) {
        $data = $response.data
        
        Write-Host "==========================================================" -ForegroundColor Green
        Write-Host "  RESULTS" -ForegroundColor Green
        Write-Host "==========================================================" -ForegroundColor Green
        Write-Host ""
        
        Write-Host "TRANSCRIPTION:" -ForegroundColor Cyan
        Write-Host "   $($data.cleaned_transcription)" -ForegroundColor White
        Write-Host ""
        
        Write-Host "ANALYSIS:" -ForegroundColor Cyan
        Write-Host "   Confidence Score: $($data.confidence_score)" -ForegroundColor $(
            if ($data.confidence_score -eq 0.5) { "Yellow" } else { "Green" }
        )
        Write-Host "   Sentiment: $($data.sentiment)" -ForegroundColor $(
            if ($data.sentiment -eq "neutral") { "Yellow" } else { "Green" }
        )
        Write-Host "   Language: $($data.language_detected)" -ForegroundColor White
        Write-Host ""
        
        if ($data.key_points -and $data.key_points.Count -gt 0) {
            Write-Host "KEY POINTS:" -ForegroundColor Cyan
            foreach ($point in $data.key_points) {
                Write-Host "   - $point" -ForegroundColor White
            }
            Write-Host ""
        }
        
        if ($data.technical_terms -and $data.technical_terms.Count -gt 0) {
            Write-Host "TECHNICAL TERMS:" -ForegroundColor Cyan
            foreach ($term in $data.technical_terms) {
                Write-Host "   - $term" -ForegroundColor White
            }
            Write-Host ""
        }
        
        Write-Host "PROCESSING:" -ForegroundColor Cyan
        Write-Host "   Model: $($data.model)" -ForegroundColor White
        Write-Host "   Processing Time: $($data.processing_time_ms)ms" -ForegroundColor White
        Write-Host "   MCP Optimized: $($data.mcp_optimized)" -ForegroundColor White
        Write-Host ""
        
        # Validation
        Write-Host "==========================================================" -ForegroundColor Cyan
        Write-Host "  VALIDATION" -ForegroundColor Cyan
        Write-Host "==========================================================" -ForegroundColor Cyan
        Write-Host ""
        
        $issuesFound = $false
        
        if ($data.confidence_score -eq 0.5) {
            Write-Host "[⚠️] Confidence is 0.5 (default value) - Analysis may not be working" -ForegroundColor Yellow
            $issuesFound = $true
        } else {
            Write-Host "[✅] Confidence varies ($($data.confidence_score)) - Analysis working!" -ForegroundColor Green
        }
        
        if ($data.sentiment -eq "neutral") {
            Write-Host "[⚠️] Sentiment is neutral - May need better analysis (text has challenges + solutions)" -ForegroundColor Yellow
            $issuesFound = $true
        } else {
            Write-Host "[✅] Sentiment is $($data.sentiment) - Analysis detecting emotion!" -ForegroundColor Green
        }
        
        if (-not $data.key_points -or $data.key_points.Count -eq 0) {
            Write-Host "[⚠️] No key points extracted - LLM analysis may be failing" -ForegroundColor Yellow
            $issuesFound = $true
        } else {
            Write-Host "[✅] Key points extracted ($($data.key_points.Count) points)" -ForegroundColor Green
        }
        
        if (-not $data.technical_terms -or $data.technical_terms.Count -eq 0) {
            Write-Host "[⚠️] No technical terms extracted - Text has technical content" -ForegroundColor Yellow
            $issuesFound = $true
        } else {
            Write-Host "[✅] Technical terms found ($($data.technical_terms.Count) terms)" -ForegroundColor Green
        }
        
        Write-Host ""
        if (-not $issuesFound) {
            Write-Host "==========================================================" -ForegroundColor Green
            Write-Host "  ALL CHECKS PASSED! Analysis is working correctly!" -ForegroundColor Green
            Write-Host "==========================================================" -ForegroundColor Green
        } else {
            Write-Host "==========================================================" -ForegroundColor Yellow
            Write-Host "  Some issues detected - Check server logs for details" -ForegroundColor Yellow
            Write-Host "==========================================================" -ForegroundColor Yellow
        }
        
    } else {
        Write-Host "==========================================================" -ForegroundColor Red
        Write-Host "  ERROR" -ForegroundColor Red
        Write-Host "==========================================================" -ForegroundColor Red
        Write-Host "Error: $($response.error.message)" -ForegroundColor Red
    }
    
} catch {
    Write-Host "==========================================================" -ForegroundColor Red
    Write-Host "  REQUEST FAILED" -ForegroundColor Red
    Write-Host "==========================================================" -ForegroundColor Red
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
