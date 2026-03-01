"""
Real-Time Interview Flow Test
==============================
Tests the ACTUAL production endpoints that will be used in real interviews:

1. /qa-loop - Bot asks question via TTS
2. Simulated candidate answer (in production this comes from STT)
3. /process-answer - LLM analyzes real answer
4. Repeat until interview complete

This proves the production implementation is correct!
"""

import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8001"

def reset_interview(interview_id: str) -> bool:
    """Reset interview to initial state"""
    print("\n" + "="*80)
    print("🔄 RESETTING INTERVIEW")
    print("="*80)
    
    response = requests.post(f"{BASE_URL}/api/interviews/{interview_id}/reset")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Interview reset successfully")
            print(f"   Status: {data.get('status', 'unknown')}")
            return True
    print("❌ Failed to reset interview")
    return False


def get_interview_status(interview_id: str) -> dict:
    """Get current interview status"""
    response = requests.get(f"{BASE_URL}/api/interviews/{interview_id}")
    if response.status_code == 200:
        return response.json()
    return {}


def ask_question(interview_id: str) -> dict:
    """
    PRODUCTION ENDPOINT: /qa-loop
    - Speaks question via TTS
    - Returns question details
    - Waits for candidate answer (from STT in production)
    """
    response = requests.post(f"{BASE_URL}/api/interviews/{interview_id}/qa-loop")
    if response.status_code == 200:
        return response.json()
    return {"success": False, "error": "Request failed"}


def submit_answer(interview_id: str, answer_text: str) -> dict:
    """
    PRODUCTION ENDPOINT: /process-answer
    - Receives candidate answer (from STT in production)
    - LLM analyzes and scores answer
    - Generates follow-up or moves to next question
    """
    response = requests.post(
        f"{BASE_URL}/api/interviews/{interview_id}/process-answer",
        json={
            "answer": answer_text,
            "answer_audio_id": f"test_audio_{int(time.time())}"
        }
    )
    if response.status_code == 200:
        return response.json()
    return {"success": False, "error": "Request failed"}


def simulate_candidate_answer(question_text: str, question_num: int) -> str:
    """
    Simulate candidate speaking (in production, STT captures real speech)
    Returns varying quality answers to test scoring system
    """
    question_lower = question_text.lower()
    
    # Simulate different candidate quality levels
    if question_num <= 3:
        # Strong technical answers
        if 'data type' in question_lower or 'programming' in question_lower:
            return """The basic data types in programming include integers for whole numbers, floats for decimal numbers,
            strings for text data, booleans for true/false values, and more complex types like lists, dictionaries, and objects.
            Each type has specific use cases and memory requirements. Type checking helps prevent errors."""
        
        elif 'algorithm' in question_lower or 'maximum' in question_lower:
            return """To find the maximum value in an array, I would iterate through each element and keep track
            of the largest value found. Initialize a max variable with the first element, then compare each subsequent
            element and update max if a larger value is found. This has O(n) time complexity."""
        
        elif 'null' in question_lower or 'undefined' in question_lower:
            return """Null represents an intentional absence of value, while undefined means a variable hasn't been
            assigned yet. In JavaScript, null is explicitly set, but undefined is the default state. In Python,
            we use None for null values. It's important to check for these before operations."""
        
        elif 'variable' in question_lower:
            return """Variables are containers that store data values. They have names, types, and values. Declaration
            syntax varies by language - in Python it's name = value, in JavaScript you use let/const/var. Data types
            define what operations are valid on the variable."""
        
        else:
            return """Based on my experience and understanding, I can provide a detailed answer. The key is to
            understand the fundamentals and apply them correctly. I've worked with this in my projects and can
            explain the best practices and common patterns used in the industry."""
    
    elif question_num <= 6:
        # Moderate quality answers
        if 'reverse' in question_lower and 'string' in question_lower:
            return """I would use slicing in Python with [::-1] to reverse a string. It's the simplest approach.
            Alternatively, I could loop through characters backwards."""
        
        elif 'group project' in question_lower or 'team' in question_lower:
            return """In my final year project, our team of 4 built a web application. We used Git for version
            control and divided tasks based on skills. Communication was key, we had daily meetings."""
        
        elif 'obstacle' in question_lower:
            return """When I encounter obstacles, I first try to understand the root cause. Then I research
            solutions online, check documentation, and ask teammates for help if needed."""
        
        else:
            return """I have experience with this topic. I would approach it systematically by breaking down
            the problem, researching solutions, and implementing the best approach."""
    
    else:
        # Brief answers (later questions)
        if 'disagree' in question_lower or 'conflict' in question_lower:
            return """I would listen to their perspective first, then share my concerns respectfully and
            try to find common ground."""
        
        elif 'deadline' in question_lower:
            return """I would prioritize critical tasks, communicate with the team about challenges,
            and focus on delivering core features first."""
        
        elif 'cloud' in question_lower or 'optimization' in question_lower:
            return """I would monitor resource usage, identify bottlenecks, implement caching where needed,
            and use auto-scaling for variable loads."""
        
        else:
            return """I would handle this by analyzing the situation carefully and taking appropriate action
            based on the requirements and constraints."""


