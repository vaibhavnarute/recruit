"""
Feature Documentation Generator

This script generates comprehensive documentation about all features
and their MongoDB integration.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from db.mongo_client import get_mongo_client, ping_db


def generate_feature_documentation():
    """Generate comprehensive feature documentation"""
    
    features = {
        "User Management": {
            "description": "Complete user registration, authentication, and profile management",
            "repository": "UserRepository",
            "collections": ["users"],
            "features": [
                "User registration with bcrypt password hashing",
                "Email/password authentication",
                "User profile management",
                "Role-based access control (recruiter, admin, candidate)",
                "Last login tracking"
            ],
            "endpoints": [
                "POST /api/auth/register - Register new user",
                "POST /api/auth/login - Authenticate user",
                "GET /api/users/:id - Get user profile",
                "PUT /api/users/:id - Update user profile"
            ]
        },
        
        "Resume Management": {
            "description": "Upload, process, and analyze resumes with text extraction",
            "repository": "ResumeRepository",
            "collections": ["resumes"],
            "features": [
                "PDF resume upload",
                "Automatic text extraction from PDFs",
                "Email and phone extraction",
                "Skills extraction",
                "Resume search and filtering",
                "Resume status tracking (pending, reviewed, selected, rejected)"
            ],
            "endpoints": [
                "POST /api/analyze - Upload and analyze resumes",
                "GET /api/resumes/:id - Get resume details",
                "GET /api/resumes/job/:jobId - Get all resumes for a job"
            ]
        },
        
        "Job Description Management": {
            "description": "Create and manage job postings with requirements",
            "repository": "JobRepository",
            "collections": ["job_descriptions"],
            "features": [
                "Create job postings",
                "Define required skills and experience",
                "Set matching threshold",
                "Track application statistics",
                "Job search and filtering",
                "Job status management (active, closed, on_hold)"
            ],
            "endpoints": [
                "POST /api/jobs - Create job posting",
                "GET /api/jobs/:id - Get job details",
                "GET /api/jobs - Get all active jobs",
                "PUT /api/jobs/:id - Update job",
                "DELETE /api/jobs/:id - Close job"
            ]
        },
        
        "Resume Analysis": {
            "description": "AI-powered resume analysis with scoring and matching",
            "repository": "AnalysisRepository",
            "collections": ["analysis_results"],
            "features": [
                "TF-IDF based similarity scoring",
                "Structured scoring system",
                "ML model predictions (salary, job possibility)",
                "Bias-reduced analysis with anonymization",
                "Analysis history tracking",
                "Performance metrics"
            ],
            "endpoints": [
                "POST /api/analyze - Analyze resumes against job description",
                "GET /api/analysis/:id - Get analysis results",
                "GET /api/analysis/job/:jobId - Get all analyses for a job"
            ]
        },
        
        "Candidate Selection": {
            "description": "Manage candidate selection and rejection with threshold-based filtering",
            "repository": "CandidateRepository",
            "collections": ["selected_candidates", "rejected_candidates"],
            "features": [
                "Automatic selection based on threshold",
                "Manual selection override",
                "Rejection with reasons",
                "Candidate status tracking",
                "Interview scheduling link",
                "Selection history"
            ],
            "endpoints": [
                "GET /api/candidates/selected/:jobId - Get selected candidates",
                "GET /api/candidates/rejected/:jobId - Get rejected candidates",
                "PUT /api/candidates/:id/status - Update candidate status"
            ]
        },
        
        "Interview Management": {
            "description": "Schedule and manage AI-assisted interviews",
            "repository": "InterviewRepository",
            "collections": ["interviews"],
            "features": [
                "Generate unique interview links",
                "AI-assisted interview mode",
                "Interview scheduling",
                "Interview status tracking",
                "Interview data storage",
                "Multiple interview types (ai_assisted, human, hybrid)"
            ],
            "endpoints": [
                "POST /api/interviews - Create interview",
                "GET /api/interviews/:id - Get interview details",
                "GET /api/interviews/job/:jobId - Get all interviews for a job",
                "PUT /api/interviews/:id/status - Update interview status"
            ]
        },
        
        "Email Management": {
            "description": "Send and track all recruitment emails",
            "repository": "EmailRepository",
            "collections": ["email_logs"],
            "features": [
                "Send selection/rejection emails",
                "Interview invitation emails",
                "Email template generation with Groq AI",
                "Email delivery tracking",
                "Attachment support",
                "Email statistics and analytics"
            ],
            "endpoints": [
                "POST /api/send-emails - Send emails to candidates",
                "POST /api/generate-message - Generate email content with AI",
                "GET /api/emails/job/:jobId - Get all emails for a job",
                "GET /api/emails/failed - Get failed emails"
            ]
        },
        
        "Q&A Sessions": {
            "description": "Interactive Q&A sessions with LangGraph integration",
            "repository": "QARepository",
            "collections": ["qa_sessions", "interview_questions"],
            "features": [
                "Create Q&A sessions",
                "AI-powered question generation",
                "Context-aware responses",
                "Conversation history tracking",
                "Session analytics",
                "Multiple session types"
            ],
            "endpoints": [
                "POST /api/qa - Ask questions and get answers",
                "POST /api/qa/session - Create new Q&A session",
                "GET /api/qa/session/:id - Get session details",
                "GET /api/qa/history/:sessionId - Get conversation history"
            ]
        }
    }
    
    print("="*80)
    print("📚 RESUMATE - COMPREHENSIVE FEATURE DOCUMENTATION")
    print("="*80)
    print(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Features: {len(features)}")
    
    # Check MongoDB connection
    print("\n" + "="*80)
    print("🔌 MONGODB CONNECTION STATUS")
    print("="*80)
    
    if ping_db():
        client = get_mongo_client()
        stats = client.get_stats()
        print(f"\n✅ Connected to MongoDB")
        print(f"📊 Database: {stats.get('database')}")
        print(f"📁 Collections: {stats.get('collections')}")
        print(f"💾 Data Size: {stats.get('data_size_mb')} MB")
        print(f"📇 Indexes: {stats.get('indexes')}")
    else:
        print("\n❌ MongoDB not connected")
    
    # Generate feature documentation
    for feature_name, feature_data in features.items():
        print("\n" + "="*80)
        print(f"🎯 {feature_name.upper()}")
        print("="*80)
        
        print(f"\n📝 Description:")
        print(f"   {feature_data['description']}")
        
        print(f"\n🗂️  Repository: {feature_data['repository']}")
        
        print(f"\n📁 MongoDB Collections:")
        for collection in feature_data['collections']:
            print(f"   • {collection}")
        
        print(f"\n✨ Features:")
        for item in feature_data['features']:
            print(f"   ✓ {item}")
        
        print(f"\n🌐 API Endpoints:")
        for endpoint in feature_data['endpoints']:
            print(f"   • {endpoint}")
    
    # Database Schema Overview
    print("\n" + "="*80)
    print("💾 DATABASE SCHEMA OVERVIEW")
    print("="*80)
    
    schema = {
        "users": {
            "fields": ["email", "password", "full_name", "role", "company", "phone", "created_at", "is_active"],
            "indexes": ["email (unique)", "role", "created_at", "is_active"]
        },
        "resumes": {
            "fields": ["filename", "file_path", "extracted_text", "candidate_email", "candidate_name", "skills", "job_id"],
            "indexes": ["candidate_email", "job_id", "uploaded_at", "status"]
        },
        "job_descriptions": {
            "fields": ["title", "description", "requirements", "skills_required", "experience_min", "threshold", "status"],
            "indexes": ["title", "status", "created_at", "created_by", "threshold"]
        },
        "selected_candidates": {
            "fields": ["resume_id", "job_id", "candidate_name", "candidate_email", "score", "selected_at", "status"],
            "indexes": ["job_id", "candidate_email", "resume_id", "selected_at", "status"]
        },
        "rejected_candidates": {
            "fields": ["resume_id", "job_id", "candidate_name", "candidate_email", "score", "reason"],
            "indexes": ["job_id", "candidate_email", "rejected_at"]
        },
        "analysis_results": {
            "fields": ["resume_id", "job_id", "similarity_score", "ml_score", "final_score", "decision", "analyzed_at"],
            "indexes": ["job_id", "resume_id", "decision", "analyzed_at", "final_score"]
        },
        "interviews": {
            "fields": ["candidate_id", "job_id", "room_id", "meet_link", "status", "scheduled_for", "interview_type"],
            "indexes": ["job_id", "candidate_email", "room_id (unique)", "scheduled_for", "status"]
        },
        "email_logs": {
            "fields": ["recipient_email", "subject", "body", "email_type", "job_id", "status", "sent_at"],
            "indexes": ["job_id", "recipient_email", "email_type", "status", "sent_at"]
        },
        "interview_questions": {
            "fields": ["session_id", "question", "answer", "question_type", "is_ai_generated", "asked_at"],
            "indexes": ["session_id", "question_type", "asked_at"]
        },
        "qa_sessions": {
            "fields": ["interview_id", "job_id", "session_type", "questions_count", "conversation_history", "status"],
            "indexes": ["interview_id", "job_id", "session_type", "created_at"]
        }
    }
    
    for collection_name, collection_data in schema.items():
        print(f"\n📋 {collection_name}")
        print(f"   Fields: {', '.join(collection_data['fields'])}")
        print(f"   Indexes: {', '.join(collection_data['indexes'])}")
    
    # Integration Summary
    print("\n" + "="*80)
    print("🔗 INTEGRATION SUMMARY")
    print("="*80)
    
    print(f"""
✅ MongoDB Database: Fully Integrated
✅ Repository Pattern: 8 repositories implemented
✅ Service Layer: Business logic separation
✅ API Endpoints: RESTful API with Flask
✅ LangGraph Integration: AI-powered Q&A
✅ Groq AI Integration: Email generation, analysis
✅ MCP Optimization: Context management, token optimization

📊 Architecture:
   Request → API Endpoint → Service Layer → Repository → MongoDB

🎯 Data Flow:
   1. User uploads resumes → ResumeRepository → MongoDB
   2. System analyzes resumes → AnalysisRepository → MongoDB
   3. Candidates selected/rejected → CandidateRepository → MongoDB
   4. Emails sent → EmailRepository → MongoDB
   5. Interviews scheduled → InterviewRepository → MongoDB
   6. Q&A sessions tracked → QARepository → MongoDB

💡 Every action is stored in MongoDB for:
   - Complete audit trail
   - Analytics and reporting
   - Historical data access
   - Data persistence
   - Backup and recovery
""")
    
    print("="*80)
    print("✅ DOCUMENTATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    try:
        generate_feature_documentation()
    except Exception as e:
        print(f"\n❌ Error generating documentation: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
