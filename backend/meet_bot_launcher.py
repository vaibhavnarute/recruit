"""
Google Meet Bot Launcher - Authentication & Session Management

This module handles Google account authentication and Meet session initialization
for the AI interview bot. It uses Playwright for browser automation and manages
persistent sessions to avoid repeated logins.

Features:
- Google OAuth authentication with session persistence
- Automatic cookie/token management
- Headless and headed mode support
- Error handling and retry logic
- Session validation and refresh

Author: AI Recruiter Team
Created: February 2026
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeout
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleMeetAuth:
    """
    Handles Google authentication for Meet bot sessions.
    Manages browser context, cookies, and persistent login state.
    """
    
    def __init__(
        self,
        email: str,
        password: str,
        headless: bool = False,
        user_data_dir: Optional[str] = None
    ):
        """
        Initialize Google Meet authentication.
        
        Args:
            email: Google account email
            password: Google account password
            headless: Run browser in headless mode (default: False for debugging)
            user_data_dir: Directory to store persistent browser data
        """
        self.email = email
        self.password = password
        self.headless = headless
        self.user_data_dir = user_data_dir or os.path.join(
            os.getcwd(), "meet_bot_sessions", email.replace("@", "_at_")
        )
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
        # Session state
        self.is_authenticated = False
        self.session_file = os.path.join(self.user_data_dir, "session.json")
        
        # Ensure user data directory exists
        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"GoogleMeetAuth initialized for {email}")
        logger.info(f"Session directory: {self.user_data_dir}")
    
    async def initialize(self) -> None:
        """
        Initialize Playwright browser instance.
        """
        logger.info("Initializing Playwright browser...")
        
        self.playwright = await async_playwright().start()
        
        # Launch browser with persistent context to maintain login
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--use-fake-ui-for-media-stream',  # Auto-allow mic/camera
                '--use-fake-device-for-media-stream',  # Use fake media devices
                '--disable-blink-features=AutomationControlled',  # Hide automation
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu'
            ]
        )
        
        # Create context with persistent storage
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            permissions=['microphone', 'camera'],  # Pre-grant permissions
            storage_state=self.session_file if os.path.exists(self.session_file) else None
        )
        
        self.page = await self.context.new_page()

        # Listen to browser console — only log WebRTC audio info and errors
        def _on_console(msg):
            txt = msg.text
            # Only show WebRTC audio events (not BotAdmit - JS admit removed)
            if '[BotAudio]' in txt or msg.type == 'error':
                logger.info(f"[BROWSER] {txt}")
        self.page.on('console', _on_console)

        # CRITICAL FIX: Install RTCPeerConnection interceptor BEFORE any page loads.
        # This runs as an init script on every navigation, so when Google Meet creates
        # its WebRTC connections, they are captured in window._botPeerConnections.
        # Without this, initialize() in MeetAudioIntegration runs AFTER RTCPeerConnections
        # are already established and window._botPeerConnections stays empty → TTS fails.
        await self.page.add_init_script("""
            window._botPeerConnections = [];
            window._botRemoteStream   = null;
            window.botAudioChunks     = [];
            window.botMediaRecorder   = null;
            window.botMicDestination  = null;
            window.audioContext       = null;

            const _OriginalRTCPC = window.RTCPeerConnection;
            window.RTCPeerConnection = function(...args) {
                const pc = new _OriginalRTCPC(...args);
                window._botPeerConnections.push(pc);

                pc.addEventListener('track', (event) => {
                    if (event.track.kind === 'audio') {
                        window._botRemoteStream = event.streams[0] || new MediaStream([event.track]);
                        console.log('[BotAudio] Remote audio track captured from candidate');
                    }
                });

                pc.addEventListener('connectionstatechange', () => {
                    console.log('[BotAudio] PC state:', pc.connectionState,
                                '| total PCs:', window._botPeerConnections.length);
                    if (pc.connectionState === 'closed' || pc.connectionState === 'failed') {
                        window._botPeerConnections = window._botPeerConnections.filter(p => p !== pc);
                    }
                });

                console.log('[BotAudio] RTCPeerConnection #' + window._botPeerConnections.length + ' created');
                return pc;
            };
            Object.assign(window.RTCPeerConnection, _OriginalRTCPC);
            window.RTCPeerConnection.prototype = _OriginalRTCPC.prototype;
            console.log('[BotAudio] RTCPeerConnection interceptor installed ✅');
        """)

        logger.info("Browser initialized successfully (WebRTC interceptor installed)")
    
    async def login(self, force_reauth: bool = False) -> bool:
        """
        Authenticate with Google account.
        
        Strategy: MANUAL LOGIN ONCE → session saved → auto-reused forever.
        Google blocks automated logins (CAPTCHAs, challenges, etc.), so
        instead of fighting it, we let the user log in manually ONE TIME
        in the Playwright browser window. The session is saved and reused
        on all future runs (typically valid for weeks).
        
        Args:
            force_reauth: Force re-authentication even if session exists
            
        Returns:
            bool: True if authentication successful
        """
        logger.info(f"Starting Google authentication for {self.email}...")
        
        # Check if we have a valid saved session
        if not force_reauth and await self._validate_session():
            logger.info("✅ Existing session is valid, skipping login")
            self.is_authenticated = True
            return True
        
        # No valid session — need manual login
        try:
            logger.info("="*60)
            logger.info("🔐 MANUAL LOGIN REQUIRED (one-time only)")
            logger.info("="*60)
            logger.info("")
            logger.info("A browser window will open to Google's login page.")
            logger.info(f"Please log in as: {self.email}")
            logger.info("Complete ALL steps (password, 2FA, etc.)")
            logger.info("Once you see your Google account page, we'll save the session.")
            logger.info("You will NOT need to do this again until the session expires.")
            logger.info("")
            logger.info("="*60)
            
            # Navigate to Google login
            await self.page.goto(
                'https://accounts.google.com/signin',
                wait_until='domcontentloaded',
                timeout=30000
            )
            
            # Wait for user to complete login manually
            # Detect success by checking if URL changes to a logged-in page
            logger.info("⏳ Waiting for you to complete login in the browser...")
            logger.info("   (You have 5 minutes)")
            
            max_wait = 300  # 5 minutes
            check_interval = 2  # Check every 2 seconds
            waited = 0
            
            logged_in_indicators = [
                'myaccount.google.com',
                'meet.google.com',
                'mail.google.com',
                'drive.google.com',
                'google.com/search',
                'accounts.google.com/b/',  # Multi-account view
            ]
            
            # URLs that mean still logging in
            still_logging_in = [
                'accounts.google.com/signin',
                'accounts.google.com/v3/signin',
                'accounts.google.com/ServiceLogin',
                'accounts.google.com/challenge',
                'accounts.google.com/speedbump',
                'accounts.google.com/interstitial',
            ]
            
            while waited < max_wait:
                await asyncio.sleep(check_interval)
                waited += check_interval
                
                current_url = self.page.url
                
                # Check if we landed on a logged-in page
                if any(indicator in current_url for indicator in logged_in_indicators):
                    logger.info(f"✅ Login detected! URL: {current_url}")
                    break
                
                # Check if we're past all login/challenge pages
                still_on_login = any(login_url in current_url for login_url in still_logging_in)
                
                if not still_on_login and 'google.com' in current_url:
                    # We're on some google page that isn't login — probably logged in
                    logger.info(f"✅ Login appears complete! URL: {current_url}")
                    break
                
                # Progress updates
                if waited % 30 == 0:
                    logger.info(f"   Still waiting... ({max_wait - waited}s remaining)")
                    logger.info(f"   Current URL: {current_url}")
            
            if waited >= max_wait:
                logger.error("❌ Login timeout — 5 minutes elapsed")
                return False
            
            # Give a moment for page to settle
            await asyncio.sleep(2)
            
            # Verify login by navigating to myaccount
            await self.page.goto('https://myaccount.google.com', wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(2)
            
            is_logged_in = await self._check_login_status()
            
            if is_logged_in:
                logger.info("✅ Google authentication successful!")
                await self._save_session()
                self.is_authenticated = True
                logger.info("")
                logger.info("="*60)
                logger.info("🎉 Session saved! You won't need to login again.")
                logger.info("="*60)
                return True
            else:
                logger.error("❌ Authentication failed — could not verify login")
                try:
                    debug_path = os.path.join(self.user_data_dir, 'debug_login_failed.png')
                    await self.page.screenshot(path=debug_path)
                    logger.error(f"📸 Screenshot: {debug_path}")
                except Exception:
                    pass
                return False
                
        except Exception as e:
            logger.error(f"❌ Error during authentication: {e}")
            return False
    
    async def _check_login_status(self) -> bool:
        """
        Check if currently logged into Google account.
        
        Returns:
            bool: True if logged in
        """
        try:
            # Check for account profile elements
            profile_button = await self.page.query_selector('[aria-label*="Google Account"]')
            if profile_button:
                return True
            
            # Alternative check - look for user email
            page_content = await self.page.content()
            if self.email.split('@')[0] in page_content:
                return True
            
            return False
        except Exception as e:
            logger.warning(f"Error checking login status: {e}")
            return False
    
    async def _validate_session(self) -> bool:
        """
        Validate existing session by navigating to meet.google.com.
        If Google redirects us to accounts.google.com, the session is expired.
        """
        if not os.path.exists(self.session_file):
            logger.info("No session file found")
            return False

        try:
            logger.info("Validating existing session...")
            await self.page.goto(
                'https://meet.google.com',
                wait_until='domcontentloaded',
                timeout=20000
            )
            await asyncio.sleep(2)

            current_url = self.page.url
            # If still on meet.google.com, session is valid
            if 'meet.google.com' in current_url and 'accounts.google.com' not in current_url:
                logger.info("Session is valid \u2713")
                return True

            logger.info("Session expired or invalid (redirected to login)")
            return False

        except Exception as e:
            logger.warning(f"Session validation failed: {e}")
            return False
    
    async def _save_session(self) -> None:
        """
        Save current browser session state (cookies, tokens).
        """
        try:
            logger.info("Saving session state...")
            
            # Save storage state (cookies, localStorage, sessionStorage)
            await self.context.storage_state(path=self.session_file)
            
            # Save metadata
            metadata = {
                'email': self.email,
                'saved_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
            }
            
            metadata_file = os.path.join(self.user_data_dir, "metadata.json")
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"✅ Session saved to {self.session_file}")
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    async def navigate_to_meet(self, meeting_url: str) -> bool:
        """
        Navigate to Google Meet meeting URL.
        
        Args:
            meeting_url: Full Google Meet URL (https://meet.google.com/xxx-xxxx-xxx)
            
        Returns:
            bool: True if navigation successful
        """
        if not self.is_authenticated:
            logger.error("Cannot navigate to Meet - not authenticated")
            return False
        
        try:
            logger.info(f"Navigating to Meet: {meeting_url}")
            await self.page.goto(meeting_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # Check if we're on the Meet page
            current_url = self.page.url
            if 'meet.google.com' in current_url:
                logger.info("✅ Successfully navigated to Meet")
                return True
            else:
                logger.error(f"Navigation failed - ended up at: {current_url}")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to Meet: {e}")
            return False
    
    async def create_meeting_as_host(self) -> Optional[str]:
        """
        Create a new Google Meet instant meeting where the bot is the HOST.

        By navigating to https://meet.google.com/new while authenticated as the bot,
        Google creates a fresh Meet room and the bot becomes the meeting owner/host.
        As host, the bot can admit participants directly (no waiting room approval needed).

        Returns:
            str: The Google Meet URL (e.g. https://meet.google.com/abc-defg-hij)
                 or None if creation failed.
        """
        if not self.is_authenticated:
            logger.error("Cannot create meeting - not authenticated")
            return None

        try:
            logger.info("🎥 Creating new Google Meet (bot as host)...")

            await self.page.goto(
                "https://meet.google.com/new",
                wait_until="domcontentloaded",
                timeout=60000
            )
            # Meet pages have constant WebSocket activity, so wait for redirect
            await asyncio.sleep(8)

            current_url = self.page.url
            logger.info(f"URL after /new: {current_url}")

            # If redirected to Google login, session cookies didn't cover Meet
            # Force a full re-login and retry once
            if 'accounts.google.com' in current_url:
                logger.warning("⚠️ Session expired for meet.google.com, forcing re-login...")
                self.is_authenticated = False
                reauth_ok = await self.login(force_reauth=True)
                if not reauth_ok:
                    logger.error("❌ Re-authentication failed")
                    return None

                # Retry after re-login
                await self.page.goto(
                    "https://meet.google.com/new",
                    wait_until="domcontentloaded",
                    timeout=60000
                )
                await asyncio.sleep(8)
                current_url = self.page.url
                logger.info(f"URL after re-login retry: {current_url}")

            # Extract meeting URL
            meet_url = None
            if "meet.google.com/" in current_url:
                meet_url = current_url.split("?")[0].rstrip("/")
                room_code = meet_url.split("/")[-1]
                if len(room_code) >= 8 and "-" in room_code:
                    logger.info(f"✅ Meeting created: {meet_url} (host: {self.email})")
                else:
                    meet_url = None

            # Fallback: check for data-meeting-code attribute
            if not meet_url:
                for selector in ['[data-meeting-code]', 'c-wiz[data-meeting-code]']:
                    try:
                        el = await self.page.query_selector(selector)
                        if el:
                            code = await el.get_attribute("data-meeting-code") or ""
                            if code:
                                meet_url = f"https://meet.google.com/{code}"
                                logger.info(f"✅ Meeting created via attribute: {meet_url}")
                                break
                    except Exception:
                        pass

            if not meet_url:
                logger.error(f"❌ Could not extract meeting URL from: {current_url}")
                return None

            # ============================================================
            # CRITICAL: Actually JOIN the meeting by clicking "Join now"
            # Without this, bot is on pre-join screen and can't host/admit
            # ============================================================
            join_success = await self._join_created_meeting()
            if join_success:
                logger.info(f"🎉 Bot successfully created AND joined meeting: {meet_url}")
            else:
                logger.warning(f"⚠️ Meeting created ({meet_url}) but bot may not have joined!")

            return meet_url

        except Exception as e:
            logger.error(f"❌ Error creating meeting: {e}")
            return None

    async def _join_created_meeting(self) -> bool:
        """
        Confirm the bot is in the meeting after creating it via /new.

        KEY INSIGHT: When a Google account creates a meeting via meet.google.com/new,
        it is AUTOMATICALLY placed in the meeting — there is no pre-join screen.
        The in-meeting UI (mic/camera/leave buttons) appears immediately.

        Previous code pressed Ctrl+D (which is the MIC TOGGLE shortcut, not join),
        which muted the bot's microphone. This version avoids that entirely.
        """
        try:
            logger.info("🎥 Confirming bot is in meeting (after /new creation)...")
            await asyncio.sleep(4)  # Wait for Meet UI to fully render

            # Screenshot: what does the bot see?
            ss_path = f"meet_BEFORE_join_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await self.page.screenshot(path=ss_path)
            logger.info(f"📸 Screenshot: {ss_path}")

            # Dump page text for diagnosis
            page_text = await self.page.evaluate("() => document.body.innerText")
            logger.info(f"📄 Page text snippet: {page_text[:400].replace(chr(10), ' | ')}")

            # Check if already in-meeting (mic/camera/leave controls visible)
            in_meeting_state = await self.page.evaluate("""() => {
                const mic  = document.querySelector('button[aria-label*="microphone" i]');
                const leave = document.querySelector('button[aria-label*="Leave" i], button[aria-label*="End call" i]');
                const joinBtn = document.querySelector('button[aria-label*="Join now" i]');
                const bodyText = document.body.innerText.toLowerCase();
                return {
                    hasMic:    !!mic,
                    micLabel:  mic  ? mic.getAttribute('aria-label')  : null,
                    hasLeave:  !!leave,
                    hasJoinBtn: !!joinBtn,
                    hasMicText:  bodyText.includes('microphone'),
                    hasCameraText: bodyText.includes('camera'),
                    hasLeaveText: bodyText.includes('leave call') || bodyText.includes('end call'),
                };
            }""")
            logger.info(f"In-meeting state: {in_meeting_state}")

            is_in_meeting = (
                in_meeting_state.get('hasMic') or
                in_meeting_state.get('hasLeave') or
                in_meeting_state.get('hasMicText') or
                in_meeting_state.get('hasLeaveText')
            ) and not in_meeting_state.get('hasJoinBtn')

            if not is_in_meeting:
                # Pre-join screen detected — try clicking join buttons
                logger.info("⚠️ Pre-join screen detected, clicking 'Join now'...")
                for sel in [
                    'button:has-text("Join now")', 'button:has-text("Join")',
                    'button:has-text("Ask to join")', 'button[aria-label*="Join now" i]',
                    'div[role="button"]:has-text("Join now")',
                ]:
                    try:
                        btn = await self.page.wait_for_selector(sel, timeout=2000)
                        if btn and await btn.is_visible():
                            logger.info(f"Found join button via '{sel}', clicking...")
                            await btn.click()
                            await asyncio.sleep(5)
                            is_in_meeting = True
                            break
                    except Exception:
                        continue

            if is_in_meeting:
                # Bring the bot's browser to the FOREGROUND.
                # Google Meet only shows admission notifications reliably when
                # the browser window is the active foreground window.
                try:
                    await self.page.bring_to_front()
                    logger.info("🪟 Bot browser brought to foreground")
                except Exception:
                    pass

                # Ensure microphone is ON (do NOT press Ctrl+D — that toggles mic!)
                await self._ensure_mic_on()

                # NOTE: We deliberately skip _disable_waiting_room() here.
                # Reason: opening the Host Controls panel and then closing it
                # can leave a side-panel overlay that BLOCKS the "Admit" toast
                # from being clickable when the candidate knocks.
                # The auto-admit loop handles admission perfectly without it.
                # (Proven by earlier successful test runs.)

                after_ss = f"meet_AFTER_join_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.page.screenshot(path=after_ss)
                logger.info(f"📸 Post-join screenshot: {after_ss}")

                # NOTE: JS auto-admit (MutationObserver) is intentionally NOT used here.
                # Reason: JS el.click() is an UNTRUSTED synthetic event — React/Google Meet
                # ignores it. The button stays in the DOM, observer fires again on next
                # DOM mutation (even the clock ticking!), creating an infinite CPU loop that
                # starves the Python Playwright trusted clicks (which DO work).
                # Python Playwright page.click(force=True) IS a trusted event → React handles it.

                logger.info("✅ Bot is confirmed IN the meeting as host!")
                return True
            else:
                logger.error("❌ Could not confirm bot in meeting!")
                err_ss = f"meet_join_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.page.screenshot(path=err_ss, full_page=True)
                logger.error(f"📸 Debug screenshot: {err_ss}")
                return False

        except Exception as e:
            logger.error(f"❌ _join_created_meeting error: {e}", exc_info=True)
            return False

    async def _install_js_auto_admit(self) -> None:
        """
        Install a JavaScript MutationObserver + interval inside Google Meet's page.

        This is the MOST RELIABLE admit approach because it:
        - Runs inside the browser (no Python polling delay)
        - Reacts INSTANTLY (within one DOM mutation frame) when Admit appears
        - Also polls every 800ms as backup
        - Logs every admit to browser console for debugging

        The observer persists for the entire duration of the meeting.
        """
        try:
            result = await self.page.evaluate("""() => {
                if (window._botAdmitInstalled) return 'already installed';

                // Click helper: tries bare click, then full MouseEvent sequence
                function safeClick(el) {
                    try { el.click(); } catch(e) {}
                    try {
                        el.dispatchEvent(new MouseEvent('mousedown', {bubbles:true, cancelable:true, view:window}));
                        el.dispatchEvent(new MouseEvent('mouseup',   {bubbles:true, cancelable:true, view:window}));
                        el.dispatchEvent(new MouseEvent('click',     {bubbles:true, cancelable:true, view:window}));
                    } catch(e) {}
                    // Also try clicking the parent (Google Meet sometimes wraps buttons in a div)
                    try {
                        const parent = el.closest('div[class], li, [data-prober]');
                        if (parent && parent !== el) {
                            parent.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}));
                        }
                    } catch(e) {}
                }

                function tryAdmitAll() {
                    let admitted = 0;
                    const keywords = ['admit', 'admit all', 'accept', 'accept all'];
                    const elements = document.querySelectorAll(
                        'button, div[role="button"], span[role="button"]'
                    );
                    for (const el of elements) {
                        const text = (el.innerText || '').trim().toLowerCase();
                        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 5 && rect.height > 5) {
                            for (const kw of keywords) {
                                if (text === kw || text.startsWith(kw)
                                        || aria.includes(kw)) {
                                    safeClick(el);
                                    admitted++;
                                    console.log('[BotAdmit] ✅ Clicked admit:', text || aria);
                                    break;
                                }
                            }
                        }
                    }

                    // Also look for "wants to join" spans and click nearby buttons
                    if (admitted === 0) {
                        const spans = document.querySelectorAll('span, div, p');
                        for (const sp of spans) {
                            const t = (sp.innerText || '').toLowerCase();
                            if (t.includes('wants to join') || t.includes('asking to join')
                                    || (t.includes('waiting') && t.length < 50)) {
                                const container = sp.closest('[class]');
                                if (container) {
                                    const btn = container.querySelector('button');
                                    if (btn && btn.getBoundingClientRect().width > 0) {
                                        safeClick(btn);
                                        admitted++;
                                        console.log('[BotAdmit] ✅ Clicked near waiting text:', t);
                                    }
                                }
                            }
                        }
                    }
                    return admitted;
                }

                // MutationObserver: fires immediately on ANY DOM change
                const observer = new MutationObserver(() => {
                    const n = tryAdmitAll();
                    if (n > 0) console.log('[BotAdmit] Observer admitted:', n);
                });
                observer.observe(document.body, { childList: true, subtree: true });

                // Backup interval: every 800ms (catches cases observer misses)
                setInterval(() => {
                    const n = tryAdmitAll();
                    if (n > 0) console.log('[BotAdmit] Interval admitted:', n);
                }, 800);

                window._botAdmitInstalled = true;
                console.log('[BotAdmit] ✅ JS auto-admit MutationObserver + interval installed');
                return 'installed';
            }""")
            logger.info(f"✅ JS auto-admit installed in browser: {result}")
        except Exception as e:
            logger.warning(f"⚠️ Could not install JS auto-admit: {e}")

    async def _ensure_mic_on(self) -> None:
        """Ensure the bot's microphone is ON (enabled) inside the meeting."""
        try:
            mic_btn = await self.page.query_selector('button[aria-label*="microphone" i]')
            if mic_btn:
                aria = await mic_btn.get_attribute('aria-label') or ''
                logger.info(f"Mic button aria-label: '{aria}'")
                if 'turn on' in aria.lower():
                    logger.warning("🎤 Mic was MUTED — enabling now...")
                    await mic_btn.click()
                    await asyncio.sleep(1)
                    logger.info("🎤 Microphone enabled ✅")
                else:
                    logger.info("🎤 Microphone already ON ✅")
            else:
                logger.warning("⚠️ Could not find microphone button")
        except Exception as e:
            logger.warning(f"⚠️ Error enabling mic: {e}")



    async def _disable_waiting_room(self) -> None:
        """
        Try to configure host controls so participants can join without manual approval.

        Google Meet 2024+: Host controls panel shows toggles like:
          • "Quick access"         → ON = anyone with link can join instantly
          • "Host must join first" → OFF = others can join without host present
        
        This method opens the host controls panel and tries to find + enable "Quick access".
        If that toggle isn't found (UI changes frequently), we just log the available toggles
        and rely on the auto-admit loop as fallback.
        """
        try:
            logger.info("🔧 Configuring host controls...")
            await asyncio.sleep(2)

            # Open host controls panel
            host_opened = False
            host_selectors = [
                'button[aria-label*="Host controls" i]',
                'button[aria-label*="host control" i]',
                'button[aria-label*="Safety" i]',
                'button[aria-label*="meeting safety" i]',
                'button[data-tooltip*="Host controls" i]',
            ]
            for sel in host_selectors:
                try:
                    btn = await self.page.wait_for_selector(sel, timeout=3000)
                    if btn:
                        await btn.click()
                        host_opened = True
                        await asyncio.sleep(1.5)
                        logger.info(f"Host controls opened via: {sel}")
                        break
                except Exception:
                    continue

            if not host_opened:
                logger.info("ℹ️ Host controls button not found — relying on auto-admit fallback")
                return

            # Enumerate ALL toggles to understand current Meet UI
            toggles = await self.page.query_selector_all(
                'div[role="switch"], input[type="checkbox"], button[role="switch"]'
            )
            logger.info(f"Found {len(toggles)} toggle(s) in host controls panel")
            
            quick_access_enabled = False
            for toggle in toggles:
                try:
                    label   = await toggle.get_attribute('aria-label') or ''
                    checked = await toggle.get_attribute('aria-checked') or ''
                    # Get surrounding text for context
                    ctx = await toggle.evaluate(
                        "el => (el.closest('div[class]') || el).innerText"
                    ) or ''
                    ctx_short = ctx.replace('\n', ' ')[:80]
                    logger.info(f"  Toggle: label='{label}' checked='{checked}' ctx='{ctx_short}'")

                    label_lower = label.lower()
                    ctx_lower   = ctx.lower()

                    # Enable "Quick access" (lets anyone with link join without asking)
                    if 'quick access' in label_lower or 'quick access' in ctx_lower:
                        if checked != 'true':
                            logger.info("🔓 Enabling 'Quick access' toggle")
                            await toggle.click()
                            await asyncio.sleep(1)
                            quick_access_enabled = True
                        else:
                            logger.info("✅ 'Quick access' already ON")
                            quick_access_enabled = True

                    # Disable "Host must join first" (allows participants to join before host)
                    elif ('host must join' in ctx_lower or 'host must join' in label_lower):
                        if checked == 'true':
                            logger.info("🔓 Disabling 'Host must join first' toggle")
                            await toggle.click()
                            await asyncio.sleep(1)

                except Exception as e:
                    logger.debug(f"Toggle error: {e}")
                    continue

            if not quick_access_enabled:
                logger.info(
                    "ℹ️ 'Quick access' toggle not found in current Meet UI — "
                    "auto-admit loop will handle admission requests"
                )

            # Close panel — press Escape then click the meeting video area
            # to ensure focus returns to the main meeting UI.
            # Just pressing Escape can leave panel partially open in some Meet versions.
            try:
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(0.5)
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(0.5)
                # Click on the main video area (center of screen) to dismiss any lingering panels
                viewport = self.page.viewport_size or {'width': 1920, 'height': 1080}
                cx = viewport['width'] // 2
                cy = viewport['height'] // 2
                await self.page.mouse.click(cx, cy)
                await asyncio.sleep(0.5)
                logger.info("Host controls panel closed (Escape x2 + center click)")
            except Exception:
                pass

            logger.info("✅ Host controls configuration complete")

        except Exception as e:
            logger.info(f"ℹ️ Host controls config skipped (non-critical): {e}")



    async def close(self) -> None:
        """
        Close browser and cleanup resources.
        """
        logger.info("Closing browser and cleaning up...")
        
        if self.page:
            await self.page.close()
        
        if self.context:
            await self.context.close()
        
        if self.browser:
            await self.browser.close()
        
        if self.playwright:
            await self.playwright.stop()
        
        logger.info("✅ Cleanup complete")
    
    def get_page(self) -> Page:
        """
        Get the current Playwright page instance.
        
        Returns:
            Page: Playwright page object
        """
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")
        return self.page


