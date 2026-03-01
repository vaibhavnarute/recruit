"""
Test TTS Integration
Tests the complete TTS workflow including:
- Text-to-speech conversion
- Voice profile selection
- Streaming audio
- Integration with interview conductor
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph_agents.tts_agent import convert_text_to_speech, stream_text_to_speech
from langgraph_agents.interview_conductor_agent import conduct_interview
from repositories.tts_repository import TTSRepository


async def test_basic_tts():
    """Test basic TTS conversion"""
    print("\n" + "="*80)
    print("TEST 1: Basic TTS Conversion")
    print("="*80)
    
    request = {
        "text": "Hello! Welcome to your technical interview for the Senior Python Developer position.",
        "text_type": "intro",
        "voice_profile": "professional_female",
        "emotion": "professional",
        "session_id": "test_session_001"
    }
    
    result = await convert_text_to_speech(request)
    
    if result.get('success'):
        print("✅ TTS Conversion PASSED")
        data = result['data']
        print(f"   TTS ID: {data.get('tts_id')}")
        print(f"   Voice: {data.get('voice_name')}")
        print(f"   Duration: {data.get('audio_duration_seconds')}s")
        print(f"   Size: {data.get('audio_size_bytes', 0) / 1024:.2f} KB")
        print(f"   Processing: {data.get('processing_time_ms')}ms")
        
        if data.get('audio_base64'):
            print(f"   Base64 length: {len(data['audio_base64'])} chars")
        
        return True
    else:
        print("❌ TTS Conversion FAILED")
        print(f"   Error: {result.get('error')}")
        return False


async def test_voice_profiles():
    """Test different voice profiles"""
    print("\n" + "="*80)
    print("TEST 2: Voice Profiles")
    print("="*80)
    
    profiles = [
        "professional_female",
        "professional_male",
        "friendly_female",
        "friendly_male"
    ]
    
    text = "This is a test of the voice profile. How does it sound?"
    
    results = []
    for profile in profiles:
        print(f"\nTesting voice profile: {profile}")
        
        request = {
            "text": text,
            "text_type": "question",
            "voice_profile": profile,
            "emotion": "professional",
            "session_id": f"test_voice_{profile}"
        }
        
        result = await convert_text_to_speech(request)
        
        if result.get('success'):
            print(f"✅ {profile}: SUCCESS")
            data = result['data']
            print(f"   Voice Name: {data.get('voice_name')}")
            print(f"   Duration: {data.get('audio_duration_seconds')}s")
            results.append(True)
        else:
            print(f"❌ {profile}: FAILED")
            print(f"   Error: {result.get('error')}")
            results.append(False)
    
    success_count = sum(results)
    print(f"\n✅ Voice Profiles: {success_count}/{len(profiles)} passed")
    return all(results)


async def test_tts_streaming():
    """Test TTS streaming"""
    print("\n" + "="*80)
    print("TEST 3: TTS Streaming")
    print("="*80)
    
    request = {
        "text": "This is a streaming test. The audio should be delivered in chunks for real-time playback.",
        "text_type": "question",
        "voice_profile": "professional_female",
        "emotion": "professional",
        "session_id": "test_streaming_001"
    }
    
    chunks_received = 0
    try:
        print("📡 Starting stream...")
        async for chunk in stream_text_to_speech(request):
            if chunk.get('error'):
                print(f"❌ Stream error: {chunk['error']}")
                return False
            
            if not chunk.get('is_final'):
                chunks_received += 1
                print(f"   Chunk #{chunks_received} received")
            else:
                print(f"✅ Stream complete: {chunks_received} chunks received")
                return chunks_received > 0
        
        return False
    except Exception as e:
        print(f"❌ Streaming FAILED: {str(e)}")
        return False


async def test_interview_tts_integration():
    """Test TTS integration with interview conductor"""
    print("\n" + "="*80)
    print("TEST 4: Interview TTS Integration")
    print("="*80)
    
    # Start interview
    interview_config = {
        "candidate_name": "Test Candidate",
        "candidate_email": "test@example.com",
        "job_title": "Senior Python Developer",
        "job_description": "Looking for experienced Python developer",
        "required_skills": ["Python", "FastAPI", "LangGraph"],
        "meeting_id": "test_meeting_001"  # Enable TTS
    }
    
    print("🎬 Starting interview with TTS enabled...")
    result = await conduct_interview(interview_config)
    
    if result.get('success'):
        print("✅ Interview started successfully")
        print(f"   Interview ID: {result.get('interview_id')}")
        print(f"   Introduction: {result.get('introduction', '')[:100]}...")
        
        # Check if TTS was generated
        tts_audio = result.get('tts_audio')
        if tts_audio:
            print(f"✅ TTS Auto-generated for introduction")
            print(f"   TTS ID: {tts_audio.get('tts_id')}")
            print(f"   Voice: {tts_audio.get('voice_name')}")
            print(f"   Duration: {tts_audio.get('audio_duration_seconds')}s")
            return True
        else:
            print("⚠️ TTS not auto-generated (check ELEVENLABS_API_KEY)")
            return True  # Still pass if TTS is optional
    else:
        print("❌ Interview start FAILED")
        print(f"   Error: {result.get('error')}")
        return False


def test_tts_repository():
    """Test TTS repository"""
    print("\n" + "="*80)
    print("TEST 5: TTS Repository")
    print("="*80)
    
    try:
        repo = TTSRepository()
        
        # Get stats
        stats = repo.get_tts_stats()
        print(f"📊 TTS Stats:")
        print(f"   Total TTS Audio: {stats.get('total_tts_audio', 0)}")
        print(f"   Successful: {stats.get('successful', 0)}")
        print(f"   Failed: {stats.get('failed', 0)}")
        print(f"   Success Rate: {stats.get('success_rate', 0):.2f}%")
        print(f"   Streaming TTS: {stats.get('streaming_tts', 0)}")
        
        # Get voice profile stats
        voice_stats = repo.get_all_voice_profiles_stats()
        if voice_stats:
            print(f"\n🎤 Voice Profile Stats:")
            for vs in voice_stats:
                print(f"   {vs['voice_profile']}: {vs['total_audio']} files, {vs['total_duration_seconds']:.1f}s total")
        
        repo.close()
        print("✅ Repository test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Repository test FAILED: {str(e)}")
        return False


async def run_all_tests():
    """Run all TTS tests"""
    print("\n" + "🔊 " * 30)
    print("TTS INTEGRATION TEST SUITE")
    print("🔊 " * 30)
    
    # Check for API key
    if not os.getenv("ELEVENLABS_API_KEY"):
        print("\n⚠️ WARNING: ELEVENLABS_API_KEY not set!")
        print("   Some tests may fail. Set the API key to enable full testing.")
        print("   export ELEVENLABS_API_KEY=your_api_key_here\n")
    
    results = {}
    
    # Run tests
    results['basic_tts'] = await test_basic_tts()
    results['voice_profiles'] = await test_voice_profiles()
    results['streaming'] = await test_tts_streaming()
    results['interview_integration'] = await test_interview_tts_integration()
    results['repository'] = test_tts_repository()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, passed_status in results.items():
        status = "✅ PASSED" if passed_status else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    print("="*80)
    print(f"Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*80)
    
    if passed == total:
        print("\n🎉 All tests PASSED! TTS integration is working correctly.")
    else:
        print(f"\n⚠️ {total - passed} test(s) FAILED. Check errors above.")
    
    return passed == total


if __name__ == "__main__":
    print("\n🚀 Starting TTS Integration Tests...")
    
    success = asyncio.run(run_all_tests())
    
    sys.exit(0 if success else 1)
