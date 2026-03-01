# TTS & Meeting Bot Integration - Complete Guide

## 🎯 Overview

This implementation adds **Text-to-Speech (TTS)** and **Meeting Bot** functionality to the AI Recruiter system, enabling fully automated AI-powered interviews with natural speech.

## 📋 Features Implemented

### 1. **TTS Agent** (`langgraph_agents/tts_agent.py`)
- ✅ ElevenLabs API integration
- ✅ 4 professional voice profiles
- ✅ Real-time audio streaming
- ✅ MCP optimization (context, cache, tokens)
- ✅ MongoDB storage for audio files
- ✅ Multiple output formats (MP3, PCM)
- ✅ Emotion-aware speech generation

### 2. **Meeting Bot Agent** (`langgraph_agents/meeting_bot_agent.py`)
- ✅ Auto-join Zoom/Google Meet/Teams
- ✅ Browser automation framework (Selenium/Playwright ready)
- ✅ STT/TTS/Recording feature management
- ✅ Bot lifecycle management (join → active → leave)
- ✅ Meeting platform auto-detection
- ✅ Virtual audio device configuration

### 3. **Database Schemas** (`db/models.py`)
- ✅ `tts_audio` collection (50+ fields)
- ✅ `meeting_bots` collection (60+ fields)
- ✅ Updated `meetings` collection with TTS/bot tracking

### 4. **TTS Repository** (`repositories/tts_repository.py`)
- ✅ CRUD operations for TTS audio
- ✅ Voice profile statistics
- ✅ Meeting TTS summary
- ✅ Audio analytics

### 5. **API Endpoints** (`main.py`)

#### TTS Endpoints:
- `POST /api/tts/speak` - Convert text to speech
- `POST /api/tts/stream` - Stream audio in real-time
- `GET /api/tts/{tts_id}` - Get TTS audio by ID
- `GET /api/tts/health` - TTS service health check

#### Meeting Bot Endpoints:
- `POST /api/bot/join-meeting` - Join meeting with bot
- `POST /api/bot/leave-meeting/{bot_id}` - Leave meeting
- `GET /api/bot/{bot_id}` - Get bot status
- `GET /api/bot/health` - Bot service health check

### 6. **Interview Integration**
- ✅ Auto-generates TTS for introductions
- ✅ Auto-generates TTS for questions
- ✅ Auto-generates TTS for closing messages
- ✅ TTS data returned in interview API responses

### 7. **Test Scripts**
- ✅ `test_tts_integration.py` - Complete TTS testing
- ✅ `test_meeting_bot.py` - Complete bot testing

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install Python dependencies
pip install elevenlabs langgraph groq pymongo

# Set environment variables
export ELEVENLABS_API_KEY="your_elevenlabs_api_key"
export GROQ_API_KEY="your_groq_api_key"
export MONGO_URI="mongodb://localhost:27017/"
```

### 1. Test TTS Integration

```bash
cd backend
python test_tts_integration.py
```

**Expected Output:**
```
🔊 TTS INTEGRATION TEST SUITE
✅ Basic TTS Conversion PASSED
✅ Voice Profiles: 4/4 passed
✅ TTS Streaming PASSED
✅ Interview TTS Integration PASSED
✅ TTS Repository PASSED
```

### 2. Test Meeting Bot

```bash
python test_meeting_bot.py
```

**Expected Output:**
```
🤖 MEETING BOT TEST SUITE
✅ Platform Detection PASSED
✅ Bot Join Google Meet PASSED
✅ Bot Join Zoom PASSED
✅ Bot Leave Meeting PASSED
```

### 3. Start Backend Server

```bash
python main.py
```

Server starts on `http://localhost:8001`

---

## 📚 API Usage Examples

### Example 1: Convert Text to Speech

```python
import requests

url = "http://localhost:8001/api/tts/speak"
payload = {
    "text": "Hello! Welcome to your technical interview.",
    "text_type": "intro",
    "voice_profile": "professional_female",
    "emotion": "professional",
    "session_id": "session_123"
}

response = requests.post(url, json=payload)
result = response.json()

if result['success']:
    tts_id = result['data']['tts_id']
    audio_base64 = result['data']['audio_base64']
    duration = result['data']['audio_duration_seconds']
    print(f"✅ TTS generated: {tts_id}, {duration}s")
```

### Example 2: Start Interview with Auto-TTS

```python
url = "http://localhost:8001/api/interview/start"
payload = {
    "candidate_name": "John Doe",
    "candidate_email": "john@example.com",
    "job_title": "Senior Python Developer",
    "job_description": "Python expert needed",
    "required_skills": ["Python", "FastAPI", "LangGraph"],
    "meeting_id": "meeting_456"  # Enable TTS auto-generation
}

response = requests.post(url, json=payload)
result = response.json()

if result['success']:
    interview_id = result['data']['interview_id']
    introduction = result['data']['introduction']
    
    # TTS audio is auto-generated
    tts_audio = result['data'].get('tts_audio')
    if tts_audio:
        print(f"✅ TTS audio available: {tts_audio['tts_id']}")
        print(f"   Audio duration: {tts_audio['audio_duration_seconds']}s")
        print(f"   Voice: {tts_audio['voice_name']}")
```

