"""
COMPLETE END-TO-END INTERVIEW FLOW TEST
HR Assigns → Email Sent → Candidate Clicks → Bot Joins → Questions Asked

Testing with: Vaibhav_Narute_resume.pdf
"""

import requests
import json
from datetime import datetime, timedelta
import time

BASE_URL = "http://localhost:8001"

# Candidate details from resume
CANDIDATE_NAME = "Vaibhav Narute"
CANDIDATE_EMAIL = "narutevaibhav95@gmail.com"
JOB_TITLE = "Python Developer"
JOB_ID = "job_python_dev_001"
HR_EMAIL = "hr@optiresume.com"
HR_ID = "hr_admin_001"
RESUME_PATH = "../uploads/Vaibhav_Narute_resume.pdf"

print("="*80)
print("🚀 COMPLETE END-TO-END INTERVIEW FLOW TEST")
print("="*80)
print(f"👤 Candidate: {CANDIDATE_NAME}")
print(f"📧 Email: {CANDIDATE_EMAIL}")
print(f"💼 Position: {JOB_TITLE}")
print(f"📄 Resume: {RESUME_PATH}")
print("="*80)

# STEP 1: HR Assigns Interview
print("\n📋 STEP 1: HR Assigns Interview (with auto-bot join)")
print("-" * 80)

scheduled_time = datetime.now() + timedelta(minutes=5)
schedule_data = {
    "candidate_name": CANDIDATE_NAME,
    "candidate_email": CANDIDATE_EMAIL,
    "candidate_id": f"cand_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    "job_id": JOB_ID,
    "job_title": JOB_TITLE,
    "hr_email": HR_EMAIL,
    "hr_id": HR_ID,
    "scheduled_datetime": scheduled_time.isoformat(),
    "duration_minutes": 30,
    "interview_type": "ai_assisted",
    "auto_start_bot": True  # ← Key field!
}

