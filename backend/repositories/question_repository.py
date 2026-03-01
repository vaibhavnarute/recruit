"""
Interview Questions Repository

Handles MongoDB operations for interview questions:
- Store generated questions
- Retrieve questions by interview ID
- Update questions with answers
- Track question analytics
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pymongo import MongoClient
import os
import uuid
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class QuestionRepository:
    """MongoDB repository for interview questions"""
    
    def __init__(self):
        """Initialize MongoDB connection"""
        # Try MONGODB_URI first, then fall back to MONGO_URI for compatibility
        mongo_uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGODB_URI or MONGO_URI not found in environment variables")
        
        # Configure MongoDB client with proper timeout settings for Atlas
        self.client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000,  # 10 seconds
            connectTimeoutMS=10000,  # 10 seconds
            socketTimeoutMS=45000,  # 45 seconds for operations
            maxPoolSize=50,
            retryWrites=True,
            retryReads=True
        )
        # Use database name from environment or default
        db_name = os.getenv("MONGO_DB_NAME", "resumate")
        self.db = self.client.get_database(db_name)
        self.questions_collection = self.db.get_collection("interview_questions")
        
        # Create indexes
        self._create_indexes()
        
        logger.info("✅ Question Repository initialized")
    
    def _create_indexes(self):
        """Create database indexes for efficient querying"""
        try:
            # Drop problematic question_id_unique index if it exists
            try:
                self.questions_collection.drop_index("question_id_unique")
                logger.info("🗑️ Dropped old question_id_unique index")
            except Exception:
                pass  # Index doesn't exist, that's fine
            
            # Index on interview_id for fast retrieval
            self.questions_collection.create_index("interview_id")
            
            # Index on candidate_id
            self.questions_collection.create_index("candidate_id")
            
            # Index on job_id
            self.questions_collection.create_index("job_id")
            
            # Compound index for filtering
            self.questions_collection.create_index([
                ("interview_id", 1),
                ("candidate_id", 1)
            ])
            
            logger.info("✅ Database indexes created")
        except Exception as e:
            logger.warning(f"⚠️ Index creation warning: {str(e)}")
    
    def save_questions(
        self,
        interview_id: str,
        candidate_id: str,
        job_id: str,
        questions: List[Dict[str, Any]],
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Save generated questions to MongoDB
        
        Args:
            interview_id: Unique interview identifier
            candidate_id: Candidate identifier
            job_id: Job identifier
            questions: List of question objects
            metadata: Additional metadata (threshold, categories, etc.)
        
        Returns (ALWAYS succeeds):
            {
                "success": True/False,
                "question_set_id": "uuid",
                "saved_count": 10,
                "error": "error message if failed"
            }
        """
        logger.info(f"💾 Saving {len(questions)} questions for interview {interview_id}")
        
        try:
            if self.questions_collection is None:
                raise ValueError("MongoDB collection not initialized")
            
            # Ensure each question has a unique ID
            for question in questions:
                if "question_id" not in question:
                    question["question_id"] = str(uuid.uuid4())
            
            # Create question set document
            question_set = {
                "interview_id": interview_id,
                "candidate_id": candidate_id,
                "job_id": job_id,
                "questions": questions,
                "total_questions": len(questions),
                "metadata": metadata or {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "status": "pending",  # pending, in_progress, completed
                "answered_count": 0
            }
            
            # Insert into MongoDB
            result = self.questions_collection.insert_one(question_set)
            question_set_id = str(result.inserted_id)
            
            logger.info(f"✅ Questions saved successfully: {question_set_id}")
            logger.info(f"   Total questions: {len(questions)}")
            logger.info(f"   Categories: {metadata.get('categories', {})}")
            
            return {
                "success": True,
                "question_set_id": question_set_id,
                "saved_count": len(questions),
                "interview_id": interview_id
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to save questions: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "error": f"Database error: {str(e)}",
                "saved_count": 0
            }
    
    def get_questions_by_interview(self, interview_id: str) -> Dict[str, Any]:
        """
        Retrieve questions for a specific interview
        
        Returns (ALWAYS 200):
            {
                "success": True/False,
                "data": {
                    "questions": [...],
                    "total_questions": 10,
                    "answered_count": 3,
                    "status": "pending"
                }
            }
        """
        logger.info(f"🔍 Retrieving questions for interview {interview_id}")
        
        try:
            question_set = self.questions_collection.find_one(
                {"interview_id": interview_id}
            )
            
            if not question_set:
                logger.warning(f"⚠️ No questions found for interview {interview_id}")
                return {
                    "success": False,
                    "error": "Questions not found for this interview",
                    "data": None
                }
            
            # Convert ObjectId to string
            question_set["_id"] = str(question_set["_id"])
            
            logger.info(f"✅ Found {question_set['total_questions']} questions")
            
            return {
                "success": True,
                "data": question_set
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to retrieve questions: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    def update_question_answer(
        self,
        interview_id: str,
        question_id: str,
        answer: str,
        is_correct: bool = None,
        score: float = None
    ) -> Dict[str, Any]:
        """
        Update a question with candidate's answer
        
        Returns (ALWAYS 200):
            {"success": True/False}
        """
        logger.info(f"✍️ Updating answer for question {question_id}")
        
        try:
            # Find the question set
            question_set = self.questions_collection.find_one(
                {"interview_id": interview_id}
            )
            
            if not question_set:
                return {
                    "success": False,
                    "error": "Interview not found"
                }
            
            # Update the specific question
            questions = question_set.get("questions", [])
            question_found = False
            
            for q in questions:
                if q.get("question_id") == question_id:
                    q["answer"] = answer
                    q["answered_at"] = datetime.utcnow().isoformat()
                    if is_correct is not None:
                        q["is_correct"] = is_correct
                    if score is not None:
                        q["score"] = score
                    question_found = True
                    break
            
            if not question_found:
                return {
                    "success": False,
                    "error": "Question not found"
                }
            
            # Update answered count
            answered_count = sum(1 for q in questions if "answer" in q)
            
            # Update status
            status = "in_progress"
            if answered_count == len(questions):
                status = "completed"
            
            # Save updates
            self.questions_collection.update_one(
                {"interview_id": interview_id},
                {
                    "$set": {
                        "questions": questions,
                        "answered_count": answered_count,
                        "status": status,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"✅ Answer updated successfully")
            logger.info(f"   Progress: {answered_count}/{len(questions)}")
            
            return {
                "success": True,
                "answered_count": answered_count,
                "total_questions": len(questions),
                "status": status
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to update answer: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_questions_by_candidate(self, candidate_id: str) -> Dict[str, Any]:
        """Get all question sets for a candidate (for adaptive questioning)"""
        logger.info(f"🔍 Retrieving all questions for candidate {candidate_id}")
        
        try:
            question_sets = list(self.questions_collection.find(
                {"candidate_id": candidate_id}
            ).sort("created_at", -1))
            
            # Convert ObjectIds to strings
            for qs in question_sets:
                qs["_id"] = str(qs["_id"])
            
            logger.info(f"✅ Found {len(question_sets)} question sets")
            
            return {
                "success": True,
                "data": question_sets,
                "count": len(question_sets)
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to retrieve candidate questions: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    def get_previous_answers(self, candidate_id: str) -> List[Dict[str, Any]]:
        """
        Get all previous answers for adaptive questioning
        
        Returns list of answered questions with scores
        """
        logger.info(f"📊 Getting previous answers for candidate {candidate_id}")
        
        try:
            question_sets = self.questions_collection.find(
                {"candidate_id": candidate_id}
            ).sort("created_at", -1)
            
            all_answers = []
            for qs in question_sets:
                questions = qs.get("questions", [])
                answered = [q for q in questions if "answer" in q]
                all_answers.extend(answered)
            
            logger.info(f"✅ Found {len(all_answers)} previous answers")
            
            return all_answers
        
        except Exception as e:
            logger.error(f"❌ Failed to get previous answers: {str(e)}")
            return []
    
    def get_question_analytics(self, interview_id: str) -> Dict[str, Any]:
        """Get analytics for question set"""
        logger.info(f"📈 Getting analytics for interview {interview_id}")
        
        try:
            question_set = self.questions_collection.find_one(
                {"interview_id": interview_id}
            )
            
            if not question_set:
                return {"success": False, "error": "Interview not found"}
            
            questions = question_set.get("questions", [])
            answered = [q for q in questions if "answer" in q]
            correct = [q for q in answered if q.get("is_correct", False)]
            
            # Calculate stats
            total = len(questions)
            answered_count = len(answered)
            correct_count = len(correct)
            
            analytics = {
                "total_questions": total,
                "answered": answered_count,
                "pending": total - answered_count,
                "correct": correct_count,
                "incorrect": answered_count - correct_count,
                "accuracy": (correct_count / answered_count * 100) if answered_count > 0 else 0,
                "completion": (answered_count / total * 100) if total > 0 else 0,
                "categories": question_set.get("metadata", {}).get("categories", {}),
                "status": question_set.get("status", "unknown")
            }
            
            logger.info(f"✅ Analytics generated: {analytics['completion']:.1f}% complete")
            
            return {
                "success": True,
                "data": analytics
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to get analytics: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    repo = QuestionRepository()
    
    # Test save
    test_questions = [
        {
            "question_id": "q1",
            "question": "What is Python?",
            "category": "technical",
            "difficulty": "easy"
        }
    ]
    
    result = repo.save_questions(
        interview_id="test-123",
        candidate_id="cand-456",
        job_id="job-789",
        questions=test_questions,
        metadata={"categories": {"technical": 1}}
    )
    
    print(f"Save result: {result}")
