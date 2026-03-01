"""
Cleanup Script: Remove Old ai_recruiter_db Database
====================================================

This script will:
1. Connect to MongoDB
2. Check if ai_recruiter_db exists
3. Show collections and document counts
4. DELETE the entire ai_recruiter_db database
5. Verify only 'resumate' remains

⚠️  WARNING: This will permanently delete ai_recruiter_db!
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def print_success(msg):
    print(f"\033[92m✅ {msg}\033[0m")

def print_error(msg):
    print(f"\033[91m❌ {msg}\033[0m")

def print_warning(msg):
    print(f"\033[93m⚠️  {msg}\033[0m")

def print_info(msg):
    print(f"\033[94mℹ️  {msg}\033[0m")

def main():
    print("\n" + "="*70)
    print("🧹 CLEANUP OLD DATABASE: ai_recruiter_db")
    print("="*70 + "\n")
    
    # Get MongoDB URI
    mongo_uri = os.getenv('MONGODB_URI')
    if not mongo_uri:
        print_error("MONGODB_URI not found in .env file!")
        return
    
    print_info(f"Connecting to MongoDB...")
    
    try:
        client = MongoClient(mongo_uri)
        
        # Test connection
        client.admin.command('ping')
        print_success("Connected to MongoDB successfully!")
        
        # List all databases
        all_dbs = client.list_database_names()
        print_info(f"Found {len(all_dbs)} databases total")
        
        # Check for ai_recruiter_db
        if 'ai_recruiter_db' not in all_dbs:
            print_success("ai_recruiter_db does not exist - already clean!")
            print_info("Current databases:")
            for db_name in all_dbs:
                if db_name not in ['admin', 'local', 'config']:
                    print(f"   - {db_name}")
            return
        
        # Show what's in ai_recruiter_db
        print_warning("Found ai_recruiter_db - inspecting contents...")
        old_db = client['ai_recruiter_db']
        collections = old_db.list_collection_names()
        
        print(f"\n📦 Collections in ai_recruiter_db ({len(collections)} total):")
        total_docs = 0
        for coll in collections:
            count = old_db[coll].count_documents({})
            total_docs += count
            print(f"   - {coll}: {count} documents")
        
        print(f"\n   Total: {total_docs} documents across all collections")
        
        # Ask for confirmation
        print("\n" + "="*70)
        print_warning("⚠️  THIS WILL PERMANENTLY DELETE ai_recruiter_db!")
        print("="*70)
        confirm = input("\nType 'DELETE' to confirm (or anything else to cancel): ")
        
        if confirm != 'DELETE':
            print_info("Cancelled - no changes made")
            return
        
        # Delete the database
        print_info("Deleting ai_recruiter_db...")
        client.drop_database('ai_recruiter_db')
        
        # Verify deletion
        remaining_dbs = client.list_database_names()
        if 'ai_recruiter_db' in remaining_dbs:
            print_error("Failed to delete ai_recruiter_db!")
        else:
            print_success("ai_recruiter_db deleted successfully!")
        
        # Show remaining databases
        print("\n✨ Remaining databases:")
        for db_name in remaining_dbs:
            if db_name not in ['admin', 'local', 'config']:
                db_obj = client[db_name]
                colls = db_obj.list_collection_names()
                print(f"   - {db_name} ({len(colls)} collections)")
        
        # Verify resumate exists
        if 'resumate' in remaining_dbs:
            print_success("\n'resumate' database is active and ready!")
            resumate_db = client['resumate']
            resumate_colls = resumate_db.list_collection_names()
            print(f"   Collections: {len(resumate_colls)}")
            for coll in resumate_colls:
                count = resumate_db[coll].count_documents({})
                print(f"      - {coll}: {count} documents")
        
        print("\n" + "="*70)
        print_success("🎉 CLEANUP COMPLETE!")
        print("="*70)
        print("\n✅ All new data will now be written to 'resumate' database only")
        
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
