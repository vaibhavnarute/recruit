"""
Candidate Service - Candidate management business logic

Placeholder for future candidate-related business logic
"""

from repositories.candidate_repository import CandidateRepository


class CandidateService:
    """Service for candidate-related operations"""
    
    def __init__(self):
        self.candidate_repo = CandidateRepository()
