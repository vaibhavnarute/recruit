"""
Text-to-Speech (TTS) LangGraph Agent
Converts interview questions/responses to natural speech using Deepgram Aura
Streams audio back to meetings with voice profile matching
"""

import json
import logging
import uuid
import os
import sys
from typing import Dict, Any, TypedDict, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
import asyncio
from pymongo import MongoClient
import base64
import io
from dotenv import load_dotenv
from deepgram import DeepgramClient
import httpx

# Load environment variables from .env file
load_dotenv()
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


class TTSState(TypedDict):
    """State for TTS workflow"""
    # TTS Request
    tts_id: str
    session_id: str
    meeting_id: Optional[str]
    interview_id: Optional[str]
    
    # Text to convert
    text: str
    text_type: str  # intro, question, followup, closing, feedback
    
    # Voice configuration
    voice_id: str
    voice_name: str
    voice_profile: str  # professional_female, professional_male, friendly_female, friendly_male
    stability: float
    similarity_boost: float
    style: float
    use_speaker_boost: bool
    
    # Audio settings
    model_id: str  # eleven_multilingual_v2, eleven_turbo_v2
    output_format: str  # mp3_44100_128, pcm_16000, pcm_22050_16
    
    # Audio output
    audio_data: Optional[bytes]
    audio_base64: Optional[str]
    audio_url: Optional[str]
    audio_duration_seconds: float
    audio_size_bytes: int
    
    # Streaming
    is_streaming: bool
    stream_chunks: List[bytes]
    chunks_count: int
    
    # Analytics
    character_count: int
    word_count: int
    processing_time_ms: int
    
    # Context
    conversation_context: str
    emotion: str  # neutral, encouraging, professional, empathetic
    
    # Status
    processing_status: str  # pending, processing, completed, failed, streaming
    success: bool
    
    # Error handling
    errors: List[Dict[str, str]]
    last_error: str
    retry_count: int
    
    # Timestamps
    created_at: str
    started_at: str
    completed_at: Optional[str]


