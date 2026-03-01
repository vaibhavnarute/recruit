"""
Check if bot joined the meeting after trigger
"""
import requests
from datetime import datetime

INTERVIEW_ID = "0c832b77-d981-4b0e-bdec-c8439b3ce0c8"

print("="*80)
print("🔍 CHECKING BOT JOIN STATUS")
print("="*80)

# Get interview details
response = requests.get(f"http://localhost:8001/api/interviews/{INTERVIEW_ID}")
if response.status_code == 200:
    interview = response.json()['data']
    
    print(f"\n📋 Interview: {interview.get('interview_id')}")
    print(f"👤 Candidate: {interview.get('candidate_name')}")
    print(f"🔗 Meet Link: {interview.get('meet_link')}")
    print()
    print("🤖 BOT STATUS:")
    print(f"  bot_join_status: {interview.get('bot_join_status', 'N/A')}")
    print(f"  candidate_joined_at: {interview.get('candidate_joined_at', 'N/A')}")
    print(f"  bot_joined_at: {interview.get('bot_joined_at', 'N/A')}")
    print(f"  trigger_timestamp: {interview.get('trigger_timestamp', 'N/A')}")
    print()
    
    status = interview.get('bot_join_status')
    if status == 'joined':
        print("✅ Bot successfully joined the meeting!")
    elif status == 'joining':
        print("⏳ Bot is currently joining...")
    elif status == 'pending':
        print("⚠️  Bot has not started joining yet")
    else:
        print(f"❓ Bot status: {status}")
        
    # Check if there's an active session
    print()
    print("📊 Checking active meet session...")
    sessions_response = requests.get("http://localhost:8001/api/meet/sessions")
    if sessions_response.status_code == 200:
        sessions = sessions_response.json()
        for session in sessions:
            if session.get('interview_id') == INTERVIEW_ID:
                print(f"  Session ID: {session.get('session_id')}")
                print(f"  Status: {session.get('session_status')}")
                print(f"  Audio chunks: {session.get('audio_chunks_received', 0)}")
                break
    
else:
    print("❌ Failed to get interview details")

print("="*80)
