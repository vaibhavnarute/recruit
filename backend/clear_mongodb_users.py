"""
Script to clear all users from MongoDB
This removes test users from your MongoDB database
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def clear_mongodb_users():
    """
    Delete all users from MongoDB users collection
    """
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGO_URI')
        db_name = os.getenv('MONGO_DB_NAME', 'resumate')
        
        if not mongo_uri:
            print("❌ Error: MONGO_URI not found in .env file")
            return
        
        print("Connecting to MongoDB...")
        client = MongoClient(mongo_uri)
        db = client[db_name]
        
        # Get users collection
        users_collection = db['users']
        
        # Count existing users
        user_count = users_collection.count_documents({})
        print(f"Found {user_count} users in MongoDB")
        
        if user_count == 0:
            print("✅ MongoDB users collection is already empty!")
            return
        
        # Delete all users
        result = users_collection.delete_many({})
        print(f"✅ Successfully deleted {result.deleted_count} users from MongoDB!")
        print("Your MongoDB users collection is now clean and ready for fresh testing.")
        
        # Close connection
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("⚠️  WARNING: This will delete ALL users from MongoDB!")
    print("⚠️  This action cannot be undone!")
    confirmation = input("\nType 'DELETE ALL USERS' to confirm: ")
    
    if confirmation == "DELETE ALL USERS":
        clear_mongodb_users()
    else:
        print("❌ Deletion cancelled. No users were deleted.")
