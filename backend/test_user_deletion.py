"""
Test script for user deletion with Firebase Auth cleanup

This script demonstrates:
1. Creating a test user in MongoDB
2. Deleting the user from MongoDB
3. Automatic cleanup from Firebase Auth (if configured)
"""

import logging
import sys
from services.firebase_auth_service import FirebaseAuthService
from db.models import UserRole

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_user_deletion():
    """Test user deletion with Firebase cleanup"""
    
    print("\n" + "="*80)
    print("🧪 TEST: User Deletion with Firebase Auth Cleanup")
    print("="*80 + "\n")
    
    service = FirebaseAuthService()
    
    # Step 1: Create a test user
    print("📝 Step 1: Creating test user...")
    test_user = service.register_user_with_role(
        firebase_uid="test-firebase-uid-12345",
        email="test.deletion@example.com",
        full_name="Test User for Deletion",
        role=UserRole.EMPLOYEE,
        phone="+1234567890"
    )
    
    if test_user:
        print(f"✅ Test user created: {test_user['email']}")
        print(f"   MongoDB ID: {test_user['_id']}")
        print(f"   Firebase UID: {test_user.get('firebase_uid', 'N/A')}")
        user_id = test_user['_id']
    else:
        print("❌ Failed to create test user")
        return
    
    # Step 2: Verify user exists
    print("\n📋 Step 2: Verifying user exists...")
    existing_user = service.get_user_by_firebase_uid("test-firebase-uid-12345")
    if existing_user:
        print(f"✅ User found in MongoDB: {existing_user['email']}")
    else:
        print("❌ User not found in MongoDB")
        return
    
    # Step 3: Delete user
    print("\n🗑️  Step 3: Deleting user from MongoDB and Firebase Auth...")
    result = service.delete_user(user_id)
    
    print("\n📊 Deletion Result:")
    print(f"   Overall Success: {result['success']}")
    print(f"   MongoDB Deleted: {result['mongodb_deleted']}")
    print(f"   Firebase Deleted: {result['firebase_deleted']}")
    print(f"   Firebase Message: {result['firebase_message']}")
    print(f"   Message: {result['message']}")
    
    if result.get('firebase_uid'):
        print(f"   Firebase UID: {result['firebase_uid']}")
    
    # Step 4: Verify user is deleted
    print("\n🔍 Step 4: Verifying user is deleted...")
    deleted_user = service.get_user_by_firebase_uid("test-firebase-uid-12345")
    if deleted_user:
        print("❌ User still exists in MongoDB (unexpected)")
    else:
        print("✅ User successfully deleted from MongoDB")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETED")
    print("="*80 + "\n")
    
    # Summary
    print("📌 Summary:")
    print("   - User was created in MongoDB")
    print("   - User was deleted from MongoDB")
    if result['firebase_deleted']:
        print("   - User was deleted from Firebase Auth ✅")
    elif result.get('firebase_uid'):
        print("   - User had Firebase UID but Firebase Admin SDK not configured ⚠️")
        print("   - Install firebase-admin and configure service account for full cleanup")
    else:
        print("   - User had no Firebase UID (local user only)")
    
    print("\n💡 Note:")
    print("   To enable automatic Firebase Auth deletion:")
    print("   1. Install: pip install firebase-admin")
    print("   2. Download service account JSON from Firebase Console")
    print("   3. Set FIREBASE_SERVICE_ACCOUNT_PATH in .env")
    print("   4. Users will be deleted from both MongoDB and Firebase Auth automatically!")


def test_delete_by_email():
    """Test deletion by email"""
    
    print("\n" + "="*80)
    print("🧪 TEST: Delete User by Email")
    print("="*80 + "\n")
    
    service = FirebaseAuthService()
    
    # Create test user
    print("📝 Creating test user...")
    test_user = service.register_user_with_role(
        firebase_uid="test-email-delete-789",
        email="test.email.delete@example.com",
        full_name="Test Email Delete",
        role=UserRole.HR,
        company="Test Company"
    )
    
    if not test_user:
        print("❌ Failed to create test user")
        return
    
    print(f"✅ Test user created: {test_user['email']}")
    
    # Delete by email
    print(f"\n🗑️  Deleting user by email: {test_user['email']}")
    result = service.delete_user_by_email(test_user['email'])
    
    print(f"\n📊 Deletion Result:")
    print(f"   Success: {result['success']}")
    print(f"   MongoDB Deleted: {result['mongodb_deleted']}")
    print(f"   Firebase Deleted: {result['firebase_deleted']}")
    print(f"   Message: {result['message']}")
    
    # Verify
    verify = service.get_user_by_firebase_uid("test-email-delete-789")
    if not verify:
        print("\n✅ User successfully deleted")
    else:
        print("\n❌ User still exists")


if __name__ == "__main__":
    try:
        # Run tests
        test_user_deletion()
        print("\n" + "-"*80 + "\n")
        test_delete_by_email()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        logger.exception("Test error:")
        sys.exit(1)
