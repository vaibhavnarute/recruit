"""
Candidate Repository - Handles selected and rejected candidates

Features:
- Track candidate selection/rejection
- Candidate status management
- Candidate history
- Decision tracking
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
from bson import ObjectId

from db.mongo_client import get_collection
from db.models import Collections

logger = logging.getLogger(__name__)


class CandidateRepository:
    """Repository for candidate selection/rejection operations"""
    
    def __init__(self):
        self.selected_collection = get_collection(Collections.SELECTED_CANDIDATES)
        self.rejected_collection = get_collection(Collections.REJECTED_CANDIDATES)
    
    def add_selected_candidate(
        self,
        resume_id: str,
        job_id: str,
        candidate_name: str,
        candidate_email: str,
        score: float,
        selected_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[str]:
        """
        Add candidate to selected list
        
        Args:
            resume_id: Resume ID
            job_id: Job ID
            candidate_name: Candidate's name
            candidate_email: Candidate's email
            score: Final selection score
            selected_by: User ID who selected
            notes: Additional notes
            
        Returns:
            Selection ID if successful, None otherwise
        """
        try:
            selection_doc = {
                "resume_id": resume_id,
                "job_id": job_id,
                "candidate_name": candidate_name,
                "candidate_email": candidate_email,
                "score": score,
                "selected_by": selected_by,
                "notes": notes,
                "selected_at": datetime.utcnow(),
                "status": "selected",  # selected, interviewed, offered, hired, declined
                "interview_scheduled": False
            }
            
            result = self.selected_collection.insert_one(selection_doc)
            logger.info(f"✅ Candidate selected: {candidate_name} (ID: {result.inserted_id})")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to add selected candidate: {str(e)}")
            return None
    
    def add_rejected_candidate(
        self,
        resume_id: str,
        job_id: str,
        candidate_name: str,
        candidate_email: str,
        score: float,
        reason: Optional[str] = None,
        rejected_by: Optional[str] = None
    ) -> Optional[str]:
        """
        Add candidate to rejected list
        
        Args:
            resume_id: Resume ID
            job_id: Job ID
            candidate_name: Candidate's name
            candidate_email: Candidate's email
            score: Final score
            reason: Rejection reason
            rejected_by: User ID who rejected
            
        Returns:
            Rejection ID if successful, None otherwise
        """
        try:
            rejection_doc = {
                "resume_id": resume_id,
                "job_id": job_id,
                "candidate_name": candidate_name,
                "candidate_email": candidate_email,
                "score": score,
                "reason": reason,
                "rejected_by": rejected_by,
                "rejected_at": datetime.utcnow()
            }
            
            result = self.rejected_collection.insert_one(rejection_doc)
            logger.info(f"✅ Candidate rejected: {candidate_name} (ID: {result.inserted_id})")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to add rejected candidate: {str(e)}")
            return None
    
    def get_selected_candidates(self, job_id: Optional[str] = None) -> List[Dict]:
        """Get selected candidates, optionally filtered by job"""
        try:
            query = {"job_id": job_id} if job_id else {}
            candidates = list(self.selected_collection.find(query))
            
            for candidate in candidates:
                candidate['_id'] = str(candidate['_id'])
            
            return candidates
        except Exception as e:
            logger.error(f"❌ Failed to get selected candidates: {str(e)}")
            return []
    
    def get_rejected_candidates(self, job_id: Optional[str] = None) -> List[Dict]:
        """Get rejected candidates, optionally filtered by job"""
        try:
            query = {"job_id": job_id} if job_id else {}
            candidates = list(self.rejected_collection.find(query))
            
            for candidate in candidates:
                candidate['_id'] = str(candidate['_id'])
            
            return candidates
        except Exception as e:
            logger.error(f"❌ Failed to get rejected candidates: {str(e)}")
            return []
    
    def update_candidate_status(self, candidate_id: str, status: str) -> bool:
        """Update selected candidate status"""
        try:
            result = self.selected_collection.update_one(
                {"_id": ObjectId(candidate_id)},
                {"$set": {"status": status, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to update candidate status: {str(e)}")
            return False
    
    def mark_interview_scheduled(self, candidate_id: str, interview_id: str) -> bool:
        """Mark that interview has been scheduled for candidate"""
        try:
            result = self.selected_collection.update_one(
                {"_id": ObjectId(candidate_id)},
                {
                    "$set": {
                        "interview_scheduled": True,
                        "interview_id": interview_id,
                        "status": "interviewed",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to mark interview scheduled: {str(e)}")
            return False
    
    def get_candidate_by_email(self, email: str, job_id: Optional[str] = None) -> Optional[Dict]:
        """Get candidate by email"""
        try:
            query = {"candidate_email": email}
            if job_id:
                query["job_id"] = job_id
            
            # Check selected first
            candidate = self.selected_collection.find_one(query)
            if candidate:
                candidate['_id'] = str(candidate['_id'])
                candidate['selection_status'] = 'selected'
                return candidate
            
            # Check rejected
            candidate = self.rejected_collection.find_one(query)
            if candidate:
                candidate['_id'] = str(candidate['_id'])
                candidate['selection_status'] = 'rejected'
                return candidate
            
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get candidate: {str(e)}")
            return None
