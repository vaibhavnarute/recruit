"""
Test Firebase Authentication Integration

This script tests the Firebase auth service and MongoDB sync
"""

import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from services.firebase_auth_service import FirebaseAuthService
from db.models import UserRole
from db.mongo_client import ping_db

def test_firebase_auth():
    """Test Firebase authentication integration"""
    print("="*80)
    print("🧪 TESTING FIREBASE AUTHENTICATION INTEGRATION")
    print("="*80)
    
    # Test MongoDB connection
    print("\n1. Testing MongoDB Connection...")
    if not ping_db():
        print("❌ MongoDB connection failed!")
        return False
    print("✅ MongoDB connected")
    
    # Initialize service
    print("\n2. Initializing Firebase Auth Service...")
    try:
        service = FirebaseAuthService()
        print("✅ Service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize service: {str(e)}")
        return False
    
    # Test 1: Register HR user
    print("\n3. Testing HR User Registration...")
    try:
        hr_user = service.register_user_with_role(
            firebase_uid="test-firebase-hr-123",
            email="hr@testcompany.com",
            full_name="HR Manager Test",
            role=UserRole.HR,
            company="Test Company Inc.",
            phone="+1234567890"
        )
        
        if hr_user:
            print("✅ HR user registered successfully")
            print(f"   Email: {hr_user['email']}")
            print(f"   Role: {hr_user['role']}")
            print(f"   Company: {hr_user.get('company')}")
        else:
            print("❌ Failed to register HR user")
            return False
    except Exception as e:
        print(f"❌ HR registration error: {str(e)}")
        return False
    
    # Test 2: Register Employee user
    print("\n4. Testing Employee User Registration...")
    try:
        employee_user = service.register_user_with_role(
            firebase_uid="test-firebase-emp-456",
            email="employee@testcompany.com",
            full_name="John Doe Employee",
            role=UserRole.EMPLOYEE,
            phone="+0987654321"
        )
        
        if employee_user:
            print("✅ Employee user registered successfully")
            print(f"   Email: {employee_user['email']}")
            print(f"   Role: {employee_user['role']}")
        else:
            print("❌ Failed to register employee user")
            return False
    except Exception as e:
        print(f"❌ Employee registration error: {str(e)}")
        return False
    
    # Test 3: Login user
    print("\n5. Testing User Login...")
    try:
        logged_in_user = service.login_user(
            firebase_uid="test-firebase-hr-123",
            email="hr@testcompany.com"
        )
        
        if logged_in_user:
            print("✅ User login successful")
            print(f"   Email: {logged_in_user['email']}")
            print(f"   Last Login: {logged_in_user.get('last_login')}")
        else:
            print("❌ Failed to login user")
            return False
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return False
    
    # Test 4: Get user by Firebase UID
    print("\n6. Testing Get User by Firebase UID...")
    try:
        fetched_user = service.get_user_by_firebase_uid("test-firebase-hr-123")
        
        if fetched_user:
            print("✅ User fetched successfully")
            print(f"   Email: {fetched_user['email']}")
            print(f"   MongoDB ID: {fetched_user['_id']}")
        else:
            print("❌ Failed to fetch user")
            return False
    except Exception as e:
        print(f"❌ Fetch error: {str(e)}")
        return False
    
    # Test 5: Update user role
    print("\n7. Testing Update User Role...")
    try:
        success = service.update_user_role(
            firebase_uid="test-firebase-emp-456",
            role=UserRole.HR
        )
        
        if success:
            print("✅ Role updated successfully")
            updated_user = service.get_user_by_firebase_uid("test-firebase-emp-456")
            print(f"   New Role: {updated_user['role']}")
        else:
            print("❌ Failed to update role")
            return False
    except Exception as e:
        print(f"❌ Update role error: {str(e)}")
        return False
    
    # Test 6: Get users by role
    print("\n8. Testing Get Users by Role...")
    try:
        hr_users = service.get_users_by_role(UserRole.HR)
        print(f"✅ Found {len(hr_users)} HR users")
        
        for user in hr_users:
            print(f"   - {user['email']} ({user['role']})")
    except Exception as e:
        print(f"❌ Get users by role error: {str(e)}")
        return False
    
    print("\n" + "="*80)
    print("✅ ALL FIREBASE AUTH TESTS PASSED!")
    print("="*80)
    return True


if __name__ == "__main__":
    try:
        success = test_firebase_auth()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
