"""
MongoDB Database Models/Schemas

Purpose: Define structure for all collections in the database
Features:
- Schema validation
- Default values
- Timestamp management
- Data type definitions
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum


class UserRole(str, Enum):
    """User roles in the system"""
    HR = "hr"
    EMPLOYEE = "employee"
    ADMIN = "admin"


class InterviewStatus(str, Enum):
    """Interview status"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class CandidateStatus(str, Enum):
    """Candidate application status"""
    PENDING = "pending"
    SCREENING = "screening"
    SELECTED = "selected"
    REJECTED = "rejected"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    OFFER_SENT = "offer_sent"
    HIRED = "hired"


# Collection: users
USERS_SCHEMA = {
    "email": str,  # Required, unique
    "password_hash": str,  # Bcrypt hashed password
    "name": str,  # Full name
    "role": str,  # UserRole: hr, employee, admin
    "firebase_uid": Optional[str],  # Firebase user ID (for migration)
    "company": Optional[str],  # Company name (for HR)
    "profile_image": Optional[str],  # URL to profile image
    "created_at": datetime,
    "updated_at": datetime,
    "last_login": Optional[datetime],
    "is_active": bool,  # Account status
    "metadata": Dict[str, Any]  # Additional user data
}

# Collection: resumes
RESUMES_SCHEMA = {
    "candidate_email": str,  # Required
    "candidate_name": str,
    "file_name": str,  # Original filename
    "file_path": str,  # Storage path or URL
    "file_size": int,  # File size in bytes
    "extracted_text": str,  # Extracted resume text
    "structured_data": {  # Parsed resume data
        "skills": List[str],
        "years_experience": Optional[int],
        "education_level": Optional[str],
        "certifications": List[str],
        "email": Optional[str],
        "phone": Optional[str],
        "linkedin": Optional[str],
        "github": Optional[str]
    },
    "uploaded_by": str,  # User email who uploaded
    "uploaded_at": datetime,
    "updated_at": datetime,
    "metadata": Dict[str, Any]
}

# Collection: job_descriptions
JOB_DESCRIPTIONS_SCHEMA = {
    "job_id": str,  # Unique job ID
    "title": str,  # Job title
    "description": str,  # Full job description
    "required_skills": List[str],  # List of required skills
    "preferred_skills": List[str],  # List of preferred skills
    "experience_min": Optional[int],  # Minimum years of experience
    "experience_max": Optional[int],  # Maximum years of experience
    "education_level": Optional[str],  # Required education
    "job_level": str,  # Entry-level, Mid-level, Senior, Executive
    "industry": str,  # Industry type
    "location": str,  # Job location
    "remote_ok": bool,  # Remote work allowed
    "salary_min": Optional[float],  # Minimum salary
    "salary_max": Optional[float],  # Maximum salary
    "created_by": str,  # HR email who created
    "created_at": datetime,
    "updated_at": datetime,
    "is_active": bool,  # Job is open/closed
    "metadata": Dict[str, Any]
}

# Collection: selected_candidates
SELECTED_CANDIDATES_SCHEMA = {
    "candidate_email": str,
    "candidate_name": str,
    "job_id": str,  # Reference to job_description
    "resume_id": str,  # Reference to resume
    "match_score": float,  # ATS score (0-100)
    "matching_skills": List[str],
    "missing_skills": List[str],
    "strengths": List[str],
    "improvement_areas": List[str],
    "selected_by": str,  # HR email
    "selected_at": datetime,
    "status": str,  # CandidateStatus
    "interview_link": Optional[str],  # Interview room link
    "interview_scheduled_at": Optional[datetime],
    "notes": Optional[str],  # HR notes
    "metadata": Dict[str, Any]
}

# Collection: rejected_candidates
REJECTED_CANDIDATES_SCHEMA = {
    "candidate_email": str,
    "candidate_name": str,
    "job_id": str,
    "resume_id": str,
    "match_score": float,
    "rejection_reason": str,  # Auto-reject or manual
    "missing_skills": List[str],
    "rejected_by": str,  # HR email or "system"
    "rejected_at": datetime,
    "feedback_sent": bool,  # Whether rejection email was sent
    "metadata": Dict[str, Any]
}

