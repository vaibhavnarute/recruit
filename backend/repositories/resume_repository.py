"""
Resume Repository - Handles all resume-related database operations

Features:
- Resume upload and storage
- Resume text extraction
- Resume search and filtering
- Resume metadata management
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
from bson import ObjectId

from db.mongo_client import get_collection
from db.models import Collections

logger = logging.getLogger(__name__)


class ResumeRepository:
    """Repository for resume data operations"""
    
    def __init__(self):
        self.collection = get_collection(Collections.RESUMES)
    
    def save_resume(
        self,
        filename: str,
        file_path: str,
        extracted_text: str,
        candidate_email: Optional[str] = None,
        candidate_name: Optional[str] = None,
        candidate_phone: Optional[str] = None,
        skills: Optional[List[str]] = None,
        experience_years: Optional[int] = None,
        education: Optional[List[str]] = None,
        job_id: Optional[str] = None,
        uploaded_by: Optional[str] = None
    ) -> Optional[str]:
        """
        Save resume to database
        
        Args:
            filename: Original filename
            file_path: Path where file is stored
            extracted_text: Extracted text from resume
            candidate_email: Candidate's email
            candidate_name: Candidate's name
            candidate_phone: Candidate's phone
            skills: List of skills
            experience_years: Years of experience
            education: List of education
            job_id: Associated job description ID
            uploaded_by: User ID who uploaded
            
        Returns:
            Resume ID if successful, None otherwise
        """
        try:
            resume_doc = {
                "filename": filename,
                "file_path": file_path,
                "extracted_text": extracted_text,
                "candidate_email": candidate_email,
                "candidate_name": candidate_name,
                "candidate_phone": candidate_phone,
                "skills": skills or [],
                "experience_years": experience_years,
                "education": education or [],
                "job_id": job_id,
                "uploaded_by": uploaded_by,
                "uploaded_at": datetime.utcnow(),
                "status": "pending",  # pending, reviewed, selected, rejected
                "metadata": {
                    "file_size": len(extracted_text),
                    "word_count": len(extracted_text.split())
                }
            }
            
            result = self.collection.insert_one(resume_doc)
            logger.info(f"✅ Resume saved: {filename} (ID: {result.inserted_id})")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to save resume: {str(e)}")
            return None
    
    def get_resume_by_id(self, resume_id: str) -> Optional[Dict]:
        """Get resume by ID"""
        try:
            resume = self.collection.find_one({"_id": ObjectId(resume_id)})
            if resume:
                resume['_id'] = str(resume['_id'])
            return resume
        except Exception as e:
            logger.error(f"❌ Failed to get resume: {str(e)}")
            return None
    
    def get_resumes_by_job(self, job_id: str) -> List[Dict]:
        """Get all resumes for a specific job"""
        try:
            resumes = list(self.collection.find({"job_id": job_id}))
            for resume in resumes:
                resume['_id'] = str(resume['_id'])
            return resumes
        except Exception as e:
            logger.error(f"❌ Failed to get resumes: {str(e)}")
            return []
    
    def update_resume_status(self, resume_id: str, status: str) -> bool:
        """Update resume status"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(resume_id)},
                {"$set": {"status": status, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to update resume status: {str(e)}")
            return False
    
    def search_resumes(
        self,
        skills: Optional[List[str]] = None,
        min_experience: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Dict]:
        """Search resumes with filters"""
        try:
            query = {}
            
            if skills:
                query["skills"] = {"$in": skills}
            
            if min_experience is not None:
                query["experience_years"] = {"$gte": min_experience}
            
            if status:
                query["status"] = status
            
            resumes = list(self.collection.find(query))
            for resume in resumes:
                resume['_id'] = str(resume['_id'])
            
            return resumes
        except Exception as e:
            logger.error(f"❌ Failed to search resumes: {str(e)}")
            return []
    
    def get_all_resumes(self, limit: int = 100) -> List[Dict]:
        """Get all resumes with optional limit"""
        try:
            resumes = list(self.collection.find().limit(limit))
            for resume in resumes:
                resume['_id'] = str(resume['_id'])
            return resumes
        except Exception as e:
            logger.error(f"❌ Failed to get resumes: {str(e)}")
            return []
    
    def delete_resume(self, resume_id: str) -> bool:
        """Delete resume"""
        try:
            result = self.collection.delete_one({"_id": ObjectId(resume_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to delete resume: {str(e)}")
            return False
