"""
MongoDB Connection Test - Verify resumate database connectivity
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def test_mongodb_connection():
    """Test MongoDB connection and basic operations"""
    print("=" * 80)
    print("MONGODB CONNECTION TEST")
    print("=" * 80)
    
    try:
        # Get MongoDB connection details
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
        
        print(f"\n📡 Connecting to MongoDB...")
        print(f"   URI: {mongo_uri}")
        print(f"   Database: {mongo_db_name}")
        
        # Connect to MongoDB with timeout
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000
        )
        
        # Test connection
        print("\n🔍 Testing connection...")
        client.admin.command('ping')
        print("✅ MongoDB connection successful!")
        
        # Get database
        db = client[mongo_db_name]
        
        # List collections
        print(f"\n📂 Collections in '{mongo_db_name}' database:")
        collections = db.list_collection_names()
        if collections:
            for idx, collection in enumerate(collections, 1):
                count = db[collection].count_documents({})
                print(f"   {idx}. {collection}: {count} documents")
        else:
            print("   (No collections found)")
        
        # Test write operation
        print(f"\n💾 Testing WRITE operation...")
        test_collection = db['test_connection']
        test_doc = {
            'test_id': 'connection_test_001',
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'success',
            'message': 'MongoDB connection test successful'
        }
        
        result = test_collection.insert_one(test_doc)
        print(f"✅ Write successful! Inserted ID: {result.inserted_id}")
        
        # Test read operation
        print(f"\n📖 Testing READ operation...")
        retrieved_doc = test_collection.find_one({'test_id': 'connection_test_001'})
        if retrieved_doc:
            print(f"✅ Read successful!")
            print(f"   Document: {retrieved_doc}")
        else:
            print("❌ Read failed - document not found")
        
        # Test update operation
        print(f"\n✏️ Testing UPDATE operation...")
        update_result = test_collection.update_one(
            {'test_id': 'connection_test_001'},
            {'$set': {'updated_at': datetime.utcnow().isoformat(), 'update_count': 1}}
        )
        print(f"✅ Update successful! Modified: {update_result.modified_count} document(s)")
        
        # Test delete operation
        print(f"\n🗑️ Testing DELETE operation...")
        delete_result = test_collection.delete_one({'test_id': 'connection_test_001'})
        print(f"✅ Delete successful! Deleted: {delete_result.deleted_count} document(s)")
        
        # Check TTS collection
        print(f"\n🔊 Checking TTS Audio collection...")
        tts_collection = db['tts_audio']
        tts_count = tts_collection.count_documents({})
        print(f"   Total TTS audio files: {tts_count}")
        
        if tts_count > 0:
            # Get sample TTS document
            sample_tts = tts_collection.find_one()
            print(f"   Sample TTS ID: {sample_tts.get('tts_id', 'N/A')}")
            print(f"   Voice: {sample_tts.get('voice_name', 'N/A')}")
            print(f"   Created: {sample_tts.get('created_at', 'N/A')}")
        
        # Check Meeting Bots collection
        print(f"\n🤖 Checking Meeting Bots collection...")
        bots_collection = db['meeting_bots']
        bots_count = bots_collection.count_documents({})
        print(f"   Total bot sessions: {bots_count}")
        
        if bots_count > 0:
            # Get sample bot document
            sample_bot = bots_collection.find_one()
            print(f"   Sample Bot ID: {sample_bot.get('bot_id', 'N/A')}")
            print(f"   Platform: {sample_bot.get('platform', 'N/A')}")
            print(f"   Status: {sample_bot.get('status', 'N/A')}")
        
        # Database stats
        print(f"\n📊 Database Statistics:")
        stats = db.command('dbstats')
        print(f"   Database: {stats['db']}")
        print(f"   Collections: {stats['collections']}")
        print(f"   Data Size: {stats['dataSize'] / 1024 / 1024:.2f} MB")
        print(f"   Storage Size: {stats['storageSize'] / 1024 / 1024:.2f} MB")
        
        # Close connection
        client.close()
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED - MongoDB is working perfectly!")
        print("=" * 80)
        return True
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ ERROR: {str(e)}")
        print("=" * 80)
        print("\n💡 Troubleshooting:")
        print("   1. Make sure MongoDB is running:")
        print("      - Windows: Check Services (services.msc) for MongoDB")
        print("      - Or run: mongod --dbpath <your_data_path>")
        print("   2. Check .env file has correct MONGO_URI and MONGO_DB_NAME")
        print("   3. Verify port 27017 is not blocked by firewall")
        return False

if __name__ == "__main__":
    test_mongodb_connection()
