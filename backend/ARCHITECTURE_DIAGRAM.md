# 🎯 Google Meet Interview - Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMPLETE SYSTEM ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────┐
│                              1. API LAYER (FastAPI)                            │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  POST /api/meet-interview/start                                               │
│  ├─ Request: { interview_id, meet_url, candidate_name, job_title }           │
│  └─ Returns: { overall_score, qa_history, session_id, completed_at }         │
│                                                                                │
│  GET /api/meet-interview/status/{interview_id}                                │
│  └─ Returns: Real-time interview status from MongoDB                          │
│                                                                                │
└────────────────────┬──────────────────────────────────────────────────────────┘
                     │ calls
                     ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                    2. ORCHESTRATION LAYER (interview_orchestrator.py)         │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  MeetInterviewOrchestrator.conduct_interview()                                │
│  │                                                                             │
│  ├─ Phase 1: Join Meeting                                                     │
│  │   ├─ GoogleMeetAuth.initialize() ────────► Playwright Browser            │
│  │   ├─ GoogleMeetAuth.login() ─────────────► Google OAuth                  │
│  │   ├─ MeetBotJoiner.join_meeting() ───────► Click "Join now"              │
│  │   ├─ MeetBotJoiner.wait_for_participants() ► Wait for candidate          │
│  │   └─ MeetAudioIntegration.initialize() ──► Inject Web Audio API          │
│  │                                                                             │
│  ├─ Phase 2: Load Questions                                                   │
│  │   └─ QuestionRepository.get_questions_by_job_title() ──► MongoDB          │
│  │                                                                             │
│  ├─ Phase 3: Greet Candidate                                                  │
│  │   ├─ TTSAgent.text_to_speech("Hello...") ────────────► Deepgram Aura     │
│  │   └─ MeetAudioIntegration.play_tts_audio(greeting) ──► Play in Meet       │
│  │                                                                             │
│  ├─ Phase 4: Q&A Loop (for each question)                                     │
│  │   │                                                                         │
│  │   ├─ [ASK QUESTION]                                                        │
│  │   │   ├─ TTSAgent.text_to_speech(question) ────────► Deepgram Aura       │
│  │   │   └─ MeetAudioIntegration.play_tts_audio() ────► Play in Meet         │
│  │   │                                                                         │
│  │   ├─ [RECORD ANSWER]                                                       │
│  │   │   ├─ MeetAudioIntegration.start_recording() ───► MediaRecorder        │
│  │   │   ├─ MeetAudioIntegration.wait_for_silence() ──► Detect silence       │
│  │   │   └─ MeetAudioIntegration.stop_recording() ────► Get audio chunks     │
│  │   │                                                                         │
│  │   ├─ [TRANSCRIBE ANSWER]                                                   │
│  │   │   └─ AudioTranscriptionAgent.transcribe() ─────► Groq Whisper        │
│  │   │                                                                         │
│  │   ├─ [ANALYZE ANSWER]                                                      │
│  │   │   └─ Groq.chat.completions.create() ───────────► Groq LLM             │
│  │   │       ├─ Input: Question + Answer                                      │
│  │   │       └─ Output: Score (0-10), Feedback, Strengths, Improvements       │
│  │   │                                                                         │
│  │   └─ [SAVE Q&A PAIR]                                                       │
│  │       ├─ qa_history.append(question, answer, score, feedback)              │
│  │       └─ QARepository.save_qa_pair() ──────────────► MongoDB              │
│  │                                                                             │
│  ├─ Phase 5: Close Interview                                                  │
│  │   ├─ Calculate overall_score = average(all scores)                         │
│  │   ├─ TTSAgent.text_to_speech("Thank you...") ───────► Deepgram Aura       │
│  │   └─ MeetAudioIntegration.play_tts_audio(closing) ─► Play in Meet          │
│  │                                                                             │
│  ├─ Phase 6: Leave Meeting                                                    │
│  │   ├─ MeetBotJoiner.leave_meeting() ─────────────────► Click "Leave call"  │
│  │   └─ GoogleMeetAuth.close() ────────────────────────► Close browser       │
│  │                                                                             │
│  └─ Phase 7: Save Results                                                     │
│      └─ InterviewRepository.update_interview_status() ──► MongoDB             │
│                                                                                │
└────────────────────┬──────────────────────────────────────────────────────────┘
                     │ uses
                     ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                     3. COMPONENT LAYER (Meet Bot + AI Agents)                 │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─────────────────────────────────────────────────────────────┐             │
