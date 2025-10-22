"""
Test script to create a real Google Meet link and verify it's accessible
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.google_calendar_service import GoogleCalendarService
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_meet_link_creation():
    """Create a test Google Meet link and display it"""
    print("\n" + "="*80)
    print("🧪 TESTING GOOGLE MEET LINK CREATION")
    print("="*80 + "\n")
    
    try:
        # Initialize Google Calendar service
        calendar_service = GoogleCalendarService()
        
        # Create a test interview meeting
        scheduled_time = datetime.utcnow() + timedelta(hours=2)
        
        print("📅 Creating test interview meeting...")
        print(f"   Scheduled for: {scheduled_time.isoformat()}")
        print(f"   Duration: 30 minutes\n")
        
        result = calendar_service.create_interview_meeting(
            candidate_name="Test Candidate",
            candidate_email="test.candidate@example.com",  # Replace with your test email
            hr_email="hr@example.com",  # Replace with your email
            job_title="Test Position",
            interview_datetime=scheduled_time,
            duration_minutes=30,
            interview_id="test-interview-123"
        )
        
        if result["success"]:
            data = result["data"]
            
            print("✅ SUCCESS! Meet link created:\n")
            print("="*80)
            print(f"🔗 MEET LINK: {data['meet_link']}")
            print("="*80)
            print(f"\n📅 Calendar Link: {data['calendar_link']}")
            print(f"🆔 Event ID: {data['event_id']}")
            print(f"⏰ Scheduled: {data['scheduled_for']}")
            print(f"⏳ Expires: {data['expires_at']}")
            print(f"\n👥 Attendees:")
            for attendee in data['attendees']:
                print(f"   - {attendee['name']} ({attendee['email']})")
            
            print("\n" + "="*80)
            print("🎯 VERIFICATION STEPS:")
            print("="*80)
            print(f"\n1. Copy this link: {data['meet_link']}")
            print("2. Open it in a browser (incognito mode recommended)")
            print("3. You should see Google Meet interface")
            print("4. Click 'Ask to join' or 'Join now'")
            print("5. ✅ If you can join, the link is LEGITIMATE and ACCESSIBLE!")
            print("\n" + "="*80 + "\n")
            
            return True
        else:
            print(f"❌ FAILED: {result['error']['message']}\n")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_meet_link_creation()
    sys.exit(0 if success else 1)
