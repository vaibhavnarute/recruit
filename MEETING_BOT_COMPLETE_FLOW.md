# Meeting Bot System - Complete Flow Documentation

## 🤖 Overview

The Meeting Bot is an AI-powered system that automatically joins Google Meet/Zoom meetings, conducts interviews, and records/transcribes conversations.

---

## 📋 System Architecture

```
User → Frontend UI → Backend API → Meeting Bot Agent → Google Meet
                                         ↓
                                  Puppeteer Bot
                                         ↓
                                  STT (Speech-to-Text)
                                         ↓
                                  LLM (Interview AI)
                                         ↓
                                  TTS (Text-to-Speech)
```

---

## 🔄 Complete Flow: How Bot Joins & Conducts Interview

### Step 1: User Assigns Meeting (Frontend)

**Location**: `talentstream-hr/src/pages/AssignInterviews.tsx` or `talentstream-hr/src/components/MeetingBotControl.tsx`

**User Actions**:
1. Navigates to "Assign Interviews" or "Meeting Bot" page
2. Selects a candidate from batch
3. Enters/generates Google Meet link
4. Assigns interview details:
   - Interview ID
   - Meeting link (e.g., `https://meet.google.com/abc-defg-hij`)
   - Interview type (Technical/Behavioral)
   - Duration

**Frontend Code**:
```typescript
// In MeetingBotControl.tsx
const handleStartBot = async () => {
  const result = await meetBotApi.startBot({
    meeting_link: "https://meet.google.com/abc-defg-hij",
    interview_id: "INT_12345",
    bot_name: "AI Interview Assistant",
    auto_transcribe: true,
    auto_tts: true,
    auto_record: true,
  });
};
```

**API Call**: 
```
POST http://localhost:8001/api/meet/start
```

---

### Step 2: Backend Receives Request (FastAPI)

**Location**: `backend/main.py` (Line 3028)

**Endpoint**: `POST /api/meet/start`

**What Happens**:
1. Receives meeting details from frontend
2. Validates credentials (bot email/password)
3. Generates unique `session_id`
4. Creates session record in MongoDB

**Code Flow**:
```python
@app.post("/api/meet/start")
async def start_meet_recording(request: MeetSessionRequest):
    # 1. Generate session ID
    session_id = f"meet_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4()[:8]}"
    
    # 2. Get bot credentials
    bot_email = os.getenv("MEET_BOT_EMAIL")
    bot_password = os.getenv("MEET_BOT_PASSWORD")
    
    # 3. Create session in database
    session_doc = meet_session_repo.create_session({
        "session_id": session_id,
        "interview_id": request.interview_id,
        "meet_url": request.meet_url,
        "bot_email": bot_email,
        "status": "joining"
    })
    
    # 4. Start Puppeteer bot process
    # 5. Start LangGraph orchestration
    # 6. Return session ID to frontend
```

**Database Collections Used**:
- `meet_sessions` - Stores session metadata
- `meet_transcripts` - Stores conversation transcript
- `meet_audio_chunks` - Stores audio recordings

---

### Step 3: Puppeteer Bot Joins Meeting

**Location**: `backend/services/meet_bot/meet_recorder.js` (Node.js)

**What Happens**:
1. Launches headless Chrome browser using Puppeteer
2. Navigates to Google Meet link
3. Logs in with bot credentials (email/password)
4. Handles permissions (microphone, camera)
5. Joins the meeting
6. Starts recording audio

**Technical Details**:
```javascript
// Simplified flow from meet_recorder.js
const puppeteer = require('puppeteer');

async function joinMeeting(meetUrl, botEmail, botPassword) {
  // 1. Launch browser
  const browser = await puppeteer.launch({
    headless: false, // Set to true for production
    args: [
      '--use-fake-ui-for-media-stream', // Auto-accept mic/camera
      '--disable-blink-features=AutomationControlled'
    ]
  });
  
  const page = await browser.newPage();
  
  // 2. Navigate to Google Meet
  await page.goto(meetUrl);
  
  // 3. Login (if not already logged in)
  await page.type('#identifierId', botEmail);
  await page.click('#identifierNext');
  await page.waitForTimeout(2000);
  await page.type('input[type="password"]', botPassword);
  await page.click('#passwordNext');
  
  // 4. Join meeting
  await page.waitForSelector('[data-meeting-code]');
  await page.click('button[jsname="Qx7Oae"]'); // Join button
  
  // 5. Start capturing audio
  const mediaRecorder = await startAudioCapture(page);
  
  return { browser, page, mediaRecorder };
}
```

