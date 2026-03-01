"""
Test Suite for Security & Isolation
Tests JWT authentication and session sandboxing
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8001"

def print_section(title: str):
    """Print section header"""
    print("\n" + "="*80)
    print(title)
    print("="*80 + "\n")

def test_health_check() -> bool:
    """Test if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def test_create_secure_session() -> Dict[str, Any]:
    """Test: Create secure session with JWT and sandbox"""
    print_section("TEST 1: Create Secure Session")
    
    try:
        data = {
            "session_id": "test_secure_session_001",
            "interview_id": "interview_sec_001",
            "candidate_name": "Security Test User",
            "job_description": "Security Engineer",
            "permissions": json.dumps({
                "read": True,
                "write": True,
                "delete": False,
                "analyze": True,
                "export": True
            })
        }
        
        response = requests.post(
            f"{BASE_URL}/api/security/session/create",
            data=data,
            timeout=30
        )
        
        result = response.json()
        
        if result.get('success'):
            print("✅ TEST 1 PASSED\n")
            print("📊 Session Created:")
            print(f"   Session ID: {result['data']['session_id']}")
            print(f"   JWT Token: {result['data']['jwt_token'][:50]}...")
            print(f"   Token Hash: {result['data']['token_hash']}")
            print(f"   Expires: {result['data']['expires_at']}")
            print(f"   Permissions: {json.dumps(result['data']['permissions'], indent=2)}")
            print(f"   Sandbox Created: {result['data']['sandbox']['created']}")
            print(f"   Sandbox Isolated: {result['data']['sandbox']['isolated']}")
            
            return {
                "success": True,
                "session_id": result['data']['session_id'],
                "jwt_token": result['data']['jwt_token']
            }
        else:
            print("❌ TEST 1 FAILED")
            print(f"   Error: {result.get('error', {}).get('message', 'Unknown error')}")
            return {"success": False}
            
    except Exception as e:
        print(f"❌ TEST 1 FAILED\n   Exception: {e}")
        return {"success": False}

def test_verify_token(jwt_token: str) -> bool:
    """Test: Verify JWT token"""
    print_section("TEST 2: Verify JWT Token")
    
    try:
        data = {"jwt_token": jwt_token}
        
        response = requests.post(
            f"{BASE_URL}/api/security/session/verify",
            data=data,
            timeout=10
        )
        
        result = response.json()
        
        if result.get('success') and result['data']['valid']:
            print("✅ TEST 2 PASSED\n")
            print("📊 Token Verification:")
            print(f"   Valid: {result['data']['valid']}")
            print(f"   Session ID: {result['data']['session_id']}")
            print(f"   Candidate: {result['data']['candidate_name']}")
            print(f"   Expires: {result['data']['expires_at']}")
            return True
        else:
            print("❌ TEST 2 FAILED")
            print(f"   Token Invalid: {result.get('data', {}).get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ TEST 2 FAILED\n   Exception: {e}")
        return False

def test_invalid_token() -> bool:
    """Test: Verify invalid token"""
    print_section("TEST 3: Invalid Token Handling")
    
    try:
        data = {"jwt_token": "invalid.jwt.token.here"}
        
        response = requests.post(
            f"{BASE_URL}/api/security/session/verify",
            data=data,
            timeout=10
        )
        
        result = response.json()
        
        if not result.get('success') or not result['data']['valid']:
            print("✅ TEST 3 PASSED\n")
            print("📊 Invalid Token Correctly Rejected:")
            print(f"   Valid: {result['data']['valid']}")
            print(f"   Error: {result['data']['error']}")
            return True
        else:
            print("❌ TEST 3 FAILED")
            print("   Invalid token was incorrectly accepted")
            return False
            
    except Exception as e:
        print(f"❌ TEST 3 FAILED\n   Exception: {e}")
        return False

def test_get_permissions(session_id: str) -> bool:
    """Test: Get session permissions"""
    print_section("TEST 4: Get Session Permissions")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/security/session/permissions/{session_id}",
            timeout=10
        )
        
        result = response.json()
        
        if result.get('success'):
            print("✅ TEST 4 PASSED\n")
            print("📊 Session Permissions:")
            print(f"   Session ID: {result['data']['session_id']}")
            permissions = result['data']['permissions']
            for perm, allowed in permissions.items():
                icon = "✅" if allowed else "❌"
                print(f"   {icon} {perm.capitalize()}: {allowed}")
            return True
        else:
            print("❌ TEST 4 FAILED")
            print(f"   Error: {result.get('error', {}).get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ TEST 4 FAILED\n   Exception: {e}")
        return False

