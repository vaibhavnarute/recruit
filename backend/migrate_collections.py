"""
Database Migration Script

Migrates existing data to new collections:
- meet_transcripts → transcriptions
- Creates meetings collection from interviews
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def migrate_transcripts():
    """Migrate meet_transcripts to transcriptions collection"""
    print("\n" + "=" * 80)
    print("MIGRATING TRANSCRIPTS")
    print("=" * 80)
    
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
    client = MongoClient(mongo_uri)
    db = client[mongo_db_name]
    
    old_collection = db['meet_transcripts']
    new_collection = db['transcriptions']
    
    # Get all old transcripts
    old_transcripts = list(old_collection.find())
    print(f"\nFound {len(old_transcripts)} transcripts in meet_transcripts")
    
    if len(old_transcripts) == 0:
        print("✅ No transcripts to migrate")
        client.close()
        return
    
    migrated = 0
    skipped = 0
    
    for old_trans in old_transcripts:
        try:
            chunk_id = old_trans.get('chunk_id')
            if not chunk_id:
                print(f"⚠️  Skipping transcript with no chunk_id")
                skipped += 1
                continue
            
            # Check if already migrated
            if new_collection.find_one({"chunk_id": chunk_id}):
                print(f"⏭️  Already migrated: {chunk_id}")
                skipped += 1
                continue
            
            # Create new document
            new_doc = {
                "transcription_id": f"trans_{chunk_id}",
                "session_id": old_trans.get('session_id', ''),
                "meeting_id": None,
                "interview_id": old_trans.get('interview_id'),
                "chunk_id": chunk_id,
                "audio_chunk_number": old_trans.get('chunk_number', 0),
                
                # Audio metadata
                "audio_format": old_trans.get('audio_format', 'mp3'),
                "audio_duration": old_trans.get('duration'),
                "audio_size_bytes": old_trans.get('audio_size'),
                
                # Transcription data
                "raw_transcription": old_trans.get('raw_transcription', ''),
                "cleaned_transcription": old_trans.get('cleaned_transcription', old_trans.get('raw_transcription', '')),
                "language_detected": old_trans.get('language_detected', old_trans.get('language', 'en')),
                "confidence_score": old_trans.get('confidence_score', old_trans.get('confidence', 0.5)),
                
                # Analysis
                "sentiment": old_trans.get('sentiment', 'neutral'),
                "speaker_detected": old_trans.get('speaker_detected', old_trans.get('speaker', '')),
                "key_points": old_trans.get('key_points', []),
                "technical_terms": old_trans.get('technical_terms', []),
                "questions_asked": [],
                "answers_given": [],
                
                # Processing
                "model": old_trans.get('model', 'whisper-large-v3'),
                "llm_model": old_trans.get('llm_model'),
                "workflow": old_trans.get('workflow', 'langgraph'),
                "mcp_optimized": old_trans.get('mcp_optimized', True),
                "processing_time_ms": old_trans.get('processing_time_ms', old_trans.get('processing_time', 0.0)),
                "tokens_used": old_trans.get('tokens_used'),
                
                # Context
                "question_context": old_trans.get('question_context', old_trans.get('context', '')),
                "interview_stage": old_trans.get('interview_stage'),
                
                # Timestamps
                "transcribed_at": old_trans.get('transcribed_at', old_trans.get('timestamp', datetime.utcnow())),
                "analyzed_at": old_trans.get('analyzed_at'),
                "created_at": old_trans.get('created_at', datetime.utcnow()),
                "updated_at": datetime.utcnow(),
                
                # Errors
                "has_errors": old_trans.get('has_errors', False),
                "errors": old_trans.get('errors', []),
                
                "metadata": old_trans.get('metadata', {})
            }
            
            # Insert into new collection
            new_collection.insert_one(new_doc)
            migrated += 1
            print(f"✅ Migrated: {chunk_id}")
            
        except Exception as e:
            print(f"❌ Error migrating transcript: {str(e)}")
            skipped += 1
    
    print(f"\n📊 Migration Summary:")
    print(f"   Migrated: {migrated}")
    print(f"   Skipped: {skipped}")
    print(f"   Total: {len(old_transcripts)}")
    
    client.close()


def create_sample_meeting():
    """Create a sample meeting in the new collection"""
    print("\n" + "=" * 80)
    print("CREATING SAMPLE MEETING")
    print("=" * 80)
    
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
    client = MongoClient(mongo_uri)
    db = client[mongo_db_name]
    
    meetings_collection = db['meetings']
    
    # Check if sample already exists
    if meetings_collection.find_one({"meeting_id": "meet_sample_001"}):
        print("✅ Sample meeting already exists")
        client.close()
        return
    
    sample_meeting = {
        "meeting_id": "meet_sample_001",
        "session_id": "session_sample_001",
        "room_id": "room_001",
        
        "meeting_title": "Sample Interview Meeting",
        "meeting_type": "interview",
        "meeting_link": "https://meet.google.com/xxx-yyyy-zzz",
        "meeting_platform": "google_meet",
        
        "host_email": "hr@company.com",
        "host_name": "HR Manager",
        "participants": [
            {"email": "hr@company.com", "name": "HR Manager", "role": "host"},
            {"email": "candidate@email.com", "name": "Candidate", "role": "interviewee"}
        ],
        "expected_participants": 2,
        "actual_participants": 0,
        
        "interview_id": None,
        "candidate_email": "candidate@email.com",
        "candidate_name": "John Doe",
        "job_id": None,
        
        "status": "scheduled",
        "is_recording": False,
        "recording_enabled": True,
        "recording_url": None,
        
        "scheduled_at": datetime.utcnow(),
        "started_at": None,
        "ended_at": None,
        "duration_minutes": None,
        "expected_duration_minutes": 60,
        
        "ai_bot_enabled": True,
        "ai_bot_name": "AI Interviewer",
        "ai_bot_email": "bot@company.com",
        "bot_join_attempts": 0,
        "bot_joined_at": None,
        "bot_left_at": None,
        
        "transcription_enabled": True,
        "total_transcriptions": 0,
        "transcription_ids": [],
        "full_transcript": None,
        
        "total_audio_chunks": 0,
        "total_participants_joined": 0,
        "participant_join_times": [],
        "average_sentiment": None,
        "key_topics": [],
        "questions_count": 0,
        "technical_score": None,
        "communication_score": None,
        
        "calendar_event_id": None,
        "calendar_link": None,
        "reminder_sent": False,
        "reminder_sent_at": None,
        
        "access_code": None,
        "is_private": True,
        "allowed_domains": ["company.com"],
        
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_activity_at": None,
        
        "join_errors": [],
        "recording_errors": [],
        "has_errors": False,
        
        "metadata": {"source": "migration_script"}
    }
    
    meetings_collection.insert_one(sample_meeting)
    print("✅ Created sample meeting: meet_sample_001")
    
    client.close()


def verify_collections():
    """Verify new collections exist and have data"""
    print("\n" + "=" * 80)
    print("VERIFYING COLLECTIONS")
    print("=" * 80)
    
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
    client = MongoClient(mongo_uri)
    db = client[mongo_db_name]
    
    # Check collections
    all_collections = db.list_collection_names()
    print(f"\n📂 All collections in database:")
    for coll in sorted(all_collections):
        count = db[coll].count_documents({})
        print(f"   {coll}: {count} documents")
    
    # Check new collections specifically
    print(f"\n✅ New Collections Status:")
    
    if 'transcriptions' in all_collections:
        trans_count = db['transcriptions'].count_documents({})
        print(f"   transcriptions: ✅ EXISTS ({trans_count} documents)")
    else:
        print(f"   transcriptions: ❌ NOT FOUND")
    
    if 'meetings' in all_collections:
        meet_count = db['meetings'].count_documents({})
        print(f"   meetings: ✅ EXISTS ({meet_count} documents)")
    else:
        print(f"   meetings: ❌ NOT FOUND")
    
    client.close()


def main():
    """Main migration function"""
    print("=" * 80)
    print("DATABASE MIGRATION - Transcriptions & Meetings")
    print("=" * 80)
    print("\nThis script will:")
    print("1. Migrate meet_transcripts → transcriptions")
    print("2. Create sample meeting in meetings collection")
    print("3. Verify new collections")
    
    response = input("\nProceed with migration? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("❌ Migration cancelled")
        return
    
    try:
        # Step 1: Migrate transcripts
        migrate_transcripts()
        
        # Step 2: Create sample meeting
        create_sample_meeting()
        
        # Step 3: Verify
        verify_collections()
        
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETE")
        print("=" * 80)
        print("\nNew collections created:")
        print("  - transcriptions: STT audio transcriptions with analysis")
        print("  - meetings: Virtual meeting sessions with participants")
        print("\nOld collections preserved:")
        print("  - meet_transcripts: Original data (backup)")
        print("  - meet_sessions: Original data (backup)")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
