"""
Quick Meeting Creator for Testing

This utility creates Google Meet meetings with the bot automatically invited.
Perfect for local testing without manual setup.

Usage:
    python create_test_meeting.py

Author: AI Recruiter Team
Created: February 2026
"""

import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from services.google_calendar_service import GoogleCalendarService

load_dotenv()


async def create_test_meeting():
    """
    Create a test Google Meet with bot auto-invited.
    """
    print("\n" + "="*60)
    print("🎥 CREATE TEST GOOGLE MEET WITH BOT AUTO-INVITED")
    print("="*60 + "\n")
    
    # Get inputs
    candidate_name = input("Candidate name (default: Test Candidate): ").strip() or "Test Candidate"
    candidate_email = input("Candidate email (default: candidate@example.com): ").strip() or "candidate@example.com"
    hr_email = input("HR email (default: swarupkakade1810@gmail.com): ").strip() or "swarupkakade1810@gmail.com"
    job_title = input("Job title (default: Software Engineer): ").strip() or "Software Engineer"
    
    # Schedule for 5 minutes from now
    interview_datetime = datetime.now() + timedelta(minutes=5)
    print(f"\n📅 Scheduling for: {interview_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create meeting
    print("\n🔄 Creating Google Meet...")
    calendar_service = GoogleCalendarService()
    
    result = calendar_service.create_interview_meeting(
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        hr_email=hr_email,
        job_title=job_title,
        interview_datetime=interview_datetime,
        duration_minutes=30
    )
    
    if result["success"]:
        data = result["data"]
        
        print("\n" + "="*60)
        print("✅ MEETING CREATED SUCCESSFULLY!")
        print("="*60)
        print(f"\n🔗 Google Meet Link: {data['meet_link']}")
        print(f"📅 Calendar Event: {data['calendar_link']}")
        print(f"🕐 Event ID: {data['event_id']}")
        print(f"⏰ Expires at: {data['expires_at']}")
        
        print("\n" + "="*60)
        print("👥 ATTENDEES (AUTO-INVITED):")
        print("="*60)
        print(f"1. {candidate_name} ({candidate_email})")
        print(f"2. HR Recruiter ({hr_email})")
        print(f"3. 🤖 AI Interview Bot ({os.getenv('MEET_BOT_EMAIL', 'airecruiterbot@gmail.com')}) ✅")
        
        print("\n" + "="*60)
        print("🧪 TESTING INSTRUCTIONS:")
        print("="*60)
        print("1. Bot is now invited - can join without approval!")
        print("2. Test join with: python meet_audio_integration.py")
        print(f"3. Paste URL: {data['meet_link']}")
        print("4. Bot will auto-join (no 'Ask to join' needed)")
        print("\n" + "="*60 + "\n")
        
    else:
        print("\n" + "="*60)
        print("❌ MEETING CREATION FAILED")
        print("="*60)
        error = result.get("error", {})
        print(f"Error Code: {error.get('code', 'UNKNOWN')}")
        print(f"Message: {error.get('message', 'Unknown error')}")
        print(f"Details: {error.get('details', {})}")
        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(create_test_meeting())
