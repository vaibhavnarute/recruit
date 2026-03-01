# New Database Collections - Transcriptions & Meetings

## Overview

Added **2 new MongoDB collections** to better organize STT transcriptions and meeting data:

### 1. **transcriptions** Collection
Stores all STT audio transcriptions with detailed analysis

### 2. **meetings** Collection  
Stores virtual meeting sessions with participants, analytics, and status tracking

---

## Collections Structure

### **transcriptions** Collection

**Purpose**: Store STT audio transcriptions from interviews/meetings

**Key Fields**:
```python
{
    "transcription_id": str,          # Unique ID (trans_xxx)
    "session_id": str,                # Session reference
    "meeting_id": str,                # Meeting reference
    "interview_id": str,              # Interview reference
    "chunk_id": str,                  # Audio chunk ID
    
    # Audio metadata
    "audio_format": str,              # mp3, wav, webm
    "audio_duration": float,          # Seconds
    "audio_size_bytes": int,          # File size
    
    # Transcription data
    "raw_transcription": str,         # Original Whisper output
    "cleaned_transcription": str,     # Cleaned text
    "language_detected": str,         # Language code
    "confidence_score": float,        # 0-1 confidence
    
    # Analysis
    "sentiment": str,                 # positive, negative, neutral, mixed
    "speaker_detected": str,          # Speaker identification
    "key_points": [str],              # Extracted key points
    "technical_terms": [str],         # Technical terms found
    "questions_asked": [str],         # Questions detected
    "answers_given": [str],           # Answers detected
    
    # Processing
    "model": str,                     # whisper-large-v3
    "llm_model": str,                 # llama-3.3-70b-versatile
    "workflow": str,                  # langgraph
    "mcp_optimized": bool,            # MCP enabled
    "processing_time_ms": float,      # Processing time
    "tokens_used": int,               # LLM tokens
    
    # Context
    "question_context": str,          # Interview question
    "interview_stage": str,           # Stage in interview
    
    # Timestamps
    "transcribed_at": datetime,       # When transcribed
    "analyzed_at": datetime,          # When analyzed
    "created_at": datetime,
    "updated_at": datetime,
    
    # Error tracking
    "has_errors": bool,
    "errors": [dict],
    
    "metadata": dict
}
```

**Indexes**:
- `transcription_id` (unique)
- `session_id`
- `meeting_id`
- `interview_id`
- `transcribed_at` (desc)
- `sentiment`
- `confidence_score`

---

### **meetings** Collection

**Purpose**: Store virtual meeting sessions (Google Meet, Zoom, etc.)

