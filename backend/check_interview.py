"""
Quick script to check interview in MongoDB
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# Get MongoDB URI
mongo_uri = os.getenv('MONGODB_URI')
client = MongoClient(mongo_uri)
db = client['resumate']
interviews = db['interviews']

# Get the latest interview
latest = interviews.find_one(sort=[('created_at', -1)])

if latest:
    print("="*80)
    print("📋 LATEST INTERVIEW IN DATABASE")
    print("="*80)
    print(f"Interview ID: {latest.get('interview_id')}")
    print(f"Candidate: {latest.get('candidate_name')}")
    print(f"Email: {latest.get('candidate_email')}")
    print(f"Meet Link: {latest.get('meet_link')}")
    print()
    print("🤖 AUTO-JOIN FIELDS:")
    print(f"   auto_start_bot: {latest.get('auto_start_bot', 'NOT FOUND')}")
    print(f"   auto_join_token: {latest.get('auto_join_token', 'NOT FOUND')}")
    print(f"   bot_join_status: {latest.get('bot_join_status', 'NOT FOUND')}")
    print(f"   candidate_joined_at: {latest.get('candidate_joined_at', 'NOT FOUND')}")
    print(f"   bot_joined_at: {latest.get('bot_joined_at', 'NOT FOUND')}")
    print(f"   trigger_timestamp: {latest.get('trigger_timestamp', 'NOT FOUND')}")
    print("="*80)
else:
    print("❌ No interviews found in database")
