"""
Email Repository - Handles email logging and tracking

Features:
- Log all sent emails
- Track email delivery status
- Email history
- Email templates
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
from bson import ObjectId

from db.mongo_client import get_collection
from db.models import Collections

logger = logging.getLogger(__name__)


class EmailRepository:
    """Repository for email logging operations"""
    
    def __init__(self):
        self.collection = get_collection(Collections.EMAIL_LOGS)
    
    def log_email(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        body: str,
        email_type: str,
        job_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        interview_id: Optional[str] = None,
        has_attachment: bool = False,
        attachment_name: Optional[str] = None,
        sent_by: Optional[str] = None,
        status: str = "pending"
    ) -> Optional[str]:
        """
        Log an email
        
        Args:
            recipient_email: Recipient's email
            recipient_name: Recipient's name
            subject: Email subject
            body: Email body
            email_type: Type (selection, rejection, interview_invite, etc.)
            job_id: Related job ID
            candidate_id: Related candidate ID
            interview_id: Related interview ID
            has_attachment: Whether email has attachment
            attachment_name: Attachment filename
            sent_by: User ID who sent
            status: Email status (pending, sent, failed)
            
        Returns:
            Email log ID if successful, None otherwise
        """
        try:
            import uuid
            
            email_doc = {
                "email_id": str(uuid.uuid4()),  # Unique email ID for index
                "recipient_email": recipient_email,
                "recipient_name": recipient_name,
                "subject": subject,
                "body": body,
                "email_type": email_type,
                "job_id": job_id,
                "candidate_id": candidate_id,
                "interview_id": interview_id,
                "has_attachment": has_attachment,
                "attachment_name": attachment_name,
                "sent_by": sent_by,
                "status": status,
                "sent_at": datetime.utcnow() if status == "sent" else None,
                "created_at": datetime.utcnow(),
                "error_message": None
            }
            
            result = self.collection.insert_one(email_doc)
            logger.info(f"✅ Email logged: {recipient_email} - {email_type} (ID: {result.inserted_id})")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to log email: {str(e)}")
            return None
    
    def update_email_status(
        self,
        email_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """Update email status"""
        try:
            updates = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            if status == "sent":
                updates["sent_at"] = datetime.utcnow()
            
            if error_message:
                updates["error_message"] = error_message
            
            result = self.collection.update_one(
                {"_id": ObjectId(email_id)},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to update email status: {str(e)}")
            return False
    
    def get_emails_by_recipient(self, recipient_email: str) -> List[Dict]:
        """Get all emails sent to a recipient"""
        try:
            emails = list(self.collection.find({"recipient_email": recipient_email}))
            for email in emails:
                email['_id'] = str(email['_id'])
            return emails
        except Exception as e:
            logger.error(f"❌ Failed to get emails: {str(e)}")
            return []
    
    def get_emails_by_job(self, job_id: str) -> List[Dict]:
        """Get all emails for a job"""
        try:
            emails = list(self.collection.find({"job_id": job_id}))
            for email in emails:
                email['_id'] = str(email['_id'])
            return emails
        except Exception as e:
            logger.error(f"❌ Failed to get emails: {str(e)}")
            return []
    
    def get_emails_by_type(self, email_type: str, limit: int = 100) -> List[Dict]:
        """Get emails by type"""
        try:
            emails = list(self.collection.find({"email_type": email_type}).limit(limit))
            for email in emails:
                email['_id'] = str(email['_id'])
            return emails
        except Exception as e:
            logger.error(f"❌ Failed to get emails: {str(e)}")
            return []
    
    def get_failed_emails(self) -> List[Dict]:
        """Get all failed emails"""
        try:
            emails = list(self.collection.find({"status": "failed"}))
            for email in emails:
                email['_id'] = str(email['_id'])
            return emails
        except Exception as e:
            logger.error(f"❌ Failed to get failed emails: {str(e)}")
            return []
    
    def get_email_statistics(self, job_id: Optional[str] = None) -> Dict:
        """Get email statistics"""
        try:
            match_query = {"job_id": job_id} if job_id else {}
            
            pipeline = [
                {"$match": match_query},
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }}
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            stats = {
                "total": 0,
                "sent": 0,
                "failed": 0,
                "pending": 0
            }
            
            for result in results:
                status = result['_id']
                count = result['count']
                stats['total'] += count
                if status in stats:
                    stats[status] = count
            
            return stats
        except Exception as e:
            logger.error(f"❌ Failed to get email statistics: {str(e)}")
            return {}
