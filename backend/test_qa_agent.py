"""
Test script for Q&A Agent (LangGraph + MCP)

This script tests the /api/qa endpoint with sample questions.
Run this after starting the FastAPI server (python main.py)
"""

import requests
import json
from pathlib import Path

# Server URL
BASE_URL = "http://localhost:8001"
QA_URL = f"{BASE_URL}/api/qa"

def test_qa_with_file():
    """Test Q&A with a resume file"""
    
    print("=" * 80)
    print("🧪 TESTING Q&A AGENT (with file upload)")
    print("=" * 80)
    
    # Sample questions
    questions = [
        "What programming languages does the candidate know?",
        "How many years of experience does the candidate have?",
        "What is the candidate's educational background?",
        "What are the candidate's key technical skills?",
        "What companies has the candidate worked for?"
    ]
    
    # Check if we have a sample resume
    resume_path = None
    uploads_dir = Path("uploads")
    
    if uploads_dir.exists():
        pdf_files = list(uploads_dir.glob("*.pdf"))
        if pdf_files:
            resume_path = pdf_files[0]
            print(f"📄 Using resume: {resume_path.name}")
    
    if not resume_path:
        print("\n❌ No resume file found in uploads/ directory")
        print("\n💡 To test with a real resume:")
        print("   1. Place a PDF resume in the backend/uploads/ folder")
        print("   2. Run this script again")
        test_with_curl()
        return
    
    # Test each question
    for i, question in enumerate(questions, 1):
        print(f"\n{'=' * 80}")
        print(f"❓ Question {i}/{len(questions)}")
        print(f"{'=' * 80}")
        print(f"\n📝 {question}")
        
        try:
            with open(resume_path, 'rb') as resume_file:
                files = {'resume_file': resume_file}
                data = {'question': question}
                
                print(f"\n🚀 Sending request...")
                response = requests.post(QA_URL, files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                
                if 'error' in result:
                    print(f"\n❌ Error: {result['error']}")
                else:
                    print(f"\n💡 Answer:")
                    answer = result.get('answer', [])
                    if isinstance(answer, list):
                        for point in answer:
                            print(f"   {point}")
                    else:
                        print(f"   {answer}")
                    
                    # Show performance if available
                    if 'metadata' in result:
                        metadata = result['metadata']
                        print(f"\n📊 Performance:")
                        print(f"   💰 Tokens saved: {metadata.get('tokens_saved', 0)}")
                        print(f"   📊 Cache hit: {'Yes ✅' if metadata.get('cache_hit') else 'No'}")
                        print(f"   🏷️  Question type: {metadata.get('question_type', 'unknown')}")
            else:
                print(f"\n❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
    
    print("\n" + "=" * 80)
    print("✅ ALL QUESTIONS TESTED!")
    print("=" * 80)

def test_qa_with_text():
    """Test Q&A with resume text (no file upload)"""
    
    print("\n" + "=" * 80)
    print("🧪 TESTING Q&A AGENT (with resume text)")
    print("=" * 80)
    
    # Sample resume text
    resume_text = """
    John Doe
    Senior Software Engineer
    
    SKILLS:
    - Python, JavaScript, TypeScript
    - React, Node.js, Django
    - AWS, Docker, Kubernetes
    - PostgreSQL, MongoDB
    - Git, CI/CD, Agile
    
    EXPERIENCE:
    Senior Software Engineer at Tech Corp (2020-2024)
    - Led team of 5 developers building ML-powered applications
    - Implemented CI/CD pipelines reducing deployment time by 60%
    - Built scalable REST APIs handling 1M+ requests/day
    
    Software Engineer at Startup Inc (2018-2020)
    - Developed full-stack web applications using React and Node.js
    - Designed and optimized database schemas
    
    EDUCATION:
    Bachelor of Science in Computer Science
    Stanford University (2014-2018)
    """
    
    question = "What programming languages does this candidate know?"
    
    print(f"\n📝 Question: {question}")
    print(f"📄 Using sample resume text ({len(resume_text)} characters)")
    
    try:
        data = {
            'resume_text': resume_text,
            'question': question
        }
        
        print(f"\n🚀 Sending request...")
        response = requests.post(QA_URL, data=data)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'error' in result:
                print(f"\n❌ Error: {result['error']}")
            else:
                print(f"\n💡 Answer:")
                answer = result.get('answer', [])
                if isinstance(answer, list):
                    for point in answer:
                        print(f"   {point}")
                else:
                    print(f"   {answer}")
                
                print("\n✅ Test with text passed!")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

def test_with_curl():
    """Show curl commands for manual testing"""
    print("\n" + "=" * 80)
    print("🔧 MANUAL TESTING WITH CURL")
    print("=" * 80)
    
    print("\n1. Test with file upload:")
    print("\ncurl -X POST http://localhost:8001/api/qa \\")
    print('  -F "resume_file=@path/to/resume.pdf" \\')
    print('  -F "question=What skills does the candidate have?"')
    
    print("\n\n2. Test with resume text:")
    print("\ncurl -X POST http://localhost:8001/api/qa \\")
    print('  -F "resume_text=Your resume text here..." \\')
    print('  -F "question=What is the candidate\'s experience?"')
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    # Check if server is running
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=2)
        print("✅ FastAPI server is running!\n")
    except:
        print("⚠️  FastAPI server is NOT running!")
        print("\n💡 Start the server first:")
        print("   cd backend")
        print("   python main.py")
        print("\n   Then run this script again.")
        print("\n" + "=" * 80)
        exit(1)
    
    # Run tests
    test_qa_with_file()
    print("\n")
    test_qa_with_text()
    test_with_curl()
