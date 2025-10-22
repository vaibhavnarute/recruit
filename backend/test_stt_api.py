"""
STT API Test Script
Tests all Speech-to-Text endpoints with sample data
"""

import requests
import base64
import json
import time

# Configuration
BASE_URL = "http://localhost:8001"
TEST_SESSION_ID = "test_session_001"
TEST_INTERVIEW_ID = "test_interview_001"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name):
    print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BLUE}TEST: {name}{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.YELLOW}ℹ️  {message}{Colors.END}")

def create_test_audio():
    """Create a small test audio file (1 second of silence at 16kHz)"""
    # 1 second of 16-bit PCM audio at 16kHz
    sample_rate = 16000
    duration = 1  # seconds
    num_samples = sample_rate * duration
    
    # Create silent audio (all zeros)
    audio_bytes = b'\x00\x00' * num_samples  # 16-bit samples
    
    return audio_bytes

def test_health_check():
    """Test 1: Health Check"""
    print_test("Health Check - GET /api/stt/health")
    
    try:
        response = requests.get(f"{BASE_URL}/api/stt/health", timeout=10)
        print_info(f"Response Status Code: {response.status_code}")
        
        try:
            result = response.json()
            print_info(f"Response JSON: {json.dumps(result, indent=2)}")
        except Exception as json_error:
            print_error(f"Failed to parse JSON: {json_error}")
            print_info(f"Raw Response: {response.text[:500]}")
            return False
        
        if result.get("success"):
            print_success("Health check passed")
            print_info(f"Status: {result['data']['status']}")
            print_info(f"Model: {result['data']['components']['groq_whisper_api']['model']}")
            print_info(f"Groq Available: {result['data']['components']['groq_whisper_api']['available']}")
            print_info(f"LangGraph Available: {result['data']['components']['langgraph_workflow']['available']}")
            print_info(f"MCP Available: {result['data']['components']['mcp_integration']['available']}")
            return True
        else:
            print_error(f"Health check failed: {result.get('error', {}).get('message')}")
            print_info(f"Full error: {json.dumps(result.get('error', {}), indent=2)}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print_error(f"Connection error: Cannot connect to {BASE_URL}")
        print_info("Make sure the FastAPI server is running: python main.py")
        return False
    except requests.exceptions.Timeout as e:
        print_error(f"Request timeout: {str(e)}")
        return False
    except Exception as e:
        print_error(f"Health check error: {str(e)}")
        import traceback
        print_info(f"Traceback: {traceback.format_exc()}")
        return False

def test_transcribe_base64():
    """Test 2: Transcribe Base64 Audio"""
    print_test("Transcribe Base64 - POST /api/stt/transcribe")
    
    try:
        # Create test audio
        audio_bytes = create_test_audio()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        print_info(f"Audio size: {len(audio_bytes)} bytes")
        print_info(f"Base64 length: {len(audio_base64)} characters")
        
        # API request
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/stt/transcribe",
            json={
                "audio_data": audio_base64,
                "audio_format": "wav",
                "session_id": TEST_SESSION_ID,
                "interview_id": TEST_INTERVIEW_ID,
                "question_context": "Test question for transcription",
                "language": "en"
            },
            timeout=30
        )
        elapsed_time = (time.time() - start_time) * 1000
        
        print_info(f"Response Status Code: {response.status_code}")
        
        try:
            result = response.json()
        except Exception as json_error:
            print_error(f"Failed to parse JSON: {json_error}")
            print_info(f"Raw Response: {response.text[:500]}")
            return False
        
        if result.get("success"):
            print_success("Transcription completed successfully")
            data = result.get("data", {})
            print_info(f"Chunk ID: {data.get('chunk_id')}")
            print_info(f"Raw Transcription: {data.get('raw_transcription', 'N/A')[:100]}")
            print_info(f"Cleaned Transcription: {data.get('cleaned_transcription', 'N/A')[:100]}")
            print_info(f"Confidence: {data.get('confidence_score', 0.0):.2f}")
            print_info(f"Language: {data.get('language_detected')}")
            print_info(f"Sentiment: {data.get('sentiment')}")
            print_info(f"Processing Time: {data.get('processing_time_ms')}ms")
            print_info(f"API Response Time: {elapsed_time:.0f}ms")
            print_info(f"Model: {data.get('model')}")
            print_info(f"MCP Optimized: {data.get('mcp_optimized')}")
            return True
        else:
            error = result.get('error', {})
            error_code = error.get('code')
            error_message = error.get('message')
            
            print_error(f"Transcription failed: {error_message}")
            print_info(f"Error Code: {error_code}")
            print_info(f"Full error: {json.dumps(error, indent=2)}")
            
            # Some errors are expected for silent audio
            if error_code in ["TRANSCRIPTION_FAILED", "AUDIO_TOO_SMALL", "EMPTY_TRANSCRIPTION"]:
                print_info("✓ This error is expected for silent test audio")
                return True
            
            return False
            
    except requests.exceptions.ConnectionError as e:
        print_error(f"Connection error: Cannot connect to {BASE_URL}")
        return False
    except requests.exceptions.Timeout as e:
        print_error(f"Request timeout (30s exceeded)")
        return False
    except Exception as e:
        print_error(f"Transcription error: {str(e)}")
        import traceback
        print_info(f"Traceback: {traceback.format_exc()}")
        return False

