"""
Audio Transcription LangGraph Agent
Handles real-time audio transcription using Groq Whisper API
"""

import json
import logging
import asyncio
import base64
from typing import Dict, Any, TypedDict, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from groq import Groq
import os
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
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


class TranscriptionState(TypedDict):
    """State for audio transcription workflow"""
    session_id: str
    audio_chunk_id: str
    audio_data: bytes
    audio_format: str  # webm, wav, mp3, etc.
    audio_file_path: str  # Path to temp audio file
    
    # Processing state
    processing_status: str  # pending, converting, transcribing, analyzing, completed, failed
    chunk_size: int
    chunk_duration: float
    
    # Transcription results
    raw_transcription: str
    cleaned_transcription: str
    speaker_detected: str
    confidence_score: float
    language_detected: str
    
    # Interview context
    interview_id: str
    question_context: str
    previous_transcripts: List[Dict[str, Any]]
    
    # Analysis
    sentiment: str
    key_points: List[str]
    technical_terms: List[str]
    
    # Error handling
    errors: List[Dict[str, str]]
    last_error: str
    retry_count: int
    max_retries: int
    
    # Timestamps
    received_at: str
    transcribed_at: str
    analyzed_at: str


class AudioTranscriptionAgent:
    """
    LangGraph agent for real-time audio transcription and analysis
    
    Workflow:
    1. receive_audio: Validate and prepare audio chunk
    2. convert_format: Ensure audio is in Whisper-compatible format
    3. transcribe_audio: Use Groq Whisper API for STT
    4. clean_transcription: Remove artifacts and format text
    5. analyze_content: Extract insights using LLM
    6. store_transcript: Prepare for storage
    """
    
    def __init__(self):
        """Initialize Audio Transcription Agent with MCP components"""
        logger.info("Initializing AudioTranscriptionAgent")
        
        # Initialize Groq client
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.whisper_model = "whisper-large-v3"
        self.llm_model = "llama-3.3-70b-versatile"
        
        # Initialize MCP components
        self.context_manager = MCPContextManager(max_context_length=10000)
        self.cache_manager = MCPCacheManager(
            ttl_minutes=60,  # Cache transcriptions for 1 hour
            max_cache_size=500
        )
        self.token_optimizer = TokenOptimizer(
            max_input_tokens=10000,
            max_output_tokens=10000
        )
        
        # Temp directory for audio files
        self.temp_dir = Path(tempfile.gettempdir()) / "meet_bot_audio"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Build workflow
        self.workflow = self._build_workflow()
        logger.info("AudioTranscriptionAgent initialized successfully")
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow"""
        workflow = StateGraph(TranscriptionState)
        
        # Add nodes
        workflow.add_node("receive_audio", self.receive_audio)
        workflow.add_node("convert_format", self.convert_format)
        workflow.add_node("transcribe_audio", self.transcribe_audio)
        workflow.add_node("clean_transcription", self.clean_transcription)
        workflow.add_node("analyze_content", self.analyze_content)
        workflow.add_node("store_transcript", self.store_transcript)
        
        # Define edges
        workflow.set_entry_point("receive_audio")
        
        workflow.add_edge("receive_audio", "convert_format")
        
        workflow.add_conditional_edges(
            "convert_format",
            self._should_continue_after_conversion,
            {
                "continue": "transcribe_audio",
                "retry": "convert_format",
                "fail": "store_transcript"
            }
        )
        
        workflow.add_conditional_edges(
            "transcribe_audio",
            self._should_continue_after_transcription,
            {
                "continue": "clean_transcription",
                "retry": "transcribe_audio",
                "fail": "store_transcript"
            }
        )
        
        workflow.add_edge("clean_transcription", "analyze_content")
        workflow.add_edge("analyze_content", "store_transcript")
        workflow.add_edge("store_transcript", END)
        
        return workflow.compile()
    
    def receive_audio(self, state: TranscriptionState) -> TranscriptionState:
        """Receive and validate audio chunk"""
        logger.info(f"Receiving audio chunk: {state.get('audio_chunk_id', 'unknown')}")
        
        try:
            # Validate audio data
            if not state.get('audio_data'):
                raise ValueError("No audio data provided")
            
            state['processing_status'] = 'pending'
            state['received_at'] = datetime.utcnow().isoformat()
            state['retry_count'] = 0
            state['max_retries'] = state.get('max_retries', 3)
            state['errors'] = []
            state['chunk_size'] = len(state['audio_data'])
            
            logger.info(f"Audio chunk received: {state['chunk_size']} bytes")
            logger.info(f"Format: {state.get('audio_format', 'unknown')}")
            
            return state
            
        except Exception as e:
            logger.error(f"Error receiving audio: {str(e)}", exc_info=True)
            state['processing_status'] = 'failed'
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'receive_audio',
                'error': str(e)
            })
            return state
    
    def convert_format(self, state: TranscriptionState) -> TranscriptionState:
        """Convert audio to Whisper-compatible format if needed"""
        logger.info(f"Converting audio format: {state.get('audio_format', 'unknown')}")
        
        try:
            state['processing_status'] = 'converting'
            
            # Validate audio data exists
            if not state.get('audio_data'):
                raise ValueError("No audio data in state")
            
            audio_data = state['audio_data']
            if isinstance(audio_data, str):
                # If it's a base64 string, decode it
                import base64
                try:
                    audio_data = base64.b64decode(audio_data)
                    logger.info("Decoded base64 audio data")
                except Exception as decode_error:
                    logger.error(f"Failed to decode base64: {decode_error}")
                    raise ValueError(f"Invalid base64 audio data: {decode_error}")
            
            if not isinstance(audio_data, bytes):
                raise ValueError(f"Audio data must be bytes, got {type(audio_data)}")
            
            if len(audio_data) < 100:
                raise ValueError(f"Audio data too small: {len(audio_data)} bytes")
            
            # Whisper API supports: mp3, mp4, mpeg, mpga, m4a, wav, webm
            supported_formats = ['mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm']
            audio_format = state.get('audio_format', '').lower()
            
            if audio_format not in supported_formats:
                logger.warning(f"Unsupported format '{audio_format}', defaulting to mp3")
                audio_format = 'mp3'
                state['audio_format'] = audio_format
            
            # Ensure temp directory exists
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Temp directory: {self.temp_dir}")
            
            # Save audio chunk to temp file
            audio_filename = f"{state['audio_chunk_id']}.{audio_format}"
            audio_path = self.temp_dir / audio_filename
            
            logger.info(f"Writing audio to: {audio_path}")
            logger.info(f"Audio data size: {len(audio_data)} bytes")
            
            with open(audio_path, 'wb') as f:
                bytes_written = f.write(audio_data)
            
            # Verify file was written
            if not audio_path.exists():
                raise IOError(f"Failed to create audio file: {audio_path}")
            
            file_size = audio_path.stat().st_size
            if file_size == 0:
                raise IOError(f"Audio file is empty: {audio_path}")
            
            state['audio_file_path'] = str(audio_path)
            
            logger.info(f"✅ Audio saved successfully: {audio_path}")
            logger.info(f"   File size: {file_size} bytes")
            logger.info(f"   Format: {audio_format}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error converting audio format: {str(e)}", exc_info=True)
            state['retry_count'] = state.get('retry_count', 0) + 1
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'convert_format',
                'error': str(e)
            })
            # Don't set audio_file_path if conversion failed
            state['audio_file_path'] = None
            return state
    
    def transcribe_audio(self, state: TranscriptionState) -> TranscriptionState:
        """Transcribe audio using Groq Whisper API"""
        logger.info(f"Transcribing audio chunk: {state.get('audio_chunk_id', 'unknown')}")
        
        try:
            state['processing_status'] = 'transcribing'
            
            # Check cache first
            cache_key = f"transcription_{state['audio_chunk_id']}"
            cached_transcription = self.cache_manager.get(cache_key)
            
            if cached_transcription:
                logger.info("Using cached transcription")
                state['raw_transcription'] = cached_transcription
                state['transcribed_at'] = datetime.utcnow().isoformat()
                return state
            
            # Read audio file
            audio_path = state.get('audio_file_path')
            if not audio_path or not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            # Call Groq Whisper API
            logger.info(f"Calling Groq Whisper API with model: {self.whisper_model}")
            
            with open(audio_path, 'rb') as audio_file:
                transcription = self.groq_client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), audio_file.read()),
                    model=self.whisper_model,
                    response_format="verbose_json",
                    language="en",
                    temperature=0.0
                )
            
            # Extract transcription text
            if hasattr(transcription, 'text'):
                state['raw_transcription'] = transcription.text
                state['language_detected'] = getattr(transcription, 'language', 'en')
                state['chunk_duration'] = getattr(transcription, 'duration', 0.0)
            else:
                state['raw_transcription'] = str(transcription)
            
            state['transcribed_at'] = datetime.utcnow().isoformat()
            
            # Cache the transcription
            self.cache_manager.set(cache_key, state['raw_transcription'])
            
            logger.info(f"Transcription completed: {len(state['raw_transcription'])} characters")
            logger.info(f"Transcription preview: {state['raw_transcription'][:100]}...")
            
            # Cleanup temp file
            try:
                os.remove(audio_path)
                logger.debug(f"Cleaned up temp file: {audio_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
            
            return state
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}", exc_info=True)
            state['retry_count'] += 1
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'transcribe_audio',
                'error': str(e)
            })
            return state
    
    def clean_transcription(self, state: TranscriptionState) -> TranscriptionState:
        """Clean and format transcription"""
        logger.info(f"Cleaning transcription for chunk: {state.get('audio_chunk_id', 'unknown')}")
        
        try:
            raw_text = state.get('raw_transcription', '')
            
            if not raw_text or raw_text.strip() == '':
                logger.warning("Empty transcription received")
                state['cleaned_transcription'] = ''
                return state
            
            # Build context for LLM cleaning
            context = self.context_manager.build_context([
                f"Raw transcription: {raw_text}",
                f"Interview context: {state.get('question_context', 'General interview question')}",
                f"Previous context: {state.get('previous_transcripts', [])[-1:] if state.get('previous_transcripts') else 'None'}"
            ])
            
            prompt = f"""You are a transcription cleaning expert. Clean this interview transcription by:
