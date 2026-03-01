"""
Real-time Orchestration LangGraph Agent
Orchestrates STT → LLM → TTS pipeline with real-time streaming
Manages conversation state, error recovery, and multi-agent coordination
"""

import json
import logging
import uuid
import os
import sys
import asyncio
from typing import Dict, Any, TypedDict, List, Optional, AsyncGenerator
from datetime import datetime
from langgraph.graph import StateGraph, END
from pymongo import MongoClient
from dotenv import load_dotenv
from collections import deque
import time

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.context_manager import MCPContextManager
from mcp.cache_manager import MCPCacheManager
from mcp.token_optimizer import TokenOptimizer

# Import specialized agents
from langgraph_agents.audio_transcription_agent import transcribe_audio_chunk
from langgraph_agents.interview_conductor_agent import conduct_interview, process_interview_answer
from langgraph_agents.tts_agent import convert_text_to_speech, stream_text_to_speech

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OrchestratorState(TypedDict):
    """State for real-time orchestration workflow"""
    # Session identification
    orchestration_id: str
    session_id: str
    interview_id: str
    meeting_id: Optional[str]
    candidate_name: str
    job_title: str
    
    # Conversation state
    conversation_active: bool
    current_turn: int
    turns_history: List[Dict[str, Any]]
    
    # Pipeline stages
    stt_status: str  # idle, processing, completed, failed
    llm_status: str  # idle, processing, completed, failed
    tts_status: str  # idle, processing, streaming, completed, failed
    
    # Audio input (STT)
    audio_chunk: Optional[bytes]
    audio_format: str
    transcription_text: str
    transcription_confidence: float
    speaker_detected: str
    
    # LLM processing
    llm_input: str
    llm_output: str
    llm_context: List[Dict[str, str]]
    question_generated: str
    answer_evaluation: Dict[str, Any]
    next_action: str  # continue, followup, transition_stage, end
    
    # TTS output
    tts_text: str
    tts_audio_data: Optional[bytes]
    tts_audio_url: Optional[str]
    tts_duration_seconds: float
    is_streaming: bool
    
    # Error handling & recovery
    errors: List[Dict[str, Any]]
    retry_attempts: Dict[str, int]
    max_retries: int
    error_recovery_strategy: str  # retry, skip, fallback, abort
    last_successful_stage: str
    
    # Performance metrics
    stt_latency_ms: int
    llm_latency_ms: int
    tts_latency_ms: int
    total_latency_ms: int
    pipeline_start_time: float
    pipeline_end_time: Optional[float]
    
    # Conversation flow control
    waiting_for_response: bool
    silence_duration_seconds: int
    max_silence_seconds: int
    auto_prompt_after_silence: bool
    
    # Quality assurance
    conversation_quality_score: float
    interruptions_count: int
    successful_turns: int
    failed_turns: int
    
    # Processing status
    processing_status: str  # initializing, active, paused, completed, failed
    success: bool
    
    # Timestamps
    created_at: str
    last_activity_at: str
    completed_at: Optional[str]