│  │  MEET BOT COMPONENTS (NEW)                                  │             │
│  ├─────────────────────────────────────────────────────────────┤             │
│  │  meet_bot_launcher.py                                       │             │
│  │  ├─ GoogleMeetAuth                                          │             │
│  │  │   ├─ Playwright browser control                          │             │
│  │  │   ├─ Google OAuth authentication                         │             │
│  │  │   └─ Session persistence (7-day TTL)                     │             │
│  │  │                                                           │             │
│  │  meet_bot_joiner.py                                         │             │
│  │  ├─ MeetBotJoiner                                           │             │
│  │  │   ├─ Pre-join configuration (camera/mic)                 │             │
│  │  │   ├─ Join button detection (10+ selectors)               │             │
│  │  │   ├─ Rejection detection (NO false positives)            │             │
│  │  │   ├─ Participant counting                                │             │
│  │  │   └─ Leave meeting logic                                 │             │
│  │  │                                                           │             │
│  │  meet_audio_integration.py                                  │             │
│  │  └─ MeetAudioIntegration                                    │             │
│  │      ├─ Web Audio API injection                             │             │
│  │      ├─ MediaRecorder setup (Opus codec, 16kHz)             │             │
│  │      ├─ TTS audio playback                                  │             │
│  │      ├─ Candidate audio recording                           │             │
│  │      └─ Silence detection (-40dB threshold, 3s duration)    │             │
│  └─────────────────────────────────────────────────────────────┘             │
│                                                                                │
│  ┌─────────────────────────────────────────────────────────────┐             │
│  │  AI AGENTS (EXISTING LangGraph)                             │             │
│  ├─────────────────────────────────────────────────────────────┤             │
│  │  tts_agent.py                                               │             │
│  │  ├─ TTSAgent (Deepgram Aura)                                │             │
│  │  │   ├─ 4 Voice Profiles:                                   │             │
│  │  │   │   • professional_female (aura-asteria-en)            │             │
│  │  │   │   • professional_male (aura-orpheus-en)              │             │
│  │  │   │   • friendly_female (aura-luna-en)                   │             │
│  │  │   │   • friendly_male (aura-perseus-en)                  │             │
│  │  │   └─ Returns: Base64 audio data                          │             │
│  │  │                                                           │             │
│  │  audio_transcription_agent.py                               │             │
│  │  ├─ AudioTranscriptionAgent (Groq Whisper)                  │             │
│  │  │   ├─ Model: whisper-large-v3                             │             │
│  │  │   ├─ Input: Audio bytes (WebM/Opus)                      │             │
│  │  │   └─ Output: Transcription text                          │             │
│  │  │                                                           │             │
│  │  question_generator_agent.py                                │             │
│  │  ├─ QuestionGeneratorAgent                                  │             │
│  │  │   ├─ Generates questions from resume/job description     │             │
│  │  │   └─ Uses: Groq LLM                                      │             │
│  │  │                                                           │             │
│  │  MCP Components (Context & Cache Management)                │             │
│  │  ├─ MCPContextManager (conversation context)                │             │
│  │  ├─ MCPCacheManager (response caching)                      │             │
│  │  └─ TokenOptimizer (reduce API costs)                       │             │
│  └─────────────────────────────────────────────────────────────┘             │
│                                                                                │
└────────────────────┬──────────────────────────────────────────────────────────┘
                     │ uses
                     ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                        4. EXTERNAL SERVICES                                    │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────────┐│
