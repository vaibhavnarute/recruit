"""
Comprehensive Integration Test Suite

Tests all features and their MongoDB integration end-to-end.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

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


class IntegrationTest:
    """Comprehensive integration test suite"""
    
    def __init__(self):
        self.test_results = {}
        self.test_data = {}
        
    def setup(self):
        """Setup test environment"""
        print("="*70)
        print("🧪 COMPREHENSIVE INTEGRATION TEST SUITE")
        print("="*70)
        print(f"\nTest Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Initialize repositories
        self.user_repo = UserRepository()
        self.resume_repo = ResumeRepository()
        self.job_repo = JobRepository()
        self.candidate_repo = CandidateRepository()
        self.analysis_repo = AnalysisRepository()
        self.interview_repo = InterviewRepository()
        self.email_repo = EmailRepository()
        self.qa_repo = QARepository()
        
        print("\n✅ All repositories initialized")
        
    def test_mongodb_connection(self):
        """Test 1: MongoDB Connection"""
        print("\n" + "-"*70)
        print("TEST 1: MongoDB Connection")
        print("-"*70)
        
        try:
            assert ping_db(), "MongoDB ping failed"
            client = get_mongo_client()
            stats = client.get_stats()
            
            print(f"✅ MongoDB connected")
            print(f"   Database: {stats.get('database')}")
            print(f"   Collections: {stats.get('collections')}")
            
            self.test_results['mongodb_connection'] = True
            return True
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.test_results['mongodb_connection'] = False
            return False
    
    def test_user_flow(self):
        """Test 2: Complete User Flow"""
        print("\n" + "-"*70)
        print("TEST 2: User Management Flow")
        print("-"*70)
        
        try:
            # Create user
            user_id = self.user_repo.create_user(
                email=f"test_{datetime.now().timestamp()}@example.com",
                password="SecurePass123!",
                full_name="Integration Test User",
                role="recruiter",
                company="Test Corp"
            )
            assert user_id, "User creation failed"
            print(f"✅ User created: {user_id}")
            self.test_data['user_id'] = user_id
            
            # Authenticate user
            user = self.user_repo.get_user_by_id(user_id)
            assert user, "User retrieval failed"
            print(f"✅ User retrieved: {user['email']}")
            
            self.test_results['user_flow'] = True
            return True
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.test_results['user_flow'] = False
            return False
    
    def test_job_flow(self):
        """Test 3: Job Creation and Management"""
        print("\n" + "-"*70)
        print("TEST 3: Job Management Flow")
        print("-"*70)
        
        try:
            # Create job
            job_id = self.job_repo.create_job(
                title="Senior Software Engineer - Test",
                description="Looking for an experienced software engineer with Python and React skills",
                requirements=["5+ years experience", "Strong Python skills", "React experience"],
                skills_required=["Python", "React", "MongoDB", "REST APIs"],
                experience_min=5,
                experience_max=10,
                location="Remote",
                salary_min=100000,
                salary_max=150000,
                company="Test Corp",
                threshold=0.75
            )
            assert job_id, "Job creation failed"
            print(f"✅ Job created: {job_id}")
            self.test_data['job_id'] = job_id
            
            # Retrieve job
            job = self.job_repo.get_job_by_id(job_id)
            assert job, "Job retrieval failed"
            assert job['title'] == "Senior Software Engineer - Test"
            print(f"✅ Job retrieved: {job['title']}")
            
            # Update job statistics
            success = self.job_repo.update_job_statistics(
                job_id=job_id,
                total_applications=10
            )
            assert success, "Job statistics update failed"
            print(f"✅ Job statistics updated")
            
            self.test_results['job_flow'] = True
            return True
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.test_results['job_flow'] = False
            return False
    
    def test_resume_flow(self):
        """Test 4: Resume Upload and Processing"""
        print("\n" + "-"*70)
        print("TEST 4: Resume Management Flow")
        print("-"*70)
        
        try:
            # Save resume
            resume_id = self.resume_repo.save_resume(
                filename="john_doe_resume.pdf",
                file_path="/uploads/test/john_doe_resume.pdf",
                extracted_text="John Doe\nSoftware Engineer\n\nSkills: Python, React, MongoDB, REST APIs\nExperience: 6 years\nEmail: john.doe@example.com\nPhone: +1-234-567-8900",
                candidate_email="john.doe@example.com",
                candidate_name="John Doe",
                candidate_phone="+1-234-567-8900",
                skills=["Python", "React", "MongoDB", "REST APIs"],
                experience_years=6,
                job_id=self.test_data.get('job_id')
            )
            assert resume_id, "Resume creation failed"
            print(f"✅ Resume saved: {resume_id}")
            self.test_data['resume_id'] = resume_id
            
            # Retrieve resume
            resume = self.resume_repo.get_resume_by_id(resume_id)
            assert resume, "Resume retrieval failed"
            assert resume['candidate_name'] == "John Doe"
            print(f"✅ Resume retrieved: {resume['candidate_name']}")
            
            # Search resumes
            resumes = self.resume_repo.search_resumes(skills=["Python"], min_experience=5)
            assert len(resumes) > 0, "Resume search failed"
            print(f"✅ Resume search successful: {len(resumes)} results")
            
            self.test_results['resume_flow'] = True
            return True
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.test_results['resume_flow'] = False
            return False
    
    def test_analysis_flow(self):
        """Test 5: Resume Analysis"""
        print("\n" + "-"*70)
        print("TEST 5: Resume Analysis Flow")
        print("-"*70)
        
        try:
            # Save analysis
            analysis_id = self.analysis_repo.save_analysis(
                resume_id=self.test_data.get('resume_id'),
                job_id=self.test_data.get('job_id'),
                similarity_score=87.5,
                ml_score=85.0,
                final_score=86.25,
                decision="selected",
                salary_prediction={"predicted_salary": 120000, "confidence": 0.85},
                job_possibility={"match_probability": 0.88, "recommendation": "Strong Match"},
                analysis_details={
                    "skills_match": ["Python", "React", "MongoDB"],
                    "experience_match": True,
                    "education_match": True
                }
            )
            assert analysis_id, "Analysis creation failed"
            print(f"✅ Analysis saved: {analysis_id}")
            self.test_data['analysis_id'] = analysis_id
            
            # Retrieve analysis
            analysis = self.analysis_repo.get_analysis_by_id(analysis_id)
            assert analysis, "Analysis retrieval failed"
            assert analysis['decision'] == "selected"
            print(f"✅ Analysis retrieved: Score {analysis['final_score']}%")
            
            # Get statistics
            stats = self.analysis_repo.get_analysis_statistics(self.test_data.get('job_id'))
            print(f"✅ Analysis statistics: {stats}")
            
            self.test_results['analysis_flow'] = True
            return True
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.test_results['analysis_flow'] = False
            return False
    
    def test_candidate_flow(self):
        """Test 6: Candidate Selection/Rejection"""
        print("\n" + "-"*70)
        print("TEST 6: Candidate Management Flow")
        print("-"*70)
        
        try:
            # Add selected candidate
            candidate_id = self.candidate_repo.add_selected_candidate(
                resume_id=self.test_data.get('resume_id'),
                job_id=self.test_data.get('job_id'),
                candidate_name="John Doe",
                candidate_email="john.doe@example.com",
                score=86.25,
                notes="Excellent technical skills, good cultural fit"
            )
            assert candidate_id, "Candidate selection failed"
            print(f"✅ Candidate selected: {candidate_id}")
            self.test_data['candidate_id'] = candidate_id
            
            # Get selected candidates
            selected = self.candidate_repo.get_selected_candidates(self.test_data.get('job_id'))
            assert len(selected) > 0, "Selected candidates retrieval failed"
            print(f"✅ Selected candidates retrieved: {len(selected)}")
            
            # Update candidate status
            success = self.candidate_repo.update_candidate_status(candidate_id, "interviewed")
            assert success, "Candidate status update failed"
            print(f"✅ Candidate status updated to 'interviewed'")
            
            self.test_results['candidate_flow'] = True
            return True
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.test_results['candidate_flow'] = False
            return False
    
    def test_interview_flow(self):
        """Test 7: Interview Scheduling"""
        print("\n" + "-"*70)
        print("TEST 7: Interview Management Flow")
        print("-"*70)
        
        try:
            # Create interview
            interview = self.interview_repo.create_interview(
                candidate_id=self.test_data.get('candidate_id'),
                job_id=self.test_data.get('job_id'),
                candidate_email="john.doe@example.com",
                candidate_name="John Doe",
                interview_type="ai_assisted",
                scheduled_for=datetime.utcnow()
            )
            assert interview, "Interview creation failed"
            print(f"✅ Interview created: {interview['_id']}")
            print(f"   Meet Link: {interview['meet_link']}")
            self.test_data['interview_id'] = interview['_id']
            
            # Mark questions generated
            success = self.interview_repo.mark_questions_generated(interview['_id'])
            assert success, "Interview update failed"
            print(f"✅ Interview questions marked as generated")
            
            self.test_results['interview_flow'] = True
            return True
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.test_results['interview_flow'] = False
            return False
    
    def test_email_flow(self):
        """Test 8: Email Logging"""
        print("\n" + "-"*70)
        print("TEST 8: Email Management Flow")
        print("-"*70)
        
        try:
            # Log selection email
            email_id = self.email_repo.log_email(
                recipient_email="john.doe@example.com",
                recipient_name="John Doe",
                subject="Congratulations! You're Selected",
                body="We're pleased to inform you that you've been selected for the next round...",
                email_type="selection",
                job_id=self.test_data.get('job_id'),
                candidate_id=self.test_data.get('candidate_id'),
                interview_id=self.test_data.get('interview_id'),
                status="sent"
            )
            assert email_id, "Email logging failed"
            print(f"✅ Email logged: {email_id}")
            
            # Get email statistics
            stats = self.email_repo.get_email_statistics(self.test_data.get('job_id'))
            print(f"✅ Email statistics: {stats}")
            
            self.test_results['email_flow'] = True
            return True
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.test_results['email_flow'] = False
            return False
    
    def test_qa_flow(self):
        """Test 9: Q&A Session Management"""
        print("\n" + "-"*70)
        print("TEST 9: Q&A Management Flow")
        print("-"*70)
        
        try:
            # Create Q&A session
            session_id = self.qa_repo.create_session(
                interview_id=self.test_data.get('interview_id'),
                job_id=self.test_data.get('job_id'),
                resume_text="John Doe resume content...",
                job_description="Senior Software Engineer job description...",
                session_type="interview"
            )
            assert session_id, "Q&A session creation failed"
            print(f"✅ Q&A session created: {session_id}")
            
            # Add questions
            for i in range(3):
                question_id = self.qa_repo.add_question(
                    session_id=session_id,
                    question=f"Question {i+1}: Tell me about your Python experience?",
                    answer=f"Answer {i+1}: I have 6 years of Python experience...",
                    question_type="technical"
                )
                assert question_id, f"Question {i+1} addition failed"
            print(f"✅ Added 3 questions to session")
            
            # Get conversation history
            history = self.qa_repo.get_conversation_history(session_id)
            assert len(history) == 3, "Conversation history retrieval failed"
            print(f"✅ Conversation history retrieved: {len(history)} exchanges")
            
            # Get statistics
            stats = self.qa_repo.get_session_statistics(self.test_data.get('job_id'))
            print(f"✅ Q&A statistics: {stats}")
            
            self.test_results['qa_flow'] = True
            return True
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.test_results['qa_flow'] = False
            return False
    
    def display_results(self):
        """Display test results"""
        print("\n" + "="*70)
        print("📊 TEST RESULTS SUMMARY")
        print("="*70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        failed_tests = total_tests - passed_tests
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        print("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {status} - {test_name.replace('_', ' ').title()}")
        
        all_passed = all(self.test_results.values())
        
        if all_passed:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ MongoDB integration is fully functional")
            print("✅ All features are working correctly")
        else:
            print("\n⚠️  SOME TESTS FAILED")
            print("Please review the errors above")
        
        print("="*70)
        
        return all_passed
    
    def run_all_tests(self):
        """Run all integration tests"""
        self.setup()
        
        # Run all tests
        self.test_mongodb_connection()
        self.test_user_flow()
        self.test_job_flow()
        self.test_resume_flow()
        self.test_analysis_flow()
        self.test_candidate_flow()
        self.test_interview_flow()
        self.test_email_flow()
        self.test_qa_flow()
        
        # Display results
        all_passed = self.display_results()
        
        return all_passed


if __name__ == "__main__":
    try:
        test_suite = IntegrationTest()
        all_passed = test_suite.run_all_tests()
        sys.exit(0 if all_passed else 1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
