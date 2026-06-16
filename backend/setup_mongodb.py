#!/usr/bin/env python
"""
MongoDB Setup Script for Resumate

This script will:
1. Install required Python packages
2. Test MongoDB connection
3. Create all collections
4. Create indexes
5. Optionally seed sample data

Usage:
    python setup_mongodb.py                    # Basic setup
    python setup_mongodb.py --seed             # Setup with sample data
    python setup_mongodb.py --test             # Test connection only
"""

import sys
import subprocess
import logging
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_python_version():
    """Check if Python version is 3.11+"""
    logger.info("🔍 Checking Python version...")
    version = sys.version_info
    
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        logger.error(f"❌ Python 3.11+ required, you have Python {version.major}.{version.minor}")
        return False
    
    logger.info(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_dependencies():
    """Install MongoDB Python packages"""
    logger.info("\n" + "="*80)
    logger.info("📦 INSTALLING MONGODB PACKAGES")
    logger.info("="*80)
    
    packages = [
        "pymongo==4.6.0",
        "motor==3.3.2",
        "bcrypt==4.1.2",
        "dnspython==2.4.2"
    ]
    
    try:
        for package in packages:
            logger.info(f"📥 Installing {package}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package, "--quiet"
            ])
            logger.info(f"   ✅ Installed {package}")
        
        logger.info("\n✅ All packages installed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install packages: {str(e)}")
        return False


def check_env_file():
    """Check if .env file exists with MongoDB URI"""
    logger.info("\n" + "="*80)
    logger.info("🔍 CHECKING ENVIRONMENT CONFIGURATION")
    logger.info("="*80)
    
    env_path = Path(".env")  # Now in backend folder
    
    if not env_path.exists():
        logger.warning("⚠️  .env file not found!")
        logger.info("\n📝 Creating .env file template...")
        
        # Create .env from example
        example_path = Path(".env.example")  # Same directory
        if example_path.exists():
            import shutil
            shutil.copy(example_path, env_path)
            logger.info("✅ Created .env file from template")
        else:
            logger.error("❌ .env.example not found!")
            return False
    
    # Check if MONGO_URI is set
    with open(env_path, 'r') as f:
        env_content = f.read()
        
        if "MONGO_URI=mongodb" not in env_content or "your_" in env_content:
            logger.warning("\n⚠️  MONGO_URI not configured in .env file!")
            logger.info("\n📝 Please update .env with your MongoDB connection string:")
            logger.info("   MONGO_URI=mongo_url")
            logger.info("   MONGO_DB_NAME=resumate_db")
            logger.info("\n💡 Get your connection string from MongoDB Atlas or use local:")
            logger.info("   Local: MONGO_URI=mongodb://localhost:27017/")
            return False
    
    logger.info("✅ .env file configured")
    return True


def test_connection():
    """Test MongoDB connection"""
    logger.info("\n" + "="*80)
    logger.info("🔌 TESTING MONGODB CONNECTION")
    logger.info("="*80)
    
    try:
        # Add current directory to path (we're already in backend)
        sys.path.insert(0, str(Path(__file__).parent))
        
        from db.mongo_client import get_mongo_client, ping_db
        
        # Test connection
        if not ping_db():
            logger.error("❌ MongoDB connection failed!")
            logger.info("\n💡 Troubleshooting:")
            logger.info("   1. Check your MONGO_URI in .env")
            logger.info("   2. Ensure MongoDB service is running (if local)")
            logger.info("   3. Check network connection (if Atlas)")
            logger.info("   4. Verify credentials are correct")
            return False
        
        # Get stats
        client = get_mongo_client()
        stats = client.get_stats()
        
        logger.info(f"\n✅ Connected to MongoDB!")
        logger.info(f"📊 Database: {stats.get('database')}")
        logger.info(f"   Collections: {stats.get('collections')}")
        logger.info(f"   Data Size: {stats.get('data_size_mb')} MB")
        logger.info(f"   Documents: {stats.get('objects')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def initialize_database(seed_data=False):
    """Initialize database with collections and indexes"""
    logger.info("\n" + "="*80)
    logger.info("🏗️  INITIALIZING DATABASE")
    logger.info("="*80)
    
    try:
        # Add current directory to path (we're already in backend)
        sys.path.insert(0, str(Path(__file__).parent))
        
        from db.init_db import initialize_database as init_db
        
        init_db(seed_data=seed_data)
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main setup function"""
    logger.info("="*80)
    logger.info("🚀 RESUMATE MONGODB SETUP")
    logger.info("="*80)
    
    # Parse arguments
    test_only = "--test" in sys.argv or "-t" in sys.argv
    seed_data = "--seed" in sys.argv or "-s" in sys.argv
    skip_install = "--skip-install" in sys.argv
    
    # Step 1: Check Python version
    if not check_python_version():
        return 1
    
    # Step 2: Install dependencies
    if not skip_install:
        if not install_dependencies():
            return 1
    else:
        logger.info("\n⏭️  Skipping package installation")
    
    # Step 3: Check environment
    if not check_env_file():
        logger.warning("\n⚠️  Setup incomplete: Please configure .env file")
        return 1
    
    # Step 4: Test connection
    if not test_connection():
        return 1
    
    # If test only, stop here
    if test_only:
        logger.info("\n✅ Connection test completed successfully!")
        return 0
    
    # Step 5: Initialize database
    if not initialize_database(seed_data=seed_data):
        return 1
    
    # Success!
    logger.info("\n" + "="*80)
    logger.info("🎉 SETUP COMPLETE!")
    logger.info("="*80)
    logger.info("\n✅ MongoDB is ready for Resumate!")
    logger.info("\n📚 Next steps:")
    logger.info("   1. Start Flask backend: cd backend && python app.py")
    logger.info("   2. Start FastAPI backend: cd backend && python main.py")
    logger.info("   3. Start Frontend: npm run dev")
    logger.info("\n🔗 Access application at: http://localhost:5173")
    logger.info("")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
