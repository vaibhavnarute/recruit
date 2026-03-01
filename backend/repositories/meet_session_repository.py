"""
Meet Session Repository

Handles MongoDB operations for Google Meet recording sessions:
- Store session metadata and state
- Save transcription segments
- Track session analytics
- Manage session lifecycle
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pymongo import MongoClient, DESCENDING
import os
import uuid
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class MeetSessionRepository:
    """MongoDB repository for Meet recording sessions"""
    
    def __init__(self):
        """Initialize MongoDB connection"""
        # Try MONGODB_URI first, then fall back to MONGO_URI for compatibility
        mongo_uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGODB_URI or MONGO_URI not found in environment variables")
        
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
        # Use database name from environment or default
        db_name = os.getenv("MONGO_DB_NAME", "resumate")
        self.db = self.client.get_database(db_name)
        
        # Collections
        self.sessions_collection = self.db.get_collection("meet_sessions")
        self.transcripts_collection = self.db.get_collection("meet_transcripts")
        self.audio_chunks_collection = self.db.get_collection("meet_audio_chunks")
        
        # Create indexes
        self._create_indexes()
        
        logger.info("✅ Meet Session Repository initialized")
    
    def _create_indexes(self):
        """Create database indexes for efficient querying"""
        try:
            # Sessions indexes
            if self.sessions_collection is not None:
                self.sessions_collection.create_index("session_id", unique=True, name="session_id_unique")
                self.sessions_collection.create_index("interview_id", name="interview_id_idx")
                self.sessions_collection.create_index([("created_at", DESCENDING)], name="created_at_desc")
                self.sessions_collection.create_index("session_status", name="session_status_idx")
                
                logger.info("✅ Created indexes for meet_sessions collection")
            
            # Transcripts indexes
            if self.transcripts_collection is not None:
                self.transcripts_collection.create_index("session_id", name="transcript_session_id_idx")
                self.transcripts_collection.create_index("chunk_id", unique=True, name="chunk_id_unique")
                self.transcripts_collection.create_index([("transcribed_at", DESCENDING)], name="transcribed_at_desc")
                
                logger.info("✅ Created indexes for meet_transcripts collection")
            
            # Audio chunks indexes
            if self.audio_chunks_collection is not None:
                self.audio_chunks_collection.create_index("session_id", name="audio_session_id_idx")
                self.audio_chunks_collection.create_index("chunk_id", unique=True, name="audio_chunk_id_unique")
                
                logger.info("✅ Created indexes for meet_audio_chunks collection")
                
        except Exception as e:
            logger.warning(f"⚠️ Error creating indexes: {str(e)}")
    
    # ==================== Session Operations ====================
    
    def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new Meet recording session
        
        Args:
            session_data: Session configuration
            
        Returns:
            Created session document
        """
        try:
            session_doc = {
                "session_id": session_data.get("session_id", str(uuid.uuid4())),
                "interview_id": session_data.get("interview_id"),
                "meet_url": session_data.get("meet_url"),
                "bot_email": session_data.get("bot_email"),
                "session_status": "pending",
                "join_attempts": 0,
                "audio_chunks_received": 0,
                "transcription_segments": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "started_at": None,
                "joined_at": None,
                "ended_at": None,
                "errors": [],
                "metadata": session_data.get("metadata", {})
            }
            
            if self.sessions_collection is None:
                raise RuntimeError("Sessions collection is not initialized")
            
            result = self.sessions_collection.insert_one(session_doc)
            session_doc['_id'] = str(result.inserted_id)
            
            logger.info(f"✅ Created session: {session_doc['session_id']}")
            
            return session_doc
            
        except Exception as e:
            logger.error(f"❌ Error creating session: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create session"
            }
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update session state
        
        Args:
            session_id: Session identifier
            updates: Fields to update
            
        Returns:
            Success status
        """
        try:
            if self.sessions_collection is None:
                raise RuntimeError("Sessions collection is not initialized")
            
            updates['updated_at'] = datetime.utcnow()
            
            result = self.sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": updates}
            )
            
            if result.matched_count == 0:
                logger.warning(f"⚠️ Session not found: {session_id}")
                return {
                    "success": False,
                    "message": "Session not found"
                }
            
            logger.info(f"✅ Updated session: {session_id}")
            
            return {
                "success": True,
                "message": "Session updated successfully",
                "modified_count": result.modified_count
            }
            
        except Exception as e:
            logger.error(f"❌ Error updating session: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update session"
            }
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session document or None
        """
        try:
            if self.sessions_collection is None:
                raise RuntimeError("Sessions collection is not initialized")
            
            session = self.sessions_collection.find_one({"session_id": session_id})
            
            if session:
                session['_id'] = str(session['_id'])
                logger.info(f"✅ Retrieved session: {session_id}")
                return session
            else:
                logger.warning(f"⚠️ Session not found: {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error retrieving session: {str(e)}", exc_info=True)
            return None
    
    def get_sessions_by_interview(self, interview_id: str) -> List[Dict[str, Any]]:
        """
        Get all sessions for an interview
        
        Args:
            interview_id: Interview identifier
            
        Returns:
            List of session documents
        """
        try:
            if self.sessions_collection is None:
                raise RuntimeError("Sessions collection is not initialized")
            
            sessions = list(self.sessions_collection.find(
                {"interview_id": interview_id}
            ).sort("created_at", DESCENDING))
            
            for session in sessions:
                session['_id'] = str(session['_id'])
            
            logger.info(f"✅ Retrieved {len(sessions)} sessions for interview: {interview_id}")
            
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Error retrieving sessions: {str(e)}", exc_info=True)
            return []
    
    def add_session_error(self, session_id: str, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add error to session error log
        
        Args:
            session_id: Session identifier
            error_data: Error information
            
        Returns:
            Success status
        """
        try:
            if self.sessions_collection is None:
                raise RuntimeError("Sessions collection is not initialized")
            
            error_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "stage": error_data.get("stage", "unknown"),
                "error": error_data.get("error", "Unknown error"),
                "details": error_data.get("details", {})
            }
            
            result = self.sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {"errors": error_entry},
                    "$set": {
                        "last_error": error_entry["error"],
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"✅ Added error to session: {session_id}")
            
            return {
                "success": True,
                "message": "Error logged successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Error logging session error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to log error"
            }
    
    # ==================== Transcript Operations ====================
    
    def save_transcript(self, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save transcription segment
        
        Args:
            transcript_data: Transcription data
            
        Returns:
            Saved transcript document
        """
        try:
            transcript_doc = {
                "chunk_id": transcript_data.get("chunk_id", str(uuid.uuid4())),
                "session_id": transcript_data["session_id"],
                "interview_id": transcript_data.get("interview_id"),
                "raw_transcription": transcript_data.get("raw_transcription", ""),
                "cleaned_transcription": transcript_data.get("cleaned_transcription", ""),
                "confidence_score": transcript_data.get("confidence_score", 0.0),
                "language_detected": transcript_data.get("language_detected", "en"),
                "speaker_detected": transcript_data.get("speaker_detected", ""),
                "sentiment": transcript_data.get("sentiment", "neutral"),
                "key_points": transcript_data.get("key_points", []),
                "technical_terms": transcript_data.get("technical_terms", []),
                "chunk_duration": transcript_data.get("chunk_duration", 0.0),
                "transcribed_at": datetime.utcnow(),
                "metadata": transcript_data.get("metadata", {})
            }
            
            if self.transcripts_collection is None:
                raise RuntimeError("Transcripts collection is not initialized")
            
            result = self.transcripts_collection.insert_one(transcript_doc)
            transcript_doc['_id'] = str(result.inserted_id)
            
            # Update session transcript count
            self.sessions_collection.update_one(
                {"session_id": transcript_data["session_id"]},
                {
                    "$inc": {"transcription_segments": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            logger.info(f"✅ Saved transcript: {transcript_doc['chunk_id']}")
            
            return transcript_doc
            
        except Exception as e:
            logger.error(f"❌ Error saving transcript: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to save transcript"
            }
    
    def get_transcripts_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all transcripts for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of transcript documents
        """
        try:
            if self.transcripts_collection is None:
                raise RuntimeError("Transcripts collection is not initialized")
            
            transcripts = list(self.transcripts_collection.find(
                {"session_id": session_id}
            ).sort("transcribed_at", DESCENDING))
            
            for transcript in transcripts:
                transcript['_id'] = str(transcript['_id'])
            
            logger.info(f"✅ Retrieved {len(transcripts)} transcripts for session: {session_id}")
            
            return transcripts
            
        except Exception as e:
            logger.error(f"❌ Error retrieving transcripts: {str(e)}", exc_info=True)
            return []
    
    def get_full_transcript(self, session_id: str) -> Dict[str, Any]:
        """
        Get complete transcript for a session (all segments combined)
        
        Args:
            session_id: Session identifier
            
        Returns:
            Combined transcript data
        """
        try:
            transcripts = self.get_transcripts_by_session(session_id)
            
            if not transcripts:
                return {
                    "session_id": session_id,
                    "full_transcript": "",
                    "segments": [],
                    "total_segments": 0,
                    "total_duration": 0.0,
                    "average_confidence": 0.0
                }
            
            # Sort by transcribed_at
            transcripts.sort(key=lambda x: x.get('transcribed_at', ''))
            
            # Combine transcripts
            full_text = " ".join([
                t.get('cleaned_transcription', t.get('raw_transcription', ''))
                for t in transcripts
            ])
            
            # Calculate statistics
            total_duration = sum([t.get('chunk_duration', 0.0) for t in transcripts])
            avg_confidence = sum([t.get('confidence_score', 0.0) for t in transcripts]) / len(transcripts)
            
            # Collect all key points and technical terms
            all_key_points = []
            all_technical_terms = []
            for t in transcripts:
                all_key_points.extend(t.get('key_points', []))
                all_technical_terms.extend(t.get('technical_terms', []))
            
            result = {
                "session_id": session_id,
                "full_transcript": full_text,
                "segments": transcripts,
                "total_segments": len(transcripts),
                "total_duration": total_duration,
                "average_confidence": avg_confidence,
                "key_points": list(set(all_key_points)),  # Remove duplicates
                "technical_terms": list(set(all_technical_terms))
            }
            
            logger.info(f"✅ Generated full transcript for session: {session_id}")
            logger.info(f"   Total segments: {len(transcripts)}")
            logger.info(f"   Total duration: {total_duration:.2f}s")
            logger.info(f"   Average confidence: {avg_confidence:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error generating full transcript: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to generate full transcript"
            }
    
    # ==================== Audio Chunk Operations ====================
    
    def save_audio_chunk_metadata(self, chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save audio chunk metadata (not the actual audio data)
        
        Args:
            chunk_data: Audio chunk metadata
            
        Returns:
            Saved chunk document
        """
        try:
            chunk_doc = {
                "chunk_id": chunk_data.get("chunk_id", str(uuid.uuid4())),
                "session_id": chunk_data["session_id"],
                "chunk_size": chunk_data.get("chunk_size", 0),
                "audio_format": chunk_data.get("audio_format", "webm"),
                "duration": chunk_data.get("duration", 0.0),
                "received_at": datetime.utcnow(),
                "processing_status": chunk_data.get("processing_status", "pending"),
                "metadata": chunk_data.get("metadata", {})
            }
            
            if self.audio_chunks_collection is None:
                raise RuntimeError("Audio chunks collection is not initialized")
            
            result = self.audio_chunks_collection.insert_one(chunk_doc)
            chunk_doc['_id'] = str(result.inserted_id)
            
            # Update session audio chunk count
            self.sessions_collection.update_one(
                {"session_id": chunk_data["session_id"]},
                {
                    "$inc": {"audio_chunks_received": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            logger.debug(f"✅ Saved audio chunk metadata: {chunk_doc['chunk_id']}")
            
            return chunk_doc
            
        except Exception as e:
            logger.error(f"❌ Error saving audio chunk metadata: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to save audio chunk metadata"
            }
    
    # ==================== Analytics ====================
    
    def get_session_analytics(self, session_id: str) -> Dict[str, Any]:
        """
        Get comprehensive analytics for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Analytics data
        """
        try:
            session = self.get_session(session_id)
            if not session:
                return {
                    "success": False,
                    "message": "Session not found"
                }
            
            transcripts = self.get_transcripts_by_session(session_id)
            
            # Calculate analytics
            total_duration = sum([t.get('chunk_duration', 0.0) for t in transcripts])
            avg_confidence = sum([t.get('confidence_score', 0.0) for t in transcripts]) / len(transcripts) if transcripts else 0.0
            
            # Sentiment distribution
            sentiment_counts = {}
            for t in transcripts:
                sentiment = t.get('sentiment', 'neutral')
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            
            # Calculate session duration
            started_at = session.get('started_at')
            ended_at = session.get('ended_at')
            session_duration = 0
            if started_at and ended_at:
                if isinstance(started_at, str):
                    started_at = datetime.fromisoformat(started_at)
                if isinstance(ended_at, str):
                    ended_at = datetime.fromisoformat(ended_at)
                session_duration = (ended_at - started_at).total_seconds()
            
            analytics = {
                "session_id": session_id,
                "session_status": session.get('session_status', 'unknown'),
                "session_duration_seconds": session_duration,
                "audio_chunks_received": session.get('audio_chunks_received', 0),
                "transcription_segments": len(transcripts),
                "total_audio_duration": total_duration,
                "average_confidence": avg_confidence,
                "sentiment_distribution": sentiment_counts,
                "errors_count": len(session.get('errors', [])),
                "join_attempts": session.get('join_attempts', 0),
                "created_at": session.get('created_at'),
                "started_at": session.get('started_at'),
                "ended_at": session.get('ended_at')
            }
            
            logger.info(f"✅ Generated analytics for session: {session_id}")
            
            return analytics
            
        except Exception as e:
            logger.error(f"❌ Error generating analytics: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to generate analytics"
            }
    
    # ==================== Cleanup ====================
    
    def delete_session(self, session_id: str) -> Dict[str, Any]:
        """
        Delete session and all related data
        
        Args:
            session_id: Session identifier
            
        Returns:
            Deletion result
        """
        try:
            if self.sessions_collection is None or self.transcripts_collection is None or self.audio_chunks_collection is None:
                raise RuntimeError("Collections not initialized")
            
            # Delete session
            session_result = self.sessions_collection.delete_one({"session_id": session_id})
            
            # Delete transcripts
            transcripts_result = self.transcripts_collection.delete_many({"session_id": session_id})
            
            # Delete audio chunks
            chunks_result = self.audio_chunks_collection.delete_many({"session_id": session_id})
            
            logger.info(f"✅ Deleted session: {session_id}")
            logger.info(f"   Sessions deleted: {session_result.deleted_count}")
            logger.info(f"   Transcripts deleted: {transcripts_result.deleted_count}")
            logger.info(f"   Audio chunks deleted: {chunks_result.deleted_count}")
            
            return {
                "success": True,
                "message": "Session deleted successfully",
                "sessions_deleted": session_result.deleted_count,
                "transcripts_deleted": transcripts_result.deleted_count,
                "audio_chunks_deleted": chunks_result.deleted_count
            }
            
        except Exception as e:
            logger.error(f"❌ Error deleting session: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to delete session"
            }


# Test the repository
if __name__ == "__main__":
    repo = MeetSessionRepository()
    
    # Test create session
    session = repo.create_session({
        "interview_id": "test_interview_001",
        "meet_url": "https://meet.google.com/test",
        "bot_email": "bot@example.com"
    })
    
    print(f"Created session: {session.get('session_id')}")
    
    # Test update session
    repo.update_session(session['session_id'], {
        "session_status": "recording",
        "started_at": datetime.utcnow()
    })
    
    # Test get session
    retrieved = repo.get_session(session['session_id'])
    print(f"Retrieved session status: {retrieved.get('session_status')}")
    
    # Test save transcript
    transcript = repo.save_transcript({
        "session_id": session['session_id'],
        "interview_id": "test_interview_001",
        "raw_transcription": "This is a test transcription.",
        "cleaned_transcription": "This is a test transcription.",
        "confidence_score": 0.95
    })
    
    print(f"Saved transcript: {transcript.get('chunk_id')}")
    
    # Test analytics
    analytics = repo.get_session_analytics(session['session_id'])
    print(f"Analytics: {analytics}")
