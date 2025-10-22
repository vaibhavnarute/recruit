"""
Master Test & Validation Script

Runs all tests and validations in sequence.
"""

import sys
import subprocess
from pathlib import Path


def run_script(script_name, description):
    """Run a Python script and return success status"""
    print(f"\n{'='*70}")
    print(f"🏃 Running: {description}")
    print(f"{'='*70}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=False,
            text=True,
            cwd=Path(__file__).parent
        )
        
        success = result.returncode == 0
        
        if success:
            print(f"\n✅ {description} - PASSED")
        else:
            print(f"\n❌ {description} - FAILED")
        
        return success
        
    except Exception as e:
        print(f"\n❌ {description} - ERROR: {str(e)}")
        return False


def main():
    """Run all validation scripts"""
    print("="*70)
    print("🚀 RESUMATE - MASTER VALIDATION SUITE")
    print("="*70)
    print("\nThis will run all validation scripts in sequence:")
    print("1. Project Structure")
    print("2. MongoDB Connection")
    print("3. Application Startup")
    print("4. Repository Tests")
    print("5. Integration Tests")
    print("6. Feature Documentation")
    
    input("\nPress Enter to continue...")
    
    results = {}
    
    # 1. Show project structure
    results['structure'] = run_script(
        'show_structure.py',
        'Project Structure Display'
    )
    
    # 2. Test MongoDB connection
    results['connection'] = run_script(
        'test_mongo_connection.py',
        'MongoDB Connection Test'
    )
    
    # 3. Run startup checks
    results['startup'] = run_script(
        'startup.py',
        'Application Startup Checks'
    )
    
    # 4. Test repositories
    results['repositories'] = run_script(
        'test_repositories.py',
        'Repository Tests'
    )
    
    # 5. Run integration tests
    results['integration'] = run_script(
        'test_integration.py',
        'Integration Tests'
    )
    
    # 6. Generate documentation
    results['documentation'] = run_script(
        'generate_documentation.py',
        'Feature Documentation'
    )
    
    # Display final summary
    print("\n" + "="*70)
    print("📊 FINAL VALIDATION SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"\nTotal Validations: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    print("\nDetailed Results:")
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} - {test_name.replace('_', ' ').title()}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("✅ Your application is fully configured and ready to use!")
        print("\n🚀 Next Steps:")
        print("   1. Start the Flask app: python app.py")
        print("   2. Start the FastAPI app: python main.py")
        print("   3. Access the application in your browser")
    else:
        print("\n⚠️  SOME VALIDATIONS FAILED")
        print("Please review the errors above and fix them before proceeding")
    
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
