# Meet Bot - Quick Test Guide

## Prerequisites
✅ MongoDB Atlas running  
✅ `.env` file configured with credentials  
✅ Node.js installed (`node --version`)  
✅ Python dependencies installed (`pip install -r requirements.txt`)  
✅ WebSocket bridge dependencies (`pip install websockets`)

---

## Start Services (3 Terminals)

### Terminal 1: FastAPI Backend
```bash
cd backend
python main.py
```
**Expected:** `Uvicorn running on http://0.0.0.0:8001`

### Terminal 2: WebSocket Bridge
```bash
cd backend
python services/websocket_bridge.py
```
**Expected:** `WebSocket server started on ws://0.0.0.0:8765`

### Terminal 3: API Testing (keep open for commands)
```bash
cd backend
```

---

## Test Workflow

### 1. Start Recording Session
```powershell
# PowerShell
$body = @{
    meet_url = "https://meet.google.com/YOUR-MEETING-CODE"
    interview_id = "YOUR-INTERVIEW-ID-FROM-MONGODB"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8001/api/meet/start" -Method POST -ContentType "application/json" -Body $body
$response | ConvertTo-Json -Depth 10
```

**Expected Response:**
```json
{
    "success": true,
    "message": "Meet recording session started successfully",
    "data": {
        "session_id": "meet_session_20251022_183000_abc12345",
        "session_status": "initializing",
        "meet_url": "https://meet.google.com/...",
        "interview_id": "...",
        "started_at": "2025-10-22T18:30:00.123456"
    }
}
```

**Save session_id for next commands!**

---

### 2. Check Session Status
```powershell
# Replace <session_id> with actual value
Invoke-RestMethod -Uri "http://localhost:8001/api/meet/status/<session_id>" -Method GET | ConvertTo-Json -Depth 10
```

**Expected Response:**
```json
{
    "success": true,
    "data": {
        "session_id": "meet_session_20251022_183000_abc12345",
        "session_status": "recording",
        "meet_url": "https://meet.google.com/...",
        "started_at": "2025-10-22T18:30:00.123456",
        "joined_at": "2025-10-22T18:30:15.789012",
        "audio_chunks_received": 7,
        "join_attempts": 1
    }
}
```

**Status Progression:**
1. `initializing` → Bot starting up
2. `joining` → Planning join strategy
3. `joined` → Successfully joined meeting
4. `recording` → Capturing audio
5. `transcribing` → Processing audio
6. `completing` → Finalizing session
7. `completed` → Done!

---

### 3. Get Transcript
```powershell
Invoke-RestMethod -Uri "http://localhost:8001/api/meet/transcript/<session_id>" -Method GET | ConvertTo-Json -Depth 10
```

**Expected Response:**
```json
{
    "success": true,
    "data": {
        "session_id": "meet_session_20251022_183000_abc12345",
        "interview_id": "...",
        "full_transcript": "Candidate: Hello, I'm excited to...\nInterviewer: Tell me about...",
        "segments": [
            {
                "segment_number": 1,
                "text": "Hello, I'm excited to...",
                "speaker": "candidate",
                "timestamp": "2025-10-22T18:30:20.000000",
                "confidence": 0.95
            }
        ],
        "stats": {
            "total_segments": 10,
            "total_duration_seconds": 300,
            "average_confidence": 0.92
        }
    }
}
```

---

### 4. Stop Recording
```powershell
$stopBody = @{
    session_id = "<session_id>"
    reason = "Interview completed"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/meet/stop" -Method POST -ContentType "application/json" -Body $stopBody | ConvertTo-Json -Depth 10
```

---

## Monitor Logs

### Terminal 1 (main.py) - Watch For:
```
✅ "🚀 Starting Puppeteer bot process" (FIRST)
✅ "✅ Puppeteer bot process started (PID: ...)"
✅ "🤖 [Background] Starting Meet Bot agent"
✅ "✅ [Background] Meet Bot agent completed: completed"
❌ NO "Recursion limit" errors
❌ NO "Fatal error" messages
```

### Terminal 2 (websocket_bridge.py) - Watch For:
```
✅ "New client connected"
✅ "Received audio chunk"
✅ "Saved audio chunk to MongoDB"
✅ "Starting transcription for chunk"
✅ "Broadcasting transcript update"
```

---

## Expected Workflow Timeline

