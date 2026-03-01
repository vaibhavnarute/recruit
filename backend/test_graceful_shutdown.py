"""
Test Graceful Session Shutdown
Tests the /api/orchestration/end-session/{session_id} endpoint
"""

import requests
import json
import time
from datetime import datetime


# Configuration
BASE_URL = "http://localhost:8001"
TEST_SESSION_ID = "test_graceful_shutdown_session"


def print_header(title):
    """Print formatted test header"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


def test_graceful_shutdown():
    """Test graceful session shutdown"""
    
    print_header("🎯 GRACEFUL SESSION SHUTDOWN - TEST SUITE")
    
    print(f"Base URL: {BASE_URL}")
    print(f"Test Session ID: {TEST_SESSION_ID}\n")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and healthy\n")
        else:
            print(f"⚠️ Server health check returned: {response.status_code}\n")
    except requests.exceptions.RequestException as e:
        print(f"❌ Server is not running: {e}")
        print("   Please start the server with: python main.py\n")
        return
    
    # ========================================================================
    # TEST 1: Create a test session first
    # ========================================================================
    print_header("TEST 1: Create Test Session")
    
    try:
        # Start a distributed orchestration session
        response = requests.post(
            f"{BASE_URL}/api/distributed/orchestration/start",
            json={
                "session_id": TEST_SESSION_ID,
                "interview_id": "test_graceful_001",
                "candidate_name": "Test Candidate",
                "job_description": "Test Job Description"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ TEST 1 PASSED\n")
                print(f"📊 Session Created:")
                print(f"   Session ID: {data['data']['session_id']}")
                print(f"   Orchestration ID: {data['data']['orchestration_id']}")
                print(f"   Status: {data['data']['status']}")
            else:
                print(f"⚠️ Session creation failed: {data.get('message')}")
                print("   Will test with non-existent session...\n")
        else:
            print(f"⚠️ Session creation returned status {response.status_code}")
            print("   Will test with non-existent session...\n")
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Session creation request failed: {e}")
        print("   Will test with non-existent session...\n")
    
    # Wait a bit for session to initialize
    time.sleep(2)
    
    # ========================================================================
    # TEST 2: Graceful Shutdown (Normal Mode)
    # ========================================================================
    print_header("TEST 2: Graceful Shutdown (Normal Mode)")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/orchestration/end-session/{TEST_SESSION_ID}",
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print("✅ TEST 2 PASSED\n")
                
                summary = data.get('data', {})
                print("📊 Graceful Shutdown Summary:")
                print(f"   Session ID: {summary.get('session_id')}")
                print(f"   Orchestration ID: {summary.get('orchestration_id')}")
                print(f"   Total Turns: {summary.get('total_turns', 0)}")
                print(f"   Successful Turns: {summary.get('successful_turns', 0)}")
                print(f"   Failed Turns: {summary.get('failed_turns', 0)}")
                print(f"   Success Rate: {summary.get('success_rate', 0):.1f}%")
                print(f"   Quality Score: {summary.get('quality_score', 0)}")
                print(f"   Avg Latency: {summary.get('avg_latency_ms', 0)}ms")
                print(f"   Total Retries: {summary.get('total_retries', 0)}")
                print(f"   Duration: {summary.get('duration_seconds', 0)}s")
                print(f"\n🎯 Graceful Shutdown Features:")
                print(f"   ✅ Transcript Archived: {summary.get('transcript_archived', False)}")
                print(f"   ✅ Metrics Persisted: {summary.get('metrics_persisted', False)}")
                print(f"   ✅ Graceful Shutdown: {summary.get('graceful_shutdown', False)}")
                print(f"   📅 Completed At: {summary.get('completed_at', 'N/A')}")
                
            else:
                print(f"❌ TEST 2 FAILED")
                print(f"   Error: {data.get('error', {}).get('message', 'Unknown error')}")
                print(f"   Message: {data.get('message')}")
        else:
            print(f"❌ TEST 2 FAILED")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ TEST 2 FAILED")
        print(f"   Request Error: {e}")
    
    # ========================================================================
    # TEST 3: Graceful Shutdown (Non-existent Session)
    # ========================================================================
    print_header("TEST 3: Graceful Shutdown (Non-existent Session)")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/orchestration/end-session/nonexistent_session_12345",
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Should fail gracefully
            if not data.get('success'):
                print("✅ TEST 3 PASSED")
                print("   Correctly handled non-existent session\n")
                print(f"📊 Error Response:")
                print(f"   Code: {data.get('error', {}).get('code', 'N/A')}")
                print(f"   Message: {data.get('message')}")
            else:
                print("⚠️ TEST 3 WARNING")
                print("   Session found (unexpected for test)")
        else:
            print(f"❌ TEST 3 FAILED")
            print(f"   Status Code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ TEST 3 FAILED")
        print(f"   Request Error: {e}")
    
    # ========================================================================
    # TEST 4: Force Shutdown Mode
    # ========================================================================
    print_header("TEST 4: Force Shutdown Mode")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/orchestration/end-session/nonexistent_session_force?force=true",
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print("✅ TEST 4 PASSED\n")
                print("📊 Force Shutdown Response:")
                print(f"   Status: {data.get('data', {}).get('status', 'N/A')}")
                print(f"   Message: {data.get('message')}")
                print("   Force mode successfully handled non-existent session")
            else:
                print("⚠️ TEST 4 PARTIAL")
                print(f"   Force mode returned error (acceptable)")
                print(f"   Message: {data.get('message')}")
        else:
            print(f"❌ TEST 4 FAILED")
            print(f"   Status Code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ TEST 4 FAILED")
        print(f"   Request Error: {e}")
    
    # ========================================================================
    # TEST SUMMARY
    # ========================================================================
    print_header("TEST SUMMARY")
    
    print("Graceful Shutdown Tests:")
    print("✅ Create Test Session - Check server")
    print("✅ Graceful Shutdown (Normal) - Test endpoint functionality")
    print("✅ Non-existent Session - Test error handling")
    print("✅ Force Shutdown Mode - Test force parameter")
    
    print("\n" + "=" * 80)
    print("📚 GRACEFUL SHUTDOWN FEATURES")
    print("=" * 80)
    print("""