**Google Meet Authentication**:
- Requires Google account credentials
- Stored in `backend/.env`:
  ```
  MEET_BOT_EMAIL=your-bot-email@gmail.com
  MEET_BOT_PASSWORD=your-bot-password
  ```

---

### Step 4: LangGraph Agent Orchestrates Interview

**Location**: `backend/langgraph_agents/meeting_bot_agent.py`

**What Happens**:
1. Initializes bot state
2. Monitors meeting status
3. Coordinates STT, LLM, and TTS agents
4. Manages conversation flow

**State Management**:
```python
class MeetingBotState(TypedDict):
    bot_id: str
    session_id: str
    meeting_link: str
    bot_status: str  # pending, joining, joined, active, leaving
    interview_id: str
    participant_count: int
    stt_enabled: bool
    tts_enabled: bool
    recording_enabled: bool
```

**LangGraph Workflow**:
```
┌─────────────┐
│ Initialize  │
│   Bot       │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Join       │
│  Meeting    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Monitor    │
│  Audio      │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    STT      │────▶│     LLM     │────▶│     TTS     │
│  (Groq)     │     │  (Question) │     │ (ElevenLabs)│
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Save to MongoDB │
                  └─────────────────┘
```

---

### Step 5: Real-time Interview Conversation

#### 5.1 Candidate Speaks
1. **Audio Capture**: Puppeteer captures audio stream
2. **STT Processing**: Audio sent to Groq Whisper API
3. **Transcript**: Text saved to `meet_transcripts` collection

```python
# STT Agent processes audio
transcript = await stt_agent.transcribe(audio_chunk)
# Output: "I have 5 years of Python experience..."

# Save to database
meet_session_repo.add_transcript(session_id, {
    "speaker": "candidate",
    "text": transcript,
    "timestamp": datetime.now()
})
```

#### 5.2 AI Generates Response
1. **LLM Processing**: Groq LLM analyzes transcript
2. **Context**: Uses interview type, candidate resume, previous answers
3. **Response Generation**: Creates follow-up question or feedback

```python
# LLM generates next question
llm_response = await llm_agent.generate_response({
    "transcript": transcript,
    "interview_type": "technical",
    "question_history": previous_questions
})
# Output: "That's great! Can you explain the difference between..."
```

#### 5.3 Bot Speaks (TTS)
1. **TTS Generation**: ElevenLabs converts text to speech
2. **Audio Playback**: Puppeteer plays audio in meeting
3. **Transcript Update**: Bot's response saved to database

```python
# TTS converts text to audio
audio_file = await tts_agent.synthesize(llm_response)

# Play audio in meeting
await puppeteer_bot.play_audio(audio_file)

# Save bot's response
meet_session_repo.add_transcript(session_id, {
    "speaker": "bot",
    "text": llm_response,
    "timestamp": datetime.now()
})
```

---

### Step 6: Frontend Gets Live Updates

**WebSocket Connection**: `ws://localhost:8001/api/dashboard/ws`

**Real-time Updates**:
- Session status changes
- Transcript segments
- Participant count
- Audio quality metrics

**Frontend Code**:
```typescript
// In MeetingBotControl.tsx
useEffect(() => {
  const interval = setInterval(async () => {
    // Poll for status
    const statusResult = await meetBotApi.getStatus(sessionId);
    setStatus(statusResult);
    
    // Get transcript
    const transcriptResult = await meetBotApi.getTranscript(sessionId);
    setTranscript(transcriptResult.data.segments);
  }, 3000); // Poll every 3 seconds
}, [sessionId]);
```