class TTSAgent:
    """
    LangGraph agent for Text-to-Speech conversion using Deepgram Aura
    
    Workflow:
    1. initialize_tts: Setup voice profile and audio settings
    2. validate_text: Check text length, content quality
    3. optimize_text: Clean and optimize text for speech
    4. select_voice: Choose appropriate voice based on context
    5. generate_speech: Call Deepgram Aura API to generate audio
    6. process_audio: Process and optimize audio output
    7. stream_audio: Stream audio chunks for real-time playback
    8. store_audio: Save audio data and metadata to MongoDB
    """
    
    # Deepgram Aura Voice profiles optimized for HR/Interview context
    VOICE_PROFILES = {
        'professional_female': {
            'voice_id': 'aura-asteria-en',  # Professional, clear female voice
            'name': 'Asteria',
            'description': 'Professional female voice, clear and confident'
        },
        'professional_male': {
            'voice_id': 'aura-orpheus-en',  # Professional male voice
            'name': 'Orpheus',
            'description': 'Professional male voice, authoritative'
        },
        'friendly_female': {
            'voice_id': 'aura-luna-en',  # Warm, friendly female
            'name': 'Luna',
            'description': 'Warm and friendly female voice'
        },
        'friendly_male': {
            'voice_id': 'aura-perseus-en',  # Friendly male
            'name': 'Perseus',
            'description': 'Friendly and approachable male voice'
        }
    }
    
    def __init__(self):
        """Initialize TTS Agent with Deepgram and MCP components"""
        logger.info("🔊 Initializing TTSAgent with Deepgram Aura")
        
        # Initialize Deepgram client
        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            logger.warning("⚠️ DEEPGRAM_API_KEY not found in environment")
        
        self.deepgram_client = DeepgramClient(api_key=api_key)
        
        # Initialize MCP components
        self.context_manager = MCPContextManager(max_context_length=5000)
        self.cache_manager = MCPCacheManager(
            ttl_minutes=60,  # Cache TTS results for 1 hour
            max_cache_size=200
        )
        self.token_optimizer = TokenOptimizer(
            max_input_tokens=5000,
            max_output_tokens=2000
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
        
        # Default settings for Deepgram Aura
        self.default_model = "aura-asteria-en"  # Default voice
        self.default_output_format = "mp3"  # Deepgram supports mp3, linear16, etc.
        self.default_voice_profile = "professional_female"
        
        # Build workflow
        self.workflow = self._build_workflow()
        logger.info("✅ TTSAgent initialized successfully with Deepgram")
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow for TTS"""
        workflow = StateGraph(TTSState)
        
        # Add nodes
        workflow.add_node("initialize_tts", self.initialize_tts)
        workflow.add_node("validate_text", self.validate_text)
        workflow.add_node("optimize_text", self.optimize_text)
        workflow.add_node("select_voice", self.select_voice)
        workflow.add_node("generate_speech", self.generate_speech)
        workflow.add_node("process_audio", self.process_audio)
        workflow.add_node("store_audio", self.store_audio)
        
        # Define edges
        workflow.set_entry_point("initialize_tts")
        workflow.add_edge("initialize_tts", "validate_text")
        workflow.add_edge("validate_text", "optimize_text")
        workflow.add_edge("optimize_text", "select_voice")
        workflow.add_edge("select_voice", "generate_speech")
        workflow.add_edge("generate_speech", "process_audio")
        workflow.add_edge("process_audio", "store_audio")
        workflow.add_edge("store_audio", END)
        
        return workflow.compile()
    
    # ==================== Workflow Nodes ====================
    
    def initialize_tts(self, state: TTSState) -> TTSState:
        """Initialize TTS request"""
        logger.info(f"🎬 Initializing TTS: {state.get('tts_id', 'unknown')}")
        
        try:
            state['processing_status'] = 'pending'
            state['created_at'] = datetime.utcnow().isoformat()
            state['started_at'] = datetime.utcnow().isoformat()
            state['success'] = False
            
            # Initialize counters
            state['character_count'] = len(state.get('text', ''))
            state['word_count'] = len(state.get('text', '').split())
            state['chunks_count'] = 0
            state['audio_duration_seconds'] = 0.0
            state['audio_size_bytes'] = 0
            state['retry_count'] = 0
            
            # Initialize lists
            state['errors'] = []
            state['stream_chunks'] = []
            
            # Set defaults if not provided
            if not state.get('voice_profile'):
                state['voice_profile'] = self.default_voice_profile
            
            if not state.get('model_id'):
                state['model_id'] = self.default_model
            
            if not state.get('output_format'):
                state['output_format'] = self.default_output_format
            
            if not state.get('emotion'):
                state['emotion'] = 'professional'
            
            logger.info(f"✅ TTS initialized")
            logger.info(f"   Text length: {state['character_count']} characters")
            logger.info(f"   Voice profile: {state.get('voice_profile')}")
            logger.info(f"   Model: {state.get('model_id')}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error initializing TTS: {str(e)}", exc_info=True)
            state['processing_status'] = 'failed'
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'initialize_tts',
                'error': str(e)
            })
            return state
    
    def validate_text(self, state: TTSState) -> TTSState:
        """Validate input text"""
        logger.info("✅ Validating text input")
        
        try:
            text = state.get('text', '').strip()
            
            if not text:
                raise ValueError("Text is empty")
            
            # Check length limits (ElevenLabs has 5000 char limit for some models)
            max_length = 5000
            if len(text) > max_length:
                logger.warning(f"⚠️ Text too long ({len(text)} chars), truncating to {max_length}")
                text = text[:max_length]
                state['text'] = text
                state['character_count'] = len(text)
                state['word_count'] = len(text.split())
            
            # Check minimum length
            if len(text) < 5:
                logger.warning("⚠️ Text very short, may not produce good audio")
            
            logger.info(f"✅ Text validated ({len(text)} chars)")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error validating text: {str(e)}", exc_info=True)
            state['processing_status'] = 'failed'
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'validate_text',
                'error': str(e)
            })
            return state
    
    def optimize_text(self, state: TTSState) -> TTSState:
        """Optimize text for better speech synthesis"""
        logger.info("🔧 Optimizing text for speech")
        
        try:
            text = state.get('text', '')
            
            # Clean up common issues
            # Replace multiple spaces with single space
            text = ' '.join(text.split())
            
            # Add pauses for better pacing
            text = text.replace('. ', '. ... ')  # Pause after sentences
            text = text.replace('? ', '? ... ')  # Pause after questions
            text = text.replace('! ', '! ... ')  # Pause after exclamations
            
            # Handle technical terms (add slight pauses)
            technical_terms = ['API', 'SDK', 'REST', 'HTTP', 'JSON', 'SQL', 'NoSQL']
            for term in technical_terms:
                text = text.replace(f' {term} ', f' {term}, ')
            
            state['text'] = text
            state['character_count'] = len(text)
            
            logger.info(f"✅ Text optimized ({len(text)} chars)")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error optimizing text: {str(e)}", exc_info=True)
            # Don't fail, just log warning and continue
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'optimize_text',
                'error': str(e),
                'severity': 'warning'
            })
            return state
    
    def select_voice(self, state: TTSState) -> TTSState:
        """Select appropriate voice based on profile and context"""
        logger.info(f"🎤 Selecting voice: {state.get('voice_profile')}")
        
        try:
            voice_profile = state.get('voice_profile', self.default_voice_profile)
            
            if voice_profile not in self.VOICE_PROFILES:
                logger.warning(f"⚠️ Unknown voice profile: {voice_profile}, using default")
                voice_profile = self.default_voice_profile
            
            profile = self.VOICE_PROFILES[voice_profile]
            
            # Set voice settings (Deepgram uses simpler voice selection)
            state['voice_id'] = profile['voice_id']
            state['voice_name'] = profile['name']
            
            logger.info(f"✅ Voice selected: {state['voice_name']}")
            logger.info(f"   Voice ID: {state['voice_id']}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error selecting voice: {str(e)}", exc_info=True)
            # Use defaults
            state['voice_id'] = self.VOICE_PROFILES[self.default_voice_profile]['voice_id']
            state['voice_name'] = self.VOICE_PROFILES[self.default_voice_profile]['name']
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'select_voice',
                'error': str(e),
                'severity': 'warning'
            })
            return state
    
    def generate_speech(self, state: TTSState) -> TTSState:
        """Generate speech using Deepgram Aura API"""
        logger.info(f"🎙️ Generating speech with Deepgram Aura")
        
        start_time = datetime.utcnow()
        
        try:
            state['processing_status'] = 'processing'
            
            text = state.get('text', '')
            voice_id = state.get('voice_id', 'aura-asteria-en')
            
            # Check if streaming is requested
            is_streaming = state.get('is_streaming', False)
            
            if is_streaming:
                logger.info("📡 Streaming mode enabled")
                # Stream using httpx
                url = f"https://api.deepgram.com/v1/speak?model={voice_id}&encoding=mp3"
                headers = {
                    "Authorization": f"Token {os.getenv('DEEPGRAM_API_KEY')}",
                    "Content-Type": "text/plain"
                }
                
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(url, headers=headers, content=text)
                    response.raise_for_status()
                    audio_data = response.content
                
                state['stream_chunks'] = []
                
            else:
                logger.info("🔊 Standard mode (non-streaming)")
                # Generate audio using REST API via httpx
                # Deepgram expects plain text in body, not JSON
                url = f"https://api.deepgram.com/v1/speak?model={voice_id}&encoding=mp3"
                headers = {
                    "Authorization": f"Token {os.getenv('DEEPGRAM_API_KEY')}",
                    "Content-Type": "text/plain"
                }
                
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(url, headers=headers, content=text)
                    response.raise_for_status()
                    audio_data = response.content
            
            state['audio_data'] = audio_data
            state['audio_size_bytes'] = len(audio_data)
            
            # Estimate duration based on character count
            # Deepgram Aura is fast: ~150-200 chars per second of speech
            estimated_duration = len(text) / 175  # Conservative estimate
            state['audio_duration_seconds'] = round(estimated_duration, 2)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            state['processing_time_ms'] = int(processing_time)
            
            logger.info(f"✅ Speech generated successfully")
            logger.info(f"   Audio size: {state['audio_size_bytes'] / 1024:.2f} KB")
            logger.info(f"   Duration: {state['audio_duration_seconds']} seconds")
            logger.info(f"   Processing time: {state['processing_time_ms']} ms")
            
            if is_streaming:
                logger.info(f"   Chunks: {state['chunks_count']}")
            
            state['processing_status'] = 'completed'
            state['success'] = True
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error generating speech: {str(e)}", exc_info=True)
            state['processing_status'] = 'failed'
            state['success'] = False
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'generate_speech',
                'error': str(e)
            })
            
            # Retry logic
            if state.get('retry_count', 0) < 3:
                state['retry_count'] += 1
                logger.info(f"🔄 Retrying... (attempt {state['retry_count']}/3)")
                # In production, implement exponential backoff
            
            return state
    
    def process_audio(self, state: TTSState) -> TTSState:
        """Process and encode audio data"""
        logger.info("🔧 Processing audio data")
        
        try:
            audio_data = state.get('audio_data')
            
            if not audio_data:
                logger.warning("⚠️ No audio data to process")
                return state
            
            # Convert to base64 for API response
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            state['audio_base64'] = audio_base64
            
            logger.info(f"✅ Audio processed")
            logger.info(f"   Base64 length: {len(audio_base64)} chars")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error processing audio: {str(e)}", exc_info=True)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'process_audio',
                'error': str(e),
                'severity': 'warning'
            })
            return state
    
    def store_audio(self, state: TTSState) -> TTSState:
        """Store audio and metadata in MongoDB"""
        logger.info(f"💾 Storing TTS audio: {state.get('tts_id')}")
        
        try:
            state['completed_at'] = datetime.utcnow().isoformat()
            
            # Prepare TTS document
            tts_doc = {
                "tts_id": state.get('tts_id'),
                "session_id": state.get('session_id'),
                "meeting_id": state.get('meeting_id'),
                "interview_id": state.get('interview_id'),
                
                # Text
                "text": state.get('text', ''),
                "text_type": state.get('text_type', 'question'),
                "character_count": state.get('character_count', 0),
                "word_count": state.get('word_count', 0),
                
                # Voice
                "voice_id": state.get('voice_id'),
                "voice_name": state.get('voice_name'),
                "voice_profile": state.get('voice_profile'),
                "stability": state.get('stability'),
                "similarity_boost": state.get('similarity_boost'),
                "style": state.get('style'),
                "use_speaker_boost": state.get('use_speaker_boost'),
                
                # Audio settings
                "model_id": state.get('model_id'),
                "output_format": state.get('output_format'),
                
                # Audio data
                "audio_base64": state.get('audio_base64'),
                "audio_url": state.get('audio_url'),
                "audio_duration_seconds": state.get('audio_duration_seconds', 0),
                "audio_size_bytes": state.get('audio_size_bytes', 0),
                
                # Streaming
                "is_streaming": state.get('is_streaming', False),
                "chunks_count": state.get('chunks_count', 0),
                
                # Context
                "conversation_context": state.get('conversation_context', ''),
                "emotion": state.get('emotion', 'professional'),
                
                # Performance
                "processing_time_ms": state.get('processing_time_ms', 0),
                
                # Status
                "processing_status": state.get('processing_status', 'completed'),
                "success": state.get('success', False),
                "errors": state.get('errors', []),
                "has_errors": len(state.get('errors', [])) > 0,
                
                # Timestamps
                "created_at": datetime.fromisoformat(state.get('created_at', datetime.utcnow().isoformat())),
                "started_at": datetime.fromisoformat(state.get('started_at', datetime.utcnow().isoformat())),
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Store in tts_audio collection
            tts_collection = self.db['tts_audio']
            result = tts_collection.update_one(
                {"tts_id": tts_doc["tts_id"]},
                {"$set": tts_doc},
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"✅ Stored new TTS audio: {tts_doc['tts_id']}")
            else:
                logger.info(f"✅ Updated TTS audio: {tts_doc['tts_id']}")
            
            # Update meeting with TTS info if meeting_id exists
            if state.get('meeting_id'):
                meetings_collection = self.db['meetings']
                meetings_collection.update_one(
                    {"meeting_id": state['meeting_id']},
                    {
                        "$push": {"tts_audio_ids": state['tts_id']},
                        "$set": {
                            "tts_enabled": True,
                            "last_tts_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
            
            logger.info(f"📊 TTS Summary:")
            logger.info(f"   Text: {state.get('text', '')[:50]}...")
            logger.info(f"   Voice: {state.get('voice_name')}")
            logger.info(f"   Duration: {state.get('audio_duration_seconds')}s")
            logger.info(f"   Size: {state.get('audio_size_bytes', 0) / 1024:.2f} KB")
            logger.info(f"   Processing: {state.get('processing_time_ms')}ms")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error storing TTS audio: {str(e)}", exc_info=True)
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'store_audio',
                'error': str(e)
            })
            return state
    
    # ==================== Public API Methods ====================
    
    async def text_to_speech(self, tts_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert text to speech
        
        Args:
            tts_request: TTS configuration
            
        Returns:
            Audio data and metadata
        """
        logger.info(f"🔊 Converting text to speech")
        
        try:
            # Initialize state
            initial_state = TTSState(
                tts_id=tts_request.get('tts_id', f"tts_{uuid.uuid4()}"),
                session_id=tts_request.get('session_id', ''),
                meeting_id=tts_request.get('meeting_id'),
                interview_id=tts_request.get('interview_id'),
                
                text=tts_request.get('text', ''),
                text_type=tts_request.get('text_type', 'question'),
                
                voice_id='',
                voice_name='',
                voice_profile=tts_request.get('voice_profile', self.default_voice_profile),
                stability=0.5,
                similarity_boost=0.75,
                style=0.5,
                use_speaker_boost=True,
                
                model_id=tts_request.get('model_id', self.default_model),
                output_format=tts_request.get('output_format', self.default_output_format),
                
                audio_data=None,
                audio_base64=None,
                audio_url=None,
                audio_duration_seconds=0.0,
                audio_size_bytes=0,
                
                is_streaming=tts_request.get('is_streaming', False),
                stream_chunks=[],
                chunks_count=0,
                
                character_count=0,
                word_count=0,
                processing_time_ms=0,
                
                conversation_context=tts_request.get('conversation_context', ''),
                emotion=tts_request.get('emotion', 'professional'),
                
                processing_status='pending',
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
                        "tts_id": result['tts_id'],
                        "audio_base64": result.get('audio_base64'),
                        "audio_url": result.get('audio_url'),
                        "audio_duration_seconds": result.get('audio_duration_seconds'),
                        "audio_size_bytes": result.get('audio_size_bytes'),
                        "voice_name": result.get('voice_name'),
                        "processing_time_ms": result.get('processing_time_ms'),
                        "is_streaming": result.get('is_streaming', False),
                        "chunks_count": result.get('chunks_count', 0)
                    },
                    "message": "Speech generated successfully"
                }
            else:
                return {
                    "success": False,
                    "error": {
                        "code": "TTS_GENERATION_FAILED",
                        "message": result.get('last_error', 'Failed to generate speech'),
                        "details": result.get('errors', [])
                    },
                    "message": "Failed to generate speech"
                }
            
        except Exception as e:
            logger.error(f"❌ Error in text_to_speech: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": {
                    "code": "TTS_ERROR",
                    "message": str(e)
                },
                "message": "TTS processing failed"
            }
    
    async def stream_speech(self, tts_request: Dict[str, Any]):
        """
        Stream speech audio in real-time
        
        Args:
            tts_request: TTS configuration
            
        Yields:
            Audio chunks as they're generated
        """
        logger.info(f"📡 Streaming speech audio")
        
        try:
            text = tts_request.get('text', '')
            voice_profile = tts_request.get('voice_profile', self.default_voice_profile)
            
            # Get voice settings
            profile = self.VOICE_PROFILES.get(voice_profile, self.VOICE_PROFILES[self.default_voice_profile])
            
            voice_settings = VoiceSettings(
                stability=profile['stability'],
                similarity_boost=profile['similarity_boost'],
                style=profile.get('style', 0.5),
                use_speaker_boost=profile.get('use_speaker_boost', True)
            )
            
            # Stream audio using ElevenLabs SDK
            # The convert() method returns a generator that streams audio chunks
            audio_stream = self.elevenlabs_client.text_to_speech.convert(
                voice_id=profile['voice_id'],
                text=text,
                model_id=tts_request.get('model_id', self.default_model),
                voice_settings=voice_settings,
                output_format=tts_request.get('output_format', self.default_output_format)
            )
            
            chunk_count = 0
            for chunk in audio_stream:
                if chunk:
                    chunk_count += 1
                    yield {
                        "chunk": base64.b64encode(chunk).decode('utf-8'),
                        "chunk_number": chunk_count,
                        "is_final": False
                    }
            
            # Send final chunk marker
            yield {
                "chunk": "",
                "chunk_number": chunk_count,
                "is_final": True
            }
            
            logger.info(f"✅ Streamed {chunk_count} audio chunks")
            
        except Exception as e:
            logger.error(f"❌ Error streaming speech: {str(e)}", exc_info=True)
            yield {
                "error": str(e),
                "is_final": True
            }
    
    def close(self):
        """Close MongoDB connection"""
        self.mongo_client.close()
        logger.info("✅ Closed MongoDB connection")


