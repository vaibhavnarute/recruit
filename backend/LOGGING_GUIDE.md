# Logging Guide - AI Recruiter TTS & Meeting Bot

## 📋 Overview

Comprehensive logging has been implemented across all TTS and Meeting Bot features to track operations, debug issues, and monitor performance.

## 🗂️ Log Files Structure

All logs are stored in `backend/logs/` directory with daily rotation:

```
backend/logs/
├── ai_recruiter_YYYYMMDD.log      # Main application log (all modules)
├── tts_YYYYMMDD.log                # TTS-specific operations
├── meeting_bot_YYYYMMDD.log        # Meeting bot operations
├── interview_YYYYMMDD.log          # Interview conductor operations
└── errors_YYYYMMDD.log             # All ERROR level logs
```

## 🎯 Logging Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error events with stack traces

## 📊 TTS Logging

### TTS Speak Endpoint (`/api/tts/speak`)

```
============================================================================
🔊 TTS SPEAK REQUEST RECEIVED
   Timestamp: 2025-10-24T00:28:16.343Z
   Text Length: 84 characters
   Text Preview: Hello! Welcome to your technical interview for...
   Text Type: intro
   Voice Profile: professional_female
   Emotion: professional
   Model: eleven_multilingual_v2
   Output Format: mp3_44100_128
   Session ID: session_123
   Meeting ID: meeting_456
   Interview ID: int_789
   Streaming: False
🎬 Starting TTS generation...
✅ TTS GENERATION SUCCESSFUL
   TTS ID: tts_7beb7af9-047d-4f6c-bbe3-99154086fee3
   Voice Name: Sarah
   Audio Duration: 5.51s
   Audio Size: 86.17 KB
   Processing Time: 2796ms
   Total Request Time: 3.42s
   Stored in DB: True
============================================================================
```

### TTS Agent Workflow

Each step in the LangGraph workflow is logged:

```
2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO - 🎬 Initializing TTS: tts_xxx
2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO - ✅ TTS initialized
2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO -    Text length: 84 characters
2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO -    Voice profile: professional_female
2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO -    Model: eleven_multilingual_v2

2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO - ✅ Validating text input
2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO - ✅ Text validated (84 chars)

2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO - 🔧 Optimizing text for speech
2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO - ✅ Text optimized (88 chars)

2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO - 🎤 Selecting voice: professional_female
2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO - ✅ Voice selected: Sarah
2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO -    Voice ID: EXAVITQu4vr4xnSDxMaL
2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO -    Stability: 0.5
2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO -    Similarity: 0.75

2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO - 🎙️ Generating speech with ElevenLabs
2025-10-24 00:28:16 - langgraph_agents.tts_agent - INFO - 🔊 Standard mode (non-streaming)
2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO - ✅ Speech generated successfully
2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO -    Audio size: 86.17 KB
2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO -    Duration: 5.51 seconds
2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO -    Processing time: 2796 ms

2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO - 🔧 Processing audio data
2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO - ✅ Audio processed
2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO -    Base64 length: 117648 chars

2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO - 💾 Storing TTS audio: tts_xxx
2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO - ✅ Stored new TTS audio: tts_xxx
2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO - 📊 TTS Summary:
2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO -    Text: Hello! ... Welcome to your technical interview for...
2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO -    Voice: Sarah
2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO -    Duration: 5.51s
2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO -    Size: 86.17 KB
2025-10-24 00:28:19 - langgraph_agents.tts_agent - INFO -    Processing: 2796ms
```

### TTS Error Logging

```
2025-10-24 00:28:19 - langgraph_agents.tts_agent - ERROR - ❌ Error generating speech: API rate limit exceeded
Traceback (most recent call last):
  File "langgraph_agents/tts_agent.py", line 456, in generate_speech
    audio_bytes = self.elevenlabs_client.generate(...)
  ...
```

## 🤖 Meeting Bot Logging

### Bot Join Endpoint (`/api/bot/join-meeting`)