│  │   Google Services    │  │   AI/ML Services     │  │   Database          ││
│  ├──────────────────────┤  ├──────────────────────┤  ├─────────────────────┤│
│  │ • Google Meet        │  │ • Deepgram Aura (TTS)│  │ • MongoDB           ││
│  │ • Google OAuth       │  │ • Groq Whisper (STT) │  │   Collections:      ││
│  │ • Google Calendar    │  │ • Groq LLM           │  │   - interviews      ││
│  │   API                │  │   (llama-3.3-70b)    │  │   - qa_pairs        ││
│  │                      │  │                      │  │   - questions       ││
│  └──────────────────────┘  └──────────────────────┘  └─────────────────────┘│
│                                                                                │
└───────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────┐
│                           5. DATA FLOW DIAGRAM                                 │
└───────────────────────────────────────────────────────────────────────────────┘

User Creates Meeting
  │
  ├─► GoogleCalendarService.create_interview_meeting()
  │   ├─ Attendees: [Candidate, HR, AI Bot] ◄── Auto-invite bot
  │   └─ Returns: meet_link, event_id
  │
  ▼
User Calls API
  │
  ├─► POST /api/meet-interview/start
  │   └─ Body: { interview_id, meet_url, candidate_name, job_title }
  │
  ▼
Bot Authenticates
  │
  ├─► GoogleMeetAuth.initialize()
  │   ├─ Check cached session (meet_bot_sessions/)
  │   ├─ If expired: Re-authenticate with Google
  │   └─ Save session (7-day TTL)
  │
  ▼
Bot Joins Meeting
  │
  ├─► MeetBotJoiner.join_meeting()
  │   ├─ Navigate to meet_url
  │   ├─ Configure pre-join (camera OFF, mic ON)
  │   ├─ Click "Join now"
  │   ├─ Verify in meeting (check controls, NOT just URL)
  │   └─ Wait for candidate (min 2 participants, max 5 min)
  │
  ▼
Bot Initializes Audio
  │
  ├─► MeetAudioIntegration.initialize()
  │   ├─ Inject Web Audio API into page
  │   ├─ Setup AudioContext (16kHz sample rate)
  │   └─ Setup MediaRecorder (Opus codec, 128kbps)
  │
  ▼
Bot Loads Questions
  │
  ├─► QuestionRepository.get_questions_by_job_title(job_title)
  │   ├─ MongoDB query: { job_title: "Software Engineer" }
  │   └─ Returns: List of 5-10 questions
  │
  ▼
Bot Greets Candidate
  │
  ├─► TTSAgent.text_to_speech("Hello {name}! Welcome...")
  │   ├─ Deepgram Aura API call
  │   └─ Returns: Audio bytes (MP3/WAV)
  │
  ├─► MeetAudioIntegration.play_tts_audio(greeting_audio)
  │   ├─ Decode Base64
  │   ├─ Create AudioBuffer
  │   └─ Play through virtual microphone in Meet
  │
  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Q&A LOOP (For Each Question)                        │
└─────────────────────────────────────────────────────────────────────────────┘
  │
  ├─► [ASK QUESTION]
  │   ├─ TTSAgent.text_to_speech(question)
  │   │   └─► Deepgram Aura API ──► Audio bytes
  │   └─ MeetAudioIntegration.play_tts_audio(question_audio)
  │       └─► Play in Google Meet
  │
  ├─► [RECORD ANSWER]
  │   ├─ MeetAudioIntegration.start_recording_candidate()
  │   │   ├─ Get Meet audio stream (getUserMedia API)
  │   │   └─ MediaRecorder.start()
  │   │
  │   ├─ MeetAudioIntegration.wait_for_silence(duration=3.0, threshold=-40dB)
  │   │   ├─ Analyze audio level every 100ms
  │   │   └─ Detect 3 seconds of silence
  │   │
  │   └─ MeetAudioIntegration.stop_recording()
  │       └─► Returns: List of audio chunks (Base64 encoded)
  │
  ├─► [TRANSCRIBE ANSWER]
  │   ├─ Combine audio chunks → single byte stream
  │   └─ AudioTranscriptionAgent.transcribe(audio_data)
  │       └─► Groq Whisper API (whisper-large-v3)
  │           └─► Returns: "I have 5 years of experience..."
  │
  ├─► [ANALYZE ANSWER]
  │   ├─ Prompt: "Question: {Q}\nAnswer: {A}\nScore (0-10), Feedback, Strengths, Improvements"
  │   └─ Groq.chat.completions.create(model="llama-3.3-70b-versatile")
  │       └─► Returns: { score: 8, feedback: "...", strengths: [...], improvements: [...] }
  │
  ├─► [SAVE Q&A PAIR]
  │   ├─ qa_history.append({ question, answer, score, feedback, timestamp })
  │   └─ QARepository.save_qa_pair(interview_id, ...)
  │       └─► MongoDB.qa_pairs.insertOne(...)
  │
  └─► [REPEAT for next question]
  │
  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          END OF Q&A LOOP                                     │