# Collection: analysis_results
ANALYSIS_RESULTS_SCHEMA = {
    "resume_id": str,  # Reference to resume
    "job_id": str,  # Reference to job
    "candidate_email": str,
    "match_score": float,  # Overall match score (0-100)
    "skill_match_score": float,  # Skills match (0-100)
    "experience_score": float,  # Experience match (0-100)
    "education_score": float,  # Education match (0-100)
    "matching_skills": List[str],
    "missing_skills": List[str],
    "strengths": List[str],
    "areas_for_improvement": List[str],
    "detailed_analysis": Dict[str, Any],  # LLM-generated analysis
    "analyzed_at": datetime,
    "analyzed_by": str,  # System or user email
    "processing_time": float,  # Time taken in seconds
    "tokens_used": Optional[int],  # LLM tokens consumed
    "metadata": Dict[str, Any]
}

# Collection: interviews
INTERVIEWS_SCHEMA = {
    "interview_id": str,  # Unique interview ID
    "room_id": str,  # Meeting room ID
    "interview_link": str,  # Full interview link
    "candidate_email": str,
    "candidate_name": str,
    "job_id": str,
    "resume_id": str,
    "interviewer": str,  # HR or "AI Bot"
    "status": str,  # InterviewStatus
    "scheduled_at": datetime,
    "started_at": Optional[datetime],
    "completed_at": Optional[datetime],
    "duration_minutes": Optional[int],
    "recording_url": Optional[str],  # Video recording link
    "transcript_id": Optional[str],  # Reference to interview_transcripts
    "join_count": int,  # Number of times joined
    "ai_enabled": bool,  # Whether AI interviewer was used
    "overall_score": Optional[float],  # Final interview score
    "technical_score": Optional[float],
    "communication_score": Optional[float],
    "problem_solving_score": Optional[float],
    "created_at": datetime,
    "updated_at": datetime,
    "metadata": Dict[str, Any]
}

# Collection: email_logs
EMAIL_LOGS_SCHEMA = {
    "email_id": str,  # Unique email ID
    "to_email": str,  # Recipient
    "subject": str,  # Email subject
    "body": str,  # Email body
    "email_type": str,  # "acceptance", "rejection", "interview_invite", "reminder"
    "sent_by": str,  # User who triggered email
    "sent_at": datetime,
    "status": str,  # "sent", "failed", "queued"
    "error_message": Optional[str],  # If failed
    "candidate_id": Optional[str],
    "job_id": Optional[str],
    "interview_id": Optional[str],
    "metadata": Dict[str, Any]
}

# Collection: interview_questions
INTERVIEW_QUESTIONS_SCHEMA = {
    "question_id": str,  # Unique question ID
    "interview_id": str,  # Reference to interviews
    "questions": [  # Array of questions with details
        {
            "question_number": int,
            "question_text": str,
            "question_type": str,  # "technical", "behavioral", "situational"
            "difficulty": str,  # "easy", "medium", "hard"
            "asked_at": datetime,
            "time_limit_seconds": Optional[int]
        }
    ],
    "job_id": str,
    "generated_by": str,  # "AI" or user email
    "generated_at": datetime,
    "metadata": Dict[str, Any]
}

# Collection: resume_analysis_results (detailed AI analysis)
RESUME_ANALYSIS_RESULTS_SCHEMA = {
    "analysis_id": str,  # Unique analysis ID
    "resume_id": str,
    "job_id": str,
    "candidate_email": str,
    "analysis_type": str,  # "initial_screening", "detailed_review", "comparison"
    "llm_model": str,  # Model used (e.g., "llama-3.3-70b-versatile")
    "extracted_skills": List[str],
    "experience_summary": str,
    "education_summary": str,
    "key_achievements": List[str],
    "red_flags": List[str],  # Potential concerns
    "recommendations": List[str],
    "overall_rating": str,  # "excellent", "good", "average", "poor"
    "confidence_score": float,  # 0-1
    "analysis_text": str,  # Full LLM response
    "tokens_used": int,
    "processing_time": float,
    "analyzed_at": datetime,
    "metadata": Dict[str, Any]
}

