"""
Interview Repository - Handles interview scheduling and management

Features:
- Schedule interviews
- Generate interview links
- Track interview status
- Interview history
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
from bson import ObjectId
import uuid

from db.mongo_client import get_collection
from db.models import Collections

logger = logging.getLogger(__name__)


class InterviewRepository:
    """Repository for interview operations"""
    
    def __init__(self):
        self.collection = get_collection(Collections.INTERVIEWS)
        if self.collection is None:
            logger.error("❌ Failed to get interviews collection from MongoDB!")
        else:
            logger.info(f"✅ Interview repository initialized with collection: {Collections.INTERVIEWS}")
    
    def create_interview(
        self,
        candidate_id: str,
        job_id: str,
        candidate_email: str,
        candidate_name: str,
        interview_type: str = "ai_assisted",
        scheduled_for: Optional[datetime] = None,
        created_by: Optional[str] = None,
        interview_id: Optional[str] = None,
        meet_link: Optional[str] = None,
        calendar_event_id: Optional[str] = None,
        calendar_link: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[str] = None,
        auto_start_bot: bool = True,
        auto_join_token: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Create an interview
        
        Args:
            candidate_id: Selected candidate ID
            job_id: Job ID
            candidate_email: Candidate's email
            candidate_name: Candidate's name
            interview_type: Type of interview (ai_assisted, human, hybrid)
            scheduled_for: Scheduled date/time
            created_by: User ID who created
            interview_id: Optional pre-generated interview ID
            meet_link: Optional Google Meet link
            calendar_event_id: Optional Google Calendar event ID
            calendar_link: Optional Google Calendar link
            refresh_token: Optional refresh token for Meet link
            expires_at: Optional expiration time for Meet link
            
        Returns:
            Interview document with meet_link if successful, None otherwise
        """
        try:
            # Check if collection is available
            if self.collection is None:
                logger.error("❌ MongoDB collection is None! Cannot create interview.")
                return None
            
            # Use provided interview_id or generate new one
            interview_id = interview_id or str(uuid.uuid4())
            
            # Extract or generate room_id from meet_link
            room_id = None
            if meet_link:
                # Extract room_id from Google Meet link (e.g., "https://meet.google.com/abc-defg-hij")
                try:
                    room_id = meet_link.split('/')[-1]  # Gets "abc-defg-hij"
                except:
                    room_id = str(uuid.uuid4())[:12]  # Fallback
            else:
                # Generate meet_link and room_id
                room_id = str(uuid.uuid4())[:12]
                meet_link = f"https://meet.google.com/{room_id[:3]}-{room_id[3:7]}-{room_id[7:10]}"
            
            interview_doc = {
                "interview_id": interview_id,  # Unique interview ID for index
                "room_id": room_id,  # Unique room ID (required by MongoDB index)
                "candidate_id": candidate_id,
                "job_id": job_id,
                "candidate_email": candidate_email,
                "candidate_name": candidate_name,
                "interview_type": interview_type,
                "meet_link": meet_link,
                "calendar_event_id": calendar_event_id,
                "calendar_link": calendar_link,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "scheduled_for": scheduled_for or datetime.utcnow(),
                "created_by": created_by,
                "created_at": datetime.utcnow(),
                "status": "scheduled",  # scheduled, in_progress, completed, cancelled
                "ai_enabled": interview_type in ["ai_assisted", "hybrid"],
                "questions_generated": False,
                "interview_data": {},
                # Auto-join fields
                "auto_start_bot": auto_start_bot,
                "auto_join_token": auto_join_token,
                "bot_join_status": "pending" if auto_start_bot else None,
                "candidate_joined_at": None,
                "bot_joined_at": None,
                "trigger_timestamp": None
            }
            
            result = self.collection.insert_one(interview_doc)
            interview_doc['_id'] = str(result.inserted_id)
            
            logger.info(f"✅ Interview created: {candidate_name} (ID: {result.inserted_id})")
            return interview_doc
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Failed to create interview: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def get_interview_by_id(self, interview_id: str) -> Optional[Dict]:
        """
        Get interview by interview_id (UUID field) or MongoDB _id
        
        Args:
            interview_id: Either the interview_id UUID or MongoDB ObjectId
        """
        try:
            # Try to find by interview_id field first (UUID)
            interview = self.collection.find_one({"interview_id": interview_id})
            
            # If not found, try MongoDB _id
            if not interview:
                try:
                    interview = self.collection.find_one({"_id": ObjectId(interview_id)})
                except:
                    pass
            
            if interview:
                interview['_id'] = str(interview['_id'])
                logger.info(f"✅ Found interview: {interview_id}")
            else:
                logger.warning(f"⚠️ Interview not found: {interview_id}")
            
            return interview
        except Exception as e:
            logger.error(f"❌ Failed to get interview: {str(e)}")
            return None
    
    def get_interview_by_room_id(self, room_id: str) -> Optional[Dict]:
        """Get interview by room ID"""
        try:
            interview = self.collection.find_one({"room_id": room_id})
            if interview:
                interview['_id'] = str(interview['_id'])
            return interview
        except Exception as e:
            logger.error(f"❌ Failed to get interview: {str(e)}")
            return None
    
    def get_interviews_by_job(self, job_id: str) -> List[Dict]:
        """Get all interviews for a job"""
        try:
            interviews = list(self.collection.find({"job_id": job_id}))
            for interview in interviews:
                interview['_id'] = str(interview['_id'])
            return interviews
        except Exception as e:
            logger.error(f"❌ Failed to get interviews: {str(e)}")
            return []
    
    def get_interviews_by_candidate(self, candidate_email: str) -> List[Dict]:
        """Get all interviews for a candidate"""
        try:
            interviews = list(self.collection.find({"candidate_email": candidate_email}))
            for interview in interviews:
                interview['_id'] = str(interview['_id'])
            return interviews
        except Exception as e:
            logger.error(f"❌ Failed to get interviews: {str(e)}")
            return []
    
    def update_interview_status(self, interview_id: str, status: str) -> bool:
        """Update interview status"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(interview_id)},
                {"$set": {"status": status, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to update interview status: {str(e)}")
            return False
    
    def update_interview(self, interview_id: str, update_data: dict) -> bool:
        """
        Update interview with arbitrary fields
        
        Args:
            interview_id: Interview ID (UUID) or MongoDB ObjectId
            update_data: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try to find by interview_id field first (UUID)
            result = self.collection.update_one(
                {"interview_id": interview_id},
                {"$set": {**update_data, "updated_at": datetime.utcnow()}}
            )
            
            # If not found, try MongoDB _id
            if result.matched_count == 0:
                try:
                    result = self.collection.update_one(
                        {"_id": ObjectId(interview_id)},
                        {"$set": {**update_data, "updated_at": datetime.utcnow()}}
                    )
                except:
                    pass
            
            if result.modified_count > 0:
                logger.info(f"✅ Updated interview {interview_id}: {list(update_data.keys())}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to update interview: {str(e)}")
            return False
    
    def mark_questions_generated(self, interview_id: str) -> bool:
        """Mark that AI questions have been generated"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(interview_id)},
                {"$set": {"questions_generated": True, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to mark questions generated: {str(e)}")
            return False
    
    def save_interview_data(self, interview_id: str, data: Dict) -> bool:
        """Save interview data (scores, feedback, etc.)"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(interview_id)},
                {"$set": {"interview_data": data, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to save interview data: {str(e)}")
            return False
    
    def get_scheduled_interviews(self, from_date: Optional[datetime] = None) -> List[Dict]:
        """Get scheduled interviews"""
        try:
            query = {"status": "scheduled"}
            if from_date:
                query["scheduled_for"] = {"$gte": from_date}
            
            interviews = list(self.collection.find(query))
            for interview in interviews:
                interview['_id'] = str(interview['_id'])
            
            return interviews
        except Exception as e:
            logger.error(f"❌ Failed to get scheduled interviews: {str(e)}")
            return []
