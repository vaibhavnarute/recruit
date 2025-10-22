"""
Database Initialization Script

Purpose: Create all collections and indexes in MongoDB
Features:
- Create all required collections
- Add indexes for performance
- Add validation rules
- Initial data seeding (optional)
"""

import logging
from datetime import datetime
from pymongo import IndexModel, ASCENDING, DESCENDING
from pymongo.errors import CollectionInvalid
from db.mongo_client import get_db, get_mongo_client
from db.models import ALL_COLLECTIONS, Collections

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_collections():
    """
    Create all required collections
    
    Why: Explicitly create collections for better control and validation
    """
    logger.info("="*80)
    logger.info("🏗️  CREATING MONGODB COLLECTIONS")
    logger.info("="*80)
    
    db = get_db()
    existing_collections = db.list_collection_names()
    
    for collection_name in ALL_COLLECTIONS:
        try:
            if collection_name in existing_collections:
                logger.info(f"✅ Collection '{collection_name}' already exists")
            else:
                db.create_collection(collection_name)
                logger.info(f"✨ Created collection '{collection_name}'")
        except CollectionInvalid:
            logger.info(f"⚠️  Collection '{collection_name}' already exists")
        except Exception as e:
            logger.error(f"❌ Failed to create collection '{collection_name}': {str(e)}")
    
    logger.info(f"\n✅ Total collections: {len(db.list_collection_names())}")


