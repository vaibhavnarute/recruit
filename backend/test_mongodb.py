"""
Quick MongoDB Connection Test

Run this to verify MongoDB is working before running the full test suite
"""

import logging
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.mongo_client import get_db, ping_db, get_collection
from db.models import Collections

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_mongodb():
    """Test MongoDB connection and operations"""
    print("\n" + "="*80)
    print("🧪 MONGODB CONNECTION TEST")
    print("="*80 + "\n")
    
    try:
        # Test 1: Ping
        print("Test 1: Ping MongoDB...")
        if ping_db():
            print("✅ PASS: MongoDB is reachable\n")
        else:
            print("❌ FAIL: Cannot ping MongoDB\n")
            return False
        
        # Test 2: Get database
        print("Test 2: Get database...")
        db = get_db()
        print(f"✅ PASS: Connected to database '{db.name}'\n")
        
        # Test 3: List collections
        print("Test 3: List collections...")
        collections = db.list_collection_names()
        print(f"📂 Found {len(collections)} collections:")
        for col in collections:
            print(f"   - {col}")
        print()
        
        # Test 4: Get interviews collection
        print("Test 4: Get interviews collection...")
        interviews_col = get_collection(Collections.INTERVIEWS)
        if interviews_col is not None:
            print(f"✅ PASS: Got collection '{interviews_col.name}'")
            
            # Count documents
            count = interviews_col.count_documents({})
            print(f"📊 Collection has {count} documents\n")
        else:
            print("❌ FAIL: interviews collection is None\n")
            return False
        
        # Test 5: Test write permissions (optional - commented out to avoid test data)
        print("Test 5: Test write permissions...")
        import uuid
        test_room_id = f"test-{str(uuid.uuid4())[:8]}"
        test_doc = {
            "test": True,
            "message": "MongoDB connection test",
            "room_id": test_room_id,  # Required by unique index
            "interview_id": str(uuid.uuid4())
        }
        result = interviews_col.insert_one(test_doc)
        print(f"✅ PASS: Can write to database (inserted ID: {result.inserted_id})")
        
        # Clean up test document
        interviews_col.delete_one({"_id": result.inserted_id})
        print(f"🧹 Cleaned up test document\n")
        
        print("="*80)
        print("✅ ALL TESTS PASSED - MongoDB is working correctly!")
        print("="*80 + "\n")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}\n")
        import traceback
        print("Traceback:")
        print(traceback.format_exc())
        print("="*80 + "\n")
        return False

if __name__ == "__main__":
    success = test_mongodb()
    sys.exit(0 if success else 1)
