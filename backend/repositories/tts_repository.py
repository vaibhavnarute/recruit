"""
TTS Repository
Manages TTS audio storage, retrieval, and voice profiles
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TTSRepository:
    """Repository for TTS audio data and voice profiles"""
    
    def __init__(self, mongo_uri: str = None):
        """Initialize TTS repository"""
        if mongo_uri is None:
            mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        
        mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
        
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
        self.db = self.client[mongo_db_name]
        self.tts_collection = self.db['tts_audio']
        self.meetings_collection = self.db['meetings']
        self.bots_collection = self.db['meeting_bots']
        
        # Create indexes
        self._create_indexes()
        logger.info("✅ TTS Repository initialized")
    
    def _create_indexes(self):
        """Create database indexes for TTS collection"""
        try:
            # Unique index on tts_id
            self.tts_collection.create_index("tts_id", unique=True)
            
            # Indexes for querying
            self.tts_collection.create_index("session_id")
            self.tts_collection.create_index("meeting_id")
            self.tts_collection.create_index("interview_id")
            self.tts_collection.create_index("text_type")
            self.tts_collection.create_index("voice_profile")
            self.tts_collection.create_index("processing_status")
            self.tts_collection.create_index([("created_at", DESCENDING)])
            
            # Compound indexes for common queries
            self.tts_collection.create_index([
                ("meeting_id", ASCENDING),
                ("text_type", ASCENDING),
                ("created_at", DESCENDING)
            ])
            
            logger.info("✅ TTS indexes created successfully")
        except Exception as e:
            logger.error(f"❌ Error creating indexes: {str(e)}")
    
    # ==================== TTS Audio CRUD Operations ====================
    
    def create_tts_audio(self, tts_data: Dict[str, Any]) -> str:
        """
        Create new TTS audio record
        
        Args:
            tts_data: TTS audio data
            
        Returns:
            tts_id of created record
        """
        try:
            tts_id = tts_data.get('tts_id')
            
            # Set timestamps
            now = datetime.utcnow()
            tts_data['created_at'] = now
            tts_data['updated_at'] = now
            
            # Insert
            result = self.tts_collection.insert_one(tts_data)
            
            logger.info(f"✅ Created TTS audio: {tts_id}")
            return tts_id
            
        except PyMongoError as e:
            logger.error(f"❌ Error creating TTS audio: {str(e)}")
            raise
    
    def get_tts_audio(self, tts_id: str) -> Optional[Dict[str, Any]]:
        """
        Get TTS audio by ID
        
        Args:
            tts_id: TTS audio ID
            
        Returns:
            TTS audio document or None
        """
        try:
            tts_audio = self.tts_collection.find_one({"tts_id": tts_id})
            
            if tts_audio:
                logger.info(f"✅ Retrieved TTS audio: {tts_id}")
            else:
                logger.warning(f"⚠️ TTS audio not found: {tts_id}")
            
            return tts_audio
            
        except PyMongoError as e:
            logger.error(f"❌ Error retrieving TTS audio: {str(e)}")
            return None
    
    def get_tts_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all TTS audio for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            List of TTS audio documents
        """
        try:
            tts_list = list(self.tts_collection.find(
                {"session_id": session_id}
            ).sort("created_at", ASCENDING))
            
            logger.info(f"✅ Retrieved {len(tts_list)} TTS audio for session {session_id}")
            return tts_list
            
        except PyMongoError as e:
            logger.error(f"❌ Error retrieving TTS audio: {str(e)}")
            return []
    
    def get_tts_by_meeting(self, meeting_id: str) -> List[Dict[str, Any]]:
        """
        Get all TTS audio for a meeting
        
        Args:
            meeting_id: Meeting ID
            
        Returns:
            List of TTS audio documents
        """
        try:
            tts_list = list(self.tts_collection.find(
                {"meeting_id": meeting_id}
            ).sort("created_at", ASCENDING))
            
            logger.info(f"✅ Retrieved {len(tts_list)} TTS audio for meeting {meeting_id}")
            return tts_list
            
        except PyMongoError as e:
            logger.error(f"❌ Error retrieving TTS audio: {str(e)}")
            return []
    
    def get_tts_by_interview(self, interview_id: str) -> List[Dict[str, Any]]:
        """
        Get all TTS audio for an interview
        
        Args:
            interview_id: Interview ID
            
        Returns:
            List of TTS audio documents
        """
        try:
            tts_list = list(self.tts_collection.find(
                {"interview_id": interview_id}
            ).sort("created_at", ASCENDING))
            
            logger.info(f"✅ Retrieved {len(tts_list)} TTS audio for interview {interview_id}")
            return tts_list
            
        except PyMongoError as e:
            logger.error(f"❌ Error retrieving TTS audio: {str(e)}")
            return []
    
    def get_tts_by_type(self, text_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get TTS audio by text type
        
        Args:
            text_type: Text type (intro, question, followup, closing, feedback)
            limit: Maximum number of results
            
        Returns:
            List of TTS audio documents
        """
        try:
            tts_list = list(self.tts_collection.find(
                {"text_type": text_type}
            ).sort("created_at", DESCENDING).limit(limit))
            
            logger.info(f"✅ Retrieved {len(tts_list)} TTS audio of type {text_type}")
            return tts_list
            
        except PyMongoError as e:
            logger.error(f"❌ Error retrieving TTS audio: {str(e)}")
            return []
    
    def update_tts_audio(self, tts_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update TTS audio record
        
        Args:
            tts_id: TTS audio ID
            update_data: Fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data['updated_at'] = datetime.utcnow()
            
            result = self.tts_collection.update_one(
                {"tts_id": tts_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Updated TTS audio: {tts_id}")
                return True
            else:
                logger.warning(f"⚠️ No changes made to TTS audio: {tts_id}")
                return False
            
        except PyMongoError as e:
            logger.error(f"❌ Error updating TTS audio: {str(e)}")
            return False
    
    def delete_tts_audio(self, tts_id: str) -> bool:
        """
        Delete TTS audio record
        
        Args:
            tts_id: TTS audio ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.tts_collection.delete_one({"tts_id": tts_id})
            
            if result.deleted_count > 0:
                logger.info(f"✅ Deleted TTS audio: {tts_id}")
                return True
            else:
                logger.warning(f"⚠️ TTS audio not found: {tts_id}")
                return False
            
        except PyMongoError as e:
            logger.error(f"❌ Error deleting TTS audio: {str(e)}")
            return False
    
    # ==================== Voice Profile Management ====================
    
    def get_voice_profile_stats(self, voice_profile: str) -> Dict[str, Any]:
        """
        Get statistics for a voice profile
        
        Args:
            voice_profile: Voice profile name
            
        Returns:
            Statistics dictionary
        """
        try:
            pipeline = [
                {"$match": {"voice_profile": voice_profile, "success": True}},
                {"$group": {
                    "_id": "$voice_profile",
                    "total_audio": {"$sum": 1},
                    "total_duration": {"$sum": "$audio_duration_seconds"},
                    "total_size": {"$sum": "$audio_size_bytes"},
                    "avg_processing_time": {"$avg": "$processing_time_ms"},
                    "avg_duration": {"$avg": "$audio_duration_seconds"}
                }}
            ]
            
            result = list(self.tts_collection.aggregate(pipeline))
            
            if result:
                stats = result[0]
                logger.info(f"✅ Retrieved stats for voice profile: {voice_profile}")
                return {
                    "voice_profile": voice_profile,
                    "total_audio": stats.get('total_audio', 0),
                    "total_duration_seconds": stats.get('total_duration', 0),
                    "total_size_mb": stats.get('total_size', 0) / (1024 * 1024),
                    "avg_processing_time_ms": stats.get('avg_processing_time', 0),
                    "avg_duration_seconds": stats.get('avg_duration', 0)
                }
            else:
                return {
                    "voice_profile": voice_profile,
                    "total_audio": 0
                }
            
        except PyMongoError as e:
            logger.error(f"❌ Error getting voice profile stats: {str(e)}")
            return {"voice_profile": voice_profile, "error": str(e)}
    
    def get_all_voice_profiles_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all voice profiles
        
        Returns:
            List of statistics dictionaries
        """
        try:
            pipeline = [
                {"$match": {"success": True}},
                {"$group": {
                    "_id": "$voice_profile",
                    "total_audio": {"$sum": 1},
                    "total_duration": {"$sum": "$audio_duration_seconds"},
                    "total_size": {"$sum": "$audio_size_bytes"},
                    "avg_processing_time": {"$avg": "$processing_time_ms"}
                }},
                {"$sort": {"total_audio": DESCENDING}}
            ]
            
            results = list(self.tts_collection.aggregate(pipeline))
            
            stats_list = []
            for result in results:
                stats_list.append({
                    "voice_profile": result['_id'],
                    "total_audio": result.get('total_audio', 0),
                    "total_duration_seconds": result.get('total_duration', 0),
                    "total_size_mb": result.get('total_size', 0) / (1024 * 1024),
                    "avg_processing_time_ms": result.get('avg_processing_time', 0)
                })
            
            logger.info(f"✅ Retrieved stats for {len(stats_list)} voice profiles")
            return stats_list
            
        except PyMongoError as e:
            logger.error(f"❌ Error getting voice profile stats: {str(e)}")
            return []
    
    # ==================== Meeting Integration ====================
    
    def link_tts_to_meeting(self, tts_id: str, meeting_id: str) -> bool:
        """
        Link TTS audio to a meeting
        
        Args:
            tts_id: TTS audio ID
            meeting_id: Meeting ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update TTS record
            self.tts_collection.update_one(
                {"tts_id": tts_id},
                {
                    "$set": {
                        "meeting_id": meeting_id,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Update meeting record
            self.meetings_collection.update_one(
                {"meeting_id": meeting_id},
                {
                    "$push": {"tts_audio_ids": tts_id},
                    "$inc": {"total_tts_audio": 1},
                    "$set": {
                        "tts_enabled": True,
                        "last_tts_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"✅ Linked TTS {tts_id} to meeting {meeting_id}")
            return True
            
        except PyMongoError as e:
            logger.error(f"❌ Error linking TTS to meeting: {str(e)}")
            return False
    
    # ==================== Analytics ====================
    
    def get_tts_stats(self) -> Dict[str, Any]:
        """
        Get overall TTS statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            total_tts = self.tts_collection.count_documents({})
            successful_tts = self.tts_collection.count_documents({"success": True})
            failed_tts = self.tts_collection.count_documents({"success": False})
            
            # Get streaming stats
            streaming_tts = self.tts_collection.count_documents({"is_streaming": True})
            
            # Get recent TTS
            recent_tts = list(self.tts_collection.find().sort("created_at", DESCENDING).limit(10))
            
            stats = {
                "total_tts_audio": total_tts,
                "successful": successful_tts,
                "failed": failed_tts,
                "success_rate": (successful_tts / total_tts * 100) if total_tts > 0 else 0,
                "streaming_tts": streaming_tts,
                "recent_tts_count": len(recent_tts)
            }
            
            logger.info(f"✅ Retrieved TTS stats: {total_tts} total")
            return stats
            
        except PyMongoError as e:
            logger.error(f"❌ Error getting TTS stats: {str(e)}")
            return {"error": str(e)}
    
    def get_meeting_tts_summary(self, meeting_id: str) -> Dict[str, Any]:
        """
        Get TTS summary for a meeting
        
        Args:
            meeting_id: Meeting ID
            
        Returns:
            Summary dictionary
        """
        try:
            tts_list = self.get_tts_by_meeting(meeting_id)
            
            if not tts_list:
                return {
                    "meeting_id": meeting_id,
                    "total_tts": 0
                }
            
            total_duration = sum(tts.get('audio_duration_seconds', 0) for tts in tts_list)
            total_size = sum(tts.get('audio_size_bytes', 0) for tts in tts_list)
            
            # Count by type
            type_counts = {}
            for tts in tts_list:
                text_type = tts.get('text_type', 'unknown')
                type_counts[text_type] = type_counts.get(text_type, 0) + 1
            
            # Get voice profiles used
            voice_profiles = list(set(tts.get('voice_profile') for tts in tts_list if tts.get('voice_profile')))
            
            summary = {
                "meeting_id": meeting_id,
                "total_tts": len(tts_list),
                "total_duration_seconds": total_duration,
                "total_size_mb": total_size / (1024 * 1024),
                "type_counts": type_counts,
                "voice_profiles_used": voice_profiles,
                "first_tts_at": tts_list[0].get('created_at') if tts_list else None,
                "last_tts_at": tts_list[-1].get('created_at') if tts_list else None
            }
            
            logger.info(f"✅ Retrieved TTS summary for meeting {meeting_id}")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error getting meeting TTS summary: {str(e)}")
            return {"meeting_id": meeting_id, "error": str(e)}
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()
        logger.info("✅ Closed TTS Repository connection")


if __name__ == "__main__":
    # Test the repository
    print("=" * 80)
    print("Testing TTS Repository")
    print("=" * 80)
    
    repo = TTSRepository()
    
    # Get stats
    stats = repo.get_tts_stats()
    print(f"\n📊 TTS Stats:")
    print(f"  Total TTS Audio: {stats.get('total_tts_audio', 0)}")
    print(f"  Successful: {stats.get('successful', 0)}")
    print(f"  Failed: {stats.get('failed', 0)}")
    print(f"  Success Rate: {stats.get('success_rate', 0):.2f}%")
    
    # Get voice profile stats
    voice_stats = repo.get_all_voice_profiles_stats()
    if voice_stats:
        print(f"\n🎤 Voice Profile Stats:")
        for vs in voice_stats:
            print(f"  {vs['voice_profile']}: {vs['total_audio']} audio files")
    
    repo.close()
    print("\n✅ Test complete")
