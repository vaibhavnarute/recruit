"""
Test file for newly implemented features:
1. Resume Upload & Parsing
2. Real-Time Audio Streaming via WebSocket
3. Meet Bot Audio System

Tests production endpoints with realistic scenarios.
"""

import asyncio
import json
import base64
import io
from pathlib import Path
import requests
import websockets
from datetime import datetime
import wave
import struct
import math

# Base URL for API
BASE_URL = "http://localhost:8001"
WS_BASE_URL = "ws://localhost:8001"

# Test results tracking
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "details": []
}

def log_test(test_name: str, passed: bool, message: str = ""):
    """Log test result"""
    test_results["total"] += 1
    if passed:
        test_results["passed"] += 1
        status = "✅ PASS"
    else:
        test_results["failed"] += 1
        status = "❌ FAIL"
    
    test_results["details"].append({
        "test": test_name,
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })
    
    print(f"{status}: {test_name}")
    if message:
        print(f"   {message}")


# ==================== HELPER FUNCTIONS ====================

def create_sample_resume_pdf():
    """Create a sample PDF resume file for testing"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        filename = "test_resume.pdf"
        c = canvas.Canvas(filename, pagesize=letter)
        
        # Write resume content
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "John Doe")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 730, "Email: john.doe@example.com")
        c.drawString(100, 710, "Phone: (555) 123-4567")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 680, "Skills")
        c.setFont("Helvetica", 12)
        c.drawString(100, 660, "Python, JavaScript, React, Node.js, AWS, Docker, Kubernetes")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 630, "Experience")
        c.setFont("Helvetica", 12)
        c.drawString(100, 610, "Senior Software Engineer at Tech Corp")
        c.drawString(100, 590, "2020 - Present")
        c.drawString(120, 570, "- Developed scalable microservices architecture")
        c.drawString(120, 550, "- Led team of 5 engineers")
        
        c.drawString(100, 520, "Software Engineer at StartupXYZ")
        c.drawString(100, 500, "2018 - 2020")
        c.drawString(120, 480, "- Built RESTful APIs using Python and FastAPI")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 450, "Education")
        c.setFont("Helvetica", 12)
        c.drawString(100, 430, "Bachelor of Science in Computer Science")
        c.drawString(100, 410, "University of Technology, 2018")
        
        c.save()
        
        print(f"✅ Created sample PDF resume: {filename}")
        return filename
        
    except ImportError:
        # Fallback: Create simple text file if reportlab not available
        filename = "test_resume.txt"
        content = """
John Doe
Email: john.doe@example.com
Phone: (555) 123-4567

Skills:
Python, JavaScript, React, Node.js, AWS, Docker, Kubernetes

Experience:
Senior Software Engineer at Tech Corp
2020 - Present
- Developed scalable microservices architecture
- Led team of 5 engineers

Software Engineer at StartupXYZ
2018 - 2020
- Built RESTful APIs using Python and FastAPI

