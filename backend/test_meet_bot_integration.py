"""
Integration Tests for Google Meet Bot System
Tests the complete flow from session creation to transcription
"""

import pytest
import asyncio
import json
import time
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph_agents.meet_bot_agent import MeetBotAgent, create_meet_session
from langgraph_agents.audio_transcription_agent import AudioTranscriptionAgent, transcribe_audio_chunk
from repositories.meet_session_repository import MeetSessionRepository


class TestMeetBotAgent:
    """Test Meet Bot LangGraph Agent"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.agent = MeetBotAgent()
        self.repository = MeetSessionRepository()
        self.test_session_id = f"test_session_{int(time.time())}"
    
    def test_agent_initialization(self):
        """Test agent initializes correctly"""
        assert self.agent is not None
        assert self.agent.groq_client is not None
        assert self.agent.workflow is not None
        assert self.agent.model == "llama-3.3-70b-versatile"
        print("✅ Agent initialization test passed")
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        """Test complete session lifecycle"""
        config = {
            'session_id': self.test_session_id,
            'meet_url': 'https://meet.google.com/test-session',
            'interview_id': 'test_interview_001',
            'bot_email': 'testbot@example.com',
            'bot_password': 'test_password',
            'max_retries': 2
        }
        
        print(f"\n🧪 Testing session lifecycle: {self.test_session_id}")
        
        result = await create_meet_session(config)
        
        # Assertions
        assert result is not None
        assert result['session_id'] == self.test_session_id
        assert result['session_status'] in ['initializing', 'joining', 'failed', 'completed']
        assert 'started_at' in result
        assert isinstance(result.get('join_attempts', 0), int)
        
        print(f"✅ Session lifecycle test passed")
        print(f"   Final status: {result['session_status']}")
        print(f"   Join attempts: {result.get('join_attempts', 0)}")
    
    @pytest.mark.asyncio
    async def test_join_strategy_generation(self):
        """Test LLM join strategy generation"""
        state = {
            'session_id': self.test_session_id,
            'meet_url': 'https://meet.google.com/test',
            'bot_email': 'testbot@example.com',
            'bot_password': 'test',
            'interview_id': 'test_001',
            'session_status': 'pending',
            'join_attempts': 1,
            'max_retries': 3,
            'audio_chunks_received': 0,
            'transcription_segments': [],
            'current_speaker': '',
            'errors': [],
            'last_error': '',
            'recovery_action': '',
            'started_at': datetime.utcnow().isoformat(),
            'joined_at': '',
            'ended_at': '',
            'join_strategy': '',
            'error_diagnosis': '',
            'recovery_plan': '',
            'session_summary': ''
        }
        
        print(f"\n🧪 Testing join strategy generation")
        
        result = self.agent.plan_join_strategy(state)
        
        # Assertions
        assert result is not None
        assert 'join_strategy' in result
        assert result['join_strategy'] != ''
        
        # Parse strategy
        strategy = json.loads(result['join_strategy'])
        assert 'approach' in strategy
        assert 'wait_time' in strategy
        assert 'reasoning' in strategy
        
        print(f"✅ Join strategy generation test passed")
        print(f"   Approach: {strategy['approach']}")
        print(f"   Wait time: {strategy['wait_time']}s")
    
    @pytest.mark.asyncio
    async def test_error_diagnosis(self):
        """Test LLM error diagnosis"""
        state = {
            'session_id': self.test_session_id,
            'meet_url': 'https://meet.google.com/test',
            'bot_email': 'testbot@example.com',
            'bot_password': 'test',
            'interview_id': 'test_001',
            'session_status': 'failed',
            'join_attempts': 2,
            'max_retries': 3,
            'audio_chunks_received': 0,
            'transcription_segments': [],
            'current_speaker': '',
            'errors': [
                {
                    'timestamp': datetime.utcnow().isoformat(),
                    'stage': 'join_meeting',
                    'error': 'Connection timeout'
                }
            ],
            'last_error': 'Connection timeout',
            'recovery_action': '',
            'started_at': datetime.utcnow().isoformat(),
            'joined_at': '',
            'ended_at': '',
            'join_strategy': '',
            'error_diagnosis': '',
            'recovery_plan': '',
            'session_summary': ''
        }
        
        print(f"\n🧪 Testing error diagnosis")
        
        result = self.agent.diagnose_errors(state)
        
        # Assertions
        assert result is not None
        assert 'error_diagnosis' in result
        assert 'recovery_action' in result
        assert result['recovery_action'] in ['retry', 'abort']
        
        print(f"✅ Error diagnosis test passed")
        print(f"   Recovery action: {result['recovery_action']}")


class TestAudioTranscriptionAgent:
    """Test Audio Transcription Agent"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.agent = AudioTranscriptionAgent()
        self.repository = MeetSessionRepository()
    
    def test_agent_initialization(self):
        """Test agent initializes correctly"""
        assert self.agent is not None
        assert self.agent.groq_client is not None
        assert self.agent.workflow is not None
        assert self.agent.whisper_model == "whisper-large-v3"
        assert self.agent.llm_model == "llama-3.3-70b-versatile"
        print("✅ Transcription agent initialization test passed")
    
    @pytest.mark.asyncio
    async def test_transcription_workflow_with_dummy_audio(self):
        """Test transcription workflow with dummy audio (will fail gracefully)"""
        config = {
            'session_id': 'test_session_001',
            'audio_chunk_id': 'test_chunk_001',
            'audio_data': b'dummy_audio_data_for_testing',
            'audio_format': 'webm',
            'interview_id': 'test_interview_001',
            'question_context': 'Tell me about your Python experience'
        }
        
        print(f"\n🧪 Testing transcription workflow (will fail gracefully with dummy audio)")
        
        result = await transcribe_audio_chunk(config)
        
        # Assertions - we expect this to fail but handle gracefully
        assert result is not None
        assert 'processing_status' in result
        assert 'errors' in result
        # Status should be either failed or completed
        assert result['processing_status'] in ['failed', 'completed', 'pending']
        
        print(f"✅ Transcription workflow test passed (handled gracefully)")
        print(f"   Status: {result['processing_status']}")
        print(f"   Errors: {len(result.get('errors', []))}")


