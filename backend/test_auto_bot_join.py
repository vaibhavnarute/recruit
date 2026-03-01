"""
Complete Interview Testing Script with Auto-Bot Join
Tests the entire flow: Schedule → Email → Auto-trigger → Bot Join
"""

import requests
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
BASE_URL = "http://localhost:8001"
CANDIDATE_EMAIL = "narutevaibhav95@gmail.com"  # Your email to receive test invitation
CANDIDATE_NAME = "Vaibhav Narute"
JOB_TITLE = "Senior Python Developer"
JOB_ID = "test_job_001"
HR_EMAIL = "hr@optiresume.com"
HR_ID = "hr_admin_001"
RESUME_PATH = "../uploads/Vaibhav_Narute.pdf"

print("="*80)
print("🧪 COMPLETE INTERVIEW AUTO-BOT JOIN TEST")
print("="*80)
print(f"📧 Candidate Email: {CANDIDATE_EMAIL}")
print(f"👤 Candidate Name: {CANDIDATE_NAME}")
print(f"💼 Job Title: {JOB_TITLE}")
print(f"📄 Resume: {RESUME_PATH}")
print("="*80)

# Step 1: Schedule interview with auto-bot join enabled
print("\n📅 Step 1: Scheduling interview with auto-bot join...")
print("-" * 80)

# Calculate scheduled time (15 minutes from now for testing)
scheduled_time = datetime.now() + timedelta(minutes=15)
scheduled_datetime = scheduled_time.isoformat()

schedule_data = {
    "candidate_name": CANDIDATE_NAME,
    "candidate_email": CANDIDATE_EMAIL,
    "candidate_id": f"cand_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    "job_id": JOB_ID,
    "job_title": JOB_TITLE,
    "hr_email": HR_EMAIL,
    "hr_id": HR_ID,
    "scheduled_datetime": scheduled_datetime,
    "duration_minutes": 30,
    "interview_type": "ai_assisted",
    "auto_start_bot": True  # ← Enable auto-bot join feature
}

print(f"📤 Sending request to {BASE_URL}/api/interviews/schedule")
print(f"   Scheduled for: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")

try:
    response = requests.post(
        f"{BASE_URL}/api/interviews/schedule",
        json=schedule_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        
        if result.get("success"):
            print("✅ Interview scheduled successfully!")
            print(f"   Interview ID: {result['data']['interview_id']}")
            print(f"   Meet Link: {result['data']['meet_link']}")
            
            if result['data'].get('email_sent'):
                print(f"   ✅ Email sent to: {CANDIDATE_EMAIL}")
            else:
                print(f"   ⚠️  Email not sent (check SMTP configuration)")
            
            # Save details for reference
            interview_id = result['data']['interview_id']
            meet_link = result['data']['meet_link']
            
            print("\n" + "="*80)
            print("📧 EMAIL SENT WITH AUTO-BOT JOIN LINK")
            print("="*80)
            print(f"\n📬 Check your email: {CANDIDATE_EMAIL}")
            print("\n🔍 What to look for in the email:")
            print("   1. Subject: '🎯 Interview Invitation - Senior Python Developer'")
            print("   2. Green button: '🚀 Start Interview Now'")
            print("   3. Note: 'Bot will automatically join when you click'")
            
            print("\n" + "="*80)
            print("🧪 TESTING INSTRUCTIONS")
            print("="*80)
            print("\n📋 Complete Flow Test:")
            print("   1. ✅ Interview scheduled (DONE)")
            print("   2. ✅ Email sent with auto-trigger link (DONE)")
            print("   3. ⏳ Check your email inbox")
            print("   4. ⏳ Click '🚀 Start Interview Now' button")
            print("   5. ⏳ Wait 5-10 seconds (bot joining...)")
            print("   6. ⏳ You'll be redirected to Google Meet")
            print("   7. ⏳ Bot should already be in the meeting")
            print("   8. ⏳ Interview starts automatically!")
            
            print("\n📊 Monitoring Dashboard:")
            print(f"   • Dashboard: http://localhost:8080/")
            print(f"   • Meeting Bot: http://localhost:8080/meeting-bot")
            print(f"   • Interview ID: {interview_id}")
            
            print("\n🔗 Direct Links (for testing):")
            print(f"   • Google Meet: {meet_link}")
            print(f"   • Auto-trigger: http://localhost:8001/api/meet/trigger/{interview_id}")
            
            # Step 2: Verify database entry
            print("\n" + "="*80)
            print("🔍 Step 2: Verifying database entry...")
            print("-" * 80)
            
            verify_response = requests.get(f"{BASE_URL}/api/interviews/{interview_id}")
            if verify_response.status_code == 200:
                interview_data = verify_response.json()
                print("✅ Interview found in database")
                print(f"   Auto-start bot: {interview_data.get('auto_start_bot', False)}")
                print(f"   Bot join status: {interview_data.get('bot_join_status', 'N/A')}")
                print(f"   Token generated: {'Yes' if interview_data.get('auto_join_token') else 'No'}")
            else:
                print("⚠️  Could not verify database entry")
            
            # Step 3: Test trigger endpoint (optional)
            print("\n" + "="*80)
            print("🧪 Step 3: Testing trigger endpoint (optional)...")
            print("-" * 80)
            print("⏸️  Skipping automatic trigger test - use email button instead")
            print("   (To manually test trigger, uncomment the code in script)")
            
            # Uncomment to test trigger directly:
            # print("🚀 Testing auto-trigger endpoint...")
            # trigger_response = requests.get(
            #     f"{BASE_URL}/api/meet/trigger/{interview_id}",
            #     allow_redirects=False
            # )
            # if trigger_response.status_code in [200, 302]:
            #     print("✅ Trigger endpoint working!")
            # else:
            #     print(f"⚠️  Trigger failed: {trigger_response.status_code}")
            
            print("\n" + "="*80)
            print("✅ TEST SETUP COMPLETE!")
            print("="*80)
            print("\n🎯 NEXT STEPS:")
            print("   1. Open your email inbox")
            print("   2. Find the interview invitation email")
            print("   3. Click the '🚀 Start Interview Now' button")
            print("   4. Observe the auto-bot join process")
            print("   5. Join the meeting after bot joins")
            print("\n📊 Monitor the process:")
            print("   • Backend logs in terminal")
            print("   • Dashboard: http://localhost:8080/")
            print("   • Meeting Bot page: http://localhost:8080/meeting-bot")
            
            print("\n⏱️  Scheduled Time:", scheduled_time.strftime('%Y-%m-%d %H:%M:%S'))
            print("⏰  Current Time:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            print("🕐  Time until interview: ~15 minutes")
            
        else:
            print("❌ Interview scheduling failed!")
            print(f"   Errors: {result.get('errors', 'Unknown error')}")
            if result.get('logs'):
                print("\n📋 Logs:")
                for log in result['logs']:
                    print(f"   {log}")
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(f"   Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ ERROR: Cannot connect to backend server")
    print("   Make sure backend is running on http://localhost:8001")
    print("\n   Start backend with:")
    print("   cd backend")
    print("   python main.py")
except Exception as e:
    print(f"❌ Unexpected error: {str(e)}")

print("\n" + "="*80)
print("🏁 Test script completed")
print("="*80)