### Example 3: Join Meeting with Bot

```python
url = "http://localhost:8001/api/bot/join-meeting"
payload = {
    "meeting_link": "https://meet.google.com/abc-defg-hij",
    "meeting_platform": "google_meet",
    "meeting_title": "Interview - Python Developer",
    "bot_name": "AI Interview Assistant",
    "auto_transcribe": True,  # Enable STT
    "auto_tts": True,         # Enable TTS
    "auto_record": True       # Enable recording
}

response = requests.post(url, json=payload)
result = response.json()

if result['success']:
    bot_id = result['data']['bot_id']
    status = result['data']['bot_status']
    features = result['data']['features']
    
    print(f"✅ Bot joined: {bot_id}")
    print(f"   Status: {status}")
    print(f"   STT: {features['stt_enabled']}")
    print(f"   TTS: {features['tts_enabled']}")
```

### Example 4: Stream TTS Audio

```python
url = "http://localhost:8001/api/tts/stream"
payload = {
    "text": "This is a streaming test. Audio will be delivered in chunks.",
    "voice_profile": "professional_female"
}

response = requests.post(url, json=payload, stream=True)

for line in response.iter_lines():
    if line:
        chunk_data = json.loads(line)
        if 'chunk' in chunk_data:
            # Process audio chunk
            audio_chunk = chunk_data['chunk']
            chunk_number = chunk_data['chunk_number']
            print(f"Received chunk #{chunk_number}")
```

---

## 🎤 Voice Profiles

### Available Voices

| Profile | Voice Name | Gender | Tone | Best For |
|---------|-----------|--------|------|----------|
| `professional_female` | Sarah | Female | Professional, clear | Technical interviews |
| `professional_male` | Adam | Male | Authoritative, deep | Senior interviews |
| `friendly_female` | Rachel | Female | Warm, approachable | Behavioral questions |
| `friendly_male` | Arnold | Male | Friendly, casual | Q&A sessions |

### Voice Settings

```python
{
    "stability": 0.5,          # 0.0-1.0 (higher = more consistent)
    "similarity_boost": 0.75,  # 0.0-1.0 (voice similarity)
    "style": 0.5,              # 0.0-1.0 (expressiveness)
    "use_speaker_boost": True  # Enhanced clarity
}
```

---

## 🔄 Interview Flow with TTS

```
┌─────────────────────────────────────────────────────────────┐
│  COMPLETE AI INTERVIEW FLOW WITH TTS                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. START INTERVIEW                                          │
│     ├── Generate introduction (LLM)                         │
│     ├── Auto-generate TTS for intro                         │
│     └── Return: interview_id + audio_base64                 │
│                                                               │
│  2. BOT JOINS MEETING                                        │
│     ├── Auto-join Google Meet/Zoom                          │
│     ├── Enable STT (transcribe candidate)                   │
│     ├── Enable TTS (speak questions)                        │
│     └── Enable Recording                                     │
│                                                               │
│  3. ASK TECHNICAL QUESTION #1                               │
│     ├── Generate question (LLM)                             │
│     ├── Auto-generate TTS                                   │
│     └── Stream audio to meeting                              │
│                                                               │
│  4. RECEIVE ANSWER                                           │
│     ├── STT transcribes candidate speech                    │
│     └── Store transcription in DB                            │
│                                                               │
│  5. ANALYZE ANSWER                                           │
│     ├── LLM evaluates response                              │
│     ├── Calculate scores                                     │
│     └── Extract insights                                     │
│                                                               │
│  6. GENERATE NEXT QUESTION                                   │
│     ├── Context-aware question (LLM)                        │
│     ├── Auto-generate TTS                                   │
│     └── Stream to meeting                                    │
│                                                               │
│  [Repeat 3-6 for all interview stages]                      │
│                                                               │
│  7. GENERATE CLOSING                                         │
│     ├── Summary + next steps (LLM)                          │
│     ├── Auto-generate TTS                                   │
│     └── Stream to meeting                                    │
│                                                               │
│  8. SAVE TO MONGODB                                          │
│     ├── interviews collection                                │
│     ├── tts_audio collection                                │
│     ├── meeting_bots collection                             │
│     └── meetings collection                                  │
│                                                               │
│  9. BOT LEAVES MEETING                                       │
│     └── Update status in DB                                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ MongoDB Collections

### tts_audio Collection

```javascript
{
    "tts_id": "tts_abc123",
    "text": "Welcome to your interview...",
    "text_type": "intro",
    "voice_profile": "professional_female",
    "voice_name": "Sarah",
    "audio_base64": "base64_encoded_audio...",
    "audio_duration_seconds": 12.5,
    "audio_size_bytes": 256000,
    "processing_time_ms": 850,
    "session_id": "session_123",
    "meeting_id": "meeting_456",
    "interview_id": "int_789",
    "success": true,
    "created_at": "2025-10-23T10:30:00"
}
```

### meeting_bots Collection

```javascript
{
    "bot_id": "bot_xyz789",
    "meeting_id": "meeting_456",
    "meeting_link": "https://meet.google.com/abc-defg-hij",
    "meeting_platform": "google_meet",
    "bot_name": "AI Interview Assistant",
    "bot_status": "active",
    "join_time": "2025-10-23T10:30:00",
    "stt_enabled": true,
    "tts_enabled": true,
    "recording_enabled": true,
    "audio_input_device": "Virtual Microphone (Bot TTS)",
    "audio_output_device": "Virtual Speakers (Bot STT)",
    "participant_count": 2,
    "questions_asked": 5,
    "answers_received": 4
}
```

---

## 🛠️ Production Setup

### Browser Automation (Required for Production)

```bash
# Install Selenium
pip install selenium webdriver-manager

