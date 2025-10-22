"""
Test script for Resume Analysis Agent (LangGraph + MCP)

This script tests the /api/analyze endpoint with sample data.
Run this after starting the FastAPI server (python main.py)
"""

import requests
import json
import os
from pathlib import Path

# Server URL
BASE_URL = "http://localhost:8001"
ANALYZE_URL = f"{BASE_URL}/api/analyze"

def test_resume_analysis():
    """Test resume analysis with sample data"""
    
    print("=" * 80)
    print("🧪 TESTING RESUME ANALYSIS AGENT")
    print("=" * 80)
    
    # Sample job description
    job_description = """
    We're looking for a Senior Full Stack Engineer with:
    
    Required Skills:
    - Python and JavaScript/TypeScript
    - React and modern frontend frameworks
    - Backend development (Node.js, Django, or Flask)
    - Cloud platforms (AWS, GCP, or Azure)
    - Database design (SQL and NoSQL)
    - RESTful API development
    - Git and CI/CD practices
    
    Experience:
    - 5+ years of software development
    - Strong problem-solving skills
    - Experience leading technical projects
    - Bachelor's degree in Computer Science or related field
    
    Nice to Have:
    - Machine Learning experience
    - Docker/Kubernetes
    - Microservices architecture
    """
    
    # Check if we have a sample resume
    resume_path = None
    uploads_dir = Path("uploads")
    
    if uploads_dir.exists():
        # Try to find a resume in uploads
        pdf_files = list(uploads_dir.glob("*.pdf"))
        if pdf_files:
            resume_path = pdf_files[0]
            print(f"📄 Using resume: {resume_path.name}")
    
    if not resume_path:
        print("\n❌ No resume file found in uploads/ directory")
        print("\n💡 To test with a real resume:")
        print("   1. Place a PDF resume in the backend/uploads/ folder")
        print("   2. Run this script again")
        print("\n📝 For now, you can test manually with curl or Postman:")
        print(f"\nPOST {ANALYZE_URL}")
        print("Form Data:")
        print("  - resume: [PDF file]")
        print("  - job_description: [job description text]")
        return
    
    # Prepare the request
    print(f"\n📋 Job Description Length: {len(job_description)} characters")
    print(f"📄 Resume File: {resume_path}")
    
    # Make the request
    print("\n🚀 Sending request to FastAPI server...")
    print(f"   URL: {ANALYZE_URL}")
    
    try:
        with open(resume_path, 'rb') as resume_file:
            files = {'resume': resume_file}
            data = {'job_description': job_description}
            
            response = requests.post(ANALYZE_URL, files=files, data=data)
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n" + "=" * 80)
            print("✅ RESUME ANALYSIS RESULTS")
            print("=" * 80)
            
            # Display results
            print(f"\n📊 Match Score: {result.get('match_score', 0)}/100")
            
            print(f"\n✅ Matching Skills ({len(result.get('matching_skills', []))}):")
            for skill in result.get('matching_skills', [])[:10]:
                print(f"   • {skill}")
            if len(result.get('matching_skills', [])) > 10:
                print(f"   ... and {len(result.get('matching_skills', [])) - 10} more")
            
            print(f"\n❌ Missing Skills ({len(result.get('missing_skills', []))}):")
            for skill in result.get('missing_skills', [])[:10]:
                print(f"   • {skill}")
            if len(result.get('missing_skills', [])) > 10:
                print(f"   ... and {len(result.get('missing_skills', [])) - 10} more")
            
            print(f"\n💪 Strengths ({len(result.get('strengths', []))}):")
            for strength in result.get('strengths', [])[:5]:
                print(f"   • {strength}")
            
            print(f"\n📈 Areas for Improvement ({len(result.get('areas_for_improvement', []))}):")
            for area in result.get('areas_for_improvement', [])[:5]:
                print(f"   • {area}")
            
            # Display performance metrics if available
            if 'metadata' in result:
                metadata = result['metadata']
                print(f"\n🚀 PERFORMANCE METRICS:")
                print(f"   ⏱️  Processing time: {metadata.get('processing_time', 'N/A')}")
                print(f"   💰 Tokens saved: {metadata.get('tokens_saved', 0)}")
                print(f"   📊 Cache hit rate: {metadata.get('cache_hit_rate', 'N/A')}")
                if metadata.get('cache_hit'):
                    print(f"   ✅ Response served from CACHE! (50x faster)")
            
            print("\n" + "=" * 80)
            print("✅ TEST PASSED!")
            print("=" * 80)
            
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error!")
        print("\n💡 Make sure the FastAPI server is running:")
        print("   cd backend")
        print("   python main.py")
        print("\n   Then run this test script again.")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        print(traceback.format_exc())

def test_with_curl():
    """Show curl command for manual testing"""
    print("\n" + "=" * 80)
    print("🔧 MANUAL TESTING WITH CURL")
    print("=" * 80)
    
    print("\nIf you prefer to test manually, use this curl command:")
    print("\ncurl -X POST http://localhost:8001/api/analyze \\")
    print('  -F "resume=@path/to/your/resume.pdf" \\')
    print('  -F "job_description=Your job description here"')
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    # Check if server is running
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=2)
        print("✅ FastAPI server is running!")
    except:
        print("⚠️  FastAPI server is NOT running!")
        print("\n💡 Start the server first:")
        print("   cd backend")
        print("   python main.py")
        print("\n   Then run this script again.")
        print("\n" + "=" * 80)
        exit(1)
    
    # Run tests
    test_resume_analysis()
    test_with_curl() 