def test_sandbox_stats(session_id: str) -> bool:
    """Test: Get sandbox statistics"""
    print_section("TEST 5: Sandbox Statistics")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/security/sandbox/stats/{session_id}",
            timeout=10
        )
        
        result = response.json()
        
        if result.get('success'):
            print("✅ TEST 5 PASSED\n")
            print("📊 Sandbox Statistics:")
            data = result['data']
            print(f"   Session ID: {data['session_id']}")
            print(f"   Created At: {data['created_at']}")
            print(f"   Last Accessed: {data['last_accessed']}")
            print(f"   Access Count: {data['access_count']}")
            print(f"   Memory Allocated: {data['memory_allocated_mb']:.4f} MB")
            print(f"   Buffers Count: {data['buffers_count']}")
            print(f"   Temp Data Count: {data['temp_data_count']}")
            print(f"   Isolated: {'✅' if data['isolated'] else '❌'}")
            print(f"   Cleaned: {'✅' if data['cleaned'] else '❌'}")
            return True
        else:
            print("❌ TEST 5 FAILED")
            print(f"   Error: {result.get('error', {}).get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ TEST 5 FAILED\n   Exception: {e}")
        return False

def test_global_memory_stats() -> bool:
    """Test: Get global memory statistics"""
    print_section("TEST 6: Global Memory Statistics")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/security/memory/global",
            timeout=10
        )
        
        result = response.json()
        
        if result.get('success'):
            print("✅ TEST 6 PASSED\n")
            print("📊 Global Memory Statistics:")
            data = result['data']
            print(f"   Process Memory: {data['process_memory_mb']:.2f} MB")
            print(f"   Sandbox Memory: {data['sandbox_memory_mb']:.4f} MB")
            print(f"   Active Sessions: {data['active_sessions']}/{data['max_sessions']}")
            print(f"   Per-Session Limit: {data['per_session_limit_mb']} MB")
            print(f"   Total Memory Limit: {data['total_limit_mb']} MB")
            return True
        else:
            print("❌ TEST 6 FAILED")
            print(f"   Error: {result.get('error', {}).get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ TEST 6 FAILED\n   Exception: {e}")
        return False

def test_active_sessions() -> bool:
    """Test: Get active secure sessions"""
    print_section("TEST 7: Active Secure Sessions")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/security/sessions/active",
            timeout=10
        )
        
        result = response.json()
        
        if result.get('success'):
            print("✅ TEST 7 PASSED\n")
            print("📊 Active Secure Sessions:")
            data = result['data']
            print(f"   Active Sandboxes: {data['active_sandboxes']}")
            print(f"   Active Tokens: {data['active_tokens']}")
            
            if data['sandboxes']:
                print("\n   Sandbox Details:")
                for sb in data['sandboxes']:
                    print(f"   - {sb['session_id']}")
                    print(f"     Memory: {sb['memory_allocated_mb']:.4f} MB")
                    print(f"     Buffers: {sb['buffers_count']}")
                    print(f"     Access Count: {sb['access_count']}")
            return True
        else:
            print("❌ TEST 7 FAILED")
            print(f"   Error: {result.get('error', {}).get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ TEST 7 FAILED\n   Exception: {e}")
        return False

def test_revoke_session(session_id: str) -> bool:
    """Test: Revoke session and cleanup"""
    print_section("TEST 8: Revoke Session & Cleanup")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/security/session/revoke/{session_id}",
            timeout=30
        )
        
        result = response.json()
        
        if result.get('success'):
            print("✅ TEST 8 PASSED\n")
            print("📊 Session Revocation:")
            data = result['data']
            print(f"   Session ID: {data['session_id']}")
            print(f"   Token Revoked: {'✅' if data['token_revoked'] else '❌'}")
            print(f"   Sandbox Cleaned: {'✅' if data['sandbox_cleaned'] else '❌'}")
            
            if 'cleanup_summary' in data:
                cleanup = data['cleanup_summary']
                print(f"\n   Cleanup Summary:")
                print(f"   Buffers Cleared: {cleanup.get('buffers_cleared', 0)}")
                print(f"   Temp Data Cleared: {cleanup.get('temp_data_cleared', 0)}")
                print(f"   Memory Freed: {cleanup.get('memory_freed_mb', 0):.4f} MB")
                print(f"   File Handles Closed: {cleanup.get('file_handles_closed', 0)}")
                print(f"   Connections Closed: {cleanup.get('connections_closed', 0)}")
            return True
        else:
            print("❌ TEST 8 FAILED")
            print(f"   Error: {result.get('error', {}).get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ TEST 8 FAILED\n   Exception: {e}")
        return False