# Collection: improved_resumes
IMPROVED_RESUMES_SCHEMA = {
    "improved_resume_id": str,  # Unique ID
    "original_resume_id": str,  # Reference to original
    "candidate_email": str,
    "target_job_id": Optional[str],  # Job being targeted
    "target_role": str,  # Desired role
    "original_text": str,  # Original resume text
    "improved_text": str,  # AI-improved resume
    "improvements_made": List[str],  # List of changes
    "skills_highlighted": List[str],
    "sections_enhanced": List[str],  # e.g., ["summary", "experience"]
    "improvement_score": float,  # How much better (0-100)
    "generated_by": str,  # LLM model
    "generated_at": datetime,
    "tokens_used": int,
    "downloaded": bool,  # Whether user downloaded
    "downloaded_at": Optional[datetime],
    "metadata": Dict[str, Any]
}

# Collection: qa_sessions (Q&A about resumes)
QA_SESSIONS_SCHEMA = {
    "qa_id": str,  # Unique Q&A session ID
    "resume_id": str,
    "user_email": str,  # Who asked questions
    "questions": [  # Array of questions and answers
        {
            "question_number": int,
            "question": str,
            "answer": str,
            "question_type": str,  # "skills", "experience", "education", "general"
            "confidence": float,  # Answer confidence (0-1)
            "asked_at": datetime,
            "tokens_used": int,
            "relevant_sections": List[str]  # Which resume sections were used
        }
    ],
    "total_questions": int,
    "session_started_at": datetime,
    "session_ended_at": Optional[datetime],
    "total_tokens_used": int,
    "metadata": Dict[str, Any]
}


# Helper function to get default document
def get_default_document(collection_name: str, **kwargs) -> Dict[str, Any]:
    """
    Get a default document structure for a collection
    
    Args:
        collection_name: Name of the collection
        **kwargs: Field values to override defaults
    
    Returns:
        Document dictionary with defaults
    """
    now = datetime.utcnow()
    
    defaults = {
        "created_at": now,
        "updated_at": now,
        "metadata": {}
    }
    
    # Merge with provided kwargs
    defaults.update(kwargs)
    
    return defaults


# Collection: transcriptions (STT audio transcriptions)
TRANSCRIPTIONS_SCHEMA = {
    "transcription_id": str,  # Unique transcription ID
    "session_id": str,  # Reference to meeting session
    "meeting_id": Optional[str],  # Reference to meetings collection
    "interview_id": Optional[str],  # Reference to interviews
    "chunk_id": str,  # Audio chunk identifier
    "audio_chunk_number": int,  # Sequence number
    
    # Audio metadata
    "audio_format": str,  # mp3, wav, webm, etc.
    "audio_duration": Optional[float],  # Duration in seconds
    "audio_size_bytes": Optional[int],  # File size
    
    # Transcription data
    "raw_transcription": str,  # Original Whisper output
    "cleaned_transcription": str,  # Cleaned text
    "language_detected": str,  # Detected language
    "confidence_score": float,  # Transcription confidence (0-1)
    
    # Analysis results
    "sentiment": str,  # positive, negative, neutral, mixed
    "speaker_detected": Optional[str],  # Speaker identification
    "key_points": List[str],  # Extracted key points
    "technical_terms": List[str],  # Technical terms found
    "questions_asked": List[str],  # Questions detected
    "answers_given": List[str],  # Answers detected
    
    # Processing details
    "model": str,  # Model used (whisper-large-v3)
    "llm_model": Optional[str],  # LLM for analysis
    "workflow": str,  # langgraph, direct, etc.
    "mcp_optimized": bool,  # MCP optimization applied
    "processing_time_ms": float,  # Processing time
    "tokens_used": Optional[int],  # Tokens consumed
    
    # Context
    "question_context": Optional[str],  # Interview question context
    "interview_stage": Optional[str],  # Stage in interview
    
    # Timestamps
    "transcribed_at": datetime,
    "analyzed_at": Optional[datetime],
    "created_at": datetime,
    "updated_at": datetime,
    
    # Error tracking
    "has_errors": bool,
    "errors": List[Dict[str, Any]],  # Error log
    
    "metadata": Dict[str, Any]
}