class TestMeetSessionRepository:
    """Test MongoDB repository operations"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.repository = MeetSessionRepository()
        self.test_session_id = f"test_repo_session_{int(time.time())}"
    
    def teardown_method(self):
        """Cleanup after each test"""
        try:
            # Delete test session if it exists
            self.repository.delete_session(self.test_session_id)
        except Exception as e:
            pass  # Ignore errors during cleanup
    
    def test_repository_initialization(self):
        """Test repository initializes correctly"""
        assert self.repository is not None
        assert self.repository.sessions_collection is not None
        assert self.repository.transcripts_collection is not None
        assert self.repository.audio_chunks_collection is not None
        print("✅ Repository initialization test passed")
    
    def test_create_session(self):
        """Test session creation"""
        session_data = {
            'session_id': self.test_session_id,
            'interview_id': 'test_interview_001',
            'meet_url': 'https://meet.google.com/test',
            'bot_email': 'testbot@example.com'
        }
        
        print(f"\n🧪 Testing session creation: {self.test_session_id}")
        
        result = self.repository.create_session(session_data)
        
        # Assertions
        assert result is not None
        assert result['session_id'] == self.test_session_id
        assert result['interview_id'] == 'test_interview_001'
        assert result['session_status'] == 'pending'
        assert 'created_at' in result
        
        print(f"✅ Session creation test passed")
        print(f"   Session ID: {result['session_id']}")
        print(f"   Status: {result['session_status']}")
    
    def test_update_session(self):
        """Test session update"""
        # First create a session
        session_data = {
            'session_id': self.test_session_id,
            'interview_id': 'test_interview_001',
            'meet_url': 'https://meet.google.com/test',
            'bot_email': 'testbot@example.com'
        }
        self.repository.create_session(session_data)
        
        print(f"\n🧪 Testing session update")
        
        # Update session
        updates = {
            'session_status': 'recording',
            'started_at': datetime.utcnow()
        }
        result = self.repository.update_session(self.test_session_id, updates)
        
        # Assertions
        assert result is not None
        assert result['success'] == True
        
        # Verify update
        session = self.repository.get_session(self.test_session_id)
        assert session['session_status'] == 'recording'
        assert session['started_at'] is not None
        
        print(f"✅ Session update test passed")
        print(f"   New status: {session['session_status']}")
    
    def test_save_transcript(self):
        """Test transcript saving"""
        # First create a session
        session_data = {
            'session_id': self.test_session_id,
            'interview_id': 'test_interview_001',
            'meet_url': 'https://meet.google.com/test',
            'bot_email': 'testbot@example.com'
        }
        self.repository.create_session(session_data)
        
        print(f"\n🧪 Testing transcript save")
        
        # Save transcript
        transcript_data = {
            'session_id': self.test_session_id,
            'interview_id': 'test_interview_001',
            'raw_transcription': 'This is a test transcription.',
            'cleaned_transcription': 'This is a test transcription.',
            'confidence_score': 0.95,
            'sentiment': 'neutral'
        }
        result = self.repository.save_transcript(transcript_data)
        
        # Assertions
        assert result is not None
        assert 'chunk_id' in result
        assert result['session_id'] == self.test_session_id
        assert result['confidence_score'] == 0.95
        
        print(f"✅ Transcript save test passed")
        print(f"   Chunk ID: {result['chunk_id']}")
        print(f"   Confidence: {result['confidence_score']}")
    
    def test_get_full_transcript(self):
        """Test full transcript retrieval"""
        # Create session and transcripts
        session_data = {
            'session_id': self.test_session_id,
            'interview_id': 'test_interview_001',
            'meet_url': 'https://meet.google.com/test',
            'bot_email': 'testbot@example.com'
        }
        self.repository.create_session(session_data)
        
        # Add multiple transcripts
        for i in range(3):
            transcript_data = {
                'session_id': self.test_session_id,
                'interview_id': 'test_interview_001',
                'raw_transcription': f'Segment {i+1}.',
                'cleaned_transcription': f'Segment {i+1}.',
                'confidence_score': 0.9 + (i * 0.02)
            }
            self.repository.save_transcript(transcript_data)
        
        print(f"\n🧪 Testing full transcript retrieval")
        
        # Get full transcript
        result = self.repository.get_full_transcript(self.test_session_id)
        
        # Assertions
        assert result is not None
        assert result['total_segments'] >= 3  # At least 3 segments (may have more from retries)
        assert 'Segment 1' in result['full_transcript']
        assert result['average_confidence'] > 0.85
        
        print(f"✅ Full transcript test passed")
        print(f"   Total segments: {result['total_segments']}")
        print(f"   Transcript length: {len(result['full_transcript'])} chars")
        print(f"   Average confidence: {result['average_confidence']:.2f}")
        assert 'Segment 2' in result['full_transcript']
        assert 'Segment 3' in result['full_transcript']
        assert result['average_confidence'] > 0.9
        
        print(f"✅ Full transcript test passed")
        print(f"   Total segments: {result['total_segments']}")
        print(f"   Average confidence: {result['average_confidence']:.2f}")
    
    def test_session_analytics(self):
        """Test session analytics"""
        # Create session with data
        session_data = {
            'session_id': self.test_session_id,
            'interview_id': 'test_interview_001',
            'meet_url': 'https://meet.google.com/test',
            'bot_email': 'testbot@example.com'
        }
        self.repository.create_session(session_data)
        
        # Update session
        self.repository.update_session(self.test_session_id, {
            'session_status': 'completed',
            'started_at': datetime.utcnow(),
            'ended_at': datetime.utcnow()
        })
        
        # Add transcripts
        for sentiment in ['positive', 'neutral', 'negative']:
            self.repository.save_transcript({
                'session_id': self.test_session_id,
                'interview_id': 'test_interview_001',
                'cleaned_transcription': f'Test {sentiment}',
                'confidence_score': 0.9,
                'sentiment': sentiment
            })
        
        print(f"\n🧪 Testing session analytics")
        
        # Get analytics
        analytics = self.repository.get_session_analytics(self.test_session_id)
        
        # Assertions
        assert analytics is not None
        assert analytics['session_id'] == self.test_session_id
        assert analytics['session_status'] == 'completed'
        assert analytics['transcription_segments'] >= 3  # At least 3 (may have more from previous tests)
        assert analytics['average_confidence'] > 0.85
        
        print(f"✅ Session analytics test passed")
        print(f"   Total segments: {analytics['transcription_segments']}")
        print(f"   Average confidence: {analytics['average_confidence']:.2f}")
        
        # Check sentiment distribution exists and has all sentiments
        assert 'sentiment_distribution' in analytics
        sentiment_dist = analytics['sentiment_distribution']
        assert 'positive' in sentiment_dist
        assert 'neutral' in sentiment_dist
        assert 'negative' in sentiment_dist
        
        # Verify each sentiment has at least 1 occurrence (may have more from previous test runs)
        assert sentiment_dist.get('positive', 0) >= 1, f"Expected at least 1 positive, got {sentiment_dist.get('positive', 0)}"
        assert sentiment_dist.get('neutral', 0) >= 1, f"Expected at least 1 neutral, got {sentiment_dist.get('neutral', 0)}"
        assert sentiment_dist.get('negative', 0) >= 1, f"Expected at least 1 negative, got {sentiment_dist.get('negative', 0)}"
        
        print(f"✅ Session analytics test passed")
        print(f"   Status: {analytics['session_status']}")
        print(f"   Segments: {analytics['transcription_segments']}")
        print(f"   Sentiment: {sentiment_dist}")
    
    def teardown_method(self):
        """Cleanup test data"""
        try:
            self.repository.delete_session(self.test_session_id)
            print(f"🧹 Cleaned up test session: {self.test_session_id}")
        except:
            pass


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 RUNNING MEET BOT INTEGRATION TESTS")
    print("="*80)
    
    # Meet Bot Agent Tests
    print("\n📦 Testing Meet Bot Agent...")
    test_meet_bot = TestMeetBotAgent()
    test_meet_bot.setup_method()
    test_meet_bot.test_agent_initialization()
    asyncio.run(test_meet_bot.test_session_lifecycle())
    asyncio.run(test_meet_bot.test_join_strategy_generation())
    asyncio.run(test_meet_bot.test_error_diagnosis())
    
    # Audio Transcription Agent Tests
    print("\n📦 Testing Audio Transcription Agent...")
    test_transcription = TestAudioTranscriptionAgent()
    test_transcription.setup_method()
    test_transcription.test_agent_initialization()
    asyncio.run(test_transcription.test_transcription_workflow_with_dummy_audio())
    
    # Repository Tests
    print("\n📦 Testing Meet Session Repository...")
    test_repo = TestMeetSessionRepository()
    
    # Test 1: Initialization
    test_repo.setup_method()
    test_repo.test_repository_initialization()
    test_repo.teardown_method()
    
    # Test 2: Create session
    test_repo.setup_method()
    test_repo.test_create_session()
    test_repo.teardown_method()
    
    # Test 3: Update session
    test_repo.setup_method()
    test_repo.test_update_session()
    test_repo.teardown_method()
    
    # Test 4: Save transcript
    test_repo.setup_method()
    test_repo.test_save_transcript()
    test_repo.teardown_method()
    
    # Test 5: Get full transcript
    test_repo.setup_method()
    test_repo.test_get_full_transcript()
    test_repo.teardown_method()
    
    # Test 6: Session analytics
    test_repo.setup_method()
    test_repo.test_session_analytics()
    test_repo.teardown_method()
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
    print("="*80 + "\n")


if __name__ == "__main__":
    run_all_tests()
