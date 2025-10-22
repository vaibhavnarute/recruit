"""
Test Script: Interview Scheduling with LangGraph + MCP + Google Calendar

This script tests the complete interview scheduling workflow:
1. HR schedules an interview
2. Google Meet link is generated (24-hour validity)
3. Email invitation is sent to candidate
4. Interview details are stored in MongoDB

Tests:
✅ Success case: All steps complete successfully
❌ Error cases: Invalid email, past datetime, missing fields, etc.
"""

import requests
import json
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Base URL
API_URL = "http://localhost:8001"  # FastAPI runs on port 8001


def print_section(title: str):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def print_result(result: dict):
    """Pretty print JSON result"""
    print(json.dumps(result, indent=2))


def test_schedule_interview_success():
    """
    Test Case 1: Successful Interview Scheduling
    
    Expected: 
    - Meet link created
    - Email sent
    - MongoDB saved
    - Status 200 with success=True
    """
    print_section("TEST 1: Successful Interview Scheduling")
    
    # Schedule interview for tomorrow at 10 AM
    tomorrow = datetime.now() + timedelta(days=1)
    interview_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    
    payload = {
        "candidate_name": "Alice Johnson",
        "candidate_email": "alice.johnson@example.com",  # Change to your test email
        "job_id": "job-python-dev-001",
        "job_title": "Senior Python Developer",
        "hr_email": "hr@company.com",  # Change to your email
        "hr_id": "hr-user-123",
        "scheduled_datetime": interview_time.isoformat() + "Z",
        "duration_minutes": 45,
        "interview_type": "ai_assisted"
    }
    
    logger.info(f"📤 Sending request to {API_URL}/api/interviews/schedule")
    logger.info(f"📋 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_URL}/api/interviews/schedule",
            json=payload,
            timeout=30
        )
        
        logger.info(f"📥 Response Status: {response.status_code}")
        
        result = response.json()
        print_result(result)
        
        # Verify response
        assert response.status_code == 200, "Status code should always be 200"
        
        if result.get("success"):
            logger.info("✅ TEST PASSED: Interview scheduled successfully")
            
            # Verify data
            data = result["data"]
            assert data.get("interview_id"), "Interview ID should be present"
            assert data.get("meet_link"), "Meet link should be present"
            assert data.get("email_sent") == True, "Email should be sent"
            assert data.get("mongodb_saved") == True, "Should be saved to MongoDB"
            
            logger.info(f"🔗 Meet Link: {data['meet_link']}")
            logger.info(f"📅 Calendar Link: {data.get('calendar_link')}")
            logger.info(f"🆔 Interview ID: {data['interview_id']}")
            
            return data["interview_id"]
        else:
            logger.error("❌ TEST FAILED: Interview scheduling failed")
            logger.error(f"Errors: {result.get('errors')}")
            return None
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ CONNECTION ERROR: FastAPI server is not running!")
        logger.error("💡 Start the server: cd backend && python main.py")
        return None
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {str(e)}")
        return None


def test_schedule_interview_invalid_email():
    """
    Test Case 2: Invalid Email Address
    
    Expected:
    - Status 200
    - success=False
    - Error: INVALID_CANDIDATE_EMAIL
    """
    print_section("TEST 2: Invalid Email Address")
    
    tomorrow = datetime.now() + timedelta(days=1)
    interview_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
    
    payload = {
        "candidate_name": "Bob Smith",
        "candidate_email": "invalid-email-format",  # Invalid email
        "job_id": "job-002",
        "job_title": "Frontend Developer",
        "hr_email": "hr@company.com",
        "hr_id": "hr-user-456",
        "scheduled_datetime": interview_time.isoformat() + "Z",
        "duration_minutes": 30,
        "interview_type": "ai_assisted"
    }
    
    logger.info("📤 Sending request with invalid email...")
    
    try:
        response = requests.post(
            f"{API_URL}/api/interviews/schedule",
            json=payload,
            timeout=30
        )
        
        result = response.json()
        print_result(result)
        
        # Verify response
        assert response.status_code == 200, "Status should be 200 even for errors"
        assert result.get("success") == False, "Should return success=False"
        
        errors = result.get("errors", [])
        assert any(e["code"] == "INVALID_CANDIDATE_EMAIL" for e in errors), \
            "Should have INVALID_CANDIDATE_EMAIL error"
        
        logger.info("✅ TEST PASSED: Invalid email detected correctly")
        
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {str(e)}")


