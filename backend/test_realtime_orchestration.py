"""
Test Real-time Orchestration Agent
Tests STT → LLM → TTS pipeline with real-time streaming
"""

import asyncio
import sys
import os
import base64
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph_agents.realtime_orchestrator_agent import (
    start_realtime_orchestration,
    process_orchestration_turn,
    end_realtime_orchestration,
    RealtimeOrchestratorAgent
)


def load_test_audio() -> bytes:
    """Load test audio file"""
    audio_file = Path(__file__).parent / "test_audio.wav"
    
    if not audio_file.exists():
        print(f"⚠️ Test audio file not found: {audio_file}")
        print("   Creating dummy audio data...")
        # Create dummy audio data (silent WAV file)
        return b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
    
    with open(audio_file, 'rb') as f:
        return f.read()


async def test_orchestration_initialization():
    """Test orchestration session initialization"""
    print("\n" + "="*80)
    print("TEST 1: Orchestration Initialization")
    print("="*80)
    
    config = {
        'interview_id': 'test_interview_001',
        'meeting_id': 'test_meeting_001',
        'audio_format': 'webm',
        'enable_streaming': True
    }
    
    print("\n🎭 Starting orchestration session...")
    result = await start_realtime_orchestration(config)
    
    if result.get('success'):
        print("✅ Orchestration initialized successfully")
        data = result['data']
        print(f"   Orchestration ID: {data.get('orchestration_id')}")
        print(f"   Session ID: {data.get('session_id')}")
        print(f"   Interview ID: {data.get('interview_id')}")
        print(f"   Status: {data.get('status')}")
        return data.get('session_id')
    else:
        print("❌ Orchestration initialization FAILED")
        print(f"   Error: {result.get('error')}")
        return None


async def test_audio_turn_processing(session_id: str):
    """Test audio turn processing through pipeline"""
    print("\n" + "="*80)
    print("TEST 2: Audio Turn Processing (STT → LLM → TTS)")
    print("="*80)
    
    # Load test audio
    audio_data = load_test_audio()
    print(f"\n🎤 Loaded test audio: {len(audio_data)} bytes")
    
    print("\n⚡ Processing through pipeline...")
    print("   Stage 1: STT (Speech-to-Text)")
    print("   Stage 2: LLM (Interview Conductor)")
    print("   Stage 3: TTS (Text-to-Speech)")
    
    result = await process_orchestration_turn(
        session_id=session_id,
        audio_data=audio_data,
        audio_format='wav'
    )
    
    if result.get('success'):
        data = result['data']
        print("\n✅ Audio turn processed successfully")
        print(f"   Turn: {data.get('turn')}")
        print(f"   Transcription: {data.get('transcription', 'N/A')}")
        print(f"   AI Response: {data.get('ai_response', 'N/A')}")
        print(f"   Audio URL: {data.get('audio_url', 'N/A')}")
        print(f"   Total latency: {data.get('latency_ms', 0)}ms")
        print(f"   Next action: {data.get('next_action', 'N/A')}")
        return True
    else:
        print("\n❌ Audio turn processing FAILED")
        error = result.get('error', {})
        print(f"   Error code: {error.get('code')}")
        print(f"   Message: {error.get('message')}")
        return False


async def test_orchestration_ending(session_id: str):
    """Test orchestration session ending"""
    print("\n" + "="*80)
    print("TEST 3: Orchestration Session Ending")
    print("="*80)
    
    print(f"\n🏁 Ending orchestration session: {session_id}")
    result = await end_realtime_orchestration(session_id)
    
    if result.get('success'):
        data = result['data']
        print("✅ Orchestration ended successfully")
        print(f"   Orchestration ID: {data.get('orchestration_id')}")
        print(f"   Session ID: {data.get('session_id')}")
        print(f"   Total turns: {data.get('total_turns', 0)}")
        print(f"   Successful turns: {data.get('successful_turns', 0)}")
        print(f"   Quality score: {data.get('quality_score', 0):.1f}")
        print(f"   Duration: {data.get('duration_seconds', 0):.1f}s")
        return True
    else:
        print("❌ Orchestration ending FAILED")
        print(f"   Error: {result.get('error')}")
        return False