# Async helper functions
async def convert_text_to_speech(tts_request: Dict[str, Any]) -> Dict[str, Any]:
    """Convert text to speech"""
    agent = TTSAgent()
    try:
        result = await agent.text_to_speech(tts_request)
        return result
    finally:
        agent.close()


async def stream_text_to_speech(tts_request: Dict[str, Any]):
    """Stream text to speech"""
    agent = TTSAgent()
    try:
        async for chunk in agent.stream_speech(tts_request):
            yield chunk
    finally:
        agent.close()


if __name__ == "__main__":
    # Test the agent
    print("=" * 80)
    print("Testing TTS Agent")
    print("=" * 80)
    
    import asyncio
    
    async def test():
        request = {
            "text": "Hello! Welcome to your technical interview for the Senior Python Developer position. I'm excited to learn about your experience with Python, FastAPI, and system design. Let's get started with some technical questions.",
            "text_type": "intro",
            "voice_profile": "professional_female",
            "emotion": "professional",
            "session_id": "test_session_123"
        }
        
        result = await convert_text_to_speech(request)
        print("\n✅ TTS Test Result:")
        print(f"Success: {result.get('success')}")
        if result.get('success'):
            data = result.get('data', {})
            print(f"TTS ID: {data.get('tts_id')}")
            print(f"Voice: {data.get('voice_name')}")
            print(f"Duration: {data.get('audio_duration_seconds')}s")
            print(f"Size: {data.get('audio_size_bytes', 0) / 1024:.2f} KB")
            print(f"Processing: {data.get('processing_time_ms')}ms")
        else:
            print(f"Error: {result.get('error')}")
    
    asyncio.run(test())
    print("\n✅ Test complete")
