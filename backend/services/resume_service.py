"""
Resume Service - Business logic for resume operations

Handles:
- Resume upload and processing
- Text extraction
- Resume analysis
- Resume search
"""

import logging
import os
from typing import Optional, Dict, List
import PyPDF2

from repositories.resume_repository import ResumeRepository

logger = logging.getLogger(__name__)


class ResumeService:
    """Service for resume business logic"""
    
    def __init__(self):
        self.repository = ResumeRepository()
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text.strip()
        except Exception as e:
            logger.error(f"❌ Failed to extract text from PDF: {str(e)}")
            return ""
    
    def upload_resume(
        self,
        file,
        upload_folder: str,
        job_id: Optional[str] = None,
        uploaded_by: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Upload and process resume
        
        Args:
            file: Uploaded file object
            upload_folder: Folder to save file
            job_id: Associated job ID
            uploaded_by: User ID who uploaded
            
        Returns:
            Resume data with ID if successful, None otherwise
        """
        try:
            # Save file
            filename = file.filename
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            # Extract text
            extracted_text = self.extract_text_from_pdf(file_path)
            
            if not extracted_text:
                logger.warning(f"No text extracted from {filename}")
                return None
            
            # Extract basic info (can be enhanced with NLP)
            candidate_email = self._extract_email(extracted_text)
            candidate_phone = self._extract_phone(extracted_text)
            
            # Save to database
            resume_id = self.repository.save_resume(
                filename=filename,
                file_path=file_path,
                extracted_text=extracted_text,
                candidate_email=candidate_email,
                candidate_phone=candidate_phone,
                job_id=job_id,
                uploaded_by=uploaded_by
            )
            
            if resume_id:
                return {
                    "resume_id": resume_id,
                    "filename": filename,
                    "extracted_text": extracted_text,
                    "candidate_email": candidate_email,
                    "status": "uploaded"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to upload resume: {str(e)}")
            return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email from text"""
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone from text"""
        import re
        phone_pattern = r'\+?[\d\s\-\(\)]{10,}'
        match = re.search(phone_pattern, text)
        return match.group(0).strip() if match else None
    
    def get_resume(self, resume_id: str) -> Optional[Dict]:
        """Get resume by ID"""
        return self.repository.get_resume_by_id(resume_id)
    
    def get_resumes_for_job(self, job_id: str) -> List[Dict]:
        """Get all resumes for a job"""
        return self.repository.get_resumes_by_job(job_id)
    
    def update_status(self, resume_id: str, status: str) -> bool:
        """Update resume status"""
        return self.repository.update_resume_status(resume_id, status)
