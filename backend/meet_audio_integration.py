"""
Google Meet Bot - Complete Audio Integration

This module integrates TTS playback and STT recording with Google Meet sessions.
It connects meet_bot_audio.py functionality to the actual Meet call.

Features:
- Play TTS audio through bot's virtual microphone
- Capture candidate audio via Meet's audio stream
- Real-time audio processing and transcription
- Audio quality management and buffering

Author: AI Recruiter Team
Created: February 2026
"""

import asyncio
import base64
import logging
from typing import Optional, Dict, Any, List
from playwright.async_api import Page
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class MeetAudioIntegration:
    """
    Complete audio integration for Google Meet interviews.
    Handles both TTS playback and candidate audio capture.
    """
    
    def __init__(self, page: Page):
        """
        Initialize audio integration.
        
        Args:
            page: Playwright page instance (in active Meet call)
        """
        self.page = page
        self.is_initialized = False
        self.is_playing_audio = False
        self.is_recording = False
        self.audio_buffer = []
        
    async def initialize(self) -> bool:
        """
        Initialize audio system in Google Meet.
        Sets up Web Audio API, MediaStreamDestination for TTS output,
        and intercepts RTCPeerConnections to capture candidate's remote audio.
        
        Returns:
            bool: True if successful
        """
        try:
            logger.info("🎵 Initializing Meet audio integration...")
            
            success = await self.page.evaluate("""
                () => {
                    try {
                        // 1. Create Web Audio Context
                        if (!window.audioContext) {
                            window.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                                sampleRate: 16000
                            });
                        }
                        
                        // 2. Storage for recorded audio chunks (candidate's voice)
                        // Only reset if not already set (preserve chunks from previous init)
                        if (!window.botAudioChunks) window.botAudioChunks = [];
                        if (!window.botMicDestination) window.botMicDestination = null;
                        window.botMediaRecorder = null;  // Always reset recorder (fresh start)
                        
                        // 3. RTCPeerConnection interceptor:
                        // CRITICAL: DO NOT reset window._botPeerConnections here!
                        // The add_init_script() in GoogleMeetAuth.initialize() already installed
                        // this interceptor and populated _botPeerConnections with the PCs that
                        // Google Meet created when the bot joined. Resetting the array here would
                        // destroy those captures, making TTS unable to reach the candidate.
                        if (!window._botPeerConnections) window._botPeerConnections = [];
                        // _botRemoteStream: only reset if not already captured
                        if (!window._botRemoteStream) window._botRemoteStream = null;

                        // Re-install interceptor only if not already installed by init_script
                        // (identified by window._botRTCInterceptorInstalled flag)
                        if (!window._botRTCInterceptorInstalled) {
                            const OriginalRTCPeerConnection = window.RTCPeerConnection;
                            window.RTCPeerConnection = function(...args) {
                                const pc = new OriginalRTCPeerConnection(...args);
                                window._botPeerConnections.push(pc);
                                
                                pc.addEventListener('track', (event) => {
                                    if (event.track.kind === 'audio') {
                                        console.log('📡 Remote audio track received from candidate');
                                        window._botRemoteStream = event.streams[0] || new MediaStream([event.track]);
                                    }
                                });
                                
                                pc.addEventListener('connectionstatechange', () => {
                                    if (pc.connectionState === 'closed' || pc.connectionState === 'failed') {
                                        window._botPeerConnections = window._botPeerConnections.filter(p => p !== pc);
                                    }
                                });
                                
                                return pc;
                            };
                            Object.assign(window.RTCPeerConnection, OriginalRTCPeerConnection);
                            window.RTCPeerConnection.prototype = OriginalRTCPeerConnection.prototype;
                            window._botRTCInterceptorInstalled = true;
                        }
                        
                        const pcCount = (window._botPeerConnections || []).length;
                        console.log('✅ Audio initialized | existing PCs preserved:', pcCount,
                                    '| remoteStream:', !!(window._botRemoteStream));
                        return {ok: true, pcCount, hasRemoteStream: !!(window._botRemoteStream)};
                    } catch (e) {
                        console.error('❌ Audio initialization failed:', e);
                        return false;
                    }
                }
            """)
            
            # JS returns {ok: true, pcCount, hasRemoteStream} or false on error
            ok = success.get('ok') if isinstance(success, dict) else bool(success)
            if ok:
                pc_count = success.get('pcCount', 0) if isinstance(success, dict) else 0
                has_remote = success.get('hasRemoteStream', False) if isinstance(success, dict) else False
                self.is_initialized = True
                logger.info(f"✅ Audio initialized | peer connections preserved: {pc_count} | remote stream: {has_remote}")
                if pc_count == 0:
                    logger.warning("⚠️ 0 peer connections captured — TTS may not reach candidate until Meet creates new PCs")
                return True
            else:
                logger.error("❌ Audio initialization failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error initializing audio: {e}")
            return False
    
    async def play_tts_audio(self, audio_data: bytes, sample_rate: int = 24000) -> bool:
        """
        Play TTS audio and route it into the Meet microphone stream so candidates hear it.
        
        HOW IT WORKS:
        - Decodes the MP3 bytes via AudioContext.decodeAudioData()
        - Creates a MediaStreamDestinationNode so the audio becomes a MediaStream track
        - Replaces (or mixes with) the existing microphone track in every RTCPeerConnection
          that Google Meet has open — this is what actually sends audio to the candidate
        - Also plays locally through a hidden <audio> element for monitoring
        
        Args:
            audio_data: Raw audio bytes (MP3 from Deepgram TTS)
            sample_rate: Audio sample rate in Hz
            
        Returns:
            bool: True if audio routed and played successfully
        """
        try:
            logger.info(f"🔊 Playing TTS audio ({len(audio_data)} bytes) → routing to Meet mic stream...")
            
            if not self.is_initialized:
                await self.initialize()
            
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            self.is_playing_audio = True
            
            result = await self.page.evaluate("""
                async ([audioBase64]) => {
                    try {
                        // 1. Decode base64 → ArrayBuffer
                        const binaryString = atob(audioBase64);
                        const bytes = new Uint8Array(binaryString.length);
                        for (let i = 0; i < binaryString.length; i++) {
                            bytes[i] = binaryString.charCodeAt(i);
                        }
                        const arrayBuffer = bytes.buffer;
                        
                        // 2. Decode audio with AudioContext
                        if (!window.audioContext) {
                            window.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                        }
                        const audioContext = window.audioContext;
                        if (audioContext.state === 'suspended') {
                            await audioContext.resume();
                        }
                        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer.slice(0));
                        
                        // 3. Create a MediaStreamDestination — audio sent here becomes a MediaStream track
                        if (!window.botMicDestination) {
                            window.botMicDestination = audioContext.createMediaStreamDestination();
                        }
                        const destination = window.botMicDestination;
                        
                        // 4. Route audio buffer → destination node
                        const source = audioContext.createBufferSource();
                        source.buffer = audioBuffer;
                        source.connect(destination);
                        source.connect(audioContext.destination); // also play locally for monitoring
                        source.start(0);
                        
                        // 5. Replace mic track in ALL active RTCPeerConnections (Google Meet's WebRTC)
                        const botAudioTrack = destination.stream.getAudioTracks()[0];
                        if (botAudioTrack) {
                            const peerConnections = window._botPeerConnections || [];
                            for (const pc of peerConnections) {
                                if (pc.connectionState === 'connected') {
                                    const senders = pc.getSenders().filter(s => s.track && s.track.kind === 'audio');
                                    for (const sender of senders) {
                                        await sender.replaceTrack(botAudioTrack);
                                    }
                                }
                            }
                            console.log('✅ Audio track injected into', peerConnections.length, 'peer connections');
                        }
                        
                        // 6. Wait for audio to finish
                        return new Promise((resolve) => {
                            source.onended = () => {
                                console.log('✅ TTS playback complete');
                                resolve(true);
                            };
                            // Fallback timeout: audioBuffer.duration + 2 extra seconds
                            setTimeout(() => resolve(true), (audioBuffer.duration + 2) * 1000);
                        });
                        
                    } catch (e) {
                        console.error('❌ TTS play error:', e.message);
                        return false;
                    }
                }
            """, [audio_base64])
            
            self.is_playing_audio = False
            
            if result:
                logger.info("✅ TTS audio played and sent to candidate")
                return True
            else:
                logger.error("❌ TTS audio playback/routing failed")
                return False
                
        except Exception as e:
            self.is_playing_audio = False
            logger.error(f"❌ Error playing TTS audio: {e}")
            return False
    
    async def start_recording_candidate(self) -> bool:
        """
        Start recording candidate's audio from the Meet WebRTC remote stream.
        
        HOW IT WORKS:
        - Uses the remote audio track captured by our RTCPeerConnection interceptor
          (set up during initialize()) instead of getUserMedia (which would capture
          the bot's own local microphone, not the candidate's voice)
        - Falls back to getUserMedia only if no remote stream is available yet
        
        Returns:
            bool: True if recording started successfully
        """
        try:
            logger.info("🎙️ Starting candidate audio recording (from remote WebRTC stream)...")
            
            if not self.is_initialized:
                await self.initialize()
            
            success = await self.page.evaluate("""
                async () => {
                    try {
                        let stream;
                        
                        // Prefer remote stream (candidate's actual voice from Meet)
                        if (window._botRemoteStream && window._botRemoteStream.getAudioTracks().length > 0) {
                            stream = window._botRemoteStream;
                            console.log('✅ Using remote WebRTC stream (candidate voice)');
                        } else {
                            // Fallback: use getUserMedia (captures local mic — useful for testing only)
                            console.warn('⚠️ No remote stream yet, falling back to getUserMedia (local mic)');
                            stream = await navigator.mediaDevices.getUserMedia({
                                audio: {
                                    echoCancellation: true,
                                    noiseSuppression: true,
                                    autoGainControl: true,
                                    sampleRate: 16000
                                }
                            });
                        }
                        
                        // Create MediaRecorder on the chosen stream
                        window.botMediaRecorder = new MediaRecorder(stream, {
                            mimeType: 'audio/webm;codecs=opus',
                            audioBitsPerSecond: 128000
                        });
                        
                        // Clear previous chunks
                        window.botAudioChunks = [];
                        
                        // Store audio chunks as they arrive
                        window.botMediaRecorder.ondataavailable = (event) => {
                            if (event.data.size > 0) {
                                window.botAudioChunks.push(event.data);
                                console.log(`📊 Audio chunk: ${event.data.size} bytes`);
                            }
                        };
                        
                        // Start recording (1 second chunks)
                        window.botMediaRecorder.start(1000);
                        
                        console.log('✅ Recording started');
                        return true;
                        
                    } catch (e) {
                        console.error('❌ Recording failed:', e.message);
                        return false;
                    }
                }
            """)
            
            if success:
                self.is_recording = True
                logger.info("✅ Candidate audio recording started")
                return True
            else:
                logger.error("❌ Failed to start recording")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting recording: {e}")
            return False
    
    async def get_audio_chunk(self) -> Optional[bytes]:
        """
        Get the latest audio chunk from candidate recording.
        
        Returns:
            Optional[bytes]: Audio chunk data or None
        """
        try:
            if not self.is_recording:
                logger.warning("⚠️ Not currently recording")
                return None
            
            # Get latest audio chunk from browser
            chunk_data = await self.page.evaluate("""
                async () => {
                    if (!window.botAudioChunks || window.botAudioChunks.length === 0) {
                        return null;
                    }
                    
                    // Get all chunks and combine
                    const chunks = window.botAudioChunks.splice(0);
                    const blob = new Blob(chunks, { type: 'audio/webm;codecs=opus' });
                    
                    // Convert to base64
                    return new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onloadend = () => {
                            const base64 = reader.result.split(',')[1];
                            resolve(base64);
                        };
                        reader.readAsDataURL(blob);
                    });
                }
            """)
            
            if chunk_data:
                # Decode from base64
                audio_bytes = base64.b64decode(chunk_data)
                logger.debug(f"📥 Retrieved audio chunk: {len(audio_bytes)} bytes")
                return audio_bytes
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting audio chunk: {e}")
            return None
    
    async def stop_recording(self) -> List[bytes]:
        """
        Stop recording and return all captured audio chunks.
        
        Returns:
            List[bytes]: List of audio chunks
        """
        try:
            logger.info("⏹️ Stopping candidate audio recording...")
            
            if not self.is_recording:
                logger.warning("⚠️ Not currently recording")
                return []
            
            # Stop MediaRecorder and get final chunks
            # IMPORTANT: Wait for onstop event so the final ondataavailable chunk is included
            final_chunks = await self.page.evaluate("""
                async () => {
                    try {
                        if (!window.botMediaRecorder) {
                            return [];
                        }
                        
                        // Wait for recorder to fully stop before reading chunks
                        await new Promise((resolve) => {
                            window.botMediaRecorder.onstop = () => resolve();
                            window.botMediaRecorder.stop();
                        });
                        
                        // Now all ondataavailable events have fired — safe to read
                        const chunks = window.botAudioChunks.splice(0);
                        const results = [];
                        
                        for (const chunk of chunks) {
                            const blob = new Blob([chunk], { type: 'audio/webm;codecs=opus' });
                            const base64 = await new Promise((resolve) => {
                                const reader = new FileReader();
                                reader.onloadend = () => {
                                    resolve(reader.result.split(',')[1]);
                                };
                                reader.readAsDataURL(blob);
                            });
                            results.push(base64);
                        }
                        
                        // Stop tracks
                        window.botMediaRecorder.stream.getTracks().forEach(track => track.stop());
                        
                        console.log('✅ Recording stopped, chunks:', results.length);
                        return results;
                        
                    } catch (e) {
                        console.error('❌ Stop recording error:', e);
                        return [];
                    }
                }
            """)
            
            # Decode chunks
            audio_chunks = []
            for chunk_base64 in final_chunks:
                audio_bytes = base64.b64decode(chunk_base64)
                audio_chunks.append(audio_bytes)
            
            self.is_recording = False
            logger.info(f"✅ Recording stopped, {len(audio_chunks)} chunks captured")
            return audio_chunks
            
        except Exception as e:
            self.is_recording = False
            logger.error(f"❌ Error stopping recording: {e}")
            return []
    
    async def wait_for_silence(self, duration: float = 3.0, threshold: float = -40.0, max_wait: float = 45.0) -> bool:
        """
        Wait for candidate to finish speaking by monitoring audio chunk activity.
        Watches how many new audio chunks arrive — when chunks stop coming in,
        the candidate has stopped speaking.
        
        Args:
            duration: Seconds of inactivity before considering silence (default 3s)
            threshold: Unused (kept for API compatibility)
            max_wait: Maximum seconds to wait before forcing stop (default 45s)
            
        Returns:
            bool: True when silence/end-of-answer detected
        """
        try:
            logger.info(f"🔇 Waiting for answer (max {max_wait}s, silence threshold {duration}s)...")
            
            check_interval = 0.5  # Check every 500ms
            last_chunk_count = 0
            silence_start = None
            total_waited = 0.0
            
            # Give candidate at least 2 seconds to start speaking
            await asyncio.sleep(2.0)
            total_waited += 2.0
            
            while total_waited < max_wait:
                # Read current chunk count from browser
                current_chunk_count = await self.page.evaluate("""
                    () => {
                        return window.botAudioChunks ? window.botAudioChunks.length : 0;
                    }
                """)
                
                if current_chunk_count > last_chunk_count:
                    # New audio chunks arriving — candidate is still speaking
                    logger.debug(f"🔊 Audio active ({current_chunk_count} chunks)")
                    last_chunk_count = current_chunk_count
                    silence_start = None  # Reset silence timer
                else:
                    # No new chunks — candidate may have paused
                    if silence_start is None:
                        silence_start = datetime.now()
                        logger.debug("🔇 No new audio, starting silence timer")
                    else:
                        silence_duration = (datetime.now() - silence_start).total_seconds()
                        if silence_duration >= duration:
                            logger.info(f"✅ Silence detected after {total_waited:.1f}s total wait")
                            return True
                
                await asyncio.sleep(check_interval)
                total_waited += check_interval
            
            logger.info(f"⏱️ Max wait time ({max_wait}s) reached, stopping recording")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error waiting for silence: {e}")
            # Return True so recording still stops rather than hanging forever
            return True
    
    async def get_audio_stats(self) -> Dict[str, Any]:
        """
        Get current audio system statistics.
        
        Returns:
            Dict[str, Any]: Audio stats
        """
        try:
            stats = {
                'initialized': self.is_initialized,
                'playing': self.is_playing_audio,
                'recording': self.is_recording,
                'buffer_size': len(self.audio_buffer),
                'timestamp': datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting audio stats: {e}")
            return {}


async def test_audio_integration():
    """
    Test audio integration with a live Meet session.
    """
    from meet_bot_launcher import GoogleMeetAuth
    from meet_bot_joiner import MeetBotJoiner
    import os
    
    # Get credentials
    email = os.getenv('MEET_BOT_EMAIL')
    password = os.getenv('MEET_BOT_PASSWORD')
    
    # Get meeting URL
    meeting_url = input("Enter Google Meet URL: ").strip()
    
    if not meeting_url:
        logger.error("No meeting URL provided")
        return
    
    # Authenticate and join
    auth = GoogleMeetAuth(email=email, password=password, headless=False)
    
    try:
        await auth.initialize()
        await auth.login()
        await auth.navigate_to_meet(meeting_url)
        
        # Join meeting
        joiner = MeetBotJoiner(auth.get_page())
        join_success = await joiner.join_meeting(
            meeting_url=meeting_url,
            disable_camera=True,
            enable_microphone=True,
            bot_name="AI Interview Bot"
        )
        
        if not join_success:
            logger.error("Failed to join meeting")
            return
        
        # Initialize audio integration
        audio = MeetAudioIntegration(auth.get_page())
        await audio.initialize()
        
        # Test: Play a test beep
        logger.info("Playing test audio...")
        # Generate 1 second sine wave beep (440Hz)
        import numpy as np
        sample_rate = 16000
        duration = 1.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        sine_wave = np.sin(2 * np.pi * frequency * t)
        audio_data = (sine_wave * 32767).astype(np.int16).tobytes()
        
        # Note: This is PCM, need to convert to MP3 for browser
        # For now, skip actual playback test
        logger.info("Audio system ready (playback test skipped - needs MP3 encoding)")
        
        # Test: Start recording
        logger.info("Starting audio recording...")
        await audio.start_recording_candidate()
        
        # Record for 10 seconds
        logger.info("Recording for 10 seconds...")
        await asyncio.sleep(10)
        
        # Stop and get chunks
        chunks = await audio.stop_recording()
        logger.info(f"Recorded {len(chunks)} audio chunks")
        
        # Leave meeting
        await joiner.leave_meeting()
        
    finally:
        await auth.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_audio_integration())