async def main():
    """
    Test Google Meet authentication.
    """
    # Get credentials from environment or use test values
    email = os.getenv('MEET_BOT_EMAIL', 'your-email@gmail.com')
    password = os.getenv('MEET_BOT_PASSWORD', 'your-password')
    
    if email == 'your-email@gmail.com':
        logger.error("❌ Please set MEET_BOT_EMAIL and MEET_BOT_PASSWORD environment variables")
        logger.error("Example: set MEET_BOT_EMAIL=your-email@gmail.com")
        logger.error("Example: set MEET_BOT_PASSWORD=your-password")
        return
    
    # Create authenticator
    auth = GoogleMeetAuth(
        email=email,
        password=password,
        headless=False  # Set to True for production
    )
    
    try:
        # Initialize browser
        await auth.initialize()
        
        # Login to Google
        success = await auth.login()
        
        if success:
            logger.info("🎉 Authentication successful!")
            logger.info("You can now use this session to join Google Meet calls")
            
            # Keep browser open for manual testing
            logger.info("Browser will remain open for 30 seconds for testing...")
            await asyncio.sleep(30)
        else:
            logger.error("❌ Authentication failed")
    
    finally:
        # Cleanup
        await auth.close()


if __name__ == "__main__":
    asyncio.run(main())
