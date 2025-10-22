"""
Test script for ML prediction endpoints

This tests the new ML prediction functionality:
1. Salary prediction
2. Job possibility prediction

Usage:
    python test_ml_predictions.py
"""

import requests
import json

# Backend API base URL
API_BASE_URL = "http://localhost:8001"

def test_salary_prediction():
    """Test salary prediction endpoint"""
    print("="*80)
    print("🧪 Testing Salary Prediction")
    print("="*80)
    
    # Test data
    data = {
        'years_experience': 5,
        'education_level': 'Bachelor',
        'job_level': 'Mid-level',
        'industry': 'Technology',
        'location': 'Urban'
    }
    
    print(f"📤 Sending request with data:")
    print(json.dumps(data, indent=2))
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/predict-salary",
            data=data
        )
        
        print(f"\n📥 Response status: {response.status_code}")
        
        if response.ok:
            result = response.json()
            print(f"\n✅ Salary Prediction Result:")
            print(f"   Predicted Salary: ${result['predicted_salary']:,.2f}")
            print(f"   Confidence: {result['confidence']:.2%}")
            print(f"   Model Used: {result['model_used']}")
            print(f"\n   Feature Importance:")
            for feature, importance in result['feature_importance'].items():
                print(f"      {feature}: {importance}%")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False


def test_job_possibility_prediction():
    """Test job possibility prediction endpoint"""
    print("\n" + "="*80)
    print("🧪 Testing Job Possibility Prediction")
    print("="*80)
    
    # Test data
    data = {
        'years_experience': 3,
        'education_level': 'Bachelor',
        'job_level': 'Mid-level',
        'industry': 'Technology',
        'skill_match_score': 0.75
    }
    
    print(f"📤 Sending request with data:")
    print(json.dumps(data, indent=2))
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/predict-job-possibility",
            data=data
        )
        
        print(f"\n📥 Response status: {response.status_code}")
        
        if response.ok:
            result = response.json()
            print(f"\n✅ Job Possibility Prediction Result:")
            print(f"   Probability: {result['probability']:.2%}")
            print(f"   Recommended: {'Yes ✓' if result['recommended'] else 'No ✗'}")
            print(f"   Confidence: {result['confidence']:.2%}")
            print(f"   Model Used: {result['model_used']}")
            print(f"\n   Feature Importance:")
            for feature, importance in result['feature_importance'].items():
                print(f"      {feature}: {importance}%")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False


def test_validation():
    """Test input validation"""
    print("\n" + "="*80)
    print("🧪 Testing Input Validation")
    print("="*80)
    
    # Test invalid skill match score
    data = {
        'years_experience': 3,
        'education_level': 'Bachelor',
        'job_level': 'Mid-level',
        'industry': 'Technology',
        'skill_match_score': 1.5  # Invalid: > 1
    }
    
    print(f"📤 Sending request with INVALID skill_match_score (1.5):")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/predict-job-possibility",
            data=data
        )
        
        result = response.json()
        if 'error' in result:
            print(f"✅ Validation working: {result['error']}")
            return True
        else:
            print(f"❌ Validation failed: Should have rejected invalid input")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False


if __name__ == "__main__":
    print("\n🚀 Starting ML Prediction Tests")
    print("="*80)
    print("Make sure the backend server is running on http://localhost:8001")
    print("="*80)
    
    results = []
    
    # Test 1: Salary Prediction
    results.append(("Salary Prediction", test_salary_prediction()))
    
    # Test 2: Job Possibility Prediction
    results.append(("Job Possibility Prediction", test_job_possibility_prediction()))
    
    # Test 3: Input Validation
    results.append(("Input Validation", test_validation()))
    
    # Summary
    print("\n" + "="*80)
    print("📊 Test Summary")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)
    
    print("\n" + "="*80)
    print(f"Results: {passed_tests}/{total_tests} tests passed")
    print("="*80)