def create_indexes():
    """
    Create indexes for better query performance
    
    Why indexes:
    - Faster lookups on frequently queried fields
    - Enforce uniqueness constraints
    - Improve sorting performance
    """
    logger.info("\n" + "="*80)
    logger.info("📊 CREATING INDEXES")
    logger.info("="*80)
    
    db = get_db()
    
    # Users collection indexes
    logger.info(f"\n📁 Creating indexes for '{Collections.USERS}'...")
    users = db[Collections.USERS]
    users.create_index([("email", ASCENDING)], unique=True, name="email_unique")
    users.create_index([("role", ASCENDING)], name="role_idx")
    users.create_index([("created_at", DESCENDING)], name="created_at_idx")
    users.create_index([("firebase_uid", ASCENDING)], sparse=True, name="firebase_uid_idx")
    logger.info("   ✅ Created 4 indexes")
    
    # Resumes collection indexes
    logger.info(f"\n📁 Creating indexes for '{Collections.RESUMES}'...")
    resumes = db[Collections.RESUMES]
    resumes.create_index([("candidate_email", ASCENDING)], name="candidate_email_idx")
    resumes.create_index([("uploaded_at", DESCENDING)], name="uploaded_at_idx")
    resumes.create_index([("uploaded_by", ASCENDING)], name="uploaded_by_idx")
    resumes.create_index([("structured_data.skills", ASCENDING)], name="skills_idx")
    logger.info("   ✅ Created 4 indexes")
    
    # Job Descriptions collection indexes
    logger.info(f"\n📁 Creating indexes for '{Collections.JOB_DESCRIPTIONS}'...")
    jobs = db[Collections.JOB_DESCRIPTIONS]
    jobs.create_index([("job_id", ASCENDING)], unique=True, name="job_id_unique")
    jobs.create_index([("is_active", ASCENDING)], name="is_active_idx")
    jobs.create_index([("created_by", ASCENDING)], name="created_by_idx")
    jobs.create_index([("created_at", DESCENDING)], name="created_at_idx")
    jobs.create_index([("required_skills", ASCENDING)], name="required_skills_idx")
    logger.info("   ✅ Created 5 indexes")
    
    # Selected Candidates collection indexes
    logger.info(f"\n📁 Creating indexes for '{Collections.SELECTED_CANDIDATES}'...")
    selected = db[Collections.SELECTED_CANDIDATES]
    selected.create_index([("candidate_email", ASCENDING)], name="candidate_email_idx")
    selected.create_index([("job_id", ASCENDING)], name="job_id_idx")
    selected.create_index([("status", ASCENDING)], name="status_idx")
    selected.create_index([("selected_at", DESCENDING)], name="selected_at_idx")
    selected.create_index([("match_score", DESCENDING)], name="match_score_idx")
    logger.info("   ✅ Created 5 indexes")
    
    # Rejected Candidates collection indexes
    logger.info(f"\n📁 Creating indexes for '{Collections.REJECTED_CANDIDATES}'...")
    rejected = db[Collections.REJECTED_CANDIDATES]
    rejected.create_index([("candidate_email", ASCENDING)], name="candidate_email_idx")
    rejected.create_index([("job_id", ASCENDING)], name="job_id_idx")
    rejected.create_index([("rejected_at", DESCENDING)], name="rejected_at_idx")
    logger.info("   ✅ Created 3 indexes")
    
    # Analysis Results collection indexes
    logger.info(f"\n📁 Creating indexes for '{Collections.ANALYSIS_RESULTS}'...")
    analysis = db[Collections.ANALYSIS_RESULTS]
    analysis.create_index([("resume_id", ASCENDING)], name="resume_id_idx")
    analysis.create_index([("job_id", ASCENDING)], name="job_id_idx")
    analysis.create_index([("candidate_email", ASCENDING)], name="candidate_email_idx")
    analysis.create_index([("match_score", DESCENDING)], name="match_score_idx")
    analysis.create_index([("analyzed_at", DESCENDING)], name="analyzed_at_idx")
    logger.info("   ✅ Created 5 indexes")
    
    # Interviews collection indexes
    logger.info(f"\n📁 Creating indexes for '{Collections.INTERVIEWS}'...")
    interviews = db[Collections.INTERVIEWS]
    interviews.create_index([("interview_id", ASCENDING)], unique=True, name="interview_id_unique")
    interviews.create_index([("room_id", ASCENDING)], unique=True, name="room_id_unique")
    interviews.create_index([("candidate_email", ASCENDING)], name="candidate_email_idx")
    interviews.create_index([("status", ASCENDING)], name="status_idx")
    interviews.create_index([("scheduled_at", DESCENDING)], name="scheduled_at_idx")
    logger.info("   ✅ Created 5 indexes")
    
    # Email Logs collection indexes
    logger.info(f"\n📁 Creating indexes for '{Collections.EMAIL_LOGS}'...")
    emails = db[Collections.EMAIL_LOGS]
    emails.create_index([("email_id", ASCENDING)], unique=True, name="email_id_unique")
    emails.create_index([("to_email", ASCENDING)], name="to_email_idx")
    emails.create_index([("email_type", ASCENDING)], name="email_type_idx")
    emails.create_index([("sent_at", DESCENDING)], name="sent_at_idx")
    emails.create_index([("status", ASCENDING)], name="status_idx")
    logger.info("   ✅ Created 5 indexes")
    
    # Interview Questions collection indexes
    logger.info(f"\n📁 Creating indexes for '{Collections.INTERVIEW_QUESTIONS}'...")
    questions = db[Collections.INTERVIEW_QUESTIONS]
    questions.create_index([("question_id", ASCENDING)], unique=True, name="question_id_unique")
    questions.create_index([("interview_id", ASCENDING)], name="interview_id_idx")
    questions.create_index([("job_id", ASCENDING)], name="job_id_idx")
    logger.info("   ✅ Created 3 indexes")
    
    # Resume Analysis Results collection indexes
    logger.info(f"\n📁 Creating indexes for '{Collections.RESUME_ANALYSIS_RESULTS}'...")
    resume_analysis = db[Collections.RESUME_ANALYSIS_RESULTS]
    resume_analysis.create_index([("analysis_id", ASCENDING)], unique=True, name="analysis_id_unique")
    resume_analysis.create_index([("resume_id", ASCENDING)], name="resume_id_idx")
    resume_analysis.create_index([("candidate_email", ASCENDING)], name="candidate_email_idx")
    resume_analysis.create_index([("analyzed_at", DESCENDING)], name="analyzed_at_idx")
    logger.info("   ✅ Created 4 indexes")
    
    # Improved Resumes collection indexes
    logger.info(f"\n📁 Creating indexes for '{Collections.IMPROVED_RESUMES}'...")
    improved = db[Collections.IMPROVED_RESUMES]
    improved.create_index([("improved_resume_id", ASCENDING)], unique=True, name="improved_resume_id_unique")
    improved.create_index([("original_resume_id", ASCENDING)], name="original_resume_id_idx")
    improved.create_index([("candidate_email", ASCENDING)], name="candidate_email_idx")
    improved.create_index([("generated_at", DESCENDING)], name="generated_at_idx")
    logger.info("   ✅ Created 4 indexes")
    
    # Q&A Sessions collection indexes
    logger.info(f"\n📁 Creating indexes for '{Collections.QA_SESSIONS}'...")
    qa = db[Collections.QA_SESSIONS]
    qa.create_index([("qa_id", ASCENDING)], unique=True, name="qa_id_unique")
    qa.create_index([("resume_id", ASCENDING)], name="resume_id_idx")
    qa.create_index([("user_email", ASCENDING)], name="user_email_idx")
    qa.create_index([("session_started_at", DESCENDING)], name="session_started_at_idx")
    logger.info("   ✅ Created 4 indexes")
    
    logger.info("\n✅ All indexes created successfully!")