**Key Fields**:
```python
{
    "meeting_id": str,                # Unique ID (meet_xxx)
    "session_id": str,                # Session ID
    "room_id": str,                   # Virtual room ID
    
    # Meeting details
    "meeting_title": str,             # Title
    "meeting_type": str,              # interview, screening, followup
    "meeting_link": str,              # Google Meet link
    "meeting_platform": str,          # google_meet, zoom, teams
    
    # Participants
    "host_email": str,                # Host email
    "host_name": str,                 # Host name
    "participants": [dict],           # List of participants
    "expected_participants": int,     # Expected count
    "actual_participants": int,       # Actual count
    
    # Related entities
    "interview_id": str,              # Interview reference
    "candidate_email": str,           # Candidate email
    "candidate_name": str,            # Candidate name
    "job_id": str,                    # Job reference
    
    # Status
    "status": str,                    # scheduled, in_progress, completed, cancelled
    "is_recording": bool,             # Currently recording
    "recording_enabled": bool,        # Recording capability
    "recording_url": str,             # Recording link
    
    # Timing
    "scheduled_at": datetime,         # Scheduled start
    "started_at": datetime,           # Actual start
    "ended_at": datetime,             # Actual end
    "duration_minutes": int,          # Actual duration
    "expected_duration_minutes": int, # Expected duration
    
    # AI Features
    "ai_bot_enabled": bool,           # AI bot enabled
    "ai_bot_name": str,               # Bot name
    "ai_bot_email": str,              # Bot email
    "bot_join_attempts": int,         # Join attempts
    "bot_joined_at": datetime,        # Bot join time
    "bot_left_at": datetime,          # Bot leave time
    
    # Transcription
    "transcription_enabled": bool,    # STT enabled
    "total_transcriptions": int,      # Transcript count
    "transcription_ids": [str],       # Transcript IDs
    "full_transcript": str,           # Combined transcript
    
    # Analytics
    "total_audio_chunks": int,        # Audio chunks received
    "total_participants_joined": int, # Join count
    "participant_join_times": [dict], # Join/leave log
    "average_sentiment": str,         # Overall sentiment
    "key_topics": [str],              # Main topics
    "questions_count": int,           # Questions asked
    "technical_score": float,         # Technical assessment
    "communication_score": float,     # Communication score
    
    # Calendar
    "calendar_event_id": str,         # Google Calendar ID
    "calendar_link": str,             # Calendar link
    "reminder_sent": bool,            # Reminder sent
    "reminder_sent_at": datetime,     # When reminder sent
    
    # Security
    "access_code": str,               # Meeting code
    "is_private": bool,               # Private meeting
    "allowed_domains": [str],         # Allowed domains
    
    # Timestamps
    "created_at": datetime,
    "updated_at": datetime,
    "last_activity_at": datetime,
    
    # Errors
    "join_errors": [dict],
    "recording_errors": [dict],
    "has_errors": bool,
    
    "metadata": dict
}
```

**Indexes**:
- `meeting_id` (unique)
- `session_id`
- `interview_id`
- `candidate_email`
- `host_email`
- `status`
- `scheduled_at` (desc)
- `started_at` (desc)
- `calendar_event_id`

---

## Usage

### 1. **Import Repository**
```python
from repositories.transcriptions_meetings_repository import TranscriptionsMeetingsRepository

repo = TranscriptionsMeetingsRepository()
```

### 2. **Create Transcription**
```python
transcription_data = {
    "session_id": "session_123",
    "meeting_id": "meet_456",
    "chunk_id": "chunk_789",
    "raw_transcription": "Hello, this is a test...",
    "cleaned_transcription": "Hello, this is a test.",
    "confidence_score": 0.85,
    "sentiment": "positive",
    "technical_terms": ["Python", "FastAPI"]
}

result = repo.create_transcription(transcription_data)
print(f"Created: {result['transcription_id']}")
```

### 3. **Create Meeting**
```python
meeting_data = {
    "meeting_title": "Interview with John Doe",
    "meeting_type": "interview",
    "meeting_link": "https://meet.google.com/xxx-yyyy-zzz",
    "host_email": "hr@company.com",
    "candidate_email": "john@email.com",
    "candidate_name": "John Doe",
    "scheduled_at": datetime.utcnow(),
    "ai_bot_enabled": True,
    "transcription_enabled": True
}

meeting = repo.create_meeting(meeting_data)
print(f"Created: {meeting['meeting_id']}")
```

### 4. **Get Transcriptions for Session**
```python
transcriptions = repo.get_transcriptions_by_session("session_123")
print(f"Found {len(transcriptions)} transcriptions")
```

### 5. **Get Full Transcript**
```python
full_transcript = repo.get_full_transcript("session_123")
print(full_transcript)
```

### 6. **Update Meeting Status**
```python
repo.update_meeting("meet_456", {
    "status": "in_progress",
    "started_at": datetime.utcnow(),
    "actual_participants": 2
})
```

### 7. **Link Transcription to Meeting**
```python
repo.add_transcription_to_meeting("meet_456", "trans_789")
repo.update_meeting_transcript("meet_456")  # Rebuild full transcript
```

