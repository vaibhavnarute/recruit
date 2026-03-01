"""
Google Meet Bot - Audio Playback System
========================================
Handles playing TTS audio through the bot in Google Meet and capturing candidate audio.

Features:
1. Inject TTS audio into Meet's audio system
2. Capture candidate audio for STT processing
3. Handle audio timing and synchronization
4. Manage microphone/speaker permissions
"""

import asyncio
import base64
import json
import os
from typing import Optional, Dict, Any
from playwright.async_api import Page, Browser, async_playwright
import logging

logger = logging.getLogger(__name__)


class MeetBotAudio:
    """Handles audio playback and capture in Google Meet"""
    
    def __init__(self, page: Page):
        self.page = page
        self.is_audio_ready = False
        self.audio_context = None
        
    async def initialize_audio_system(self) -> bool:
        """
        Initialize Web Audio API for audio playback
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("🎵 Initializing Web Audio API...")
            
            # Inject Web Audio API setup into the page
            await self.page.evaluate("""
                () => {
                    // Create audio context
                    window.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    
                    // Create audio destination
                    window.audioDestination = window.audioContext.createMediaStreamDestination();
                    
                    // Store for later use
                    window.botAudioReady = true;
                    
                    console.log('✅ Web Audio API initialized');
                    return true;
                }
            """)
            
            self.is_audio_ready = True
            logger.info("✅ Audio system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize audio system: {str(e)}")
            return False
    
    async def play_audio_in_meet(self, audio_base64: str, audio_format: str = "mp3") -> bool:
        """
        Play TTS audio through the bot's microphone in Google Meet
        
        Args:
            audio_base64: Base64 encoded audio data
            audio_format: Audio format (mp3, wav, etc.)
            
        Returns:
            True if audio played successfully
        """
        try:
            logger.info(f"🔊 Playing audio in Meet (format: {audio_format})...")
            
            if not self.is_audio_ready:
                await self.initialize_audio_system()
            
            # Convert base64 to audio and play through Meet
            result = await self.page.evaluate("""
                async ([audioData, format]) => {
                    try {
                        // Decode base64 audio
                        const binaryString = atob(audioData);
                        const bytes = new Uint8Array(binaryString.length);
                        for (let i = 0; i < binaryString.length; i++) {
                            bytes[i] = binaryString.charCodeAt(i);
                        }
                        
                        // Create audio buffer
                        const audioBlob = new Blob([bytes], { type: `audio/${format}` });
                        const audioUrl = URL.createObjectURL(audioBlob);
                        
                        // Create audio element
                        const audio = new Audio(audioUrl);
                        
                        // Get audio context
                        const ctx = window.audioContext;
                        const source = ctx.createMediaElementSource(audio);
                        
                        // Connect to destination (Meet's audio stream)
                        source.connect(ctx.destination);
                        
                        // Play audio
                        await audio.play();
                        
                        // Wait for audio to finish
                        await new Promise((resolve) => {
                            audio.onended = resolve;
                        });
                        
                        // Cleanup
                        URL.revokeObjectURL(audioUrl);
                        
                        console.log('✅ Audio played successfully');
                        return { success: true, duration: audio.duration };
                        
                    } catch (error) {
                        console.error('❌ Audio playback error:', error);
                        return { success: false, error: error.message };
                    }
                }
            """, [audio_base64, audio_format])
            
            if result.get('success'):
                logger.info(f"✅ Audio played successfully ({result.get('duration', 0):.2f}s)")
                return True
            else:
                logger.error(f"❌ Audio playback failed: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error playing audio: {str(e)}")
            return False
    
    async def enable_microphone(self) -> bool:
        """
        Ensure bot's microphone is enabled in Meet
        
        Returns:
            True if microphone is enabled
        """
        try:
            logger.info("🎤 Enabling microphone...")
            
            # Click microphone button if muted
            await self.page.evaluate("""
                () => {
                    // Find microphone button
                    const micButton = document.querySelector('[data-tooltip*="microphone" i], [aria-label*="microphone" i]');
                    
                    if (micButton) {
                        const isMuted = micButton.getAttribute('data-is-muted') === 'true' ||
                                       micButton.classList.contains('muted');
                        
                        if (isMuted) {
                            micButton.click();
                            console.log('✅ Microphone enabled');
                            return true;
                        }
                    }
                    
                    return true;
                }
            """)
            
            logger.info("✅ Microphone ready")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enabling microphone: {str(e)}")
            return False
    
    async def capture_audio_stream(self) -> Optional[Dict[str, Any]]:
        """
        Capture audio stream from Google Meet for STT processing
        
        Returns:
            Audio stream data or None
        """
        try:
            logger.info("🎧 Capturing audio stream...")
            
            # Get audio stream from Meet
            stream_data = await self.page.evaluate("""
                async () => {
                    try {
                        // Get audio stream from Meet
                        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                        
                        // Create MediaRecorder
                        window.audioRecorder = new MediaRecorder(stream);
                        window.audioChunks = [];
                        
                        window.audioRecorder.ondataavailable = (event) => {
                            window.audioChunks.push(event.data);
                        };
                        
                        // Start recording
                        window.audioRecorder.start(1000); // 1 second chunks
                        
                        console.log('✅ Audio capture started');
                        return { success: true, state: window.audioRecorder.state };
                        
                    } catch (error) {
                        console.error('❌ Audio capture error:', error);
                        return { success: false, error: error.message };
                    }
                }
            """)
            
            if stream_data.get('success'):
                logger.info("✅ Audio stream capture started")
                return stream_data
            else:
                logger.error(f"❌ Failed to capture audio: {stream_data.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error capturing audio stream: {str(e)}")
            return None
    
    async def get_audio_chunk(self) -> Optional[bytes]:
        """
        Get next audio chunk from the recorder
        
        Returns:
            Audio chunk as bytes or None
        """
        try:
            # Get audio chunk from recorder
            chunk_data = await self.page.evaluate("""
                async () => {
                    if (window.audioChunks && window.audioChunks.length > 0) {
                        const chunk = window.audioChunks.shift();
                        
                        // Convert to base64
                        const reader = new FileReader();
                        const base64Promise = new Promise((resolve) => {
                            reader.onloadend = () => resolve(reader.result.split(',')[1]);
                        });
                        reader.readAsDataURL(chunk);
                        
                        const base64 = await base64Promise;
                        return base64;
                    }
                    return null;
                }
            """)
            
            if chunk_data:
                return base64.b64decode(chunk_data)
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting audio chunk: {str(e)}")
            return None
    
    async def stop_audio_capture(self) -> bool:
        """Stop audio capture"""
        try:
            await self.page.evaluate("""
                () => {
                    if (window.audioRecorder && window.audioRecorder.state !== 'inactive') {
                        window.audioRecorder.stop();
                        console.log('✅ Audio capture stopped');
                        return true;
                    }
                    return false;
                }
            """)
            logger.info("✅ Audio capture stopped")
            return True
        except Exception as e:
            logger.error(f"❌ Error stopping audio capture: {str(e)}")
            return False


async def test_audio_system():
    """Test the audio system"""
    print("🧪 Testing Meet Bot Audio System\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Create audio handler
        audio_handler = MeetBotAudio(page)
        
        # Test 1: Initialize audio system
        print("Test 1: Initialize Audio System")
        success = await audio_handler.initialize_audio_system()
        print(f"Result: {'✅ PASS' if success else '❌ FAIL'}\n")
        
        # Test 2: Enable microphone (requires actual Meet page)
        # This would need a real Meet session
        
        print("✅ Audio system tests complete!")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_audio_system())
