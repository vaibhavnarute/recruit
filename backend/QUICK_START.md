# Quick Start Guide - AI Interview System

## 🚀 Quick Start (5 Minutes)

### Step 1: Start the Server
```bash
cd backend
python main.py
```
Server runs on `http://localhost:8001`

### Step 2: Schedule Interview
```bash
curl -X POST http://localhost:8001/api/interviews/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_name": "John Doe",
    "candidate_email": "john@example.com",
    "job_id": "job-123",
    "job_title": "Python Developer",
    "hr_email": "hr@company.com",
    "hr_id": "hr-001",
    "scheduled_datetime": "2025-10-21T10:00:00Z",
    "duration_minutes": 30,
    "auto_start_bot": true
  }'
```

Response includes `interview_id` and `trigger_url`.

### Step 3: Generate Questions
```bash
curl -X POST http://localhost:8001/api/questions/generate \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_id": "candidate-123",
    "job_id": "job-123",
    "interview_id": "YOUR_INTERVIEW_ID",
    "resume_data": {
      "skills": ["Python", "FastAPI", "MongoDB"],
      "experience": "3 years"
    },
    "job_description": {
      "title": "Python Developer",
      "requirements": ["Python", "API development"]
    }
  }'
```

### Step 4: Run Automated Interview
```bash
curl -X POST http://localhost:8001/api/interviews/YOUR_INTERVIEW_ID/auto-conduct
```

This will:
- ✅ Speak introduction (TTS)
- ✅ Ask all 10 questions (TTS)
- ✅ Analyze answers (LLM)
- ✅ Generate follow-ups
- ✅ Calculate scores
- ✅ Save results

---

## 📋 Test Scripts

### Run All Tests
```bash
# Test 1: Single Q&A loop
python test_qa_loop.py

# Test 2: Multiple questions (2-3)
python test_multiple_questions.py

# Test 3: Complete interview (10 questions)
python test_complete_interview.py

# Test 4: Audio playback readiness
python test_audio_playback.py

# Test 5: Automated orchestrator
python test_auto_conductor.py
```

---

## 🎯 Key Endpoints

### Core Interview Flow
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/interviews/schedule` | POST | Schedule interview with auto-join |
| `/api/questions/generate` | POST | Generate 10 questions from resume |
| `/api/interviews/{id}/auto-conduct` | POST | **Run complete interview** |
| `/api/interviews/{id}` | GET | Get interview details |

### Manual Q&A Loop
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/interviews/{id}/conduct` | POST | Speak introduction |
| `/api/interviews/{id}/qa-loop` | POST | Ask question, wait for answer |
| `/api/interviews/{id}/process-answer` | POST | Analyze answer with LLM |

### Bot Control
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/meet/trigger/{id}?token={token}` | GET | Auto-trigger bot join |
| `/api/meet/start` | POST | Manually start bot |
| `/api/meet/stop` | POST | Stop bot session |

---

## 💡 Example Workflow

### Manual Interview (Step-by-Step)
```bash
INTERVIEW_ID="your-interview-id"

# 1. Start introduction
curl -X POST http://localhost:8001/api/interviews/$INTERVIEW_ID/conduct

# 2. Ask first question
curl -X POST http://localhost:8001/api/interviews/$INTERVIEW_ID/qa-loop

# 3. Process answer
curl -X POST http://localhost:8001/api/interviews/$INTERVIEW_ID/process-answer \
  -H "Content-Type: application/json" \
  -d '{
    "answer": "Data types include integers, floats, strings...",
    "answer_audio_id": "audio_123"
  }'

# 4. Repeat steps 2-3 for all questions
```

### Automated Interview (One Command)
```bash
# Just one call - handles everything!
curl -X POST http://localhost:8001/api/interviews/$INTERVIEW_ID/auto-conduct
```

---

## 📊 Response Examples

### Auto-Conduct Response
```json
{
  "success": true,
  "message": "Automated interview completed successfully",
  "data": {
    "interview_id": "uuid",
    "candidate_name": "John Doe",
    "total_questions": 10,
    "questions_asked": 10,
    "questions_answered": 10,
    "followups_generated": 3,
    "scores": [8, 7, 9, 6, 8, 7, 5, 6, 8, 7],
    "average_score": 7.1,
    "started_at": "2025-10-21T10:00:00Z",
    "completed_at": "2025-10-21T10:30:00Z",
    "status": "completed"
  }
}
```

### Process Answer Response
```json
{
  "success": true,
  "message": "Answer processed successfully",
  "data": {
    "score": 8,
    "feedback": "Good answer covering key points...",
    "next_action": "followup",
    "followup_question": "Can you provide specific examples?",
    "followup_audio_id": "tts_uuid",
    "followup_audio_duration": 10.56
  }
}
```

---

## 🔧 Configuration

### Environment Variables (.env)
```env
# Required
GROQ_API_KEY=your_groq_key
ELEVENLABS_API_KEY=your_elevenlabs_key
MONGODB_URI=your_mongodb_atlas_uri