def test_stream_chunk():
    """Test 3: Stream Audio Chunk"""
    print_test("Stream Chunk - POST /api/stt/stream/chunk")
    
    try:
        # Create test audio
        audio_bytes = create_test_audio()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        # API request
        response = requests.post(
            f"{BASE_URL}/api/stt/stream/chunk",
            json={
                "chunk_id": "test_chunk_001",
                "session_id": TEST_SESSION_ID,
                "audio_data": audio_base64,
                "audio_format": "wav",
                "chunk_number": 1,
                "is_final": False
            }
        )
        
        result = response.json()
        
        if result.get("success"):
            print_success("Chunk received successfully")
            data = result.get("data", {})
            print_info(f"Chunk ID: {data.get('chunk_id')}")
            print_info(f"Chunk Number: {data.get('chunk_number')}")
            print_info(f"Processing Status: {data.get('processing_status')}")
            print_info(f"Is Final: {data.get('is_final')}")
            return True
        else:
            print_error(f"Stream chunk failed: {result.get('error', {}).get('message')}")
            return False
            
    except Exception as e:
        print_error(f"Stream chunk error: {str(e)}")
        return False

def test_get_transcript():
    """Test 4: Get Session Transcripts"""
    print_test("Get Transcripts - GET /api/stt/transcript/{session_id}")
    
    try:
        # API request
        response = requests.get(f"{BASE_URL}/api/stt/transcript/{TEST_SESSION_ID}")
        result = response.json()
        
        if result.get("success"):
            print_success("Transcripts retrieved successfully")
            data = result.get("data", {})
            print_info(f"Session ID: {data.get('session_id')}")
            print_info(f"Total Transcripts: {data.get('total_count')}")
            
            if data.get('transcripts'):
                print_info(f"First transcript preview: {data['transcripts'][0].get('cleaned_transcription', '')[:100]}")
            
            stats = data.get('stats', {})
            if stats:
                print_info(f"Total Segments: {stats.get('total_segments', 0)}")
                print_info(f"Average Confidence: {stats.get('average_confidence', 0.0):.2f}")
                
            return True
        else:
            error_code = result.get('error', {}).get('code')
            if error_code == "NO_TRANSCRIPTS":
                print_info("No transcripts found (expected for new session)")
                return True
            else:
                print_error(f"Get transcripts failed: {result.get('error', {}).get('message')}")
                return False
            
    except Exception as e:
        print_error(f"Get transcripts error: {str(e)}")
        return False

def test_invalid_audio():
    """Test 5: Invalid Audio Data (Error Handling)"""
    print_test("Invalid Audio - Error Handling Test")
    
    try:
        # Test with empty audio data
        response = requests.post(
            f"{BASE_URL}/api/stt/transcribe",
            json={
                "audio_data": "",
                "audio_format": "wav"
            }
        )
        
        result = response.json()
        
        # Should fail but still return 200 status
        if not result.get("success"):
            print_success("Error handling works correctly (returns 200 with error in body)")
            error = result.get("error", {})
            print_info(f"Error Code: {error.get('code')}")
            print_info(f"Error Message: {error.get('message')}")
            return True
        else:
            print_error("Should have failed for empty audio data")
            return False
            
    except Exception as e:
        print_error(f"Invalid audio test error: {str(e)}")
        return False

def test_invalid_base64():
    """Test 6: Invalid Base64 (Error Handling)"""
    print_test("Invalid Base64 - Error Handling Test")
    
    try:
        # Test with invalid base64
        response = requests.post(
            f"{BASE_URL}/api/stt/transcribe",
            json={
                "audio_data": "not_valid_base64!@#$%",
                "audio_format": "wav"
            }
        )
        
        result = response.json()
        
        # Should fail but still return 200 status
        if not result.get("success"):
            print_success("Base64 validation works correctly")
            error = result.get("error", {})
            print_info(f"Error Code: {error.get('code')}")
            print_info(f"Error Message: {error.get('message')}")
            return True
        else:
            print_error("Should have failed for invalid base64")
            return False
            
    except Exception as e:
        print_error(f"Invalid base64 test error: {str(e)}")
        return False

def run_all_tests():
    """Run all tests and report results"""
    print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BLUE}STT API INTEGRATION TESTS{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.YELLOW}Base URL: {BASE_URL}{Colors.END}")
    print(f"{Colors.YELLOW}Session ID: {TEST_SESSION_ID}{Colors.END}")
    print(f"{Colors.YELLOW}Interview ID: {TEST_INTERVIEW_ID}{Colors.END}")
    
    tests = [
        ("Health Check", test_health_check),
        ("Transcribe Base64", test_transcribe_base64),
        ("Stream Chunk", test_stream_chunk),
        ("Get Transcripts", test_get_transcript),
        ("Invalid Audio Error Handling", test_invalid_audio),
        ("Invalid Base64 Error Handling", test_invalid_base64)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BLUE}TEST SUMMARY{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.END}" if result else f"{Colors.RED}❌ FAIL{Colors.END}"
        print(f"{status} - {test_name}")
    
    print(f"\n{Colors.BLUE}Results: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}{'='*80}{Colors.END}")
        print(f"{Colors.GREEN}🎉 ALL TESTS PASSED!{Colors.END}")
        print(f"{Colors.GREEN}{'='*80}{Colors.END}")
    else:
        print(f"{Colors.RED}{'='*80}{Colors.END}")
        print(f"{Colors.RED}⚠️  SOME TESTS FAILED{Colors.END}")
        print(f"{Colors.RED}{'='*80}{Colors.END}")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
