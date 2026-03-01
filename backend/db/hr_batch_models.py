"""
HR Batch Management Models

New collections for HR-specific candidate and interview batch management
"""

from datetime import datetime
from typing import Dict, List, Any, Optional


# Collection: interview_batches
INTERVIEW_BATCHES_SCHEMA = {
    "batch_id": str,  # Unique batch ID
    "batch_name": str,  # e.g., "Python Developer Batch - Jan 2025"
    "job_id": str,  # Reference to job_description
    "hr_id": str,  # HR who created the batch
    "hr_email": str,  # HR email
    "hr_name": str,  # HR name
    
    # Batch configuration
    "interview_type": str,  # "AI", "Manual", "Hybrid"
    "batch_size": int,  # Number of candidates in batch
    "scheduled_date": Optional[datetime],  # When interviews scheduled
    "interview_duration_minutes": int,  # Expected duration per interview
    
    # Candidates in batch
    "candidate_ids": List[str],  # List of selected_candidate IDs
    "candidate_emails": List[str],  # List of candidate emails
    "candidates_info": List[Dict[str, Any]],  # Full candidate details
    
    # Batch status
    "status": str,  # "draft", "scheduled", "in_progress", "completed", "cancelled"
    "progress": {
        "total": int,
        "completed": int,
        "in_progress": int,
        "pending": int,
        "failed": int
    },
    
    # Interview links
    "batch_interview_links": List[Dict[str, str]],  # [{candidate_email, interview_link}, ...]
    "meeting_platform": str,  # "google_meet", "zoom", "teams"
    
    # Email tracking
    "invites_sent": bool,
    "invites_sent_at": Optional[datetime],
    "invite_email_ids": List[str],  # References to email_logs
    
    # Timestamps
    "created_at": datetime,
    "updated_at": datetime,
    "completed_at": Optional[datetime],
    
    # Notes
    "notes": Optional[str],
    "metadata": Dict[str, Any]
}


# Enhanced selected_candidates schema with HR tracking
SELECTED_CANDIDATES_ENHANCED_SCHEMA = {
    # Existing fields
    "candidate_email": str,
    "candidate_name": str,
    "job_id": str,
    "resume_id": str,
    "match_score": float,
    "matching_skills": List[str],
    "missing_skills": List[str],
    "strengths": List[str],
    "improvement_areas": List[str],
    
    # Enhanced HR tracking
    "selected_by_hr_id": str,  # HR user ID who selected
    "selected_by_hr_email": str,  # HR email
    "selected_by_hr_name": str,  # HR name
    "selected_at": datetime,
    
    # Selection method
    "selection_method": str,  # "auto" (threshold), "manual" (HR override)
    "acceptance_email_sent": bool,  # Whether acceptance email sent
    "acceptance_email_sent_at": Optional[datetime],
    "acceptance_email_id": Optional[str],  # Reference to email_logs
    
    # Batch tracking
    "batch_id": Optional[str],  # Reference to interview_batches
    "batch_assigned": bool,  # Whether assigned to batch
    "batch_assigned_at": Optional[datetime],
    
    # Interview status
    "status": str,  # "selected", "email_sent", "batch_assigned", "interviewed", "offered", "hired", "declined"
    "interview_link": Optional[str],
    "interview_id": Optional[str],  # Reference to interviews
    "interview_scheduled": bool,
    "interview_scheduled_at": Optional[datetime],
    "interview_completed": bool,
    "interview_completed_at": Optional[datetime],
    
    # HR notes
    "hr_notes": Optional[str],
    "internal_rating": Optional[float],  # HR's internal rating
    "tags": List[str],  # Tags like "urgent", "star_candidate", etc.
    
    # Timestamps
    "created_at": datetime,
    "updated_at": datetime,
    
    "metadata": Dict[str, Any]
}


# Collection: hr_actions_log
HR_ACTIONS_LOG_SCHEMA = {
    "action_id": str,  # Unique action ID
    "hr_id": str,  # HR user ID
    "hr_email": str,  # HR email
    "hr_name": str,  # HR name
    
    # Action details
    "action_type": str,  # "select_candidate", "reject_candidate", "send_email", "create_batch", "schedule_interview"
    "action_target": str,  # "candidate", "batch", "job"
    "target_id": str,  # ID of the target (candidate_id, batch_id, job_id)
    "target_email": Optional[str],  # Email if applicable
    
    # Action context
    "job_id": Optional[str],
    "batch_id": Optional[str],
    "candidate_ids": List[str],  # Multiple candidates affected
    
    # Action details
    "action_details": Dict[str, Any],  # Full action context
    "reason": Optional[str],  # Reason for action
    
    # Result
    "success": bool,
    "error_message": Optional[str],
    
    # Timestamps
    "performed_at": datetime,
    
    "metadata": Dict[str, Any]
}


# Add new collections to Collections class
class BatchCollections:
    """New collection names for batch management"""
    INTERVIEW_BATCHES = "interview_batches"
    HR_ACTIONS_LOG = "hr_actions_log"


# All batch-related collections
BATCH_COLLECTIONS = [
    BatchCollections.INTERVIEW_BATCHES,
    BatchCollections.HR_ACTIONS_LOG
]
