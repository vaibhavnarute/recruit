"""
Q&A Repository - Handles Q&A sessions and questions

Features:
- Create Q&A sessions
- Track questions and answers
- Conversation history
- Performance tracking
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
from bson import ObjectId

from db.mongo_client import get_collection
from db.models import Collections

logger = logging.getLogger(__name__)


class QARepository:
    """Repository for Q&A operations"""
    
    def __init__(self):
        self.sessions_collection = get_collection(Collections.QA_SESSIONS)
        self.questions_collection = get_collection(Collections.INTERVIEW_QUESTIONS)
    
    def create_session(
        self,
        interview_id: Optional[str] = None,
        job_id: Optional[str] = None,
        resume_text: Optional[str] = None,
        job_description: Optional[str] = None,
        session_type: str = "general",
        created_by: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a Q&A session
        
        Args:
            interview_id: Related interview ID
            job_id: Related job ID
            resume_text: Resume content for context
            job_description: Job description for context
            session_type: Type of session (general, interview, improvement)
            created_by: User ID who created
            
        Returns:
            Session ID if successful, None otherwise
        """
        try:
            import uuid
            
            session_doc = {
                "qa_id": str(uuid.uuid4()),  # Unique Q&A session ID for index
                "interview_id": interview_id,
                "job_id": job_id,
                "resume_text": resume_text,
                "job_description": job_description,
                "session_type": session_type,
                "created_by": created_by,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "status": "active",  # active, completed, abandoned
                "questions_count": 0,
                "conversation_history": []
            }
            
            result = self.sessions_collection.insert_one(session_doc)
            logger.info(f"✅ Q&A session created (ID: {result.inserted_id})")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to create Q&A session: {str(e)}")
            return None
    
    def add_question(
        self,
        session_id: str,
        question: str,
        answer: str,
        question_type: str = "general",
        is_ai_generated: bool = True
    ) -> Optional[str]:
        """
        Add a question to the session
        
        Args:
            session_id: Q&A session ID
            question: Question text
            answer: Answer text
            question_type: Type of question
            is_ai_generated: Whether question was AI-generated
            
        Returns:
            Question ID if successful, None otherwise
        """
        try:
            # Add to conversation history in session
            conversation_entry = {
                "question": question,
                "answer": answer,
                "timestamp": datetime.utcnow(),
                "question_type": question_type
            }
            
            self.sessions_collection.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$push": {"conversation_history": conversation_entry},
                    "$inc": {"questions_count": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            # Also store as individual question
            import uuid
            
            question_doc = {
                "question_id": str(uuid.uuid4()),  # Unique question ID for index
                "session_id": session_id,
                "question": question,
                "answer": answer,
                "question_type": question_type,
                "is_ai_generated": is_ai_generated,
                "asked_at": datetime.utcnow()
            }
            
            result = self.questions_collection.insert_one(question_doc)
            logger.info(f"✅ Question added to session {session_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to add question: {str(e)}")
            return None
    
    def get_session_by_id(self, session_id: str) -> Optional[Dict]:
        """Get Q&A session by ID"""
        try:
            session = self.sessions_collection.find_one({"_id": ObjectId(session_id)})
            if session:
                session['_id'] = str(session['_id'])
            return session
        except Exception as e:
            logger.error(f"❌ Failed to get session: {str(e)}")
            return None
    
    def get_sessions_by_interview(self, interview_id: str) -> List[Dict]:
        """Get all Q&A sessions for an interview"""
        try:
            sessions = list(self.sessions_collection.find({"interview_id": interview_id}))
            for session in sessions:
                session['_id'] = str(session['_id'])
            return sessions
        except Exception as e:
            logger.error(f"❌ Failed to get sessions: {str(e)}")
            return []
    
    def get_questions_by_session(self, session_id: str) -> List[Dict]:
        """Get all questions for a session"""
        try:
            questions = list(self.questions_collection.find({"session_id": session_id}))
            for question in questions:
                question['_id'] = str(question['_id'])
            return questions
        except Exception as e:
            logger.error(f"❌ Failed to get questions: {str(e)}")
            return []
    
    def update_session_status(self, session_id: str, status: str) -> bool:
        """Update session status"""
        try:
            result = self.sessions_collection.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"status": status, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to update session status: {str(e)}")
            return False
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get full conversation history for a session"""
        try:
            session = self.sessions_collection.find_one({"_id": ObjectId(session_id)})
            if session and 'conversation_history' in session:
                return session['conversation_history']
            return []
        except Exception as e:
            logger.error(f"❌ Failed to get conversation history: {str(e)}")
            return []
    
    def get_session_statistics(self, job_id: Optional[str] = None) -> Dict:
        """Get Q&A session statistics"""
        try:
            match_query = {"job_id": job_id} if job_id else {}
            
            pipeline = [
                {"$match": match_query},
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "total_questions": {"$sum": "$questions_count"}
                }}
            ]
            
            results = list(self.sessions_collection.aggregate(pipeline))
            
            stats = {
                "total_sessions": 0,
                "active_sessions": 0,
                "completed_sessions": 0,
                "total_questions": 0
            }
            
            for result in results:
                status = result['_id']
                count = result['count']
                questions = result['total_questions']
                
                stats['total_sessions'] += count
                stats['total_questions'] += questions
                
                if status == "active":
                    stats['active_sessions'] = count
                elif status == "completed":
                    stats['completed_sessions'] = count
            
            return stats
        except Exception as e:
            logger.error(f"❌ Failed to get session statistics: {str(e)}")
            return {}