# Collection: meetings (Virtual meeting sessions)
MEETINGS_SCHEMA = {
    "meeting_id": str,  # Unique meeting ID
    "session_id": str,  # Session identifier for tracking
    "room_id": Optional[str],  # Virtual room ID
    
    # Meeting details
    "meeting_title": str,  # Meeting title
    "meeting_type": str,  # "interview", "screening", "followup", "other"
    "meeting_link": str,  # Google Meet or other platform link
    "meeting_platform": str,  # "google_meet", "zoom", "teams", etc.
    
    # Participants
    "host_email": str,  # Meeting host
    "host_name": str,
    "participants": List[Dict[str, Any]],  # List of participants with roles
    "expected_participants": int,
    "actual_participants": int,
    
    # Related entities
    "interview_id": Optional[str],  # Reference to interviews
    "candidate_email": Optional[str],  # Candidate email
    "candidate_name": Optional[str],  # Candidate name
    "job_id": Optional[str],  # Reference to job
    
    # Meeting status
    "status": str,  # "scheduled", "in_progress", "completed", "cancelled", "failed"
    "is_recording": bool,  # Recording enabled
    "recording_enabled": bool,  # Recording capability
    "recording_url": Optional[str],  # Recording storage link
    
    # Timing
    "scheduled_at": datetime,  # Scheduled start time
    "started_at": Optional[datetime],  # Actual start time
    "ended_at": Optional[datetime],  # Actual end time
    "duration_minutes": Optional[int],  # Actual duration
    "expected_duration_minutes": int,  # Expected duration
    
    # AI Features
    "ai_bot_enabled": bool,  # AI bot participation
    "ai_bot_name": Optional[str],  # Bot name
    "ai_bot_email": Optional[str],  # Bot email
    "bot_id": Optional[str],  # Reference to meeting_bots collection
    "bot_status": Optional[str],  # Bot status: "pending", "joined", "active", "left"
    "bot_join_attempts": int,  # Number of bot join attempts
    "bot_joined_at": Optional[datetime],  # When bot joined
    "bot_left_at": Optional[datetime],  # When bot left
    "bot_join_time": Optional[datetime],  # Bot join timestamp
    "bot_leave_time": Optional[datetime],  # Bot leave timestamp
    
    # Transcription (STT)
    "transcription_enabled": bool,  # STT enabled
    "total_transcriptions": int,  # Number of transcription chunks
    "transcription_ids": List[str],  # List of transcription IDs
    "full_transcript": Optional[str],  # Combined transcript
    "stt_enabled": bool,  # STT service enabled
    
    # Text-to-Speech (TTS)
    "tts_enabled": bool,  # TTS service enabled
    "tts_audio_ids": List[str],  # List of TTS audio IDs
    "total_tts_audio": int,  # Number of TTS audio generated
    "last_tts_at": Optional[datetime],  # Last TTS generation time
    "voice_profile": Optional[str],  # Voice profile used (professional_female, etc.)
    
    # Analytics
    "total_audio_chunks": int,  # Audio chunks received
    "total_participants_joined": int,  # Join count
    "participant_join_times": List[Dict[str, Any]],  # Join/leave log
    "average_sentiment": Optional[str],  # Overall sentiment
    "key_topics": List[str],  # Main topics discussed
    "questions_count": int,  # Number of questions
    "technical_score": Optional[float],  # Technical assessment
    "communication_score": Optional[float],  # Communication score
    
    # Calendar integration
    "calendar_event_id": Optional[str],  # Google Calendar event ID
    "calendar_link": Optional[str],  # Calendar event link
    "reminder_sent": bool,  # Reminder email sent
    "reminder_sent_at": Optional[datetime],
    
    # Security
    "access_code": Optional[str],  # Meeting access code
    "is_private": bool,  # Private meeting
    "allowed_domains": List[str],  # Allowed email domains
    
    # Timestamps
    "created_at": datetime,
    "updated_at": datetime,
    "last_activity_at": Optional[datetime],
    
    # Error tracking
    "join_errors": List[Dict[str, Any]],  # Join error log
    "recording_errors": List[Dict[str, Any]],  # Recording error log
    "has_errors": bool,
    
    "metadata": Dict[str, Any]
}