**UI Display**:
- Status badge: "JOINING" → "ACTIVE" → "COMPLETED"
- Live transcript with speaker labels
- Participant list
- Duration counter

---

### Step 7: Interview Completion

**Auto-completion Triggers**:
1. Scheduled duration reached (e.g., 30 minutes)
2. Silence detected for 5+ minutes
3. User manually clicks "Stop Bot"
4. All participants leave meeting

**Completion Flow**:
```python
# 1. Stop audio recording
puppeteer_bot.stop_recording()

# 2. Leave meeting
await puppeteer_bot.leave_meeting()

# 3. Close browser
browser.close()

# 4. Update session status
meet_session_repo.update_session(session_id, {
    "status": "completed",
    "leave_time": datetime.now(),
    "duration_minutes": calculate_duration()
})

# 5. Trigger analytics
analytics_service.analyze_interview(interview_id)
```

---

## 📊 Data Flow & Storage

### MongoDB Collections

#### 1. `meet_sessions`
```json
{
  "_id": "ObjectId(...)",
  "session_id": "meet_session_20260201_153045_a1b2c3d4",
  "interview_id": "INT_12345",
  "meet_url": "https://meet.google.com/abc-defg-hij",
  "bot_email": "bot@example.com",
  "status": "active",
  "join_time": "2026-02-01T15:30:45Z",
  "leave_time": null,
  "duration_minutes": 0,
  "participant_count": 2,
  "metadata": {
    "bot_name": "AI Interview Assistant",
    "auto_transcribe": true,
    "auto_tts": true
  }
}
```

#### 2. `meet_transcripts`
```json
{
  "_id": "ObjectId(...)",
  "session_id": "meet_session_20260201_153045_a1b2c3d4",
  "segments": [
    {
      "speaker": "bot",
      "text": "Hello! Tell me about yourself.",
      "timestamp": "2026-02-01T15:31:00Z",
      "confidence": 0.98
    },
    {
      "speaker": "candidate",
      "text": "I have 5 years of Python experience...",
      "timestamp": "2026-02-01T15:31:15Z",
      "confidence": 0.95
    }
  ]
}
```

#### 3. `meet_audio_chunks`
```json
{
  "_id": "ObjectId(...)",
  "session_id": "meet_session_20260201_153045_a1b2c3d4",
  "chunk_number": 1,
  "audio_data": "base64_encoded_audio...",
  "duration_seconds": 30,
  "timestamp": "2026-02-01T15:31:00Z"
}
```

---

## 🔐 Security & Credentials

### Required Credentials

**1. Google Meet Bot Account**
```bash
# In backend/.env
MEET_BOT_EMAIL=your-bot-email@gmail.com
MEET_BOT_PASSWORD=your-bot-password
```

**2. API Keys**
```bash
# Speech-to-Text (Groq)
GROQ_API_KEY=gsk_...

# Text-to-Speech (ElevenLabs)
ELEVENLABS_API_KEY=sk_...
```

### Best Practices
- ✅ Use dedicated Google account for bot
- ✅ Enable "Less secure app access" in Google account
- ✅ Use strong passwords
- ✅ Store credentials in `.env` (never commit to Git)
- ✅ Rotate credentials regularly

---

## 🧪 Testing the Bot

### Manual Test Flow

**1. Start Backend**
```powershell
cd backend
python main.py
```

**2. Start Frontend**
```powershell
cd talentstream-hr
npm run dev
```

**3. Navigate to Meeting Bot Page**
```
http://localhost:8080/meeting-bot
```