```
============================================================================
🤖 MEETING BOT JOIN REQUEST RECEIVED
   Timestamp: 2025-10-24T10:30:00.000Z
   Meeting Link: https://meet.google.com/abc-defg-hij
   Platform: google_meet
   Meeting Title: Interview - Python Developer
   Bot Name: AI Interview Assistant
   Auto Transcribe: True
   Auto TTS: True
   Auto Record: True
   Session ID: session_123
   Meeting ID: meeting_456
   Interview ID: int_789
   Expected Participants: ['candidate@email.com']
   Host: HR Manager
   Has Password: False
🎬 Starting bot join process...
✅ BOT JOINED MEETING SUCCESSFULLY
   Bot ID: bot_xyz789
   Bot Status: joined
   Join Time: 2025-10-24T10:30:02.500Z
   Meeting Platform: google_meet
   Features:
      - STT (Transcription): True
      - TTS (Text-to-Speech): True
      - Recording: True
   Browser Session: chrome_session_abc123
   Total Request Time: 2.85s
============================================================================
```

### Bot Workflow Logging

```
2025-10-24 10:30:00 - langgraph_agents.meeting_bot_agent - INFO - 🎬 Initializing bot: bot_xxx
2025-10-24 10:30:00 - langgraph_agents.meeting_bot_agent - INFO - ✅ Bot initialized
2025-10-24 10:30:00 - langgraph_agents.meeting_bot_agent - INFO -    Bot name: AI Interview Assistant
2025-10-24 10:30:00 - langgraph_agents.meeting_bot_agent - INFO -    Platform: google_meet

2025-10-24 10:30:00 - langgraph_agents.meeting_bot_agent - INFO - ✅ Validating meeting
2025-10-24 10:30:00 - langgraph_agents.meeting_bot_agent - INFO -    Platform detected: google_meet
2025-10-24 10:30:00 - langgraph_agents.meeting_bot_agent - INFO -    Has password: False

2025-10-24 10:30:01 - langgraph_agents.meeting_bot_agent - INFO - 🌐 Preparing browser
2025-10-24 10:30:01 - langgraph_agents.meeting_bot_agent - INFO - ✅ Browser ready

2025-10-24 10:30:02 - langgraph_agents.meeting_bot_agent - INFO - 🚪 Joining meeting
2025-10-24 10:30:02 - langgraph_agents.meeting_bot_agent - INFO - ✅ Joined meeting

2025-10-24 10:30:02 - langgraph_agents.meeting_bot_agent - INFO - 🔊 Setting up audio
2025-10-24 10:30:02 - langgraph_agents.meeting_bot_agent - INFO - ✅ Audio configured

2025-10-24 10:30:02 - langgraph_agents.meeting_bot_agent - INFO - ⚙️ Activating features
2025-10-24 10:30:02 - langgraph_agents.meeting_bot_agent - INFO -    STT: enabled
2025-10-24 10:30:02 - langgraph_agents.meeting_bot_agent - INFO -    TTS: enabled
2025-10-24 10:30:02 - langgraph_agents.meeting_bot_agent - INFO -    Recording: enabled

2025-10-24 10:30:02 - langgraph_agents.meeting_bot_agent - INFO - 💾 Storing session
2025-10-24 10:30:02 - langgraph_agents.meeting_bot_agent - INFO - ✅ Session stored
```

## 🎤 Interview + TTS Integration Logging

### Interview Start with Auto-TTS

```
2025-10-24 00:28:27 - langgraph_agents.interview_conductor_agent - INFO - 🎬 Starting new interview session
2025-10-24 00:28:27 - langgraph_agents.interview_conductor_agent - INFO - 🎬 Initializing interview: int_xxx
2025-10-24 00:28:27 - langgraph_agents.interview_conductor_agent - INFO - ✅ Interview initialized successfully
2025-10-24 00:28:27 - langgraph_agents.interview_conductor_agent - INFO -    Candidate: Test Candidate
2025-10-24 00:28:27 - langgraph_agents.interview_conductor_agent - INFO -    Position: Senior Python Developer
2025-10-24 00:28:27 - langgraph_agents.interview_conductor_agent - INFO -    Target Duration: 60 minutes

2025-10-24 00:28:27 - langgraph_agents.interview_conductor_agent - INFO - 👋 Generating introduction for Test Candidate
2025-10-24 00:28:27 - langgraph_agents.interview_conductor_agent - INFO - 🎤 Auto-generating TTS for introduction
2025-10-24 00:28:27 - langgraph_agents.interview_conductor_agent - INFO - 🔊 Generating TTS for intro
2025-10-24 00:28:27 - langgraph_agents.interview_conductor_agent - INFO -    Text: Hello Test Candidate! Welcome to your interview fo...

[TTS workflow logs...]

2025-10-24 00:28:30 - langgraph_agents.interview_conductor_agent - INFO - ✅ TTS generated for intro
2025-10-24 00:28:30 - langgraph_agents.interview_conductor_agent - INFO -    TTS ID: tts_5527594a-c6dc-48a3-a56d-3d6b42a8ea20
2025-10-24 00:28:30 - langgraph_agents.interview_conductor_agent - INFO -    Duration: 15.36s
```