# Collection: tts_audio
TTS_AUDIO_SCHEMA = {
    "tts_id": str,  # Unique TTS ID
    "session_id": str,  # Session identifier
    "meeting_id": Optional[str],  # Reference to meeting
    "interview_id": Optional[str],  # Reference to interview
    
    # Text input
    "text": str,  # Text to convert to speech
    "text_type": str,  # "intro", "question", "followup", "closing", "feedback"
    "character_count": int,  # Text length
    "word_count": int,  # Word count
    
    # Voice configuration
    "voice_id": str,  # ElevenLabs voice ID
    "voice_name": str,  # Voice name (Sarah, Adam, etc.)
    "voice_profile": str,  # "professional_female", "professional_male", etc.
    "stability": float,  # Voice stability (0.0-1.0)
    "similarity_boost": float,  # Voice similarity (0.0-1.0)
    "style": float,  # Voice style (0.0-1.0)
    "use_speaker_boost": bool,  # Speaker boost enabled
    
    # Audio settings
    "model_id": str,  # ElevenLabs model (eleven_multilingual_v2, etc.)
    "output_format": str,  # "mp3_44100_128", "pcm_16000", etc.
    
    # Audio output
    "audio_base64": Optional[str],  # Base64 encoded audio
    "audio_url": Optional[str],  # Storage URL for audio file
    "audio_duration_seconds": float,  # Audio duration
    "audio_size_bytes": int,  # Audio file size
    
    # Streaming
    "is_streaming": bool,  # Streaming mode enabled
    "chunks_count": int,  # Number of chunks streamed
    
    # Context
    "conversation_context": str,  # Context for speech generation
    "emotion": str,  # "neutral", "encouraging", "professional", "empathetic"
    
    # Performance
    "processing_time_ms": int,  # Processing time in milliseconds
    
    # Status
    "processing_status": str,  # "pending", "processing", "completed", "failed"
    "success": bool,  # Generation successful
    "errors": List[Dict[str, str]],  # Error log
    "has_errors": bool,
    
    # Timestamps
    "created_at": datetime,
    "started_at": datetime,
    "completed_at": Optional[datetime],
    "updated_at": datetime,
    
    "metadata": Dict[str, Any]
}

