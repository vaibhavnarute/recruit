/**
 * Google Meet Recorder using Puppeteer
 * Automates joining Google Meet and captures audio streams
 */

const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const WebSocket = require('ws');
const EventEmitter = require('events');
const fs = require('fs').promises;
const path = require('path');

// Use stealth plugin to avoid bot detection
puppeteer.use(StealthPlugin());

/**
 * Logger utility
 */
class Logger {
    static log(level, message, data = {}) {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            level,
            message,
            ...data
        };
        console.log(JSON.stringify(logEntry));
    }

    static info(message, data) {
        this.log('INFO', message, data);
    }

    static warn(message, data) {
        this.log('WARN', message, data);
    }

    static error(message, data) {
        this.log('ERROR', message, data);
    }

    static debug(message, data) {
        this.log('DEBUG', message, data);
    }
}

/**
 * Meet Recorder class
 */
class MeetRecorder extends EventEmitter {
    constructor(config) {
        super();
        
        this.sessionId = config.sessionId;
        this.meetUrl = config.meetUrl;
        this.botEmail = config.botEmail;
        this.botPassword = config.botPassword;
        this.websocketUrl = config.websocketUrl || 'ws://localhost:8765';
        
        this.browser = null;
        this.page = null;
        this.websocket = null;
        this.isRecording = false;
        this.audioChunkCount = 0;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
        
        Logger.info('MeetRecorder initialized', {
            sessionId: this.sessionId,
            meetUrl: this.meetUrl,
            botEmail: this.botEmail
        });
    }

    /**
     * Connect to WebSocket server
     */
    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            Logger.info('Connecting to WebSocket', { url: this.websocketUrl });
            
            this.websocket = new WebSocket(this.websocketUrl);
            
            this.websocket.on('open', () => {
                Logger.info('WebSocket connected');
                this.emit('websocket:connected');
                resolve();
            });
            
            this.websocket.on('message', (data) => {
                try {
                    const message = JSON.parse(data);
                    this.handleWebSocketMessage(message);
                } catch (error) {
                    Logger.error('Error parsing WebSocket message', {
                        error: error.message,
                        data: data.toString()
                    });
                }
            });
            
            this.websocket.on('error', (error) => {
                Logger.error('WebSocket error', { error: error.message });
                this.emit('websocket:error', error);
                reject(error);
            });
            
            this.websocket.on('close', () => {
                Logger.warn('WebSocket closed');
                this.emit('websocket:closed');
                this.handleWebSocketReconnect();
            });
            