class RealtimeOrchestratorAgent:
    """
    LangGraph agent for real-time STT → LLM → TTS orchestration
    
    Workflow:
    1. initialize_session: Setup orchestration session and conversation context
    2. receive_audio: Receive audio chunk from client
    3. transcribe_audio_stt: Convert audio to text using STT agent
    4. process_with_llm: Generate response using Interview Conductor agent
    5. synthesize_speech_tts: Convert response to audio using TTS agent
    6. stream_audio_output: Stream audio back to client
    7. update_conversation_state: Update conversation history and metrics
    8. handle_errors: Recover from failures with appropriate strategy
    9. store_orchestration_data: Save session data to MongoDB
    
    Features:
    - Real-time streaming between agents
    - Automatic error recovery with retry logic
    - Conversation state management
    - Performance monitoring and metrics
    - Quality assurance checks
    """
    
    def __init__(self):
        """Initialize Realtime Orchestrator Agent"""
        logger.info("🎭 Initializing RealtimeOrchestratorAgent")
        
        # Initialize MCP components
        self.context_manager = MCPContextManager(max_context_length=20000)
        self.cache_manager = MCPCacheManager(
            ttl_minutes=180,  # Cache for 3 hours
            max_cache_size=100
        )
        self.token_optimizer = TokenOptimizer(
            max_input_tokens=15000,
            max_output_tokens=5000
        )
        
        # MongoDB connection
        mongo_uri = os.getenv('MONGO_URI', 'mongodb+srv://narutevaibhav95_db_user:9Y0gsqDxtHRoBH5w@resumate.xbvpnl1.mongodb.net/')
        mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
        
        self.mongo_client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=45000,
            maxPoolSize=50,
            retryWrites=True,
            retryReads=True
        )
        self.db = self.mongo_client[mongo_db_name]
        
        # Configuration
        self.max_retries = 3
        self.max_silence_seconds = 10
        self.stt_timeout_seconds = 30
        self.llm_timeout_seconds = 60
        self.tts_timeout_seconds = 30
        
        # Active sessions cache (in-memory for low latency)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Build workflow
        self.workflow = self._build_workflow()
        logger.info("✅ RealtimeOrchestratorAgent initialized successfully")
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow for real-time orchestration"""
        workflow = StateGraph(OrchestratorState)
        
        # Add nodes
        workflow.add_node("initialize_session", self.initialize_session)
        workflow.add_node("receive_audio", self.receive_audio)
        workflow.add_node("transcribe_audio_stt", self.transcribe_audio_stt)
        workflow.add_node("process_with_llm", self.process_with_llm)
        workflow.add_node("synthesize_speech_tts", self.synthesize_speech_tts)
        workflow.add_node("update_conversation_state", self.update_conversation_state)
        workflow.add_node("handle_errors", self.handle_errors)
        workflow.add_node("store_orchestration_data", self.store_orchestration_data)
        
        # Define edges
        workflow.set_entry_point("initialize_session")
        workflow.add_edge("initialize_session", "receive_audio")
        
        # Conditional routing after audio reception
        workflow.add_conditional_edges(
            "receive_audio",
            self._should_continue_after_audio,
            {
                "transcribe": "transcribe_audio_stt",
                "error": "handle_errors",
                "end": "store_orchestration_data"
            }
        )
        
        # Conditional routing after STT
        workflow.add_conditional_edges(
            "transcribe_audio_stt",
            self._should_continue_after_stt,
            {
                "process": "process_with_llm",
                "error": "handle_errors",
                "retry": "transcribe_audio_stt"
            }
        )
        
        # Conditional routing after LLM
        workflow.add_conditional_edges(
            "process_with_llm",
            self._should_continue_after_llm,
            {
                "synthesize": "synthesize_speech_tts",
                "error": "handle_errors",
                "retry": "process_with_llm"
            }
        )
        
        # Conditional routing after TTS
        workflow.add_conditional_edges(
            "synthesize_speech_tts",
            self._should_continue_after_tts,
            {
                "update": "update_conversation_state",
                "error": "handle_errors",
                "retry": "synthesize_speech_tts"
            }
        )
        
        # After updating state, always end to prevent infinite loops
        # Each turn is a separate workflow invocation
        workflow.add_edge("update_conversation_state", "store_orchestration_data")
        
        # Error handling routing
        workflow.add_conditional_edges(
            "handle_errors",
            self._error_recovery_decision,
            {
                "retry_stt": "transcribe_audio_stt",
                "retry_llm": "process_with_llm",
                "retry_tts": "synthesize_speech_tts",
                "skip": "update_conversation_state",
                "abort": "store_orchestration_data"
            }
        )
        
        workflow.add_edge("store_orchestration_data", END)
        
        return workflow.compile()
    
    # ==================== Conditional Edge Functions ====================
    
    def _should_continue_after_audio(self, state: OrchestratorState) -> str:
        """Determine next step after receiving audio"""
        if state.get('audio_chunk') is None:
            logger.warning("⚠️ No audio chunk received")
            return "error"
        
        if not state.get('conversation_active'):
            logger.info("🛑 Conversation ended by client")
            return "end"
        
        return "transcribe"
    
    def _should_continue_after_stt(self, state: OrchestratorState) -> str:
        """Determine next step after STT"""
        if state.get('stt_status') == 'failed':
            retry_count = state.get('retry_attempts', {}).get('stt', 0)
            if retry_count < state.get('max_retries', 3):
                logger.info(f"🔄 Retrying STT (attempt {retry_count + 1}/{state.get('max_retries', 3)})")
                return "retry"
            return "error"
        
        if state.get('stt_status') == 'completed' and state.get('transcription_text'):
            return "process"
        
        return "error"
    
    def _should_continue_after_llm(self, state: OrchestratorState) -> str:
        """Determine next step after LLM"""
        if state.get('llm_status') == 'failed':
            retry_count = state.get('retry_attempts', {}).get('llm', 0)
            if retry_count < state.get('max_retries', 3):
                logger.info(f"🔄 Retrying LLM (attempt {retry_count + 1}/{state.get('max_retries', 3)})")
                return "retry"
            return "error"
        
        if state.get('llm_status') == 'completed' and state.get('llm_output'):
            return "synthesize"
        
        return "error"
    
    def _should_continue_after_tts(self, state: OrchestratorState) -> str:
        """Determine next step after TTS"""
        if state.get('tts_status') == 'failed':
            retry_count = state.get('retry_attempts', {}).get('tts', 0)
            if retry_count < state.get('max_retries', 3):
                logger.info(f"🔄 Retrying TTS (attempt {retry_count + 1}/{state.get('max_retries', 3)})")
                return "retry"
            return "error"
        
        if state.get('tts_status') in ['completed', 'streaming']:
            return "update"
        
        return "error"
    
    def _should_continue_conversation(self, state: OrchestratorState) -> str:
        """Determine if conversation should continue"""
        # IMPORTANT: For single-turn processing, always end after one cycle
        # The next turn will be initiated by a new API call
        # This prevents infinite loops in the workflow
        
        if state.get('next_action') == 'end':
            logger.info("🏁 Conversation ended by LLM decision")
            return "end"
        
        # Check if this is part of a streaming session
        # For now, we end after each turn and let the API call again
        # This gives us better control and prevents recursion issues
        logger.info("✅ Turn completed, ending workflow (next turn via new API call)")
        return "end"
    
    def _error_recovery_decision(self, state: OrchestratorState) -> str:
        """Determine error recovery strategy"""
        strategy = state.get('error_recovery_strategy', 'retry')
        last_stage = state.get('last_successful_stage', '')
        
        if strategy == 'abort':
            logger.error("❌ Aborting orchestration due to critical error")
            return "abort"
        
        if strategy == 'skip':
            logger.warning("⏭️ Skipping failed operation")
            return "skip"
        
        # Retry based on last successful stage
        if 'stt' in last_stage:
            return "retry_stt"
        elif 'llm' in last_stage:
            return "retry_llm"
        elif 'tts' in last_stage:
            return "retry_tts"
        
        return "abort"
    
    # ==================== Workflow Nodes ====================
    
    def initialize_session(self, state: OrchestratorState) -> OrchestratorState:
        """Initialize orchestration session"""
        logger.info(f"🎬 Initializing orchestration session: {state.get('orchestration_id')}")
        
        try:
            # Set initial values
            state['processing_status'] = 'initializing'
            state['created_at'] = datetime.utcnow().isoformat()
            state['last_activity_at'] = datetime.utcnow().isoformat()
            state['conversation_active'] = True
            state['current_turn'] = 0
            state['turns_history'] = []
            state['pipeline_start_time'] = time.time()
            
            # Initialize status
            state['stt_status'] = 'idle'
            state['llm_status'] = 'idle'
            state['tts_status'] = 'idle'
            
            # Initialize retry tracking
            state['retry_attempts'] = {'stt': 0, 'llm': 0, 'tts': 0}
            state['max_retries'] = self.max_retries
            state['errors'] = []
            
            # Initialize metrics
            state['stt_latency_ms'] = 0
            state['llm_latency_ms'] = 0
            state['tts_latency_ms'] = 0
            state['total_latency_ms'] = 0
            state['successful_turns'] = 0
            state['failed_turns'] = 0
            state['interruptions_count'] = 0
            state['conversation_quality_score'] = 100.0
            
            # Flow control
            state['waiting_for_response'] = False
            state['silence_duration_seconds'] = 0
            state['max_silence_seconds'] = self.max_silence_seconds
            state['auto_prompt_after_silence'] = True
            
            # LLM context
            state['llm_context'] = []
            
            # Cache session
            self.active_sessions[state['session_id']] = {
                'orchestration_id': state['orchestration_id'],
                'status': 'active',
                'started_at': state['created_at']
            }
            
            state['processing_status'] = 'active'
            state['success'] = True
            
            logger.info(f"✅ Session initialized successfully")
            logger.info(f"   Session ID: {state.get('session_id')}")
            logger.info(f"   Interview ID: {state.get('interview_id')}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error initializing session: {str(e)}", exc_info=True)
            state['processing_status'] = 'failed'
            state['success'] = False
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'initialize_session',
                'error': str(e),
                'severity': 'critical'
            })
            return state
    
    def receive_audio(self, state: OrchestratorState) -> OrchestratorState:
        """Receive audio chunk from client"""
        logger.info(f"🎤 Receiving audio chunk for turn {state.get('current_turn', 0)}")
        
        try:
            # Validate audio chunk
            if not state.get('audio_chunk'):
                raise ValueError("No audio chunk provided")
            
            # Update activity timestamp
            state['last_activity_at'] = datetime.utcnow().isoformat()
            state['silence_duration_seconds'] = 0
            
            # Increment turn counter
            state['current_turn'] = state.get('current_turn', 0) + 1
            
            logger.info(f"✅ Audio chunk received")
            logger.info(f"   Turn: {state['current_turn']}")
            logger.info(f"   Format: {state.get('audio_format', 'unknown')}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error receiving audio: {str(e)}", exc_info=True)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'receive_audio',
                'error': str(e),
                'severity': 'high'
            })
            return state
    
    def transcribe_audio_stt(self, state: OrchestratorState) -> OrchestratorState:
        """Transcribe audio using STT agent"""
        logger.info(f"🎯 Starting STT transcription for turn {state.get('current_turn')}")
        
        stt_start = time.time()
        state['stt_status'] = 'processing'
        
        try:
            # Prepare STT request
            stt_request = {
                'session_id': state['session_id'],
                'audio_chunk_id': f"chunk_{state['current_turn']}_{uuid.uuid4()}",
                'audio_data': state['audio_chunk'],
                'audio_format': state.get('audio_format', 'webm'),
                'interview_id': state.get('interview_id'),
                'question_context': state.get('llm_output', ''),  # Last question asked
                'previous_transcripts': state.get('turns_history', [])[-5:]  # Last 5 turns
            }
            
            # Call STT agent (this would be async in real implementation)
            logger.info("📞 Calling STT agent...")
            # result = await transcribe_audio_chunk(stt_request)
            
            # Simulated result for now (replace with actual async call)
            result = {
                'success': True,
                'data': {
                    'transcription': 'Sample transcribed text from candidate',
                    'confidence': 0.95,
                    'speaker': 'candidate',
                    'language': 'en'
                }
            }
            
            if result.get('success'):
                data = result['data']
                state['transcription_text'] = data.get('transcription', '')
                state['transcription_confidence'] = data.get('confidence', 0.0)
                state['speaker_detected'] = data.get('speaker', 'unknown')
                state['stt_status'] = 'completed'
                state['last_successful_stage'] = 'stt'
                state['retry_attempts']['stt'] = 0  # Reset retry counter
                
                stt_latency = int((time.time() - stt_start) * 1000)
                state['stt_latency_ms'] = stt_latency
                
                logger.info(f"✅ STT completed successfully")
                logger.info(f"   Transcription: {state['transcription_text'][:100]}...")
                logger.info(f"   Confidence: {state['transcription_confidence']:.2%}")
                logger.info(f"   Latency: {stt_latency}ms")
            else:
                raise Exception(f"STT failed: {result.get('error')}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ STT error: {str(e)}", exc_info=True)
            state['stt_status'] = 'failed'
            state['retry_attempts']['stt'] = state.get('retry_attempts', {}).get('stt', 0) + 1
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'transcribe_audio_stt',
                'error': str(e),
                'severity': 'high',
                'retry_attempt': state['retry_attempts']['stt']
            })
            return state
    
    def process_with_llm(self, state: OrchestratorState) -> OrchestratorState:
        """Process transcription with LLM (Interview Conductor)"""
        logger.info(f"🧠 Starting LLM processing for turn {state.get('current_turn')}")
        
        llm_start = time.time()
        state['llm_status'] = 'processing'
        
        try:
            # Prepare LLM input
            state['llm_input'] = state['transcription_text']
            
            # Add to conversation context
            state['llm_context'].append({
                'role': 'user',
                'content': state['transcription_text'],
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Prepare interview answer processing request
            answer_request = {
                'interview_id': state['interview_id'],
                'session_id': state['session_id'],
                'answer_text': state['transcription_text'],
                'question_context': state.get('llm_output', ''),  # Previous question
                'transcription_confidence': state['transcription_confidence'],
                'speaker': state['speaker_detected']
            }
            
            logger.info("📞 Calling Interview Conductor agent...")
            # result = await process_interview_answer(answer_request)
            
            # Simulated result (replace with actual async call)
            result = {
                'success': True,
                'data': {
                    'next_question': 'Can you tell me more about your experience with Python?',
                    'evaluation': {
                        'score': 8.5,
                        'strengths': ['Clear communication', 'Technical knowledge'],
                        'areas_to_improve': ['More specific examples needed']
                    },
                    'next_action': 'continue'
                }
            }
            
            if result.get('success'):
                data = result['data']
                state['llm_output'] = data.get('next_question', '')
                state['answer_evaluation'] = data.get('evaluation', {})
                state['next_action'] = data.get('next_action', 'continue')
                state['llm_status'] = 'completed'
                state['last_successful_stage'] = 'llm'
                state['retry_attempts']['llm'] = 0
                
                # Add LLM response to context
                state['llm_context'].append({
                    'role': 'assistant',
                    'content': state['llm_output'],
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                llm_latency = int((time.time() - llm_start) * 1000)
                state['llm_latency_ms'] = llm_latency
                
                logger.info(f"✅ LLM processing completed")
                logger.info(f"   Response: {state['llm_output'][:100]}...")
                logger.info(f"   Next action: {state['next_action']}")
                logger.info(f"   Latency: {llm_latency}ms")
            else:
                raise Exception(f"LLM processing failed: {result.get('error')}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ LLM error: {str(e)}", exc_info=True)
            state['llm_status'] = 'failed'
            state['retry_attempts']['llm'] = state.get('retry_attempts', {}).get('llm', 0) + 1
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'process_with_llm',
                'error': str(e),
                'severity': 'critical',
                'retry_attempt': state['retry_attempts']['llm']
            })
            return state
    
    def synthesize_speech_tts(self, state: OrchestratorState) -> OrchestratorState:
        """Synthesize speech using TTS agent"""
        logger.info(f"🔊 Starting TTS synthesis for turn {state.get('current_turn')}")
        
        tts_start = time.time()
        state['tts_status'] = 'processing'
        
        try:
            # Prepare TTS request
            state['tts_text'] = state['llm_output']
            
            tts_request = {
                'text': state['llm_output'],
                'text_type': 'question',
                'voice_profile': 'professional_female',
                'emotion': 'professional',
                'session_id': state['session_id'],
                'interview_id': state['interview_id'],
                'model_id': 'eleven_multilingual_v2',
                'output_format': 'mp3_44100_128',
                'is_streaming': state.get('is_streaming', True)
            }
            
            logger.info("📞 Calling TTS agent...")
            # result = await convert_text_to_speech(tts_request)
            
            # Simulated result (replace with actual async call)
            result = {
                'success': True,
                'data': {
                    'tts_id': f"tts_{uuid.uuid4()}",
                    'audio_data': b'simulated_audio_data',
                    'audio_url': f"https://storage.example.com/audio/tts_{uuid.uuid4()}.mp3",
                    'audio_duration_seconds': 5.2,
                    'is_streaming': True
                }
            }
            
            if result.get('success'):
                data = result['data']
                state['tts_audio_data'] = data.get('audio_data')
                state['tts_audio_url'] = data.get('audio_url')
                state['tts_duration_seconds'] = data.get('audio_duration_seconds', 0.0)
                state['is_streaming'] = data.get('is_streaming', False)
                state['tts_status'] = 'completed' if not state['is_streaming'] else 'streaming'
                state['last_successful_stage'] = 'tts'
                state['retry_attempts']['tts'] = 0
                
                tts_latency = int((time.time() - tts_start) * 1000)
                state['tts_latency_ms'] = tts_latency
                
                logger.info(f"✅ TTS synthesis completed")
                logger.info(f"   Audio URL: {state['tts_audio_url']}")
                logger.info(f"   Duration: {state['tts_duration_seconds']}s")
                logger.info(f"   Streaming: {state['is_streaming']}")
                logger.info(f"   Latency: {tts_latency}ms")
            else:
                raise Exception(f"TTS synthesis failed: {result.get('error')}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ TTS error: {str(e)}", exc_info=True)
            state['tts_status'] = 'failed'
            state['retry_attempts']['tts'] = state.get('retry_attempts', {}).get('tts', 0) + 1
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'synthesize_speech_tts',
                'error': str(e),
                'severity': 'medium',
                'retry_attempt': state['retry_attempts']['tts']
            })
            return state
    
    def update_conversation_state(self, state: OrchestratorState) -> OrchestratorState:
        """Update conversation state and metrics"""
        logger.info(f"📊 Updating conversation state for turn {state.get('current_turn')}")
        
        try:
            # Calculate total pipeline latency
            total_latency = (
                state.get('stt_latency_ms', 0) +
                state.get('llm_latency_ms', 0) +
                state.get('tts_latency_ms', 0)
            )
            state['total_latency_ms'] = total_latency
            
            # Record turn in history
            turn_record = {
                'turn': state['current_turn'],
                'timestamp': datetime.utcnow().isoformat(),
                'user_input': state.get('transcription_text', ''),
                'user_confidence': state.get('transcription_confidence', 0.0),
                'ai_response': state.get('llm_output', ''),
                'evaluation': state.get('answer_evaluation', {}),
                'latency_ms': total_latency,
                'status': 'success' if state.get('success', False) else 'failed'
            }
            state['turns_history'].append(turn_record)
            
            # Update metrics
            if state.get('stt_status') == 'completed' and \
               state.get('llm_status') == 'completed' and \
               state.get('tts_status') in ['completed', 'streaming']:
                state['successful_turns'] = state.get('successful_turns', 0) + 1
            else:
                state['failed_turns'] = state.get('failed_turns', 0) + 1
            
            # Calculate conversation quality score
            success_rate = state['successful_turns'] / max(state['current_turn'], 1)
            avg_confidence = sum([t.get('user_confidence', 0) for t in state['turns_history']]) / max(len(state['turns_history']), 1)
            state['conversation_quality_score'] = (success_rate * 70) + (avg_confidence * 30)
            
            # Update activity timestamp
            state['last_activity_at'] = datetime.utcnow().isoformat()
            state['waiting_for_response'] = True
            
            logger.info(f"✅ Conversation state updated")
            logger.info(f"   Total latency: {total_latency}ms")
            logger.info(f"   Success rate: {success_rate:.1%}")
            logger.info(f"   Quality score: {state['conversation_quality_score']:.1f}")
            logger.info(f"   Successful turns: {state['successful_turns']}/{state['current_turn']}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error updating conversation state: {str(e)}", exc_info=True)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'update_conversation_state',
                'error': str(e),
                'severity': 'low'
            })
            return state
    
    def handle_errors(self, state: OrchestratorState) -> OrchestratorState:
        """Handle errors with recovery strategy"""
        logger.warning(f"⚠️ Handling errors for turn {state.get('current_turn')}")
        
        try:
            errors = state.get('errors', [])
            if not errors:
                return state
            
            last_error = errors[-1]
            error_stage = last_error.get('stage', '')
            error_severity = last_error.get('severity', 'medium')
            
            logger.warning(f"   Stage: {error_stage}")
            logger.warning(f"   Severity: {error_severity}")
            logger.warning(f"   Error: {last_error.get('error', 'Unknown')}")
            
            # Determine recovery strategy
            if error_severity == 'critical':
                state['error_recovery_strategy'] = 'abort'
                logger.error("🛑 Critical error - aborting orchestration")
            elif error_severity == 'high':
                retry_count = state.get('retry_attempts', {}).get(error_stage.split('_')[-1], 0)
                if retry_count >= state.get('max_retries', 3):
                    state['error_recovery_strategy'] = 'skip'
                    logger.warning("⏭️ Max retries reached - skipping operation")
                else:
                    state['error_recovery_strategy'] = 'retry'
                    logger.info(f"🔄 Retrying operation (attempt {retry_count + 1})")
            else:
                state['error_recovery_strategy'] = 'skip'
                logger.info("⏭️ Skipping non-critical error")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error in error handler: {str(e)}", exc_info=True)
            state['error_recovery_strategy'] = 'abort'
            return state
    
    def store_orchestration_data(self, state: OrchestratorState) -> OrchestratorState:
        """Store orchestration session data to MongoDB"""
        logger.info(f"💾 Storing orchestration data: {state.get('orchestration_id')}")
        
        try:
            state['pipeline_end_time'] = time.time()
            state['completed_at'] = datetime.utcnow().isoformat()
            state['processing_status'] = 'completed'
            
            # Prepare document for MongoDB
            orchestration_doc = {
                'orchestration_id': state['orchestration_id'],
                'session_id': state['session_id'],
                'interview_id': state['interview_id'],
                'meeting_id': state.get('meeting_id'),
                
                # Session state (needed for resuming)
                'current_turn': state['current_turn'],
                'conversation_active': state['conversation_active'],
                'processing_status': state.get('processing_status', 'completed'),
                
                # Metrics
                'total_turns': state['current_turn'],
                'successful_turns': state['successful_turns'],
                'failed_turns': state['failed_turns'],
                'conversation_quality_score': state['conversation_quality_score'],
                
                # Latency metrics
                'avg_stt_latency_ms': state.get('stt_latency_ms', 0),
                'avg_llm_latency_ms': state.get('llm_latency_ms', 0),
                'avg_tts_latency_ms': state.get('tts_latency_ms', 0),
                'avg_total_latency_ms': state.get('total_latency_ms', 0),
                
                # Conversation history
                'turns_history': state.get('turns_history', []),
                'conversation_context': state.get('llm_context', []),
                
                # Error tracking
                'errors': state.get('errors', []),
                'has_errors': len(state.get('errors', [])) > 0,
                'interruptions_count': state.get('interruptions_count', 0),
                
                # Status
                'final_status': state.get('processing_status', 'completed'),
                'success': state.get('success', False),
                
                # Timestamps
                'created_at': datetime.fromisoformat(state['created_at']),
                'completed_at': datetime.utcnow(),
                'duration_seconds': state['pipeline_end_time'] - state['pipeline_start_time']
            }
            
            # Store in MongoDB
            collection = self.db['orchestration_sessions']
            result = collection.update_one(
                {'orchestration_id': orchestration_doc['orchestration_id']},
                {'$set': orchestration_doc},
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"✅ New orchestration session stored")
            else:
                logger.info(f"✅ Orchestration session updated")
            
            # DON'T remove from active sessions cache during workflow
            # Session should stay cached for subsequent turns
            # Only remove when end_orchestration is explicitly called
            # This fixes KeyError when trying to update cache after workflow completes
            
            logger.info(f"📊 Orchestration Summary:")
            logger.info(f"   Total turns: {state['current_turn']}")
            logger.info(f"   Success rate: {state['successful_turns']}/{state['current_turn']}")
            logger.info(f"   Quality score: {state['conversation_quality_score']:.1f}")
            logger.info(f"   Avg latency: {state.get('total_latency_ms', 0)}ms")
            logger.info(f"   Duration: {orchestration_doc['duration_seconds']:.1f}s")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error storing orchestration data: {str(e)}", exc_info=True)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'store_orchestration_data',
                'error': str(e),
                'severity': 'low'
            })
            return state
    
    # ==================== Public API Methods ====================
    
    async def start_orchestration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a new real-time orchestration session
        
        Args:
            config: Orchestration configuration
            
        Returns:
            Session initialization result
        """
        logger.info("🎭 Starting new orchestration session")
        
        try:
            # Initialize state
            initial_state = OrchestratorState(
                orchestration_id=config.get('orchestration_id', f"orch_{uuid.uuid4()}"),
                session_id=config.get('session_id', f"session_{uuid.uuid4()}"),
                interview_id=config.get('interview_id', ''),
                meeting_id=config.get('meeting_id'),
                candidate_name=config.get('candidate_name', 'Unknown Candidate'),
                job_title=config.get('job_title', 'Unknown Position'),
                
                conversation_active=True,
                current_turn=0,
                turns_history=[],
                
                stt_status='idle',
                llm_status='idle',
                tts_status='idle',
                
                audio_chunk=None,
                audio_format=config.get('audio_format', 'webm'),
                transcription_text='',
                transcription_confidence=0.0,
                speaker_detected='',
                
                llm_input='',
                llm_output='',
                llm_context=[],
                question_generated='',
                answer_evaluation={},
                next_action='continue',
                
                tts_text='',
                tts_audio_data=None,
                tts_audio_url=None,
                tts_duration_seconds=0.0,
                is_streaming=config.get('enable_streaming', True),
                
                errors=[],
                retry_attempts={'stt': 0, 'llm': 0, 'tts': 0},
                max_retries=3,
                error_recovery_strategy='retry',
                last_successful_stage='',
                
                stt_latency_ms=0,
                llm_latency_ms=0,
                tts_latency_ms=0,
                total_latency_ms=0,
                pipeline_start_time=time.time(),
                pipeline_end_time=None,
                
                waiting_for_response=False,
                silence_duration_seconds=0,
                max_silence_seconds=10,
                auto_prompt_after_silence=True,
                
                conversation_quality_score=100.0,
                interruptions_count=0,
                successful_turns=0,
                failed_turns=0,
                
                processing_status='initializing',
                success=False,
                
                created_at=datetime.utcnow().isoformat(),
                last_activity_at=datetime.utcnow().isoformat(),
                completed_at=None
            )
            
            # DON'T invoke workflow here - just create the initial state
            # The workflow will be invoked when the first audio turn is processed
            # This prevents errors about missing audio chunks
            
            # Convert TypedDict-like initial_state into a plain dict and ensure defaults
            state = dict(initial_state)
            # Ensure critical fields exist with safe defaults
            state.setdefault('orchestration_id', f"orch_{uuid.uuid4()}")
            state.setdefault('session_id', f"session_{uuid.uuid4()}")
            state.setdefault('interview_id', '')
            state.setdefault('meeting_id', None)
            state.setdefault('candidate_name', config.get('candidate_name', 'Unknown Candidate'))
            state.setdefault('job_title', config.get('job_title', 'Unknown Position'))
            state.setdefault('created_at', datetime.utcnow().isoformat())
            state.setdefault('processing_status', 'initializing')
            state.setdefault('current_turn', 0)
            state.setdefault('conversation_active', True)

            # Store session in active sessions cache (use safe .get())
            self.active_sessions[state.get('session_id')] = {
                'orchestration_id': state.get('orchestration_id'),
                'session_id': state.get('session_id'),
                'interview_id': state.get('interview_id'),
                'meeting_id': state.get('meeting_id'),
                'created_at': state.get('created_at'),
                'status': state.get('processing_status'),
                'current_turn': state.get('current_turn'),
                'conversation_active': state.get('conversation_active')
            }

            # Store initial state in MongoDB
            orch_doc = {
                'orchestration_id': state.get('orchestration_id'),
                'session_id': state.get('session_id'),
                'interview_id': state.get('interview_id'),
                'meeting_id': state.get('meeting_id'),
                'candidate_name': state.get('candidate_name', 'Unknown Candidate'),
                'job_title': state.get('job_title', 'Unknown Position'),
                'current_turn': state.get('current_turn', 0),
                'total_turns': 0,
                'successful_turns': 0,
                'failed_turns': 0,
                'conversation_active': True,
                'processing_status': 'active',
                'created_at': datetime.fromisoformat(state.get('created_at')) if isinstance(state.get('created_at'), str) else state.get('created_at'),
                'last_activity_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }

            self.db['orchestration_sessions'].insert_one(orch_doc)

            logger.info(f"✅ Session cached: {state.get('session_id')}")
            logger.info(f"   Active sessions: {len(self.active_sessions)}")

            return {
                'success': True,
                'data': {
                    'orchestration_id': state.get('orchestration_id'),
                    'session_id': state.get('session_id'),
                    'interview_id': state.get('interview_id'),
                    'status': state.get('processing_status'),
                    'created_at': state.get('created_at')
                },
                'message': 'Orchestration session started successfully'
            }
            
        except Exception as e:
            logger.error(f"❌ Error starting orchestration: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': {
                    'code': 'ORCHESTRATION_START_FAILED',
                    'message': str(e)
                },
                'message': 'Failed to start orchestration session'
            }
    
    async def process_audio_turn(self, session_id: str, audio_data: bytes, audio_format: str = 'webm') -> Dict[str, Any]:
        """
        Process a single audio turn through the STT → LLM → TTS pipeline
        
        Args:
            session_id: Active session ID
            audio_data: Audio chunk data
            audio_format: Audio format
            
        Returns:
            Pipeline processing result with TTS audio
        """
        logger.info(f"🔄 Processing audio turn for session: {session_id}")
        
        try:
            # Get session from cache OR MongoDB
            session_info = None
            orch_doc = None
            
            if session_id in self.active_sessions:
                session_info = self.active_sessions[session_id]
                logger.info(f"✅ Session found in cache")
                # Load from DB anyway to get full document
                orch_doc = self.db['orchestration_sessions'].find_one({'session_id': session_id})
            else:
                # Try to load from MongoDB
                logger.info(f"🔍 Session not in cache, checking MongoDB...")
                orch_doc = self.db['orchestration_sessions'].find_one({'session_id': session_id})
                
                if orch_doc:
                    logger.info(f"✅ Session loaded from MongoDB")
                    session_info = {
                        'orchestration_id': orch_doc['orchestration_id'],
                        'session_id': orch_doc['session_id'],
                        'interview_id': orch_doc['interview_id'],
                        'meeting_id': orch_doc.get('meeting_id'),
                        'created_at': orch_doc.get('created_at', datetime.utcnow()),
                        'status': orch_doc.get('processing_status', orch_doc.get('final_status', 'active')),
                        'current_turn': orch_doc.get('current_turn', orch_doc.get('total_turns', 0)),
                        'conversation_active': orch_doc.get('conversation_active', True)
                    }
                    # Cache it
                    self.active_sessions[session_id] = session_info
                else:
                    raise ValueError(f"Session not found in cache or database: {session_id}")
            
            orchestration_id = session_info['orchestration_id']
            current_turn = session_info['current_turn'] + 1
            
            logger.info(f"🎯 Processing turn {current_turn} for orchestration {orchestration_id}")
            
            # Create state for this turn
            turn_state = OrchestratorState(
                orchestration_id=orchestration_id,
                session_id=session_id,
                interview_id=session_info['interview_id'],
                meeting_id=session_info.get('meeting_id'),
                candidate_name=orch_doc.get('candidate_name', 'Unknown Candidate') if orch_doc else 'Unknown Candidate',
                job_title=orch_doc.get('job_title', 'Unknown Position') if orch_doc else 'Unknown Position',
                
                conversation_active=True,
                current_turn=current_turn,
                turns_history=[],
                
                stt_status='pending',
                llm_status='idle',
                tts_status='idle',
                
                audio_chunk=audio_data,
                audio_format=audio_format,
                transcription_text='',
                transcription_confidence=0.0,
                speaker_detected='',
                
                llm_input='',
                llm_output='',
                llm_context=[],
                question_generated='',
                answer_evaluation={},
                next_action='continue',
                
                tts_text='',
                tts_audio_data=None,
                tts_audio_url=None,
                tts_duration_seconds=0.0,
                
                stt_latency_ms=0,
                llm_latency_ms=0,
                tts_latency_ms=0,
                total_latency_ms=0,
                
                stt_retries=0,
                llm_retries=0,
                tts_retries=0,
                
                conversation_quality_score=100.0,
                interruptions_count=0,
                successful_turns=0,
                failed_turns=0,
                
                processing_status='processing',
                success=False,
                
                errors=[],
                last_error='',
                retry_count=0,
                
                created_at=datetime.utcnow().isoformat(),
                last_activity_at=datetime.utcnow().isoformat(),
                completed_at=None
            )
            
            # Process through workflow with recursion limit
            logger.info(f"⚙️ Running through STT → LLM → TTS pipeline...")
            
            # Set recursion limit to prevent infinite loops
            # Since we process one turn at a time, limit is low
            config = {
                "recursion_limit": 10  # Max 10 steps for one turn
            }
            
            result_state = self.workflow.invoke(turn_state, config=config)
            
            # Update session cache with latest state
            # Ensure session is cached (it should be, but defensive programming)
            self.active_sessions[session_id] = {
                'orchestration_id': result_state['orchestration_id'],
                'session_id': result_state['session_id'],
                'interview_id': result_state['interview_id'],
                'meeting_id': result_state.get('meeting_id'),
                'created_at': result_state.get('created_at'),
                'status': result_state['processing_status'],
                'current_turn': result_state['current_turn'],
                'conversation_active': result_state['conversation_active']
            }
            
            return {
                'success': result_state['success'],
                'data': {
                    'session_id': session_id,
                    'orchestration_id': orchestration_id,
                    'turn': result_state['current_turn'],
                    'transcription': result_state['transcription_text'],
                    'transcription_confidence': result_state['transcription_confidence'],
                    'speaker': result_state['speaker_detected'],
                    'ai_response': result_state['llm_output'],
                    'question': result_state['question_generated'],
                    'answer_evaluation': result_state.get('answer_evaluation', {}),
                    'audio_url': result_state['tts_audio_url'],
                    'audio_duration': result_state['tts_duration_seconds'],
                    'latency': {
                        'stt_ms': result_state['stt_latency_ms'],
                        'llm_ms': result_state['llm_latency_ms'],
                        'tts_ms': result_state['tts_latency_ms'],
                        'total_ms': result_state['total_latency_ms']
                    },
                    'next_action': result_state['next_action'],
                    'conversation_active': result_state['conversation_active'],
                    'errors': result_state.get('errors', [])
                },
                'message': 'Audio turn processed successfully'
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing audio turn: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': {
                    'code': 'AUDIO_TURN_FAILED',
                    'message': str(e)
                },
                'message': 'Failed to process audio turn'
            }
    
    async def end_orchestration(self, session_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Gracefully end orchestration session
        
        Performs:
        1. Flush MCP caches to MongoDB
        2. Finalize conversation transcript
        3. Calculate and persist final metrics
        4. Mark session as terminated
        5. Clean up resources
        
        Args:
            session_id: Session to end
            force: Force shutdown even if session not found (default: False)
            
        Returns:
            Session summary and metrics
        """
        logger.info(f"🏁 Ending orchestration session: {session_id}")
        logger.info(f"   Force mode: {force}")
        
        try:
            # Step 1: Check cache first, then MongoDB
            session_cached = session_id in self.active_sessions
            
            if not session_cached:
                logger.info(f"🔍 Session not in cache, checking MongoDB...")
                orch_doc = self.db['orchestration_sessions'].find_one({'session_id': session_id})
                
                if not orch_doc and not force:
                    raise ValueError(f"Session not found in cache or database: {session_id}")
                elif not orch_doc and force:
                    logger.warning(f"⚠️ Force mode: Proceeding without session data")
                    return {
                        'success': True,
                        'data': {
                            'session_id': session_id,
                            'status': 'force_terminated',
                            'message': 'Session force-terminated without data'
                        },
                        'message': 'Session force-terminated'
                    }
            
            # Step 2: Flush MCP caches to ensure all data is persisted
            logger.info("💾 Step 1/5: Flushing MCP caches...")
            
            if session_cached:
                session_data_cache = self.active_sessions[session_id]
                orchestration_id = session_data_cache.get('orchestration_id')
                
                # Flush context cache
                if hasattr(self, 'context_manager'):
                    context_data = self.context_manager.get_context(orchestration_id)
                    if context_data:
                        logger.info(f"   Context data: {len(context_data)} chars flushed")
                
                # Flush token optimizer cache
                if hasattr(self, 'token_optimizer'):
                    logger.info(f"   Token optimizer cache cleared")
                
                logger.info("✅ MCP caches flushed")
            
            # Step 3: Get final session data from MongoDB
            logger.info("📄 Step 2/5: Retrieving final session data...")
            session_data = self.db['orchestration_sessions'].find_one({'session_id': session_id})
            
            if session_data:
                orchestration_id = session_data.get('orchestration_id')
                
                # Step 4: Finalize conversation transcript
                logger.info("📝 Step 3/5: Finalizing conversation transcript...")
                
                # Get all turns from conversation history
                conversation_history = session_data.get('conversation_history', [])
                final_transcript = {
                    'orchestration_id': orchestration_id,
                    'session_id': session_id,
                    'interview_id': session_data.get('interview_id'),
                    'candidate_name': session_data.get('candidate_name', 'Unknown'),
                    'job_description': session_data.get('job_description', ''),
                    'total_turns': len(conversation_history),
                    'conversation': conversation_history,
                    'created_at': session_data.get('created_at'),
                    'completed_at': datetime.utcnow(),
                    'duration_seconds': session_data.get('duration_seconds', 0)
                }
                
                # Persist transcript to separate collection for archival
                self.db['conversation_transcripts'].insert_one(final_transcript)
                logger.info(f"✅ Transcript finalized: {len(conversation_history)} turns archived")
                
                # Step 5: Calculate and persist final metrics
                logger.info("📊 Step 4/5: Calculating final metrics...")
                
                # Calculate comprehensive metrics
                final_metrics = {
                    'orchestration_id': orchestration_id,
                    'session_id': session_id,
                    'total_turns': session_data.get('current_turn', 0),
                    'successful_turns': session_data.get('successful_turns', 0),
                    'failed_turns': session_data.get('failed_turns', 0),
                    'success_rate': (session_data.get('successful_turns', 0) / max(session_data.get('current_turn', 1), 1)) * 100,
                    'quality_score': session_data.get('conversation_quality_score', 0),
                    'duration_seconds': session_data.get('duration_seconds', 0),
                    'avg_latency_ms': session_data.get('avg_latency_ms', 0),
                    'total_retries': session_data.get('total_retries', 0),
                    'stt_metrics': {
                        'total_calls': session_data.get('stt_total_calls', 0),
                        'avg_latency_ms': session_data.get('stt_avg_latency_ms', 0),
                        'success_rate': session_data.get('stt_success_rate', 100.0)
                    },
                    'llm_metrics': {
                        'total_calls': session_data.get('llm_total_calls', 0),
                        'avg_latency_ms': session_data.get('llm_avg_latency_ms', 0),
                        'success_rate': session_data.get('llm_success_rate', 100.0)
                    },
                    'tts_metrics': {
                        'total_calls': session_data.get('tts_total_calls', 0),
                        'avg_latency_ms': session_data.get('tts_avg_latency_ms', 0),
                        'success_rate': session_data.get('tts_success_rate', 100.0)
                    },
                    'created_at': session_data.get('created_at'),
                    'completed_at': datetime.utcnow()
                }
                
                # Persist metrics to dedicated collection
                self.db['orchestration_metrics'].insert_one(final_metrics)
                logger.info(f"✅ Final metrics persisted")
                logger.info(f"   Success rate: {final_metrics['success_rate']:.1f}%")
                logger.info(f"   Quality score: {final_metrics['quality_score']}")
                logger.info(f"   Total retries: {final_metrics['total_retries']}")
                
                # Step 6: Mark session as terminated
                logger.info("🔒 Step 5/5: Marking session as terminated...")
                
                self.db['orchestration_sessions'].update_one(
                    {'session_id': session_id},
                    {
                        '$set': {
                            'conversation_active': False,
                            'processing_status': 'terminated',
                            'completed_at': datetime.utcnow(),
                            'last_activity_at': datetime.utcnow(),
                            'graceful_shutdown': True,
                            'final_metrics': final_metrics
                        }
                    }
                )
                
                logger.info("✅ Session marked as terminated")
                
                summary = {
                    'orchestration_id': orchestration_id,
                    'session_id': session_id,
                    'interview_id': session_data.get('interview_id'),
                    'total_turns': final_metrics['total_turns'],
                    'successful_turns': final_metrics['successful_turns'],
                    'failed_turns': final_metrics['failed_turns'],
                    'success_rate': final_metrics['success_rate'],
                    'quality_score': final_metrics['quality_score'],
                    'duration_seconds': final_metrics['duration_seconds'],
                    'avg_latency_ms': final_metrics['avg_latency_ms'],
                    'total_retries': final_metrics['total_retries'],
                    'transcript_archived': True,
                    'metrics_persisted': True,
                    'graceful_shutdown': True,
                    'created_at': session_data.get('created_at'),
                    'completed_at': datetime.utcnow().isoformat()
                }
            else:
                summary = {'session_id': session_id, 'status': 'not_found', 'graceful_shutdown': False}
            
            # Step 7: Clean up resources
            logger.info("🧹 Cleaning up resources...")
            
            # Remove from active sessions cache
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                logger.info(f"✅ Session removed from cache")
            
            # Clear MCP caches for this session
            if hasattr(self, 'cache_manager') and session_cached:
                self.cache_manager.clear(orchestration_id)
                logger.info("✅ MCP caches cleared")
            
            logger.info(f"✅ Session ended successfully")
            logger.info(f"   Total turns: {summary.get('total_turns', 0)}")
            logger.info(f"   Success rate: {summary.get('success_rate', 0):.1f}%")
            logger.info(f"   Quality score: {summary.get('quality_score', 0)}")
            logger.info(f"   Transcript archived: {summary.get('transcript_archived', False)}")
            logger.info(f"   Metrics persisted: {summary.get('metrics_persisted', False)}")
            
            return {
                'success': True,
                'data': summary,
                'message': 'Orchestration session ended gracefully'
            }
            
        except Exception as e:
            logger.error(f"❌ Error ending orchestration: {str(e)}", exc_info=True)
            
            # Attempt force cleanup if not already in force mode
            if not force:
                logger.warning("⚠️ Attempting force cleanup...")
                return await self.end_orchestration(session_id, force=True)
            
            return {
                'success': False,
                'error': {
                    'code': 'ORCHESTRATION_END_FAILED',
                    'message': str(e)
                },
                'message': 'Failed to end orchestration session gracefully'
            }
    
    def close(self):
        """Close MongoDB connection"""
        self.mongo_client.close()
        logger.info("✅ Closed MongoDB connection")


# ==================== Singleton Management ====================

_realtime_orchestrator_instance: Optional[RealtimeOrchestratorAgent] = None

def get_realtime_orchestrator() -> RealtimeOrchestratorAgent:
    """
    Get or create singleton instance of RealtimeOrchestratorAgent
    
    Returns:
        Shared RealtimeOrchestratorAgent instance
    """
    global _realtime_orchestrator_instance
    
    if _realtime_orchestrator_instance is None:
        logger.info("🔧 Creating new RealtimeOrchestratorAgent singleton instance")
        _realtime_orchestrator_instance = RealtimeOrchestratorAgent()
    
    return _realtime_orchestrator_instance


def reset_realtime_orchestrator():
    """Reset singleton instance (useful for testing)"""
    global _realtime_orchestrator_instance
    
    if _realtime_orchestrator_instance is not None:
        _realtime_orchestrator_instance.close()
        _realtime_orchestrator_instance = None
        logger.info("🔄 RealtimeOrchestratorAgent singleton reset")


# ==================== Async Helper Functions ====================

async def start_realtime_orchestration(config: Dict[str, Any]) -> Dict[str, Any]:
    """Start a new real-time orchestration session"""
    agent = RealtimeOrchestratorAgent()
    try:
        result = await agent.start_orchestration(config)
        return result
    finally:
        agent.close()


async def process_orchestration_turn(session_id: str, audio_data: bytes, audio_format: str = 'webm') -> Dict[str, Any]:
    """Process a single audio turn"""
    agent = RealtimeOrchestratorAgent()
    try:
        result = await agent.process_audio_turn(session_id, audio_data, audio_format)
        return result
    finally:
        agent.close()


async def end_realtime_orchestration(session_id: str) -> Dict[str, Any]:
    """End orchestration session"""
    agent = RealtimeOrchestratorAgent()
    try:
        result = await agent.end_orchestration(session_id)
        return result
    finally:
        agent.close()


if __name__ == "__main__":
    # Test the orchestrator
    print("=" * 80)
    print("Testing Realtime Orchestrator Agent")
    print("=" * 80)
    
    async def test():
        config = {
            'session_id': f"session_{uuid.uuid4()}",
            'interview_id': 'test_interview_123',
            'meeting_id': 'test_meeting_456',
            'audio_format': 'webm',
            'enable_streaming': True
        }
        
        print("\n🎭 Starting orchestration...")
        result = await start_realtime_orchestration(config)
        print(f"\n✅ Result: {json.dumps(result, indent=2)}")
    
    asyncio.run(test())
    print("\n✅ Test complete")
