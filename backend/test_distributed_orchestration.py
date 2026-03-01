"""
Test script for Distributed Orchestration with Redis Streams
Tests session management, message publishing, and worker load balancing
"""

import asyncio
import json
import logging
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp.redis_stream_manager import RedisStreamManager
from langgraph_agents.distributed_orchestrator_agent import DistributedOrchestratorAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_redis_connection():
    """Test 1: Redis Connection"""
    print("\n" + "="*80)
    print("TEST 1: Redis Connection & Health Check")
    print("="*80)
    
    try:
        manager = RedisStreamManager()
        connected = await manager.connect()
        
        if not connected:
            print("❌ FAILED: Could not connect to Redis")
            print("   Make sure Redis is running: redis-server")
            return False
        
        print(f"✅ Connected to Redis")
        print(f"   Consumer ID: {manager.consumer_id}")
        
        # Health check
        health = await manager.health_check()
        print(f"\n📊 Health Status:")
        print(f"   Status: {health['status']}")
        print(f"   Redis Version: {health.get('redis_version')}")
        print(f"   Uptime: {health.get('uptime_seconds')}s")
        
        await manager.disconnect()
        print("\n✅ TEST 1 PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {str(e)}")
        return False


async def test_stream_operations():
    """Test 2: Stream Create, Publish, Consume"""
    print("\n" + "="*80)
    print("TEST 2: Stream Operations (Create, Publish, Consume)")
    print("="*80)
    
    try:
        manager = RedisStreamManager()
        await manager.connect()
        
        session_id = "test_session_001"
        
        # Create consumer group
        print(f"\n📝 Creating consumer group for session: {session_id}")
        await manager.create_consumer_group(session_id)
        print(f"✅ Consumer group created")
        
        # Publish messages
        print(f"\n📤 Publishing test messages...")
        for i in range(3):
            message_id = await manager.publish_message(
                session_id=session_id,
                message_type="test_message",
                data={"test_id": i, "timestamp": datetime.utcnow().isoformat()},
                priority=5
            )
            print(f"   Message {i+1}: {message_id}")
        
        # Get stream info
        info = await manager.get_stream_info(session_id)
        print(f"\n📊 Stream Info:")
        print(f"   Length: {info.get('length')} messages")
        print(f"   Groups: {info.get('groups')}")
        
        # Consume messages
        print(f"\n📥 Consuming messages...")
        consumed_count = 0
        
        async def message_handler(message):
            nonlocal consumed_count
            consumed_count += 1
            print(f"   Received: {message['type']} (ID: {message['message_id']})")
        
        # Start consumer task
        consumer_task = asyncio.create_task(
            manager.consume_session_messages(
                session_id=session_id,
                handler=message_handler,
                block_ms=1000,
                count=1
            )
        )
        
        # Wait for messages to be consumed
        await asyncio.sleep(3)
        
        # Stop consumer
        await manager.stop_consuming()
        await consumer_task
        
        print(f"\n✅ Consumed {consumed_count}/3 messages")
        
        # Cleanup
        await manager.delete_session_stream(session_id)
        print(f"🗑️ Stream deleted")
        
        await manager.disconnect()
        
        if consumed_count == 3:
            print("\n✅ TEST 2 PASSED")
            return True
        else:
            print(f"\n⚠️ TEST 2 PARTIAL: Only consumed {consumed_count}/3 messages")
            return False
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_distributed_orchestrator():
    """Test 3: Distributed Orchestrator Agent"""
    print("\n" + "="*80)
    print("TEST 3: Distributed Orchestrator Agent")
    print("="*80)
    
    try:
        # Initialize orchestrator
        print("\n🎭 Initializing Distributed Orchestrator...")
        orchestrator = DistributedOrchestratorAgent()
        await orchestrator.initialize()
        print(f"✅ Orchestrator initialized")
        print(f"   Worker ID: {orchestrator.redis_manager.consumer_id}")
        
        # Start session
        print(f"\n🎬 Starting orchestration session...")
        config = {
            'interview_id': 'test_interview_001',
            'meeting_id': 'test_meeting_001',
            'candidate_name': 'Test Candidate',
            'job_title': 'Software Engineer',
            'audio_format': 'webm'
        }
        
        result = await orchestrator.start_session(config)
        
        if not result.get('success'):
            print(f"❌ Failed to start session: {result.get('error')}")
            return False
        
        session_id = result['data']['session_id']
        print(f"✅ Session started")
        print(f"   Session ID: {session_id}")
        print(f"   Orchestration ID: {result['data']['orchestration_id']}")
        print(f"   Redis Stream: {result['data']['redis_stream']}")
        
        # Publish audio turn
        print(f"\n📤 Publishing audio turn...")
        audio_data = b"fake_audio_data" * 1000  # 15KB fake audio
        
        publish_result = await orchestrator.publish_audio_turn(
            session_id=session_id,
            audio_data=audio_data,
            audio_format='webm'
        )
        
        if not publish_result.get('success'):
            print(f"❌ Failed to publish audio: {publish_result.get('error')}")
            return False
        
        print(f"✅ Audio published")
        print(f"   Message ID: {publish_result['data']['message_id']}")
        
        # Wait for processing
        print(f"\n⏳ Waiting for processing (5 seconds)...")
        await asyncio.sleep(5)
        
        # Get active sessions
        print(f"\n📊 Getting active sessions...")
        sessions = await orchestrator.get_active_sessions()
        print(f"✅ Active sessions: {len(sessions)}")
        for session in sessions:
            print(f"   - {session['session_id']} ({session['status']})")
        
        # Health check
        print(f"\n🏥 Health check...")
        health = await orchestrator.health_check()
        print(f"✅ Status: {health['status']}")
        print(f"   Active sessions: {health['sessions']['active']}")
        print(f"   Orchestrators: {health['sessions']['orchestrators']}")
        
        # End session
        print(f"\n🏁 Ending session...")
        end_result = await orchestrator.end_session(session_id)
        
        if end_result.get('success'):
            print(f"✅ Session ended")
            if 'data' in end_result and 'total_turns' in end_result['data']:
                print(f"   Total turns: {end_result['data'].get('total_turns', 0)}")
        
        # Shutdown orchestrator
        await orchestrator.shutdown()
        print(f"🛑 Orchestrator shut down")
        
        print("\n✅ TEST 3 PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_multi_session_concurrency():
    """Test 4: Multiple Concurrent Sessions"""
    print("\n" + "="*80)
    print("TEST 4: Multiple Concurrent Sessions")
    print("="*80)
    
    try:
        orchestrator = DistributedOrchestratorAgent()
        await orchestrator.initialize()
        
        print(f"\n🎬 Starting 3 concurrent sessions...")
        
        sessions = []
        
        # Start 3 sessions concurrently
        for i in range(3):
            config = {
                'interview_id': f'test_interview_{i+1}',
                'candidate_name': f'Candidate {i+1}',
                'job_title': 'Software Engineer'
            }
            
            result = await orchestrator.start_session(config)
            
            if result.get('success'):
                session_id = result['data']['session_id']
                sessions.append(session_id)
                print(f"✅ Session {i+1} started: {session_id}")
        
        if len(sessions) != 3:
            print(f"❌ Failed to start all sessions")
            return False
        
        # Publish audio to all sessions
        print(f"\n📤 Publishing audio to all sessions...")
        audio_data = b"fake_audio" * 100
        
        for i, session_id in enumerate(sessions):
            result = await orchestrator.publish_audio_turn(
                session_id=session_id,
                audio_data=audio_data,
                audio_format='webm'
            )
            print(f"   Session {i+1}: {result.get('success')}")
        
        # Check active sessions
        print(f"\n📊 Checking active sessions...")
        active = await orchestrator.get_active_sessions()
        print(f"✅ Active sessions: {len(active)}")
        
        # Wait for processing
        print(f"\n⏳ Waiting for processing (5 seconds)...")
        await asyncio.sleep(5)
        
        # End all sessions
        print(f"\n🏁 Ending all sessions...")
        for i, session_id in enumerate(sessions):
            await orchestrator.end_session(session_id)
            print(f"   Session {i+1} ended")
        
        # Verify cleanup
        active_after = await orchestrator.get_active_sessions()
        print(f"\n📊 Active sessions after cleanup: {len(active_after)}")
        
        await orchestrator.shutdown()
        
        if len(active_after) == 0:
            print("\n✅ TEST 4 PASSED")
            return True
        else:
            print(f"\n⚠️ TEST 4 PARTIAL: {len(active_after)} sessions still active")
            return False
        
    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all distributed orchestration tests"""
    print("\n" + "="*80)
    print("🚀 DISTRIBUTED ORCHESTRATION TEST SUITE")
    print("Testing Redis Streams + Multi-Worker Scaling")
    print("="*80)
    
    tests = [
        ("Redis Connection", test_redis_connection),
        ("Stream Operations", test_stream_operations),
        ("Distributed Orchestrator", test_distributed_orchestrator),
        ("Multi-Session Concurrency", test_multi_session_concurrency)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print("="*80)
    print(f"Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*80)
    
    if passed == total:
        print("\n🎉 All tests PASSED! Distributed orchestration is ready.")
    else:
        print(f"\n⚠️ {total - passed} test(s) FAILED. Check errors above.")


if __name__ == "__main__":
    print("""
Prerequisites:
1. Redis must be running: redis-server
2. MongoDB must be configured in .env
3. Python dependencies installed: pip install redis[hiredis]

Press Ctrl+C to cancel, or wait 3 seconds to start tests...
    """)
    
    try:
        import time
        time.sleep(3)
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\n🛑 Tests cancelled by user")
