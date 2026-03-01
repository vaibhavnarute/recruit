"""
Redis Stream Manager for Distributed Orchestration
Handles session-specific message queues for horizontal scaling
Enables multiple FastAPI workers to handle concurrent interviews
"""

import json
import logging
import asyncio
import os
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError, ConnectionError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class RedisStreamManager:
    """
    Manages Redis Streams for distributed orchestration
    
    Features:
    - Session-specific channels (stream per session_id)
    - Consumer groups for horizontal scaling
    - Message acknowledgment and retry
    - Health monitoring and connection pooling
    - Automatic cleanup of completed sessions
    """
    
    def __init__(
        self,
        redis_host: str = None,
        redis_port: int = None,
        redis_password: str = None,
        redis_username: str = None,
        redis_db: int = 0,
        max_connections: int = 50,
        consumer_group: str = "orchestration_workers"
    ):
        """Initialize Redis Stream Manager"""
        logger.info("🔧 Initializing RedisStreamManager")
        
        # Redis configuration
        self.redis_host = redis_host or os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = redis_port or int(os.getenv('REDIS_PORT', 6379))
        self.redis_password = redis_password or os.getenv('REDIS_PASSWORD')
        self.redis_username = redis_username or os.getenv('REDIS_USERNAME')
        self.redis_db = redis_db or int(os.getenv('REDIS_DB', 0))
        
        # Connection pool configuration
        self.max_connections = max_connections
        self.consumer_group = consumer_group
        
        # Redis client (will be initialized in connect())
        self.redis_client: Optional[Redis] = None
        
        # Stream naming
        self.stream_prefix = "orchestration:session:"
        self.control_stream = "orchestration:control"
        
        # Message handlers registry
        self.message_handlers: Dict[str, Callable] = {}
        
        # Consumer state
        self.consumer_id: Optional[str] = None
        self.is_consuming = False
        self.consumer_tasks: List[asyncio.Task] = []
        
        logger.info(f"✅ RedisStreamManager configured")
        logger.info(f"   Host: {self.redis_host}:{self.redis_port}")
        logger.info(f"   Consumer Group: {self.consumer_group}")
    
    async def connect(self) -> bool:
        """Connect to Redis with connection pooling"""
        try:
            logger.info("🔌 Connecting to Redis...")
            
            # Create connection pool
            pool = redis.ConnectionPool(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                username=self.redis_username,
                db=self.redis_db,
                max_connections=self.max_connections,
                decode_responses=True,
                encoding='utf-8'
            )
            
            # Create Redis client
            self.redis_client = Redis(connection_pool=pool)
            
            # Test connection
            await self.redis_client.ping()
            
            # Generate unique consumer ID with process ID for multi-worker support
            import uuid
            import os
            process_id = os.getpid()
            random_suffix = uuid.uuid4().hex[:6]
            self.consumer_id = f"worker_pid{process_id}_{random_suffix}"
            
            logger.info(f"✅ Connected to Redis successfully")
            logger.info(f"   Consumer ID: {self.consumer_id}")
            logger.info(f"   Process ID: {process_id}")
            logger.info(f"   🔍 Multi-worker: Each process has unique consumer ID")
            
            return True
            
        except ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to Redis: {str(e)}", exc_info=True)
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            logger.info("🔌 Disconnecting from Redis...")
            
            # Stop consuming
            await self.stop_consuming()
            
            # Close connection
            await self.redis_client.close()
            await self.redis_client.connection_pool.disconnect()
            
            logger.info("✅ Disconnected from Redis")
    
    def get_stream_name(self, session_id: str) -> str:
        """Get Redis stream name for a session"""
        return f"{self.stream_prefix}{session_id}"
    
    async def create_consumer_group(self, session_id: str) -> bool:
        """
        Create consumer group for a session stream
        Idempotent - safe to call multiple times
        """
        try:
            stream_name = self.get_stream_name(session_id)
            
            # Try to create group (MKSTREAM creates stream if it doesn't exist)
            try:
                await self.redis_client.xgroup_create(
                    name=stream_name,
                    groupname=self.consumer_group,
                    id='0',
                    mkstream=True
                )
                logger.info(f"✅ Created consumer group for session: {session_id}")
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    # Group already exists - this is fine
                    logger.debug(f"Consumer group already exists for session: {session_id}")
                else:
                    raise
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating consumer group: {str(e)}", exc_info=True)
            return False
    
    async def publish_message(
        self,
        session_id: str,
        message_type: str,
        data: Dict[str, Any],
        priority: int = 5
    ) -> Optional[str]:
        """
        Publish message to session stream
        
        Args:
            session_id: Target session ID
            message_type: Type of message (audio_turn, control, etc.)
            data: Message payload
            priority: Priority (1-10, lower = higher priority)
            
        Returns:
            Message ID or None if failed
        """
        try:
            stream_name = self.get_stream_name(session_id)
            
            # Ensure consumer group exists
            await self.create_consumer_group(session_id)
            
            # Prepare message
            message = {
                'type': message_type,
                'session_id': session_id,
                'priority': priority,
                'timestamp': datetime.utcnow().isoformat(),
                'data': json.dumps(data)
            }
            
            # Add to stream
            message_id = await self.redis_client.xadd(
                name=stream_name,
                fields=message,
                maxlen=1000  # Keep last 1000 messages
            )
            
            logger.info(f"📤 Published message to session {session_id}")
            logger.info(f"   Type: {message_type}")
            logger.info(f"   Message ID: {message_id}")
            
            return message_id
            
        except Exception as e:
            logger.error(f"❌ Error publishing message: {str(e)}", exc_info=True)
            return None
    
    async def consume_session_messages(
        self,
        session_id: str,
        handler: Callable[[Dict[str, Any]], None],
        block_ms: int = 5000,
        count: int = 1
    ):
        """
        Consume messages from a specific session stream
        
        Args:
            session_id: Session to consume from
            handler: Async function to handle messages
            block_ms: Block timeout in milliseconds
            count: Number of messages to read per call
        """
        try:
            stream_name = self.get_stream_name(session_id)
            
            # Ensure consumer group exists
            await self.create_consumer_group(session_id)
            
            logger.info(f"👂 Starting consumer for session: {session_id}")
            self.is_consuming = True
            
            while self.is_consuming:
                try:
                    # Read messages from consumer group
                    messages = await self.redis_client.xreadgroup(
                        groupname=self.consumer_group,
                        consumername=self.consumer_id,
                        streams={stream_name: '>'},
                        count=count,
                        block=block_ms
                    )
                    
                    if not messages:
                        continue
                    
                    # Process messages
                    for stream, message_list in messages:
                        for message_id, message_data in message_list:
                            try:
                                # Parse message
                                message_type = message_data.get('type')
                                data = json.loads(message_data.get('data', '{}'))
                                
                                logger.info(f"📥 Received message: {message_id}")
                                logger.info(f"   Type: {message_type}")
                                logger.info(f"   Session: {session_id}")
                                
                                # Call handler
                                await handler({
                                    'message_id': message_id,
                                    'type': message_type,
                                    'session_id': session_id,
                                    'data': data,
                                    'timestamp': message_data.get('timestamp')
                                })
                                
                                # Acknowledge message
                                await self.redis_client.xack(
                                    stream_name,
                                    self.consumer_group,
                                    message_id
                                )
                                
                                logger.debug(f"✅ Acknowledged message: {message_id}")
                                
                            except Exception as e:
                                logger.error(f"❌ Error processing message {message_id}: {str(e)}", exc_info=True)
                                # Don't acknowledge - message will be redelivered
                
                except redis.ResponseError as e:
                    error_msg = str(e)
                    # NOGROUP errors are expected for cleaned-up or non-existent streams
                    if 'NOGROUP' in error_msg:
                        logger.debug(f"Stream or consumer group doesn't exist (session may be closed): {error_msg}")
                        await asyncio.sleep(5)  # Longer back off for non-existent streams
                    else:
                        logger.error(f"❌ Redis error in consumer: {error_msg}")
                        await asyncio.sleep(1)  # Back off on error
                
                except asyncio.CancelledError:
                    logger.info("🛑 Consumer task cancelled")
                    break
                    
        except Exception as e:
            logger.error(f"❌ Fatal error in consumer: {str(e)}", exc_info=True)
        finally:
            self.is_consuming = False
            logger.info(f"🛑 Stopped consumer for session: {session_id}")
    
    async def consume_multiple_sessions(
        self,
        session_ids: List[str],
        handler: Callable[[Dict[str, Any]], None],
        block_ms: int = 5000
    ):
        """
        Consume messages from multiple session streams concurrently
        
        Args:
            session_ids: List of session IDs to consume from
            handler: Async function to handle messages
            block_ms: Block timeout in milliseconds
        """
        try:
            # Create consumer groups for all sessions
            for session_id in session_ids:
                await self.create_consumer_group(session_id)
            
            # Build streams dict
            streams = {
                self.get_stream_name(sid): '>' for sid in session_ids
            }
            
            logger.info(f"👂 Starting multi-session consumer")
            logger.info(f"   Sessions: {len(session_ids)}")
            self.is_consuming = True
            
            while self.is_consuming:
                try:
                    # Read from multiple streams
                    messages = await self.redis_client.xreadgroup(
                        groupname=self.consumer_group,
                        consumername=self.consumer_id,
                        streams=streams,
                        count=10,
                        block=block_ms
                    )
                    
                    if not messages:
                        continue
                    
                    # Process messages from all streams
                    for stream_name, message_list in messages:
                        # Extract session_id from stream name
                        session_id = stream_name.replace(self.stream_prefix, '')
                        
                        for message_id, message_data in message_list:
                            try:
                                message_type = message_data.get('type')
                                data = json.loads(message_data.get('data', '{}'))
                                
                                logger.info(f"📥 Received message: {message_id} from {session_id}")
                                
                                # Call handler
                                await handler({
                                    'message_id': message_id,
                                    'type': message_type,
                                    'session_id': session_id,
                                    'data': data,
                                    'timestamp': message_data.get('timestamp')
                                })
                                
                                # Acknowledge
                                await self.redis_client.xack(
                                    stream_name,
                                    self.consumer_group,
                                    message_id
                                )
                                
                            except Exception as e:
                                logger.error(f"❌ Error processing message: {str(e)}", exc_info=True)
                
                except asyncio.CancelledError:
                    break
                except redis.ResponseError as e:
                    error_msg = str(e)
                    # NOGROUP errors are expected for cleaned-up or non-existent streams
                    if 'NOGROUP' in error_msg:
                        logger.debug(f"Stream or consumer group doesn't exist (session may be closed): {error_msg}")
                        await asyncio.sleep(5)  # Longer back off for non-existent streams
                    else:
                        logger.error(f"❌ Redis error in multi-consumer: {error_msg}")
                        await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"❌ Error in multi-consumer: {str(e)}")
                    await asyncio.sleep(1)
        
        finally:
            self.is_consuming = False
            logger.info("🛑 Stopped multi-session consumer")
    
    async def stop_consuming(self):
        """Stop all consumer tasks"""
        logger.info("🛑 Stopping all consumers...")
        self.is_consuming = False
        
        # Cancel all consumer tasks
        for task in self.consumer_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.consumer_tasks.clear()
        logger.info("✅ All consumers stopped")
    
    async def get_pending_messages(self, session_id: str) -> int:
        """Get count of pending messages for a session"""
        try:
            stream_name = self.get_stream_name(session_id)
            
            # Get pending messages info
            pending = await self.redis_client.xpending(
                name=stream_name,
                groupname=self.consumer_group
            )
            
            if pending:
                return pending['pending']
            return 0
            
        except Exception as e:
            logger.error(f"❌ Error getting pending messages: {str(e)}")
            return 0
    
    async def claim_pending_messages(
        self,
        session_id: str,
        min_idle_time_ms: int = 60000
    ) -> List[Dict[str, Any]]:
        """
        Claim messages that have been idle too long (worker died/stuck)
        
        Args:
            session_id: Session to claim from
            min_idle_time_ms: Minimum idle time before claiming (default 60s)
            
        Returns:
            List of claimed messages
        """
        try:
            stream_name = self.get_stream_name(session_id)
            
            # Get pending messages
            pending_info = await self.redis_client.xpending_range(
                name=stream_name,
                groupname=self.consumer_group,
                min='-',
                max='+',
                count=10
            )
            
            claimed = []
            
            for info in pending_info:
                message_id = info['message_id']
                idle_time = info['time_since_delivered']
                
                # Claim if idle too long
                if idle_time >= min_idle_time_ms:
                    claimed_msgs = await self.redis_client.xclaim(
                        name=stream_name,
                        groupname=self.consumer_group,
                        consumername=self.consumer_id,
                        min_idle_time=min_idle_time_ms,
                        message_ids=[message_id]
                    )
                    
                    if claimed_msgs:
                        logger.info(f"🔄 Claimed stuck message: {message_id}")
                        claimed.extend(claimed_msgs)
            
            return claimed
            
        except Exception as e:
            logger.error(f"❌ Error claiming pending messages: {str(e)}")
            return []
    
    async def delete_session_stream(self, session_id: str) -> bool:
        """Delete stream when session is completed"""
        try:
            stream_name = self.get_stream_name(session_id)
            
            # Delete stream
            await self.redis_client.delete(stream_name)
            
            logger.info(f"🗑️ Deleted stream for session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting stream: {str(e)}")
            return False
    
    async def get_stream_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a session stream"""
        try:
            stream_name = self.get_stream_name(session_id)
            
            # Get stream info
            info = await self.redis_client.xinfo_stream(stream_name)
            
            return {
                'length': info.get('length', 0),
                'first_entry': info.get('first-entry'),
                'last_entry': info.get('last-entry'),
                'groups': info.get('groups', 0)
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting stream info: {str(e)}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis connection health"""
        try:
            # Ping Redis
            response = await self.redis_client.ping()
            
            # Get info
            info = await self.redis_client.info('server')
            
            return {
                'status': 'healthy' if response else 'unhealthy',
                'connected': True,
                'redis_version': info.get('redis_version'),
                'uptime_seconds': info.get('uptime_in_seconds'),
                'consumer_id': self.consumer_id,
                'is_consuming': self.is_consuming
            }
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'connected': False,
                'error': str(e)
            }


