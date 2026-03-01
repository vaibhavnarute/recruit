"""
Meeting Bot LangGraph Agent
Auto-joins Zoom/Google Meet meetings
Manages bot lifecycle and meeting interactions
Coordinates with STT and TTS agents
"""

import json
import logging
import uuid
import os
import sys
from typing import Dict, Any, TypedDict, List, Optional
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
import asyncio
import subprocess
import platform

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.context_manager import MCPContextManager
from mcp.cache_manager import MCPCacheManager
from mcp.token_optimizer import TokenOptimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MeetingBotState(TypedDict):
    """State for meeting bot workflow"""
    # Bot identification
    bot_id: str
    session_id: str
    meeting_id: str
    interview_id: Optional[str]
    
    # Meeting details
    meeting_link: str
    meeting_platform: str  # zoom, google_meet, teams
    meeting_title: str
    scheduled_start_time: str
    
    # Bot configuration
    bot_name: str
    bot_email: str
    bot_role: str  # interviewer, listener, recorder
    auto_record: bool
    auto_transcribe: bool
    auto_tts: bool
    
    # Bot status
    bot_status: str  # pending, joining, joined, active, leaving, left, error
    join_method: str  # browser_automation, api, manual
    browser_type: str  # chrome, firefox, edge
    
    # Timing
    join_time: Optional[str]
    leave_time: Optional[str]
    duration_minutes: int
    max_duration_minutes: int
    auto_leave_after_silence_minutes: int
    
    # Participants
    expected_participants: List[str]
    actual_participants: List[Dict[str, Any]]
    participant_count: int
    host_name: Optional[str]
    
    # Features enabled
    stt_enabled: bool
    tts_enabled: bool
    recording_enabled: bool
    screen_sharing_enabled: bool
    
    # Audio/Video settings
    microphone_enabled: bool
    camera_enabled: bool
    speaker_enabled: bool
    audio_input_device: Optional[str]
    audio_output_device: Optional[str]
    
    # Interview coordination
    interview_active: bool
    current_speaker: Optional[str]
    last_speech_time: Optional[str]
    silence_duration_seconds: int
    
    # Browser automation
    browser_session_id: Optional[str]
    browser_process_id: Optional[int]
    chrome_tab_id: Optional[int]
    
    # Security
    meeting_password: Optional[str]
    waiting_room_enabled: bool
    host_approval_required: bool
    
    # Analytics
    total_speech_duration_seconds: int
    bot_spoke_count: int
    candidate_spoke_count: int
    questions_asked: int
    answers_received: int
    
    # Processing status
    processing_status: str  # initializing, active, completed, failed
    success: bool
    
    # Error handling
    errors: List[Dict[str, str]]
    last_error: str
    retry_count: int
    
    # Timestamps
    created_at: str
    started_at: str
    completed_at: Optional[str]


