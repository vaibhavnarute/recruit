"""
Master Test & Validation Script

Runs all tests and validations in sequence.
Updated: 2025-10-28 - Added comprehensive validation suite
"""

import sys
import io
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def run_script(script_name, description, required=True):
    """Run a Python script and return success status"""
    print(f"\n{'='*80}")
    print(f"🧪 {description}")
    print(f"{'='*80}\n")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=False,
            text=True,
            cwd=Path(__file__).parent,
            timeout=120,  # 2 minute timeout
            encoding='utf-8',
            errors='replace'
        )
        
        duration = time.time() - start_time
        success = result.returncode == 0
        
        if success:
            print(f"\n✅ {description} - PASSED ({duration:.1f}s)")
        else:
            if required:
                print(f"\n❌ {description} - FAILED ({duration:.1f}s)")
            else:
                print(f"\n⚠️  {description} - FAILED ({duration:.1f}s) [Optional]")
        
        return success, duration
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"\n❌ {description} - TIMEOUT ({duration:.1f}s)")
        return False, duration
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ {description} - ERROR: {str(e)} ({duration:.1f}s)")
        return False, duration


def main():
    """Run all validation scripts"""
    print("="*80)
    print("🚀 RESUMATE - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: resumate (cleaned - old databases removed)")
    print("\nTest Sequence:")
    print("  1. Database Consistency Verification")
    print("  2. MongoDB Connection Test") 
    print("  3. Validation Checklist (5 Production Tests)")
    print("  4. Performance Test (4 Workers)")
    print("  5. Real-time Orchestration Test")
    print("  6. Analytics Engine Test")
    
    input("\nPress Enter to continue...")
    
    results = []
    total_duration = 0
    
    # Core Infrastructure Tests (REQUIRED)
    print("\n" + "="*80)
    print("📋 PHASE 1: CORE INFRASTRUCTURE TESTS (Required)")
    print("="*80)
    
    success, duration = run_script('verify_db_consistency.py', '1. Database Consistency Verification', required=True)
    results.append(('Database Consistency', success, duration, True))
    total_duration += duration
    
    success, duration = run_script('test_mongodb_connection.py', '2. MongoDB Connection Test', required=True)
    results.append(('MongoDB Connection', success, duration, True))
    total_duration += duration
    
    # Production Readiness Tests (REQUIRED)
    print("\n" + "="*80)
    print("📋 PHASE 2: PRODUCTION READINESS VALIDATION (Required)")
    print("="*80)
    
    success, duration = run_script('test_validation_checklist.py', '3. Validation Checklist (5 Critical Tests)', required=True)
    results.append(('Validation Checklist', success, duration, True))
    total_duration += duration
    
    # Performance Tests (OPTIONAL)
    print("\n" + "="*80)
    print("📋 PHASE 3: PERFORMANCE & SCALING TESTS (Optional)")
    print("="*80)
    
    success, duration = run_script('test_performance_4_workers.py', '4. Performance Test - 4 Workers', required=False)
    results.append(('Performance Test', success, duration, False))
    total_duration += duration
    
    # Component Tests (OPTIONAL)
    print("\n" + "="*80)
    print("📋 PHASE 4: COMPONENT TESTS (Optional)")
    print("="*80)
    
    success, duration = run_script('test_realtime_orchestration.py', '5. Real-time Orchestration', required=False)
    results.append(('Realtime Orchestration', success, duration, False))
    total_duration += duration
    
    success, duration = run_script('test_analytics_engine.py', '6. Analytics Engine', required=False)
    results.append(('Analytics Engine', success, duration, False))
    total_duration += duration
    
    # Display final summary
    print("\n" + "="*80)
    print("📊 FINAL TEST RESULTS SUMMARY")
    print("="*80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    
    # Calculate statistics
    total = len(results)
    passed = sum(1 for _, success, _, _ in results if success)
    failed = total - passed
    
    required_tests = [(name, success, dur) for name, success, dur, req in results if req]
    required_passed = sum(1 for _, success, _ in required_tests if success)
    required_failed = len(required_tests) - required_passed
    
    optional_tests = [(name, success, dur) for name, success, dur, req in results if not req]
    optional_passed = sum(1 for _, success, _ in optional_tests if success)
    
    print(f"\nTotal Tests Run: {total}")
    print(f"Total Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"Total Failed: {failed}/{total}")
    
    print(f"\nRequired Tests (Must Pass):")
    print(f"  ✅ Passed: {required_passed}/{len(required_tests)}")
    print(f"  ❌ Failed: {required_failed}/{len(required_tests)}")
    
    if optional_tests:
        print(f"\nOptional Tests:")
        print(f"  ✅ Passed: {optional_passed}/{len(optional_tests)}")
        print(f"  ❌ Failed: {len(optional_tests) - optional_passed}/{len(optional_tests)}")
    
    print("\nDetailed Results:")
    print("┌────┬─────────────────────────────────────┬──────────┬──────────┬──────────┐")
    print("│ #  │ Test Name                           │ Status   │ Duration │ Required │")
    print("├────┼─────────────────────────────────────┼──────────┼──────────┼──────────┤")
    
    for i, (name, success, duration, required) in enumerate(results, 1):
        status = "✅ PASS" if success else "❌ FAIL"
        req_str = "Yes" if required else "No"
        name_padded = name[:35].ljust(35)
        dur_str = f"{duration:.1f}s".rjust(8)
        req_padded = req_str.center(8)
        
        print(f"│ {i:2d} │ {name_padded} │ {status} │ {dur_str} │ {req_padded} │")
    
    print("└────┴─────────────────────────────────────┴──────────┴──────────┴──────────┘")
    
    all_passed = all(success for _, success, _, _ in results)
    required_all_passed = required_failed == 0
    
    print("\n" + "="*80)
    
    if required_all_passed:
        print("🎉 SUCCESS! All required tests passed!")
        print("✅ System is PRODUCTION READY!")
        
        if failed > 0:
            print(f"\n⚠️  Note: {failed} optional test(s) failed")
            print("   These don't affect production readiness")
        
        print("\n🚀 Next Steps:")
        print("   1. Deploy with: uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4")
        print("   2. Monitor metrics: /api/distributed/orchestration/workers")
        print("   3. Run production monitoring")
        return 0
    else:
        print("❌ FAILURE: Required tests failed")
        print("⚠️  System needs fixes before production")
        
        print(f"\nFailed Required Tests:")
        for name, success, _, required in results:
            if required and not success:
                print(f"  ❌ {name}")
        
        print("\nPlease fix these issues and run the tests again")
        return 1
    
    print("="*70)
    
    return all_passed


if __name__ == "__main__":
    try:
        all_passed = main()
        sys.exit(0 if all_passed else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Master validation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
