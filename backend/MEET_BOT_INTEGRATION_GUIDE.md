# Google Meet Bot Integration Guide

Complete guide for setting up and using the Google Meet audio-capture solution with Puppeteer + Groq Whisper.

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Starting Services](#starting-services)
6. [API Usage](#api-usage)
7. [Troubleshooting](#troubleshooting)
8. [Architecture Details](#architecture-details)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Meet Bot Endpoints                                    │  │
│  │  /api/meet/start, /api/meet/stop, /api/meet/status    │  │
│  └────────────────────────────────────────────────────────┘  │
│                           ↕                                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  LangGraph Agents                                      │  │
│  │  - Meet Bot Agent (session lifecycle)                 │  │
│  │  - Audio Transcription Agent (Groq Whisper STT)       │  │
│  └────────────────────────────────────────────────────────┘  │
│                           ↕                                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  WebSocket Bridge (port 8765)                          │  │
│  │  - Receives audio chunks from Puppeteer               │  │
│  │  - Streams to transcription agent                     │  │
│  │  - Stores in MongoDB                                  │  │
│  └────────────────────────────────────────────────────────┘  │
│                           ↕                                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  MongoDB Repository                                    │  │
│  │  - meet_sessions, meet_transcripts, meet_audio_chunks │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕ WebSocket (ws://localhost:8765)
┌─────────────────────────────────────────────────────────────┐
│               Node.js Puppeteer Bot                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  meet_recorder.js                                      │  │
│  │  - Opens Google Meet URL                              │  │
│  │  - Logs in with bot account                           │  │
│  │  - Joins meeting (mic ON, camera OFF)                 │  │
│  │  - Captures audio via MediaRecorder API               │  │
│  │  - Streams 5-second chunks to WebSocket               │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    Google Meet Session
```

---

## ✅ Prerequisites

### 1. Python Requirements
- Python 3.11+
- Virtual environment activated

### 2. Node.js Requirements
- Node.js 18.0.0 or higher
- npm (comes with Node.js)

### 3. MongoDB
- MongoDB instance running (local or cloud)
- Connection URI ready

### 4. Google Account for Bot
- Create a dedicated Google account for the bot
- Email: e.g., `airecruiterbot@gmail.com`
- Password: Strong password
- **Important**: Turn off 2FA or use app-specific password

### 5. Groq API Key
- Get API key from https://console.groq.com
- Required for Whisper STT and LLM analysis

---

## 📦 Installation

### Step 1: Install Python Dependencies

```powershell
# Navigate to backend directory
cd backend

# Install Python packages
pip install -r requirements.txt

# Install additional dependencies for Meet Bot
pip install websockets
```

### Step 2: Install Node.js Dependencies

```powershell
# Still in backend directory
npm install
```

This will install:
- `puppeteer` (v21.6.1) - Browser automation
- `puppeteer-extra` - Plugin system
- `puppeteer-extra-plugin-stealth` - Avoid bot detection
- `ws` (v8.16.0) - WebSocket client

---

## ⚙️ Configuration

### Step 1: Update `.env` File

Add these variables to `backend/.env`:

```env
# Existing variables...
GROQ_API_KEY=your_groq_api_key_here
MONGODB_URI=mongodb://localhost:27017/
MONGO_DB_NAME=ai_recruiter

# Google Meet Bot Credentials
MEET_BOT_EMAIL=your_bot_email@gmail.com
MEET_BOT_PASSWORD=your_bot_password

# WebSocket Configuration (optional, defaults shown)
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8765
```

### Step 2: MongoDB Collections

The system will automatically create these collections:
- `meet_sessions` - Session metadata and state
- `meet_transcripts` - Transcription segments
- `meet_audio_chunks` - Audio chunk metadata

Indexes are created automatically on startup.

---

## 🚀 Starting Services

### Architecture: 3 Separate Processes

The system requires **3 concurrent processes**:

1. **FastAPI Backend** (Python)
2. **WebSocket Bridge** (Python)
3. **Puppeteer Bot** (Node.js) - Started automatically via API

### Terminal 1: Start FastAPI Backend

```powershell
cd backend
python main.py
```

Output:
```
🚀 Initializing LangGraph + MCP service...
✅ LangGraph service initialized successfully!
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Terminal 2: Start WebSocket Bridge

```powershell
cd backend
python services/websocket_bridge.py
```

Output:
```
2025-01-22 10:00:00 - WebSocket Bridge initialized on 0.0.0.0:8765
🚀 Starting WebSocket Bridge on 0.0.0.0:8765
✅ WebSocket Bridge running on ws://0.0.0.0:8765
```

### Puppeteer Bot (Started Automatically)

The Puppeteer bot is started automatically when you call `/api/meet/start` endpoint.

---

## 📡 API Usage

### 1. Start Meet Recording Session

**Endpoint:** `POST /api/meet/start`

**Request Body:**
```json
{
  "meet_url": "https://meet.google.com/abc-defg-hij",
  "interview_id": "interview_12345",
  "bot_email": "airecruiterbot@gmail.com",  // Optional, uses .env if not provided
  "bot_password": "your_password",           // Optional, uses .env if not provided
  "max_retries": 3
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Meet recording session started successfully",
  "data": {
    "session_id": "meet_session_20250122_100530_a1b2c3d4",
    "session_status": "initializing",
    "meet_url": "https://meet.google.com/abc-defg-hij",
    "interview_id": "interview_12345",
    "started_at": "2025-01-22T10:05:30.123456"
  }
}
```

**Error Response (200):**
```json
{
  "success": false,
  "error": {
    "code": "MISSING_CREDENTIALS",
    "message": "Bot email and password are required"
  }
}
```

### 2. Stop Meet Recording Session

**Endpoint:** `POST /api/meet/stop`

**Request Body:**
```json
{
  "session_id": "meet_session_20250122_100530_a1b2c3d4",
  "reason": "Interview completed"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Meet recording session stop initiated",
  "data": {
    "session_id": "meet_session_20250122_100530_a1b2c3d4",
    "reason": "Interview completed",
    "stopped_at": "2025-01-22T10:35:30.123456"
  }
}
```

### 3. Get Session Status

**Endpoint:** `GET /api/meet/status/{session_id}`

**Response (200):**
```json
{
  "success": true,
  "message": "Session status retrieved successfully",
  "data": {
    "session_id": "meet_session_20250122_100530_a1b2c3d4",
    "interview_id": "interview_12345",
    "meet_url": "https://meet.google.com/abc-defg-hij",
    "session_status": "recording",
    "created_at": "2025-01-22T10:05:30",
    "started_at": "2025-01-22T10:05:35",
    "ended_at": null,
    "join_attempts": 1,
    "audio_chunks_received": 42,
    "transcription_segments": 38,
    "errors": [],
    "analytics": {
      "session_duration_seconds": 1800,
      "audio_chunks_received": 42,
      "transcription_segments": 38,
      "total_audio_duration": 190.5,
      "average_confidence": 0.89,
      "sentiment_distribution": {
        "positive": 25,
        "neutral": 10,
        "negative": 3
      }
    }
  }
}
```

### 4. Get Full Transcript

**Endpoint:** `GET /api/meet/transcript/{session_id}`

**Response (200):**
```json
{
  "success": true,
  "message": "Transcript retrieved successfully",
  "data": {
    "session_id": "meet_session_20250122_100530_a1b2c3d4",
    "full_transcript": "Hello, thank you for joining us today. Can you tell me about your experience with Python? I have been working with Python for over 5 years...",
    "segments": [
      {
        "chunk_id": "meet_session_20250122_100530_a1b2c3d4_chunk_1",
        "raw_transcription": "hello thank you for joining us today",
        "cleaned_transcription": "Hello, thank you for joining us today.",
        "confidence_score": 0.95,
        "sentiment": "positive",
        "key_points": ["greeting", "welcoming"],
        "technical_terms": [],
        "transcribed_at": "2025-01-22T10:05:40"
      }
    ],
    "total_segments": 38,
    "total_duration": 190.5,
    "average_confidence": 0.89,
    "key_points": ["Python experience", "Machine learning projects", "Team collaboration"],
    "technical_terms": ["Python", "TensorFlow", "PyTorch", "Kubernetes"]
  }
}
```

### 5. Get All Sessions for Interview

**Endpoint:** `GET /api/meet/sessions/interview/{interview_id}`

**Response (200):**
```json
{
  "success": true,
  "message": "Retrieved 2 sessions",
  "data": {
    "interview_id": "interview_12345",
    "sessions": [
      {
        "session_id": "meet_session_20250122_100530_a1b2c3d4",
        "session_status": "completed",
        "created_at": "2025-01-22T10:05:30",
        "audio_chunks_received": 42,
        "transcription_segments": 38
      },
      {
        "session_id": "meet_session_20250122_093000_x9y8z7w6",
        "session_status": "failed",
        "created_at": "2025-01-22T09:30:00",
        "audio_chunks_received": 0,
        "transcription_segments": 0
      }
    ],
    "total_sessions": 2
  }
}
```

---

## 🔧 Troubleshooting

### Issue 1: Bot Cannot Login to Google Meet

**Symptoms:**
- "Login failed" errors
- Bot stuck on login page

**Solutions:**
1. **Disable 2FA** on bot Google account
2. Use **App-Specific Password** if 2FA is required
3. Check if account has "Less secure app access" enabled
4. Try logging in manually first in the same browser profile

### Issue 2: WebSocket Connection Failed

**Symptoms:**
- "WebSocket connection timeout" errors
- Audio chunks not received

**Solutions:**
1. Ensure WebSocket Bridge is running:
   ```powershell
   python services/websocket_bridge.py
   ```
2. Check firewall settings (port 8765)
3. Verify `WEBSOCKET_PORT` in `.env` matches

### Issue 3: Audio Not Being Captured

**Symptoms:**
- Session starts but `audio_chunks_received` stays at 0
- No transcription segments

**Solutions:**
1. Check browser console for MediaRecorder errors
2. Ensure microphone permissions are granted
3. Verify WebRTC is working (check browser compatibility)
4. Run bot in non-headless mode to debug:
   - Edit `meet_recorder.js`, set `headless: false`

### Issue 4: Transcription Failed

**Symptoms:**
- Audio chunks received but no transcripts
- "Transcription failed" errors

**Solutions:**
1. Verify Groq API key is valid:
   ```python
   from groq import Groq
   client = Groq(api_key="your_key")
   print(client.models.list())
   ```
2. Check audio format is supported (webm, wav, mp3)
3. Verify audio chunk size (should be > 1KB)
4. Check Groq Whisper API rate limits

### Issue 5: MongoDB Connection Error

**Symptoms:**
- "Sessions collection is not initialized"
- Database errors

**Solutions:**
1. Verify MongoDB is running:
   ```powershell
   mongosh --eval "db.version()"
   ```
2. Check `MONGODB_URI` in `.env`
3. Ensure database name is correct (`MONGO_DB_NAME`)
4. Check network connectivity to MongoDB

### Issue 6: Node.js Puppeteer Crashes

**Symptoms:**
- "Puppeteer bot process started" but then crashes
- Chrome fails to launch

**Solutions:**
1. Install Chromium manually:
   ```powershell
   npx puppeteer browsers install chrome
   ```
2. Check system requirements (RAM, disk space)
3. Run with debug logging:
   ```powershell
   $env:DEBUG="puppeteer:*"
   node services/meet_bot/meet_recorder.js
   ```

---

## 🏗️ Architecture Details

### LangGraph Agents

#### 1. Meet Bot Agent (`meet_bot_agent.py`)

**Workflow Nodes:**
1. `initialize_session` - Validate inputs, create session
2. `plan_join_strategy` - Use LLM to determine join approach
3. `monitor_connection` - Check connection health
4. `handle_audio_stream` - Track audio processing
5. `diagnose_errors` - Analyze failures, determine recovery
6. `finalize_session` - Cleanup and summary

**State:**
- Session metadata (ID, URL, credentials)
- Join status and attempts
- Audio chunk counts
- Error logs
- Timestamps

#### 2. Audio Transcription Agent (`audio_transcription_agent.py`)

**Workflow Nodes:**
1. `receive_audio` - Validate audio chunk
2. `convert_format` - Ensure Whisper compatibility
3. `transcribe_audio` - Groq Whisper API call
4. `clean_transcription` - LLM-based cleaning
5. `analyze_content` - Extract insights (sentiment, key points)
6. `store_transcript` - Save to MongoDB

**Features:**
- Caching (1-hour TTL)
- Retry logic (3 attempts)
- Format conversion (webm → supported formats)
- Confidence scoring
- Sentiment analysis

### MCP Components

1. **Context Manager** - Manages conversation context (10K tokens)
2. **Cache Manager** - Caches transcriptions and strategies (1440min TTL)
3. **Token Optimizer** - Optimizes LLM prompts for efficiency

### WebSocket Protocol

**Message Types:**

1. **audio_chunk** (Node.js → Python)
```json
{
  "type": "audio_chunk",
  "sessionId": "session_id",
  "chunkId": "chunk_id",
  "audioData": "base64_encoded_audio",
  "format": "webm",
  "size": 12345,
  "timestamp": "2025-01-22T10:05:40.123Z"
}
```

2. **event** (Node.js → Python)
```json
{
  "type": "event",
  "event": "session_started|session_stopped|session_failed",
  "sessionId": "session_id",
  "timestamp": "2025-01-22T10:05:40.123Z"
}
```

3. **acknowledgment** (Python → Node.js)
```json
{
  "type": "acknowledgment",
  "chunkId": "chunk_id",
  "message": "Audio chunk received"
}
```

4. **transcription_completed** (Broadcast)
```json
{
  "type": "transcription_completed",
  "sessionId": "session_id",
  "chunkId": "chunk_id",
  "transcription": "transcribed text",
  "confidence": 0.95,
  "sentiment": "positive",
  "timestamp": "2025-01-22T10:05:45.123Z"
}
```

### MongoDB Schema

#### Collection: `meet_sessions`
```javascript
{
  _id: ObjectId,
  session_id: String (unique),
  interview_id: String,
  meet_url: String,
  bot_email: String,
  session_status: String, // pending, initializing, joining, recording, transcribing, disconnecting, completed, failed
  join_attempts: Number,
  audio_chunks_received: Number,
  transcription_segments: Number,
  created_at: DateTime,
  updated_at: DateTime,
  started_at: DateTime,
  joined_at: DateTime,
  ended_at: DateTime,
  errors: Array,
  last_error: String,
  metadata: Object
}
```

#### Collection: `meet_transcripts`
```javascript
{
  _id: ObjectId,
  chunk_id: String (unique),
  session_id: String,
  interview_id: String,
  raw_transcription: String,
  cleaned_transcription: String,
  confidence_score: Number,
  language_detected: String,
  speaker_detected: String,
  sentiment: String,
  key_points: Array,
  technical_terms: Array,
  chunk_duration: Number,
  transcribed_at: DateTime,
  metadata: Object
}
```

#### Collection: `meet_audio_chunks`
```javascript
{
  _id: ObjectId,
  chunk_id: String (unique),
  session_id: String,
  chunk_size: Number,
  audio_format: String,
  duration: Number,
  received_at: DateTime,
  processing_status: String,
  metadata: Object
}
```

---

## 📝 Logging

All components include comprehensive logging:

### Log Levels:
- `INFO` - Normal operations
- `WARN` - Non-critical issues
- `ERROR` - Critical failures
- `DEBUG` - Detailed debugging (disabled in production)

### Log Format:
```
2025-01-22 10:05:30 - component_name - LEVEL - message - {context}
```

### Example Logs:

**FastAPI Backend:**
```
🎤 Starting Meet recording session
   Meet URL: https://meet.google.com/abc-defg-hij
   Interview ID: interview_12345
✅ Session created: meet_session_20250122_100530_a1b2c3d4
🤖 Invoking Meet Bot LangGraph agent
✅ Meet Bot agent completed: initializing
```

**WebSocket Bridge:**
```
✅ Client connected: 140234567890
🎤 Received audio chunk: chunk_001
   Session: meet_session_20250122_100530_a1b2c3d4
   Size: 45632 bytes
   Format: webm
🔄 Starting transcription for chunk: chunk_001
🤖 Invoking audio transcription agent for: chunk_001
✅ Transcription completed for chunk: chunk_001
   Status: completed
   Confidence: 0.95
💾 Transcript saved to database: chunk_001
```

**Puppeteer Bot:**
```
{"timestamp":"2025-01-22T10:05:30.123Z","level":"INFO","message":"MeetRecorder initialized","sessionId":"meet_session_20250122_100530_a1b2c3d4"}
{"timestamp":"2025-01-22T10:05:32.456Z","level":"INFO","message":"WebSocket connected"}
{"timestamp":"2025-01-22T10:05:35.789Z","level":"INFO","message":"Browser launched successfully"}
{"timestamp":"2025-01-22T10:05:40.123Z","level":"INFO","message":"Successfully joined meeting"}
{"timestamp":"2025-01-22T10:05:45.456Z","level":"INFO","message":"Audio capture started successfully"}
```

---

## 🎯 Best Practices

### 1. Bot Account Management
- Use dedicated bot account (not personal)
- Rotate credentials regularly
- Monitor account for suspicious activity
- Keep credentials in environment variables

### 2. Resource Management
- Limit concurrent sessions (recommend max 5)
- Monitor CPU/RAM usage
- Clean up old transcripts periodically
- Use headless mode in production

### 3. Error Handling
- Always check API responses for `success: false`
- Implement retry logic in frontend
- Monitor session status regularly
- Log all errors for debugging

### 4. Security
- Never commit `.env` file
- Use HTTPS in production
- Implement rate limiting
- Validate all inputs
- Use WebSocket SSL (wss://) in production

### 5. Performance
- Enable caching for transcriptions
- Use connection pooling for MongoDB
- Optimize audio chunk size (5-10 seconds)
- Batch database writes where possible

---

## 📚 Additional Resources

- [Puppeteer Documentation](https://pptr.dev/)
- [Groq Whisper API](https://console.groq.com/docs/speech-text)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [MongoDB Best Practices](https://www.mongodb.com/docs/manual/administration/production-notes/)

---

## 🆘 Support

For issues and questions:
1. Check logs in all 3 processes
2. Review this troubleshooting guide
3. Check MongoDB for session errors
4. Test components individually
5. Contact development team

---

**Last Updated:** January 22, 2025  
**Version:** 1.0.0
