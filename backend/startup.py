"""
Application Startup Script

This script initializes the entire application with MongoDB integration:
1. Checks MongoDB connection
2. Initializes all repositories
3. Sets up required indexes
4. Verifies all services are working
"""

import sys
import logging
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from db.mongo_client import get_mongo_client, ping_db
from repositories import (
    UserRepository,
    ResumeRepository,
    JobRepository,
    CandidateRepository,
    AnalysisRepository,
    InterviewRepository,
    EmailRepository,
    QARepository
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_mongodb_connection():
    """Verify MongoDB connection"""
    logger.info("🔍 Checking MongoDB connection...")
    
    if not ping_db():
        logger.error("❌ MongoDB connection failed!")
        return False
    
    client = get_mongo_client()
    stats = client.get_stats()
    
    logger.info("✅ MongoDB connected successfully!")
    logger.info(f"📊 Database: {stats.get('database')}")
    logger.info(f"📁 Collections: {stats.get('collections')}")
    
    return True


def initialize_repositories():
    """Initialize all repository instances"""
    logger.info("\n🔧 Initializing Repositories...")
    
    try:
        repos = {
            'user': UserRepository(),
            'resume': ResumeRepository(),
            'job': JobRepository(),
            'candidate': CandidateRepository(),
            'analysis': AnalysisRepository(),
            'interview': InterviewRepository(),
            'email': EmailRepository(),
            'qa': QARepository()
        }
        
        logger.info("✅ All repositories initialized successfully!")
        logger.info(f"   📦 {len(repos)} repositories ready")
        
        return repos
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize repositories: {str(e)}")
        return None


def verify_collections():
    """Verify all required collections exist"""
    logger.info("\n📋 Verifying Collections...")
    
    try:
        client = get_mongo_client()
        db = client.get_database()
        existing_collections = set(db.list_collection_names())
        
        required_collections = [
            'users',
            'resumes',
            'job_descriptions',
            'selected_candidates',
            'rejected_candidates',
            'analysis_results',
            'interviews',
            'email_logs',
            'interview_questions',
            'resume_analysis_results',
            'improved_resumes',
            'qa_sessions'
        ]
        
        all_exist = True
        for collection in required_collections:
            if collection in existing_collections:
                count = db[collection].count_documents({})
                logger.info(f"   ✅ {collection:30s} ({count} documents)")
            else:
                logger.warning(f"   ⚠️  {collection:30s} (NOT FOUND)")
                all_exist = False
        
        if not all_exist:
            logger.warning("\n⚠️  Some collections are missing. Run setup_mongodb.py first.")
            return False
        
        logger.info(f"\n✅ All {len(required_collections)} collections verified!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to verify collections: {str(e)}")
        return False


def run_health_checks():
    """Run basic health checks"""
    logger.info("\n🏥 Running Health Checks...")
    
    health_status = {
        'mongodb': False,
        'repositories': False,
        'collections': False
    }
    
    # Check MongoDB
    health_status['mongodb'] = check_mongodb_connection()
    
    # Check repositories
    repos = initialize_repositories()
    health_status['repositories'] = repos is not None
    
    # Check collections
    health_status['collections'] = verify_collections()
    
    return health_status


def display_startup_summary(health_status):
    """Display startup summary"""
    logger.info("\n" + "="*70)
    logger.info("🚀 APPLICATION STARTUP SUMMARY")
    logger.info("="*70)
    
    all_healthy = all(health_status.values())
    
    logger.info("\n📊 Component Status:")
    for component, status in health_status.items():
        status_icon = "✅" if status else "❌"
        logger.info(f"   {status_icon} {component.title()}: {'Healthy' if status else 'Unhealthy'}")
    
    if all_healthy:
        logger.info("\n✅ ALL SYSTEMS OPERATIONAL!")
        logger.info("🎯 Application is ready to use")
    else:
        logger.warning("\n⚠️  SOME SYSTEMS ARE NOT OPERATIONAL")
        logger.warning("💡 Please check the errors above and fix them")
    
    logger.info("="*70)
    
    return all_healthy


def main():
    """Main startup function"""
    logger.info("="*70)
    logger.info("🚀 RESUMATE APPLICATION STARTUP")
    logger.info("="*70)
    
    # Run health checks
    health_status = run_health_checks()
    
    # Display summary
    all_healthy = display_startup_summary(health_status)
    
    # Exit with appropriate code
    sys.exit(0 if all_healthy else 1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"\n❌ Startup failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