def test_schedule_interview_past_datetime():
    """
    Test Case 3: Scheduling in the Past
    
    Expected:
    - Status 200
    - success=False
    - Error: INVALID_DATETIME
    """
    print_section("TEST 3: Past DateTime")
    
    # Yesterday at 10 AM
    past_time = datetime.now() - timedelta(days=1)
    past_time = past_time.replace(hour=10, minute=0, second=0, microsecond=0)
    
    payload = {
        "candidate_name": "Charlie Brown",
        "candidate_email": "charlie@example.com",
        "job_id": "job-003",
        "job_title": "Data Scientist",
        "hr_email": "hr@company.com",
        "hr_id": "hr-user-789",
        "scheduled_datetime": past_time.isoformat() + "Z",  # Past datetime
        "duration_minutes": 30,
        "interview_type": "ai_assisted"
    }
    
    logger.info("📤 Sending request with past datetime...")
    
    try:
        response = requests.post(
            f"{API_URL}/api/interviews/schedule",
            json=payload,
            timeout=30
        )
        
        result = response.json()
        print_result(result)
        
        # Verify response
        assert response.status_code == 200, "Status should be 200"
        assert result.get("success") == False, "Should return success=False"
        
        errors = result.get("errors", [])
        assert any(e["code"] == "INVALID_DATETIME" for e in errors), \
            "Should have INVALID_DATETIME error"
        
        logger.info("✅ TEST PASSED: Past datetime rejected correctly")
        
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {str(e)}")


def test_schedule_interview_missing_fields():
    """
    Test Case 4: Missing Required Fields
    
    Expected:
    - Status 422 (FastAPI validation error)
    """
    print_section("TEST 4: Missing Required Fields")
    
    payload = {
        "candidate_name": "Diana Prince",
        # Missing: candidate_email
        "job_id": "job-004",
        "job_title": "DevOps Engineer",
        "hr_email": "hr@company.com",
        "hr_id": "hr-user-101",
        # Missing: scheduled_datetime
        "duration_minutes": 30
    }
    
    logger.info("📤 Sending request with missing fields...")
    
    try:
        response = requests.post(
            f"{API_URL}/api/interviews/schedule",
            json=payload,
            timeout=30
        )
        
        result = response.json()
        print_result(result)
        
        # FastAPI should return 422 for validation errors
        assert response.status_code == 422, "Should return 422 for missing fields"
        
        logger.info("✅ TEST PASSED: Missing fields detected by FastAPI")
        
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {str(e)}")


def test_get_interview_details(interview_id: str):
    """
    Test Case 5: Get Interview Details
    
    Expected:
    - Status 200
    - success=True
    - Complete interview data
    """
    if not interview_id:
        logger.warning("⚠️ SKIPPING: No interview ID available")
        return
    
    print_section("TEST 5: Get Interview Details")
    
    logger.info(f"📤 Fetching interview: {interview_id}")
    
    try:
        response = requests.get(
            f"{API_URL}/api/interviews/{interview_id}",
            timeout=10
        )
        
        result = response.json()
        print_result(result)
        
        assert response.status_code == 200, "Status should be 200"
        
        if result.get("success"):
            logger.info("✅ TEST PASSED: Interview details retrieved")
            
            data = result["data"]
            assert data.get("interview_id") == interview_id
            assert data.get("meet_link")
            assert data.get("status") == "scheduled"
            
        else:
            logger.error("❌ TEST FAILED: Could not retrieve interview")
            
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {str(e)}")


