"""
Reset Interview Script
Resets an interview to fresh state so it can be tested again
"""
import requests
import sys
from pymongo import MongoClient
from db.mongo_client import get_db

INTERVIEW_ID = "8981e204-605b-4693-bbcf-34d7bbb61db3"

def reset_interview():
    """Reset interview to initial state"""
    print(f"🔄 Resetting interview: {INTERVIEW_ID}")
    
    # Connect to MongoDB
    db = get_db()
    interviews_collection = db["interviews"]
    
    # Reset interview fields
    result = interviews_collection.update_one(
        {"interview_id": INTERVIEW_ID},
        {
            "$set": {
                "interview_status": "pending",
                "current_question_index": 0,
                "waiting_for_answer": False,
                "completed_at": None,
                "closing_audio_id": None
            },
            "$unset": {
                "questions.$[].answer": "",
                "questions.$[].answer_audio_id": "",
                "questions.$[].answered_at": "",
                "questions.$[].score": "",
                "questions.$[].feedback": "",
                "questions.$[].followup": "",
                "questions.$[].followup_audio_id": "",
                "questions.$[].followup_spoken_at": "",
                "questions.$[].followup_answer": "",
                "questions.$[].followup_answer_audio_id": "",
                "questions.$[].followup_answered_at": "",
                "questions.$[].needs_followup": "",
                "questions.$[].status": ""
            }
        }
    )
    
    if result.modified_count > 0:
        print(f"✅ Interview reset successfully")
        print(f"   Modified: {result.modified_count} document(s)")
        
        # Verify reset
        interview = interviews_collection.find_one({"interview_id": INTERVIEW_ID})
        print(f"\n📊 Reset State:")
        print(f"   Status: {interview.get('interview_status')}")
        print(f"   Current Index: {interview.get('current_question_index')}")
        print(f"   Waiting for Answer: {interview.get('waiting_for_answer')}")
        
        answered_count = sum(1 for q in interview.get('questions', []) if q.get('answer'))
        print(f"   Questions Answered: {answered_count}/{len(interview.get('questions', []))}")
        
        return True
    else:
        print(f"❌ No changes made - interview may not exist")
        return False

if __name__ == "__main__":
    try:
        reset_interview()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
