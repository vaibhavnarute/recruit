"""
Job Repository - Handles all job description database operations

Features:
- Create and manage job postings
- Job search and filtering
- Job requirements tracking
- Job statistics
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
from bson import ObjectId

from db.mongo_client import get_collection
from db.models import Collections

logger = logging.getLogger(__name__)


class JobRepository:
    """Repository for job description operations"""
    
    def __init__(self):
        self.collection = get_collection(Collections.JOB_DESCRIPTIONS)
    
    def create_job(
        self,
        title: str,
        description: str,
        requirements: List[str],
        skills_required: List[str],
        experience_min: int,
        experience_max: int,
        location: Optional[str] = None,
        salary_min: Optional[float] = None,
        salary_max: Optional[float] = None,
        company: Optional[str] = None,
        created_by: Optional[str] = None,
        threshold: float = 0.5
    ) -> Optional[str]:
        """
        Create a new job description
        
        Args:
            title: Job title
            description: Full job description
            requirements: List of requirements
            skills_required: Required skills
            experience_min: Minimum experience years
            experience_max: Maximum experience years
            location: Job location
            salary_min: Minimum salary
            salary_max: Maximum salary
            company: Company name
            created_by: User ID who created the job
            threshold: Matching threshold for candidate selection
            
        Returns:
            Job ID if successful, None otherwise
        """
        try:
            import uuid
            
            job_doc = {
                "job_id": str(uuid.uuid4()),  # Generate unique job ID
                "title": title,
                "description": description,
                "requirements": requirements,
                "skills_required": skills_required,
                "experience_min": experience_min,
                "experience_max": experience_max,
                "location": location,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "company": company,
                "created_by": created_by,
                "threshold": threshold,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "status": "active",  # active, closed, on_hold
                "statistics": {
                    "total_applications": 0,
                    "selected_count": 0,
                    "rejected_count": 0
                }
            }
            
            result = self.collection.insert_one(job_doc)
            logger.info(f"✅ Job created: {title} (ID: {result.inserted_id})")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to create job: {str(e)}")
            return None
    
    def get_job_by_id(self, job_id: str) -> Optional[Dict]:
        """Get job by ID"""
        try:
            job = self.collection.find_one({"_id": ObjectId(job_id)})
            if job:
                job['_id'] = str(job['_id'])
            return job
        except Exception as e:
            logger.error(f"❌ Failed to get job: {str(e)}")
            return None
    
    def update_job(self, job_id: str, updates: Dict) -> bool:
        """Update job description"""
        try:
            updates['updated_at'] = datetime.utcnow()
            result = self.collection.update_one(
                {"_id": ObjectId(job_id)},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to update job: {str(e)}")
            return False
    
    def update_job_statistics(
        self,
        job_id: str,
        total_applications: Optional[int] = None,
        selected_count: Optional[int] = None,
        rejected_count: Optional[int] = None
    ) -> bool:
        """Update job statistics"""
        try:
            updates = {}
            if total_applications is not None:
                updates["statistics.total_applications"] = total_applications
            if selected_count is not None:
                updates["statistics.selected_count"] = selected_count
            if rejected_count is not None:
                updates["statistics.rejected_count"] = rejected_count
            
            if not updates:
                return False
            
            result = self.collection.update_one(
                {"_id": ObjectId(job_id)},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to update job statistics: {str(e)}")
            return False
    
    def increment_application_count(self, job_id: str) -> bool:
        """Increment application count"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(job_id)},
                {"$inc": {"statistics.total_applications": 1}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to increment application count: {str(e)}")
            return False
    
    def get_active_jobs(self) -> List[Dict]:
        """Get all active jobs"""
        try:
            jobs = list(self.collection.find({"status": "active"}))
            for job in jobs:
                job['_id'] = str(job['_id'])
            return jobs
        except Exception as e:
            logger.error(f"❌ Failed to get active jobs: {str(e)}")
            return []
    
    def search_jobs(
        self,
        skills: Optional[List[str]] = None,
        location: Optional[str] = None,
        min_salary: Optional[float] = None
    ) -> List[Dict]:
        """Search jobs with filters"""
        try:
            query = {"status": "active"}
            
            if skills:
                query["skills_required"] = {"$in": skills}
            
            if location:
                query["location"] = {"$regex": location, "$options": "i"}
            
            if min_salary:
                query["salary_min"] = {"$gte": min_salary}
            
            jobs = list(self.collection.find(query))
            for job in jobs:
                job['_id'] = str(job['_id'])
            
            return jobs
        except Exception as e:
            logger.error(f"❌ Failed to search jobs: {str(e)}")
            return []
    
    def close_job(self, job_id: str) -> bool:
        """Close a job posting"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(job_id)},
                {"$set": {"status": "closed", "closed_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to close job: {str(e)}")
            return False
