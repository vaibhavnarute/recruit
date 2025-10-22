"""
Repository Layer - Data Access Layer for MongoDB

This package contains repository classes for each feature/functionality.
Repositories handle all database operations for their respective domains.
"""

from .user_repository import UserRepository
from .resume_repository import ResumeRepository
from .job_repository import JobRepository
from .candidate_repository import CandidateRepository
from .analysis_repository import AnalysisRepository
from .interview_repository import InterviewRepository
from .email_repository import EmailRepository
from .qa_repository import QARepository

__all__ = [
    'UserRepository',
    'ResumeRepository',
    'JobRepository',
    'CandidateRepository',
    'AnalysisRepository',
    'InterviewRepository',
    'EmailRepository',
    'QARepository'
]
