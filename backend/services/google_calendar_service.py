"""
Google Calendar Service - Generate Meet Links with Refresh Tokens

This service handles:
1. Creating Google Calendar events with Meet links
2. Managing OAuth refresh tokens (valid for 24 hours)
3. Proper error handling with 200 status codes
4. Token refresh and expiration handling

Architecture:
- Uses Google Calendar API v3
- OAuth 2.0 with refresh tokens
- Automatic token refresh when expired
- Error responses always return 200 status with error details
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarService:
    """
    Google Calendar Service for creating Meet links
    
    Why we need this:
    - Generate unique Google Meet links for interviews
    - Manage OAuth tokens (refresh every 24 hours)
    - Handle Google API errors gracefully
    - All errors return 200 status with error details in body
    """
    
    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """
        Initialize Google Calendar Service
        
        Args:
            credentials_path: Path to OAuth client credentials JSON
            token_path: Path to store/load refresh tokens
        """
        self.credentials_path = credentials_path or os.getenv(
            'GOOGLE_CREDENTIALS_PATH',
            'google_credentials.json'
        )
        self.token_path = token_path or os.getenv(
            'GOOGLE_TOKEN_PATH',
            'google_token.json'
        )
        self.service = None
        self.credentials = None
        
        logger.info("🔧 Initializing Google Calendar Service")
        logger.info(f"📁 Credentials path: {self.credentials_path}")
        logger.info(f"📁 Token path: {self.token_path}")
    
    def authenticate(self) -> Tuple[bool, Optional[str]]:
        """
        Authenticate with Google Calendar API
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
            
        Process:
        1. Check for existing token
        2. Refresh if expired
        3. Request new token if needed
        4. Build calendar service
        """
        try:
            logger.info("🔐 Authenticating with Google Calendar API...")
            
            # Check for existing token
            if os.path.exists(self.token_path):
                logger.info("📂 Loading existing token...")
                self.credentials = Credentials.from_authorized_user_file(
                    self.token_path, SCOPES
                )
            
            # Refresh or request new token
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    logger.info("🔄 Refreshing expired token...")
                    self.credentials.refresh(Request())
                    logger.info("✅ Token refreshed successfully")
                else:
                    if not os.path.exists(self.credentials_path):
                        error_msg = f"Google credentials file not found: {self.credentials_path}"
                        logger.error(f"❌ {error_msg}")
                        return False, error_msg
                    
                    logger.info("🆕 Requesting new token (first time setup)...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    self.credentials = flow.run_local_server(port=0)
                    logger.info("✅ New token obtained")
                
                # Save token for future use
                with open(self.token_path, 'w') as token_file:
                    token_file.write(self.credentials.to_json())
                logger.info(f"💾 Token saved to {self.token_path}")
            
            # Build calendar service
            self.service = build('calendar', 'v3', credentials=self.credentials)
            logger.info("✅ Google Calendar API authenticated successfully")
            return True, None
            
        except FileNotFoundError as e:
            error_msg = f"Credentials file not found: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Authentication failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
    
    def create_interview_meeting(
        self,
        candidate_name: str,
        candidate_email: str,
        hr_email: str,
        job_title: str,
        interview_datetime: datetime,
        duration_minutes: int = 30,
        interview_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create Google Calendar event with LEGITIMATE Google Meet link
        
        🔐 IMPORTANT: This method uses the OFFICIAL Google Calendar API to create
        100% legitimate Google Meet rooms. The Meet links are:
        - Created by Google's servers (not generated by us)
        - Real Google Meet rooms accessible to all invited attendees
        - Associated with a Calendar event
        - Compliant with Google Meet's security and privacy policies
        
        How it works:
        1. Creates Calendar event with conferenceData.conferenceSolutionKey.type = 'hangoutsMeet'
        2. Google Calendar API automatically provisions a Meet room
        3. Returns 'hangoutLink' field containing the official Meet URL
        4. Meet room persists as long as the Calendar event exists
        
        Args:
            candidate_name: Candidate's full name
            candidate_email: Candidate's email
            hr_email: HR/interviewer email
            job_title: Position being interviewed for
            interview_datetime: Scheduled date/time
            duration_minutes: Interview duration (default: 30 min)
            interview_id: Optional unique interview ID
            
        Returns:
            Dict with structure (ALWAYS returns 200 status):
            {
                "success": True/False,
                "data": {
                    "meet_link": "https://meet.google.com/xxx-xxxx-xxx",  # Official Google Meet URL
                    "event_id": "calendar_event_id",
                    "calendar_link": "https://calendar.google.com/...",
                    "expires_at": "2025-10-21T10:00:00Z",
                    "refresh_token": "token_here"  # For 24-hour validity
                },
                "error": {
                    "code": "ERROR_CODE",
                    "message": "Error description",
                    "details": {...}
                }  # Only if success = False
            }
        """
        logger.info(f"📅 Creating OFFICIAL Google Meet room via Calendar API")
        logger.info(f"👤 Candidate: {candidate_name} ({candidate_email})")
        logger.info(f"💼 Position: {job_title}")
        logger.info(f"⏰ Scheduled for: {interview_datetime}")
        
        try:
            # Ensure authenticated
            if not self.service:
                auth_success, auth_error = self.authenticate()
                if not auth_success:
                    return {
                        "success": False,
                        "error": {
                            "code": "AUTHENTICATION_FAILED",
                            "message": auth_error or "Failed to authenticate with Google Calendar",
                            "details": {
                                "credentials_path": self.credentials_path,
                                "token_path": self.token_path
                            }
                        }
                    }
            
            # Calculate end time
            end_datetime = interview_datetime + timedelta(minutes=duration_minutes)
            
            # Build event
            event = {
                'summary': f'AI Interview - {job_title}',
                'description': f"""
🤖 AI-Powered Interview Session

Candidate: {candidate_name}
Position: {job_title}
Interview ID: {interview_id or 'N/A'}

This is an automated AI interview session. Please join on time.
The AI interviewer will guide you through the questions.

Good luck! 🍀
                """.strip(),
                'start': {
                    'dateTime': interview_datetime.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'UTC',
                },
                'attendees': [
                    {'email': candidate_email, 'displayName': candidate_name},
                    {'email': hr_email, 'displayName': 'HR Recruiter'},
                ],
                # 🔐 CRITICAL: This is how we create LEGITIMATE Google Meet rooms
                # - 'conferenceSolutionKey': {'type': 'hangoutsMeet'} tells Google to create a real Meet room
                # - Google Calendar API provisions the room on Google's infrastructure
                # - Returns official 'hangoutLink' (e.g., https://meet.google.com/abc-defg-hij)
                # - NOT generated by us - 100% official Google Meet URL
                #
                # 🎥 SECURITY & PERMISSIONS:
                # - Only invited attendees can join directly
                # - Others must request permission from host
                # - Camera/mic permissions controlled by Google Meet's default settings
                # - Recording requires host permission
                'conferenceData': {
                    'createRequest': {
                        'requestId': interview_id or f"interview_{int(datetime.now().timestamp())}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'},  # ← Creates real Google Meet room
                        # Note: Advanced Meet settings (camera/mic restrictions, recording, etc.)
                        # are controlled through Google Workspace admin console, not via API
                    }
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 60},  # 1 hour before
                        {'method': 'popup', 'minutes': 30},  # 30 min before
                    ],
                },
                # 🔒 EVENT SECURITY SETTINGS
                'guestsCanModify': False,          # Only organizer can modify event
                'guestsCanInviteOthers': False,    # Guests cannot invite additional people
                'guestsCanSeeOtherGuests': True,   # Attendees can see each other
                # Note: For stricter Meet room controls (e.g., disable camera for certain users),
                # use Google Workspace admin console to set organization-wide policies
            }
            
            logger.info("📤 Sending event creation request to Google Calendar API...")
            logger.info("   🔐 Requesting Google to provision a real Meet room...")
            
            # Create event with Meet room
            # conferenceDataVersion=1 is REQUIRED to enable Meet link creation
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,  # ← REQUIRED: Enables conferenceData processing
                sendUpdates='all'  # Send email invites to all attendees
            ).execute()
            
            logger.info(f"✅ Event created successfully: {created_event['id']}")
            
            # Validate that we received a legitimate Google Meet link
            meet_link = created_event.get('hangoutLink', '')
            conference_data = created_event.get('conferenceData', {})
            
            # Validation 1: Check if Meet link exists
            if not meet_link:
                logger.error("❌ No Meet link found in event - This should not happen!")
                logger.error(f"Event details: {created_event}")
                return {
                    "success": False,
                    "error": {
                        "code": "NO_MEET_LINK",
                        "message": "Google Calendar event created but no Meet link was generated. This may indicate an API configuration issue.",
                        "details": {
                            "event_id": created_event['id'],
                            "html_link": created_event.get('htmlLink', ''),
                            "conference_data": conference_data
                        }
                    }
                }
            
            # Validation 2: Verify it's a legitimate Google Meet URL format
            if not meet_link.startswith('https://meet.google.com/'):
                logger.error(f"❌ Invalid Meet link format: {meet_link}")
                return {
                    "success": False,
                    "error": {
                        "code": "INVALID_MEET_LINK",
                        "message": f"Meet link has invalid format: {meet_link}",
                        "details": {
                            "event_id": created_event['id'],
                            "meet_link": meet_link
                        }
                    }
                }
            
            # Validation 3: Extract and validate room code
            room_code = meet_link.split('/')[-1]  # e.g., "wjk-wang-kqd"
            if not room_code or len(room_code) < 8:
                logger.warning(f"⚠️ Unusual room code format: {room_code}")
            
            # Validation 4: Verify conferenceData exists
            conference_id = conference_data.get('conferenceId', '')
            if not conference_id:
                logger.warning("⚠️ No conference ID found in conferenceData")
            
            # Calculate expiration (24 hours from creation)
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Get refresh token (if available)
            refresh_token = None
            if self.credentials and self.credentials.refresh_token:
                refresh_token = self.credentials.refresh_token
            
            # Log success with validation details
            logger.info(f"✅ LEGITIMATE Google Meet link created: {meet_link}")
            logger.info(f"   Room Code: {room_code}")
            logger.info(f"   Conference ID: {conference_id}")
            logger.info(f"   Calendar Event: {created_event['id']}")
            logger.info(f"⏳ Token expires at: {expires_at}")
            
            return {
                "success": True,
                "data": {
                    "meet_link": meet_link,
                    "event_id": created_event['id'],
                    "calendar_link": created_event.get('htmlLink', ''),
                    "conference_id": created_event.get('conferenceData', {}).get('conferenceId', ''),
                    "expires_at": expires_at.isoformat(),
                    "refresh_token": refresh_token,
                    "scheduled_for": interview_datetime.isoformat(),
                    "duration_minutes": duration_minutes,
                    "attendees": [
                        {"email": candidate_email, "name": candidate_name},
                        {"email": hr_email, "name": "HR Recruiter"}
                    ]
                }
            }
            
        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8'))
            error_msg = error_details.get('error', {}).get('message', str(e))
            logger.error(f"❌ Google Calendar API error: {error_msg}")
            
            return {
                "success": False,
                "error": {
                    "code": "GOOGLE_API_ERROR",
                    "message": error_msg,
                    "details": {
                        "status": e.resp.status,
                        "reason": e.resp.reason,
                        "error_details": error_details
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Unexpected error creating meeting: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "UNEXPECTED_ERROR",
                    "message": f"Failed to create meeting: {str(e)}",
                    "details": {
                        "exception_type": type(e).__name__,
                        "candidate_email": candidate_email
                    }
                }
            }
    
    def cancel_meeting(self, event_id: str) -> Dict[str, Any]:
        """
        Cancel a scheduled meeting
        
        Args:
            event_id: Google Calendar event ID
            
        Returns:
            Dict with success status (always 200)
        """
        try:
            logger.info(f"🗑️ Canceling event: {event_id}")
            
            if not self.service:
                auth_success, auth_error = self.authenticate()
                if not auth_success:
                    return {
                        "success": False,
                        "error": {
                            "code": "AUTHENTICATION_FAILED",
                            "message": auth_error
                        }
                    }
            
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id,
                sendUpdates='all'  # Notify attendees
            ).execute()
            
            logger.info(f"✅ Event {event_id} cancelled successfully")
            
            return {
                "success": True,
                "data": {
                    "event_id": event_id,
                    "cancelled_at": datetime.utcnow().isoformat()
                }
            }
            
        except HttpError as e:
            logger.error(f"❌ Failed to cancel event: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "CANCEL_FAILED",
                    "message": f"Failed to cancel event: {str(e)}"
                }
            }
    
    def get_meeting_status(self, event_id: str) -> Dict[str, Any]:
        """
        Check if meeting is still valid
        
        Args:
            event_id: Google Calendar event ID
            
        Returns:
            Dict with meeting status
        """
        try:
            if not self.service:
                auth_success, auth_error = self.authenticate()
                if not auth_success:
                    return {
                        "success": False,
                        "error": {
                            "code": "AUTHENTICATION_FAILED",
                            "message": auth_error
                        }
                    }
            
            event = self.service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            return {
                "success": True,
                "data": {
                    "event_id": event_id,
                    "status": event.get('status', 'unknown'),
                    "meet_link": event.get('hangoutLink', ''),
                    "start_time": event['start'].get('dateTime'),
                    "end_time": event['end'].get('dateTime'),
                }
            }
            
        except HttpError as e:
            return {
                "success": False,
                "error": {
                    "code": "EVENT_NOT_FOUND",
                    "message": f"Event not found or inaccessible: {str(e)}"
                }
            }


