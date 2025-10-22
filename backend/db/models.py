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
    "phone": Optional[str],  # Phone number
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
    Collections.QA_SESSIONS
]


if __name__ == "__main__":
    print("📋 Database Collections:")
    print("="*80)
    for i, collection in enumerate(ALL_COLLECTIONS, 1):
        print(f"{i}. {collection}")
    print("="*80)
    print(f"Total collections: {len(ALL_COLLECTIONS)}")
