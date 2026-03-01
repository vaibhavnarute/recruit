"""
Create Instant Google Meet with Open Access
No calendar invite needed - just an instant meeting link!

Usage:
    python create_instant_meet.py

Author: AI Recruiter Team
"""

import webbrowser
import time

print("\n" + "="*60)
print("🎥 CREATE INSTANT GOOGLE MEET (OPEN ACCESS)")
print("="*60 + "\n")

print("📋 INSTRUCTIONS:")
print("1. Opening Google Meet in browser...")
print("2. Click 'New meeting' → 'Start an instant meeting'")
print("3. Once in meeting, click the meeting info (i button)")
print("4. Click 'Change access' or gear icon")
print("5. Under 'Quick access' → Select 'Anyone with the link can join directly'")
print("6. Copy the meeting URL")
print("7. Use it with: python meet_audio_integration.py")
print("\n" + "="*60 + "\n")

# Open Google Meet
webbrowser.open("https://meet.google.com/")

print("✅ Browser opened!")
print("\n💡 TIP: With 'Quick access' enabled, bot joins automatically!")
print("\n" + "="*60 + "\n")
