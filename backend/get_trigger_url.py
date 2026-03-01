"""
Get the full trigger URL with token for testing
"""
import requests

INTERVIEW_ID = "0c832b77-d981-4b0e-bdec-c8439b3ce0c8"

print("="*80)
print("🔗 GETTING AUTO-TRIGGER URL WITH TOKEN")
print("="*80)

response = requests.get(f"http://localhost:8001/api/interviews/{INTERVIEW_ID}")
data = response.json()['data']

token = data['auto_join_token']
meet_link = data['meet_link']

trigger_url = f"http://localhost:8001/api/meet/trigger/{INTERVIEW_ID}?token={token}"

print(f"\n✅ Auto-join Token: {token}\n")
print(f"📋 FULL TRIGGER URL (copy this):")
print("="*80)
print(trigger_url)
print("="*80)
print()
print("🧪 HOW TO TEST:")
print("   1. Copy the URL above")
print("   2. Open it in your browser")
print("   3. Wait 8 seconds (bot joining...)")
print("   4. You'll be redirected to Google Meet")
print(f"   5. Meet Link: {meet_link}")
print()
print("💡 Or run this command:")
print(f'   Start-Process "{trigger_url}"')
print("="*80)
