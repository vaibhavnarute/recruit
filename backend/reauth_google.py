"""
Quick Google Calendar Re-Authentication Script
Run this to refresh your Google Calendar API token
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes required
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Paths
CREDENTIALS_PATH = "google_credentials.json"
TOKEN_PATH = "google_token.json"

print("="*80)
print("🔐 GOOGLE CALENDAR RE-AUTHENTICATION")
print("="*80)
print(f"📁 Credentials: {CREDENTIALS_PATH}")
print(f"💾 Token will be saved to: {TOKEN_PATH}")
print()
print("🌐 Opening browser for authentication...")
print("   Please sign in with your Google account")
print("   Grant Calendar permissions when prompted")
print("="*80)

# Delete old token if exists
if os.path.exists(TOKEN_PATH):
    os.remove(TOKEN_PATH)
    print("🗑️  Deleted old token")

# Start OAuth flow
flow = InstalledAppFlow.from_client_secrets_file(
    CREDENTIALS_PATH, 
    SCOPES,
    redirect_uri='http://localhost:8080/'
)

# Run local server for OAuth callback
creds = flow.run_local_server(port=8080)

# Save credentials
with open(TOKEN_PATH, 'w') as token_file:
    token_file.write(creds.to_json())

print()
print("="*80)
print("✅ AUTHENTICATION SUCCESSFUL!")
print("="*80)
print(f"💾 Token saved to: {TOKEN_PATH}")
print("🚀 You can now run the test script again")
print("="*80)