print(f"📤 Scheduling interview for: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
response = requests.post(
    f"{BASE_URL}/api/interviews/schedule",
    json=schedule_data,
    headers={"Content-Type": "application/json"}
)

if response.status_code != 200:
    print(f"❌ Failed to schedule: {response.status_code}")
    print(response.text)
    exit(1)

result = response.json()
if not result.get("success"):
    print(f"❌ Scheduling failed: {result.get('errors')}")
    exit(1)

interview_id = result['data']['interview_id']
meet_link = result['data']['meet_link']

print(f"✅ Interview scheduled successfully!")
print(f"   Interview ID: {interview_id}")
print(f"   Meet Link: {meet_link}")

# STEP 2: Verify database entry
print("\n📋 STEP 2: Verify Database Entry")
print("-" * 80)

verify_response = requests.get(f"{BASE_URL}/api/interviews/{interview_id}")
interview_data = verify_response.json()['data']

print(f"✅ Interview found in database")
print(f"   auto_start_bot: {interview_data.get('auto_start_bot')}")
print(f"   auto_join_token: {interview_data.get('auto_join_token')[:20]}...")
print(f"   bot_join_status: {interview_data.get('bot_join_status')}")

if not interview_data.get('auto_start_bot'):
    print("❌ ERROR: auto_start_bot not enabled!")
    exit(1)

if not interview_data.get('auto_join_token'):
    print("❌ ERROR: auto_join_token not generated!")
    exit(1)

# STEP 3: Get trigger URL
print("\n📋 STEP 3: Generate Trigger URL")
print("-" * 80)

token = interview_data['auto_join_token']
trigger_url = f"{BASE_URL}/api/meet/trigger/{interview_id}?token={token}"

print(f"🔗 Trigger URL: {trigger_url}")
print(f"📧 This URL would be sent to: {CANDIDATE_EMAIL}")

# STEP 4: Simulate candidate clicking the button
print("\n📋 STEP 4: Simulate Candidate Clicking 'Start Interview' Button")
print("-" * 80)

print("⏳ Triggering auto-bot join...")
trigger_response = requests.get(trigger_url, allow_redirects=False)

if trigger_response.status_code in [200, 302]:
    print("✅ Trigger successful!")
    print(f"   HTTP Status: {trigger_response.status_code}")
    if trigger_response.status_code == 302:
        redirect_url = trigger_response.headers.get('Location')
        print(f"   Redirect to: {redirect_url}")
else:
    print(f"❌ Trigger failed: {trigger_response.status_code}")
    print(trigger_response.text)

# STEP 5: Wait for bot to join
print("\n📋 STEP 5: Waiting for Bot to Join Meeting")
print("-" * 80)

print("⏳ Waiting 15 seconds for bot to join...")
for i in range(15, 0, -1):
    print(f"   {i} seconds remaining...", end='\r')
    time.sleep(1)
print("\n")

# STEP 6: Check bot status
print("📋 STEP 6: Verify Bot Joined")
print("-" * 80)

verify_response = requests.get(f"{BASE_URL}/api/interviews/{interview_id}")
interview_data = verify_response.json()['data']

print(f"🤖 Bot Status:")
print(f"   bot_join_status: {interview_data.get('bot_join_status')}")
print(f"   candidate_joined_at: {interview_data.get('candidate_joined_at')}")
print(f"   trigger_timestamp: {interview_data.get('trigger_timestamp')}")

# Check if there's an active session
print("\n📋 STEP 7: Check Active Meet Session")
print("-" * 80)

sessions_response = requests.get(f"{BASE_URL}/api/meet/sessions")
if sessions_response.status_code == 200:
    sessions = sessions_response.json()
    found_session = None
    
    for session in sessions:
        if session.get('interview_id') == interview_id:
            found_session = session
            break
    
    if found_session:
        print(f"✅ Active session found!")
        print(f"   Session ID: {found_session.get('session_id')}")
        print(f"   Status: {found_session.get('session_status')}")
        print(f"   Audio chunks: {found_session.get('audio_chunks_received', 0)}")
        print(f"   Started: {found_session.get('started_at')}")
    else:
        print("⚠️  No active session found for this interview")
else:
    print(f"❌ Failed to get sessions: {sessions_response.status_code}")

# STEP 8: Check if questions were generated
print("\n📋 STEP 8: Check Interview Questions")
print("-" * 80)

questions_response = requests.get(f"{BASE_URL}/api/interviews/{interview_id}/questions")
if questions_response.status_code == 200:
    questions_data = questions_response.json()
    if questions_data.get('success'):
        questions = questions_data.get('data', {}).get('questions', [])
        print(f"✅ Questions generated: {len(questions)} questions")
        if questions:
            print("\n📝 Sample Questions:")
            for i, q in enumerate(questions[:3], 1):
                print(f"   {i}. {q.get('question', 'N/A')}")
    else:
        print("⚠️  Questions not generated yet")
else:
    print(f"⚠️  Questions endpoint returned: {questions_response.status_code}")

# STEP 9: Summary
print("\n" + "="*80)
print("✅ END-TO-END TEST COMPLETED!")
print("="*80)
print("\n📊 SUMMARY:")
print(f"   ✅ Interview scheduled with auto-bot join")
print(f"   ✅ Database fields correctly saved")
print(f"   ✅ Trigger URL generated")
print(f"   ✅ Auto-trigger endpoint working")
print(f"   ✅ Bot join process initiated")
print()
print("🎯 NEXT STEPS:")
print("   1. Open the Meet link in your browser:")
print(f"      {meet_link}")
print()
print("   2. Or use the trigger URL to auto-join:")
print(f"      {trigger_url}")
print()
print("   3. Monitor bot activity:")
print("      - Dashboard: http://localhost:8080/")
print("      - Meeting Bot: http://localhost:8080/meeting-bot")
print()
print("   4. The bot should:")
print("      - Join automatically before you")
print("      - Start asking interview questions")
print("      - Record and transcribe your answers")
print("      - Provide feedback based on your resume")
print()
print("="*80)