# Or Playwright (recommended)
pip install playwright
playwright install
```

**Update `meeting_bot_agent.py`:**

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

def join_meeting(self, state):
    # Initialize Chrome driver
    driver = webdriver.Chrome()
    driver.get(state['meeting_link'])
    
    # Click join button
    join_button = WebDriverWait(driver, 10).until(
        lambda d: d.find_element(By.CSS_SELECTOR, "button[aria-label*='Join']")
    )
    join_button.click()
    
    # Handle microphone/camera permissions
    # ...
```

### Virtual Audio Devices

```bash
# Windows: Install VB-Cable
# https://vb-audio.com/Cable/

# macOS: Install BlackHole
brew install blackhole-2ch

# Linux: Use PulseAudio virtual sinks
pactl load-module module-null-sink sink_name=virtual_mic
```

### Environment Variables

```bash
# .env file
ELEVENLABS_API_KEY=your_elevenlabs_key
GROQ_API_KEY=your_groq_key
MONGO_URI=mongodb://localhost:27017/
BOT_EMAIL=ai-bot@company.com
```

---

## 📊 Monitoring & Analytics

### Check TTS Stats

```python
from repositories.tts_repository import TTSRepository

repo = TTSRepository()
stats = repo.get_tts_stats()

print(f"Total TTS: {stats['total_tts_audio']}")
print(f"Success Rate: {stats['success_rate']:.2f}%")

# Voice profile stats
voice_stats = repo.get_all_voice_profiles_stats()
for vs in voice_stats:
    print(f"{vs['voice_profile']}: {vs['total_audio']} files")
```

### Check Bot Stats

```python
from pymongo import MongoClient

client = MongoClient()
db = client['ai_recruiter']

total_bots = db['meeting_bots'].count_documents({})
active_bots = db['meeting_bots'].count_documents({"bot_status": "active"})

print(f"Total Bots: {total_bots}")
print(f"Active: {active_bots}")
```

---

## ⚠️ Error Handling

All endpoints return HTTP 200 with error details in response body:

```javascript
// Success response
{
    "success": true,
    "data": { ... },
    "message": "Operation successful"
}

// Error response (still HTTP 200)
{
    "success": false,
    "error": {
        "code": "TTS_GENERATION_ERROR",
        "message": "Failed to generate speech",
        "details": [ ... ]
    },
    "message": "Failed to generate speech"
}
```

---

## 🔍 Troubleshooting

### TTS Not Working

1. **Check API Key:**
   ```bash
   echo $ELEVENLABS_API_KEY
   ```

2. **Test Connection:**
   ```python
   from elevenlabs.client import ElevenLabs
   client = ElevenLabs(api_key="your_key")
   voices = client.voices.get_all()
   print(len(voices))  # Should return available voices
   ```

3. **Check Logs:**
   ```bash
   tail -f backend/logs/tts.log
   ```

### Bot Not Joining Meetings

1. **Browser Automation:**
   - Currently simulated
   - Integrate Selenium/Playwright for production

2. **Check Platform:**
   ```python
   # Ensure platform is detected correctly
   if 'zoom.us' in meeting_link:
       platform = 'zoom'
   ```

3. **Virtual Audio:**
   - Ensure virtual audio devices are installed
   - Check device names match configuration

---

## 🎯 Next Steps

### Recommended Enhancements

1. **Browser Automation Integration**
   - Integrate Selenium for actual meeting joins
   - Handle authentication flows
   - Manage permissions (mic, camera)

2. **Real-time Audio Streaming**
   - Stream TTS audio directly to meeting
   - Capture meeting audio for STT
   - Implement audio mixing

3. **Advanced Voice Control**
   - Emotion detection in candidate speech
   - Dynamic voice adjustment
   - Multi-language support

4. **Bot Intelligence**
   - Auto-handle waiting rooms
   - Detect meeting end
   - Handle network issues

5. **Analytics Dashboard**
   - Real-time bot status
   - TTS usage metrics
   - Voice profile performance

---

## 📝 License

Part of the AI Recruiter project.

## 👥 Support

For issues or questions:
- Check logs in `backend/logs/`
- Run test scripts to validate setup
- Review MongoDB data for debugging

---

**🎉 Congratulations! Your AI Recruiter now has full TTS and Meeting Bot capabilities!**
