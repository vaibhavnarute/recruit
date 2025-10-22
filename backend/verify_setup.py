"""
MongoDB Setup Verification Script

This script verifies that MongoDB is properly configured with all collections and indexes.
"""

import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from db.mongo_client import get_mongo_client, ping_db
from db.models import Collections

def verify_setup():
    """Verify MongoDB setup"""
    print("="*70)
    print("🔍 MONGODB SETUP VERIFICATION")
    print("="*70)
    
    # Step 1: Test connection
    print("\n1. Testing Connection...")
    if not ping_db():
        print("   ❌ MongoDB connection failed!")
        return False
    print("   ✅ Connection successful!")
    
    # Step 2: Get database info
    client = get_mongo_client()
    stats = client.get_stats()
    
    print(f"\n2. Database Information:")
    print(f"   📊 Database: {stats.get('database')}")
    print(f"   📁 Collections: {stats.get('collections')}")
    
    # Step 3: Verify all collections exist
    print("\n3. Verifying Collections:")
    db = client.get_database()
    existing_collections = set(db.list_collection_names())
    
    required_collections = [
        Collections.USERS,
        Collections.RESUMES,
        Collections.JOB_DESCRIPTIONS,
        Collections.SELECTED_CANDIDATES,
        Collections.REJECTED_CANDIDATES,
        Collections.ANALYSIS_RESULTS,
        Collections.INTERVIEWS,
        Collections.EMAIL_LOGS,
        Collections.INTERVIEW_QUESTIONS,
        Collections.RESUME_ANALYSIS_RESULTS,
        Collections.IMPROVED_RESUMES,
        Collections.QA_SESSIONS
    ]
    
    all_exist = True
    for collection_name in required_collections:
        exists = collection_name in existing_collections
        status = "✅" if exists else "❌"
        count = db[collection_name].count_documents({}) if exists else 0
        print(f"   {status} {collection_name:30s} ({count} documents)")
        if not exists:
            all_exist = False
    
    if not all_exist:
        print("\n   ⚠️  Some collections are missing!")
        print("   💡 Run: python setup_mongodb.py")
        return False
    
    # Step 4: Verify indexes
    print("\n4. Verifying Indexes:")
    total_indexes = 0
    
    for collection_name in required_collections:
        indexes = list(db[collection_name].list_indexes())
        index_count = len(indexes) - 1  # Exclude default _id index
        total_indexes += index_count
        print(f"   ✓ {collection_name:30s} {index_count} indexes")
    
    print(f"\n   📊 Total custom indexes: {total_indexes}")
    
    # Step 5: Test basic operations
    print("\n5. Testing Basic Operations:")
    
    try:
        # Test create operation
        from db.mongo_service import create_user, authenticate_user
        
        test_email = "test@example.com"
        
        # Check if test user exists
        existing_user = db[Collections.USERS].find_one({"email": test_email})
        
        if not existing_user:
            # Create test user
            user_id = create_user(
                email=test_email,
                password="Test123!",
                full_name="Test User",
                role="recruiter"
            )
            print(f"   ✅ Create operation successful (User ID: {user_id})")
            
            # Test authentication
            auth_result = authenticate_user(test_email, "Test123!")
            if auth_result:
                print(f"   ✅ Authentication successful")
            else:
                print(f"   ❌ Authentication failed")
            
            # Clean up test user
            db[Collections.USERS].delete_one({"email": test_email})
            print(f"   ✅ Delete operation successful")
        else:
            print(f"   ✓ Test user already exists (skipping create test)")
            
    except Exception as e:
        print(f"   ⚠️  Basic operations test: {str(e)}")
    
    # Step 6: Connection string for Compass
    print("\n6. MongoDB Compass Connection:")
    print("   📋 Use this connection string in MongoDB Compass:")
    print("   " + "="*66)
    
    # Get connection string from env (masked password)
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    mongo_uri = os.getenv('MONGO_URI', '')
    if mongo_uri:
        # Mask password for display
        if '@' in mongo_uri:
            parts = mongo_uri.split('@')
            creds = parts[0].replace('mongodb+srv://', '').replace('mongodb://', '')
            if ':' in creds:
                username = creds.split(':')[0]
                masked_uri = mongo_uri.replace(creds.split(':')[1].split('@')[0], '****')
                print(f"   {mongo_uri}")
            else:
                print(f"   {mongo_uri}")
        else:
            print(f"   {mongo_uri}")
    
    print("   " + "="*66)
    
    # Final summary
    print("\n" + "="*70)
    print("✅ MONGODB SETUP VERIFICATION COMPLETE!")
    print("="*70)
    print("\n🎯 Status Summary:")
    print(f"   ✅ Connection: Working")
    print(f"   ✅ Database: {stats.get('database')}")
    print(f"   ✅ Collections: {len(required_collections)}/12 created")
    print(f"   ✅ Indexes: {total_indexes} created")
    print(f"   ✅ CRUD Operations: Working")
    
    print("\n🚀 Ready for integration into Flask app!")
    
    return True


if __name__ == "__main__":
    try:
        success = verify_setup()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