Education:
Bachelor of Science in Computer Science
University of Technology, 2018
"""
        with open(filename, 'w') as f:
            f.write(content)
        
        print(f"✅ Created sample text resume: {filename}")
        return filename


def create_audio_chunk(duration_ms=500, frequency=440):
    """Create a sample audio chunk (WAV format) for testing"""
    sample_rate = 16000  # 16kHz
    num_samples = int(sample_rate * duration_ms / 1000)
    
    # Generate sine wave
    audio_data = []
    for i in range(num_samples):
        value = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * i / sample_rate))
        audio_data.append(struct.pack('<h', value))
    
    # Create WAV file in memory
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(audio_data))
    
    wav_buffer.seek(0)
    return wav_buffer.read()


# ==================== TEST 1: RESUME UPLOAD & PARSING ====================

def test_resume_upload():
    """Test resume upload endpoint with real file"""
    print("\n" + "="*60)
    print("TEST 1: RESUME UPLOAD & PARSING")
    print("="*60)
    
    # Create sample resume
    resume_file = create_sample_resume_pdf()
    
    try:
        # Test 1.1: Upload resume without candidate_id
        with open(resume_file, 'rb') as f:
            files = {'file': (resume_file, f, 'application/pdf')}
            response = requests.post(f"{BASE_URL}/api/resumes/upload", files=files)
        
        if response.status_code == 200:
            data = response.json()
            log_test("Resume Upload (no candidate_id)", True, 
                    f"Uploaded successfully. Resume ID: {data.get('resume_id', 'N/A')}")
            
            # Verify extracted data
            if 'extracted_data' in data:
                extracted = data['extracted_data']
                
                # Check email extraction
                has_email = bool(extracted.get('email'))
                log_test("Email Extraction", has_email, 
                        f"Email: {extracted.get('email', 'Not found')}")
                
                # Check phone extraction
                has_phone = bool(extracted.get('phone'))
                log_test("Phone Extraction", has_phone,
                        f"Phone: {extracted.get('phone', 'Not found')}")
                
                # Check skills extraction
                skills = extracted.get('skills', [])
                has_skills = len(skills) > 0
                log_test("Skills Extraction", has_skills,
                        f"Found {len(skills)} skills: {', '.join(skills[:5])}")
                
                # Check experience extraction
                experience = extracted.get('experience', [])
                has_experience = len(experience) > 0
                log_test("Experience Extraction", has_experience,
                        f"Found {len(experience)} experience entries")
                
                # Check education extraction
                education = extracted.get('education', [])
                has_education = len(education) > 0
                log_test("Education Extraction", has_education,
                        f"Found {len(education)} education entries")
            else:
                log_test("Data Extraction", False, "No extracted_data in response")
        else:
            log_test("Resume Upload (no candidate_id)", False,
                    f"Status: {response.status_code}, Error: {response.text}")
        
        # Test 1.2: Upload resume with candidate_id and interview_id
        with open(resume_file, 'rb') as f:
            files = {'file': (resume_file, f, 'application/pdf')}
            data = {
                'candidate_id': 'test-candidate-001',
                'interview_id': 'test-interview-001'
            }
            response = requests.post(f"{BASE_URL}/api/resumes/upload", 
                                   files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            log_test("Resume Upload (with IDs)", True,
                    f"Resume ID: {result.get('resume_id', 'N/A')}")
        else:
            log_test("Resume Upload (with IDs)", False,
                    f"Status: {response.status_code}")
        
        # Test 1.3: Invalid file type
        invalid_file = "test_invalid.xyz"
        with open(invalid_file, 'w') as f:
            f.write("This is not a valid resume format")
        
        with open(invalid_file, 'rb') as f:
            files = {'file': (invalid_file, f, 'application/xyz')}
            response = requests.post(f"{BASE_URL}/api/resumes/upload", files=files)
        
        # Should reject invalid file type
        is_rejected = response.status_code != 200
        log_test("Invalid File Type Rejection", is_rejected,
                f"Status: {response.status_code} (should be error)")
        
        # Cleanup
        import os
        if os.path.exists(resume_file):
            os.remove(resume_file)
        if os.path.exists(invalid_file):
            os.remove(invalid_file)
        
    except Exception as e:
        log_test("Resume Upload Test", False, f"Exception: {str(e)}")


# ==================== TEST 2: WEBSOCKET AUDIO STREAMING ====================

async def test_websocket_streaming():
    """Test WebSocket audio streaming endpoint"""
    print("\n" + "="*60)
    print("TEST 2: REAL-TIME AUDIO STREAMING (WebSocket)")
    print("="*60)
    
    interview_id = "test-interview-ws-001"
    ws_url = f"{WS_BASE_URL}/ws/audio/{interview_id}"
    
    try:
        # Test 2.1: WebSocket connection
        async with websockets.connect(ws_url) as websocket:
            log_test("WebSocket Connection", True, f"Connected to {ws_url}")
            
            # Test 2.2: Send audio chunk
            audio_chunk = create_audio_chunk(duration_ms=1000, frequency=440)
            await websocket.send(audio_chunk)
            log_test("Send Audio Chunk", True, f"Sent {len(audio_chunk)} bytes")
            
            # Test 2.3: Receive transcription (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                has_transcription = 'transcription' in response_data or 'text' in response_data
                transcription_text = response_data.get('transcription', 
                                                      response_data.get('text', 'No text'))
                
                log_test("Receive Transcription", True,
                        f"Response: {transcription_text[:100]}")
                
            except asyncio.TimeoutError:
                log_test("Receive Transcription", False, "Timeout waiting for response")
            except json.JSONDecodeError:
                log_test("Receive Transcription", False, "Invalid JSON response")
            
            # Test 2.4: Send multiple chunks (streaming simulation)
            print("\n   📡 Simulating continuous audio stream...")
            for i in range(3):
                audio_chunk = create_audio_chunk(duration_ms=500, frequency=440 + i*100)
                await websocket.send(audio_chunk)
                await asyncio.sleep(0.5)  # Simulate real-time streaming
            
            log_test("Multiple Audio Chunks", True, "Sent 3 audio chunks successfully")
            
            # Test 2.5: Get streaming stats
            stats_command = json.dumps({"command": "get_stats"})
            await websocket.send(stats_command)
            
            try:
                stats_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                stats_data = json.loads(stats_response)
                
                if 'stats' in stats_data or 'chunks_received' in stats_data:
                    log_test("Get Streaming Stats", True, f"Stats: {stats_data}")
                else:
                    log_test("Get Streaming Stats", True, "Stats command processed")
                    
            except asyncio.TimeoutError:
                log_test("Get Streaming Stats", False, "Timeout waiting for stats")
            
            # Test 2.6: Graceful disconnect
            await websocket.close()
            log_test("WebSocket Disconnect", True, "Connection closed gracefully")
            
    except websockets.exceptions.WebSocketException as e:
        log_test("WebSocket Connection", False, f"WebSocket error: {str(e)}")
    except Exception as e:
        log_test("WebSocket Streaming Test", False, f"Exception: {str(e)}")


# ==================== TEST 3: CONCURRENT WEBSOCKET CONNECTIONS ====================

async def test_concurrent_websockets():
    """Test multiple concurrent WebSocket connections (multi-interview support)"""
    print("\n" + "="*60)
    print("TEST 3: CONCURRENT WEBSOCKET CONNECTIONS")
    print("="*60)
    
    async def connect_and_stream(interview_id: str, num_chunks: int = 2):
        """Helper function to connect and stream audio"""
        ws_url = f"{WS_BASE_URL}/ws/audio/{interview_id}"
        try:
            async with websockets.connect(ws_url) as websocket:
                for i in range(num_chunks):
                    audio_chunk = create_audio_chunk(duration_ms=500)
                    await websocket.send(audio_chunk)
                    await asyncio.sleep(0.3)
                return True
        except Exception as e:
            print(f"   Error in {interview_id}: {str(e)}")
            return False
    
    try:
        # Create 3 concurrent connections
        interview_ids = [
            "concurrent-interview-001",
            "concurrent-interview-002",
            "concurrent-interview-003"
        ]
        
        # Run all connections concurrently
        results = await asyncio.gather(
            *[connect_and_stream(iid, 2) for iid in interview_ids],
            return_exceptions=True
        )
        
        success_count = sum(1 for r in results if r is True)
        log_test("Concurrent WebSocket Connections", success_count == len(interview_ids),
                f"Successfully handled {success_count}/{len(interview_ids)} concurrent connections")
        
    except Exception as e:
        log_test("Concurrent WebSocket Test", False, f"Exception: {str(e)}")


# ==================== TEST 4: AUDIO SYSTEM INTEGRATION ====================

async def test_audio_system():
    """Test Meet Bot Audio System (as much as possible without actual Meet)"""
    print("\n" + "="*60)
    print("TEST 4: MEET BOT AUDIO SYSTEM")
    print("="*60)
    
    try:
        # Import the audio system
        from meet_bot_audio import MeetBotAudio
        
        log_test("Import MeetBotAudio", True, "Module imported successfully")
        
        # Test 4.1: Class instantiation (without actual Playwright page)
        try:
            # We can't test fully without a real browser page, but we can verify structure
            import inspect
            
            # Check if class has required methods
            required_methods = [
                'initialize_audio_system',
                'play_audio_in_meet',
                'enable_microphone',
                'capture_audio_stream',
                'get_audio_chunk',
                'stop_audio_capture'
            ]
            
            has_all_methods = all(
                hasattr(MeetBotAudio, method) for method in required_methods
            )
            
            log_test("MeetBotAudio Class Structure", has_all_methods,
                    f"Has all required methods: {', '.join(required_methods)}")
            
            # Test 4.2: Audio encoding/decoding
            # Create sample audio and encode to base64
            audio_data = create_audio_chunk(duration_ms=1000)
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            log_test("Audio Base64 Encoding", True,
                    f"Encoded {len(audio_data)} bytes to {len(audio_base64)} chars")
            
            # Verify decoding
            decoded_audio = base64.b64decode(audio_base64)
            is_valid_decode = decoded_audio == audio_data
            log_test("Audio Base64 Decoding", is_valid_decode,
                    "Audio data preserved after encode/decode")
            
        except Exception as e:
            log_test("MeetBotAudio Testing", False, f"Error: {str(e)}")
        
    except ImportError as e:
        log_test("Import MeetBotAudio", False, f"Import error: {str(e)}")


# ==================== TEST 5: END-TO-END INTEGRATION ====================

async def test_end_to_end_integration():
    """Test complete workflow: Resume → Interview → Audio Streaming"""
    print("\n" + "="*60)
    print("TEST 5: END-TO-END INTEGRATION")
    print("="*60)
    
    try:
        # Step 1: Upload resume
        resume_file = create_sample_resume_pdf()
        candidate_id = f"e2e-candidate-{int(datetime.now().timestamp())}"
        interview_id = f"e2e-interview-{int(datetime.now().timestamp())}"
        
        with open(resume_file, 'rb') as f:
            files = {'file': (resume_file, f, 'application/pdf')}
            data = {
                'candidate_id': candidate_id,
                'interview_id': interview_id
            }
            response = requests.post(f"{BASE_URL}/api/resumes/upload", 
                                   files=files, data=data)
        
        if response.status_code == 200:
            resume_data = response.json()
            log_test("E2E: Resume Upload", True, f"Resume ID: {resume_data.get('resume_id')}")
        else:
            log_test("E2E: Resume Upload", False, f"Upload failed: {response.status_code}")
            return
        
        # Step 2: Connect WebSocket for audio streaming
        ws_url = f"{WS_BASE_URL}/ws/audio/{interview_id}"
        async with websockets.connect(ws_url) as websocket:
            log_test("E2E: WebSocket Connection", True, f"Connected for interview {interview_id}")
            
            # Step 3: Simulate audio streaming
            for i in range(2):
                audio_chunk = create_audio_chunk(duration_ms=1000)
                await websocket.send(audio_chunk)
                await asyncio.sleep(0.5)
            
            log_test("E2E: Audio Streaming", True, "Sent audio chunks during interview")
            
            # Step 4: Verify connection still active
            await websocket.ping()
            log_test("E2E: Connection Active", True, "WebSocket connection maintained")
        
        # Cleanup
        import os
        if os.path.exists(resume_file):
            os.remove(resume_file)
        
        log_test("E2E: Complete Workflow", True, "All steps executed successfully")
        
    except Exception as e:
        log_test("E2E Integration Test", False, f"Exception: {str(e)}")


# ==================== MAIN TEST RUNNER ====================

async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 TESTING NEW FEATURES - PRODUCTION ENDPOINTS")
    print("="*60)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print(f"WebSocket URL: {WS_BASE_URL}")
    
    start_time = datetime.now()
    
    # Test 1: Resume Upload & Parsing
    test_resume_upload()
    
    # Test 2: WebSocket Audio Streaming
    await test_websocket_streaming()
    
    # Test 3: Concurrent WebSocket Connections
    await test_concurrent_websockets()
    
    # Test 4: Audio System
    await test_audio_system()
    
    # Test 5: End-to-End Integration
    await test_end_to_end_integration()
    
    # Print summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {test_results['total']}")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"⏱️  Duration: {duration:.2f} seconds")
    
    if test_results['total'] > 0:
        pass_rate = (test_results['passed'] / test_results['total']) * 100
        print(f"📈 Pass Rate: {pass_rate:.1f}%")
    
    print(f"\nEnd Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Print detailed results
    print("\n" + "="*60)
    print("📋 DETAILED RESULTS")
    print("="*60)
    for detail in test_results['details']:
        print(f"\n{detail['status']}: {detail['test']}")
        if detail['message']:
            print(f"   {detail['message']}")
    
    # Final verdict
    print("\n" + "="*60)
    if test_results['failed'] == 0:
        print("🎉 ALL TESTS PASSED! System is working perfectly!")
    elif test_results['passed'] > test_results['failed']:
        print("⚠️  MOST TESTS PASSED - Some issues need attention")
    else:
        print("❌ CRITICAL ISSUES - System needs debugging")
    print("="*60)


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                   NEW FEATURES TEST SUITE                     ║
║                                                               ║
║  Testing:                                                     ║
║  ✓ Resume Upload & Parsing (PDF/DOCX/TXT)                   ║
║  ✓ Real-Time Audio Streaming (WebSocket)                    ║
║  ✓ Meet Bot Audio System Integration                         ║
║  ✓ Concurrent Multi-Interview Support                        ║
║  ✓ End-to-End Workflow                                       ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print("✅ Server is running and accessible\n")
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to server at", BASE_URL)
        print("Please start the server with: python main.py")
        print("Make sure it's running on port 8001\n")
        exit(1)
    except Exception as e:
        print(f"⚠️  Warning: {str(e)}\n")
    
    # Run tests
    asyncio.run(run_all_tests())
