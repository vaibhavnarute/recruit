# Google Meet Bot - Setup & Authentication Guide

## 📋 Overview

This guide covers setting up the Google Meet bot authentication system. The bot uses Playwright to automate browser interactions with Google Meet.

## 🔐 Step 1: Setup Credentials

### 1.1 Create Environment File

Copy the example environment file:
```bash
copy .env.example .env
```

### 1.2 Add Google Credentials

Edit `.env` file and add your Google account credentials:

```env
GOOGLE_EMAIL=your-actual-email@gmail.com
GOOGLE_PASSWORD=your-actual-password
MEET_BOT_HEADLESS=false
```

⚠️ **Security Notes:**
- Never commit `.env` file to Git
- Use a dedicated Google account for the bot (not your personal account)
- Consider using App Passwords if you have 2FA enabled on your main account
- The `.env` file is already in `.gitignore`

### 1.3 Google Account Recommendations

**Option A: Create Dedicated Bot Account (Recommended)**
1. Create a new Google account specifically for the interview bot
2. Use a simple password (since it's dedicated for this purpose)
3. Disable 2FA for easier automation (or use App Password)
4. Name: "AI Interview Bot" or similar

**Option B: Use Existing Account with App Password**
1. Go to Google Account → Security → 2-Step Verification
2. Scroll to "App passwords"
3. Generate new app password
4. Use this app password instead of your regular password in `.env`

## 🧪 Step 2: Test Authentication

### 2.1 Install Dependencies

Ensure all Python packages are installed:
```bash
pip install playwright python-dotenv pydantic
playwright install chromium
```

### 2.2 Verify Configuration

Check if your credentials are properly configured:
```bash
python meet_bot_config.py
```

Expected output:
```
============================================================
GOOGLE MEET BOT CONFIGURATION
============================================================
Google Email:        your-email@gmail.com
Google Password:     ✓ SET
Headless Mode:       False
Browser Timeout:     30000ms
...
✅ Configuration is valid
============================================================
```

### 2.3 Run Authentication Test

Test the Google login flow:
```bash
python meet_bot_launcher.py
```

**What will happen:**
1. Browser window opens (visible, not headless)
2. Navigates to Google accounts login
3. Automatically enters email
4. Automatically enters password
5. If 2FA is required, you'll see a warning to complete it manually
6. Saves session for future use
7. Browser stays open for 30 seconds for inspection

**Expected Output:**
```
INFO:__main__:GoogleMeetAuth initialized for your-email@gmail.com
INFO:__main__:Initializing Playwright browser...
INFO:__main__:Browser initialized successfully
INFO:__main__:Starting Google authentication for your-email@gmail.com...
INFO:__main__:Navigating to Google accounts login...
INFO:__main__:Entering email...
INFO:__main__:Entering password...
INFO:__main__:Waiting for authentication to complete...
INFO:__main__:✅ Google authentication successful!
INFO:__main__:✅ Session saved to ./meet_bot_sessions/your-email_at_gmail.com/session.json
INFO:__main__:🎉 Authentication successful!
```

### 2.4 Troubleshooting Authentication

**Problem: "GOOGLE_EMAIL and GOOGLE_PASSWORD not set"**
- Solution: Make sure you created `.env` file and added credentials
- Check that `.env` is in the `backend/` directory
- Verify no typos in variable names

**Problem: "2FA or additional verification required"**
- The browser window will show verification prompt
- Complete verification manually (check phone, approve login, etc.)
- Script waits 60 seconds for you to complete this
- Once verified, session is saved for future use

**Problem: "Authentication failed - not logged in"**
- Check your email/password are correct in `.env`
- Try logging in manually first in a regular browser
- Google may block automated logins - see "Security Settings" below

**Problem: Browser immediately closes**
- This is normal if there's an error
- Check the console output for error messages
- Set `MEET_BOT_HEADLESS=false` to keep browser visible

## 🔒 Step 3: Google Account Security Settings

### 3.1 Allow Less Secure Apps (if needed)

If Google blocks automated login:

1. Go to: https://myaccount.google.com/security
2. Scroll to "Less secure app access"
3. Turn ON (only for dedicated bot account, NOT your personal account)

### 3.2 Disable 2-Step Verification (Optional)

For smoother automation (dedicated bot account only):

1. Go to: https://myaccount.google.com/security
2. Click "2-Step Verification"
3. Click "Turn off"

⚠️ **Only do this for dedicated bot accounts, never your personal account!**

## 📁 Step 4: Session Management

### 4.1 Session Storage

After first successful login, session is saved:
```
meet_bot_sessions/
└── your-email_at_gmail.com/
    ├── session.json         # Browser cookies and tokens
    └── metadata.json        # Session metadata
```

### 4.2 Session Benefits

- **No repeated logins**: Session lasts 7 days
- **Faster startup**: Skip login flow on subsequent runs
- **Multiple accounts**: Each email gets own session directory

### 4.3 Clear Session (if needed)

To force fresh login:
```bash
# Delete session folder
rmdir /s meet_bot_sessions\your-email_at_gmail.com
```

Or pass `force_reauth=True` in code:
```python
success = await auth.login(force_reauth=True)
```

## 🔄 Step 5: Integration with Interview System

### 5.1 Basic Usage Example

```python
import asyncio
from meet_bot_launcher import GoogleMeetAuth

async def run_interview():
    # Initialize authentication
    auth = GoogleMeetAuth(
        email=os.getenv('GOOGLE_EMAIL'),
        password=os.getenv('GOOGLE_PASSWORD'),
        headless=False  # Set True for production
    )
    
    try:
        # Initialize browser
        await auth.initialize()
        
        # Login to Google (uses cached session if available)
        success = await auth.login()
        
        if not success:
            print("Failed to authenticate")
            return
        
        # Navigate to Meet call
        meeting_url = "https://meet.google.com/xxx-xxxx-xxx"
        await auth.navigate_to_meet(meeting_url)
        
        # Get page for further automation
        page = auth.get_page()
        
        # TODO: Join meeting, conduct interview
        
    finally:
        await auth.close()

# Run
asyncio.run(run_interview())
```

### 5.2 Next Steps

Once authentication is working, we'll implement:
- **Step 1.2**: Auto-join meeting functionality
- **Step 1.3**: Audio integration (TTS playback + recording)
- **Step 1.4**: Interview flow orchestration
- **Step 1.5**: End-to-end testing

## ✅ Verification Checklist

Before proceeding to next step:

- [ ] `.env` file created with valid credentials
- [ ] `python meet_bot_config.py` shows "✅ Configuration is valid"
- [ ] `python meet_bot_launcher.py` completes successfully
- [ ] Session saved in `meet_bot_sessions/` directory
- [ ] Browser opens and logs into Google account
- [ ] Second run uses cached session (faster)

## 🆘 Common Issues

### Issue: "Module not found: playwright"
```bash
pip install playwright
playwright install chromium
```

### Issue: "Module not found: dotenv"
```bash
pip install python-dotenv
```

### Issue: Google blocks login
- Use App Password instead of regular password
- Disable "Less secure app access" restriction
- Try from a different IP/location
- Use dedicated bot account instead of personal

### Issue: Session expired
- Sessions expire after 7 days
- Delete session folder to force re-authentication
- Or let code auto-detect and re-authenticate

## 📞 Support

If you encounter issues:
1. Check console output for error messages
2. Review this guide's troubleshooting section
3. Verify `.env` configuration
4. Try manual Google login in regular browser first
5. Check Google account security settings

---

**Status**: Step 1.1 Complete ✅  
**Next**: Step 1.2 - Meeting Join & Setup