# Google Meet Bot
MEET_BOT_EMAIL=bot@gmail.com
MEET_BOT_PASSWORD=your_password

# Optional
DASHBOARD_SECRET=your-secret-key
```

### MongoDB Collections
- `interviews` - Interview documents
- `tts_audio` - TTS audio files
- `meet_sessions` - Bot sessions
- `meet_transcripts` - STT transcripts

---

## 🐛 Troubleshooting

### Issue: No questions generated
**Solution:** 
```bash
# Check if questions exist
curl http://localhost:8001/api/interviews/$INTERVIEW_ID

# Generate questions
curl -X POST http://localhost:8001/api/questions/generate ...
```

### Issue: Bot not joining
**Solution:**
```bash
# Check trigger URL
curl http://localhost:8001/api/interviews/$INTERVIEW_ID

# Manually trigger
curl "http://localhost:8001/api/meet/trigger/$INTERVIEW_ID?token=YOUR_TOKEN"
```

### Issue: TTS not working
**Solution:**
- Check ELEVENLABS_API_KEY in .env
- Verify API key is valid
- Check logs for errors

### Issue: LLM not analyzing
**Solution:**
- Check GROQ_API_KEY in .env
- Verify Groq API is accessible
- Check rate limits

---

## 📈 Performance Tips

### Optimize Interview Speed
1. Use `auto-conduct` endpoint (fastest)
2. Reduce simulated delays in production
3. Use batch TTS generation
4. Cache frequently used audio

### Monitor Performance
```bash
# Check logs
tail -f backend/logs/interview.log

# Monitor MongoDB
# Check collection sizes and query performance

# API response times
# Track TTS generation: ~1.8s
# Track LLM analysis: ~1-2s
# Track full Q&A cycle: ~3s
```

---

## 🎓 Best Practices

### Before Interview
1. ✅ Schedule interview with auto-join enabled
2. ✅ Generate questions from resume
3. ✅ Verify bot credentials
4. ✅ Test TTS and LLM APIs

### During Interview
1. ✅ Use auto-conduct for full automation
2. ✅ Monitor bot session status
3. ✅ Check real-time transcriptions
4. ✅ Handle errors gracefully

### After Interview
1. ✅ Retrieve interview results
2. ✅ Review scores and feedback
3. ✅ Export to analytics dashboard
4. ✅ Send results to HR

---

## 🚀 Production Deployment

### Checklist
- [ ] Environment variables configured
- [ ] MongoDB Atlas connected
- [ ] Groq API key valid
- [ ] ElevenLabs API key valid
- [ ] Google Meet bot credentials set
- [ ] Server running on production host
- [ ] SSL/TLS certificates installed
- [ ] Firewall rules configured
- [ ] Monitoring enabled
- [ ] Backup strategy in place

### Recommended Setup
```bash
# Use Gunicorn for production
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8001

# Use Nginx reverse proxy
# Configure SSL with Let's Encrypt
# Set up monitoring with Prometheus/Grafana
```

---

## 📚 Additional Resources

- **Full Documentation:** [COMPLETE_INTERVIEW_SYSTEM.md](COMPLETE_INTERVIEW_SYSTEM.md)
- **API Reference:** Check `/docs` endpoint (FastAPI Swagger UI)
- **Test Scripts:** `test_*.py` files in backend/
- **Logs:** Check console output and log files

---

## 🎉 You're Ready!

Your AI Interview System is fully set up and ready to conduct automated interviews. Start with the test scripts to verify everything works, then use `auto-conduct` for production interviews.

**Happy Interviewing! 🚀**