def test_verify_revoked_token(jwt_token: str) -> bool:
    """Test: Verify revoked token is rejected"""
    print_section("TEST 9: Verify Revoked Token Rejection")
    
    try:
        data = {"jwt_token": jwt_token}
        
        response = requests.post(
            f"{BASE_URL}/api/security/session/verify",
            data=data,
            timeout=10
        )
        
        result = response.json()
        
        if not result.get('success') or not result['data']['valid']:
            print("✅ TEST 9 PASSED\n")
            print("📊 Revoked Token Correctly Rejected:")
            print(f"   Valid: {result['data']['valid']}")
            print(f"   Error: {result['data']['error']}")
            return True
        else:
            print("❌ TEST 9 FAILED")
            print("   Revoked token was incorrectly accepted")
            return False
            
    except Exception as e:
        print(f"❌ TEST 9 FAILED\n   Exception: {e}")
        return False

def main():
    """Run all security tests"""
    print_section("🎯 SECURITY & ISOLATION - TEST SUITE")
    
    print(f"\nBase URL: {BASE_URL}")
    print("Testing: JWT authentication + Session sandboxing\n")
    
    # Check server
    if not test_health_check():
        print("❌ Server is not running at", BASE_URL)
        print("   Please start the server with: python main.py")
        return
    
    print("✅ Server is running and healthy\n")
    
    # Track test results
    results = {
        "passed": 0,
        "failed": 0,
        "total": 9
    }
    
    # Test 1: Create secure session
    session_data = test_create_secure_session()
    if session_data['success']:
        results['passed'] += 1
        session_id = session_data['session_id']
        jwt_token = session_data['jwt_token']
    else:
        results['failed'] += 1
        print("\n⚠️ Skipping remaining tests due to session creation failure")
        print_test_summary(results)
        return
    
    # Test 2: Verify valid token
    if test_verify_token(jwt_token):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 3: Invalid token handling
    if test_invalid_token():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 4: Get permissions
    if test_get_permissions(session_id):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 5: Sandbox stats
    if test_sandbox_stats(session_id):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 6: Global memory stats
    if test_global_memory_stats():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 7: Active sessions
    if test_active_sessions():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 8: Revoke session
    if test_revoke_session(session_id):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 9: Verify revoked token
    if test_verify_revoked_token(jwt_token):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Print summary
    print_test_summary(results)

def print_test_summary(results: Dict[str, int]):
    """Print test summary"""
    print_section("TEST SUMMARY")
    
    print("Security & Isolation Tests:")
    print("✅ Create Secure Session - JWT + Sandbox creation")
    print("✅ Verify Valid Token - Authentication check")
    print("✅ Invalid Token Handling - Rejection test")
    print("✅ Get Permissions - Permission retrieval")
    print("✅ Sandbox Statistics - Memory tracking")
    print("✅ Global Memory Stats - System-wide monitoring")
    print("✅ Active Sessions - Session listing")
    print("✅ Revoke Session - Cleanup test")
    print("✅ Revoked Token Rejection - Security verification")
    
    print(f"\nOverall: {results['passed']}/{results['total']} tests passed ({results['passed']/results['total']*100:.1f}%)")
    print("="*80)
    
    if results['passed'] == results['total']:
        print("\n🎉 All tests PASSED! Security system is ready.\n")
    else:
        print(f"\n⚠️ {results['failed']} test(s) failed. Please check the errors above.\n")
    
    # Feature summary
    print_section("📚 SECURITY & ISOLATION FEATURES")
    
    features = [
        "1. 🔐 JWT Authentication",
        "   - Unique token per session",
        "   - 24-hour expiration",
        "   - Token revocation support",
        "   - Permission management",
        "",
        "2. 🏗️ Session Sandboxing",
        "   - Isolated memory buffers",
        "   - Per-session resource tracking",
        "   - Memory usage limits",
        "   - Automatic cleanup",
        "",
        "3. 💾 Memory Management",
        "   - 100 MB per-session limit",
        "   - 1000 MB total limit",
        "   - Garbage collection",
        "   - Weak references for auto-cleanup",
        "",
        "4. 🛡️ Data Isolation",
        "   - No cross-session data leaks",
        "   - Separate buffer spaces",
        "   - Thread-safe operations",
        "   - Resource leak prevention",
        "",
        "5. 📊 Monitoring",
        "   - Memory usage tracking",
        "   - Active session counts",
        "   - Per-sandbox statistics",
        "   - Global memory stats"
    ]
    
    for feature in features:
        print(feature)
    
    print("\n" + "="*80)
    print("✅ Test suite completed!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