1. Fixing grammar and punctuation
2. Removing filler words (um, uh, like) unless they indicate hesitation
3. Correcting obvious speech-to-text errors
4. Preserving the speaker's original meaning and tone
5. Keeping technical terms intact

Context:
{context}

Provide a JSON response with:
1. "cleaned_text": The cleaned transcription
2. "confidence": Your confidence in the cleaning (0.0-1.0)
3. "notable_changes": List of significant corrections made
4. "speaker_indicators": Any detected speaker changes or emotions

Response:"""
            
            # Optimize prompt and extract text (not TokenStats object)
            optimization_result = self.token_optimizer.optimize_prompt(prompt)
            if isinstance(optimization_result, dict) and 'optimized_text' in optimization_result:
                optimized_prompt = optimization_result['optimized_text']
            elif isinstance(optimization_result, str):
                optimized_prompt = optimization_result
            else:
                # If optimizer returns an object, just use original prompt
                optimized_prompt = prompt
            
            logger.info("Calling Groq LLM for transcription cleaning")
            response = self.groq_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": optimized_prompt}],
                temperature=0.2,
                max_tokens=2000,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            cleaning_result = response.choices[0].message.content.strip()
            logger.info(f"🔍 LLM Cleaning Response: {cleaning_result[:200]}...")
            
            # Parse JSON response
            try:
                if "```json" in cleaning_result:
                    cleaning_result = cleaning_result.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaning_result:
                    cleaning_result = cleaning_result.split("```")[1].split("```")[0].strip()
                
                cleaned_data = json.loads(cleaning_result)
                state['cleaned_transcription'] = cleaned_data.get('cleaned_text', raw_text)
                
                # Calculate confidence based on text characteristics
                confidence = cleaned_data.get('confidence', 0.8)
                # Boost confidence for clear, well-structured responses
                if len(raw_text) > 50 and '.' in raw_text:
                    confidence = min(confidence + 0.1, 1.0)
                state['confidence_score'] = round(confidence, 2)
                
                speaker_indicators = cleaned_data.get('speaker_indicators', {})
                if isinstance(speaker_indicators, dict):
                    state['speaker_detected'] = speaker_indicators.get('emotion', 'neutral')
                else:
                    state['speaker_detected'] = 'neutral'
                
                logger.info(f"✅ Transcription cleaned successfully")
                logger.info(f"   Confidence: {state['confidence_score']}")
                logger.info(f"   Cleaned text: {state['cleaned_transcription'][:100]}...")
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse cleaning JSON: {str(e)}")
                logger.error(f"   Raw response: {cleaning_result}")
                state['cleaned_transcription'] = raw_text
                # Calculate basic confidence based on transcription quality
                confidence = 0.7 if len(raw_text) > 50 else 0.5
                state['confidence_score'] = confidence
                state['speaker_detected'] = 'neutral'
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error cleaning transcription: {str(e)}", exc_info=True)
            # Fallback to raw transcription with basic analysis
            state['cleaned_transcription'] = state.get('raw_transcription', '')
            # Calculate confidence based on transcription length and structure
            raw_text = state.get('raw_transcription', '')
            if len(raw_text) > 100 and '.' in raw_text:
                state['confidence_score'] = 0.75  # Good length and structure
            elif len(raw_text) > 50:
                state['confidence_score'] = 0.65  # Medium length
            else:
                state['confidence_score'] = 0.5  # Short/unclear
            state['speaker_detected'] = 'neutral'
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'clean_transcription',
                'error': str(e)
            })
            return state
    
    def analyze_content(self, state: TranscriptionState) -> TranscriptionState:
        """Analyze transcription content for insights"""
        logger.info(f"Analyzing content for chunk: {state.get('audio_chunk_id', 'unknown')}")
        
        try:
            state['processing_status'] = 'analyzing'
            
            cleaned_text = state.get('cleaned_transcription', '')
            
            if not cleaned_text or len(cleaned_text) < 10:
                logger.warning("Transcription too short for analysis")
                state['sentiment'] = 'neutral'
                state['key_points'] = []
                state['technical_terms'] = []
                state['analyzed_at'] = datetime.utcnow().isoformat()
                return state
            
            # Build context for analysis
            context = self.context_manager.build_context([
                f"Transcription: {cleaned_text}",
                f"Interview ID: {state.get('interview_id', 'unknown')}",
                f"Question context: {state.get('question_context', 'General question')}"
            ])
            
            prompt = f"""Analyze this interview transcription segment and extract insights.

