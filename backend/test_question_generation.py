"""
Test question generation directly
"""
import requests

BASE_URL = "http://localhost:8001"

# Use the interview ID from the last test
interview_id = "5d35edbb-5a69-443c-afed-89ff129fbb27"

print("="*80)
print("🧪 TESTING QUESTION GENERATION DIRECTLY")
print("="*80)
print(f"Interview ID: {interview_id}")
print()

# Call start-interactive endpoint directly
print("📝 Step 1: Calling /api/interviews/{interview_id}/start-interactive...")
response = requests.post(f"{BASE_URL}/api/interviews/{interview_id}/start-interactive")

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
print()

if response.status_code == 200:
    result = response.json()
    if result.get('success'):
        print("✅ SUCCESS!")
        print(f"   Total questions: {result['data']['total_questions']}")
        print(f"   First question: {result['data'].get('first_question', 'N/A')}")
    else:
        print("❌ FAILED!")
        print(f"   Error: {result.get('error')}")
else:
    print(f"❌ HTTP Error: {response.status_code}")
    
print()

# Now check questions endpoint
print("📋 Step 2: Checking /api/interviews/{interview_id}/questions...")
questions_response = requests.get(f"{BASE_URL}/api/interviews/{interview_id}/questions")
print(f"Status Code: {questions_response.status_code}")

if questions_response.status_code == 200:
    questions_data = questions_response.json()
    if questions_data.get('success'):
        questions = questions_data.get('questions', [])
        print(f"✅ Found {len(questions)} questions")
        if questions:
            print(f"   First 3 questions:")
            for i, q in enumerate(questions[:3], 1):
                print(f"   {i}. {q.get('question', 'N/A')}")
    else:
        print("❌ No questions found")
else:
    print(f"❌ HTTP Error: {questions_response.status_code}")

print()
print("="*80)