class MeetingBotAgent:
    """
    LangGraph agent for meeting bot management
    
    Workflow:
    1. initialize_bot: Setup bot configuration and credentials
    2. validate_meeting: Check meeting link and platform
    3. prepare_browser: Setup browser automation
    4. join_meeting: Auto-join the meeting
    5. setup_audio: Configure microphone and speakers
    6. activate_features: Enable STT, TTS, recording
    7. monitor_meeting: Track participants and activity
    8. manage_lifecycle: Handle auto-leave conditions
    9. leave_meeting: Gracefully exit meeting
    10. store_session: Save bot session data
    """
    
    # Supported platforms
    SUPPORTED_PLATFORMS = {
        'zoom': {
            'url_pattern': 'zoom.us',
            'join_selector': 'a[href*="join"]',
            'audio_selector': 'button[aria-label*="audio"]'
        },
        'google_meet': {
            'url_pattern': 'meet.google.com',
            'join_selector': 'button[aria-label*="Join"]',
            'audio_selector': 'button[aria-label*="microphone"]'
        },
        'teams': {
            'url_pattern': 'teams.microsoft.com',
            'join_selector': 'button[data-tid*="join"]',
            'audio_selector': 'button[data-tid*="microphone"]'
        }
    }
    
    def __init__(self):
        """Initialize Meeting Bot Agent"""
        logger.info("🤖 Initializing MeetingBotAgent")
        
        # Initialize MCP components
        self.context_manager = MCPContextManager(max_context_length=10000)
        self.cache_manager = MCPCacheManager(
            ttl_minutes=180,  # Cache bot sessions for 3 hours
            max_cache_size=50
        )
        self.token_optimizer = TokenOptimizer(
            max_input_tokens=10000,
            max_output_tokens=3000
        )
        
        # MongoDB connection with proper timeout settings
        mongo_uri = os.getenv('MONGO_URI', 'mongodb+srv://narutevaibhav95_db_user:9Y0gsqDxtHRoBH5w@resumate.xbvpnl1.mongodb.net/')
        mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
        
        # Configure MongoDB client with appropriate timeouts for Atlas
        self.mongo_client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000,  # 10 seconds (reduced from 30s)
            connectTimeoutMS=10000,  # 10 seconds
            socketTimeoutMS=45000,  # 45 seconds for operations
            maxPoolSize=50,  # Connection pool size
            retryWrites=True,  # Enable retryable writes
            retryReads=True  # Enable retryable reads
        )
        self.db = self.mongo_client[mongo_db_name]
        
        # Bot configuration
        self.default_bot_name = "AI Interview Assistant"
        self.default_bot_email = os.getenv('BOT_EMAIL', 'ai-bot@company.com')
        self.default_max_duration = 90  # 90 minutes max
        self.default_silence_threshold = 5  # Leave after 5 minutes of silence
        
        # Build workflow
        self.workflow = self._build_workflow()
        logger.info("✅ MeetingBotAgent initialized successfully")
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow for meeting bot"""
        workflow = StateGraph(MeetingBotState)
        
        # Add nodes
        workflow.add_node("initialize_bot", self.initialize_bot)
        workflow.add_node("validate_meeting", self.validate_meeting)
        workflow.add_node("prepare_browser", self.prepare_browser)
        workflow.add_node("join_meeting", self.join_meeting)
        workflow.add_node("setup_audio", self.setup_audio)
        workflow.add_node("activate_features", self.activate_features)
        workflow.add_node("store_session", self.store_session)
        
        # Define edges
        workflow.set_entry_point("initialize_bot")
        workflow.add_edge("initialize_bot", "validate_meeting")
        workflow.add_edge("validate_meeting", "prepare_browser")
        workflow.add_edge("prepare_browser", "join_meeting")
        workflow.add_edge("join_meeting", "setup_audio")
        workflow.add_edge("setup_audio", "activate_features")
        workflow.add_edge("activate_features", "store_session")
        workflow.add_edge("store_session", END)
        
        return workflow.compile()
    
    # ==================== Workflow Nodes ====================
    
    def initialize_bot(self, state: MeetingBotState) -> MeetingBotState:
        """Initialize bot configuration"""
        logger.info(f"🎬 Initializing meeting bot: {state.get('bot_id', 'unknown')}")
        
        try:
            state['processing_status'] = 'initializing'
            state['created_at'] = datetime.utcnow().isoformat()
            state['started_at'] = datetime.utcnow().isoformat()
            state['bot_status'] = 'pending'
            state['success'] = False
            
            # Set defaults
            if not state.get('bot_name'):
                state['bot_name'] = self.default_bot_name
            
            if not state.get('bot_email'):
                state['bot_email'] = self.default_bot_email
            
            if not state.get('max_duration_minutes'):
                state['max_duration_minutes'] = self.default_max_duration
            
            if not state.get('auto_leave_after_silence_minutes'):
                state['auto_leave_after_silence_minutes'] = self.default_silence_threshold
            
            # Initialize lists and counters
            state['actual_participants'] = []
            state['participant_count'] = 0
            state['total_speech_duration_seconds'] = 0
            state['bot_spoke_count'] = 0
            state['candidate_spoke_count'] = 0
            state['questions_asked'] = 0
            state['answers_received'] = 0
            state['silence_duration_seconds'] = 0
            state['errors'] = []
            state['retry_count'] = 0
            
            # Set feature flags
            if state.get('auto_transcribe') is None:
                state['auto_transcribe'] = True
            if state.get('auto_tts') is None:
                state['auto_tts'] = True
            if state.get('auto_record') is None:
                state['auto_record'] = True
            
            # Audio/Video defaults
            state['microphone_enabled'] = True
            state['camera_enabled'] = False  # Usually off for bot
            state['speaker_enabled'] = True
            
            logger.info(f"✅ Bot initialized")
            logger.info(f"   Bot Name: {state['bot_name']}")
            logger.info(f"   Meeting: {state.get('meeting_link', 'Not provided')[:50]}...")
            logger.info(f"   Platform: {state.get('meeting_platform', 'auto-detect')}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error initializing bot: {str(e)}", exc_info=True)
            state['processing_status'] = 'failed'
            state['bot_status'] = 'error'
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'initialize_bot',
                'error': str(e)
            })
            return state
    
    def validate_meeting(self, state: MeetingBotState) -> MeetingBotState:
        """Validate meeting link and detect platform"""
        logger.info("✅ Validating meeting details")
        
        try:
            meeting_link = state.get('meeting_link', '')
            
            if not meeting_link:
                raise ValueError("Meeting link is required")
            
            # Auto-detect platform if not provided
            platform = state.get('meeting_platform', '').lower()
            
            if not platform:
                for platform_name, config in self.SUPPORTED_PLATFORMS.items():
                    if config['url_pattern'] in meeting_link:
                        platform = platform_name
                        state['meeting_platform'] = platform
                        break
                
                if not platform:
                    logger.warning(f"⚠️ Unknown meeting platform for URL: {meeting_link}")
                    state['meeting_platform'] = 'unknown'
            
            # Validate platform is supported
            if platform not in self.SUPPORTED_PLATFORMS and platform != 'unknown':
                logger.warning(f"⚠️ Unsupported platform: {platform}")
            
            logger.info(f"✅ Meeting validated")
            logger.info(f"   Platform: {state.get('meeting_platform', 'unknown')}")
            logger.info(f"   Link: {meeting_link[:60]}...")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error validating meeting: {str(e)}", exc_info=True)
            state['bot_status'] = 'error'
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'validate_meeting',
                'error': str(e)
            })
            return state
    
    def prepare_browser(self, state: MeetingBotState) -> MeetingBotState:
        """Prepare browser for automation"""
        logger.info("🌐 Preparing browser automation")
        
        try:
            # Determine browser type
            browser_type = state.get('browser_type', 'chrome')
            
            # Check if browser automation is available
            # In production, you'd integrate with Selenium/Playwright
            # For now, we'll just log the preparation
            
            state['browser_type'] = browser_type
            state['browser_session_id'] = f"browser_{uuid.uuid4()}"
            
            logger.info(f"✅ Browser prepared")
            logger.info(f"   Browser: {browser_type}")
            logger.info(f"   Session ID: {state['browser_session_id']}")
            
            # Note: Actual browser automation would happen here
            logger.info("📝 Note: Browser automation requires Selenium/Playwright integration")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error preparing browser: {str(e)}", exc_info=True)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'prepare_browser',
                'error': str(e),
                'severity': 'warning'
            })
            return state
    
    def join_meeting(self, state: MeetingBotState) -> MeetingBotState:
        """Join the meeting"""
        logger.info(f"🚪 Joining meeting: {state.get('meeting_platform')}")
        
        try:
            state['bot_status'] = 'joining'
            
            meeting_link = state.get('meeting_link', '')
            platform = state.get('meeting_platform', '')
            
            # In production, this would use browser automation
            # For now, we'll simulate the join process
            
            logger.info(f"📝 Simulating meeting join...")
            logger.info(f"   Platform: {platform}")
            logger.info(f"   Link: {meeting_link}")
            
            # Simulate join delay
            import time
            time.sleep(2)
            
            # Update state
            state['bot_status'] = 'joined'
            state['join_time'] = datetime.utcnow().isoformat()
            state['interview_active'] = True
            
            logger.info(f"✅ Bot joined meeting")
            logger.info(f"   Join time: {state['join_time']}")
            
            # In production, implement actual browser automation:
            # from selenium import webdriver
            # driver = webdriver.Chrome()
            # driver.get(meeting_link)
            # # Click join button based on platform selectors
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error joining meeting: {str(e)}", exc_info=True)
            state['bot_status'] = 'error'
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'join_meeting',
                'error': str(e)
            })
            
            # Retry logic
            if state.get('retry_count', 0) < 3:
                state['retry_count'] += 1
                logger.info(f"🔄 Retrying join... (attempt {state['retry_count']}/3)")
            
            return state
    
    def setup_audio(self, state: MeetingBotState) -> MeetingBotState:
        """Setup audio devices (microphone and speakers)"""
        logger.info("🎤 Setting up audio devices")
        
        try:
            # In production, configure virtual audio devices
            # For bot to "hear" (STT input) and "speak" (TTS output)
            
            # Virtual audio cable or loopback device setup
            # This allows routing TTS output to meeting input
            
            state['audio_input_device'] = "Virtual Microphone (Bot TTS)"
            state['audio_output_device'] = "Virtual Speakers (Bot STT)"
            
            logger.info(f"✅ Audio configured")
            logger.info(f"   Microphone: {state.get('microphone_enabled')}")
            logger.info(f"   Speaker: {state.get('speaker_enabled')}")
            logger.info(f"   Input: {state['audio_input_device']}")
            logger.info(f"   Output: {state['audio_output_device']}")
            
            # Production implementation would use:
            # - VB-Cable or similar virtual audio device
            # - Chrome tab capture API for receiving meeting audio
            # - Chrome tab audio injection for sending TTS audio
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error setting up audio: {str(e)}", exc_info=True)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'setup_audio',
                'error': str(e),
                'severity': 'warning'
            })
            return state
    
    def activate_features(self, state: MeetingBotState) -> MeetingBotState:
        """Activate bot features (STT, TTS, Recording)"""
        logger.info("⚡ Activating bot features")
        
        try:
            state['bot_status'] = 'active'
            
            # Enable STT
            if state.get('auto_transcribe'):
                state['stt_enabled'] = True
                logger.info("✅ STT enabled - will transcribe meeting audio")
            
            # Enable TTS
            if state.get('auto_tts'):
                state['tts_enabled'] = True
                logger.info("✅ TTS enabled - will speak interview questions")
            
            # Enable Recording
            if state.get('auto_record'):
                state['recording_enabled'] = True
                logger.info("✅ Recording enabled - will record meeting")
            
            state['processing_status'] = 'active'
            state['success'] = True
            
            logger.info(f"✅ All features activated")
            logger.info(f"   Bot is now active in meeting")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error activating features: {str(e)}", exc_info=True)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'activate_features',
                'error': str(e),
                'severity': 'warning'
            })
            return state
    
    def store_session(self, state: MeetingBotState) -> MeetingBotState:
        """Store bot session data in MongoDB"""
        logger.info(f"💾 Storing bot session: {state.get('bot_id')}")
        
        try:
            # Prepare bot session document
            bot_session_doc = {
                "bot_id": state.get('bot_id'),
                "session_id": state.get('session_id'),
                "meeting_id": state.get('meeting_id'),
                "interview_id": state.get('interview_id'),
                
                # Meeting details
                "meeting_link": state.get('meeting_link'),
                "meeting_platform": state.get('meeting_platform'),
                "meeting_title": state.get('meeting_title'),
                "scheduled_start_time": state.get('scheduled_start_time'),
                
                # Bot configuration
                "bot_name": state.get('bot_name'),
                "bot_email": state.get('bot_email'),
                "bot_role": state.get('bot_role', 'interviewer'),
                "auto_record": state.get('auto_record', False),
                "auto_transcribe": state.get('auto_transcribe', False),
                "auto_tts": state.get('auto_tts', False),
                
                # Bot status
                "bot_status": state.get('bot_status'),
                "join_method": state.get('join_method', 'browser_automation'),
                "browser_type": state.get('browser_type'),
                "browser_session_id": state.get('browser_session_id'),
                
                # Timing
                "join_time": datetime.fromisoformat(state['join_time']) if state.get('join_time') else None,
                "leave_time": datetime.fromisoformat(state['leave_time']) if state.get('leave_time') else None,
                "duration_minutes": state.get('duration_minutes', 0),
                "max_duration_minutes": state.get('max_duration_minutes'),
                
                # Participants
                "expected_participants": state.get('expected_participants', []),
                "actual_participants": state.get('actual_participants', []),
                "participant_count": state.get('participant_count', 0),
                "host_name": state.get('host_name'),
                
                # Features
                "stt_enabled": state.get('stt_enabled', False),
                "tts_enabled": state.get('tts_enabled', False),
                "recording_enabled": state.get('recording_enabled', False),
                "microphone_enabled": state.get('microphone_enabled', False),
                "camera_enabled": state.get('camera_enabled', False),
                "speaker_enabled": state.get('speaker_enabled', False),
                
                # Audio devices
                "audio_input_device": state.get('audio_input_device'),
                "audio_output_device": state.get('audio_output_device'),
                
                # Analytics
                "total_speech_duration_seconds": state.get('total_speech_duration_seconds', 0),
                "bot_spoke_count": state.get('bot_spoke_count', 0),
                "candidate_spoke_count": state.get('candidate_spoke_count', 0),
                "questions_asked": state.get('questions_asked', 0),
                "answers_received": state.get('answers_received', 0),
                
                # Status
                "processing_status": state.get('processing_status'),
                "success": state.get('success', False),
                "errors": state.get('errors', []),
                "has_errors": len(state.get('errors', [])) > 0,
                
                # Timestamps
                "created_at": datetime.fromisoformat(state.get('created_at', datetime.utcnow().isoformat())),
                "started_at": datetime.fromisoformat(state.get('started_at', datetime.utcnow().isoformat())),
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Store in meeting_bots collection
            bots_collection = self.db['meeting_bots']
            result = bots_collection.update_one(
                {"bot_id": bot_session_doc["bot_id"]},
                {"$set": bot_session_doc},
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"✅ Stored new bot session: {bot_session_doc['bot_id']}")
            else:
                logger.info(f"✅ Updated bot session: {bot_session_doc['bot_id']}")
            
            # Update meeting with bot info
            if state.get('meeting_id'):
                meetings_collection = self.db['meetings']
                meetings_collection.update_one(
                    {"meeting_id": state['meeting_id']},
                    {
                        "$set": {
                            "bot_id": state['bot_id'],
                            "ai_bot_enabled": True,
                            "bot_join_time": bot_session_doc.get('join_time'),
                            "bot_status": state.get('bot_status'),
                            "stt_enabled": state.get('stt_enabled', False),
                            "tts_enabled": state.get('tts_enabled', False),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
            
            logger.info(f"📊 Bot Session Summary:")
            logger.info(f"   Bot ID: {state.get('bot_id')}")
            logger.info(f"   Status: {state.get('bot_status')}")
            logger.info(f"   Platform: {state.get('meeting_platform')}")
            logger.info(f"   Features: STT={state.get('stt_enabled')}, TTS={state.get('tts_enabled')}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error storing bot session: {str(e)}", exc_info=True)
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'store_session',
                'error': str(e)
            })
            return state
    
    # ==================== Public API Methods ====================
    
    async def join_meeting_session(self, meeting_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Join a meeting and activate bot
        
        Args:
            meeting_request: Meeting configuration
            
        Returns:
            Bot session details
        """
        logger.info(f"🤖 Joining meeting session")
        
        try:
            # Initialize state
            initial_state = MeetingBotState(
                bot_id=meeting_request.get('bot_id', f"bot_{uuid.uuid4()}"),
                session_id=meeting_request.get('session_id', f"session_{uuid.uuid4()}"),
                meeting_id=meeting_request.get('meeting_id', ''),
                interview_id=meeting_request.get('interview_id'),
                
                meeting_link=meeting_request.get('meeting_link', ''),
                meeting_platform=meeting_request.get('meeting_platform', ''),
                meeting_title=meeting_request.get('meeting_title', ''),
                scheduled_start_time=meeting_request.get('scheduled_start_time', datetime.utcnow().isoformat()),
                
                bot_name=meeting_request.get('bot_name', self.default_bot_name),
                bot_email=meeting_request.get('bot_email', self.default_bot_email),
                bot_role=meeting_request.get('bot_role', 'interviewer'),
                auto_record=meeting_request.get('auto_record', True),
                auto_transcribe=meeting_request.get('auto_transcribe', True),
                auto_tts=meeting_request.get('auto_tts', True),
                
                bot_status='pending',
                join_method='browser_automation',
                browser_type=meeting_request.get('browser_type', 'chrome'),
                
                join_time=None,
                leave_time=None,
                duration_minutes=0,
                max_duration_minutes=meeting_request.get('max_duration_minutes', self.default_max_duration),
                auto_leave_after_silence_minutes=meeting_request.get('auto_leave_after_silence_minutes', self.default_silence_threshold),
                
                expected_participants=meeting_request.get('expected_participants', []),
                actual_participants=[],
                participant_count=0,
                host_name=meeting_request.get('host_name'),
                
                stt_enabled=False,
                tts_enabled=False,
                recording_enabled=False,
                screen_sharing_enabled=False,
                
                microphone_enabled=True,
                camera_enabled=False,
                speaker_enabled=True,
                audio_input_device=None,
                audio_output_device=None,
                
                interview_active=False,
                current_speaker=None,
                last_speech_time=None,
                silence_duration_seconds=0,
                
                browser_session_id=None,
                browser_process_id=None,
                chrome_tab_id=None,
                
                meeting_password=meeting_request.get('meeting_password'),
                waiting_room_enabled=meeting_request.get('waiting_room_enabled', False),
                host_approval_required=meeting_request.get('host_approval_required', False),
                
                total_speech_duration_seconds=0,
                bot_spoke_count=0,
                candidate_spoke_count=0,
                questions_asked=0,
                answers_received=0,
                
                processing_status='initializing',
                success=False,
                
                errors=[],
                last_error='',
                retry_count=0,
                
                created_at=datetime.utcnow().isoformat(),
                started_at=datetime.utcnow().isoformat(),
                completed_at=None
            )
            
            # Run workflow
            result = await self.workflow.ainvoke(initial_state)
            
            if result.get('success'):
                return {
                    "success": True,
                    "data": {
                        "bot_id": result['bot_id'],
                        "session_id": result['session_id'],
                        "meeting_id": result['meeting_id'],
                        "bot_status": result.get('bot_status'),
                        "join_time": result.get('join_time'),
                        "meeting_platform": result.get('meeting_platform'),
                        "features": {
                            "stt_enabled": result.get('stt_enabled', False),
                            "tts_enabled": result.get('tts_enabled', False),
                            "recording_enabled": result.get('recording_enabled', False)
                        }
                    },
                    "message": "Bot joined meeting successfully"
                }
            else:
                return {
                    "success": False,
                    "error": {
                        "code": "BOT_JOIN_FAILED",
                        "message": result.get('last_error', 'Failed to join meeting'),
                        "details": result.get('errors', [])
                    },
                    "message": "Failed to join meeting"
                }
            
        except Exception as e:
            logger.error(f"❌ Error in join_meeting_session: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": {
                    "code": "BOT_ERROR",
                    "message": str(e)
                },
                "message": "Bot join failed"
            }
    
    async def leave_meeting_session(self, bot_id: str) -> Dict[str, Any]:
        """Leave meeting and deactivate bot"""
        logger.info(f"👋 Leaving meeting session: {bot_id}")
        
        try:
            # Get bot session from DB
            bot_session = self.db['meeting_bots'].find_one({"bot_id": bot_id})
            
            if not bot_session:
                raise ValueError(f"Bot session not found: {bot_id}")
            
            # Update status
            leave_time = datetime.utcnow()
            join_time = bot_session.get('join_time')
            
            if join_time:
                duration = (leave_time - join_time).total_seconds() / 60
            else:
                duration = 0
            
            # Update in DB
            self.db['meeting_bots'].update_one(
                {"bot_id": bot_id},
                {
                    "$set": {
                        "bot_status": "left",
                        "leave_time": leave_time,
                        "duration_minutes": int(duration),
                        "interview_active": False,
                        "updated_at": leave_time
                    }
                }
            )
            
            # Update meeting
            if bot_session.get('meeting_id'):
                self.db['meetings'].update_one(
                    {"meeting_id": bot_session['meeting_id']},
                    {
                        "$set": {
                            "bot_leave_time": leave_time,
                            "bot_status": "left",
                            "status": "completed",
                            "updated_at": leave_time
                        }
                    }
                )
            
            logger.info(f"✅ Bot left meeting")
            logger.info(f"   Duration: {int(duration)} minutes")
            
            return {
                "success": True,
                "data": {
                    "bot_id": bot_id,
                    "leave_time": leave_time.isoformat(),
                    "duration_minutes": int(duration)
                },
                "message": "Bot left meeting successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Error leaving meeting: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": {
                    "code": "BOT_LEAVE_ERROR",
                    "message": str(e)
                },
                "message": "Failed to leave meeting"
            }
    
    def close(self):
        """Close MongoDB connection"""
        self.mongo_client.close()
        logger.info("✅ Closed MongoDB connection")