# Test/Demo usage
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*80)
    print("🧪 TESTING: Google Calendar Service")
    print("="*80 + "\n")
    
    # Initialize service
    calendar_service = GoogleCalendarService()
    
    # Test authentication
    print("📝 Step 1: Testing authentication...")
    auth_success, auth_error = calendar_service.authenticate()
    
    if auth_success:
        print("✅ Authentication successful!\n")
        
        # Test creating a meeting
        print("📝 Step 2: Creating test interview meeting...")
        
        # Schedule for tomorrow at 10 AM
        interview_time = datetime.now() + timedelta(days=1)
        interview_time = interview_time.replace(hour=10, minute=0, second=0, microsecond=0)
        
        result = calendar_service.create_interview_meeting(
            candidate_name="Test Candidate",
            candidate_email="candidate@example.com",
            hr_email="hr@example.com",
            job_title="Python Developer",
            interview_datetime=interview_time,
            duration_minutes=30,
            interview_id="test-interview-123"
        )
        
        print(f"\n📊 Result:")
        print(json.dumps(result, indent=2))
        
        if result['success']:
            print(f"\n✅ Meeting created successfully!")
            print(f"🔗 Meet link: {result['data']['meet_link']}")
            print(f"📅 Calendar link: {result['data']['calendar_link']}")
            print(f"⏳ Expires at: {result['data']['expires_at']}")
        else:
            print(f"\n❌ Meeting creation failed:")
            print(f"Error: {result['error']['message']}")
    else:
        print(f"❌ Authentication failed: {auth_error}")
        print("\n💡 Setup Instructions:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create a project")
        print("3. Enable Google Calendar API")
        print("4. Create OAuth 2.0 credentials")
        print("5. Download credentials as 'google_credentials.json'")
        print("6. Place in backend folder")
    
    print("\n" + "="*80)
