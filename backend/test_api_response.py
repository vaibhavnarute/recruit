"""
Quick test to verify API returns auto-join fields
"""
import requests
import json

BASE_URL = "http://localhost:8001"

# Get the latest interview ID from verification script
INTERVIEW_ID = "0c832b77-d981-4b0e-bdec-c8439b3ce0c8"

print("="*80)
print("🔍 TESTING API RESPONSE FOR AUTO-JOIN FIELDS")
print("="*80)
print(f"Interview ID: {INTERVIEW_ID}")
print(f"API Endpoint: {BASE_URL}/api/interviews/{INTERVIEW_ID}")
print()

response = requests.get(f"{BASE_URL}/api/interviews/{INTERVIEW_ID}")

if response.status_code == 200:
    data = response.json()
    
    if data.get('success'):
        interview = data.get('data', {})
        
        print("✅ API Response received successfully")
        print()
        print("🔑 Key fields:")
        print(f"  interview_id: {interview.get('interview_id')}")
        print(f"  candidate_name: {interview.get('candidate_name')}")
        print(f"  meet_link: {interview.get('meet_link')}")
        print()
        print("🤖 AUTO-JOIN FIELDS in API response:")
        print(f"  auto_start_bot: {interview.get('auto_start_bot', 'MISSING')}")
        print(f"  auto_join_token: {interview.get('auto_join_token', 'MISSING')}")
        print(f"  bot_join_status: {interview.get('bot_join_status', 'MISSING')}")
        print()
        
        if interview.get('auto_start_bot'):
            print("✅ auto_start_bot field IS present in API response")
        else:
            print("❌ auto_start_bot field MISSING or False in API response")
            
        if interview.get('auto_join_token'):
            print("✅ auto_join_token field IS present in API response")
        else:
            print("❌ auto_join_token field MISSING in API response")
            
    else:
        print(f"❌ API returned error: {data.get('error')}")
else:
    print(f"❌ HTTP Error: {response.status_code}")

print("="*80)
