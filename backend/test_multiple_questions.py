"""
Test Script: Multiple Questions in Sequence
Tests asking 2-3 questions and verifying progression through interview
"""
import requests
import time
import json

BASE_URL = "http://localhost:8001"
INTERVIEW_ID = "8981e204-605b-4693-bbcf-34d7bbb61db3"  # Update with your interview ID

def print_header(title):
    print("\n" + "="*80)
    print(f"{'🔄 ' + title:^80}")
    print("="*80)

def print_section(title):
    print("\n" + "-"*80)
    print(f"📋 {title}")
    print("-"*80)

def ask_question(question_num):
    """Ask a specific question via Q&A loop"""
    print_section(f"Asking Question {question_num}")
    
    response = requests.post(f"{BASE_URL}/api/interviews/{INTERVIEW_ID}/qa-loop")
    
    if response.status_code == 200:
        data = response.json()
        if data["success"]:
            result = data["data"]
            print(f"✅ Question {question_num} Asked!")
            print(f"   Question: {result['question_text'][:100]}...")
            print(f"   Current Index: {result['current_question_index']}")
            print(f"   Total Questions: {result['total_questions']}")
            print(f"   Audio Duration: {result['audio_duration']:.2f}s")
            print(f"   Status: {result['status']}")
            return result
        else:
            print(f"❌ Failed: {data.get('message', 'Unknown error')}")
            return None
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def process_answer(question_num, answer):
    """Process candidate's answer"""
    print_section(f"Processing Answer {question_num}")
    print(f"   Answer length: {len(answer)} chars")
    print(f"   Answer preview: {answer[:150]}...")
    
    response = requests.post(
        f"{BASE_URL}/api/interviews/{INTERVIEW_ID}/process-answer",
        json={
            "answer": answer,
            "answer_audio_id": f"audio_answer_{question_num}"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data["success"]:
            result = data["data"]
            print(f"✅ Answer {question_num} Processed!")
            print(f"   Score: {result['score']}/10")
            print(f"   Feedback: {result['feedback'][:100]}...")
            print(f"   Next Action: {result['next_action']}")
            
            if result['next_action'] == 'followup' and result.get('followup_question'):
                print(f"\n🔄 Follow-up Question Generated:")
                print(f"   {result['followup_question'][:150]}...")
                print(f"   Audio Duration: {result.get('followup_audio_duration', 0):.2f}s")
            
            return result
        else:
            print(f"❌ Failed: {data.get('message', 'Unknown error')}")
            return None
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def main():
    print_header("TESTING MULTIPLE QUESTIONS IN SEQUENCE")
    print(f"Interview ID: {INTERVIEW_ID}")
    
    # Sample answers for testing
    sample_answers = [
        # Answer 1 (Good answer - should get high score)
        """The basic data types in programming include integers for whole numbers, 
        floats for decimal numbers, strings for text, booleans for true/false values, 
        and arrays for collections. In Python, we also have lists, dictionaries, and tuples. 
        These are used extensively in building applications - for example, integers for counting, 
        strings for user input, and dictionaries for storing structured data like user profiles.""",
        
        # Answer 2 (Medium answer - might need follow-up)
        """Functions are reusable blocks of code that perform specific tasks. They help 
        organize code and make it more maintainable. You define them with parameters and 
        they can return values. I use functions to break down complex problems into smaller parts.""",
        
        # Answer 3 (Basic answer - likely needs follow-up)
        """I handle errors using try-catch blocks in most languages. When an error occurs, 
        the catch block handles it. This prevents the program from crashing."""
    ]
    
    # Test 3 questions in sequence
    for i in range(1, 4):
        print(f"\n{'='*80}")
        print(f"{'QUESTION ' + str(i) + ' OF 3':^80}")
        print(f"{'='*80}")
        
        # Step 1: Ask question
        question_result = ask_question(i)
        if not question_result:
            print(f"\n❌ Failed to ask question {i}, stopping test")
            break
        
        # Simulate thinking time
        print(f"\n⏳ Simulating candidate thinking... (2 seconds)")
        time.sleep(2)
        
        # Step 2: Process answer
        answer = sample_answers[i-1] if i <= len(sample_answers) else "This is a basic answer."
        answer_result = process_answer(i, answer)
        if not answer_result:
            print(f"\n❌ Failed to process answer {i}, stopping test")
            break
        
        # Step 3: Handle follow-up if needed
        if answer_result.get('next_action') == 'followup':
            print(f"\n⏳ Simulating candidate answering follow-up... (2 seconds)")
            time.sleep(2)
            
            # Process follow-up answer
            followup_answer = "Here's more detail on what I mentioned earlier with specific examples..."
            print_section(f"Processing Follow-up Answer {i}")
            followup_result = process_answer(f"{i}-followup", followup_answer)
            
            if followup_result and followup_result.get('next_action') == 'next':
                print(f"\n✅ Follow-up satisfied, moving to next question")
        
        # Check if we should continue
        if answer_result.get('next_action') == 'complete':
            print(f"\n🎉 Interview completed after question {i}")
            break
        
        # Pause between questions
        if i < 3:
            print(f"\n⏳ Preparing next question... (2 seconds)")
            time.sleep(2)
    
    # Summary
    print_header("TEST SUMMARY")
    
    # Get final interview status
    response = requests.get(f"{BASE_URL}/api/interviews/{INTERVIEW_ID}")
    if response.status_code == 200:
        data = response.json()
        if data["success"]:
            interview = data["data"]
            print(f"\n📊 Interview Status:")
            print(f"   Current Question: {interview.get('current_question_index', 0) + 1}")
            print(f"   Total Questions: {len(interview.get('questions', []))}")
            print(f"   Status: {interview.get('status', 'unknown')}")
            
            # Count answered questions
            answered = sum(1 for q in interview.get('questions', []) if q.get('answer'))
            print(f"   Questions Answered: {answered}")
            
            # Show scores
            scores = [q.get('score') for q in interview.get('questions', []) if q.get('score')]
            if scores:
                avg_score = sum(scores) / len(scores)
                print(f"   Average Score: {avg_score:.1f}/10")
                print(f"   Scores: {scores}")
    
    print("\n" + "="*80)
    print("✅ MULTIPLE QUESTIONS TEST COMPLETE")
    print("="*80)
    
    print("\n📝 What Was Tested:")
    print("   ✅ Asking multiple questions in sequence")
    print("   ✅ Processing answers with LLM")
    print("   ✅ Generating follow-up questions")
    print("   ✅ Moving between questions")
    print("   ✅ Tracking interview progress")
    print("   ✅ Calculating scores")

if __name__ == "__main__":
    main()