# Collection: meeting_bots
MEETING_BOTS_SCHEMA = {
    "bot_id": str,  # Unique bot ID
    "session_id": str,  # Session identifier
    "meeting_id": str,  # Reference to meeting
    "interview_id": Optional[str],  # Reference to interview
    
    # Meeting details
    "meeting_link": str,  # Meeting URL
    "meeting_platform": str,  # "zoom", "google_meet", "teams"
    "meeting_title": str,  # Meeting title
    "scheduled_start_time": Optional[datetime],  # Scheduled start
    
    # Bot configuration
    "bot_name": str,  # Bot display name
    "bot_email": str,  # Bot email address
    "bot_role": str,  # "interviewer", "listener", "recorder"
    "auto_record": bool,  # Auto-record enabled
    "auto_transcribe": bool,  # Auto-transcribe enabled
    "auto_tts": bool,  # Auto-TTS enabled
    
    # Bot status
    "bot_status": str,  # "pending", "joining", "joined", "active", "leaving", "left", "error"
    "join_method": str,  # "browser_automation", "api", "manual"
    "browser_type": str,  # "chrome", "firefox", "edge"
    "browser_session_id": Optional[str],  # Browser session ID
    "browser_process_id": Optional[int],  # Browser process ID
    "chrome_tab_id": Optional[int],  # Chrome tab ID
    
    # Timing
    "join_time": Optional[datetime],  # When bot joined
    "leave_time": Optional[datetime],  # When bot left
    "duration_minutes": int,  # Actual duration
    "max_duration_minutes": int,  # Max allowed duration
    "auto_leave_after_silence_minutes": int,  # Auto-leave threshold
    
    # Participants
    "expected_participants": List[str],  # Expected participant emails
    "actual_participants": List[Dict[str, Any]],  # Actual participants
    "participant_count": int,  # Total participants
    "host_name": Optional[str],  # Meeting host name
    
    # Features enabled
    "stt_enabled": bool,  # STT active
    "tts_enabled": bool,  # TTS active
    "recording_enabled": bool,  # Recording active
    "screen_sharing_enabled": bool,  # Screen sharing active
    
    # Audio/Video settings
    "microphone_enabled": bool,  # Microphone on
    "camera_enabled": bool,  # Camera on
    "speaker_enabled": bool,  # Speakers on
    "audio_input_device": Optional[str],  # Audio input device
    "audio_output_device": Optional[str],  # Audio output device
    
    # Interview coordination
    "interview_active": bool,  # Interview in progress
    "current_speaker": Optional[str],  # Current speaker
    "last_speech_time": Optional[datetime],  # Last speech timestamp
    "silence_duration_seconds": int,  # Silence duration
    
    # Security
    "meeting_password": Optional[str],  # Meeting password
    "waiting_room_enabled": bool,  # Waiting room enabled
    "host_approval_required": bool,  # Requires host approval
    
    # Analytics
    "total_speech_duration_seconds": int,  # Total speech time
    "bot_spoke_count": int,  # Bot speech count
    "candidate_spoke_count": int,  # Candidate speech count
    "questions_asked": int,  # Questions asked
    "answers_received": int,  # Answers received
    
    # Processing status
    "processing_status": str,  # "initializing", "active", "completed", "failed"
    "success": bool,  # Bot operation successful
    "errors": List[Dict[str, str]],  # Error log
    "has_errors": bool,
    
    # Timestamps
    "created_at": datetime,
    "started_at": datetime,
    "completed_at": Optional[datetime],
    "updated_at": datetime,
    
    "metadata": Dict[str, Any]
}

# Collection: session_tokens (JWT authentication tokens)
SESSION_TOKENS_SCHEMA = {
    "session_id": str,
    "interview_id": str,
    "candidate_name": str,
    "job_description": str,
    "jwt_token": str,
    "token_hash": str,
    "status": str,
    "revoked": bool,
    "permissions": Dict[str, bool],
    "created_at": str,
    "expires_at": str,
    "metadata": Dict[str, Any]
}

# Collection: interview_results (Post-interview analytics)
INTERVIEW_RESULTS_SCHEMA = {
    "session_id": str,
    "interview_id": Optional[str],
    "orchestration_id": Optional[str],
    "candidate_email": Optional[str],
    "candidate_name": Optional[str],
    "job_id": Optional[str],
    "summary": str,
    "recommendation": str,
    "scores": Dict[str, float],
    "strengths": List[str],
    "weaknesses": List[str],
    "technical_assessment": Dict[str, Any],
    "communication_assessment": Dict[str, Any],
    "behavioral_assessment": Optional[Dict[str, Any]],
    "transcript_analyzed": bool,
    "total_questions": int,
    "total_answers": int,
    "llm_model": Optional[str],
    "tokens_used": Optional[int],
    "processing_time": Optional[float],
    "analyzed_at": datetime,
    "created_at": datetime,
    "updated_at": datetime,
    "errors": List[str],
    "has_errors": bool,
    "metadata": Dict[str, Any]
}