**4. Enter Test Data**
- Meeting Link: Create a test Google Meet (https://meet.google.com)
- Interview ID: `test_interview_001`
- Click "Start Bot"

**5. Observe**
- Browser window opens (if headless=false)
- Bot joins meeting
- Status badge: "JOINING" → "ACTIVE"
- Transcript appears in real-time

**6. Test Conversation**
- Speak in the meeting
- Bot should transcribe and respond
- Check transcript updates

**7. Stop Bot**
- Click "Stop Bot" button
- Verify session marked as "completed"

---

## 🔍 Monitoring & Debugging

### Backend Logs
```powershell
# Watch backend terminal for:
INFO:__main__:🎤 Starting Meet recording session
INFO:__main__:   Meet URL: https://meet.google.com/...
INFO:__main__:✅ Session created: meet_session_...
INFO:__main__:🚀 Starting Puppeteer bot process
INFO:__main__:✅ BOT JOINED MEETING SUCCESSFULLY
```

### Frontend Console
```javascript
// Open browser console (F12)
// Watch for:
📡 Dashboard WebSocket connected
🎤 Bot status: ACTIVE
📝 Transcript updated: 15 segments
```

### MongoDB Queries
```javascript
// Check session status
db.meet_sessions.find({status: "active"})

// View transcript
db.meet_transcripts.findOne({session_id: "meet_session_..."})

// Count audio chunks
db.meet_audio_chunks.countDocuments({session_id: "meet_session_..."})
```

---

## 📈 Analytics After Interview

After bot completes interview, trigger analytics:

**1. Navigate to Analytics Page**
```
http://localhost:8080/analytics
```

**2. Enter Interview ID**
```
INT_12345
```

**3. View Report**
- Overall score (0-100)
- Technical skills assessment
- Communication evaluation
- Hiring recommendation
- Strengths/weaknesses

**4. Export PDF**
- Click "Export PDF"
- Download comprehensive report

---

## 🛠️ Troubleshooting

### Issue: Bot Can't Join Meeting

**Check**:
1. Google account credentials correct?
2. "Less secure app access" enabled?
3. Meeting link valid and accessible?
4. Firewall blocking Puppeteer?

**Solution**:
```bash
# Test credentials manually
# Try logging in to meet.google.com with bot account
```

### Issue: No Audio Transcription

**Check**:
1. Groq API key valid?
2. Microphone permissions granted?
3. Audio capture working in Puppeteer?

**Solution**:
```bash
# Check backend logs for STT errors
# Verify GROQ_API_KEY in .env
```

### Issue: Bot Not Responding

**Check**:
1. LLM API working?
2. TTS API key valid?
3. Audio playback enabled in meeting?

**Solution**:
```bash
# Test TTS independently
# Check ElevenLabs API quota
```

---

## 🚀 Production Deployment

### Recommendations

**1. Use Headless Mode**
```javascript
// In meet_recorder.js
const browser = await puppeteer.launch({
  headless: true, // No UI
  args: ['--no-sandbox', '--disable-setuid-sandbox']
});
```

**2. Scale with Workers**
- Run multiple bot instances
- Use queue system (Redis/RabbitMQ)
- Load balance across servers

**3. Add Monitoring**
- Track bot success rate
- Monitor API usage
- Alert on failures

**4. Optimize Performance**
- Cache common responses
- Compress audio chunks
- Use CDN for audio files

---

## 📚 Key Files Reference

| File | Purpose |
|------|---------|
| `backend/main.py` (Line 3028) | `/api/meet/start` endpoint |
| `backend/langgraph_agents/meeting_bot_agent.py` | Bot orchestration logic |
| `backend/services/meet_bot/meet_recorder.js` | Puppeteer automation |
| `backend/repositories/meet_session_repository.py` | Database operations |
| `talentstream-hr/src/components/MeetingBotControl.tsx` | Frontend UI |
| `talentstream-hr/src/services/meetBotApi.ts` | API client |

---

## ✅ Summary

**Complete Flow**:
1. 👤 User assigns meeting → Frontend sends request
2. 🔧 Backend creates session → Generates session_id
3. 🤖 Puppeteer joins meeting → Chrome automation
4. 🎙️ STT transcribes speech → Groq Whisper
5. 🧠 LLM generates responses → Groq LLaMA
6. 🔊 TTS speaks responses → ElevenLabs
7. 💾 All data saved to MongoDB → Real-time storage
8. 📊 Analytics generated → Comprehensive report

**Result**: Fully automated AI interview with human-like conversation!

---

**Last Updated**: February 1, 2026  
**Version**: 1.0.0  
**Status**: Production Ready ✅
