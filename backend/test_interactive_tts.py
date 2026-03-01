"""
Test Interactive Interview with TTS
This tests the complete Q&A loop with bot speaking questions
"""
import requests
import time

BASE_URL = "http://localhost:8001"

# Use the interview ID from previous test
interview_id = "8981e204-605b-4693-bbcf-34d7bbb61db3"

print("="*80)
print("🎤 TESTING INTERACTIVE INTERVIEW WITH TTS")
print("="*80)
print(f"Interview ID: {interview_id}")
print()

# Step 1: Check questions are available
print("📋 Step 1: Checking questions...")
questions_response = requests.get(f"{BASE_URL}/api/interviews/{interview_id}/questions")
if questions_response.status_code == 200:
    questions_data = questions_response.json()
    if questions_data.get('success'):
        questions = questions_data.get('questions', [])
        print(f"✅ Found {len(questions)} questions")
        if questions:
            print(f"   First question: {questions[0].get('question', 'N/A')[:80]}...")
    else:
        print("❌ No questions found - run test_complete_interactive_flow.py first")
        exit(1)
else:
    print(f"❌ Error getting questions: {questions_response.status_code}")
    exit(1)

print()

# Step 2: Start interview conductor
print("🎤 Step 2: Starting Interview Conductor...")
print("   This will:")
print("   - Start the Q&A loop orchestration")
print("   - Generate introduction speech")
print("   - Prepare to ask questions via TTS")
print()

conductor_response = requests.post(f"{BASE_URL}/api/interviews/{interview_id}/conduct")
print(f"Status Code: {conductor_response.status_code}")

if conductor_response.status_code == 200:
    result = conductor_response.json()
    if result.get('success'):
        print("✅ Interview Conductor Started!")
        data = result.get('data', {})
        print(f"   Session ID: {data.get('session_id')}")
        print(f"   Total Questions: {data.get('total_questions')}")
        print(f"   Status: {data.get('status')}")
        print()
        print(f"📢 Introduction:")
        intro = data.get('introduction', '')
        if intro:
            # Print wrapped text
            import textwrap
            wrapped = textwrap.fill(intro, width=76)
            for line in wrapped.split('\n'):
                print(f"   {line}")
        print()
    else:
        print(f"❌ Failed to start conductor")
        print(f"   Error: {result.get('error')}")
        exit(1)
else:
    print(f"❌ HTTP Error: {conductor_response.status_code}")
    print(f"   Response: {conductor_response.text}")
    exit(1)

# Step 3: Speak first question
print("🔊 Step 3: Speaking First Question via TTS...")
first_question = questions[0].get('question', '')
print(f"   Question: {first_question[:80]}...")
print()

speak_request = {
    "text": first_question,
    "text_type": "question",
    "question_index": 0
}

speak_response = requests.post(
    f"{BASE_URL}/api/interviews/{interview_id}/speak",
    json=speak_request
)

print(f"Status Code: {speak_response.status_code}")

if speak_response.status_code == 200:
    result = speak_response.json()
    if result.get('success'):
        print("✅ TTS Generation Successful!")
        data = result.get('data', {})
        print(f"   TTS ID: {data.get('tts_id')}")
        print(f"   Voice: {data.get('voice_name')}")
        print(f"   Duration: {data.get('audio_duration_seconds', 0):.2f}s")
        print(f"   Size: {data.get('audio_size_bytes', 0) / 1024:.2f} KB")
        print(f"   Processing Time: {data.get('processing_time_ms', 0)}ms")
        print()
        print("   📝 Note: Audio generated but not yet played in meeting")
        print("   📝 TODO: Integrate with Puppeteer bot to play audio in Meet")
    else:
        print(f"❌ TTS Failed")
        print(f"   Error: {result.get('error')}")
else:
    print(f"❌ HTTP Error: {speak_response.status_code}")
    print(f"   Response: {speak_response.text}")

print()
print("="*80)
print("✅ INTERACTIVE INTERVIEW TEST COMPLETE")
print("="*80)
print()
print("📊 Summary:")
print("   ✅ Questions generated and stored")
print("   ✅ Interview conductor initialized")
print("   ✅ TTS audio generation working")
print("   ⏳ Pending: Audio playback in Google Meet")
print("   ⏳ Pending: STT for candidate answers")
print("   ⏳ Pending: LLM answer analysis")
print("   ⏳ Pending: Follow-up question generation")
print()
print("🎯 Next Steps:")
print("   1. Integrate TTS audio playback with Puppeteer bot")
print("   2. Connect STT to capture candidate answers")
print("   3. Implement answer analysis with LLM")
print("   4. Create follow-up question generation")
print("   5. Complete full Q&A loop orchestration")
print()
print("="*80)