Context:
{context}

Provide a JSON response with:
1. "sentiment": Overall sentiment (positive, neutral, negative, mixed)
2. "key_points": List of 3-5 main points or ideas expressed
3. "technical_terms": Technical terms or jargon used
4. "clarity_score": How clear and coherent the response is (0.0-1.0)
5. "completeness": Is this a complete thought or partial response
6. "follow_up_needed": Does this require follow-up questions (true/false)

Response:"""
            
            # Optimize prompt and extract text (not TokenStats object)
            optimization_result = self.token_optimizer.optimize_prompt(prompt)
            if isinstance(optimization_result, dict) and 'optimized_text' in optimization_result:
                optimized_prompt = optimization_result['optimized_text']
            elif isinstance(optimization_result, str):
                optimized_prompt = optimization_result
            else:
                # If optimizer returns an object, just use original prompt
                optimized_prompt = prompt
            
            logger.info("Calling Groq LLM for content analysis")
            response = self.groq_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": optimized_prompt}],
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            analysis_result = response.choices[0].message.content.strip()
            logger.info(f"🔍 LLM Analysis Response: {analysis_result[:200]}...")
            
            # Parse JSON response
            try:
                if "```json" in analysis_result:
                    analysis_result = analysis_result.split("```json")[1].split("```")[0].strip()
                elif "```" in analysis_result:
                    analysis_result = analysis_result.split("```")[1].split("```")[0].strip()
                
                analysis = json.loads(analysis_result)
                
                # Extract sentiment with validation
                sentiment = analysis.get('sentiment', 'neutral').lower()
                valid_sentiments = ['positive', 'negative', 'neutral', 'mixed']
                state['sentiment'] = sentiment if sentiment in valid_sentiments else 'neutral'
                
                # Extract key points
                key_points = analysis.get('key_points', [])
                state['key_points'] = key_points if isinstance(key_points, list) else []
                
                # Extract technical terms
                tech_terms = analysis.get('technical_terms', [])
                state['technical_terms'] = tech_terms if isinstance(tech_terms, list) else []
                
                logger.info(f"✅ Content analyzed successfully")
                logger.info(f"   Sentiment: {state['sentiment']}")
                logger.info(f"   Key points: {len(state['key_points'])}")
                logger.info(f"   Technical terms: {state['technical_terms']}")
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse analysis JSON: {str(e)}")
                logger.error(f"   Raw response: {analysis_result}")
                
                # Simple fallback analysis
                text_lower = cleaned_text.lower()
                # Basic sentiment detection
                positive_words = ['good', 'great', 'excellent', 'improved', 'successful', 'achieved']
                negative_words = ['bad', 'failed', 'problem', 'issue', 'difficult', 'challenge']
                
                pos_count = sum(1 for word in positive_words if word in text_lower)
                neg_count = sum(1 for word in negative_words if word in text_lower)
                
                if pos_count > neg_count:
                    state['sentiment'] = 'positive'
                elif neg_count > pos_count:
                    state['sentiment'] = 'mixed'  # Challenges mentioned but handled
                else:
                    state['sentiment'] = 'neutral'
                
                state['key_points'] = []
                state['technical_terms'] = []
            
            state['analyzed_at'] = datetime.utcnow().isoformat()
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error analyzing content: {str(e)}", exc_info=True)
            
            # Smarter fallback analysis based on text content
            cleaned_text = state.get('cleaned_transcription', '')
            text_lower = cleaned_text.lower()
            
            # Sentiment analysis based on keywords
            positive_words = ['good', 'great', 'excellent', 'improved', 'successful', 'achieved', 
                            'effective', 'optimized', 'increased', 'enhanced', 'better']
            negative_words = ['bad', 'failed', 'problem', 'issue', 'error', 'poor', 'worse', 'decreased']
            challenge_words = ['difficult', 'challenge', 'complex', 'tough']
            
            pos_count = sum(1 for word in positive_words if word in text_lower)
            neg_count = sum(1 for word in negative_words if word in text_lower)
            challenge_count = sum(1 for word in challenge_words if word in text_lower)
            
            # Determine sentiment
            if pos_count > 2 or (pos_count > 0 and challenge_count > 0):
                state['sentiment'] = 'positive'  # Positive outcomes or overcome challenges
            elif neg_count > pos_count + 1:
                state['sentiment'] = 'negative'
            elif challenge_count > 0 and pos_count > 0:
                state['sentiment'] = 'mixed'  # Challenges with positive resolution
            else:
                state['sentiment'] = 'neutral'
            
            state['key_points'] = []
            state['technical_terms'] = []
            state['analyzed_at'] = datetime.utcnow().isoformat()
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'analyze_content',
                'error': str(e)
            })
            return state
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'analyze_content',
                'error': str(e)
            })
            return state
    
    def store_transcript(self, state: TranscriptionState) -> TranscriptionState:
        """Prepare transcript and store in MongoDB"""
        logger.info(f"📝 Storing transcript for chunk: {state.get('audio_chunk_id', 'unknown')}")
        
        try:
            # Mark as completed or failed
            if state.get('cleaned_transcription'):
                state['processing_status'] = 'completed'
                logger.info(f"✅ Transcription completed successfully")
            else:
                state['processing_status'] = 'failed'
                logger.warning(f"⚠️ Transcription failed or empty")
            
            # Store in MongoDB transcriptions collection
            try:
                from pymongo import MongoClient
                import os
                
                mongo_uri = os.getenv('MONGO_URI', 'mongodb+srv://narutevaibhav95_db_user:9Y0gsqDxtHRoBH5w@resumate.xbvpnl1.mongodb.net/')
                mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
                
                # Configure MongoDB client with proper timeout settings for Atlas
                client = MongoClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=10000,  # 10 seconds
                    connectTimeoutMS=10000,  # 10 seconds
                    socketTimeoutMS=45000,  # 45 seconds for operations
                    maxPoolSize=50,
                    retryWrites=True,
                    retryReads=True
                )
                db = client[mongo_db_name]
                transcriptions_collection = db['transcriptions']
                
                # Prepare transcription document
                transcription_doc = {
                    "transcription_id": f"trans_{state.get('audio_chunk_id', 'unknown')}",
                    "session_id": state.get('session_id', ''),
                    "meeting_id": state.get('meeting_id'),  # Optional
                    "interview_id": state.get('interview_id', ''),
                    "chunk_id": state.get('audio_chunk_id', ''),
                    "audio_chunk_number": state.get('chunk_number', 0),
                    
                    # Audio metadata
                    "audio_format": state.get('audio_format', 'unknown'),
                    "audio_duration": state.get('chunk_duration', 0.0),
                    "audio_size_bytes": state.get('chunk_size', 0),
                    
                    # Transcription data
                    "raw_transcription": state.get('raw_transcription', ''),
                    "cleaned_transcription": state.get('cleaned_transcription', ''),
                    "language_detected": state.get('language_detected', 'unknown'),
                    "confidence_score": state.get('confidence_score', 0.0),
                    
                    # Analysis results
                    "sentiment": state.get('sentiment', 'neutral'),
                    "speaker_detected": state.get('speaker_detected', ''),
                    "key_points": state.get('key_points', []),
                    "technical_terms": state.get('technical_terms', []),
                    "questions_asked": [],  # Can be enhanced later
                    "answers_given": [],  # Can be enhanced later
                    
                    # Processing details
                    "model": state.get('model', 'whisper-large-v3'),
                    "llm_model": self.llm_model,
                    "workflow": "langgraph",
                    "mcp_optimized": True,
                    "processing_time_ms": state.get('processing_time_ms', 0.0),
                    "tokens_used": state.get('tokens_used'),
                    
                    # Context
                    "question_context": state.get('question_context', ''),
                    "interview_stage": state.get('interview_stage'),
                    
                    # Timestamps
                    "transcribed_at": datetime.fromisoformat(state.get('transcribed_at', datetime.utcnow().isoformat())),
                    "analyzed_at": datetime.fromisoformat(state.get('analyzed_at', datetime.utcnow().isoformat())) if state.get('analyzed_at') else None,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    
                    # Error tracking
                    "has_errors": len(state.get('errors', [])) > 0,
                    "errors": state.get('errors', []),
                    
                    "metadata": {
                        "retry_count": state.get('retry_count', 0),
                        "max_retries": state.get('max_retries', 3),
                        "processing_status": state['processing_status']
                    }
                }
                
                # Insert or update
                result = transcriptions_collection.update_one(
                    {"transcription_id": transcription_doc["transcription_id"]},
                    {"$set": transcription_doc},
                    upsert=True
                )
                
                if result.upserted_id:
                    logger.info(f"✅ Stored new transcription in DB: {transcription_doc['transcription_id']}")
                else:
                    logger.info(f"✅ Updated existing transcription in DB: {transcription_doc['transcription_id']}")
                
                # Also keep backward compatibility with meet_transcripts
                meet_transcripts_collection = db['meet_transcripts']
                meet_transcript_doc = {
                    "chunk_id": state.get('audio_chunk_id', ''),
                    "session_id": state.get('session_id', ''),
                    "raw_transcription": state.get('raw_transcription', ''),
                    "cleaned_transcription": state.get('cleaned_transcription', ''),
                    "confidence_score": state.get('confidence_score', 0.0),
                    "sentiment": state.get('sentiment', 'neutral'),
                    "language_detected": state.get('language_detected', 'unknown'),
                    "speaker_detected": state.get('speaker_detected', ''),
                    "key_points": state.get('key_points', []),
                    "technical_terms": state.get('technical_terms', []),
                    "model": state.get('model', 'whisper-large-v3'),
                    "workflow": "langgraph",
                    "mcp_optimized": True,
                    "processing_time_ms": state.get('processing_time_ms', 0.0),
                    "transcribed_at": datetime.utcnow()
                }
                
                meet_transcripts_collection.update_one(
                    {"chunk_id": meet_transcript_doc["chunk_id"]},
                    {"$set": meet_transcript_doc},
                    upsert=True
                )
                
                client.close()
                
            except Exception as db_error:
                logger.error(f"❌ Error storing to MongoDB: {str(db_error)}", exc_info=True)
                # Don't fail the whole transcription if DB storage fails
            
            # Log final statistics
            logger.info(f"📊 Final Statistics:")
            logger.info(f"   Status: {state['processing_status']}")
            logger.info(f"   Raw length: {len(state.get('raw_transcription', ''))} chars")
            logger.info(f"   Cleaned length: {len(state.get('cleaned_transcription', ''))} chars")
            logger.info(f"   Confidence: {state.get('confidence_score', 0.0)}")
            logger.info(f"   Sentiment: {state.get('sentiment', 'neutral')}")
            logger.info(f"   Key Points: {len(state.get('key_points', []))}")
            logger.info(f"   Technical Terms: {len(state.get('technical_terms', []))}")
            logger.info(f"   Errors: {len(state.get('errors', []))}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error storing transcript: {str(e)}", exc_info=True)
            state['processing_status'] = 'failed'
            state['last_error'] = str(e)
            return state
    
    # Conditional edge functions
    
    def _should_continue_after_conversion(self, state: TranscriptionState) -> str:
        """Determine next step after audio conversion"""
        if state.get('last_error') and state.get('retry_count', 0) < state.get('max_retries', 3):
            return "retry"
        elif state.get('last_error'):
            return "fail"
        else:
            return "continue"
    
    def _should_continue_after_transcription(self, state: TranscriptionState) -> str:
        """Determine next step after transcription"""
        if state.get('last_error') and state.get('retry_count', 0) < state.get('max_retries', 3):
            logger.info(f"Retrying transcription (attempt {state.get('retry_count', 0) + 1})")
            return "retry"
        elif state.get('last_error'):
            logger.warning("Max retries reached for transcription")
            return "fail"
        elif state.get('raw_transcription'):
            return "continue"
        else:
            return "fail"
    
    async def transcribe_chunk(self, chunk_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transcribe a single audio chunk
        
        Args:
            chunk_config: Configuration with audio_data, session_id, etc.
            
        Returns:
            Transcription result
        """
        logger.info(f"Starting audio chunk transcription")
        logger.info(f"Chunk ID: {chunk_config.get('audio_chunk_id', 'unknown')}")
        logger.info(f"Session ID: {chunk_config.get('session_id', 'unknown')}")
        
        try:
            # Initialize state
            initial_state = TranscriptionState(
                session_id=chunk_config['session_id'],
                audio_chunk_id=chunk_config.get('audio_chunk_id', f"chunk_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"),
                audio_data=chunk_config['audio_data'],
                audio_format=chunk_config.get('audio_format', 'mp3'),
                audio_file_path='',  # Will be set by convert_format
                processing_status='pending',
                chunk_size=0,
                chunk_duration=0.0,
                raw_transcription='',
                cleaned_transcription='',
                speaker_detected='',
                confidence_score=0.0,
                language_detected='en',
                interview_id=chunk_config.get('interview_id', ''),
                question_context=chunk_config.get('question_context', ''),
                previous_transcripts=chunk_config.get('previous_transcripts', []),
                sentiment='neutral',
                key_points=[],
                technical_terms=[],
                errors=[],
                last_error='',
                retry_count=0,
                max_retries=3,
                received_at='',
                transcribed_at='',
                analyzed_at=''
            )
            
            # Run workflow
            logger.info("Invoking LangGraph transcription workflow")
            final_state = self.workflow.invoke(initial_state)
            
            logger.info(f"Transcription workflow completed: {final_state['processing_status']}")
            
            return dict(final_state)
            
        except Exception as e:
            logger.error(f"Fatal error in transcribe_chunk: {str(e)}", exc_info=True)
            return {
                'audio_chunk_id': chunk_config.get('audio_chunk_id', 'unknown'),
                'processing_status': 'failed',
                'last_error': str(e),
                'errors': [{'timestamp': datetime.utcnow().isoformat(), 'error': str(e)}]
            }
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up old temporary audio files"""
        logger.info(f"Cleaning up temp audio files older than {max_age_hours} hours")
        
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            deleted_count = 0
            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} temporary files")
            
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {str(e)}", exc_info=True)


# Module-level function for easy import
async def transcribe_audio_chunk(chunk_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to transcribe an audio chunk
    
    Args:
        chunk_config: Chunk configuration
        
    Returns:
        Transcription result
    """
    agent = AudioTranscriptionAgent()
    return await agent.transcribe_chunk(chunk_config)


if __name__ == "__main__":
    # Test the agent
    import asyncio
    
    # This would normally be actual audio data
    test_config = {
        'session_id': 'test_session_001',
        'audio_chunk_id': 'chunk_001',
        'audio_data': b'dummy_audio_data',  # Would be real audio bytes
        'audio_format': 'webm',
        'interview_id': 'interview_001',
        'question_context': 'Tell me about your experience with Python'
    }
    
    result = asyncio.run(transcribe_audio_chunk(test_config))
    print(json.dumps({k: v for k, v in result.items() if k != 'audio_data'}, indent=2))
