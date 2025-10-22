"""
Quick MongoDB Connection Test

This script tests the MongoDB connection and lists all collections.
"""

import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from db.mongo_client import get_mongo_client, ping_db

def test_connection():
    """Test MongoDB connection and list collections"""
    print("🔍 Testing MongoDB Connection...")
    print("="*60)
    
    # Test ping
    if not ping_db():
        print("❌ MongoDB connection failed!")
        print("\n💡 Troubleshooting:")
        print("   1. Check MONGO_URI in .env file")
        print("   2. Ensure network connection")
        print("   3. Verify MongoDB Atlas/local service is running")
        return False
    
    print("✅ MongoDB connection successful!")
    
    # Get client and stats
    client = get_mongo_client()
    stats = client.get_stats()
    
    print(f"\n📊 Database: {stats.get('database')}")
    print(f"   Collections: {stats.get('collections')}")
    
    # List all collections
    db = client.get_database()  # Use get_database() method instead of .db
    collections = db.list_collection_names()
    
    print(f"\n📁 Found {len(collections)} collections:")
    for idx, collection in enumerate(collections, 1):
        count = db[collection].count_documents({})
        print(f"   {idx}. {collection:30s} ({count} documents)")
    
    return True


if __name__ == "__main__":
    try:
        success = test_connection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