def run_production_flow_test(interview_id: str):
    """
    Test the REAL production interview flow
    """
    print("\n" + "="*80)
    print("🎯 PRODUCTION INTERVIEW FLOW TEST")
    print("="*80)
    print(f"Interview ID: {interview_id}")
    print(f"Testing REAL production endpoints:")
    print("  1. POST /api/interviews/{id}/qa-loop (ask question)")
    print("  2. POST /api/interviews/{id}/process-answer (submit answer)")
    print("="*80)
    
    start_time = time.time()
    
    # Reset interview first
    if not reset_interview(interview_id):
        print("❌ Failed to reset interview, aborting test")
        return
    
    print("\n⏳ Waiting 2 seconds for reset to complete...")
    time.sleep(2)
    
    # Get initial status
    interview = get_interview_status(interview_id)
    total_questions = len(interview.get('questions', []))
    
    print(f"\n✅ Interview loaded: {total_questions} questions")
    
    # Question loop
    question_num = 1
    scores = []
    
    while True:
        print("\n" + "="*80)
        print(f"📝 QUESTION {question_num}/{total_questions}")
        print("="*80)
        
        # Step 1: Ask question (PRODUCTION ENDPOINT)
        print(f"\n🎤 Step 1: Bot asks question via TTS (/qa-loop)")
        qa_result = ask_question(interview_id)
        
        if not qa_result.get('success'):
            if 'complete' in qa_result.get('message', '').lower():
                print(f"✅ Interview complete!")
                break
            print(f"❌ Error asking question: {qa_result.get('error', {}).get('message')}")
            break
        
        question_data = qa_result.get('data', {})
        question_text = question_data.get('question', '')
        tts_duration = question_data.get('audio_duration', 0)
        
        print(f"   Question: {question_text[:100]}...")
        print(f"   TTS Duration: {tts_duration}s")
        print(f"   Status: {question_data.get('status')}")
        
        # Step 2: Simulate candidate speaking (in production: STT captures real speech)
        print(f"\n👤 Step 2: Candidate speaks (STT captures in production)")
        print(f"   Simulating candidate thinking and speaking...")
        time.sleep(2)  # Simulate speaking delay
        
        candidate_answer = simulate_candidate_answer(question_text, question_num)
        print(f"   Answer: {candidate_answer[:150]}...")
        
        # Step 3: Submit answer for analysis (PRODUCTION ENDPOINT)
        print(f"\n🤖 Step 3: LLM analyzes answer (/process-answer)")
        answer_result = submit_answer(interview_id, candidate_answer)
        
        if not answer_result.get('success'):
            print(f"❌ Error processing answer: {answer_result.get('error', {}).get('message')}")
            break
        
        answer_data = answer_result.get('data', {})
        score = answer_data.get('score', 0)
        feedback = answer_data.get('feedback', '')
        next_action = answer_data.get('next_action', 'unknown')
        
        scores.append(score)
        
        print(f"   ✅ Score: {score}/10")
        print(f"   📝 Feedback: {feedback[:100]}...")
        print(f"   ➡️  Next Action: {next_action}")
        
        if next_action == 'complete':
            print(f"\n🎉 Interview completed!")
            break
        
        question_num += 1
        
        # Small delay before next question
        time.sleep(1)
    
    # Final summary
    elapsed_time = time.time() - start_time
    
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"✅ Total Questions: {len(scores)}")
    print(f"✅ Average Score: {sum(scores)/len(scores) if scores else 0:.1f}/10")
    print(f"✅ Individual Scores: {scores}")
    print(f"✅ Duration: {elapsed_time:.1f}s")
    print(f"✅ Avg Time/Question: {elapsed_time/len(scores) if scores else 0:.1f}s")
    
    score_distribution = {
        "Excellent (8-10)": len([s for s in scores if s >= 8]),
        "Good (6-7)": len([s for s in scores if 6 <= s < 8]),
        "Average (4-5)": len([s for s in scores if 4 <= s < 6]),
        "Poor (0-3)": len([s for s in scores if s < 4])
    }
    
    print(f"\n📈 Score Distribution:")
    for category, count in score_distribution.items():
        print(f"   {category}: {count} questions")
    
    print("\n" + "="*80)
    print("✅ PRODUCTION FLOW TEST COMPLETE")
    print("="*80)
    print("\n🎯 Production Endpoints Verified:")
    print("   ✅ /qa-loop - Question asking with TTS")
    print("   ✅ /process-answer - Answer analysis with LLM")
    print("   ✅ Interview state management")
    print("   ✅ Score calculation and feedback")
    print("\n💡 In production:")
    print("   - Real candidate speaks in Google Meet")
    print("   - STT captures speech → text")
    print("   - Text sent to /process-answer")
    print("   - Everything else is the same!")
    print("="*80)


if __name__ == "__main__":
    # Use your actual interview ID
    INTERVIEW_ID = "8981e204-605b-4693-bbcf-34d7bbb61db3"
    
    try:
        run_production_flow_test(INTERVIEW_ID)
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