# Collection: orchestration_sessions (Real-time STT->LLM->TTS)
ORCHESTRATION_SESSIONS_SCHEMA = {
    "orchestration_id": str,
    "session_id": str,
    "meeting_id": Optional[str],
    "interview_id": Optional[str],
    "candidate_name": Optional[str],
    "job_description": Optional[str],
    "pipeline_config": Dict[str, Any],
    "status": str,
    "final_status": str,
    "total_turns": int,
    "successful_turns": int,
    "failed_turns": int,
    "success_rate": float,
    "quality_score": float,
    "avg_latency_ms": float,
    "total_retries": int,
    "transcript_chunks": List[str],
    "tts_audio_chunks": List[str],
    "conversation_history": List[Dict[str, Any]],
    "duration_seconds": float,
    "total_tokens_used": Optional[int],
    "total_audio_processed_seconds": float,
    "created_at": datetime,
    "started_at": Optional[datetime],
    "completed_at": Optional[datetime],
    "updated_at": datetime,
    "errors": List[Dict[str, Any]],
    "interruptions": int,
    "has_errors": bool,
    "transcript_archived": bool,
    "metrics_persisted": bool,
    "graceful_shutdown": bool,
    "metadata": Dict[str, Any]
}


# Collection names constants
class Collections:
    """Collection name constants"""
    USERS = "users"
    RESUMES = "resumes"
    JOB_DESCRIPTIONS = "job_descriptions"
    SELECTED_CANDIDATES = "selected_candidates"
    REJECTED_CANDIDATES = "rejected_candidates"
    ANALYSIS_RESULTS = "analysis_results"
    INTERVIEWS = "interviews"
    EMAIL_LOGS = "email_logs"
    INTERVIEW_QUESTIONS = "interview_questions"
    RESUME_ANALYSIS_RESULTS = "resume_analysis_results"
    IMPROVED_RESUMES = "improved_resumes"
    QA_SESSIONS = "qa_sessions"
    TRANSCRIPTIONS = "transcriptions"  # STT transcriptions
    MEETINGS = "meetings"  # Virtual meetings
    TTS_AUDIO = "tts_audio"  # TTS audio files
    MEETING_BOTS = "meeting_bots"  # Meeting bot sessions
    SESSION_TOKENS = "session_tokens"  # JWT authentication tokens
    INTERVIEW_RESULTS = "interview_results"  # Post-interview analytics
    ORCHESTRATION_SESSIONS = "orchestration_sessions"  # Real-time orchestration


# All collections list
ALL_COLLECTIONS = [
    Collections.USERS,
    Collections.RESUMES,
    Collections.JOB_DESCRIPTIONS,
    Collections.SELECTED_CANDIDATES,
    Collections.REJECTED_CANDIDATES,
    Collections.ANALYSIS_RESULTS,
    Collections.INTERVIEWS,
    Collections.EMAIL_LOGS,
    Collections.INTERVIEW_QUESTIONS,
    Collections.RESUME_ANALYSIS_RESULTS,
    Collections.IMPROVED_RESUMES,
    Collections.QA_SESSIONS,
    Collections.TRANSCRIPTIONS,
    Collections.MEETINGS,
    Collections.TTS_AUDIO,
    Collections.MEETING_BOTS,
    Collections.SESSION_TOKENS,
    Collections.INTERVIEW_RESULTS,
    Collections.ORCHESTRATION_SESSIONS
]


if __name__ == "__main__":
    print("📋 Database Collections:")
    print("="*80)
    for i, collection in enumerate(ALL_COLLECTIONS, 1):
        print(f"{i}. {collection}")
    print("="*80)
    print(f"Total collections: {len(ALL_COLLECTIONS)}")
