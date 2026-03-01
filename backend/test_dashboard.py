"""
Test script for Dashboard API
Tests all dashboard endpoints with authentication
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
BASE_URL = "http://localhost:8001"
DASHBOARD_SECRET = os.getenv("DASHBOARD_SECRET", "your-secret-key-here")

def test_metrics_endpoint():
    """Test GET /api/dashboard/metrics"""
    print("\n" + "="*80)
    print("TEST 1: Dashboard Metrics Endpoint")
    print("="*80)
    
    headers = {
        "Authorization": f"Bearer {DASHBOARD_SECRET}"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/dashboard/metrics",
            headers=headers,
            params={"time_range_hours": 24}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ TEST 1 PASSED")
            print(f"\n📊 Metrics Summary:")
            print(f"   Total Sessions: {data['sessions']['total']}")
            print(f"   Active Sessions: {data['sessions']['active']}")
            print(f"   Success Rate: {data['sessions']['success_rate']}%")
            print(f"   STT Avg Latency: {data['latency']['stt']['avg']}ms")
            print(f"   LLM Avg Latency: {data['latency']['llm']['avg']}ms")
            print(f"   TTS Avg Latency: {data['latency']['tts']['avg']}ms")
            print(f"   Total Retries: {data['retries']['total']}")
            print(f"   Avg Quality Score: {data['quality']['avg_score']}")
            return True
        else:
            print(f"\n❌ TEST 1 FAILED")
            print(f"   Status Code: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED")
        print(f"   Error: {e}")
        return False


def test_active_sessions_endpoint():
    """Test GET /api/dashboard/sessions/active"""
    print("\n" + "="*80)
    print("TEST 2: Active Sessions Endpoint")
    print("="*80)
    
    headers = {
        "Authorization": f"Bearer {DASHBOARD_SECRET}"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/dashboard/sessions/active",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ TEST 2 PASSED")
            print(f"\n📊 Active Sessions: {data['count']}")
            
            if data['sessions']:
                print("\n   Sessions:")
                for session in data['sessions'][:5]:  # Show first 5
                    print(f"   - {session['session_id']}")
                    print(f"     Turns: {session['total_turns']}, Quality: {session['quality_score']}")
            else:
                print("   No active sessions")
            
            return True
        else:
            print(f"\n❌ TEST 2 FAILED")
            print(f"   Status Code: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED")
        print(f"   Error: {e}")
        return False


def test_authentication():
    """Test authentication with invalid token"""
    print("\n" + "="*80)
    print("TEST 3: Authentication (Invalid Token)")
    print("="*80)
    
    headers = {
        "Authorization": "Bearer invalid-token-123"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/dashboard/metrics",
            headers=headers
        )
        
        if response.status_code == 403:
            print("\n✅ TEST 3 PASSED")
            print("   Authentication correctly rejected invalid token")
            return True
        else:
            print(f"\n❌ TEST 3 FAILED")
            print(f"   Expected 403, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED")
        print(f"   Error: {e}")
        return False


def test_no_auth():
    """Test request without authentication"""
    print("\n" + "="*80)
    print("TEST 4: No Authentication Header")
    print("="*80)
    
    try:
        response = requests.get(f"{BASE_URL}/api/dashboard/metrics")
        
        if response.status_code == 401:
            print("\n✅ TEST 4 PASSED")
            print("   Authentication correctly required")
            return True
        else:
            print(f"\n❌ TEST 4 FAILED")
            print(f"   Expected 401, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST 4 FAILED")
        print(f"   Error: {e}")
        return False


def test_dashboard_html():
    """Test GET /dashboard HTML page"""
    print("\n" + "="*80)
    print("TEST 5: Dashboard HTML Page")
    print("="*80)
    
    headers = {
        "Authorization": f"Bearer {DASHBOARD_SECRET}"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/dashboard",
            headers=headers
        )
        
        if response.status_code == 200 and "AI Recruiter Dashboard" in response.text:
            print("\n✅ TEST 5 PASSED")
            print("   Dashboard HTML page loaded successfully")
            print(f"   Page size: {len(response.text)} bytes")
            return True
        else:
            print(f"\n❌ TEST 5 FAILED")
            print(f"   Status Code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST 5 FAILED")
        print(f"   Error: {e}")
        return False


def main():
    """Run all dashboard tests"""
    print("\n")
    print("="*80)
    print("🎯 AI RECRUITER DASHBOARD - TEST SUITE")
    print("="*80)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Dashboard Secret: {DASHBOARD_SECRET[:10]}..." if len(DASHBOARD_SECRET) > 10 else DASHBOARD_SECRET)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("\n❌ Server is not running or not healthy!")
            print("   Please start the server: python main.py")
            return
    except requests.exceptions.RequestException:
        print("\n❌ Cannot connect to server!")
        print("   Please start the server: python main.py")
        return
    
    print("\n✅ Server is running and healthy")
    
    # Run tests
    results = []
    
    results.append(("Metrics Endpoint", test_metrics_endpoint()))
    results.append(("Active Sessions Endpoint", test_active_sessions_endpoint()))
    results.append(("Authentication (Invalid)", test_authentication()))
    results.append(("No Authentication", test_no_auth()))
    results.append(("Dashboard HTML", test_dashboard_html()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print("="*80)
    print(f"Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*80)
    
    if passed == total:
        print("\n🎉 All tests PASSED! Dashboard is ready.")
        print(f"\n🌐 Access dashboard at: {BASE_URL}/dashboard")
        print(f"   (Remember to set Authorization header: Bearer {DASHBOARD_SECRET})")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please check the errors above.")


if __name__ == "__main__":
    main()