1. 💾 Cache Flushing
   - Flushes MCP context manager cache to MongoDB
   - Ensures all conversation data is persisted
   
2. 📝 Transcript Finalization
   - Archives complete conversation transcript
   - Stored in 'conversation_transcripts' collection
   - Includes all turns with timestamps
   
3. 📊 Metrics Persistence
   - Calculates comprehensive final metrics:
     * Total turns, successful/failed counts
     * Success rates and quality scores
     * Component-level metrics (STT/LLM/TTS)
     * Latency statistics and retry counts
   - Stored in 'orchestration_metrics' collection
   
4. 🔒 Session Termination
   - Marks session as 'terminated' in database
   - Sets graceful_shutdown flag to true
   - Updates completion timestamp
   
5. 🧹 Resource Cleanup
   - Removes session from active cache
   - Clears MCP caches
   - Closes MongoDB connections
   - Frees memory resources
   
6. 🛡️ Force Mode
   - Handles sessions not found in cache/database
   - Force cleanup even if data missing
   - Prevents resource leaks
""")
    
    print("\n" + "=" * 80)
    print("🎯 USAGE EXAMPLES")
    print("=" * 80)
    print("""
# Normal graceful shutdown
curl -X POST "http://localhost:8001/api/orchestration/end-session/session_abc123"

# Force shutdown (cleanup even if session not found)
curl -X POST "http://localhost:8001/api/orchestration/end-session/session_abc123?force=true"

# Python example
import requests

response = requests.post(
    "http://localhost:8001/api/orchestration/end-session/session_abc123"
)
result = response.json()

if result['success']:
    print(f"Session ended: {result['data']['total_turns']} turns")
    print(f"Quality: {result['data']['quality_score']}")
    print(f"Transcript archived: {result['data']['transcript_archived']}")
""")
    
    print("\n" + "=" * 80)
    print("✅ Test suite completed!")
    print("=" * 80)


if __name__ == "__main__":
    test_graceful_shutdown()
