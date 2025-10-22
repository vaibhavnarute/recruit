"""
MongoDB Service Layer - CRUD Operations

Purpose: High-level database operations for all collections
Features:
- Type-safe operations
- Error handling
- Logging
- Data validation
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError
from db.mongo_client import get_collection
from db.models import Collections
import bcrypt

logger = logging.getLogger(__name__)


class MongoDBService:
    """
    High-level MongoDB service for all database operations
    
    Why service layer:
    - Encapsulate database logic
    - Consistent error handling
    - Reusable operations
    - Easy to test and mock
    """
    
    # ==================== USER OPERATIONS ====================
    
    @staticmethod
    def create_user(email: str, password: str, name: str, role: str = "employee", **kwargs) -> Optional[Dict]:
        """
        Create a new user
        
        Args:
            email: User email (unique)
            password: Plain text password (will be hashed)
            name: Full name
            role: User role (hr, employee, admin)
            **kwargs: Additional user fields
        
        Returns:
            Created user document or None if failed
        """
        try:
            users: Collection = get_collection(Collections.USERS)
            
            # Check if user already exists
            if users.find_one({"email": email}):
                logger.warning(f"⚠️  User already exists: {email}")
                return None
            
            # Hash password
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            
            # Create user document
            user_doc = {
                "email": email,
                "password_hash": password_hash,
                "name": name,
                "role": role,
                "firebase_uid": kwargs.get("firebase_uid"),
                "company": kwargs.get("company"),
                "phone": kwargs.get("phone"),
                "profile_image": kwargs.get("profile_image"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "last_login": None,
                "is_active": True,
                "metadata": kwargs.get("metadata", {})
            }
            
            result = users.insert_one(user_doc)
            user_doc["_id"] = str(result.inserted_id)
            
            logger.info(f"✅ User created: {email} (role: {role})")
            return user_doc
            
        except DuplicateKeyError:
            logger.error(f"❌ Duplicate user: {email}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to create user: {str(e)}")
            return None
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[Dict]:
        """
        Authenticate user with email and password
        
        Args:
            email: User email
            password: Plain text password
        
        Returns:
            User document if authenticated, None otherwise
        """
        try:
            users: Collection = get_collection(Collections.USERS)
            user = users.find_one({"email": email})
            
            if not user:
                logger.warning(f"⚠️  User not found: {email}")
                return None
            
            if not user.get("is_active"):
                logger.warning(f"⚠️  User inactive: {email}")
                return None
            
            # Verify password
            if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                # Update last login
                users.update_one(
                    {"email": email},
                    {"$set": {"last_login": datetime.utcnow()}}
                )
                logger.info(f"✅ User authenticated: {email}")
                return user
            else:
                logger.warning(f"⚠️  Invalid password: {email}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Authentication failed: {str(e)}")
            return None
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            users: Collection = get_collection(Collections.USERS)
            return users.find_one({"email": email})
        except Exception as e:
            logger.error(f"❌ Failed to get user: {str(e)}")
            return None
    
    # ==================== RESUME OPERATIONS ====================
    
    @staticmethod
    def save_resume(
        candidate_email: str,
        candidate_name: str,
        file_name: str,
        file_path: str,
        extracted_text: str,
        structured_data: Dict,
        uploaded_by: str,
        **kwargs
    ) -> Optional[str]:
        """
        Save resume to database
        
        Returns:
            Resume ID if successful, None otherwise
        """
        try:
            resumes: Collection = get_collection(Collections.RESUMES)
            
            resume_doc = {
                "candidate_email": candidate_email,
                "candidate_name": candidate_name,
                "file_name": file_name,
                "file_path": file_path,
                "file_size": kwargs.get("file_size", 0),
                "extracted_text": extracted_text,
                "structured_data": structured_data,
                "uploaded_by": uploaded_by,
                "uploaded_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "metadata": kwargs.get("metadata", {})
            }
            
            result = resumes.insert_one(resume_doc)
            resume_id = str(result.inserted_id)
            
            logger.info(f"✅ Resume saved: {candidate_name} ({resume_id})")
            return resume_id
            
        except Exception as e:
            logger.error(f"❌ Failed to save resume: {str(e)}")
            return None
    
    @staticmethod
    def get_resumes_by_candidate(candidate_email: str) -> List[Dict]:
        """Get all resumes for a candidate"""
        try:
            resumes: Collection = get_collection(Collections.RESUMES)
            return list(resumes.find({"candidate_email": candidate_email}).sort("uploaded_at", -1))
        except Exception as e:
            logger.error(f"❌ Failed to get resumes: {str(e)}")
            return []
    
    # ==================== JOB DESCRIPTION OPERATIONS ====================
    
    @staticmethod
    def create_job(
        title: str,
        description: str,
        required_skills: List[str],
        created_by: str,
        **kwargs
    ) -> Optional[str]:
        """
        Create job description
        
        Returns:
            Job ID if successful
        """
        try:
            jobs: Collection = get_collection(Collections.JOB_DESCRIPTIONS)
            
            job_id = str(uuid.uuid4())[:8]
            
            job_doc = {
                "job_id": job_id,
                "title": title,
                "description": description,
                "required_skills": required_skills,
                "preferred_skills": kwargs.get("preferred_skills", []),
                "experience_min": kwargs.get("experience_min"),
                "experience_max": kwargs.get("experience_max"),
                "education_level": kwargs.get("education_level"),
                "job_level": kwargs.get("job_level", "Mid-level"),
                "industry": kwargs.get("industry", "Technology"),
                "location": kwargs.get("location", "Remote"),
                "remote_ok": kwargs.get("remote_ok", True),
                "salary_min": kwargs.get("salary_min"),
                "salary_max": kwargs.get("salary_max"),
                "created_by": created_by,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True,
                "metadata": kwargs.get("metadata", {})
            }
            
            jobs.insert_one(job_doc)
            logger.info(f"✅ Job created: {title} ({job_id})")
            return job_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create job: {str(e)}")
            return None
    
    @staticmethod
    def get_active_jobs() -> List[Dict]:
        """Get all active job descriptions"""
        try:
            jobs: Collection = get_collection(Collections.JOB_DESCRIPTIONS)
            return list(jobs.find({"is_active": True}).sort("created_at", -1))
        except Exception as e:
            logger.error(f"❌ Failed to get jobs: {str(e)}")
            return []
    
    # ==================== CANDIDATE OPERATIONS ====================
    
    @staticmethod
    def add_selected_candidate(
        candidate_email: str,
        candidate_name: str,
        job_id: str,
        resume_id: str,
        match_score: float,
        matching_skills: List[str],
        missing_skills: List[str],
        selected_by: str,
        **kwargs
    ) -> Optional[str]:
        """Add candidate to selected list"""
        try:
            selected: Collection = get_collection(Collections.SELECTED_CANDIDATES)
            
            candidate_doc = {
                "candidate_email": candidate_email,
                "candidate_name": candidate_name,
                "job_id": job_id,
                "resume_id": resume_id,
                "match_score": match_score,
                "matching_skills": matching_skills,
                "missing_skills": missing_skills,
                "strengths": kwargs.get("strengths", []),
                "improvement_areas": kwargs.get("improvement_areas", []),
                "selected_by": selected_by,
                "selected_at": datetime.utcnow(),
                "status": "selected",
                "interview_link": kwargs.get("interview_link"),
                "interview_scheduled_at": kwargs.get("interview_scheduled_at"),
                "notes": kwargs.get("notes"),
                "metadata": kwargs.get("metadata", {})
            }
            
            result = selected.insert_one(candidate_doc)
            logger.info(f"✅ Candidate selected: {candidate_name} (score: {match_score})")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to add selected candidate: {str(e)}")
            return None
    
    @staticmethod
    def add_rejected_candidate(
        candidate_email: str,
        candidate_name: str,
        job_id: str,
        resume_id: str,
        match_score: float,
        rejection_reason: str,
        rejected_by: str,
        **kwargs
    ) -> Optional[str]:
        """Add candidate to rejected list"""
        try:
            rejected: Collection = get_collection(Collections.REJECTED_CANDIDATES)
            
            candidate_doc = {
                "candidate_email": candidate_email,
                "candidate_name": candidate_name,
                "job_id": job_id,
                "resume_id": resume_id,
                "match_score": match_score,
                "rejection_reason": rejection_reason,
                "missing_skills": kwargs.get("missing_skills", []),
                "rejected_by": rejected_by,
                "rejected_at": datetime.utcnow(),
                "feedback_sent": False,
                "metadata": kwargs.get("metadata", {})
            }
            
            result = rejected.insert_one(candidate_doc)
            logger.info(f"✅ Candidate rejected: {candidate_name}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to add rejected candidate: {str(e)}")
            return None
    
    # ==================== ANALYSIS OPERATIONS ====================
    
    @staticmethod
    def save_analysis_result(
        resume_id: str,
        job_id: str,
        candidate_email: str,
        match_score: float,
        matching_skills: List[str],
        missing_skills: List[str],
        **kwargs
    ) -> Optional[str]:
        """Save resume analysis result"""
        try:
            analysis: Collection = get_collection(Collections.ANALYSIS_RESULTS)
            
            analysis_doc = {
                "resume_id": resume_id,
                "job_id": job_id,
                "candidate_email": candidate_email,
                "match_score": match_score,
                "skill_match_score": kwargs.get("skill_match_score", 0),
                "experience_score": kwargs.get("experience_score", 0),
                "education_score": kwargs.get("education_score", 0),
                "matching_skills": matching_skills,
                "missing_skills": missing_skills,
                "strengths": kwargs.get("strengths", []),
                "areas_for_improvement": kwargs.get("areas_for_improvement", []),
                "detailed_analysis": kwargs.get("detailed_analysis", {}),
                "analyzed_at": datetime.utcnow(),
                "analyzed_by": kwargs.get("analyzed_by", "system"),
                "processing_time": kwargs.get("processing_time", 0),
                "tokens_used": kwargs.get("tokens_used"),
                "metadata": kwargs.get("metadata", {})
            }
            
            result = analysis.insert_one(analysis_doc)
            logger.info(f"✅ Analysis saved for {candidate_email}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to save analysis: {str(e)}")
            return None
    
    # ==================== INTERVIEW OPERATIONS ====================
    
    @staticmethod
    def create_interview(
        candidate_email: str,
        candidate_name: str,
        job_id: str,
        resume_id: str,
        room_id: str,
        interview_link: str,
        scheduled_at: datetime,
        **kwargs
    ) -> Optional[str]:
        """Create interview session"""
        try:
            interviews: Collection = get_collection(Collections.INTERVIEWS)
            
            interview_id = str(uuid.uuid4())
            
            interview_doc = {
                "interview_id": interview_id,
                "room_id": room_id,
                "interview_link": interview_link,
                "candidate_email": candidate_email,
                "candidate_name": candidate_name,
                "job_id": job_id,
                "resume_id": resume_id,
                "interviewer": kwargs.get("interviewer", "AI Bot"),
                "status": "scheduled",
                "scheduled_at": scheduled_at,
                "started_at": None,
                "completed_at": None,
                "duration_minutes": None,
                "recording_url": None,
                "transcript_id": None,
                "join_count": 0,
                "ai_enabled": kwargs.get("ai_enabled", True),
                "overall_score": None,
                "technical_score": None,
                "communication_score": None,
                "problem_solving_score": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "metadata": kwargs.get("metadata", {})
            }
            
            interviews.insert_one(interview_doc)
            logger.info(f"✅ Interview created: {interview_id} for {candidate_name}")
            return interview_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create interview: {str(e)}")
            return None
    
    @staticmethod
    def get_interview_by_room_id(room_id: str) -> Optional[Dict]:
        """Get interview by room ID"""
        try:
            interviews: Collection = get_collection(Collections.INTERVIEWS)
            return interviews.find_one({"room_id": room_id})
        except Exception as e:
            logger.error(f"❌ Failed to get interview: {str(e)}")
            return None
    
    # ==================== EMAIL LOG OPERATIONS ====================
    
    @staticmethod
    def log_email(
        to_email: str,
        subject: str,
        body: str,
        email_type: str,
        sent_by: str,
        status: str = "sent",
        **kwargs
    ) -> Optional[str]:
        """Log sent email"""
        try:
            emails: Collection = get_collection(Collections.EMAIL_LOGS)
            
            email_id = str(uuid.uuid4())
            
            email_doc = {
                "email_id": email_id,
                "to_email": to_email,
                "subject": subject,
                "body": body,
                "email_type": email_type,
                "sent_by": sent_by,
                "sent_at": datetime.utcnow(),
                "status": status,
                "error_message": kwargs.get("error_message"),
                "candidate_id": kwargs.get("candidate_id"),
                "job_id": kwargs.get("job_id"),
                "interview_id": kwargs.get("interview_id"),
                "metadata": kwargs.get("metadata", {})
            }
            
            emails.insert_one(email_doc)
            logger.info(f"✅ Email logged: {email_type} to {to_email}")
            return email_id
            
        except Exception as e:
            logger.error(f"❌ Failed to log email: {str(e)}")
            return None
    
    # ==================== Q&A OPERATIONS ====================
    
    @staticmethod
    def create_qa_session(resume_id: str, user_email: str) -> Optional[str]:
        """Create Q&A session"""
        try:
            qa: Collection = get_collection(Collections.QA_SESSIONS)
            
            qa_id = str(uuid.uuid4())
            
            qa_doc = {
                "qa_id": qa_id,
                "resume_id": resume_id,
                "user_email": user_email,
                "questions": [],
                "total_questions": 0,
                "session_started_at": datetime.utcnow(),
                "session_ended_at": None,
                "total_tokens_used": 0,
                "metadata": {}
            }
            
            qa.insert_one(qa_doc)
            logger.info(f"✅ Q&A session created: {qa_id}")
            return qa_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create Q&A session: {str(e)}")
            return None
    
    @staticmethod
    def add_qa_question(
        qa_id: str,
        question: str,
        answer: str,
        question_type: str,
        confidence: float,
        tokens_used: int,
        relevant_sections: List[str]
    ) -> bool:
        """Add question to Q&A session"""
        try:
            qa: Collection = get_collection(Collections.QA_SESSIONS)
            
            question_doc = {
                "question_number": 0,  # Will be set by increment
                "question": question,
                "answer": answer,
                "question_type": question_type,
                "confidence": confidence,
                "asked_at": datetime.utcnow(),
                "tokens_used": tokens_used,
                "relevant_sections": relevant_sections
            }
            
            qa.update_one(
                {"qa_id": qa_id},
                {
                    "$push": {"questions": question_doc},
                    "$inc": {
                        "total_questions": 1,
                        "total_tokens_used": tokens_used
                    }
                }
            )
            
            logger.info(f"✅ Question added to session {qa_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add question: {str(e)}")
            return False


# Export service instance
mongo_service = MongoDBService()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("✅ MongoDB Service loaded successfully")
