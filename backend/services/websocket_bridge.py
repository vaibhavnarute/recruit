"""
WebSocket Bridge Service
Bridges communication between Node.js Puppeteer bot and Python backend
Handles real-time audio chunk streaming and transcription
"""

import asyncio
import json
import logging
import base64
from typing import Dict, Any, Set
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph_agents.audio_transcription_agent import transcribe_audio_chunk
from repositories.meet_session_repository import MeetSessionRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebSocketBridge:
    """
    WebSocket server that bridges Node.js Puppeteer bot and Python backend
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        """
        Initialize WebSocket bridge
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.repository = MeetSessionRepository()
        
        logger.info(f"WebSocket Bridge initialized on {host}:{port}")
    
    async def register_client(self, websocket: WebSocketServerProtocol):
        """Register new WebSocket client"""
        self.clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"✅ Client connected: {client_id}")
        logger.info(f"   Total clients: {len(self.clients)}")
    
    async def unregister_client(self, websocket: WebSocketServerProtocol):
        """Unregister WebSocket client"""
        self.clients.discard(websocket)
        client_id = id(websocket)
        logger.info(f"❌ Client disconnected: {client_id}")
        logger.info(f"   Total clients: {len(self.clients)}")
    
    async def send_to_client(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]):
        """Send message to specific client"""
        try:
            await websocket.send(json.dumps(message))
            logger.debug(f"📤 Sent message to client: {message.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"❌ Error sending message to client: {str(e)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if self.clients:
            await asyncio.gather(
                *[self.send_to_client(client, message) for client in self.clients],
                return_exceptions=True
            )
            logger.debug(f"📡 Broadcast message to {len(self.clients)} clients")
    
    async def handle_audio_chunk(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]):
        """
        Handle incoming audio chunk from Puppeteer bot
        
        Args:
            websocket: WebSocket connection
            message: Audio chunk message
        """
        try:
            session_id = message.get('sessionId')
            chunk_id = message.get('chunkId')
            audio_data_base64 = message.get('audioData')
            audio_format = message.get('format', 'webm')
            chunk_size = message.get('size', 0)
            
            logger.info(f"🎤 Received audio chunk: {chunk_id}")
            logger.info(f"   Session: {session_id}")
            logger.info(f"   Size: {chunk_size} bytes")
            logger.info(f"   Format: {audio_format}")
            
            if not audio_data_base64:
                logger.warning(f"⚠️ Empty audio data for chunk: {chunk_id}")
                await self.send_to_client(websocket, {
                    'type': 'error',
                    'error': 'Empty audio data',
                    'chunkId': chunk_id
                })
                return
            
            # Decode base64 audio data
            try:
                audio_bytes = base64.b64decode(audio_data_base64)
                logger.debug(f"✅ Decoded audio data: {len(audio_bytes)} bytes")
            except Exception as decode_error:
                logger.error(f"❌ Error decoding audio data: {str(decode_error)}")
                await self.send_to_client(websocket, {
                    'type': 'error',
                    'error': f'Failed to decode audio: {str(decode_error)}',
                    'chunkId': chunk_id
                })
                return
            
            # Save audio chunk metadata to MongoDB
            self.repository.save_audio_chunk_metadata({
                'chunk_id': chunk_id,
                'session_id': session_id,
                'chunk_size': len(audio_bytes),
                'audio_format': audio_format,
                'processing_status': 'received'
            })
            
            # Send acknowledgment
            await self.send_to_client(websocket, {
                'type': 'acknowledgment',
                'chunkId': chunk_id,
                'message': 'Audio chunk received'
            })
            
            # Process audio chunk asynchronously (transcription)
            asyncio.create_task(
                self.process_audio_transcription(session_id, chunk_id, audio_bytes, audio_format)
            )
            
        except Exception as e:
            logger.error(f"❌ Error handling audio chunk: {str(e)}", exc_info=True)
            await self.send_to_client(websocket, {
                'type': 'error',
                'error': str(e),
                'chunkId': message.get('chunkId', 'unknown')
            })
    
    async def process_audio_transcription(
        self,
        session_id: str,
        chunk_id: str,
        audio_data: bytes,
        audio_format: str
    ):
        """
        Process audio transcription using LangGraph agent
        
        Args:
            session_id: Session identifier
            chunk_id: Audio chunk identifier
            audio_data: Raw audio bytes
            audio_format: Audio format (webm, wav, etc.)
        """
        try:
            logger.info(f"🔄 Starting transcription for chunk: {chunk_id}")
            
            # Get session info
            session = self.repository.get_session(session_id)
            if not session:
                logger.error(f"❌ Session not found: {session_id}")
                return
            
            # Prepare chunk configuration
            chunk_config = {
                'session_id': session_id,
                'audio_chunk_id': chunk_id,
                'audio_data': audio_data,
                'audio_format': audio_format,
                'interview_id': session.get('interview_id', ''),
                'question_context': session.get('metadata', {}).get('current_question', ''),
                'previous_transcripts': []
            }
            
            # Call transcription agent
            logger.info(f"🤖 Invoking audio transcription agent for: {chunk_id}")
            result = await transcribe_audio_chunk(chunk_config)
            
            logger.info(f"✅ Transcription completed for chunk: {chunk_id}")
            logger.info(f"   Status: {result.get('processing_status')}")
            logger.info(f"   Confidence: {result.get('confidence_score', 0.0):.2f}")
            
            # Save transcript to MongoDB
            if result.get('processing_status') == 'completed' and result.get('cleaned_transcription'):
                transcript_doc = self.repository.save_transcript({
                    'chunk_id': chunk_id,
                    'session_id': session_id,
                    'interview_id': session.get('interview_id', ''),
                    'raw_transcription': result.get('raw_transcription', ''),
                    'cleaned_transcription': result.get('cleaned_transcription', ''),
                    'confidence_score': result.get('confidence_score', 0.0),
                    'language_detected': result.get('language_detected', 'en'),
                    'speaker_detected': result.get('speaker_detected', ''),
                    'sentiment': result.get('sentiment', 'neutral'),
                    'key_points': result.get('key_points', []),
                    'technical_terms': result.get('technical_terms', []),
                    'chunk_duration': result.get('chunk_duration', 0.0)
                })
                
                logger.info(f"💾 Transcript saved to database: {chunk_id}")
                
                # Broadcast transcription result to all clients
                await self.broadcast({
                    'type': 'transcription_completed',
                    'sessionId': session_id,
                    'chunkId': chunk_id,
                    'transcription': result.get('cleaned_transcription', ''),
                    'confidence': result.get('confidence_score', 0.0),
                    'sentiment': result.get('sentiment', 'neutral'),
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                logger.warning(f"⚠️ Transcription failed or empty for chunk: {chunk_id}")
                
                # Log error to session
                self.repository.add_session_error(session_id, {
                    'stage': 'transcription',
                    'error': result.get('last_error', 'Transcription failed'),
                    'details': {'chunk_id': chunk_id}
                })
            
        except Exception as e:
            logger.error(f"❌ Error processing transcription: {str(e)}", exc_info=True)
            
            # Log error to session
            self.repository.add_session_error(session_id, {
                'stage': 'transcription_processing',
                'error': str(e),
                'details': {'chunk_id': chunk_id}
            })
    
    async def handle_event(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]):
        """
        Handle event messages from Puppeteer bot
        
        Args:
            websocket: WebSocket connection
            message: Event message
        """
        try:
            event_type = message.get('event')
            session_id = message.get('sessionId')
            
            logger.info(f"📨 Received event: {event_type}")
            logger.info(f"   Session: {session_id}")
            
            # Update session based on event
            if event_type == 'session_started':
                self.repository.update_session(session_id, {
                    'session_status': 'recording',
                    'started_at': datetime.utcnow()
                })
                logger.info(f"✅ Session started: {session_id}")
                
            elif event_type == 'session_stopped':
                self.repository.update_session(session_id, {
                    'session_status': 'completed',
                    'ended_at': datetime.utcnow()
                })
                logger.info(f"✅ Session stopped: {session_id}")
                
            elif event_type == 'session_failed':
                error = message.get('error', 'Unknown error')
                self.repository.update_session(session_id, {
                    'session_status': 'failed',
                    'ended_at': datetime.utcnow()
                })
                self.repository.add_session_error(session_id, {
                    'stage': 'session_lifecycle',
                    'error': error
                })
                logger.error(f"❌ Session failed: {session_id} - {error}")
            
            # Broadcast event to all clients
            await self.broadcast(message)
            
        except Exception as e:
            logger.error(f"❌ Error handling event: {str(e)}", exc_info=True)
    
    async def handle_message(self, websocket: WebSocketServerProtocol, message_str: str):
        """
        Handle incoming WebSocket message
        
        Args:
            websocket: WebSocket connection
            message_str: Raw message string
        """
        try:
            message = json.loads(message_str)
            message_type = message.get('type')
            
            logger.debug(f"📥 Received message type: {message_type}")
            
            if message_type == 'audio_chunk':
                await self.handle_audio_chunk(websocket, message)
                
            elif message_type == 'event':
                await self.handle_event(websocket, message)
                
            elif message_type == 'ping':
                await self.send_to_client(websocket, {'type': 'pong'})
                
            else:
                logger.warning(f"⚠️ Unknown message type: {message_type}")
                await self.send_to_client(websocket, {
                    'type': 'error',
                    'error': f'Unknown message type: {message_type}'
                })
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON message: {str(e)}")
            await self.send_to_client(websocket, {
                'type': 'error',
                'error': f'Invalid JSON: {str(e)}'
            })
            
        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}", exc_info=True)
            await self.send_to_client(websocket, {
                'type': 'error',
                'error': str(e)
            })
    
    async def handler(self, websocket: WebSocketServerProtocol, path: str):
        """
        Main WebSocket connection handler
        
        Args:
            websocket: WebSocket connection
            path: Connection path
        """
        await self.register_client(websocket)
        
        try:
            # Send welcome message
            await self.send_to_client(websocket, {
                'type': 'connected',
                'message': 'Welcome to Meet Bot WebSocket Bridge',
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Handle messages
            async for message in websocket:
                await self.handle_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosedOK:
            logger.info("🔌 Connection closed normally")
            
        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(f"❌ Connection closed with error: {str(e)}")
            
        except Exception as e:
            logger.error(f"❌ Error in WebSocket handler: {str(e)}", exc_info=True)
            
        finally:
            await self.unregister_client(websocket)
    
    async def start(self):
        """Start WebSocket server"""
        logger.info(f"🚀 Starting WebSocket Bridge on {self.host}:{self.port}")
        
        async with websockets.serve(self.handler, self.host, self.port):
            logger.info(f"✅ WebSocket Bridge running on ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever
    
    def run(self):
        """Run WebSocket server (blocking)"""
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            logger.info("⚠️ WebSocket Bridge stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error in WebSocket Bridge: {str(e)}", exc_info=True)


# Main entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Meet Bot WebSocket Bridge')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8765, help='Port to listen on')
    
    args = parser.parse_args()
    
    bridge = WebSocketBridge(host=args.host, port=args.port)
    bridge.run()
