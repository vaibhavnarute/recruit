"""
Distributed Real-time Orchestration Agent
Handles multiple concurrent interviews using Redis Streams
Enables horizontal scaling across multiple FastAPI workers
"""

import json
import logging
import uuid
import os
import sys
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.redis_stream_manager import RedisStreamManager, get_redis_stream_manager
from langgraph_agents.realtime_orchestrator_agent import RealtimeOrchestratorAgent

logger = logging.getLogger(__name__)


class DistributedOrchestratorAgent:
    """
    Distributed orchestration agent with Redis Streams
    
    Architecture:
    - Each session has its own Redis Stream
    - Consumer group ensures load balancing across workers
    - Multiple workers can handle different sessions concurrently
    - Automatic failover if worker dies (message claiming)
    
    Workflow:
    1. Client initiates session → Creates Redis Stream
    2. Audio arrives → Publishes to session stream
    3. Worker consumes → Processes through orchestrator
    4. Results published → Client receives via WebSocket/SSE
    """
    
    def __init__(self, redis_manager: Optional[RedisStreamManager] = None):
        """Initialize Distributed Orchestrator"""
        logger.info("🌐 Initializing DistributedOrchestratorAgent")
        
        # Redis Stream Manager (will be set in async init)
        self.redis_manager = redis_manager
        
        # Orchestrator instances pool (one per active session)
        self.orchestrators: Dict[str, RealtimeOrchestratorAgent] = {}
        
        # Active session tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Consumer tasks
        self.consumer_tasks: List[asyncio.Task] = []
        self.is_running = False
        
        logger.info("✅ DistributedOrchestratorAgent initialized")
    
    async def initialize(self):
        """Async initialization"""
        if self.redis_manager is None:
            self.redis_manager = await get_redis_stream_manager()
        
        logger.info("✅ DistributedOrchestratorAgent ready")
    
    async def start_session(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a new distributed orchestration session
        
        Args:
            config: Session configuration
            
        Returns:
            Session info with Redis stream details
        """
        try:
            logger.info("🎬 Starting distributed orchestration session")
            
            # Generate session ID if not provided
            session_id = config.get('session_id', f"session_{uuid.uuid4()}")
            config['session_id'] = session_id
            
            # Create orchestrator instance for this session
            orchestrator = RealtimeOrchestratorAgent()
            result = await orchestrator.start_orchestration(config)
            
            if result.get('success'):
                # Store orchestrator instance
                self.orchestrators[session_id] = orchestrator
                
                # Create Redis Stream and consumer group
                await self.redis_manager.create_consumer_group(session_id)
                
                # Track session
                self.active_sessions[session_id] = {
                    'orchestration_id': result['data']['orchestration_id'],
                    'interview_id': config.get('interview_id'),
                    'meeting_id': config.get('meeting_id'),
                    'created_at': datetime.utcnow().isoformat(),
                    'status': 'active',
                    'worker_id': self.redis_manager.consumer_id
                }
                
                # Start consumer for this session
                await self._start_session_consumer(session_id)
                
                logger.info(f"✅ Distributed session started: {session_id}")
                logger.info(f"   Worker: {self.redis_manager.consumer_id}")
                logger.info(f"   Stream: {self.redis_manager.get_stream_name(session_id)}")
                
                return {
                    'success': True,
                    'data': {
                        **result['data'],
                        'redis_stream': self.redis_manager.get_stream_name(session_id),
                        'worker_id': self.redis_manager.consumer_id,
                        'consumer_group': self.redis_manager.consumer_group
                    },
                    'message': 'Distributed orchestration session started'
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"❌ Error starting distributed session: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': {
                    'code': 'DISTRIBUTED_SESSION_START_FAILED',
                    'message': str(e)
                }
            }
    
    async def publish_audio_turn(
        self,
        session_id: str,
        audio_data: bytes,
        audio_format: str = 'webm'
    ) -> Dict[str, Any]:
        """
        Publish audio turn to Redis Stream for processing
        
        Args:
            session_id: Target session
            audio_data: Audio chunk bytes
            audio_format: Audio format
            
        Returns:
            Message publish status
        """
        try:
            # Encode audio data to base64 for JSON serialization
            import base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Publish to Redis Stream
            message_id = await self.redis_manager.publish_message(
                session_id=session_id,
                message_type='audio_turn',
                data={
                    'audio_data': audio_b64,
                    'audio_format': audio_format,
                    'timestamp': datetime.utcnow().isoformat()
                },
                priority=5
            )
            
            if message_id:
                logger.info(f"📤 Published audio turn to stream: {message_id}")
                return {
                    'success': True,
                    'data': {
                        'message_id': message_id,
                        'session_id': session_id,
                        'stream': self.redis_manager.get_stream_name(session_id)
                    },
                    'message': 'Audio turn published to processing queue'
                }
            else:
                raise Exception("Failed to publish message to Redis Stream")
                
        except Exception as e:
            logger.error(f"❌ Error publishing audio turn: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': {
                    'code': 'AUDIO_PUBLISH_FAILED',
                    'message': str(e)
                }
            }
    
    async def _start_session_consumer(self, session_id: str):
        """Start consumer task for a specific session"""
        try:
            # Create handler for this session
            async def handle_message(message: Dict[str, Any]):
                await self._process_message(session_id, message)
            
            # Start consumer task
            task = asyncio.create_task(
                self.redis_manager.consume_session_messages(
                    session_id=session_id,
                    handler=handle_message,
                    block_ms=5000,
                    count=1
                )
            )
            
            self.consumer_tasks.append(task)
            logger.info(f"👂 Started consumer for session: {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Error starting session consumer: {str(e)}", exc_info=True)
    
    async def _process_message(self, session_id: str, message: Dict[str, Any]):
        """
        Process message from Redis Stream
        
        Args:
            session_id: Session ID
            message: Message data from stream
        """
        try:
            message_type = message['type']
            data = message['data']
            message_id = message['message_id']
            
            logger.info(f"🔄 Processing message: {message_id}")
            logger.info(f"   Type: {message_type}")
            logger.info(f"   Session: {session_id}")
            
            # Route based on message type
            if message_type == 'audio_turn':
                await self._process_audio_turn(session_id, data, message_id)
            
            elif message_type == 'audio_response':
                # Response from processing - log for monitoring/metrics
                await self._process_audio_response(session_id, data, message_id)
            
            elif message_type == 'control':
                await self._process_control_message(session_id, data)
            
            elif message_type == 'end_session':
                await self._process_end_session(session_id, data)
            
            else:
                logger.warning(f"⚠️ Unknown message type: {message_type}")
            
        except Exception as e:
            logger.error(f"❌ Error processing message: {str(e)}", exc_info=True)
    
    async def _process_audio_turn(
        self,
        session_id: str,
        data: Dict[str, Any],
        message_id: str
    ):
        """Process audio turn through orchestrator"""
        try:
            # Get orchestrator for this session
            orchestrator = self.orchestrators.get(session_id)
            
            if not orchestrator:
                logger.warning(f"⚠️ No orchestrator found for session: {session_id}")
                logger.info("🔄 Creating new orchestrator instance...")
                orchestrator = RealtimeOrchestratorAgent()
                self.orchestrators[session_id] = orchestrator
            
            # Decode audio data
            import base64
            audio_data = base64.b64decode(data['audio_data'])
            audio_format = data.get('audio_format', 'webm')
            
            logger.info(f"🎤 Processing audio turn for session: {session_id}")
            logger.info(f"   Audio size: {len(audio_data)} bytes")
            logger.info(f"   Format: {audio_format}")
            
            # Process through orchestrator
            result = await orchestrator.process_audio_turn(
                session_id=session_id,
                audio_data=audio_data,
                audio_format=audio_format
            )
            
            # Publish result back to stream (for client consumption)
            if result.get('success'):
                await self.redis_manager.publish_message(
                    session_id=session_id,
                    message_type='audio_response',
                    data={
                        'turn': result['data']['turn'],
                        'transcription': result['data']['transcription'],
                        'ai_response': result['data']['ai_response'],
                        'audio_url': result['data']['audio_url'],
                        'latency': result['data']['latency'],
                        'next_action': result['data']['next_action']
                    },
                    priority=1  # High priority for responses
                )
                
                logger.info(f"✅ Audio turn processed successfully")
                logger.info(f"   Turn: {result['data']['turn']}")
                logger.info(f"   Latency: {result['data']['latency']['total_ms']}ms")
            else:
                logger.error(f"❌ Audio turn processing failed: {result.get('error')}")
                
                # Publish error
                await self.redis_manager.publish_message(
                    session_id=session_id,
                    message_type='error',
                    data={
                        'error': result.get('error'),
                        'message_id': message_id
                    },
                    priority=1
                )
            
        except Exception as e:
            logger.error(f"❌ Error processing audio turn: {str(e)}", exc_info=True)
    
    async def _process_audio_response(
        self,
        session_id: str,
        data: Dict[str, Any],
        message_id: str
    ):
        """
        Process audio response message (sent back after processing)
        
        This handler tracks response delivery and can be used for:
        - Monitoring response delivery time
        - Tracking successful responses
        - Collecting metrics for quality monitoring
        - Client notification (WebSocket/SSE integration)
        """
        try:
            turn = data.get('turn', 0)
            latency = data.get('latency', {}).get('total_ms', 0)
            
            logger.info(f"✅ Audio response delivered for session: {session_id}")
            logger.info(f"   Turn: {turn}")
            logger.info(f"   Message ID: {message_id}")
            logger.info(f"   Processing latency: {latency}ms")
            
            # Update session metrics
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                
                # Track response delivery
                if 'response_metrics' not in session:
                    session['response_metrics'] = {
                        'total_responses': 0,
                        'total_latency': 0,
                        'avg_latency': 0
                    }
                
                metrics = session['response_metrics']
                metrics['total_responses'] += 1
                metrics['total_latency'] += latency
                metrics['avg_latency'] = metrics['total_latency'] / metrics['total_responses']
                
                logger.debug(f"📊 Session metrics updated:")
                logger.debug(f"   Total responses: {metrics['total_responses']}")
                logger.debug(f"   Avg latency: {metrics['avg_latency']:.2f}ms")
            
            # TODO: Implement WebSocket/SSE notification to client here
            # await self.notify_client(session_id, data)
            
        except Exception as e:
            logger.error(f"❌ Error processing audio response: {str(e)}", exc_info=True)
    
    async def _process_control_message(self, session_id: str, data: Dict[str, Any]):
        """Process control message (pause, resume, etc.)"""
        try:
            action = data.get('action')
            logger.info(f"🎮 Control message: {action} for session {session_id}")
            
            # Handle control actions
            if action == 'pause':
                # Pause session processing
                if session_id in self.active_sessions:
                    self.active_sessions[session_id]['status'] = 'paused'
            
            elif action == 'resume':
                # Resume session processing
                if session_id in self.active_sessions:
                    self.active_sessions[session_id]['status'] = 'active'
            
            elif action == 'cancel':
                # Cancel session
                await self.end_session(session_id)
            
        except Exception as e:
            logger.error(f"❌ Error processing control message: {str(e)}", exc_info=True)
    
    async def _process_end_session(self, session_id: str, data: Dict[str, Any]):
        """Process session end message"""
        try:
            logger.info(f"🏁 Ending session: {session_id}")
            await self.end_session(session_id)
        except Exception as e:
            logger.error(f"❌ Error processing end session: {str(e)}", exc_info=True)
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """
        End distributed orchestration session
        
        Args:
            session_id: Session to end
            
        Returns:
            Session summary
        """
        try:
            logger.info(f"🏁 Ending distributed session: {session_id}")
            
            # Get orchestrator
            orchestrator = self.orchestrators.get(session_id)
            
            if orchestrator:
                # End orchestration
                result = await orchestrator.end_orchestration(session_id)
                
                # Close orchestrator
                orchestrator.close()
                
                # Remove from pool
                del self.orchestrators[session_id]
            else:
                result = {
                    'success': True,
                    'data': {'session_id': session_id},
                    'message': 'Session not found in this worker'
                }
            
            # Remove from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            # Delete Redis Stream
            await self.redis_manager.delete_session_stream(session_id)
            
            logger.info(f"✅ Distributed session ended: {session_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error ending distributed session: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': {
                    'code': 'DISTRIBUTED_SESSION_END_FAILED',
                    'message': str(e)
                }
            }
    
    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active sessions in this worker"""
        return [
            {
                'session_id': sid,
                **info
            }
            for sid, info in self.active_sessions.items()
        ]
    
    async def claim_stuck_messages(self, session_id: str) -> int:
        """
        Claim stuck messages from dead workers
        
        Args:
            session_id: Session to check
            
        Returns:
            Number of messages claimed
        """
        try:
            claimed = await self.redis_manager.claim_pending_messages(
                session_id=session_id,
                min_idle_time_ms=60000  # 60 seconds
            )
            
            if claimed:
                logger.info(f"🔄 Claimed {len(claimed)} stuck messages for session {session_id}")
                
                # Process claimed messages
                for message in claimed:
                    message_id, message_data = message
                    await self._process_message(session_id, {
                        'message_id': message_id,
                        'type': message_data.get('type'),
                        'session_id': session_id,
                        'data': json.loads(message_data.get('data', '{}')),
                        'timestamp': message_data.get('timestamp')
                    })
            
            return len(claimed)
            
        except Exception as e:
            logger.error(f"❌ Error claiming stuck messages: {str(e)}", exc_info=True)
            return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of distributed orchestrator"""
        try:
            # Check Redis health
            redis_health = await self.redis_manager.health_check()
            
            # Get session stats
            session_count = len(self.active_sessions)
            orchestrator_count = len(self.orchestrators)
            
            return {
                'status': 'healthy' if redis_health['status'] == 'healthy' else 'degraded',
                'worker_id': self.redis_manager.consumer_id,
                'redis': redis_health,
                'sessions': {
                    'active': session_count,
                    'orchestrators': orchestrator_count,
                    'consumer_tasks': len(self.consumer_tasks)
                },
                'active_sessions': list(self.active_sessions.keys())
            }
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {str(e)}", exc_info=True)
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down distributed orchestrator...")
        
        # Stop all consumers
        await self.redis_manager.stop_consuming()
        
        # End all sessions
        for session_id in list(self.active_sessions.keys()):
            await self.end_session(session_id)
        
        # Cancel consumer tasks
        for task in self.consumer_tasks:
            if not task.done():
                task.cancel()
        
        logger.info("✅ Distributed orchestrator shut down")


# Global instance (one per worker process)
_distributed_orchestrator: Optional[DistributedOrchestratorAgent] = None


async def get_distributed_orchestrator() -> DistributedOrchestratorAgent:
    """Get or create singleton DistributedOrchestratorAgent"""
    global _distributed_orchestrator
    
    if _distributed_orchestrator is None:
        _distributed_orchestrator = DistributedOrchestratorAgent()
        await _distributed_orchestrator.initialize()
    
    return _distributed_orchestrator


async def cleanup_distributed_orchestrator():
    """Cleanup singleton instance"""
    global _distributed_orchestrator
    
    if _distributed_orchestrator is not None:
        await _distributed_orchestrator.shutdown()
        _distributed_orchestrator = None


if __name__ == "__main__":
    # Test distributed orchestrator
    async def test():
        print("=" * 80)
        print("Testing Distributed Orchestrator")
        print("=" * 80)
        
        # Initialize
        orchestrator = await get_distributed_orchestrator()
        
        # Health check
        health = await orchestrator.health_check()
        print(f"\n✅ Health: {json.dumps(health, indent=2)}")
        
        # Start session
        config = {
            'interview_id': 'test_interview_123',
            'meeting_id': 'test_meeting_456',
            'candidate_name': 'John Doe',
            'job_title': 'Python Developer'
        }
        
        result = await orchestrator.start_session(config)
        print(f"\n✅ Session started: {json.dumps(result, indent=2)}")
        
        if result.get('success'):
            session_id = result['data']['session_id']
            
            # Simulate audio turn
            audio_data = b'fake_audio_data' * 100
            await orchestrator.publish_audio_turn(session_id, audio_data, 'webm')
            
            # Wait for processing
            await asyncio.sleep(2)
            
            # End session
            await orchestrator.end_session(session_id)
        
        # Cleanup
        await cleanup_distributed_orchestrator()
        
        print("\n✅ Test complete")
    
    asyncio.run(test())