└─────────────────────────────────────────────────────────────────────────────┘
  │
  ├─► [CALCULATE OVERALL SCORE]
  │   └─ overall_score = average(all question scores)
  │
  ├─► [CLOSE INTERVIEW]
  │   ├─ TTSAgent.text_to_speech("Thank you {name}! Interview complete...")
  │   └─ MeetAudioIntegration.play_tts_audio(closing)
  │
  ├─► [LEAVE MEETING]
  │   ├─ MeetBotJoiner.leave_meeting()
  │   │   ├─ Click "Leave call" button
  │   │   └─ Wait for meeting to close
  │   └─ GoogleMeetAuth.close()
  │       └─ Browser closes
  │
  ├─► [SAVE FINAL RESULTS]
  │   └─ InterviewRepository.update_interview_status()
  │       └─► MongoDB.interviews.updateOne({
  │           interview_id,
  │           status: "completed",
  │           overall_score: 8.5,
  │           qa_data: qa_history,
  │           completed_at: "2026-02-19T14:30:00Z"
  │         })
  │
  └─► [RETURN RESULTS TO API]
      └─ API Response: {
          success: true,
          overall_score: 8.5,
          qa_history: [...],
          completed_at: "..."
        }


┌───────────────────────────────────────────────────────────────────────────────┐
│                          6. FILE DEPENDENCY TREE                               │
└───────────────────────────────────────────────────────────────────────────────┘

main.py
  └─ interview_orchestrator.py
      ├─ meet_bot_launcher.py
      │   └─ Playwright (external)
      │
      ├─ meet_bot_joiner.py
      │   └─ Playwright Page (from launcher)
      │
      ├─ meet_audio_integration.py
      │   └─ Playwright Page (from launcher)
      │
      ├─ langgraph_agents/tts_agent.py
      │   ├─ Deepgram SDK (external)
      │   └─ mcp/context_manager.py
      │
      ├─ langgraph_agents/audio_transcription_agent.py
      │   ├─ Groq SDK (external)
      │   └─ mcp/cache_manager.py
      │
      ├─ repositories/interview_repository.py
      │   └─ db/mongo_client.py
      │
      ├─ repositories/question_repository.py
      │   └─ db/mongo_client.py
      │
      └─ repositories/qa_repository.py
          └─ db/mongo_client.py


┌───────────────────────────────────────────────────────────────────────────────┐
│                         7. CONFIGURATION FLOW                                  │
└───────────────────────────────────────────────────────────────────────────────┘

.env File
  ├─ MEET_BOT_EMAIL=airecruiterbot@gmail.com
  ├─ MEET_BOT_PASSWORD=qwhk mrxo zgja vnog
  ├─ DEEPGRAM_API_KEY=120a5c4c0fa02f4478ffa6ed1aee18d6ea46de0e
  ├─ GROQ_API_KEY=your_groq_api_key
  └─ MONGODB_URI=mongodb://localhost:27017/resumate
      │
      ▼
meet_bot_config.py (Pydantic BaseModel)
  ├─ Validates environment variables
  ├─ Sets defaults (headless_mode, timeouts, audio settings)
  └─ Exports: GoogleMeetBotConfig instance
      │
      ▼