### 8. **Get Statistics**
```python
stats = repo.get_stats()
print(f"Total Transcriptions: {stats['total_transcriptions']}")
print(f"Total Meetings: {stats['total_meetings']}")
print(f"Active Meetings: {stats['active_meetings']}")
```

---

## Migration

### Run Migration Script
```powershell
python migrate_collections.py
```

This will:
1. ✅ Migrate `meet_transcripts` → `transcriptions`
2. ✅ Create sample meeting
3. ✅ Verify collections exist

**Note**: Original collections (`meet_transcripts`, `meet_sessions`) are preserved as backup.

---

## Integration

### STT Agent (Already Updated)
The `audio_transcription_agent.py` now automatically saves to both:
- **New**: `transcriptions` collection (detailed schema)
- **Backward Compatible**: `meet_transcripts` collection (legacy support)

### Example from Agent
```python
# In store_transcript() function
transcriptions_collection = db['transcriptions']
transcription_doc = {
    "transcription_id": f"trans_{state['audio_chunk_id']}",
    "session_id": state['session_id'],
    "raw_transcription": state['raw_transcription'],
    # ... all fields
}
transcriptions_collection.update_one(
    {"transcription_id": transcription_doc["transcription_id"]},
    {"$set": transcription_doc},
    upsert=True
)
```

---

## Updated Models

### db/models.py
```python
class Collections:
    # ... existing collections
    TRANSCRIPTIONS = "transcriptions"  # New
    MEETINGS = "meetings"              # New

ALL_COLLECTIONS = [
    # ... existing collections
    Collections.TRANSCRIPTIONS,
    Collections.MEETINGS
]
```

Added schemas:
- `TRANSCRIPTIONS_SCHEMA` (48 fields)
- `MEETINGS_SCHEMA` (60+ fields)

---

## Files Created/Updated

### Created:
1. ✅ `repositories/transcriptions_meetings_repository.py` - Repository class
2. ✅ `migrate_collections.py` - Migration script
3. ✅ `NEW_COLLECTIONS_GUIDE.md` - This guide

### Updated:
1. ✅ `db/models.py` - Added new schemas and collection names
2. ✅ `langgraph_agents/audio_transcription_agent.py` - Store to new collection

---

## Benefits

### ✅ Better Organization
- Transcriptions separate from raw audio chunks
- Meetings have dedicated collection with full tracking

### ✅ Rich Analytics
- Track sentiment, key points, technical terms per transcription
- Meeting-level analytics (avg sentiment, topics, scores)

### ✅ Flexible Querying
- Indexes on session_id, meeting_id, interview_id
- Easy to get all transcripts for a meeting
- Filter by sentiment, confidence, date

### ✅ Backward Compatible
- Old collections still work
- Dual writes during transition
- No breaking changes

---

## Next Steps

1. **Run migration**: `python migrate_collections.py`
2. **Test transcriptions**: Run STT tests to verify data is saved
3. **Create meetings**: Start using meetings collection for new interviews
4. **Build analytics**: Query transcriptions for sentiment analysis
5. **Update frontend**: Display meeting status and transcripts

---

## Testing

### Verify Collections Exist
```python
from pymongo import MongoClient
import os

client = MongoClient(os.getenv('MONGO_URI'))
db = client['ai_recruiter']

print("Collections:", db.list_collection_names())
# Should include: 'transcriptions', 'meetings'

print("Transcriptions:", db['transcriptions'].count_documents({}))
print("Meetings:", db['meetings'].count_documents({}))
```

### Test Repository
```python
from repositories.transcriptions_meetings_repository import get_transcriptions_meetings_repo

repo = get_transcriptions_meetings_repo()
stats = repo.get_stats()
print(stats)
repo.close()
```

---

## Support

For issues or questions:
1. Check MongoDB connection in `.env`
2. Verify collections exist: `db.list_collection_names()`
3. Run migration script if collections missing
4. Check logs for errors during transcription storage

---

**Last Updated**: October 22, 2025  
**Version**: 1.0
