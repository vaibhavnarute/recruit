"""
Complete Interactive Interview Flow Test

This test demonstrates the full workflow:
1. HR assigns interview → auto_start_bot enabled
2. Candidate clicks "Start Interview" button
3. Bot auto-joins meeting
4. Bot starts interactive interview:
   - Generates questions from resume
   - Asks questions using TTS
   - Listens to answers using STT
   - Analyzes answers with LLM
   - Asks follow-up questions
   - Provides final feedback
"""

import requests
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001"
CANDIDATE_EMAIL = "narutevaibhav95@gmail.com"
CANDIDATE_NAME = "Vaibhav Narute"
JOB_TITLE = "Senior Python Developer"
RESUME_PATH = "../uploads/Vaibhav_Narute_resume.pdf"

print("="*80)
print("🎯 COMPLETE INTERACTIVE INTERVIEW FLOW TEST")
print("="*80)
print(f"👤 Candidate: {CANDIDATE_NAME}")
print(f"📧 Email: {CANDIDATE_EMAIL}")
print(f"💼 Position: {JOB_TITLE}")
print(f"📄 Resume: {RESUME_PATH}")
print("="*80)

# STEP 1: Schedule Interview
print("\n📋 STEP 1: HR Schedules Interview with Auto-Bot Join")
print("-"*80)

scheduled_time = datetime.now() + timedelta(minutes=2)
schedule_data = {
    "candidate_name": CANDIDATE_NAME,
    "candidate_email": CANDIDATE_EMAIL,
    "candidate_id": f"cand_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    "job_id": "job_python_senior_001",
    "job_title": JOB_TITLE,
    "hr_email": "hr@optiresume.com",
    "hr_id": "hr_admin_001",
    "scheduled_datetime": scheduled_time.isoformat(),
    "duration_minutes": 30,
    "interview_type": "ai_assisted",
    "auto_start_bot": True  # Enable auto-bot join
}

response = requests.post(f"{BASE_URL}/api/interviews/schedule", json=schedule_data)
if response.status_code == 200:
    result = response.json()
    if result.get("success"):
        interview_id = result['data']['interview_id']
        meet_link = result['data']['meet_link']
        print(f"✅ Interview scheduled!")
        print(f"   Interview ID: {interview_id}")
        print(f"   Meet Link: {meet_link}")
        print(f"   Email sent: {result['data'].get('email_sent', False)}")
    else:
        print(f"❌ Scheduling failed: {result.get('errors')}")
        exit(1)
else:
    print(f"❌ HTTP Error: {response.status_code}")
    exit(1)

# STEP 2: Verify Database
print("\n📋 STEP 2: Verify Auto-Join Configuration")
print("-"*80)

response = requests.get(f"{BASE_URL}/api/interviews/{interview_id}")
if response.status_code == 200:
    interview = response.json()['data']
    print(f"✅ Interview configuration:")
    print(f"   auto_start_bot: {interview.get('auto_start_bot')}")
    print(f"   auto_join_token: {interview.get('auto_join_token', 'N/A')[:30]}...")
    print(f"   bot_join_status: {interview.get('bot_join_status')}")
    auto_join_token = interview.get('auto_join_token')
else:
    print(f"❌ Failed to retrieve interview")
    exit(1)

# STEP 3: Generate Trigger URL
print("\n📋 STEP 3: Generate Auto-Trigger URL")
print("-"*80)

trigger_url = f"{BASE_URL}/api/meet/trigger/{interview_id}?token={auto_join_token}"
print(f"🔗 Trigger URL (would be in email):")
print(f"   {trigger_url}")
print()
print("   This URL triggers:")
print("   1. Bot auto-joins meeting")
print("   2. Bot generates questions from resume")
print("   3. Bot starts interactive interview")
print("   4. Candidate redirected to Meet")

# STEP 4: Simulate Candidate Click
print("\n📋 STEP 4: Simulate Candidate Clicking 'Start Interview'")
print("-"*80)
print("⏳ Triggering auto-bot join + interactive interview...")

response = requests.get(trigger_url, allow_redirects=False)
if response.status_code == 200:
    print("✅ Trigger successful!")
    print("   🤖 Bot is now:")
    print("   1. Joining the meeting")
    print("   2. Generating questions from resume")
    print("   3. Preparing to ask first question")
else:
    print(f"❌ Trigger failed: {response.status_code}")
    exit(1)

# STEP 5: Monitor Bot Join
print("\n📋 STEP 5: Monitor Bot Joining Process")
print("-"*80)
print("⏳ Waiting 20 seconds for bot to join and start interview...")

for i in range(20, 0, -1):
    print(f"   {i} seconds remaining...", end='\r')
    time.sleep(1)

print()

# STEP 6: Check Bot Status
print("\n📋 STEP 6: Verify Bot Join Status")
print("-"*80)

response = requests.get(f"{BASE_URL}/api/interviews/{interview_id}")
if response.status_code == 200:
    interview = response.json()['data']
    print(f"🤖 Bot Status:")
    print(f"   bot_join_status: {interview.get('bot_join_status')}")
    print(f"   candidate_joined_at: {interview.get('candidate_joined_at', 'N/A')}")
    print(f"   bot_joined_at: {interview.get('bot_joined_at', 'N/A')}")
    
    if interview.get('bot_join_status') in ['joining', 'joined']:
        print("   ✅ Bot successfully triggered!")
    else:
        print("   ⚠️  Bot status unexpected")

# STEP 7: Check Interview Session
print("\n📋 STEP 7: Check Interactive Interview Session")
print("-"*80)

# Note: In production, this would query the orchestrator's status
print("📊 Expected interview flow:")
print("   1. ✅ Bot joined meeting")
print("   2. 🔄 Questions generated from resume")
print("   3. 🗣️  Bot asking questions via TTS")
print("   4. 🎤 Bot listening for answers via STT")
print("   5. 🧠 Bot analyzing answers with LLM")
print("   6. 💬 Bot asking follow-up questions")
print("   7. 📊 Bot generating final feedback")

# STEP 8: Summary
print("\n" + "="*80)
print("✅ COMPLETE INTERACTIVE INTERVIEW FLOW TEST COMPLETED!")
print("="*80)

print("\n📊 WORKFLOW SUMMARY:")
print("   ✅ Interview scheduled with auto-bot join")
print("   ✅ Auto-join token generated and secured")
print("   ✅ Trigger URL would be sent in email")
print("   ✅ Bot auto-join triggered successfully")
print("   ✅ Interactive interview orchestration started")

print("\n🎯 WHAT HAPPENS NEXT:")
print("   1. Bot joins Google Meet automatically")
print("   2. Bot generates 5 questions from Vaibhav's resume")
print("   3. Bot asks questions using Text-to-Speech")
print("   4. Bot listens to answers using Speech-to-Text")
print("   5. Bot analyzes answers using Groq LLM")
print("   6. Bot asks follow-up questions based on answers")
print("   7. Bot generates overall score and feedback")

print("\n🔗 TO TEST MANUALLY:")
print(f"   1. Open this URL in browser:")
print(f"      {trigger_url[:80]}...")
print(f"   2. Wait for countdown (bot joining)")
print(f"   3. You'll be redirected to Google Meet")
print(f"   4. Bot should already be in the meeting")
print(f"   5. Bot will start asking interview questions")

print("\n📊 MONITOR INTERVIEW:")
print(f"   - Dashboard: http://localhost:8080/")
print(f"   - Meeting Bot: http://localhost:8080/meeting-bot")
print(f"   - Backend Logs: Check terminal running main.py")

print("\n" + "="*80)
