"""
Database Migration: Add Auto-Bot Join Fields
Date: February 5, 2026
Purpose: Add new fields for automatic bot joining functionality
"""

import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI') or os.getenv('MONGODB_URI')

if not MONGO_URI:
    print("❌ ERROR: MONGO_URI not found in environment variables")
    sys.exit(1)

print("="*80)
print("🔄 DATABASE MIGRATION: Add Auto-Bot Join Fields")
print("="*80)
print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"🗄️  Database: {MONGO_URI.split('@')[1] if '@' in MONGO_URI else 'localhost'}")
print("="*80)

try:
    # Connect to MongoDB
    print("\n🔌 Connecting to MongoDB...")
    client = MongoClient(MONGO_URI)
    db = client['resumate']  # Database name
    
    # Test connection
    client.admin.command('ping')
    print("✅ Connected to MongoDB successfully")
    
    # Migration 1: Update interviews collection
    print("\n📊 Migration 1: Updating 'interviews' collection...")
    interviews_collection = db['interviews']
    
    # Count existing documents
    total_interviews = interviews_collection.count_documents({})
    print(f"   Found {total_interviews} interview documents")
    
    if total_interviews > 0:
        # Add new fields to existing documents
        result = interviews_collection.update_many(
            {
                "$or": [
                    {"auto_start_bot": {"$exists": False}},
                    {"bot_join_status": {"$exists": False}}
                ]
            },
            {
                "$set": {
                    "auto_start_bot": False,  # Default to False for existing interviews
                    "bot_join_status": "not_applicable",
                    "candidate_joined_at": None,
                    "bot_joined_at": None,
                    "auto_join_token": None,
                    "migration_applied_at": datetime.now()
                }
            }
        )
        print(f"   ✅ Updated {result.modified_count} interview documents")
    else:
        print("   ℹ️  No existing interviews to update")
    
    # Migration 2: Update meet_sessions collection
    print("\n📊 Migration 2: Updating 'meet_sessions' collection...")
    sessions_collection = db['meet_sessions']
    
    # Count existing documents
    total_sessions = sessions_collection.count_documents({})
    print(f"   Found {total_sessions} session documents")
    
    if total_sessions > 0:
        # Add new fields to existing sessions
        result = sessions_collection.update_many(
            {
                "$or": [
                    {"triggered_by": {"$exists": False}},
                    {"trigger_timestamp": {"$exists": False}}
                ]
            },
            {
                "$set": {
                    "triggered_by": "manual",  # Existing sessions were manual
                    "trigger_timestamp": None,
                    "migration_applied_at": datetime.now()
                }
            }
        )
        print(f"   ✅ Updated {result.modified_count} session documents")
    else:
        print("   ℹ️  No existing sessions to update")
    
    # Create indexes for new fields
    print("\n📑 Creating indexes for new fields...")
    
    # Index on auto_join_token for quick lookups
    interviews_collection.create_index("auto_join_token", sparse=True)
    print("   ✅ Created index on 'auto_join_token'")
    
    # Index on bot_join_status for filtering
    interviews_collection.create_index("bot_join_status")
    print("   ✅ Created index on 'bot_join_status'")
    
    # Index on triggered_by for analytics
    sessions_collection.create_index("triggered_by")
    print("   ✅ Created index on 'triggered_by'")
    
    # Verification
    print("\n🔍 Verifying migration...")
    
    # Check interviews collection
    sample_interview = interviews_collection.find_one({})
    if sample_interview:
        required_fields = ['auto_start_bot', 'bot_join_status', 'candidate_joined_at', 
                          'bot_joined_at', 'auto_join_token']
        missing_fields = [f for f in required_fields if f not in sample_interview]
        
        if missing_fields:
            print(f"   ⚠️  Warning: Missing fields in interviews: {missing_fields}")
        else:
            print("   ✅ All required fields present in 'interviews' collection")
    
    # Check sessions collection
    sample_session = sessions_collection.find_one({})
    if sample_session:
        required_fields = ['triggered_by', 'trigger_timestamp']
        missing_fields = [f for f in required_fields if f not in sample_session]
        
        if missing_fields:
            print(f"   ⚠️  Warning: Missing fields in sessions: {missing_fields}")
        else:
            print("   ✅ All required fields present in 'meet_sessions' collection")
    
    # Summary
    print("\n" + "="*80)
    print("✅ MIGRATION COMPLETED SUCCESSFULLY")
    print("="*80)
    print("\n📋 Summary:")
    print(f"   • Interviews updated: {result.modified_count if total_interviews > 0 else 0}")
    print(f"   • Sessions updated: {result.modified_count if total_sessions > 0 else 0}")
    print(f"   • New indexes created: 3")
    print(f"   • Migration timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n✨ Database is ready for auto-bot join functionality!")
    print("="*80)
    
except Exception as e:
    print(f"\n❌ ERROR during migration: {str(e)}")
    print("\n⚠️  Migration failed! Please check the error and try again.")
    sys.exit(1)
finally:
    if 'client' in locals():
        client.close()
        print("\n🔌 Disconnected from MongoDB")

print("\n✅ Migration script completed successfully!\n")