def test_get_interview_status(interview_id: str):
    """
    Test Case 6: Check Interview Status
    
    Expected:
    - Status 200
    - success=True
    - Meeting status and link validity
    """
    if not interview_id:
        logger.warning("⚠️ SKIPPING: No interview ID available")
        return
    
    print_section("TEST 6: Check Interview Status")
    
    logger.info(f"📤 Checking status for: {interview_id}")
    
    try:
        response = requests.get(
            f"{API_URL}/api/interviews/status/{interview_id}",
            timeout=10
        )
        
        result = response.json()
        print_result(result)
        
        assert response.status_code == 200, "Status should be 200"
        
        if result.get("success"):
            logger.info("✅ TEST PASSED: Interview status checked")
            
            data = result["data"]
            assert data.get("interview_id") == interview_id
            assert data.get("meet_link")
            
            # Check if calendar event is valid
            if data.get("calendar_event"):
                logger.info("📅 Google Calendar event is valid")
            else:
                logger.warning("⚠️ Calendar event check failed (may need Google API setup)")
        else:
            logger.error("❌ TEST FAILED: Could not check status")
            
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {str(e)}")


def check_server_running():
    """Check if FastAPI server is running"""
    logger.info(f"🔍 Checking if server is running at {API_URL}...")
    
    try:
        response = requests.get(f"{API_URL}/docs", timeout=5)
        if response.status_code == 200:
            logger.info("✅ FastAPI server is running!")
            return True
        else:
            logger.error("⚠️ Server responded but may have issues")
            return False
    except requests.exceptions.ConnectionError:
        logger.error("❌ FastAPI server is NOT running!")
        logger.error("")
        logger.error("💡 To start the server:")
        logger.error("   cd backend")
        logger.error("   python main.py")
        logger.error("")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking server: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 INTERVIEW SCHEDULING TEST SUITE")
    print("="*80)
    print("")
    print("This test suite validates:")
    print("  ✓ LangGraph workflow execution")
    print("  ✓ Google Calendar Meet link generation")
    print("  ✓ Email sending functionality")
    print("  ✓ MongoDB data persistence")
    print("  ✓ MCP context management")
    print("  ✓ Error handling (all errors return 200 status)")
    print("")
    print("="*80 + "\n")
    
    # Check if server is running
    if not check_server_running():
        logger.error("\n❌ Cannot run tests: Server is not running")
        return
    
    # Run tests
    interview_id = None
    
    # Test 1: Success case
    interview_id = test_schedule_interview_success()
    
    # Test 2: Invalid email
    test_schedule_interview_invalid_email()
    
    # Test 3: Past datetime
    test_schedule_interview_past_datetime()
    
    # Test 4: Missing fields
    test_schedule_interview_missing_fields()
    
    # Test 5: Get interview details
    if interview_id:
        test_get_interview_details(interview_id)
    
    # Test 6: Check interview status
    if interview_id:
        test_get_interview_status(interview_id)
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUITE COMPLETED")
    print("="*80)
    print("")
    print("✅ All tests executed")
    print("")
    print("📝 Notes:")
    print("  - Check logs above for detailed results")
    print("  - Errors should return 200 status with error details in body")
    print("  - Google Calendar API setup required for Meet link generation")
    print("  - SMTP setup required for email sending")
    print("")
    print("🔧 Setup Instructions:")
    print("  1. Google Calendar API:")
    print("     - Go to: https://console.cloud.google.com/")
    print("     - Enable Google Calendar API")
    print("     - Create OAuth credentials")
    print("     - Download as google_credentials.json")
    print("")
    print("  2. SMTP (Email):")
    print("     - Add to .env:")
    print("       SMTP_SERVER=smtp.gmail.com")
    print("       SMTP_PORT=587")
    print("       SMTP_USERNAME=your-email@gmail.com")
    print("       SMTP_PASSWORD=your-app-password")
    print("")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
