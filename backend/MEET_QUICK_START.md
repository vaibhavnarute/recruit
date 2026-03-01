# 🚀 Quick Start Guide - Google Meet Interview System

## ⚡ 5-Minute Setup

### 1. Install Dependencies (2 minutes)
```bash
cd backend

# Install Python packages
pip install playwright fastapi uvicorn groq deepgram-sdk pymongo python-dotenv pydantic

# Install Playwright browser
python -m playwright install chromium
```

### 2. Configure Environment (1 minute)
Create `backend/.env`:
```bash
# Google Meet Bot
MEET_BOT_EMAIL=airecruiterbot@gmail.com
MEET_BOT_PASSWORD=qwhk mrxo zgja vnog

# Deepgram TTS
DEEPGRAM_API_KEY=120a5c4c0fa02f4478ffa6ed1aee18d6ea46de0e

# Groq LLM & STT
GROQ_API_KEY=your_groq_api_key_here

# MongoDB
MONGODB_URI=mongodb://localhost:27017/resumate
```

### 3. First-Time Authentication (1 minute)
```bash
python meet_bot_launcher.py

# Follow prompts:
# 1. Browser opens with Google login
# 2. Enter credentials (or use cached session)
# 3. Complete 2FA if prompted
# 4. Session saved to meet_bot_sessions/
```

### 4. Run Test Interview (30 seconds)
```bash
python test_complete_meet_interview.py

# Enter when prompted:
# - Candidate Name: Test User
# - Email: test@example.com
# - Job Title: Software Engineer

# Bot creates meeting, joins, and conducts interview!
```

---

## 🎯 API Usage Examples

### cURL
```bash
# Start Interview
curl -X POST http://localhost:8001/api/meet-interview/start \
  -H "Content-Type: application/json" \
  -d '{
    "interview_id": "int_001",
    "meet_url": "https://meet.google.com/abc-defg-hij",
    "candidate_name": "John Doe",
    "job_title": "Software Engineer",
    "headless": true
  }'

# Get Status
curl http://localhost:8001/api/meet-interview/status/int_001
```

### Python
```python
import requests

# Start Interview
response = requests.post(
    "http://localhost:8001/api/meet-interview/start",
    json={
        "interview_id": "int_001",
        "meet_url": "https://meet.google.com/abc-defg-hij",
        "candidate_name": "John Doe",
        "job_title": "Software Engineer",
        "headless": True
    }
)

results = response.json()
print(f"Overall Score: {results['data']['overall_score']}/10")
```

---

## 🔧 Troubleshooting

### Issue: "Bot can't join meeting"
**Solution:** Invite `airecruiterbot@gmail.com` to meeting OR enable "Quick Access" in Meet settings

### Issue: "Session expired"
**Solution:** Delete `meet_bot_sessions/` folder and re-run `python meet_bot_launcher.py`

### Issue: "No audio recorded"
**Solution:** Check candidate's microphone is enabled in Google Meet

---

## 📚 Documentation

- **Complete Guide:** `MEET_INTERVIEW_COMPLETE_GUIDE.md`
- **Architecture:** `ARCHITECTURE_DIAGRAM.md`
- **API Docs:** http://localhost:8001/docs

**Made with ❤️ by AI Recruiter Team**