interview_orchestrator.py
  ├─ Reads config from meet_bot_config
  └─ Passes to components:
      ├─ GoogleMeetAuth(email, password, headless)
      ├─ TTSAgent(api_key=DEEPGRAM_API_KEY)
      ├─ AudioTranscriptionAgent(api_key=GROQ_API_KEY)
      └─ MongoDB(uri=MONGODB_URI)


┌───────────────────────────────────────────────────────────────────────────────┐
│                          8. ERROR HANDLING FLOW                                │
└───────────────────────────────────────────────────────────────────────────────┘

Error Detected
  │
  ├─ Authentication Error
  │   ├─ GoogleMeetAuth.login() fails
  │   └─ Solution: Delete meet_bot_sessions/, re-authenticate
  │
  ├─ Join Meeting Error
  │   ├─ MeetBotJoiner.join_meeting() returns False
  │   ├─ Check: Rejection text in page
  │   └─ Solution: Invite bot OR enable "Quick access"
  │
  ├─ Audio Recording Error
  │   ├─ MeetAudioIntegration.stop_recording() returns empty chunks
  │   └─ Solution: Check candidate's microphone, verify audio permissions
  │
  ├─ Transcription Error
  │   ├─ AudioTranscriptionAgent.transcribe() fails
  │   └─ Solution: Check audio format, verify Groq API key
  │
  ├─ LLM Analysis Error
  │   ├─ Groq.chat.completions.create() fails
  │   └─ Solution: Check API quota, verify prompt format
  │
  └─ Database Error
      ├─ MongoDB connection fails
      └─ Solution: Check MongoDB URI, verify database running
          │
          ▼
      Error Handler (in orchestrator)
          ├─ Log error with full stack trace
          ├─ Update interview status to "failed"
          ├─ Save error details to MongoDB
          ├─ Leave meeting gracefully
          └─ Return error to API caller


┌───────────────────────────────────────────────────────────────────────────────┐
│                         9. TESTING WORKFLOW                                    │
└───────────────────────────────────────────────────────────────────────────────┘

Developer Runs Test
  │
  ├─► python test_complete_meet_interview.py
  │
  ├─ Step 1: Create Meeting
  │   ├─ GoogleCalendarService.create_interview_meeting()
  │   ├─ Returns: meet_link, event_id
  │   └─ Bot auto-invited to attendees ✅
  │
  ├─ Step 2: User Confirmation
  │   ├─ Displays Meet link
  │   ├─ Asks: "Join the meeting from your browser?"
  │   └─ User joins and clicks "Ready"
  │
  ├─ Step 3: Start Interview Bot
  │   ├─ POST /api/meet-interview/start
  │   └─ Orchestrator.conduct_interview() begins
  │
  ├─ Step 4: Monitor Progress (Real-time logs)
  │   ├─ "📞 Joining Google Meet..."
  │   ├─ "✅ Successfully joined meeting"
  │   ├─ "👋 Greeting candidate..."
  │   ├─ "💬 Question 1/5: Tell me about yourself..."
  │   ├─ "🎙️ Recording answer..."
  │   ├─ "🔄 Transcribing..."
  │   ├─ "🧠 Analyzing... (Score: 8/10)"
  │   └─ [Repeat for all questions]
  │
  ├─ Step 5: Interview Completes
  │   ├─ "👋 Closing interview..."
  │   ├─ "🚪 Leaving meeting..."
  │   └─ "📊 Results saved to MongoDB"
  │
  └─ Step 6: Display Results
      ├─ Overall Score: 8.5/10
      ├─ Questions: 5
      ├─ Answered: 5
      └─ Q&A History with scores and feedback


┌───────────────────────────────────────────────────────────────────────────────┐
│                           END OF ARCHITECTURE                                  │
└───────────────────────────────────────────────────────────────────────────────┘

Legend:
  ──► Direct function call
  ═══► External API call
  ├─  Sub-component
  └─  Terminal node
  ▼   Flow direction
  ✅  Success state
  ❌  Error state
