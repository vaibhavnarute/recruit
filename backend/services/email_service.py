"""
Email Service - Send professional emails for interviews and notifications

Features:
- Send interview invitations with Meet links
- Professional HTML email templates
- SMTP configuration from environment
- Error handling with 200 status codes
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, Optional

from repositories.email_repository import EmailRepository

logger = logging.getLogger(__name__)


class EmailService:
    """Service for email-related operations"""
    
    def __init__(self):
        self.email_repo = EmailRepository()
        
        # SMTP Configuration
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.sender_email = os.getenv('SENDER_EMAIL', self.smtp_username)
        
        logger.info("📧 Email Service initialized")
        logger.info(f"📮 SMTP Server: {self.smtp_server}:{self.smtp_port}")
        logger.info(f"📨 Sender Email: {self.sender_email}")
    
    def send_interview_invitation(
        self,
        to_email: str,
        candidate_name: str,
        job_title: str,
        meet_link: str,
        scheduled_datetime: datetime,
        duration_minutes: int,
        interview_id: str
    ) -> Dict[str, Any]:
        """
        Send interview invitation email
        
        Returns:
            Dict with success status (always 200)
            {
                "success": True/False,
                "message": "...",
                "error": "..."  # Only if success = False
            }
        """
        logger.info(f"📧 Preparing interview invitation email for {to_email}")
        
        try:
            # Validate SMTP credentials
            if not self.smtp_username or not self.smtp_password:
                error_msg = "SMTP credentials not configured"
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "message": "Email service not configured"
                }
            
            # Format datetime
            formatted_datetime = scheduled_datetime.strftime('%B %d, %Y at %I:%M %p UTC')
            
            # Build email
            subject = f"🎯 Interview Invitation - {job_title}"
            
            # HTML email body
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .info-box {{ background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #667eea; border-radius: 5px; }}
        .button {{ display: inline-block; padding: 15px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; }}
        .highlight {{ color: #667eea; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Interview Invitation</h1>
        </div>
        <div class="content">
            <p>Dear <strong>{candidate_name}</strong>,</p>
            
            <p>Congratulations! You have been selected for an interview for the position of <span class="highlight">{job_title}</span>.</p>
            
            <div class="info-box">
                <h3>📅 Interview Details</h3>
                <ul>
                    <li><strong>Date & Time:</strong> {formatted_datetime}</li>
                    <li><strong>Duration:</strong> {duration_minutes} minutes</li>
                    <li><strong>Interview Type:</strong> AI-Assisted Interview</li>
                    <li><strong>Interview ID:</strong> {interview_id}</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{meet_link}" class="button">🔗 Join Interview</a>
            </div>
            
            <div class="info-box">
                <h3>📌 Important Notes</h3>
                <ul>
                    <li>Please join <strong>5 minutes before</strong> the scheduled time</li>
                    <li>Ensure you have a <strong>stable internet connection</strong></li>
                    <li>Test your <strong>microphone and camera</strong> beforehand</li>
                    <li>This is an <strong>AI-assisted interview</strong> - the AI interviewer will guide you</li>
                    <li>Be prepared to discuss your <strong>experience and skills</strong></li>
                </ul>
            </div>
            
            <p>If you need to reschedule or have any questions, please contact us immediately.</p>
            
            <p><strong>Best of luck with your interview!</strong> 🍀</p>
            
            <p>Best Regards,<br><strong>HR Team</strong></p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
            <p>Interview ID: {interview_id}</p>
        </div>
    </div>
</body>
</html>
            """
            
            # Plain text fallback
            text_body = f"""
Dear {candidate_name},

Congratulations! You have been selected for an interview for the position of {job_title}.

INTERVIEW DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Date & Time: {formatted_datetime}
Duration: {duration_minutes} minutes
Interview Type: AI-Assisted Interview
Interview ID: {interview_id}

JOIN LINK:
{meet_link}

IMPORTANT NOTES:
• Please join 5 minutes before the scheduled time
• Ensure you have a stable internet connection
• Test your microphone and camera beforehand
• This is an AI-assisted interview - the AI interviewer will guide you
• Be prepared to discuss your experience and skills

If you need to reschedule or have any questions, please contact us immediately.

Best of luck with your interview!

Best Regards,
HR Team

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated message. Please do not reply to this email.
Interview ID: {interview_id}
            """
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach both plain text and HTML
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            logger.info(f"📤 Connecting to SMTP server: {self.smtp_server}:{self.smtp_port}")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                logger.info("🔐 Logging in to SMTP server...")
                server.login(self.smtp_username, self.smtp_password)
                
                logger.info(f"📨 Sending email to {to_email}...")
                server.send_message(msg)
            
            logger.info(f"✅ Email sent successfully to {to_email}")
            
            # Log email in MongoDB
            try:
                self.email_repo.log_email(
                    recipient=to_email,
                    subject=subject,
                    body=text_body,
                    status="sent",
                    metadata={
                        "interview_id": interview_id,
                        "job_title": job_title,
                        "candidate_name": candidate_name,
                        "meet_link": meet_link
                    }
                )
                logger.info("💾 Email logged in MongoDB")
            except Exception as log_error:
                logger.warning(f"⚠️ Failed to log email in MongoDB: {str(log_error)}")
            
            return {
                "success": True,
                "message": f"Interview invitation sent to {to_email}",
                "details": {
                    "recipient": to_email,
                    "subject": subject,
                    "sent_at": datetime.utcnow().isoformat()
                }
            }
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = "SMTP authentication failed. Check username/password."
            logger.error(f"❌ {error_msg}: {str(e)}")
            return {
                "success": False,
                "error": error_msg,
                "message": "Failed to authenticate with email server"
            }
            
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "message": "Failed to send email"
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "message": "Email sending failed"
            }
