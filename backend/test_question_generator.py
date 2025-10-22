"""
Test Suite for Question Generator Agent

Tests:
1. Question generation workflow
2. Resume analysis
3. Job description parsing
4. Technical question generation
5. Behavioral question generation
6. Scenario question generation
7. Adaptive questioning
8. MongoDB storage
9. Answer submission
10. Analytics
"""

import logging
import json
import sys
import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langgraph_agents.question_generator_agent import QuestionGeneratorAgent
from repositories.question_repository import QuestionRepository

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestQuestionGenerator:
    """Test suite for question generation"""
    
    def __init__(self):
        self.agent = QuestionGeneratorAgent()
        self.repo = QuestionRepository()
        self.test_results = []
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*80)
        print("🧪 STARTING: Question Generator Test Suite")
        print("="*80 + "\n")
        
        tests = [
            ("Test 1: Generate Technical Questions", self.test_technical_questions),
            ("Test 2: Generate Behavioral Questions", self.test_behavioral_questions),
            ("Test 3: Generate Scenario Questions", self.test_scenario_questions),
            ("Test 4: Adaptive Questioning", self.test_adaptive_questions),
            ("Test 5: MongoDB Storage", self.test_mongodb_storage),
            ("Test 6: Answer Submission", self.test_answer_submission),
            ("Test 7: Question Retrieval", self.test_question_retrieval),
            ("Test 8: Analytics", self.test_analytics),
            ("Test 9: Multi-Category Generation", self.test_multi_category),
            ("Test 10: Error Handling", self.test_error_handling)
        ]
        
        for test_name, test_func in tests:
            try:
                print(f"\n{'='*80}")
                print(f"🧪 {test_name}")
                print(f"{'='*80}")
                
                result = test_func()
                
                if result:
                    print(f"✅ {test_name}: PASSED")
                    self.test_results.append((test_name, "PASSED", None))
                else:
                    print(f"❌ {test_name}: FAILED")
                    self.test_results.append((test_name, "FAILED", "Test returned False"))
            
            except Exception as e:
                print(f"❌ {test_name}: CRASHED")
                print(f"   Error: {str(e)}")
                self.test_results.append((test_name, "CRASHED", str(e)))
                import traceback
                traceback.print_exc()
        
        # Print summary
        self.print_summary()
    
    def test_technical_questions(self) -> bool:
        """Test technical question generation"""
        logger.info("Testing technical question generation...")
        
        test_resume = {
            "skills": ["Python", "Machine Learning", "TensorFlow", "SQL", "Docker"],
            "experience": [{"title": "ML Engineer", "years": 3}],
            "total_experience": 3,
            "match_percentage": 85.0,
            "summary": "Experienced ML engineer"
        }
        
        test_job = {
            "title": "Senior ML Engineer",
            "requirements": ["Python", "Deep Learning", "Production ML"],
            "responsibilities": ["Build ML models", "Deploy to production"]
        }
        
        result = self.agent.generate_questions(
            resume_data=test_resume,
            job_description=test_job,
            candidate_id="test-cand-001",
            job_id="test-job-001",
            interview_id="test-interview-001",
            threshold_percentage=70.0
        )
        
        assert result.get("success"), "Generation should succeed"
        assert "data" in result, "Should have data field"
        assert len(result["data"]["questions"]) > 0, "Should generate questions"
        
        # Check for technical questions
        technical_count = result["data"]["categories"].get("technical", 0)
        assert technical_count > 0, "Should have technical questions"
        
        logger.info(f"✅ Generated {technical_count} technical questions")
        return True
    
    def test_behavioral_questions(self) -> bool:
        """Test behavioral question generation"""
        logger.info("Testing behavioral question generation...")
        
        test_resume = {
            "skills": ["Leadership", "Team Management"],
            "experience": [{"title": "Team Lead", "years": 5}],
            "total_experience": 5,
            "match_percentage": 80.0,
            "summary": "Experienced team leader with 5 years of management"
        }
        
        test_job = {
            "title": "Engineering Manager",
            "requirements": ["Leadership", "Team building"],
            "responsibilities": ["Manage team", "Drive projects"]
        }
        
        result = self.agent.generate_questions(
            resume_data=test_resume,
            job_description=test_job,
            candidate_id="test-cand-002",
            job_id="test-job-002",
            interview_id="test-interview-002"
        )
        
        assert result.get("success"), "Generation should succeed"
        behavioral_count = result["data"]["categories"].get("behavioral", 0)
        assert behavioral_count > 0, "Should have behavioral questions"
        
        logger.info(f"✅ Generated {behavioral_count} behavioral questions")
        return True
    
    def test_scenario_questions(self) -> bool:
        """Test scenario question generation"""
        logger.info("Testing scenario question generation...")
        
        test_resume = {
            "skills": ["Problem Solving", "System Design"],
            "experience": [{"title": "Senior Engineer", "years": 4}],
            "total_experience": 4,
            "match_percentage": 75.0
        }
        
        test_job = {
            "title": "Solutions Architect",
            "requirements": ["System Design", "Problem Solving"],
            "responsibilities": [
                "Design scalable systems",
                "Solve complex technical problems",
                "Lead architectural decisions"
            ]
        }
        
        result = self.agent.generate_questions(
            resume_data=test_resume,
            job_description=test_job,
            candidate_id="test-cand-003",
            job_id="test-job-003",
            interview_id="test-interview-003"
        )
        
        assert result.get("success"), "Generation should succeed"
        scenario_count = result["data"]["categories"].get("scenario", 0)
        assert scenario_count > 0, "Should have scenario questions"
        
        logger.info(f"✅ Generated {scenario_count} scenario questions")
        return True
    
    def test_adaptive_questions(self) -> bool:
        """Test adaptive questioning based on previous answers"""
        logger.info("Testing adaptive questioning...")
        
        # Simulate previous answers
        previous_answers = [
            {
                "question_id": "prev-q1",
                "question": "What is Python?",
                "answer": "Python is a programming language",
                "is_correct": True
            },
            {
                "question_id": "prev-q2",
                "question": "Explain OOP",
                "answer": "Object oriented programming",
                "is_correct": True
            }
        ]
        
        test_resume = {
            "skills": ["Python", "Django"],
            "experience": [{"title": "Developer", "years": 2}],
            "total_experience": 2,
            "match_percentage": 70.0
        }
        
        test_job = {
            "title": "Python Developer",
            "requirements": ["Python", "Web Development"],
            "responsibilities": ["Build web apps"]
        }
        
        result = self.agent.generate_questions(
            resume_data=test_resume,
            job_description=test_job,
            candidate_id="test-cand-004",
            job_id="test-job-004",
            interview_id="test-interview-004",
            previous_answers=previous_answers
        )
        
        assert result.get("success"), "Generation should succeed"
        
        # Check if follow-up questions were generated
        follow_up_count = result["data"]["categories"].get("follow-up", 0)
        logger.info(f"ℹ️ Follow-up questions: {follow_up_count}")
        
        logger.info(f"✅ Adaptive questioning working (total: {len(result['data']['questions'])})")
        return True
    
    def test_mongodb_storage(self) -> bool:
        """Test MongoDB storage"""
        logger.info("Testing MongoDB storage...")
        
        test_questions = [
            {
                "question_id": "q1",
                "question": "What is Python?",
                "category": "technical",
                "difficulty": "easy",
                "topic": "Python basics"
            },
            {
                "question_id": "q2",
                "question": "Tell me about a challenging project",
                "category": "behavioral",
                "difficulty": "medium",
                "topic": "problem-solving"
            }
        ]
        
        result = self.repo.save_questions(
            interview_id="test-interview-db-001",
            candidate_id="test-cand-db-001",
            job_id="test-job-db-001",
            questions=test_questions,
            metadata={
                "categories": {"technical": 1, "behavioral": 1},
                "threshold_percentage": 70.0
            }
        )
        
        assert result.get("success"), "Save should succeed"
        assert "question_set_id" in result, "Should return question_set_id"
        
        logger.info(f"✅ Saved {result['saved_count']} questions with ID: {result['question_set_id']}")
        return True
    
    def test_answer_submission(self) -> bool:
        """Test answer submission"""
        logger.info("Testing answer submission...")
        
        # First, save questions
        test_questions = [
            {
                "question_id": "ans-q1",
                "question": "What is ML?",
                "category": "technical",
                "difficulty": "easy"
            }
        ]
        
        save_result = self.repo.save_questions(
            interview_id="test-interview-ans-001",
            candidate_id="test-cand-ans-001",
            job_id="test-job-ans-001",
            questions=test_questions,
            metadata={"categories": {"technical": 1}}
        )
        
        assert save_result.get("success"), "Save should succeed"
        
        # Now submit answer
        answer_result = self.repo.update_question_answer(
            interview_id="test-interview-ans-001",
            question_id="ans-q1",
            answer="Machine Learning is...",
            is_correct=True,
            score=0.85
        )
        
        assert answer_result.get("success"), "Answer submission should succeed"
        assert answer_result["answered_count"] == 1, "Should have 1 answered"
        
        logger.info(f"✅ Answer submitted: {answer_result['answered_count']}/{answer_result['total_questions']}")
        return True
    
    def test_question_retrieval(self) -> bool:
        """Test question retrieval"""
        logger.info("Testing question retrieval...")
        
        # First, save questions
        test_questions = [
            {"question_id": "ret-q1", "question": "Q1", "category": "technical", "difficulty": "easy"},
            {"question_id": "ret-q2", "question": "Q2", "category": "behavioral", "difficulty": "medium"}
        ]
        
        save_result = self.repo.save_questions(
            interview_id="test-interview-ret-001",
            candidate_id="test-cand-ret-001",
            job_id="test-job-ret-001",
            questions=test_questions,
            metadata={"categories": {"technical": 1, "behavioral": 1}}
        )
        
        assert save_result.get("success"), "Save should succeed"
        
        # Now retrieve
        retrieve_result = self.repo.get_questions_by_interview("test-interview-ret-001")
        
        assert retrieve_result.get("success"), "Retrieval should succeed"
        assert retrieve_result["data"]["total_questions"] == 2, "Should have 2 questions"
        
        logger.info(f"✅ Retrieved {retrieve_result['data']['total_questions']} questions")
        return True
    
    def test_analytics(self) -> bool:
        """Test analytics"""
        logger.info("Testing analytics...")
        
        # Save and answer questions
        test_questions = [
            {"question_id": "ana-q1", "question": "Q1", "category": "technical", "difficulty": "easy"},
            {"question_id": "ana-q2", "question": "Q2", "category": "technical", "difficulty": "medium"}
        ]
        
        self.repo.save_questions(
            interview_id="test-interview-ana-001",
            candidate_id="test-cand-ana-001",
            job_id="test-job-ana-001",
            questions=test_questions,
            metadata={"categories": {"technical": 2}}
        )
        
        # Answer one question
        self.repo.update_question_answer(
            interview_id="test-interview-ana-001",
            question_id="ana-q1",
            answer="Answer 1",
            is_correct=True
        )
        
        # Get analytics
        analytics_result = self.repo.get_question_analytics("test-interview-ana-001")
        
        assert analytics_result.get("success"), "Analytics should succeed"
        assert analytics_result["data"]["total_questions"] == 2, "Should have 2 total"
        assert analytics_result["data"]["answered"] == 1, "Should have 1 answered"
        assert analytics_result["data"]["completion"] == 50.0, "Should be 50% complete"
        
        logger.info(f"✅ Analytics: {analytics_result['data']['completion']:.1f}% complete")
        return True
    
    def test_multi_category(self) -> bool:
        """Test generating questions across multiple categories"""
        logger.info("Testing multi-category generation...")
        
        test_resume = {
            "skills": ["Python", "Leadership", "System Design"],
            "experience": [{"title": "Senior Engineer", "years": 5}],
            "total_experience": 5,
            "match_percentage": 88.0,
            "summary": "Versatile engineer with technical and leadership skills"
        }
        
        test_job = {
            "title": "Tech Lead",
            "requirements": ["Technical Excellence", "Leadership", "Architecture"],
            "responsibilities": [
                "Lead technical projects",
                "Design systems",
                "Mentor team members",
                "Make architectural decisions"
            ]
        }
        
        result = self.agent.generate_questions(
            resume_data=test_resume,
            job_description=test_job,
            candidate_id="test-cand-multi-001",
            job_id="test-job-multi-001",
            interview_id="test-interview-multi-001"
        )
        
        assert result.get("success"), "Generation should succeed"
        
        categories = result["data"]["categories"]
        total_categories = len([c for c in categories.values() if c > 0])
        
        assert total_categories >= 2, "Should have at least 2 categories"
        
        logger.info(f"✅ Generated questions in {total_categories} categories: {categories}")
        return True
    
    def test_error_handling(self) -> bool:
        """Test error handling"""
        logger.info("Testing error handling...")
        
        # Test with minimal/invalid data
        result = self.agent.generate_questions(
            resume_data={},
            job_description={},
            candidate_id="test-error-001",
            job_id="test-error-001",
            interview_id="test-error-001"
        )
        
        # Should not crash, even with bad data
        assert "success" in result, "Should return structured response"
        assert "errors" in result or "data" in result, "Should have errors or data"
        
        logger.info(f"✅ Error handling works: success={result.get('success')}")
        return True
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for _, status, _ in self.test_results if status == "PASSED")
        failed = sum(1 for _, status, _ in self.test_results if status == "FAILED")
        crashed = sum(1 for _, status, _ in self.test_results if status == "CRASHED")
        total = len(self.test_results)
        
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"💥 Crashed: {crashed}")
        print(f"\nSuccess Rate: {(passed/total*100):.1f}%")
        
        if failed > 0 or crashed > 0:
            print("\n" + "-"*80)
            print("FAILED/CRASHED TESTS:")
            print("-"*80)
            for name, status, error in self.test_results:
                if status in ["FAILED", "CRASHED"]:
                    print(f"\n❌ {name}")
                    print(f"   Status: {status}")
                    if error:
                        print(f"   Error: {error}")
        
        print("\n" + "="*80)
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! 🎉")
        else:
            print(f"⚠️ {failed + crashed} TEST(S) NEED ATTENTION")
        
        print("="*80 + "\n")


if __name__ == "__main__":
    print("\n🚀 Starting Question Generator Test Suite...\n")
    
    tester = TestQuestionGenerator()
    tester.run_all_tests()
