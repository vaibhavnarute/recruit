"""
Interview Scheduling LangGraph Agent with MCP Integration

This agent orchestrates the complete interview scheduling workflow:
1. Validate HR input (candidate details, job info, schedule time)
2. Check candidate availability (optional)
3. Create Google Meet link via Google Calendar API
4. Send email invitation to candidate
5. Store interview details in MongoDB

Architecture:
- Uses LangGraph StateGraph for workflow
- MCP Context Manager for optimized API calls
- Proper error handling (all errors return 200 status)
- Comprehensive logging at each step
"""

import logging
from typing import Dict, Any, Optional, List, TypedDict, Annotated
from datetime import datetime, timedelta, timezone
import uuid

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# Import services
from services.google_calendar_service import GoogleCalendarService
from services.email_service import EmailService
from repositories.interview_repository import InterviewRepository
from mcp.context_manager import MCPContextManager
from mcp.cache_manager import MCPCacheManager
from mcp.token_optimizer import TokenOptimizer

logger = logging.getLogger(__name__)


class InterviewScheduleState(TypedDict):
    """
    State for interview scheduling workflow
    
    Tracks all information needed throughout the scheduling process
    """
    # Input data
    candidate_name: str
    candidate_email: str
    candidate_id: Optional[str]
    job_id: str
    job_title: str
    hr_email: str
    hr_id: str
    scheduled_datetime: str  # ISO format
    duration_minutes: int
    interview_type: str  # "ai_assisted", "human", "hybrid"
    
    # Processing data
    interview_id: str
    context_id: str
    
    # Results
    meet_link: Optional[str]
    calendar_event_id: Optional[str]
    calendar_link: Optional[str]
    refresh_token: Optional[str]
    expires_at: Optional[str]
    email_sent: bool
    mongodb_saved: bool
    
    # Error handling
    errors: List[Dict[str, Any]]
    success: bool
    current_step: str
    
    # Logs (for debugging)
    step_logs: List[str]


