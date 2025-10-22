"""
Database Package Initialization

Exports all database modules for easy importing
"""

from db.mongo_client import (
    get_mongo_client,
    get_db,
    get_collection,
    ping_db,
    close_db
)

from db.models import (
    Collections,
    ALL_COLLECTIONS,
    UserRole,
    InterviewStatus,
    CandidateStatus
)

from db.mongo_service import mongo_service

__all__ = [
    'get_mongo_client',
    'get_db',
    'get_collection',
    'ping_db',
    'close_db',
    'Collections',
    'ALL_COLLECTIONS',
    'UserRole',
    'InterviewStatus',
    'CandidateStatus',
    'mongo_service'
]
