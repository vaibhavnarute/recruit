"""
MongoDB Connection Diagnostics

This script helps diagnose MongoDB connection issues.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

print("="*70)
print("🔍 MONGODB CONNECTION DIAGNOSTICS")
print("="*70)

# Check .env file
mongo_uri = os.getenv('MONGO_URI')
mongo_db = os.getenv('MONGO_DB_NAME')

print("\n1. Environment Variables:")
print(f"   ✓ MONGO_URI found: {bool(mongo_uri)}")
print(f"   ✓ MONGO_DB_NAME found: {bool(mongo_db)}")

if mongo_uri:
    # Parse connection string
    if mongo_uri.startswith('mongodb+srv://'):
        print(f"   ✓ Using MongoDB Atlas (SRV)")
        
        # Extract credentials (safely)
        try:
            parts = mongo_uri.split('@')
            if len(parts) >= 2:
                creds = parts[0].replace('mongodb+srv://', '')
                if ':' in creds:
                    username = creds.split(':')[0]
                    password_masked = '*' * len(creds.split(':')[1])
                    print(f"   ✓ Username: {username}")
                    print(f"   ✓ Password: {password_masked}")
                
                cluster = parts[1].split('/')[0].split('?')[0]
                print(f"   ✓ Cluster: {cluster}")
        except:
            pass
    elif mongo_uri.startswith('mongodb://'):
        print(f"   ✓ Using MongoDB (standard connection)")
    else:
        print(f"   ❌ Invalid MongoDB URI format!")

print(f"\n2. Database Name: {mongo_db}")

# Test connection with different approaches
print("\n3. Testing Connection...")
print("-"*70)

# Method 1: Basic ping test
print("\n   Method 1: Basic Ping Test")
try:
    from pymongo import MongoClient
    from pymongo.server_api import ServerApi
    
    client = MongoClient(
        mongo_uri,
        server_api=ServerApi('1'),
        serverSelectionTimeoutMS=5000
    )
    
    # Ping test
    client.admin.command('ping')
    print("   ✅ Connection successful!")
    
    # Get server info
    info = client.server_info()
    print(f"   ✓ MongoDB version: {info.get('version')}")
    
    # List databases
    dbs = client.list_database_names()
    print(f"   ✓ Available databases: {dbs}")
    
    # Check specific database
    if mongo_db in dbs:
        print(f"   ✓ Database '{mongo_db}' exists")
        db = client[mongo_db]
        collections = db.list_collection_names()
        print(f"   ✓ Collections: {collections}")
    else:
        print(f"   ⚠️  Database '{mongo_db}' doesn't exist yet (will be created on first write)")
    
    client.close()
    
except Exception as e:
    error_msg = str(e)
    print(f"   ❌ Connection failed!")
    print(f"   Error: {error_msg}")
    
    # Provide specific troubleshooting
    if "authentication failed" in error_msg.lower():
        print("\n   💡 AUTHENTICATION ERROR - Try these solutions:")
        print("      1. Go to MongoDB Atlas → Database Access")
        print("      2. Verify user 'narutevaibhav95_db_user' exists")
        print("      3. Click 'Edit' → 'Edit Password' → Reset password")
        print("      4. Update MONGO_URI in .env with new password")
        print("      5. Ensure user has 'Read and write to any database' privilege")
        
    elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
        print("\n   💡 NETWORK/TIMEOUT ERROR - Try these solutions:")
        print("      1. Go to MongoDB Atlas → Network Access")
        print("      2. Click 'Add IP Address'")
        print("      3. Select 'Allow Access from Anywhere' (0.0.0.0/0)")
        print("      4. Or add your current IP address")
        print("      5. Check your internet connection")
        
    elif "dns" in error_msg.lower():
        print("\n   💡 DNS ERROR - Try these solutions:")
        print("      1. Check cluster URL in MongoDB Atlas")
        print("      2. Verify 'resumate.xbvpnl1.mongodb.net' is correct")
        print("      3. Try using standard connection string instead of SRV")

print("\n" + "="*70)
print("Diagnostics complete!")
print("="*70)