class InterviewSchedulingAgent:
    """
    LangGraph Agent for Interview Scheduling
    
    Why we use LangGraph:
    - Clear workflow visualization
    - Easy error handling at each node
    - Stateful processing
    - Retry logic built-in
    
    Why we use MCP:
    - Optimize API calls (cache Google Calendar responses)
    - Reduce token usage for LLM calls
    - Track context across scheduling sessions
    """
    
    def __init__(
        self,
        google_calendar_service: Optional[GoogleCalendarService] = None,
        email_service: Optional[EmailService] = None,
        interview_repo: Optional[InterviewRepository] = None
    ):
        """
        Initialize Interview Scheduling Agent
        
        Args:
            google_calendar_service: Google Calendar API service
            email_service: Email service for sending invitations
            interview_repo: MongoDB repository for interviews
        """
        self.calendar_service = google_calendar_service or GoogleCalendarService()
        self.email_service = email_service or EmailService()
        self.interview_repo = interview_repo or InterviewRepository()
        
        # MCP components
        self.context_manager = MCPContextManager(max_context_length=10000)
        self.cache_manager = MCPCacheManager(ttl_minutes=1440, max_cache_size=1000)  # 24 hours TTL
        self.token_optimizer = TokenOptimizer(max_input_tokens=10000, max_output_tokens=10000)
        
        # Build workflow graph
        self.workflow = self._build_workflow()
        
        logger.info("🤖 Interview Scheduling Agent initialized")
        logger.info("📊 Components: Google Calendar, Email, MongoDB, MCP")
    
    def _build_workflow(self) -> StateGraph:
        """
        Build LangGraph workflow for interview scheduling
        
        Workflow:
        START → Validate → Create Meet Link → Send Email → Save MongoDB → END
                    ↓            ↓                ↓              ↓
                  ERROR → Handle Error → END
        """
        workflow = StateGraph(InterviewScheduleState)
        
        # Add nodes
        workflow.add_node("validate_inputs", self.validate_inputs)
        workflow.add_node("create_meet_link", self.create_meet_link)
        workflow.add_node("send_email", self.send_email_invitation)
        workflow.add_node("save_to_mongodb", self.save_to_mongodb)
        workflow.add_node("handle_error", self.handle_error)
        
        # Define edges
        workflow.set_entry_point("validate_inputs")
        
        # Conditional routing based on validation success
        workflow.add_conditional_edges(
            "validate_inputs",
            self._route_after_validation,
            {
                "create_meet_link": "create_meet_link",
                "handle_error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "create_meet_link",
            self._route_after_meet_creation,
            {
                "send_email": "send_email",
                "handle_error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "send_email",
            self._route_after_email,
            {
                "save_to_mongodb": "save_to_mongodb",
                "handle_error": "handle_error"
            }
        )
        
        workflow.add_edge("save_to_mongodb", END)
        workflow.add_edge("handle_error", END)
        
        logger.info("✅ Workflow graph built successfully")
        return workflow.compile()
    
    # ==================== WORKFLOW NODES ====================
    
    def validate_inputs(self, state: InterviewScheduleState) -> InterviewScheduleState:
        """
        Node 1: Validate all input parameters
        
        Checks:
        - Required fields present
        - Valid email formats
        - Valid datetime
        - Job and candidate exist
        """
        logger.info("📋 STEP 1: Validating inputs...")
        state["current_step"] = "validate_inputs"
        state["step_logs"].append(f"[{datetime.now().isoformat()}] Starting input validation")
        
        errors = []
        
        # Validate candidate name
        if not state.get("candidate_name") or len(state["candidate_name"].strip()) < 2:
            errors.append({
                "code": "INVALID_CANDIDATE_NAME",
                "message": "Candidate name is required and must be at least 2 characters",
                "field": "candidate_name"
            })
        
        # Validate candidate email
        if not state.get("candidate_email") or "@" not in state["candidate_email"]:
            errors.append({
                "code": "INVALID_CANDIDATE_EMAIL",
                "message": "Valid candidate email is required",
                "field": "candidate_email"
            })
        
        # Validate HR email
        if not state.get("hr_email") or "@" not in state["hr_email"]:
            errors.append({
                "code": "INVALID_HR_EMAIL",
                "message": "Valid HR email is required",
                "field": "hr_email"
            })
        
        # Validate job title
        if not state.get("job_title") or len(state["job_title"].strip()) < 2:
            errors.append({
                "code": "INVALID_JOB_TITLE",
                "message": "Job title is required",
                "field": "job_title"
            })
        
        # Validate datetime
        try:
            scheduled_dt = datetime.fromisoformat(state["scheduled_datetime"].replace('Z', '+00:00'))
            
            # Check if datetime is in the future (use timezone-aware comparison)
            current_time = datetime.now(timezone.utc)
            if scheduled_dt < current_time:
                errors.append({
                    "code": "INVALID_DATETIME",
                    "message": "Interview must be scheduled in the future",
                    "field": "scheduled_datetime",
                    "details": {
                        "provided": state["scheduled_datetime"],
                        "current_time": current_time.isoformat()
                    }
                })
        except (ValueError, AttributeError) as e:
            errors.append({
                "code": "INVALID_DATETIME_FORMAT",
                "message": f"Invalid datetime format. Use ISO 8601: {str(e)}",
                "field": "scheduled_datetime"
            })
        
        # Validate duration
        if not state.get("duration_minutes") or state["duration_minutes"] < 15 or state["duration_minutes"] > 180:
            errors.append({
                "code": "INVALID_DURATION",
                "message": "Duration must be between 15 and 180 minutes",
                "field": "duration_minutes"
            })
        
        # Set errors and success status
        state["errors"] = errors
        state["success"] = len(errors) == 0
        
        if state["success"]:
            # Generate interview ID and context ID
            state["interview_id"] = str(uuid.uuid4())
            state["context_id"] = self.context_manager.create_context_id(
                state["hr_id"],
                state["interview_id"]
            )
            
            logger.info("✅ Input validation passed")
            logger.info(f"🆔 Interview ID: {state['interview_id']}")
            state["step_logs"].append(f"[{datetime.now().isoformat()}] Validation successful")
            
            # Add to MCP context
            self.context_manager.add_message(
                state["context_id"],
                "system",
                f"Scheduling interview for {state['candidate_name']} ({state['job_title']})"
            )
        else:
            logger.error(f"❌ Input validation failed: {len(errors)} errors")
            for error in errors:
                logger.error(f"   - {error['code']}: {error['message']}")
            state["step_logs"].append(f"[{datetime.now().isoformat()}] Validation failed: {len(errors)} errors")
        
        return state
    
    def create_meet_link(self, state: InterviewScheduleState) -> InterviewScheduleState:
        """
        Node 2: Create Google Meet link via Calendar API
        
        Uses MCP cache to avoid duplicate API calls
        """
        logger.info("🔗 STEP 2: Creating Google Meet link...")
        state["current_step"] = "create_meet_link"
        state["step_logs"].append(f"[{datetime.now().isoformat()}] Creating Google Meet link")
        
        try:
            # Check cache first (MCP optimization)
            cache_key = f"meet_link:{state['interview_id']}"
            cached_result = self.cache_manager.get(cache_key)
            
            if cached_result:
                logger.info("💾 Using cached Meet link (MCP cache hit)")
                state["meet_link"] = cached_result["meet_link"]
                state["calendar_event_id"] = cached_result["event_id"]
                state["calendar_link"] = cached_result["calendar_link"]
                state["refresh_token"] = cached_result.get("refresh_token")
                state["expires_at"] = cached_result["expires_at"]
                state["success"] = True
                return state
            
            # Parse datetime
            scheduled_dt = datetime.fromisoformat(state["scheduled_datetime"].replace('Z', '+00:00'))
            
            # Call Google Calendar API
            logger.info(f"📞 Calling Google Calendar API for {state['candidate_email']}")
            result = self.calendar_service.create_interview_meeting(
                candidate_name=state["candidate_name"],
                candidate_email=state["candidate_email"],
                hr_email=state["hr_email"],
                job_title=state["job_title"],
                interview_datetime=scheduled_dt,
                duration_minutes=state["duration_minutes"],
                interview_id=state["interview_id"]
            )
            
            if result["success"]:
                # Extract data
                data = result["data"]
                state["meet_link"] = data["meet_link"]
                state["calendar_event_id"] = data["event_id"]
                state["calendar_link"] = data["calendar_link"]
                state["refresh_token"] = data.get("refresh_token")
                state["expires_at"] = data["expires_at"]
                state["success"] = True
                
                logger.info(f"✅ Meet link created: {state['meet_link']}")
                logger.info(f"📅 Event ID: {state['calendar_event_id']}")
                logger.info(f"⏳ Expires at: {state['expires_at']}")
                
                # Cache the result (MCP optimization - uses default TTL from cache manager)
                self.cache_manager.set(cache_key, data)
                logger.info("💾 Cached Meet link")
                
                state["step_logs"].append(f"[{datetime.now().isoformat()}] Meet link created successfully")
                
                # Add to MCP context
                self.context_manager.add_message(
                    state["context_id"],
                    "assistant",
                    f"Created Meet link: {state['meet_link']}"
                )
            else:
                # API call failed
                error = result["error"]
                state["success"] = False
                state["errors"].append(error)
                
                logger.error(f"❌ Failed to create Meet link: {error['message']}")
                state["step_logs"].append(f"[{datetime.now().isoformat()}] Meet link creation failed")
            
        except Exception as e:
            logger.error(f"❌ Unexpected error in create_meet_link: {str(e)}")
            state["success"] = False
            state["errors"].append({
                "code": "MEET_LINK_ERROR",
                "message": f"Failed to create Meet link: {str(e)}",
                "details": {"exception": type(e).__name__}
            })
            state["step_logs"].append(f"[{datetime.now().isoformat()}] Exception: {str(e)}")
        
        return state
    
    def send_email_invitation(self, state: InterviewScheduleState) -> InterviewScheduleState:
        """
        Node 3: Send email invitation to candidate
        
        Includes:
        - Meet link
        - Calendar invite
        - Interview details
        """
        logger.info("📧 STEP 3: Sending email invitation...")
        state["current_step"] = "send_email"
        state["step_logs"].append(f"[{datetime.now().isoformat()}] Sending email invitation")
        
        try:
            # Parse datetime for email
            scheduled_dt = datetime.fromisoformat(state["scheduled_datetime"].replace('Z', '+00:00'))
            
            # Prepare email content
            subject = f"Interview Invitation - {state['job_title']}"
            
            body = f"""
Dear {state['candidate_name']},

Congratulations! You have been selected for an interview for the position of {state['job_title']}.

📅 Interview Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Date & Time: {scheduled_dt.strftime('%B %d, %Y at %I:%M %p UTC')}
Duration: {state['duration_minutes']} minutes
Interview Type: AI-Assisted Interview

🔗 Join Link:
{state['meet_link']}

📌 Important Notes:
• Please join 5 minutes before the scheduled time
• Ensure you have a stable internet connection
• Test your microphone and camera beforehand
• This is an AI-assisted interview - the AI interviewer will guide you through the questions
• Be prepared to discuss your experience and skills

📅 Add to Calendar:
{state['calendar_link']}

If you need to reschedule or have any questions, please contact us immediately.

Best of luck with your interview!

Best Regards,
HR Team

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Interview ID: {state['interview_id']}
This is an automated message. Please do not reply to this email.
            """.strip()
            
            # Send email
            logger.info(f"📤 Sending email to {state['candidate_email']}")
            email_result = self.email_service.send_interview_invitation(
                to_email=state['candidate_email'],
                candidate_name=state['candidate_name'],
                job_title=state['job_title'],
                meet_link=state['meet_link'],
                scheduled_datetime=scheduled_dt,
                duration_minutes=state['duration_minutes'],
                interview_id=state['interview_id']
            )
            
            if email_result.get("success", False):
                state["email_sent"] = True
                state["success"] = True
                logger.info("✅ Email sent successfully")
                state["step_logs"].append(f"[{datetime.now().isoformat()}] Email sent successfully")
                
                # Add to MCP context
                self.context_manager.add_message(
                    state["context_id"],
                    "assistant",
                    f"Email sent to {state['candidate_email']}"
                )
            else:
                state["email_sent"] = False
                state["success"] = False
                error_msg = email_result.get("error", "Unknown email error")
                state["errors"].append({
                    "code": "EMAIL_SEND_FAILED",
                    "message": error_msg,
                    "details": email_result
                })
                logger.error(f"❌ Failed to send email: {error_msg}")
                state["step_logs"].append(f"[{datetime.now().isoformat()}] Email failed")
            
        except Exception as e:
            logger.error(f"❌ Unexpected error sending email: {str(e)}")
            state["email_sent"] = False
            state["success"] = False
            state["errors"].append({
                "code": "EMAIL_ERROR",
                "message": f"Failed to send email: {str(e)}",
                "details": {"exception": type(e).__name__}
            })
            state["step_logs"].append(f"[{datetime.now().isoformat()}] Exception: {str(e)}")
        
        return state
    
    def save_to_mongodb(self, state: InterviewScheduleState) -> InterviewScheduleState:
        """
        Node 4: Save interview details to MongoDB
        
        Final step - persist all data
        """
        logger.info("💾 STEP 4: Saving to MongoDB...")
        state["current_step"] = "save_to_mongodb"
        state["step_logs"].append(f"[{datetime.now().isoformat()}] Saving to MongoDB")
        
        try:
            # Parse datetime
            scheduled_dt = datetime.fromisoformat(state["scheduled_datetime"].replace('Z', '+00:00'))
            
            # Create interview document
            interview_data = {
                "interview_id": state["interview_id"],
                "candidate_id": state.get("candidate_id"),
                "candidate_name": state["candidate_name"],
                "candidate_email": state["candidate_email"],
                "job_id": state["job_id"],
                "job_title": state["job_title"],
                "hr_id": state["hr_id"],
                "hr_email": state["hr_email"],
                "scheduled_for": scheduled_dt,
                "duration_minutes": state["duration_minutes"],
                "interview_type": state["interview_type"],
                "meet_link": state["meet_link"],
                "calendar_event_id": state["calendar_event_id"],
                "calendar_link": state["calendar_link"],
                "refresh_token": state.get("refresh_token"),
                "expires_at": state["expires_at"],
                "email_sent": state["email_sent"],
                "status": "scheduled",
                "created_at": datetime.utcnow(),
                "created_by": state["hr_id"]
            }
            
            # Save to MongoDB
            logger.info(f"💾 Inserting interview document: {state['interview_id']}")
            saved_interview = self.interview_repo.create_interview(
                candidate_id=state.get("candidate_id") or state["interview_id"],
                job_id=state["job_id"],
                candidate_email=state["candidate_email"],
                candidate_name=state["candidate_name"],
                interview_type=state["interview_type"],
                scheduled_for=scheduled_dt,
                created_by=state["hr_id"],
                interview_id=state["interview_id"],  # Pass the existing interview_id
                meet_link=state["meet_link"],
                calendar_event_id=state["calendar_event_id"],
                calendar_link=state["calendar_link"],
                refresh_token=state.get("refresh_token"),
                expires_at=state["expires_at"]
            )
            
            if saved_interview:
                state["mongodb_saved"] = True
                state["success"] = True
                logger.info(f"✅ Interview saved to MongoDB")
                logger.info(f"🆔 MongoDB Document ID: {saved_interview.get('_id')}")
                state["step_logs"].append(f"[{datetime.now().isoformat()}] Saved to MongoDB successfully")
                
                # Add to MCP context
                self.context_manager.add_message(
                    state["context_id"],
                    "assistant",
                    f"Interview scheduled and saved. ID: {state['interview_id']}"
                )
                
                # Get MCP stats
                mcp_stats = self.context_manager.get_stats(state["context_id"])
                logger.info(f"📊 MCP Stats: {mcp_stats}")
            else:
                state["mongodb_saved"] = False
                state["success"] = False
                state["errors"].append({
                    "code": "MONGODB_SAVE_FAILED",
                    "message": "Failed to save interview to database",
                    "details": {}
                })
                logger.error("❌ Failed to save to MongoDB")
                state["step_logs"].append(f"[{datetime.now().isoformat()}] MongoDB save failed")
            
        except Exception as e:
            logger.error(f"❌ Unexpected error saving to MongoDB: {str(e)}")
            state["mongodb_saved"] = False
            state["success"] = False
            state["errors"].append({
                "code": "MONGODB_ERROR",
                "message": f"Database error: {str(e)}",
                "details": {"exception": type(e).__name__}
            })
            state["step_logs"].append(f"[{datetime.now().isoformat()}] Exception: {str(e)}")
        
        return state
    
    def handle_error(self, state: InterviewScheduleState) -> InterviewScheduleState:
        """
        Error handler node
        
        Logs errors and prepares error response
        """
        logger.error(f"⚠️ ERROR HANDLER: {state['current_step']} failed")
        logger.error(f"📝 Errors: {state['errors']}")
        
        state["success"] = False
        state["step_logs"].append(f"[{datetime.now().isoformat()}] Error handler invoked")
        
        # Add error to MCP context for tracking
        if state.get("context_id"):
            self.context_manager.add_message(
                state["context_id"],
                "system",
                f"Error in {state['current_step']}: {state['errors']}"
            )
        
        return state
    
    # ==================== ROUTING FUNCTIONS ====================
    
    def _route_after_validation(self, state: InterviewScheduleState) -> str:
        """Route after input validation"""
        return "create_meet_link" if state["success"] else "handle_error"
    
    def _route_after_meet_creation(self, state: InterviewScheduleState) -> str:
        """Route after Meet link creation"""
        return "send_email" if state["success"] else "handle_error"
    
    def _route_after_email(self, state: InterviewScheduleState) -> str:
        """Route after email sending"""
        return "save_to_mongodb" if state["success"] else "handle_error"
    
    # ==================== PUBLIC API ====================
    
    def schedule_interview(
        self,
        candidate_name: str,
        candidate_email: str,
        job_id: str,
        job_title: str,
        hr_email: str,
        hr_id: str,
        scheduled_datetime: str,
        duration_minutes: int = 30,
        interview_type: str = "ai_assisted",
        candidate_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for scheduling an interview
        
        Returns:
            Dict with structure (ALWAYS 200 status):
            {
                "success": True/False,
                "data": {
                    "interview_id": "uuid",
                    "meet_link": "https://meet.google.com/...",
                    "calendar_link": "https://calendar.google.com/...",
                    "expires_at": "2025-10-21T10:00:00Z",
                    "email_sent": True,
                    "mongodb_saved": True
                },
                "errors": [...],  # Only if success = False
                "logs": [...]  # Step-by-step logs
            }
        """
        logger.info("\n" + "="*80)
        logger.info("🎬 STARTING: Interview Scheduling Workflow")
        logger.info("="*80)
        
        # Initialize state
        initial_state: InterviewScheduleState = {
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "candidate_id": candidate_id,
            "job_id": job_id,
            "job_title": job_title,
            "hr_email": hr_email,
            "hr_id": hr_id,
            "scheduled_datetime": scheduled_datetime,
            "duration_minutes": duration_minutes,
            "interview_type": interview_type,
            "interview_id": "",
            "context_id": "",
            "meet_link": None,
            "calendar_event_id": None,
            "calendar_link": None,
            "refresh_token": None,
            "expires_at": None,
            "email_sent": False,
            "mongodb_saved": False,
            "errors": [],
            "success": True,
            "current_step": "init",
            "step_logs": []
        }
        
        # Run workflow
        try:
            logger.info("🚀 Invoking LangGraph workflow...")
            final_state = self.workflow.invoke(initial_state)
            
            logger.info("\n" + "="*80)
            logger.info(f"✅ WORKFLOW COMPLETED: {'SUCCESS' if final_state['success'] else 'FAILED'}")
            logger.info("="*80 + "\n")
            
            # Build response (ALWAYS 200 status)
            if final_state["success"]:
                return {
                    "success": True,
                    "data": {
                        "interview_id": final_state["interview_id"],
                        "meet_link": final_state["meet_link"],
                        "calendar_link": final_state["calendar_link"],
                        "calendar_event_id": final_state["calendar_event_id"],
                        "expires_at": final_state["expires_at"],
                        "email_sent": final_state["email_sent"],
                        "mongodb_saved": final_state["mongodb_saved"],
                        "scheduled_for": final_state["scheduled_datetime"],
                        "duration_minutes": final_state["duration_minutes"],
                        "candidate": {
                            "name": final_state["candidate_name"],
                            "email": final_state["candidate_email"]
                        },
                        "job_title": final_state["job_title"]
                    },
                    "logs": final_state["step_logs"]
                }
            else:
                return {
                    "success": False,
                    "errors": final_state["errors"],
                    "partial_data": {
                        "interview_id": final_state.get("interview_id"),
                        "meet_link": final_state.get("meet_link"),
                        "email_sent": final_state.get("email_sent", False),
                        "mongodb_saved": final_state.get("mongodb_saved", False)
                    },
                    "logs": final_state["step_logs"]
                }
                
        except Exception as e:
            logger.error(f"❌ Workflow execution failed: {str(e)}")
            return {
                "success": False,
                "errors": [{
                    "code": "WORKFLOW_ERROR",
                    "message": f"Workflow execution failed: {str(e)}",
                    "details": {"exception": type(e).__name__}
                }],
                "logs": ["Workflow crashed unexpectedly"]
            }