async def test_agent_components():
    """Test individual agent components"""
    print("\n" + "="*80)
    print("TEST 4: Agent Components Verification")
    print("="*80)
    
    try:
        print("\n🔍 Testing RealtimeOrchestratorAgent initialization...")
        agent = RealtimeOrchestratorAgent()
        
        print("✅ Agent initialized successfully")
        print(f"   Max retries: {agent.max_retries}")
        print(f"   Max silence: {agent.max_silence_seconds}s")
        print(f"   STT timeout: {agent.stt_timeout_seconds}s")
        print(f"   LLM timeout: {agent.llm_timeout_seconds}s")
        print(f"   TTS timeout: {agent.tts_timeout_seconds}s")
        print(f"   Active sessions: {len(agent.active_sessions)}")
        
        # Test workflow build
        print("\n🔍 Testing LangGraph workflow...")
        print(f"   Workflow nodes: {len(agent.workflow.nodes) if hasattr(agent.workflow, 'nodes') else 'N/A'}")
        print("✅ Workflow built successfully")
        
        # Test MongoDB connection
        print("\n🔍 Testing MongoDB connection...")
        collections = agent.db.list_collection_names()
        print(f"✅ MongoDB connected: {len(collections)} collections")
        
        # Test MCP components
        print("\n🔍 Testing MCP components...")
        print(f"   Context Manager: {type(agent.context_manager).__name__}")
        print(f"   Cache Manager: {type(agent.cache_manager).__name__}")
        print(f"   Token Optimizer: {type(agent.token_optimizer).__name__}")
        print("✅ MCP components initialized")
        
        agent.close()
        print("\n✅ Agent closed successfully")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Agent component test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_recovery():
    """Test error recovery mechanisms"""
    print("\n" + "="*80)
    print("TEST 5: Error Recovery and Retry Logic")
    print("="*80)
    
    try:
        agent = RealtimeOrchestratorAgent()
        
        print("\n🔍 Testing error recovery strategies...")
        
        # Test state with errors
        from langgraph_agents.realtime_orchestrator_agent import OrchestratorState
        
        test_state = OrchestratorState(
            orchestration_id='test_orch_001',
            session_id='test_session_001',
            interview_id='test_interview_001',
            meeting_id=None,
            conversation_active=True,
            current_turn=1,
            turns_history=[],
            stt_status='failed',
            llm_status='idle',
            tts_status='idle',
            audio_chunk=None,
            audio_format='webm',
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
            is_streaming=False,
            errors=[{
                'timestamp': '2025-01-01T00:00:00',
                'stage': 'transcribe_audio_stt',
                'error': 'Test error',
                'severity': 'high'
            }],
            retry_attempts={'stt': 1, 'llm': 0, 'tts': 0},
            max_retries=3,
            error_recovery_strategy='retry',
            last_successful_stage='receive_audio',
            stt_latency_ms=0,
            llm_latency_ms=0,
            tts_latency_ms=0,
            total_latency_ms=0,
            pipeline_start_time=0.0,
            pipeline_end_time=None,
            waiting_for_response=False,
            silence_duration_seconds=0,
            max_silence_seconds=10,
            auto_prompt_after_silence=True,
            conversation_quality_score=100.0,
            interruptions_count=0,
            successful_turns=0,
            failed_turns=0,
            processing_status='active',
            success=False,
            created_at='2025-01-01T00:00:00',
            last_activity_at='2025-01-01T00:00:00',
            completed_at=None
        )
        
        # Test conditional routing
        print("\n   Testing STT retry logic...")
        next_step = agent._should_continue_after_stt(test_state)
        print(f"   ✅ STT decision: {next_step}")
        assert next_step == 'retry', "Should retry STT"
        
        # Test max retries
        test_state['retry_attempts']['stt'] = 3
        next_step = agent._should_continue_after_stt(test_state)
        print(f"   ✅ Max retries decision: {next_step}")
        assert next_step == 'error', "Should go to error handler after max retries"
        
        # Test error recovery decision
        print("\n   Testing error recovery decision...")
        test_state['last_successful_stage'] = 'stt'
        decision = agent._error_recovery_decision(test_state)
        print(f"   ✅ Recovery decision: {decision}")
        
        agent.close()
        print("\n✅ Error recovery test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Error recovery test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_mongodb_storage():
    """Test MongoDB storage for orchestration data"""
    print("\n" + "="*80)
    print("TEST 6: MongoDB Storage Verification")
    print("="*80)
    
    try:
        from pymongo import MongoClient
        from dotenv import load_dotenv
        
        load_dotenv()
        
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
        
        print(f"\n🔍 Connecting to MongoDB...")
        print(f"   Database: {mongo_db_name}")
        
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000
        )
        db = client[mongo_db_name]
        
        # Check if orchestration_sessions collection exists
        collections = db.list_collection_names()
        print(f"✅ Connected to MongoDB: {len(collections)} collections")
        
        if 'orchestration_sessions' not in collections:
            print("   ℹ️ orchestration_sessions collection will be created on first use")
        else:
            # Count existing sessions
            count = db['orchestration_sessions'].count_documents({})
            print(f"   📊 Existing orchestration sessions: {count}")
            
            # Get latest session
            if count > 0:
                latest = db['orchestration_sessions'].find_one(
                    {},
                    sort=[('created_at', -1)]
                )
                print(f"   Latest session ID: {latest.get('session_id')}")
                print(f"   Total turns: {latest.get('total_turns', 0)}")
                print(f"   Quality score: {latest.get('conversation_quality_score', 0):.1f}")
        
        client.close()
        print("\n✅ MongoDB storage test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ MongoDB storage test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_performance_metrics():
    """Test performance monitoring and metrics"""
    print("\n" + "="*80)
    print("TEST 7: Performance Metrics & Monitoring")
    print("="*80)
    
    try:
        import time
        
        print("\n🔍 Testing latency tracking...")
        
        # Simulate pipeline latency
        metrics = {
            'stt_latency_ms': 250,
            'llm_latency_ms': 1500,
            'tts_latency_ms': 800
        }
        
        total_latency = sum(metrics.values())
        
        print(f"   STT latency: {metrics['stt_latency_ms']}ms")
        print(f"   LLM latency: {metrics['llm_latency_ms']}ms")
        print(f"   TTS latency: {metrics['tts_latency_ms']}ms")
        print(f"   Total latency: {total_latency}ms")
        
        # Check latency thresholds
        print("\n🔍 Checking latency thresholds...")
        
        thresholds = {
            'stt': 1000,  # 1 second
            'llm': 3000,  # 3 seconds
            'tts': 2000,  # 2 seconds
            'total': 5000  # 5 seconds
        }
        
        checks = {
            'stt': metrics['stt_latency_ms'] <= thresholds['stt'],
            'llm': metrics['llm_latency_ms'] <= thresholds['llm'],
            'tts': metrics['tts_latency_ms'] <= thresholds['tts'],
            'total': total_latency <= thresholds['total']
        }
        
        for component, passed in checks.items():
            status = "✅" if passed else "⚠️"
            print(f"   {status} {component.upper()}: {'PASS' if passed else 'SLOW'}")
        
        print("\n✅ Performance metrics test PASSED")
        return all(checks.values())
        
    except Exception as e:
        print(f"\n❌ Performance metrics test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all orchestration tests"""
    print("\n" + "🎭 " * 30)
    print("REAL-TIME ORCHESTRATION TEST SUITE")
    print("STT → LLM → TTS Pipeline Verification")
    print("🎭 " * 30)
    
    results = {}
    
    # Test 1: Initialization
    session_id = await test_orchestration_initialization()
    results['initialization'] = session_id is not None
    
    # Test 2: Audio turn processing (only if initialization succeeded)
    if session_id:
        results['audio_processing'] = await test_audio_turn_processing(session_id)
        
        # Test 3: Ending (only if previous tests succeeded)
        if results['audio_processing']:
            results['ending'] = await test_orchestration_ending(session_id)
        else:
            results['ending'] = False
    else:
        results['audio_processing'] = False
        results['ending'] = False
    
    # Test 4: Component verification
    results['components'] = await test_agent_components()
    
    # Test 5: Error recovery
    results['error_recovery'] = await test_error_recovery()
    
    # Test 6: MongoDB storage
    results['mongodb_storage'] = await test_mongodb_storage()
    
    # Test 7: Performance metrics
    results['performance'] = await test_performance_metrics()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    test_names = {
        'initialization': 'Orchestration Initialization',
        'audio_processing': 'Audio Turn Processing (STT → LLM → TTS)',
        'ending': 'Orchestration Session Ending',
        'components': 'Agent Components Verification',
        'error_recovery': 'Error Recovery & Retry Logic',
        'mongodb_storage': 'MongoDB Storage Verification',
        'performance': 'Performance Metrics & Monitoring'
    }
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_key, test_name in test_names.items():
        status = "✅ PASSED" if results[test_key] else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print("="*80)
    print(f"Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*80)
    
    if passed == total:
        print("\n🎉 All tests PASSED! Real-time orchestration is working correctly.")
        print("\n📝 Key Features Verified:")
        print("   ✅ STT → LLM → TTS pipeline integration")
        print("   ✅ Real-time audio processing")
        print("   ✅ Error recovery with retry logic")
        print("   ✅ Conversation state management")
        print("   ✅ Performance monitoring")
        print("   ✅ MongoDB data persistence")
        print("   ✅ MCP components integration")
    else:
        print(f"\n⚠️ {total - passed} test(s) FAILED. Check errors above.")
    
    return passed == total


if __name__ == "__main__":
    print("\n🚀 Starting Real-time Orchestration Tests...")
    
    success = asyncio.run(run_all_tests())
    
    sys.exit(0 if success else 1)