            // Timeout
            setTimeout(() => {
                if (this.websocket.readyState !== WebSocket.OPEN) {
                    reject(new Error('WebSocket connection timeout'));
                }
            }, 10000);
        });
    }

    /**
     * Handle WebSocket reconnection
     */
    async handleWebSocketReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            Logger.error('Max WebSocket reconnect attempts reached');
            this.emit('error', new Error('WebSocket connection failed'));
            return;
        }
        
        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
        
        Logger.info('Attempting WebSocket reconnect', {
            attempt: this.reconnectAttempts,
            maxAttempts: this.maxReconnectAttempts,
            delay
        });
        
        await new Promise(resolve => setTimeout(resolve, delay));
        
        try {
            await this.connectWebSocket();
            this.reconnectAttempts = 0;
        } catch (error) {
            Logger.error('WebSocket reconnect failed', { error: error.message });
            await this.handleWebSocketReconnect();
        }
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleWebSocketMessage(message) {
        Logger.debug('WebSocket message received', { type: message.type });
        
        switch (message.type) {
            case 'command':
                this.handleCommand(message.command, message.data);
                break;
            case 'acknowledgment':
                Logger.debug('Audio chunk acknowledged', { chunkId: message.chunkId });
                break;
            default:
                Logger.warn('Unknown WebSocket message type', { type: message.type });
        }
    }

    /**
     * Handle commands from server
     */
    async handleCommand(command, data) {
        Logger.info('Received command', { command, data });
        
        switch (command) {
            case 'stop_recording':
                await this.stopRecording();
                break;
            case 'mute':
                await this.toggleMic(false);
                break;
            case 'unmute':
                await this.toggleMic(true);
                break;
            default:
                Logger.warn('Unknown command', { command });
        }
    }

    /**
     * Send message via WebSocket
     */
    sendWebSocketMessage(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(message));
        } else {
            Logger.error('WebSocket not connected, cannot send message');
        }
    }

    /**
     * Start recording session
     */
    async start() {
        try {
            Logger.info('Starting Meet recording session', { sessionId: this.sessionId });
            
            // Connect to WebSocket
            await this.connectWebSocket();
            
            // Launch browser
            await this.launchBrowser();
            
            // Navigate to Meet URL
            await this.navigateToMeet();
            
            // Login with bot account
            await this.login();
            
            // Join the meeting
            await this.joinMeeting();
            
            // Start audio capture
            await this.startAudioCapture();
            
            this.isRecording = true;
            this.emit('recording:started');
            
            Logger.info('Recording session started successfully', {
                sessionId: this.sessionId
            });
            
            // Send session started notification
            this.sendWebSocketMessage({
                type: 'event',
                event: 'session_started',
                sessionId: this.sessionId,
                timestamp: new Date().toISOString()
            });
            
        } catch (error) {
            Logger.error('Error starting recording session', {
                sessionId: this.sessionId,
                error: error.message,
                stack: error.stack
            });
            
            this.emit('error', error);
            
            // Send error notification
            this.sendWebSocketMessage({
                type: 'event',
                event: 'session_failed',
                sessionId: this.sessionId,
                error: error.message,
                timestamp: new Date().toISOString()
            });
            
            await this.cleanup();
            throw error;
        }
    }

    /**
     * Launch Puppeteer browser
     */
    async launchBrowser() {
        Logger.info('Launching browser');
        
        this.browser = await puppeteer.launch({
            headless: false, // Set to true in production
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--use-fake-ui-for-media-stream', // Auto-grant media permissions
                '--use-fake-device-for-media-stream',
                '--disable-web-security',
                '--allow-running-insecure-content',
                '--enable-features=NetworkService',
                '--autoplay-policy=no-user-gesture-required'
            ],
            defaultViewport: {
                width: 1280,
                height: 720
            }
        });
        
        this.page = await this.browser.newPage();
        
        // Set user agent
        await this.page.setUserAgent(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        );
        
        // Enable console logging
        this.page.on('console', msg => {
            Logger.debug('Browser console', {
                type: msg.type(),
                text: msg.text()
            });
        });
        
        // Handle page errors
        this.page.on('error', error => {
            Logger.error('Page error', { error: error.message });
        });
        
        Logger.info('Browser launched successfully');
    }

    /**
     * Navigate to Google Meet URL
     */
    async navigateToMeet() {
        Logger.info('Navigating to Meet URL', { url: this.meetUrl });
        
        await this.page.goto(this.meetUrl, {
            waitUntil: 'networkidle2',
            timeout: 60000
        });
        
        await this.page.waitForTimeout(2000);
        
        Logger.info('Navigated to Meet URL');
    }

    /**
     * Login with bot Google account
     */
    async login() {
        Logger.info('Attempting login', { email: this.botEmail });
        
        try {
            // Check if already logged in
            const isLoggedIn = await this.page.evaluate(() => {
                return document.querySelector('[data-is-logged-in="true"]') !== null;
            });
            
            if (isLoggedIn) {
                Logger.info('Already logged in');
                return;
            }
            
            // Wait for email input
            await this.page.waitForSelector('input[type="email"]', {
                timeout: 10000
            });
            
            // Enter email
            await this.page.type('input[type="email"]', this.botEmail, { delay: 100 });
            await this.page.keyboard.press('Enter');
            await this.page.waitForTimeout(2000);
            
            // Wait for password input
            await this.page.waitForSelector('input[type="password"]', {
                timeout: 10000
            });
            
            // Enter password
            await this.page.type('input[type="password"]', this.botPassword, { delay: 100 });
            await this.page.keyboard.press('Enter');
            
            // Wait for navigation
            await this.page.waitForNavigation({
                waitUntil: 'networkidle2',
                timeout: 30000
            });
            
            Logger.info('Login successful');
            
        } catch (error) {
            Logger.warn('Login may have failed or already logged in', {
                error: error.message
            });
            // Continue anyway - might already be logged in
        }
    }

    /**
     * Join the Google Meet meeting
     */
    async joinMeeting() {
        Logger.info('Attempting to join meeting');
        
        await this.page.waitForTimeout(3000);
        
        // Try to turn off camera
        try {
            const cameraBtnSelector = '[aria-label*="camera" i], [aria-label*="video" i]';
            await this.page.waitForSelector(cameraBtnSelector, { timeout: 5000 });
            
            const isCameraOn = await this.page.evaluate((selector) => {
                const btn = document.querySelector(selector);
                return btn && btn.getAttribute('aria-pressed') === 'true';
            }, cameraBtnSelector);
            
            if (isCameraOn) {
                await this.page.click(cameraBtnSelector);
                Logger.info('Camera turned off');
            }
        } catch (error) {
            Logger.warn('Could not toggle camera', { error: error.message });
        }
        
        // Ensure microphone is ON
        try {
            const micBtnSelector = '[aria-label*="microphone" i], [aria-label*="mic" i]';
            await this.page.waitForSelector(micBtnSelector, { timeout: 5000 });
            
            const isMicOn = await this.page.evaluate((selector) => {
                const btn = document.querySelector(selector);
                return btn && btn.getAttribute('aria-pressed') === 'true';
            }, micBtnSelector);
            
            if (!isMicOn) {
                await this.page.click(micBtnSelector);
                Logger.info('Microphone turned on');
            }
        } catch (error) {
            Logger.warn('Could not toggle microphone', { error: error.message });
        }
        
        // Click join button
        try {
            const joinButtonSelectors = [
                'button[jsname="Qx7Oae"]', // Ask to join
                'button:has-text("Ask to join")',
                'button:has-text("Join now")',
                'button:has-text("Join")',
                '[aria-label*="join" i]'
            ];
            
            let joined = false;
            for (const selector of joinButtonSelectors) {
                try {
                    await this.page.waitForSelector(selector, { timeout: 3000 });
                    await this.page.click(selector);
                    Logger.info('Clicked join button', { selector });
                    joined = true;
                    break;
                } catch (e) {
                    continue;
                }
            }
            
            if (!joined) {
                throw new Error('Could not find join button');
            }
            
            await this.page.waitForTimeout(5000);
            
            Logger.info('Successfully joined meeting');
            
        } catch (error) {
            Logger.error('Error joining meeting', { error: error.message });
            throw error;
        }
    }

    /**
     * Start capturing audio stream
     */
    async startAudioCapture() {
        Logger.info('Starting audio capture');
        
        try {
            // Inject audio capture script
            await this.page.evaluateOnNewDocument(() => {
                window.audioChunks = [];
                window.mediaRecorder = null;
            });
            
            // Start audio recording
            const captureStarted = await this.page.evaluate(async () => {
                try {
                    // Get audio stream
                    const stream = await navigator.mediaDevices.getUserMedia({
                        audio: {
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true
                        }
                    });
                    
                    // Create MediaRecorder
                    const mediaRecorder = new MediaRecorder(stream, {
                        mimeType: 'audio/webm;codecs=opus',
                        audioBitsPerSecond: 128000
                    });
                    
                    window.mediaRecorder = mediaRecorder;
                    
                    // Handle data available
                    mediaRecorder.ondataavailable = (event) => {
                        if (event.data.size > 0) {
                            window.audioChunks.push(event.data);
                        }
                    };
                    
                    // Start recording with 5-second chunks
                    mediaRecorder.start(5000);
                    
                    console.log('MediaRecorder started');
                    return true;
                    
                } catch (error) {
                    console.error('Error starting audio capture:', error);
                    return false;
                }
            });
            
            if (!captureStarted) {
                throw new Error('Failed to start audio capture in browser');
            }
            
            // Start polling for audio chunks
            this.startAudioChunkPolling();
            
            Logger.info('Audio capture started successfully');
            
        } catch (error) {
            Logger.error('Error starting audio capture', { error: error.message });
            throw error;
        }
    }

    /**
     * Poll for audio chunks and send to WebSocket
     */
    startAudioChunkPolling() {
        Logger.info('Starting audio chunk polling');
        
        this.audioPollingInterval = setInterval(async () => {
            try {
                const chunks = await this.page.evaluate(() => {
                    const chunks = window.audioChunks;
                    window.audioChunks = [];
                    return chunks.map(chunk => ({
                        size: chunk.size,
                        type: chunk.type
                    }));
                });
                
                if (chunks.length > 0) {
                    for (const chunk of chunks) {
                        await this.processAudioChunk(chunk);
                    }
                }
                
            } catch (error) {
                Logger.error('Error polling audio chunks', { error: error.message });
            }
        }, 5000);
    }

    /**
     * Process and send audio chunk
     */
    async processAudioChunk(chunkMetadata) {
        this.audioChunkCount++;
        
        const chunkId = `${this.sessionId}_chunk_${this.audioChunkCount}`;
        
        Logger.debug('Processing audio chunk', {
            chunkId,
            size: chunkMetadata.size,
            type: chunkMetadata.type
        });
        
        try {
            // Get actual audio data
            const audioData = await this.page.evaluate(() => {
                const chunks = window.audioChunks;
                if (chunks.length === 0) return null;
                
                const blob = chunks[0];
                return new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        resolve(reader.result.split(',')[1]); // Get base64 data
                    };
                    reader.readAsDataURL(blob);
                });
            });
            
            if (!audioData) {
                Logger.warn('No audio data available');
                return;
            }
            
            // Send to WebSocket
            this.sendWebSocketMessage({
                type: 'audio_chunk',
                sessionId: this.sessionId,
                chunkId: chunkId,
                audioData: audioData,
                format: 'webm',
                size: chunkMetadata.size,
                timestamp: new Date().toISOString()
            });
            
            Logger.debug('Audio chunk sent', { chunkId, size: chunkMetadata.size });
            
        } catch (error) {
            Logger.error('Error processing audio chunk', {
                chunkId,
                error: error.message
            });
        }
    }

    /**
     * Toggle microphone
     */
    async toggleMic(enable) {
        Logger.info('Toggling microphone', { enable });
        
        try {
            await this.page.evaluate((shouldEnable) => {
                const micBtn = document.querySelector('[aria-label*="microphone" i], [aria-label*="mic" i]');
                if (micBtn) {
                    const isMicOn = micBtn.getAttribute('aria-pressed') === 'true';
                    if ((shouldEnable && !isMicOn) || (!shouldEnable && isMicOn)) {
                        micBtn.click();
                    }
                }
            }, enable);
            
            Logger.info('Microphone toggled', { enable });
            
        } catch (error) {
            Logger.error('Error toggling microphone', { error: error.message });
        }
    }

    /**
     * Stop recording session
     */
    async stopRecording() {
        Logger.info('Stopping recording session', { sessionId: this.sessionId });
        
        this.isRecording = false;
        
        try {
            // Stop audio polling
            if (this.audioPollingInterval) {
                clearInterval(this.audioPollingInterval);
                this.audioPollingInterval = null;
            }
            
            // Stop MediaRecorder
            if (this.page) {
                await this.page.evaluate(() => {
                    if (window.mediaRecorder && window.mediaRecorder.state !== 'inactive') {
                        window.mediaRecorder.stop();
                    }
                }).catch(err => {
                    Logger.warn('Error stopping MediaRecorder', { error: err.message });
                });
            }
            
            // Leave meeting
            await this.leaveMeeting();
            
            // Cleanup
            await this.cleanup();
            
            this.emit('recording:stopped');
            
            // Send session stopped notification
            this.sendWebSocketMessage({
                type: 'event',
                event: 'session_stopped',
                sessionId: this.sessionId,
                audioChunksProcessed: this.audioChunkCount,
                timestamp: new Date().toISOString()
            });
            
            Logger.info('Recording session stopped', {
                sessionId: this.sessionId,
                audioChunksProcessed: this.audioChunkCount
            });
            
        } catch (error) {
            Logger.error('Error stopping recording', {
                sessionId: this.sessionId,
                error: error.message
            });
        }
    }

    /**
     * Play audio in Google Meet
     * @param {string} audioBase64 - Base64 encoded audio data
     * @param {string} format - Audio format (mp3, wav, webm)
     * @returns {Promise<Object>} - Result with duration and status
     */
    async playAudio(audioBase64, format = 'mp3') {
        Logger.info('Playing audio in meeting', { 
            format, 
            dataLength: audioBase64.length 
        });
        
        try {
            if (!this.page) {
                throw new Error('Page not initialized');
            }
            
            // Play audio in browser context
            const result = await this.page.evaluate(async (base64Data, audioFormat) => {
                return new Promise((resolve, reject) => {
                    try {
                        // Convert base64 to blob
                        const binaryString = atob(base64Data);
                        const bytes = new Uint8Array(binaryString.length);
                        for (let i = 0; i < binaryString.length; i++) {
                            bytes[i] = binaryString.charCodeAt(i);
                        }
                        
                        // Create blob and object URL
                        const mimeType = audioFormat === 'mp3' ? 'audio/mpeg' : 
                                       audioFormat === 'wav' ? 'audio/wav' : 
                                       'audio/webm';
                        const blob = new Blob([bytes], { type: mimeType });
                        const audioUrl = URL.createObjectURL(blob);
                        
                        // Create and play audio element
                        const audio = new Audio(audioUrl);
                        audio.volume = 1.0;
                        
                        // Track playback
                        let playbackStartTime = Date.now();
                        
                        audio.onended = () => {
                            const duration = (Date.now() - playbackStartTime) / 1000;
                            URL.revokeObjectURL(audioUrl);
                            resolve({
                                success: true,
                                duration,
                                message: 'Audio played successfully'
                            });
                        };
                        
                        audio.onerror = (error) => {
                            URL.revokeObjectURL(audioUrl);
                            reject(new Error(`Audio playback error: ${error.message || 'Unknown error'}`));
                        };
                        
                        // Start playback
                        audio.play().catch(err => {
                            URL.revokeObjectURL(audioUrl);
                            reject(new Error(`Failed to play audio: ${err.message}`));
                        });
                        
                    } catch (error) {
                        reject(new Error(`Audio processing error: ${error.message}`));
                    }
                });
            }, audioBase64, format);
            
            Logger.info('Audio playback completed', result);
            
            this.emit('audio:played', result);
            
            return result;
            
        } catch (error) {
            Logger.error('Error playing audio', { error: error.message });
            throw error;
        }
    }

    /**
     * Leave Google Meet meeting
     */
    async leaveMeeting() {
        Logger.info('Leaving meeting');
        
        try {
            if (this.page) {
                // Click leave button
                const leaveButtonSelectors = [
                    '[aria-label*="leave" i]',
                    '[aria-label*="hang up" i]',
                    'button[jsname="CQylAd"]'
                ];
                
                for (const selector of leaveButtonSelectors) {
                    try {
                        await this.page.waitForSelector(selector, { timeout: 3000 });
                        await this.page.click(selector);
                        Logger.info('Clicked leave button');
                        break;
                    } catch (e) {
                        continue;
                    }
                }
                
                await this.page.waitForTimeout(2000);
            }
            
            Logger.info('Left meeting');
            
        } catch (error) {
            Logger.warn('Error leaving meeting', { error: error.message });
        }
    }

    /**
     * Cleanup resources
     */
    async cleanup() {
        Logger.info('Cleaning up resources');
        
        try {
            // Close WebSocket
            if (this.websocket) {
                this.websocket.close();
                this.websocket = null;
            }
            
            // Close browser
            if (this.browser) {
                await this.browser.close();
                this.browser = null;
                this.page = null;
            }
            
            Logger.info('Cleanup completed');
            
        } catch (error) {
            Logger.error('Error during cleanup', { error: error.message });
        }
    }
}

module.exports = MeetRecorder;

// Export for testing
if (require.main === module) {
    // Test configuration
    const testConfig = {
        sessionId: 'test_session_001',
        meetUrl: 'https://meet.google.com/abc-defg-hij',
        botEmail: process.env.MEET_BOT_EMAIL || 'bot@example.com',
        botPassword: process.env.MEET_BOT_PASSWORD || 'password',
        websocketUrl: 'ws://localhost:8765'
    };
    
    const recorder = new MeetRecorder(testConfig);
    
    recorder.on('recording:started', () => {
        console.log('Recording started!');
    });
    
    recorder.on('recording:stopped', () => {
        console.log('Recording stopped!');
    });
    
    recorder.on('error', (error) => {
        console.error('Recorder error:', error);
        process.exit(1);
    });
    
    // Start recording
    recorder.start().catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
    
    // Stop after 60 seconds for testing
    setTimeout(() => {
        recorder.stopRecording();
    }, 60000);
}