| Time | Event | Log Message |
|------|-------|-------------|
| T+0s | API Call | `🎤 Starting Meet recording session` |
| T+0s | Session Created | `✅ Created session: meet_session_...` |
| T+0s | Bot Launch | `🚀 Starting Puppeteer bot process` |
| T+0s | Bot Started | `✅ Puppeteer bot process started (PID: ...)` |
| T+2s | Agent Start | `🤖 [Background] Starting Meet Bot agent` |
| T+2s | Initialize | `Initializing session: meet_session_...` |
| T+3s | Plan Strategy | `Planning join strategy` |
| T+4s | Groq LLM Call | `Calling Groq LLM for join strategy` |
| T+5s | Strategy Set | `Join strategy planned: retry_with_wait` |
| T+5s | Monitoring | `Monitoring connection (status: joining)` |
| T+6s | Joined | `✅ Successfully joined meeting` |
| T+7s | Recording | `Handling audio stream (chunks: 1)` |
| T+15s | Progress | `📊 Processed 5 audio chunks` |
| T+25s | Limit Reached | `Chunk limit reached (10/10), completing session` |
| T+26s | Finalizing | `Finalizing session` |
| T+27s | Completed | `✅ [Background] Meet Bot agent completed: completed` |

---

## Troubleshooting

### Problem: "Recursion limit" error
**Solution:** Fixed in latest code! Update `meet_bot_agent.py`

### Problem: "Bot starts after agent fails"
**Solution:** Fixed in latest code! Update `main.py`

### Problem: "Session not found: <session_id>"
**Solution:** Use actual session_id from `/api/meet/start` response, not literal `<session_id>`

### Problem: Chrome doesn't open
**Check:**
1. `PUPPETEER_HEADLESS=false` in `.env`
2. Node.js installed: `node --version`
3. Puppeteer installed: `cd backend && npm install`
4. Bot credentials correct: `MEET_BOT_EMAIL` and `MEET_BOT_PASSWORD` in `.env`

### Problem: "Failed to join meeting"
**Check:**
1. Meeting URL valid and active
2. Bot account has 2FA enabled with App Password
3. Google account not locked
4. Network connection stable

### Problem: No transcripts
**Check:**
1. WebSocket bridge running on port 8765
2. Groq API key valid: `GROQ_API_KEY` in `.env`
3. Audio chunks in MongoDB: `db.meet_audio_chunks.find()`
4. WebSocket connected: Check Terminal 2 logs

---

## Success Criteria

✅ **Bot launches BEFORE agent starts**  
✅ **No "Recursion limit" errors**  
✅ **Session completes after 10 chunks**  
✅ **Final status: `completed`**  
✅ **Chrome window opens (if headless=false)**  
✅ **API returns in <3 seconds**  
✅ **All 3 terminals show activity**

---

## MongoDB Verification

### Check Sessions
```javascript
db.meet_sessions.find().sort({created_at: -1}).limit(1).pretty()
```

### Check Audio Chunks
```javascript
db.meet_audio_chunks.find({session_id: "YOUR_SESSION_ID"}).count()
```

### Check Transcripts
```javascript
db.meet_transcripts.find({session_id: "YOUR_SESSION_ID"}).pretty()
```

---

## Next Steps After Testing

1. **Real Meeting Test:** Join actual Google Meet with another account
2. **Audio Verification:** Check if audio chunks are captured
3. **Transcription Test:** Verify Groq Whisper transcription works
4. **Error Recovery:** Test with invalid credentials/URLs
5. **Production Config:** Set `PUPPETEER_HEADLESS=true` for servers

---

## Quick Commands Reference

```powershell
# Start recording
$response = Invoke-RestMethod -Uri "http://localhost:8001/api/meet/start" -Method POST -ContentType "application/json" -Body '{"meet_url":"https://meet.google.com/abc-defg-hij","interview_id":"123"}'

# Get status
Invoke-RestMethod -Uri "http://localhost:8001/api/meet/status/$($response.data.session_id)" -Method GET

# Get transcript
Invoke-RestMethod -Uri "http://localhost:8001/api/meet/transcript/$($response.data.session_id)" -Method GET

# Stop recording
Invoke-RestMethod -Uri "http://localhost:8001/api/meet/stop" -Method POST -ContentType "application/json" -Body "{\"session_id\":\"$($response.data.session_id)\"}"
```

---

## Production Checklist

Before deploying to production:

- [ ] Update chunk limit from 10 to unlimited (remove test condition)
- [ ] Set `PUPPETEER_HEADLESS=true`
- [ ] Configure proper MongoDB indexes
- [ ] Set up monitoring/alerting
- [ ] Test error recovery with retries
- [ ] Implement proper WebSocket reconnection
- [ ] Add rate limiting to API endpoints
- [ ] Configure CORS for frontend
- [ ] Set up log aggregation
- [ ] Test with multiple concurrent sessions

---

## Support

**Documentation:**
- `MEET_BOT_IMPROVEMENTS.md` - Detailed analysis of fixes
- `MEET_BOT_INTEGRATION.md` - Original integration guide
- `MEET_BOT_QUICK_REFERENCE.md` - This guide

**Log Locations:**
- FastAPI: Terminal 1 (stdout)
- WebSocket: Terminal 2 (stdout)
- Puppeteer: Subprocess (check `bot_process.stdout`)

**MongoDB Collections:**
- `meet_sessions` - Session metadata
- `meet_audio_chunks` - Raw audio data
- `meet_transcripts` - Transcribed text
