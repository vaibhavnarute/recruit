"""
Quick MongoDB verification - check if auto-join fields are actually saved
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
mongo_uri = os.getenv('MONGODB_URI')
client = MongoClient(mongo_uri)
db = client['resumate']
interviews_collection = db['interviews']

# Get the latest interview
latest_interview = interviews_collection.find_one(
    {},
    sort=[('created_at', -1)]
)

print("="*80)
print("🔍 LATEST INTERVIEW IN DATABASE")
print("="*80)

if latest_interview:
    print(f"Interview ID: {latest_interview.get('interview_id')}")
    print(f"Candidate: {latest_interview.get('candidate_name')}")
    print(f"Meet Link: {latest_interview.get('meet_link')}")
    print()
    print("🤖 AUTO-JOIN FIELDS:")
    print("-"*80)
    print(f"  auto_start_bot: {latest_interview.get('auto_start_bot')}")
    print(f"  auto_join_token: {latest_interview.get('auto_join_token')}")
    print(f"  bot_join_status: {latest_interview.get('bot_join_status')}")
    print(f"  candidate_joined_at: {latest_interview.get('candidate_joined_at')}")
    print(f"  bot_joined_at: {latest_interview.get('bot_joined_at')}")
    print(f"  trigger_timestamp: {latest_interview.get('trigger_timestamp')}")
    print()
    
    # Check if fields exist
    if 'auto_start_bot' in latest_interview:
        print("✅ auto_start_bot field EXISTS in database")
    else:
        print("❌ auto_start_bot field MISSING from database")
    
    if 'auto_join_token' in latest_interview:
        print("✅ auto_join_token field EXISTS in database")
        if latest_interview.get('auto_join_token'):
            print(f"   Token: {latest_interview.get('auto_join_token')[:20]}...")
        else:
            print("   ⚠️ Token is None/empty")
    else:
        print("❌ auto_join_token field MISSING from database")
        
else:
    print("❌ No interviews found in database")

print("="*80)
