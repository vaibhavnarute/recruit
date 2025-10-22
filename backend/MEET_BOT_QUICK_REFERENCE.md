# 🚀 Google Meet Bot - Quick Reference

## ⚡ Quick Start (3 Steps)

### 1️⃣ Setup Environment
```powershell
cd backend
copy .env.template .env
# Edit .env with your credentials
npm install
pip install websockets
```

### 2️⃣ Start Services
```powershell
.\start_meet_bot.ps1
# OR manually:
# Terminal 1: python main.py
# Terminal 2: python services/websocket_bridge.py
```

### 3️⃣ Use API
```bash
curl -X POST http://localhost:8001/api/meet/start \
  -H "Content-Type: application/json" \
  -d '{"meet_url": "https://meet.google.com/abc-def-ghi", "interview_id": "int_001"}'
```

---

## 📡 API Endpoints Cheat Sheet

### Start Recording
```http
POST /api/meet/start
{
  "meet_url": "https://meet.google.com/abc-def-ghi",
  "interview_id": "interview_123",
  "max_retries": 3
}
```

### Stop Recording
```http
POST /api/meet/stop
{
  "session_id": "meet_session_xxx",
  "reason": "Interview completed"
}
```

### Get Status
```http
GET /api/meet/status/{session_id}
```

### Get Transcript
```http
GET /api/meet/transcript/{session_id}
```

### Get All Sessions for Interview
```http
GET /api/meet/sessions/interview/{interview_id}
```

---

## 🛠️ Required Environment Variables

```env
# Minimum required
GROQ_API_KEY=your_key_here
MONGODB_URI=mongodb://localhost:27017/
MEET_BOT_EMAIL=bot@gmail.com
MEET_BOT_PASSWORD=bot_password

# Optional (with defaults)
WEBSOCKET_PORT=8765
API_PORT=8001
```

---

## 🏗️ Architecture (3 Components)

```
1. FastAPI Backend (port 8001)
   └─ python main.py

2. WebSocket Bridge (port 8765)
   └─ python services/websocket_bridge.py

3. Puppeteer Bot (auto-started)
   └─ node services/meet_bot/meet_recorder.js
```

---

## 📝 File Locations

```
backend/
├── langgraph_agents/
│   ├── meet_bot_agent.py           # Session lifecycle
│   └── audio_transcription_agent.py # STT processing
├── services/
│   ├── websocket_bridge.py         # Real-time bridge
│   └── meet_bot/meet_recorder.js   # Puppeteer bot
├── repositories/
│   └── meet_session_repository.py  # MongoDB ops
└── main.py                         # FastAPI endpoints
```

---

## 🧪 Testing

```powershell
# Run all tests
python test_meet_bot_integration.py

# Test specific component
python langgraph_agents/meet_bot_agent.py
python langgraph_agents/audio_transcription_agent.py
python repositories/meet_session_repository.py
```

---

## 🐛 Troubleshooting Quick Fixes

### Bot Can't Login
```powershell
# 1. Disable 2FA on bot account
# 2. Use app-specific password
# 3. Enable "Less secure app access"
```

### WebSocket Connection Failed
```powershell
# Check if WebSocket Bridge is running
python services/websocket_bridge.py
# Check port 8765 is not blocked
```

### No Audio Chunks
```powershell
# Run bot in non-headless mode for debugging
# Edit meet_recorder.js: headless: false
```

### Transcription Failed
```powershell
# Verify Groq API key
python -c "from groq import Groq; print(Groq(api_key='your_key').models.list())"
```

### MongoDB Error
```powershell
# Check MongoDB is running
mongosh --eval "db.version()"
# Verify MONGODB_URI in .env
```

---

## 📊 Response Format (All Endpoints)

### Success Response
```json
{
  "success": true,
  "message": "...",
  "data": { ... }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description"
  }
}
```

**Note:** All endpoints return status 200 (errors in body).

---

## 🔥 Common Commands

```powershell
# Install dependencies
npm install
pip install websockets

# Start all services
.\start_meet_bot.ps1

# Start individual services
python main.py                      # FastAPI
python services/websocket_bridge.py # WebSocket
node services/meet_bot/meet_recorder.js # Puppeteer (manual)

# Run tests
python test_meet_bot_integration.py

# Check logs
# Logs appear in the terminal running each service

# Clean up test data
python -c "from repositories.meet_session_repository import MeetSessionRepository; repo = MeetSessionRepository(); repo.delete_session('session_id')"
```

---

## 📚 Documentation Files

- **Setup Guide:** `MEET_BOT_INTEGRATION_GUIDE.md` (full 983-line guide)
- **Implementation Summary:** `MEET_BOT_IMPLEMENTATION_COMPLETE.md`
- **This Quick Reference:** `MEET_BOT_QUICK_REFERENCE.md`
- **Environment Template:** `.env.template`

---

## ⚡ Performance Tips

1. **Limit Concurrent Sessions:** Max 5-10 recommended
2. **Use Headless Mode:** Set `PUPPETEER_HEADLESS=true` in production
3. **Enable Caching:** Transcriptions cached for 1 hour
4. **Monitor Resources:** Each session uses ~50-100MB RAM
5. **Clean Old Sessions:** Periodically delete old session data

---

## 🎯 Key Features

✅ Free & Open Source (no Recall.ai)  
✅ Real-time audio transcription (Groq Whisper)  
✅ LangGraph + MCP integration  
✅ MongoDB persistence  
✅ Comprehensive error handling  
✅ Anti-bot detection (stealth mode)  
✅ Session analytics  
✅ Production-ready  

---

## 📞 Need Help?

1. Check troubleshooting in `MEET_BOT_INTEGRATION_GUIDE.md`
2. Run integration tests
3. Review logs in all 3 processes
4. Check MongoDB for errors
5. Verify `.env` configuration

---

**Version:** 1.0.0  
**Last Updated:** January 22, 2025
