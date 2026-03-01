"""
Real-Time Audio Streaming WebSocket
====================================
WebSocket server for streaming audio between Meet Bot and STT service.

Features:
1. Receive audio chunks from Meet Bot
2. Send to STT for transcription
3. Return transcribed text in real-time
4. Handle multiple concurrent interviews
"""

import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import base64

logger = logging.getLogger(__name__)


class AudioStreamManager:
    """Manages real-time audio streaming for interviews"""
    
    def __init__(self):
        # Active WebSocket connections: interview_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Audio buffers: interview_id -> audio chunks
        self.audio_buffers: Dict[str, list] = {}
        
        # Interview states
        self.interview_states: Dict[str, Dict] = {}
        
    async def connect(self, websocket: WebSocket, interview_id: str):
        """
        Connect a new WebSocket for an interview
        
        Args:
            websocket: WebSocket connection
            interview_id: Interview ID
        """
        await websocket.accept()
        self.active_connections[interview_id] = websocket
        self.audio_buffers[interview_id] = []
        self.interview_states[interview_id] = {
            "connected_at": datetime.now().isoformat(),
            "status": "connected",
            "chunks_received": 0,
            "transcriptions": 0
        }
        
        logger.info(f"✅ WebSocket connected for interview: {interview_id}")
        
        # Send confirmation
        await self.send_message(interview_id, {
            "type": "connection_established",
            "interview_id": interview_id,
            "timestamp": datetime.now().isoformat()
        })
    
    def disconnect(self, interview_id: str):
        """Disconnect WebSocket for an interview"""
        if interview_id in self.active_connections:
            del self.active_connections[interview_id]
        if interview_id in self.audio_buffers:
            del self.audio_buffers[interview_id]
        if interview_id in self.interview_states:
            del self.interview_states[interview_id]
        
        logger.info(f"🔌 WebSocket disconnected for interview: {interview_id}")
    
    async def send_message(self, interview_id: str, message: Dict):
        """Send message to WebSocket"""
        if interview_id in self.active_connections:
            try:
                await self.active_connections[interview_id].send_json(message)
            except Exception as e:
                logger.error(f"❌ Error sending message: {str(e)}")
    
    async def process_audio_chunk(self, interview_id: str, audio_data: bytes) -> str:
        """
        Process audio chunk and return transcription
        
        Args:
            interview_id: Interview ID
            audio_data: Raw audio bytes
            
        Returns:
            Transcribed text
        """
        # Store chunk
        self.audio_buffers[interview_id].append(audio_data)
        self.interview_states[interview_id]["chunks_received"] += 1
        
        logger.info(f"🎤 Received audio chunk for interview {interview_id} (size: {len(audio_data)} bytes)")
        
        # TODO: Send to STT service (Deepgram/AssemblyAI)
        # For now, return placeholder
        from langgraph_agents.audio_transcription_agent import AudioTranscriptionAgent
        
        try:
            # Initialize STT agent
            stt_agent = AudioTranscriptionAgent()
            
            # Transcribe audio using the correct method
            result = await stt_agent.transcribe_chunk({
                'session_id': interview_id,
                'audio_data': audio_data,
                'audio_format': 'wav',
                'audio_chunk_id': f"chunk_{self.interview_states[interview_id]['chunks_received']}"
            })
            
            if result and result.get("transcription"):
                transcription = result["transcription"]
                self.interview_states[interview_id]["transcriptions"] += 1
                
                logger.info(f"✅ Transcription: {transcription[:100]}...")
                return transcription
            else:
                logger.warning(f"⚠️ No transcription returned")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Error transcribing audio: {str(e)}")
            return ""
    
    def get_stats(self, interview_id: str) -> Dict:
        """Get streaming statistics for an interview"""
        if interview_id in self.interview_states:
            return self.interview_states[interview_id]
        return {}


# Global manager instance
audio_stream_manager = AudioStreamManager()


async def handle_audio_websocket(websocket: WebSocket, interview_id: str):
    """
    WebSocket endpoint handler for audio streaming
    
    Args:
        websocket: WebSocket connection
        interview_id: Interview ID
    """
    try:
        # Connect
        await audio_stream_manager.connect(websocket, interview_id)
        
        # Listen for audio chunks
        while True:
            try:
                # Receive message
                data = await websocket.receive()
                
                if "bytes" in data:
                    # Binary audio data
                    audio_bytes = data["bytes"]
                    
                    # Process audio and get transcription
                    transcription = await audio_stream_manager.process_audio_chunk(
                        interview_id, audio_bytes
                    )
                    
                    # Send transcription back
                    await audio_stream_manager.send_message(interview_id, {
                        "type": "transcription",
                        "text": transcription,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                elif "text" in data:
                    # Text message (control commands)
                    message = json.loads(data["text"])
                    message_type = message.get("type")
                    
                    if message_type == "ping":
                        # Respond to ping
                        await audio_stream_manager.send_message(interview_id, {
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    elif message_type == "get_stats":
                        # Send statistics
                        stats = audio_stream_manager.get_stats(interview_id)
                        await audio_stream_manager.send_message(interview_id, {
                            "type": "stats",
                            "data": stats,
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    elif message_type == "stop_streaming":
                        # Stop streaming
                        logger.info(f"🛑 Stopping stream for interview: {interview_id}")
                        break
                
            except WebSocketDisconnect:
                logger.info(f"🔌 Client disconnected: {interview_id}")
                break
            except Exception as e:
                logger.error(f"❌ Error handling message: {str(e)}")
                break
        
    except Exception as e:
        logger.error(f"❌ WebSocket error: {str(e)}")
    
    finally:
        # Cleanup
        audio_stream_manager.disconnect(interview_id)
