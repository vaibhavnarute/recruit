"""
Script to delete all users from Firebase Authentication
WARNING: This will permanently delete all users!
"""

import firebase_admin
from firebase_admin import credentials, auth
import os

def delete_all_firebase_users():
    """
    Delete all users from Firebase Authentication
    """
    try:
        # Initialize Firebase Admin SDK
        # You'll need to download the service account key from Firebase Console
        # Go to: Project Settings > Service Accounts > Generate New Private Key
        
        # For now, using default credentials
        if not firebase_admin._apps:
            cred = credentials.Certificate('path/to/your/serviceAccountKey.json')
            firebase_admin.initialize_app(cred)
        
        print("Starting to delete all Firebase users...")
        
        # List all users
        page = auth.list_users()
        deleted_count = 0
        
        while page:
            for user in page.users:
                try:
                    auth.delete_user(user.uid)
                    deleted_count += 1
                    print(f"✓ Deleted user: {user.email} (UID: {user.uid})")
                except Exception as e:
                    print(f"✗ Error deleting user {user.email}: {str(e)}")
            
            # Get next batch of users
            page = page.get_next_page()
        
        print(f"\n✅ Successfully deleted {deleted_count} users from Firebase Authentication!")
        print("Your Firebase Auth is now clean and ready for fresh testing.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nNote: You need to set up Firebase Admin SDK with a service account key.")
        print("Follow these steps:")
        print("1. Go to Firebase Console: https://console.firebase.google.com/")
        print("2. Select your project: login-a8b4c")
        print("3. Go to Project Settings (⚙️) > Service Accounts")
        print("4. Click 'Generate New Private Key'")
        print("5. Save the JSON file and update the path in this script")

if __name__ == "__main__":
    print("⚠️  WARNING: This will delete ALL users from Firebase Authentication!")
    print("⚠️  This action cannot be undone!")
    confirmation = input("\nType 'DELETE ALL USERS' to confirm: ")
    
    if confirmation == "DELETE ALL USERS":
        delete_all_firebase_users()
    else:
        print("❌ Deletion cancelled. No users were deleted.")
