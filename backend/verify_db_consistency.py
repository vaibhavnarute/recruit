"""
Database Consistency Verification Script
Verifies that all MongoDB connections use the correct database name
"""

import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from colorama import init, Fore, Style

# Initialize colorama for Windows
init(autoreset=True)

# Load environment variables
load_dotenv()

def print_header(text):
    print("\n" + "="*80)
    print(f"{Fore.CYAN}{Style.BRIGHT}{text}{Style.RESET_ALL}")
    print("="*80)

def print_success(text):
    print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")

def print_error(text):
    print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")

def print_warning(text):
    print(f"{Fore.YELLOW}⚠️  {text}{Style.RESET_ALL}")

def print_info(text):
    print(f"{Fore.BLUE}ℹ️  {text}{Style.RESET_ALL}")

def main():
    print_header("🔍 DATABASE CONSISTENCY VERIFICATION")
    
    # Check environment variables
    print_header("1. Environment Variables Check")
    
    mongo_uri = os.getenv('MONGODB_URI')
    mongo_db_name = os.getenv('MONGO_DB_NAME')
    mongo_atlas_uri = os.getenv('MONGODB_ATLAS_URI')
    
    if mongo_uri:
        print_success(f"MONGODB_URI is set")
        # Hide password in output
        masked_uri = mongo_uri.split('@')[1] if '@' in mongo_uri else mongo_uri[:50]
        print_info(f"   Cluster: {masked_uri}")
    else:
        print_error("MONGODB_URI not found in environment")
    
    if mongo_db_name:
        print_success(f"MONGO_DB_NAME is set: '{mongo_db_name}'")
        if mongo_db_name != 'resumate':
            print_warning(f"   Database name is '{mongo_db_name}', expected 'resumate'")
    else:
        print_error("MONGO_DB_NAME not found in environment")
    
    if mongo_atlas_uri:
        print_success("MONGODB_ATLAS_URI is set")
    else:
        print_warning("MONGODB_ATLAS_URI not found (optional)")
    
    # Test MongoDB connection
    print_header("2. MongoDB Connection Test")
    
    if not mongo_uri:
        print_error("Cannot test connection: MONGODB_URI not set")
        return
    
    try:
        print_info("Attempting to connect to MongoDB...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Force connection
        client.admin.command('ping')
        print_success("Successfully connected to MongoDB!")
        
        # Get database
        db_name = mongo_db_name or 'resumate'
        db = client[db_name]
        
        print_success(f"Accessed database: '{db_name}'")
        
        # List collections
        collections = db.list_collection_names()
        print_success(f"Found {len(collections)} collections:")
        
        expected_collections = [
            'session_tokens',
            'conversation_transcripts',
            'interview_results',
            'meet_sessions',
            'meet_transcripts',
            'meet_audio_chunks',
            'interview_questions',
            'tts_audio'
        ]
        
        for collection in expected_collections:
            if collection in collections:
                count = db[collection].count_documents({})
                print_success(f"   ✓ {collection}: {count} documents")
            else:
                print_warning(f"   ✗ {collection}: Not found (will be created on first use)")
        
        # Test session_tokens collection (most critical)
        print_header("3. Session Tokens Collection Test")
        
        tokens_collection = db['session_tokens']
        token_count = tokens_collection.count_documents({})
        print_success(f"Session tokens collection has {token_count} documents")
        
        # Check indexes
        indexes = list(tokens_collection.list_indexes())
        print_success(f"Found {len(indexes)} indexes:")
        for idx in indexes:
            print_info(f"   - {idx['name']}")
        
        # Verify we're not accidentally using multiple databases
        print_header("4. Database Consistency Check")
        
        all_databases = client.list_database_names()
        print_info(f"All databases in cluster: {', '.join(all_databases)}")
        
        # Check for old database names
        old_dbs = ['ai_recruiter_db', 'ai_recruiter', 'test']
        found_old_dbs = [db for db in old_dbs if db in all_databases]
        
        if found_old_dbs:
            print_warning(f"Found old databases: {', '.join(found_old_dbs)}")
            print_info("   These may contain outdated data from previous configurations")
            
            for old_db in found_old_dbs:
                old_db_obj = client[old_db]
                old_collections = old_db_obj.list_collection_names()
                if old_collections:
                    print_warning(f"   '{old_db}' has {len(old_collections)} collections")
                    
                    # Check if session_tokens exists in old db
                    if 'session_tokens' in old_collections:
                        old_count = old_db_obj['session_tokens'].count_documents({})
                        print_warning(f"      - session_tokens: {old_count} documents (STALE DATA!)")
        else:
            print_success("No old database names found - clean setup!")
        
        if db_name in all_databases:
            print_success(f"Current database '{db_name}' exists and is active")
        
        # Final verdict
        print_header("5. Verification Result")
        
        issues = []
        
        if not mongo_uri:
            issues.append("MONGODB_URI not set")
        if not mongo_db_name:
            issues.append("MONGO_DB_NAME not set")
        if mongo_db_name and mongo_db_name != 'resumate':
            issues.append(f"Database name is '{mongo_db_name}' instead of 'resumate'")
        if found_old_dbs:
            issues.append(f"Old databases found: {', '.join(found_old_dbs)}")
        
        if not issues:
            print_success("🎉 ALL CHECKS PASSED!")
            print_success("   Database configuration is consistent and correct")
            print_success(f"   Using database: '{db_name}'")
            print_success("   All components will use the same database")
        else:
            print_warning("⚠️  ISSUES DETECTED:")
            for issue in issues:
                print_error(f"   - {issue}")
            print_info("\nRecommendations:")
            print_info("   1. Ensure .env file has MONGO_DB_NAME=resumate")
            print_info("   2. Restart the application to load new environment variables")
            if found_old_dbs:
                print_info(f"   3. Consider migrating data from old databases or cleaning them up")
        
        client.close()
        
    except Exception as e:
        print_error(f"Connection failed: {str(e)}")
        print_info("\nTroubleshooting:")
        print_info("   1. Check MONGODB_URI in .env file")
        print_info("   2. Verify network connection")
        print_info("   3. Check MongoDB Atlas IP whitelist")
        print_info("   4. Verify database user credentials")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification cancelled by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
