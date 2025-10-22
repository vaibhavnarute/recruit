"""
Analysis Repository - Handles resume analysis results

Features:
- Store analysis results
- Track scores and predictions
- Analysis history
- Performance metrics
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
from bson import ObjectId

from db.mongo_client import get_collection
from db.models import Collections

logger = logging.getLogger(__name__)


class AnalysisRepository:
    """Repository for analysis results operations"""
    
    def __init__(self):
        self.collection = get_collection(Collections.ANALYSIS_RESULTS)
    
    def save_analysis(
        self,
        resume_id: str,
        job_id: str,
        similarity_score: float,
        ml_score: Optional[float] = None,
        final_score: Optional[float] = None,
        decision: str = "pending",
        salary_prediction: Optional[Dict] = None,
        job_possibility: Optional[Dict] = None,
        analysis_details: Optional[Dict] = None,
        analyzed_by: Optional[str] = None
    ) -> Optional[str]:
        """
        Save analysis result
        
        Args:
            resume_id: Resume ID
            job_id: Job ID
            similarity_score: Cosine similarity score
            ml_score: ML model prediction score
            final_score: Combined final score
            decision: selected, rejected, pending
            salary_prediction: Predicted salary details
            job_possibility: Job match probability
            analysis_details: Additional analysis data
            analyzed_by: User ID who performed analysis
            
        Returns:
            Analysis ID if successful, None otherwise
        """
        try:
            analysis_doc = {
                "resume_id": resume_id,
                "job_id": job_id,
                "similarity_score": similarity_score,
                "ml_score": ml_score,
                "final_score": final_score,
                "decision": decision,
                "salary_prediction": salary_prediction,
                "job_possibility": job_possibility,
                "analysis_details": analysis_details or {},
                "analyzed_by": analyzed_by,
                "analyzed_at": datetime.utcnow()
            }
            
            result = self.collection.insert_one(analysis_doc)
            logger.info(f"✅ Analysis saved (ID: {result.inserted_id})")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to save analysis: {str(e)}")
            return None
    
    def get_analysis_by_id(self, analysis_id: str) -> Optional[Dict]:
        """Get analysis by ID"""
        try:
            analysis = self.collection.find_one({"_id": ObjectId(analysis_id)})
            if analysis:
                analysis['_id'] = str(analysis['_id'])
            return analysis
        except Exception as e:
            logger.error(f"❌ Failed to get analysis: {str(e)}")
            return None
    
    def get_analyses_by_job(self, job_id: str) -> List[Dict]:
        """Get all analyses for a job"""
        try:
            analyses = list(self.collection.find({"job_id": job_id}))
            for analysis in analyses:
                analysis['_id'] = str(analysis['_id'])
            return analyses
        except Exception as e:
            logger.error(f"❌ Failed to get analyses: {str(e)}")
            return []
    
    def get_analyses_by_resume(self, resume_id: str) -> List[Dict]:
        """Get all analyses for a resume"""
        try:
            analyses = list(self.collection.find({"resume_id": resume_id}))
            for analysis in analyses:
                analysis['_id'] = str(analysis['_id'])
            return analyses
        except Exception as e:
            logger.error(f"❌ Failed to get analyses: {str(e)}")
            return []
    
    def update_decision(self, analysis_id: str, decision: str) -> bool:
        """Update analysis decision"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(analysis_id)},
                {"$set": {"decision": decision, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to update decision: {str(e)}")
            return False
    
    def get_selected_analyses(self, job_id: Optional[str] = None) -> List[Dict]:
        """Get all selected analyses"""
        try:
            query = {"decision": "selected"}
            if job_id:
                query["job_id"] = job_id
            
            analyses = list(self.collection.find(query))
            for analysis in analyses:
                analysis['_id'] = str(analysis['_id'])
            return analyses
        except Exception as e:
            logger.error(f"❌ Failed to get selected analyses: {str(e)}")
            return []
    
    def get_analysis_statistics(self, job_id: str) -> Dict:
        """Get statistics for a job's analyses"""
        try:
            pipeline = [
                {"$match": {"job_id": job_id}},
                {"$group": {
                    "_id": "$decision",
                    "count": {"$sum": 1},
                    "avg_score": {"$avg": "$similarity_score"}
                }}
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            stats = {
                "total": 0,
                "selected": 0,
                "rejected": 0,
                "pending": 0,
                "avg_score": 0
            }
            
            for result in results:
                decision = result['_id']
                count = result['count']
                stats['total'] += count
                stats[decision] = count
            
            return stats
        except Exception as e:
            logger.error(f"❌ Failed to get statistics: {str(e)}")
            return {}