# Singleton instance
_redis_stream_manager: Optional[RedisStreamManager] = None


async def get_redis_stream_manager() -> RedisStreamManager:
    """Get or create singleton RedisStreamManager instance"""
    global _redis_stream_manager
    
    if _redis_stream_manager is None:
        _redis_stream_manager = RedisStreamManager()
        await _redis_stream_manager.connect()
    
    return _redis_stream_manager


async def cleanup_redis_stream_manager():
    """Cleanup singleton instance"""
    global _redis_stream_manager
    
    if _redis_stream_manager is not None:
        await _redis_stream_manager.disconnect()
        _redis_stream_manager = None


if __name__ == "__main__":
    # Test Redis Stream Manager
    async def test_redis_streams():
        print("=" * 80)
        print("Testing Redis Stream Manager")
        print("=" * 80)
        
        # Initialize manager
        manager = RedisStreamManager()
        await manager.connect()
        
        # Test health
        health = await manager.health_check()
        print(f"\n✅ Health: {json.dumps(health, indent=2)}")
        
        # Test publish
        session_id = "test_session_123"
        message_id = await manager.publish_message(
            session_id=session_id,
            message_type="audio_turn",
            data={"audio_data": "base64...", "format": "webm"}
        )
        print(f"\n✅ Published message: {message_id}")
        
        # Test stream info
        info = await manager.get_stream_info(session_id)
        print(f"\n✅ Stream info: {json.dumps(info, indent=2)}")
        
        # Cleanup
        await manager.delete_session_stream(session_id)
        await manager.disconnect()
        
        print("\n✅ Test complete")
    
    asyncio.run(test_redis_streams())
