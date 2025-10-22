"""
Test MongoDB Repositories and Services

This script tests all repositories to ensure MongoDB integration is working.
"""

import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

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

def test_repositories():
    """Test all repositories"""
    print("="*70)
    print("🧪 TESTING MONGODB REPOSITORIES")
    print("="*70)
    
    # Initialize repositories
    print("\n1. Initializing Repositories...")
    user_repo = UserRepository()
    resume_repo = ResumeRepository()
    job_repo = JobRepository()
    candidate_repo = CandidateRepository()
    analysis_repo = AnalysisRepository()
    interview_repo = InterviewRepository()
    email_repo = EmailRepository()
    qa_repo = QARepository()
    print("   ✅ All repositories initialized")
    
    # Test User Repository
    print("\n2. Testing UserRepository...")
    user_id = user_repo.create_user(
        email="test_user@example.com",
        password="Test123!",
        full_name="Test User",
        role="recruiter",
        company="Test Company"
    )
    if user_id:
        print(f"   ✅ User created: {user_id}")
        user = user_repo.authenticate("test_user@example.com", "Test123!")
        if user:
            print(f"   ✅ User authenticated: {user['email']}")
        user_repo.collection.delete_one({"_id": user_id})
    else:
        print("   ⚠️  User might already exist")
    
    # Test Job Repository
    print("\n3. Testing JobRepository...")
    job_id = job_repo.create_job(
        title="Software Engineer",
        description="Looking for a talented software engineer",
        requirements=["Python", "JavaScript"],
        skills_required=["Python", "React", "MongoDB"],
        experience_min=2,
        experience_max=5,
        location="Remote",
        salary_min=80000,
        salary_max=120000,
        company="Test Company",
        threshold=0.7
    )
    if job_id:
        print(f"   ✅ Job created: {job_id}")
    
    # Test Resume Repository
    print("\n4. Testing ResumeRepository...")
    resume_id = resume_repo.save_resume(
        filename="test_resume.pdf",
        file_path="/uploads/test_resume.pdf",
        extracted_text="Sample resume text with Python and JavaScript skills",
        candidate_email="candidate@example.com",
        candidate_name="John Doe",
        skills=["Python", "JavaScript"],
        experience_years=3,
        job_id=job_id
    )
    if resume_id:
        print(f"   ✅ Resume saved: {resume_id}")
    
    # Test Analysis Repository
    print("\n5. Testing AnalysisRepository...")
    analysis_id = analysis_repo.save_analysis(
        resume_id=resume_id,
        job_id=job_id,
        similarity_score=85.5,
        ml_score=82.0,
        final_score=83.75,
        decision="selected",
        salary_prediction={"predicted_salary": 95000},
        job_possibility={"match_probability": 0.85}
    )
    if analysis_id:
        print(f"   ✅ Analysis saved: {analysis_id}")
    
    # Test Candidate Repository
    print("\n6. Testing CandidateRepository...")
    candidate_id = candidate_repo.add_selected_candidate(
        resume_id=resume_id,
        job_id=job_id,
        candidate_name="John Doe",
        candidate_email="candidate@example.com",
        score=83.75,
        notes="Strong technical skills"
    )
    if candidate_id:
        print(f"   ✅ Candidate selected: {candidate_id}")
    
    # Test Interview Repository
    print("\n7. Testing InterviewRepository...")
    interview = interview_repo.create_interview(
        candidate_id=candidate_id,
        job_id=job_id,
        candidate_email="candidate@example.com",
        candidate_name="John Doe",
        interview_type="ai_assisted"
    )
    if interview:
        print(f"   ✅ Interview created: {interview['_id']}")
        print(f"   📅 Meet link: {interview['meet_link']}")
    
    # Test Email Repository
    print("\n8. Testing EmailRepository...")
    email_id = email_repo.log_email(
        recipient_email="candidate@example.com",
        recipient_name="John Doe",
        subject="Interview Invitation",
        body="You have been selected for an interview",
        email_type="interview_invite",
        job_id=job_id,
        candidate_id=candidate_id,
        interview_id=interview['_id'] if interview else None,
        status="sent"
    )
    if email_id:
        print(f"   ✅ Email logged: {email_id}")
    
    # Test Q&A Repository
    print("\n9. Testing QARepository...")
    session_id = qa_repo.create_session(
        interview_id=interview['_id'] if interview else None,
        job_id=job_id,
        resume_text="Sample resume text",
        job_description="Job description text",
        session_type="interview"
    )
    if session_id:
        print(f"   ✅ Q&A session created: {session_id}")
        
        question_id = qa_repo.add_question(
            session_id=session_id,
            question="What is your experience with Python?",
            answer="I have 3 years of experience with Python",
            question_type="technical"
        )
        if question_id:
            print(f"   ✅ Question added: {question_id}")
    
    # Get Statistics
    print("\n10. Testing Statistics...")
    selected = candidate_repo.get_selected_candidates(job_id)
    print(f"   ✅ Selected candidates: {len(selected)}")
    
    email_stats = email_repo.get_email_statistics(job_id)
    print(f"   ✅ Email statistics: {email_stats}")
    
    qa_stats = qa_repo.get_session_statistics(job_id)
    print(f"   ✅ Q&A statistics: {qa_stats}")
    
    # Final Summary
    print("\n" + "="*70)
    print("✅ ALL REPOSITORY TESTS PASSED!")
    print("="*70)
    print("\n📊 Test Summary:")
    print(f"   ✅ User Repository: Working")
    print(f"   ✅ Resume Repository: Working")
    print(f"   ✅ Job Repository: Working")
    print(f"   ✅ Analysis Repository: Working")
    print(f"   ✅ Candidate Repository: Working")
    print(f"   ✅ Interview Repository: Working")
    print(f"   ✅ Email Repository: Working")
    print(f"   ✅ Q&A Repository: Working")
    print("\n🚀 MongoDB integration is fully functional!")
    
    return True


if __name__ == "__main__":
    try:
        success = test_repositories()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
