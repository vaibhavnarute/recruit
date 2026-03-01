"""
Transcriptions and Meetings Repository

Handles MongoDB operations for:
- Transcriptions: STT audio transcriptions with analysis
- Meetings: Virtual meeting sessions with participants and analytics
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.collection import Collection
import os
import uuid
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class TranscriptionsMeetingsRepository:
    """MongoDB repository for Transcriptions and Meetings"""
    
    def __init__(self):
        """Initialize MongoDB connection"""
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGO_URI not found in environment variables")
        
        # Configure MongoDB client with proper timeout settings for Atlas
        self.client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000,  # 10 seconds
            connectTimeoutMS=10000,  # 10 seconds
            socketTimeoutMS=45000,  # 45 seconds for operations
            maxPoolSize=50,
            retryWrites=True,
            retryReads=True
        )
        db_name = os.getenv("MONGO_DB_NAME", "resumate")
        self.db = self.client.get_database(db_name)
        
        # Collections
        self.transcriptions_collection: Collection = self.db.get_collection("transcriptions")
        self.meetings_collection: Collection = self.db.get_collection("meetings")
        
        # Create indexes
        self._create_indexes()
        
        logger.info("✅ Transcriptions & Meetings Repository initialized")
    
    def _create_indexes(self):
        """Create database indexes for efficient querying"""
        try:
            # Transcriptions indexes
            self.transcriptions_collection.create_index("transcription_id", unique=True, name="transcription_id_unique")
            self.transcriptions_collection.create_index("session_id", name="trans_session_id_idx")
            self.transcriptions_collection.create_index("meeting_id", name="trans_meeting_id_idx")
            self.transcriptions_collection.create_index("interview_id", name="trans_interview_id_idx")
            self.transcriptions_collection.create_index([("transcribed_at", DESCENDING)], name="transcribed_at_desc")
            self.transcriptions_collection.create_index("sentiment", name="sentiment_idx")
            self.transcriptions_collection.create_index("confidence_score", name="confidence_idx")
            
            logger.info("✅ Created indexes for transcriptions collection")
            
            # Meetings indexes
            self.meetings_collection.create_index("meeting_id", unique=True, name="meeting_id_unique")
            self.meetings_collection.create_index("session_id", name="meet_session_id_idx")
            self.meetings_collection.create_index("interview_id", name="meet_interview_id_idx")
            self.meetings_collection.create_index("candidate_email", name="candidate_email_idx")
            self.meetings_collection.create_index("host_email", name="host_email_idx")
            self.meetings_collection.create_index("status", name="status_idx")
            self.meetings_collection.create_index([("scheduled_at", DESCENDING)], name="scheduled_at_desc")
            self.meetings_collection.create_index([("started_at", DESCENDING)], name="started_at_desc")
            self.meetings_collection.create_index("calendar_event_id", name="calendar_event_idx")
            
            logger.info("✅ Created indexes for meetings collection")
                
        except Exception as e:
            logger.warning(f"⚠️ Error creating indexes: {str(e)}")
    
    # ==================== Transcriptions Operations ====================
    
    def create_transcription(self, transcription_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new transcription record
        
        Args:
            transcription_data: Transcription details
            
        Returns:
            Created transcription document
        """
        try:
            transcription_doc = {
                "transcription_id": transcription_data.get("transcription_id", f"trans_{uuid.uuid4()}"),
                "session_id": transcription_data.get("session_id"),
                "meeting_id": transcription_data.get("meeting_id"),
                "interview_id": transcription_data.get("interview_id"),
                "chunk_id": transcription_data.get("chunk_id"),
                "audio_chunk_number": transcription_data.get("audio_chunk_number", 0),
                
                # Audio metadata
                "audio_format": transcription_data.get("audio_format", "mp3"),
                "audio_duration": transcription_data.get("audio_duration"),
                "audio_size_bytes": transcription_data.get("audio_size_bytes"),
                
                # Transcription data
                "raw_transcription": transcription_data.get("raw_transcription", ""),
                "cleaned_transcription": transcription_data.get("cleaned_transcription", ""),
                "language_detected": transcription_data.get("language_detected", "en"),
                "confidence_score": transcription_data.get("confidence_score", 0.0),
                
                # Analysis
                "sentiment": transcription_data.get("sentiment", "neutral"),
                "speaker_detected": transcription_data.get("speaker_detected"),
                "key_points": transcription_data.get("key_points", []),
                "technical_terms": transcription_data.get("technical_terms", []),
                "questions_asked": transcription_data.get("questions_asked", []),
                "answers_given": transcription_data.get("answers_given", []),
                
                # Processing
                "model": transcription_data.get("model", "whisper-large-v3"),
                "llm_model": transcription_data.get("llm_model"),
                "workflow": transcription_data.get("workflow", "langgraph"),
                "mcp_optimized": transcription_data.get("mcp_optimized", True),
                "processing_time_ms": transcription_data.get("processing_time_ms", 0.0),
                "tokens_used": transcription_data.get("tokens_used"),
                
                # Context
                "question_context": transcription_data.get("question_context"),
                "interview_stage": transcription_data.get("interview_stage"),
                
                # Timestamps
                "transcribed_at": transcription_data.get("transcribed_at", datetime.utcnow()),
                "analyzed_at": transcription_data.get("analyzed_at"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                
                # Errors
                "has_errors": transcription_data.get("has_errors", False),
                "errors": transcription_data.get("errors", []),
                
                "metadata": transcription_data.get("metadata", {})
            }
            
            result = self.transcriptions_collection.insert_one(transcription_doc)
            transcription_doc['_id'] = str(result.inserted_id)
            
            logger.info(f"✅ Created transcription: {transcription_doc['transcription_id']}")
            
            return transcription_doc
            
        except Exception as e:
            logger.error(f"❌ Error creating transcription: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create transcription"
            }
    
    def get_transcriptions_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all transcriptions for a session"""
        try:
            transcriptions = list(
                self.transcriptions_collection.find({"session_id": session_id})
                .sort("transcribed_at", ASCENDING)
            )
            
            for trans in transcriptions:
                trans['_id'] = str(trans['_id'])
            
            logger.info(f"📝 Retrieved {len(transcriptions)} transcriptions for session {session_id}")
            return transcriptions
            
        except Exception as e:
            logger.error(f"❌ Error getting transcriptions: {str(e)}", exc_info=True)
            return []
    
    def get_transcriptions_by_meeting(self, meeting_id: str) -> List[Dict[str, Any]]:
        """Get all transcriptions for a meeting"""
        try:
            transcriptions = list(
                self.transcriptions_collection.find({"meeting_id": meeting_id})
                .sort("transcribed_at", ASCENDING)
            )
            
            for trans in transcriptions:
                trans['_id'] = str(trans['_id'])
            
            logger.info(f"📝 Retrieved {len(transcriptions)} transcriptions for meeting {meeting_id}")
            return transcriptions
            
        except Exception as e:
            logger.error(f"❌ Error getting transcriptions: {str(e)}", exc_info=True)
            return []
    
    def get_full_transcript(self, session_id: str) -> str:
        """Combine all transcriptions for a session into one transcript"""
        try:
            transcriptions = self.get_transcriptions_by_session(session_id)
            
            full_transcript = "\n\n".join([
                trans.get('cleaned_transcription', trans.get('raw_transcription', ''))
                for trans in transcriptions
                if trans.get('cleaned_transcription') or trans.get('raw_transcription')
            ])
            
            return full_transcript
            
        except Exception as e:
            logger.error(f"❌ Error creating full transcript: {str(e)}", exc_info=True)
            return ""
    
    # ==================== Meetings Operations ====================
    
    def create_meeting(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new meeting record
        
        Args:
            meeting_data: Meeting details
            
        Returns:
            Created meeting document
        """
        try:
            meeting_doc = {
                "meeting_id": meeting_data.get("meeting_id", f"meet_{uuid.uuid4()}"),
                "session_id": meeting_data.get("session_id", f"session_{uuid.uuid4()}"),
                "room_id": meeting_data.get("room_id"),
                
                # Meeting details
                "meeting_title": meeting_data.get("meeting_title", "Interview Meeting"),
                "meeting_type": meeting_data.get("meeting_type", "interview"),
                "meeting_link": meeting_data.get("meeting_link", ""),
                "meeting_platform": meeting_data.get("meeting_platform", "google_meet"),
                
                # Participants
                "host_email": meeting_data.get("host_email", ""),
                "host_name": meeting_data.get("host_name", ""),
                "participants": meeting_data.get("participants", []),
                "expected_participants": meeting_data.get("expected_participants", 2),
                "actual_participants": 0,
                
                # Related entities
                "interview_id": meeting_data.get("interview_id"),
                "candidate_email": meeting_data.get("candidate_email"),
                "candidate_name": meeting_data.get("candidate_name"),
                "job_id": meeting_data.get("job_id"),
                
                # Status
                "status": "scheduled",
                "is_recording": False,
                "recording_enabled": meeting_data.get("recording_enabled", True),
                "recording_url": None,
                
                # Timing
                "scheduled_at": meeting_data.get("scheduled_at", datetime.utcnow()),
                "started_at": None,
                "ended_at": None,
                "duration_minutes": None,
                "expected_duration_minutes": meeting_data.get("expected_duration_minutes", 60),
                
                # AI Features
                "ai_bot_enabled": meeting_data.get("ai_bot_enabled", False),
                "ai_bot_name": meeting_data.get("ai_bot_name"),
                "ai_bot_email": meeting_data.get("ai_bot_email"),
                "bot_join_attempts": 0,
                "bot_joined_at": None,
                "bot_left_at": None,
                
                # Transcription
                "transcription_enabled": meeting_data.get("transcription_enabled", True),
                "total_transcriptions": 0,
                "transcription_ids": [],
                "full_transcript": None,
                
                # Analytics
                "total_audio_chunks": 0,
                "total_participants_joined": 0,
                "participant_join_times": [],
                "average_sentiment": None,
                "key_topics": [],
                "questions_count": 0,
                "technical_score": None,
                "communication_score": None,
                
                # Calendar
                "calendar_event_id": meeting_data.get("calendar_event_id"),
                "calendar_link": meeting_data.get("calendar_link"),
                "reminder_sent": False,
                "reminder_sent_at": None,
                
                # Security
                "access_code": meeting_data.get("access_code"),
                "is_private": meeting_data.get("is_private", True),
                "allowed_domains": meeting_data.get("allowed_domains", []),
                
                # Timestamps
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "last_activity_at": None,
                
                # Errors
                "join_errors": [],
                "recording_errors": [],
                "has_errors": False,
                
                "metadata": meeting_data.get("metadata", {})
            }
            
            result = self.meetings_collection.insert_one(meeting_doc)
            meeting_doc['_id'] = str(result.inserted_id)
            
            logger.info(f"✅ Created meeting: {meeting_doc['meeting_id']}")
            
            return meeting_doc
            
        except Exception as e:
            logger.error(f"❌ Error creating meeting: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create meeting"
            }
    
    def update_meeting(self, meeting_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update meeting details"""
        try:
            updates['updated_at'] = datetime.utcnow()
            
            result = self.meetings_collection.update_one(
                {"meeting_id": meeting_id},
                {"$set": updates}
            )
            
            if result.matched_count == 0:
                logger.warning(f"⚠️ Meeting not found: {meeting_id}")
                return {"success": False, "message": "Meeting not found"}
            
            logger.info(f"✅ Updated meeting: {meeting_id}")
            return {"success": True, "message": "Meeting updated"}
            
        except Exception as e:
            logger.error(f"❌ Error updating meeting: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_meeting(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """Get meeting by ID"""
        try:
            meeting = self.meetings_collection.find_one({"meeting_id": meeting_id})
            if meeting:
                meeting['_id'] = str(meeting['_id'])
            return meeting
        except Exception as e:
            logger.error(f"❌ Error getting meeting: {str(e)}", exc_info=True)
            return None
    
    def get_meetings_by_interview(self, interview_id: str) -> List[Dict[str, Any]]:
        """Get all meetings for an interview"""
        try:
            meetings = list(
                self.meetings_collection.find({"interview_id": interview_id})
                .sort("scheduled_at", DESCENDING)
            )
            
            for meeting in meetings:
                meeting['_id'] = str(meeting['_id'])
            
            return meetings
        except Exception as e:
            logger.error(f"❌ Error getting meetings: {str(e)}", exc_info=True)
            return []
    
    def add_transcription_to_meeting(self, meeting_id: str, transcription_id: str):
        """Link a transcription to a meeting"""
        try:
            result = self.meetings_collection.update_one(
                {"meeting_id": meeting_id},
                {
                    "$push": {"transcription_ids": transcription_id},
                    "$inc": {"total_transcriptions": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Added transcription {transcription_id} to meeting {meeting_id}")
            
        except Exception as e:
            logger.error(f"❌ Error adding transcription to meeting: {str(e)}", exc_info=True)
    
    def update_meeting_transcript(self, meeting_id: str):
        """Update full transcript for a meeting"""
        try:
            transcriptions = self.get_transcriptions_by_meeting(meeting_id)
            
            full_transcript = "\n\n".join([
                trans.get('cleaned_transcription', trans.get('raw_transcription', ''))
                for trans in transcriptions
                if trans.get('cleaned_transcription') or trans.get('raw_transcription')
            ])
            
            self.update_meeting(meeting_id, {"full_transcript": full_transcript})
            logger.info(f"✅ Updated full transcript for meeting {meeting_id}")
            
        except Exception as e:
            logger.error(f"❌ Error updating meeting transcript: {str(e)}", exc_info=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        try:
            return {
                "total_transcriptions": self.transcriptions_collection.count_documents({}),
                "total_meetings": self.meetings_collection.count_documents({}),
                "active_meetings": self.meetings_collection.count_documents({"status": {"$in": ["scheduled", "in_progress"]}}),
                "completed_meetings": self.meetings_collection.count_documents({"status": "completed"})
            }
        except Exception as e:
            logger.error(f"❌ Error getting stats: {str(e)}", exc_info=True)
            return {}
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()
        logger.info("✅ Closed MongoDB connection")


# Convenience functions
def get_transcriptions_meetings_repo() -> TranscriptionsMeetingsRepository:
    """Get repository instance"""
    return TranscriptionsMeetingsRepository()


if __name__ == "__main__":
    # Test the repository
    print("=" * 80)
    print("Testing Transcriptions & Meetings Repository")
    print("=" * 80)
    
    repo = get_transcriptions_meetings_repo()
    
    # Get stats
    stats = repo.get_stats()
    print(f"\n📊 Statistics:")
    print(f"   Total Transcriptions: {stats.get('total_transcriptions', 0)}")
    print(f"   Total Meetings: {stats.get('total_meetings', 0)}")
    print(f"   Active Meetings: {stats.get('active_meetings', 0)}")
    print(f"   Completed Meetings: {stats.get('completed_meetings', 0)}")
    
    repo.close()
    print("\n✅ Repository test complete")
