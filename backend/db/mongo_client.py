"""
MongoDB Client - Singleton Connection Manager

Purpose: Centralized MongoDB connection with proper error handling and logging
Features:
- Singleton pattern (one connection for entire app)
- Automatic reconnection on failure
- Connection pooling
- Detailed logging
"""

import logging
import os
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    Singleton MongoDB client with connection management
    
    Why singleton:
    - Only one connection pool needed for entire application
    - Avoid multiple connections (resource waste)
    - Centralized connection management
    
    Usage:
        from db.mongo_client import get_db, get_collection
        
        db = get_db()
        users = get_collection('users')
        users.insert_one({'email': 'test@example.com'})
    """
    
    _instance: Optional['MongoDBClient'] = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None
    
    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)"""
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize MongoDB connection (only once)"""
        if self._initialized:
            return
        
        self._initialized = True
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection"""
        try:
            mongo_uri = os.getenv('MONGO_URI')
            db_name = os.getenv('MONGO_DB_NAME', 'resumate_db')
            
            if not mongo_uri:
                logger.error("❌ MONGO_URI not found in environment variables!")
                raise ValueError("MONGO_URI is required in .env file")
            
            logger.info("🔄 Connecting to MongoDB...")
            logger.info(f"📊 Database: {db_name}")
            
            # Create MongoDB client with connection pooling
            self._client = MongoClient(
                mongo_uri,
                maxPoolSize=50,  # Maximum connections in pool
                minPoolSize=10,  # Minimum connections maintained
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=10000,  # 10 second connection timeout
                retryWrites=True,  # Automatic retry on write failures
                w='majority'  # Wait for majority of nodes to acknowledge writes
            )
            
            # Test connection
            self._client.admin.command('ping')
            
            # Get database
            self._db = self._client[db_name]
            
            logger.info("✅ MongoDB connection established successfully!")
            logger.info(f"📦 Connected to database: {db_name}")
            
            # Log available collections
            collections = self._db.list_collection_names()
            if collections:
                logger.info(f"📂 Available collections: {', '.join(collections)}")
            else:
                logger.info("📂 No collections found (database is empty)")
            
        except ConnectionFailure as e:
            logger.error(f"❌ MongoDB connection failed: {str(e)}")
            raise
        except ServerSelectionTimeoutError as e:
            logger.error(f"❌ MongoDB server not reachable: {str(e)}")
            logger.error("💡 Check your MONGO_URI and network connection")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to MongoDB: {str(e)}")
            raise
    
    def get_database(self) -> Database:
        """
        Get MongoDB database instance
        
        Returns:
            Database instance
        """
        if self._db is None:
            logger.warning("⚠️ Database not initialized, attempting reconnection...")
            self._connect()
        
        return self._db
    
    def get_collection(self, collection_name: str) -> Collection:
        """
        Get MongoDB collection
        
        Args:
            collection_name: Name of the collection
        
        Returns:
            Collection instance
        """
        db = self.get_database()
        return db[collection_name]
    
    def ping(self) -> bool:
        """
        Test MongoDB connection
        
        Returns:
            True if connection is alive, False otherwise
        """
        try:
            if self._client is None:
                return False
            
            self._client.admin.command('ping')
            logger.info("✅ MongoDB ping successful")
            return True
        except Exception as e:
            logger.error(f"❌ MongoDB ping failed: {str(e)}")
            return False
    
    def close(self):
        """Close MongoDB connection"""
        if self._client:
            logger.info("🔒 Closing MongoDB connection...")
            self._client.close()
            self._client = None
            self._db = None
            logger.info("✅ MongoDB connection closed")
    
    def get_stats(self) -> dict:
        """
        Get MongoDB connection statistics
        
        Returns:
            Dictionary with connection stats
        """
        try:
            db = self.get_database()
            stats = db.command('dbStats')
            
            return {
                'database': db.name,
                'collections': stats.get('collections', 0),
                'data_size_mb': round(stats.get('dataSize', 0) / (1024 * 1024), 2),
                'storage_size_mb': round(stats.get('storageSize', 0) / (1024 * 1024), 2),
                'indexes': stats.get('indexes', 0),
                'objects': stats.get('objects', 0)
            }
        except Exception as e:
            logger.error(f"❌ Failed to get database stats: {str(e)}")
            return {}


# Global singleton instance
_mongo_client: Optional[MongoDBClient] = None


def get_mongo_client() -> MongoDBClient:
    """
    Get or create global MongoDB client instance
    
    Returns:
        MongoDBClient instance
    """
    global _mongo_client
    
    if _mongo_client is None:
        _mongo_client = MongoDBClient()
    
    return _mongo_client


def get_db() -> Database:
    """
    Get MongoDB database (convenience function)
    
    Returns:
        Database instance
    """
    client = get_mongo_client()
    return client.get_database()


def get_collection(collection_name: str) -> Collection:
    """
    Get MongoDB collection (convenience function)
    
    Args:
        collection_name: Name of the collection
    
    Returns:
        Collection instance
    """
    client = get_mongo_client()
    return client.get_collection(collection_name)


def ping_db() -> bool:
    """
    Test MongoDB connection (convenience function)
    
    Returns:
        True if connection is alive
    """
    client = get_mongo_client()
    return client.ping()


def close_db():
    """Close MongoDB connection (convenience function)"""
    global _mongo_client
    
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Test connection
        logger.info("="*80)
        logger.info("TESTING MONGODB CONNECTION")
        logger.info("="*80)
        
        # Get database
        db = get_db()
        logger.info(f"✅ Connected to database: {db.name}")
        
        # Test ping
        if ping_db():
            logger.info("✅ Connection test successful")
        
        # Get stats
        client = get_mongo_client()
        stats = client.get_stats()
        logger.info(f"📊 Database Stats:")
        for key, value in stats.items():
            logger.info(f"   {key}: {value}")
        
        # Test collection access
        users = get_collection('users')
        logger.info(f"✅ Got collection: {users.name}")
        
        # List all collections
        collections = db.list_collection_names()
        logger.info(f"📂 Collections: {collections}")
        
        logger.info("="*80)
        logger.info("✅ ALL TESTS PASSED!")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # Close connection
        close_db()