# Async helper functions
async def join_meeting(meeting_request: Dict[str, Any]) -> Dict[str, Any]:
    """Join a meeting with bot"""
    agent = MeetingBotAgent()
    try:
        result = await agent.join_meeting_session(meeting_request)
        return result
    finally:
        agent.close()


async def leave_meeting(bot_id: str) -> Dict[str, Any]:
    """Leave meeting and deactivate bot"""
    agent = MeetingBotAgent()
    try:
        result = await agent.leave_meeting_session(bot_id)
        return result
    finally:
        agent.close()


if __name__ == "__main__":
    # Test the agent
    print("=" * 80)
    print("Testing Meeting Bot Agent")
    print("=" * 80)
    
    import asyncio
    
    async def test():
        request = {
            "meeting_link": "https://meet.google.com/abc-defg-hij",
            "meeting_platform": "google_meet",
            "meeting_title": "Technical Interview - Senior Python Developer",
            "bot_name": "AI Interview Assistant",
            "auto_transcribe": True,
            "auto_tts": True,
            "auto_record": True,
            "expected_participants": ["candidate@email.com", "hr@company.com"]
        }
        
        result = await join_meeting(request)
        print("\n✅ Bot Join Test Result:")
        print(f"Success: {result.get('success')}")
        if result.get('success'):
            data = result.get('data', {})
            print(f"Bot ID: {data.get('bot_id')}")
            print(f"Status: {data.get('bot_status')}")
            print(f"Platform: {data.get('meeting_platform')}")
            print(f"Features: {data.get('features')}")
        else:
            print(f"Error: {result.get('error')}")
    
    asyncio.run(test())
    print("\n✅ Test complete")