def seed_initial_data():
    """
    Seed initial data (optional)
    
    Why: Useful for development/testing
    """
    logger.info("\n" + "="*80)
    logger.info("🌱 SEEDING INITIAL DATA")
    logger.info("="*80)
    
    db = get_db()
    
    # Check if admin user exists
    users = db[Collections.USERS]
    admin_email = "admin@resumate.com"
    
    if users.find_one({"email": admin_email}):
        logger.info("⚠️  Admin user already exists, skipping seed data")
        return
    
    # Create admin user (example)
    logger.info(f"👤 Creating admin user: {admin_email}")
    import bcrypt
    
    admin_user = {
        "email": admin_email,
        "password_hash": bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(),
        "name": "Admin User",
        "role": "admin",
        "firebase_uid": None,
        "company": "Resumate",
        "phone": None,
        "profile_image": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_login": None,
        "is_active": True,
        "metadata": {}
    }
    
    users.insert_one(admin_user)
    logger.info("✅ Admin user created")
    logger.info("   📧 Email: admin@resumate.com")
    logger.info("   🔑 Password: admin123")
    logger.info("   ⚠️  CHANGE THIS PASSWORD IN PRODUCTION!")


def verify_setup():
    """
    Verify database setup
    
    Returns:
        True if setup is valid
    """
    logger.info("\n" + "="*80)
    logger.info("🔍 VERIFYING DATABASE SETUP")
    logger.info("="*80)
    
    try:
        client = get_mongo_client()
        db = get_db()
        
        # Check connection
        if not client.ping():
            logger.error("❌ MongoDB connection failed")
            return False
        
        logger.info("✅ Connection: OK")
        
        # Check collections
        collections = db.list_collection_names()
        logger.info(f"✅ Collections: {len(collections)}/{len(ALL_COLLECTIONS)}")
        
        missing = set(ALL_COLLECTIONS) - set(collections)
        if missing:
            logger.warning(f"⚠️  Missing collections: {missing}")
        
        # Get database stats
        stats = client.get_stats()
        logger.info(f"✅ Database: {stats.get('database')}")
        logger.info(f"   📊 Collections: {stats.get('collections')}")
        logger.info(f"   💾 Data Size: {stats.get('data_size_mb')} MB")
        logger.info(f"   📑 Indexes: {stats.get('indexes')}")
        logger.info(f"   📄 Documents: {stats.get('objects')}")
        
        logger.info("\n✅ Database setup verified successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def initialize_database(seed_data: bool = False):
    """
    Main initialization function
    
    Args:
        seed_data: Whether to seed initial data
    """
    logger.info("🚀 INITIALIZING RESUMATE DATABASE")
    logger.info("="*80)
    
    try:
        # Step 1: Create collections
        create_collections()
        
        # Step 2: Create indexes
        create_indexes()
        
        # Step 3: Seed data (optional)
        if seed_data:
            seed_initial_data()
        
        # Step 4: Verify setup
        if verify_setup():
            logger.info("\n" + "="*80)
            logger.info("🎉 DATABASE INITIALIZATION COMPLETE!")
            logger.info("="*80)
            logger.info("\n✅ Your MongoDB database is ready to use!")
            logger.info("📚 Collections created: " + str(len(ALL_COLLECTIONS)))
            logger.info("🔍 Indexes optimized for performance")
            logger.info("\n🚀 You can now start using the Resumate application!\n")
        else:
            logger.error("\n❌ Database initialization failed!")
    
    except Exception as e:
        logger.error(f"\n❌ Initialization failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    seed_data = "--seed" in sys.argv or "-s" in sys.argv
    
    if seed_data:
        logger.info("🌱 Seed data option enabled")
    
    # Run initialization
    initialize_database(seed_data=seed_data)
