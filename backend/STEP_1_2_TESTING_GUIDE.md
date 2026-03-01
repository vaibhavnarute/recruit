# Google Meet Bot - Testing & Troubleshooting Guide

## 🔧 Step 1.2 Complete: Meeting Join & Setup

### ✅ What's Implemented

The bot can now:
- Navigate to Google Meet URLs
- Configure pre-join settings (camera off, mic on)
- Set display name
- Click "Ask to join" or "Join now" button
- Wait for host approval (if required)
- Detect meeting join status
- Handle errors and security restrictions

### 🧪 Testing the Join Functionality

#### Test 1: Create a Meeting for Bot Testing

**Option A: Allow Anyone with Link (Easiest)**
1. Go to https://meet.google.com
2. Click "New meeting" → "Create a meeting for later"
3. Click on meeting settings (gear icon)
4. Set "Quick access" to **"Anyone with the link can join directly"**
5. Copy the meeting URL
6. Run: `python meet_bot_joiner.py` and paste the URL

**Option B: Invite Bot Email (Recommended for Production)**
1. Create a Google Calendar event
2. Add Google Meet
3. **Invite:** `airecruiterbot@gmail.com`
4. Save the meeting
5. Copy the Meet URL from calendar event
6. Run: `python meet_bot_joiner.py` and paste the URL

**Option C: Manual Admission (For Testing)**
1. Create any Google Meet
2. Run: `python meet_bot_joiner.py` with the URL
3. When bot asks to join, **manually admit it** from your host account
4. Bot will detect admission and join automatically

#### Test 2: Expected Output (Successful Join)

```
INFO:__main__:Attempting to join meeting: https://meet.google.com/xxx-xxxx-xxx
INFO:__main__:Meeting code: xxx-xxxx-xxx
INFO:__main__:Navigating to meeting URL...
INFO:__main__:Setting up pre-join configuration...
INFO:__main__:Ensuring camera is disabled...
INFO:__main__:Camera already disabled
INFO:__main__:Ensuring microphone is enabled...
INFO:__main__:Microphone already enabled
INFO:__main__:Pre-join configuration complete
INFO:__main__:Setting display name to: AI Interview Bot
INFO:__main__:Display name set to: AI Interview Bot
INFO:__main__:Clicking 'Join now' button...
INFO:__main__:✓ Found join button with selector: button:has-text("Join now")
INFO:__main__:Join button clicked successfully!
INFO:__main__:Waiting for meeting to load...
INFO:__main__:Waiting for meeting to fully load...
INFO:__main__:✓ Found meeting indicator: button[aria-label*="Turn off microphone"]
INFO:__main__:✅ Successfully joined the meeting!
INFO:__main__:🎉 Successfully joined meeting!
```

### ⚠️ Common Issues & Solutions

#### Issue 1: "You can't join this video call"

**Cause**: Meeting security requires host approval and bot isn't invited

**Solutions**:
1. **Invite the bot**: Add `airecruiterbot@gmail.com` to meeting invite
2. **Change settings**: Set meeting to "Anyone with link can join directly"
3. **Manual admit**: Host admits bot when it asks to join

**How to change meeting settings**:
- Click meeting link
- Click gear icon (Settings)
- Under "Quick access" → Select "Anyone with the link can join directly"

#### Issue 2: "Could not find join button"

**Cause**: Page not fully loaded or UI changed

**Solutions**:
1. Check the debug screenshot saved: `meet_join_debug_YYYYMMDD_HHMMSS.png`
2. Increase wait time before clicking join
3. Update selectors if Google Meet UI changed

#### Issue 3: "Timeout waiting for participants"

**Cause**: Candidate hasn't joined yet

**Solutions**:
- Increase timeout: `await joiner.wait_for_participants(min_participants=2, timeout=300)`
- Start the bot after candidate is already in meeting
- Skip participant wait for testing

### 📊 Current Test Status

| Test | Status | Notes |
|------|--------|-------|
| Authentication | ✅ PASSED | Session cached, no re-login needed |
| Navigate to Meet | ✅ PASSED | Successfully loads meeting URL |
| Pre-join Config | ✅ PASSED | Camera off, mic on working |
| Display Name | ✅ PASSED | Sets "AI Interview Bot" |
| Click Join Button | ✅ PASSED | Detects and clicks "Ask to join" |
| Meeting Security | ⚠️ BLOCKED | Requires host approval or invitation |
| In-Meeting Status | ⏳ PENDING | Needs successful join to test |

### 🎯 Next Steps

**For Testing Now:**
1. Create a test meeting with "Anyone with link" setting
2. Run `python meet_bot_joiner.py`
3. Verify bot joins successfully
4. Proceed to Step 1.3: Audio Integration

**For Production:**
1. When scheduling interviews, invite `airecruiterbot@gmail.com`
2. Or: Generate Meet links with "Quick access" enabled
3. Bot will join automatically without manual approval

### 🔐 Meeting Security Recommendations

**Development/Testing:**
- Use "Anyone with link can join" for faster testing
- Create dedicated test meetings

**Production:**
- Always invite `airecruiterbot@gmail.com` to meeting
- Or: Use "Anyone with link" but share link securely via email
- Enable meeting recording for compliance

### 📝 Integration Code Example

```python
import asyncio
from meet_bot_launcher import GoogleMeetAuth
from meet_bot_joiner import MeetBotJoiner
import os

async def join_interview_meeting(meeting_url: str):
    """Join a Google Meet interview."""
    
    # Authenticate
    auth = GoogleMeetAuth(
        email=os.getenv('MEET_BOT_EMAIL'),
        password=os.getenv('MEET_BOT_PASSWORD'),
        headless=False  # Set True for production
    )
    
    try:
        # Initialize and login
        await auth.initialize()
        success = await auth.login()
        
        if not success:
            print("Authentication failed")
            return None
        
        # Navigate to meeting
        await auth.navigate_to_meet(meeting_url)
        
        # Join meeting
        joiner = MeetBotJoiner(auth.get_page())
        join_success = await joiner.join_meeting(
            meeting_url=meeting_url,
            disable_camera=True,
            enable_microphone=True,
            bot_name="AI Interview Bot"
        )
        
        if not join_success:
            print("Failed to join meeting")
            return None
        
        # Wait for candidate
        print("Waiting for candidate to join...")
        await joiner.wait_for_participants(min_participants=2, timeout=300)
        
        # Return objects for further use
        return {
            'auth': auth,
            'joiner': joiner,
            'page': auth.get_page()
        }
        
    except Exception as e:
        print(f"Error: {e}")
        await auth.close()
        return None

# Usage
# meeting_url = "https://meet.google.com/xxx-xxxx-xxx"
# result = asyncio.run(join_interview_meeting(meeting_url))
```

---

**Status**: Step 1.2 Implementation Complete ✅  
**Next**: Step 1.3 - Audio Integration (Connect TTS and STT)