## 📈 Performance Metrics Logged

### TTS Metrics
- Text length (characters, words)
- Processing time (milliseconds)
- Audio duration (seconds)
- Audio file size (KB)
- API response time
- Total request duration

### Meeting Bot Metrics
- Join time
- Browser session setup time
- Feature activation time
- Total participants
- Audio/video status

### Interview Metrics
- Question generation time
- Answer evaluation time
- Total interview duration
- Questions asked
- Answers received

## 🔍 Debugging Tips

### View TTS Logs Only
```bash
cat backend/logs/tts_YYYYMMDD.log
```

### View Meeting Bot Logs Only
```bash
cat backend/logs/meeting_bot_YYYYMMDD.log
```

### View All Errors
```bash
cat backend/logs/errors_YYYYMMDD.log
```

### Tail Logs in Real-Time
```bash
# All logs
tail -f backend/logs/ai_recruiter_YYYYMMDD.log

# TTS only
tail -f backend/logs/tts_YYYYMMDD.log

# Bot only
tail -f backend/logs/meeting_bot_YYYYMMDD.log
```

### Search for Specific Event
```bash
# Find all TTS generations
grep "TTS GENERATION SUCCESSFUL" backend/logs/*.log

# Find all bot joins
grep "BOT JOINED MEETING" backend/logs/*.log

# Find all errors
grep "ERROR" backend/logs/*.log
```

## 🎨 Log Emoji Reference

- 🎬 START - Operation started
- ✅ SUCCESS - Operation completed successfully
- ❌ ERROR - Operation failed
- ⚠️ WARNING - Warning condition
- ℹ️ INFO - Information
- 🔊 TTS - Text-to-speech related
- 🤖 BOT - Meeting bot related
- 🎤 INTERVIEW - Interview related
- ❓ QUESTION - Question generation
- 💬 ANSWER - Answer received
- 🎵 AUDIO - Audio processing
- 📹 VIDEO - Video processing
- 💾 DATABASE - Database operation
- 🔌 API - API call
- 🌐 NETWORK - Network operation
- ⏱️ TIME - Timing/duration
- 🎉 COMPLETE - Process completed

## 📋 Log Retention

- Logs are rotated daily (new file each day)
- Recommend keeping logs for 30 days
- Error logs should be kept for 90 days
- Set up automated cleanup:

```bash
# Delete logs older than 30 days
find backend/logs/ -name "*.log" -mtime +30 -delete
```

## 🚨 Alerting

Set up monitoring for critical errors:

```bash
# Monitor error log and send alerts
tail -f backend/logs/errors_*.log | while read line; do
    if [[ $line == *"CRITICAL"* ]]; then
        # Send alert (email, Slack, etc.)
        echo "$line" | mail -s "CRITICAL ERROR" admin@company.com
    fi
done
```

## 📊 Log Analysis

Use log analysis tools to extract insights:

```bash
# Count TTS generations per day
grep "TTS GENERATION SUCCESSFUL" backend/logs/tts_*.log | wc -l

# Average TTS processing time
grep "Processing Time:" backend/logs/tts_*.log | awk '{sum+=$NF; count++} END {print sum/count "ms"}'

# Count bot joins by platform
grep "Platform:" backend/logs/meeting_bot_*.log | sort | uniq -c
```

## 🔒 Security

- Logs may contain sensitive data (meeting links, emails)
- Ensure logs directory has proper permissions (chmod 700)
- Never commit logs to version control (.gitignore already configured)
- Sanitize logs before sharing externally

## 📝 Custom Logging

Add custom logging in your code:

```python
from logging_config import get_logger, LogContext, log_tts_event

logger = get_logger(__name__)

# Simple logging
logger.info("Operation started")

# Context-based logging
with LogContext("Custom Operation", logger) as ctx:
    ctx.log("Step 1 complete")
    ctx.log("Step 2 complete")
    # Automatically logs duration on exit

# Event-specific logging
log_tts_event(logger, "custom_event", 
              tts_id="tts_123",
              duration="5.5s",
              custom_field="value")
```
