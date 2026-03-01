"""
Google Meet Bot - Meeting Join & Setup

This module handles joining Google Meet meetings, managing permissions,
and preparing the bot for conducting interviews.

Features:
- Auto-join meeting functionality
- Permission handling (microphone/camera)
- UI element detection and interaction
- Pre-join setup (mute/unmute, camera off)
- Error handling for common join issues

Author: AI Recruiter Team
Created: February 2026
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout, expect
from datetime import datetime

logger = logging.getLogger(__name__)


class MeetBotJoiner:
    """
    Handles joining Google Meet meetings and initial setup.
    """
    
    def __init__(self, page: Page):
        """
        Initialize Meet bot joiner.
        
        Args:
            page: Playwright page instance (already authenticated)
        """
        self.page = page
        self.is_in_meeting = False
        self.meeting_code = None
        
    async def join_meeting(
        self,
        meeting_url: str,
        disable_camera: bool = True,
        enable_microphone: bool = True,
        bot_name: Optional[str] = None
    ) -> bool:
        """
        Join a Google Meet meeting.
        
        Args:
            meeting_url: Full Google Meet URL (https://meet.google.com/xxx-xxxx-xxx)
            disable_camera: Keep camera disabled (default: True)
            enable_microphone: Enable microphone for speaking (default: True)
            bot_name: Optional display name for the bot
            
        Returns:
            bool: True if successfully joined meeting
        """
        try:
            logger.info(f"Attempting to join meeting: {meeting_url}")
            
            # Extract meeting code
            self.meeting_code = self._extract_meeting_code(meeting_url)
            logger.info(f"Meeting code: {self.meeting_code}")
            
            # Navigate to meeting URL
            logger.info("Navigating to meeting URL...")
            await self.page.goto(meeting_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)
            
            # Handle pre-join screen
            logger.info("Setting up pre-join configuration...")
            await self._handle_pre_join_screen(disable_camera, enable_microphone)
            
            # Set display name if provided
            if bot_name:
                await self._set_display_name(bot_name)
            
            # Check if we're already in the meeting (direct join)
            logger.info("Checking if already in meeting...")
            already_in = await self._verify_in_meeting()
            
            if already_in:
                logger.info("✅ Already in the meeting (direct join)!")
                self.is_in_meeting = True
                return True
            
            # Check if we got rejected before even trying to join
            page_text = await self.page.text_content('body')
            if page_text and "can't join" in page_text.lower():
                logger.error("❌ Meeting rejected bot before join attempt")
                logger.error("Solutions:")
                logger.error("  1. Invite airecruiterbot@gmail.com to the meeting")
                logger.error("  2. Change meeting settings to 'Anyone with link can join'")
                return False
            
            # Click "Join now" or "Ask to join" button
            logger.info("Clicking 'Join now' button...")
            join_success = await self._click_join_button()
            
            if not join_success:
                logger.error("Failed to find/click join button")
                return False
            
            # Wait for meeting to load or check if we need approval
            logger.info("Waiting for meeting to load...")
            await asyncio.sleep(3)
            
            # Check if we're waiting for host approval
            is_waiting = await self._check_waiting_for_approval()
            if is_waiting:
                logger.warning("⏳ Waiting for host to admit bot to the meeting...")
                logger.warning("NOTE: Make sure the meeting allows the bot's email or admits it manually")
                
                # Wait up to 2 minutes for host to admit
                admitted = await self._wait_for_admission(timeout=120)
                if not admitted:
                    logger.error("❌ Host did not admit bot to meeting")
                    logger.error("Solutions:")
                    logger.error("  1. Invite airecruiterbot@gmail.com to the meeting")
                    logger.error("  2. Change meeting settings to 'Anyone with link can join'")
                    logger.error("  3. Manually admit the bot when it asks to join")
                    return False
            
            # Additional wait for meeting interface to load
            await asyncio.sleep(5)
            
            # Verify we're in the meeting
            is_joined = await self._verify_in_meeting()
            
            if is_joined:
                self.is_in_meeting = True
                logger.info("✅ Successfully joined the meeting!")
                return True
            else:
                logger.error("❌ Failed to join meeting - verification failed")
                return False
                
        except PlaywrightTimeout as e:
            logger.error(f"Timeout while joining meeting: {e}")
            return False
        except Exception as e:
            logger.error(f"Error joining meeting: {e}")
            return False
    
    async def _handle_pre_join_screen(self, disable_camera: bool, enable_microphone: bool) -> None:
        """
        Configure settings on the pre-join screen.
        
        Args:
            disable_camera: Turn off camera
            enable_microphone: Turn on microphone
        """
        try:
            # Wait for pre-join controls to appear
            await asyncio.sleep(2)
            
            # Handle camera
            if disable_camera:
                logger.info("Ensuring camera is disabled...")
                # Try to find camera button and click if it's enabled
                camera_button = await self.page.query_selector('button[aria-label*="camera" i], button[aria-label*="Turn off camera" i]')
                if camera_button:
                    # Check if camera is currently on (button says "turn off")
                    aria_label = await camera_button.get_attribute('aria-label')
                    if aria_label and 'turn off' in aria_label.lower():
                        logger.info("Clicking to disable camera...")
                        await camera_button.click()
                        await asyncio.sleep(1)
                    else:
                        logger.info("Camera already disabled")
            
            # Handle microphone
            if enable_microphone:
                logger.info("Ensuring microphone is enabled...")
                mic_button = await self.page.query_selector('button[aria-label*="microphone" i], button[aria-label*="Turn on microphone" i]')
                if mic_button:
                    aria_label = await mic_button.get_attribute('aria-label')
                    if aria_label and 'turn on' in aria_label.lower():
                        logger.info("Clicking to enable microphone...")
                        await mic_button.click()
                        await asyncio.sleep(1)
                    else:
                        logger.info("Microphone already enabled")
            else:
                logger.info("Ensuring microphone is disabled...")
                mic_button = await self.page.query_selector('button[aria-label*="microphone" i], button[aria-label*="Turn off microphone" i]')
                if mic_button:
                    aria_label = await mic_button.get_attribute('aria-label')
                    if aria_label and 'turn off' in aria_label.lower():
                        logger.info("Clicking to disable microphone...")
                        await mic_button.click()
                        await asyncio.sleep(1)
            
            logger.info("Pre-join configuration complete")
            
        except Exception as e:
            logger.warning(f"Error configuring pre-join settings: {e}")
            # Continue anyway - not critical
    
    async def _set_display_name(self, name: str) -> None:
        """
        Set display name in pre-join screen.
        
        Args:
            name: Display name for the bot
        """
        try:
            logger.info(f"Setting display name to: {name}")
            
            # Look for name input field
            name_input = await self.page.query_selector('input[placeholder*="name" i], input[aria-label*="name" i]')
            
            if name_input:
                # Clear existing name and enter new one
                await name_input.click()
                await name_input.fill('')
                await asyncio.sleep(0.5)
                await name_input.fill(name)
                logger.info(f"Display name set to: {name}")
            else:
                logger.warning("Could not find name input field")
                
        except Exception as e:
            logger.warning(f"Error setting display name: {e}")
            # Not critical, continue
    
    async def _click_join_button(self) -> bool:
        """
        Click the "Join now" button to enter the meeting.
        
        Returns:
            bool: True if button was found and clicked
        """
        try:
            # Wait a bit for page to fully load
            await asyncio.sleep(2)
            
            # Debug: Log all buttons on the page
            logger.info("Searching for join button...")
            all_buttons = await self.page.query_selector_all('button, div[role="button"]')
            logger.info(f"Found {len(all_buttons)} clickable elements on page")
            
            # Log first few button texts for debugging
            for i, button in enumerate(all_buttons[:10]):
                try:
                    text = await button.inner_text()
                    aria_label = await button.get_attribute('aria-label')
                    logger.info(f"Button {i}: text='{text}', aria-label='{aria_label}'")
                except:
                    pass
            
            # Multiple possible selectors for join button
            join_selectors = [
                'button[aria-label*="Ask to join" i]',
                'button[aria-label*="Join now" i]',
                'button[aria-label*="join" i]',
                'button:has-text("Ask to join")',
                'button:has-text("Join now")',
                'button:has-text("Join")',
                'div[role="button"]:has-text("Ask to join")',
                'div[role="button"]:has-text("Join now")',
                'div[role="button"]:has-text("Join")',
                'span:has-text("Ask to join")',
                'span:has-text("Join now")',
            ]
            
            for selector in join_selectors:
                try:
                    button = await self.page.wait_for_selector(selector, timeout=2000)
                    if button:
                        logger.info(f"✓ Found join button with selector: {selector}")
                        await button.click()
                        logger.info("Join button clicked")
                        return True
                except PlaywrightTimeout:
                    continue
            
            # Try to find any button/div with "join" in text or aria-label
            logger.info("Trying text-based search...")
            for button in all_buttons:
                try:
                    text = await button.inner_text()
                    aria_label = await button.get_attribute('aria-label') or ''
                    
                    # Clean up text (remove whitespace, newlines)
                    text_clean = text.strip().lower() if text else ''
                    aria_clean = aria_label.strip().lower() if aria_label else ''
                    
                    if 'join' in text_clean or 'join' in aria_clean:
                        logger.info(f"✓ Found join element - text: '{text}', aria-label: '{aria_label}'")
                        
                        # Click the button
                        await button.click()
                        logger.info("Join button clicked successfully!")
                        return True
                except Exception as e:
                    logger.debug(f"Error checking button: {e}")
                    continue
            
            logger.error("Could not find join button with any method")
            
            # Save screenshot for debugging
            screenshot_path = f"meet_join_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await self.page.screenshot(path=screenshot_path)
            logger.info(f"Saved debug screenshot to: {screenshot_path}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error clicking join button: {e}")
            return False
    
    async def _check_waiting_for_approval(self) -> bool:
        """
        Check if we're waiting for host approval to join.
        
        Returns:
            bool: True if waiting for approval
        """
        try:
            # Check for rejection message
            rejection_text = await self.page.text_content('body')
            if rejection_text and "can't join" in rejection_text.lower():
                logger.error("❌ Meeting rejected bot - security settings prevent joining")
                return False
            
            # Check for waiting message
            waiting_indicators = [
                'text="Asking to join"',
                'text="Waiting for the host to let you in"',
                'text="Someone will let you in soon"',
                ':has-text("Asking to join")',
                ':has-text("let you in")',
            ]
            
            for indicator in waiting_indicators:
                try:
                    element = await self.page.wait_for_selector(indicator, timeout=2000)
                    if element:
                        return True
                except PlaywrightTimeout:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking approval status: {e}")
            return False
    
    async def _wait_for_admission(self, timeout: int = 120) -> bool:
        """
        Wait for host to admit bot to meeting.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if admitted to meeting
        """
        logger.info(f"Waiting up to {timeout} seconds for host admission...")
        
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout:
            try:
                # Check if we're now in the meeting
                is_in = await self._verify_in_meeting()
                if is_in:
                    logger.info("✅ Host admitted bot to meeting!")
                    return True
                
                # Check if we got rejected
                rejection_text = await self.page.text_content('body')
                if rejection_text and "can't join" in rejection_text.lower():
                    logger.error("❌ Bot was rejected from meeting")
                    return False
                
                # Still waiting
                elapsed = int((datetime.now() - start_time).total_seconds())
                if elapsed % 10 == 0:
                    logger.info(f"Still waiting for admission... ({timeout - elapsed}s remaining)")
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.debug(f"Error waiting for admission: {e}")
                await asyncio.sleep(2)
        
        return False
    
    async def _verify_in_meeting(self) -> bool:
        """
        Verify that we successfully joined the meeting.
        
        Returns:
            bool: True if we're in the meeting
        """
        try:
            # CRITICAL: Check for rejection FIRST
            page_text = await self.page.text_content('body')
            if page_text:
                if "can't join" in page_text.lower():
                    logger.error("❌ Bot was REJECTED from meeting")
                    return False
                if "returning to home screen" in page_text.lower():
                    logger.error("❌ Bot was kicked out of meeting")
                    return False
            
            # Look for elements that indicate we're in a meeting
            indicators = [
                # Meeting controls (mute, camera, etc.)
                'button[aria-label*="Turn off microphone" i]',
                'button[aria-label*="Turn on microphone" i]',
                # Leave call button (most reliable)
                'button[aria-label*="Leave call" i]',
                'button[aria-label*="call_end" i]',
                # Participant count
                'div[aria-label*="participant" i]',
            ]
            
            for selector in indicators:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        logger.info(f"✓ Found meeting indicator: {selector}")
                        
                        # Double-check we're not on rejection page
                        current_text = await self.page.text_content('body')
                        if current_text and "can't join" not in current_text.lower():
                            return True
                except PlaywrightTimeout:
                    continue
            
            logger.warning("Could not verify meeting join - no indicators found")
            return False
            
        except Exception as e:
            logger.error(f"Error verifying meeting join: {e}")
            return False
    
    async def wait_for_participants(self, min_participants: int = 2, timeout: int = 300) -> bool:
        """
        Wait for minimum number of participants to join.
        Automatically admits anyone waiting in the lobby.
        
        Args:
            min_participants: Minimum number of participants (including bot)
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if required participants joined
        """
        logger.info(f"Waiting for at least {min_participants} participants...")
        logger.info("🔓 Auto-admit is ON — will admit anyone who knocks")
        
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout:
            try:
                # Auto-admit anyone waiting in the lobby
                admitted = await self._auto_admit_participants()
                if admitted > 0:
                    logger.info(f"🔓 Admitted {admitted} participant(s) — waiting 5s for them to fully join...")
                    await asyncio.sleep(5)  # Give time for candidate to fully join
                
                # Check participant count
                participant_count = await self._get_participant_count()
                
                if participant_count >= min_participants:
                    logger.info(f"✅ {participant_count} participants in meeting")
                    return True
                
                elapsed = int((datetime.now() - start_time).total_seconds())
                if elapsed % 15 == 0:
                    logger.info(f"Currently {participant_count} participant(s), waiting... ({timeout - elapsed}s left)")
                
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.warning(f"Error checking participants: {e}")
                await asyncio.sleep(3)
        
        logger.warning(f"Timeout waiting for participants (waited {timeout}s)")
        return False
    
    async def _auto_admit_participants(self) -> int:
        """
        Auto-admit all participants waiting in the lobby.

        Strategy:
        1. Collect ALL admit-related buttons from the DOM (deduplicated by element).
        2. Click each ONE time with a normal Playwright click (no force — trusted event).
        3. If nothing found, try waiting-notification selectors.
        4. If still nothing, use JS as last resort.

        Returns:
            int: Number of participants admitted
        """
        admitted = 0
        clicked_els = set()  # Track element handles to avoid duplicate clicks

        try:
            # ── Method 1: Trusted Playwright click on visible Admit buttons ────────
            admit_selectors = [
                'button:has-text("Admit all")',
                'button:has-text("Accept all")',
                'button:has-text("Admit")',
                'button:has-text("Accept")',
                'button[aria-label*="Admit" i]',
            ]

            for selector in admit_selectors:
                try:
                    buttons = await self.page.query_selector_all(selector)
                    for btn in buttons:
                        try:
                            # Use element's JS identity to deduplicate
                            el_id = await btn.evaluate('el => el.outerHTML.substring(0, 120)')
                            if el_id in clicked_els:
                                continue
                            clicked_els.add(el_id)

                            text = (await btn.inner_text() or '').strip()
                            logger.info(f"🔓 Clicking admit button: '{text}'")
                            try:
                                await btn.click(timeout=3000)
                            except Exception:
                                continue
                            admitted += 1
                            await asyncio.sleep(1)  # Brief pause between clicks
                        except Exception as ce:
                            logger.debug(f"Admit click error: {ce}")
                            continue
                except Exception as se:
                    logger.debug(f"Admit selector error '{selector}': {se}")
                    continue

            # ── Method 2: Waiting-notification banner → then find Admit ──────────
            if admitted == 0:
                try:
                    waiting_selectors = [
                        'button:has-text("View all")',
                        'div:has-text("wants to join")',
                        'div:has-text("is waiting")',
                    ]
                    for ws in waiting_selectors:
                        waiting_el = await self.page.query_selector(ws)
                        if waiting_el and await waiting_el.is_visible():
                            logger.info(f"Found waiting notification: '{ws}' — clicking...")
                            await waiting_el.click()
                            await asyncio.sleep(1)
                            # Re-scan for admit buttons after revealing them
                            for sel in admit_selectors:
                                btns = await self.page.query_selector_all(sel)
                                for b in btns:
                                    try:
                                        if await b.is_visible():
                                            text = (await b.inner_text() or '').strip()
                                            logger.info(f"🔓 Post-banner admit: '{text}'")
                                            await b.click()
                                            admitted += 1
                                            await asyncio.sleep(0.5)
                                    except Exception:
                                        continue
                            break
                except Exception:
                    pass

            # ── Method 3 REMOVED (People panel toggling caused UI disruption) ────

            # ── Method 4: JavaScript fallback — last resort ───────────────────────
            if admitted == 0:
                try:
                    js_result = await self.page.evaluate("""() => {
                        let count = 0;
                        const allElements = document.querySelectorAll('button, div[role="button"]');
                        for (const el of allElements) {
                            const text = (el.innerText || '').trim().toLowerCase();
                            const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                if (text === 'admit' || text === 'admit all'
                                    || aria.includes('admit')) {
                                    el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                                    count++;
                                }
                            }
                        }
                        
                        // Also check for "wants to join" / "waiting" notifications and click them
                        if (count === 0) {
                            const spans = document.querySelectorAll('span, div');
                            for (const sp of spans) {
                                const t = (sp.innerText || '').toLowerCase();
                                if ((t.includes('wants to join') || t.includes('waiting') || t.includes('asking to join'))
                                    && sp.getBoundingClientRect().width > 0) {
                                    // Click parent or nearby admit button
                                    const parent = sp.closest('div[class]');
                                    if (parent) {
                                        const admitBtn = parent.querySelector('button');
                                        if (admitBtn) {
                                            admitBtn.click();
                                            count++;
                                        }
                                    }
                                }
                            }
                        }
                        
                        return count;
                    }""")
                    if js_result and js_result > 0:
                        logger.info(f"🔓 JS auto-admit: admitted {js_result} participant(s)")
                        admitted += js_result
                except Exception:
                    pass
            
        except Exception as e:
            logger.debug(f"Auto-admit check error (non-critical): {e}")
        
        return admitted
    
    async def _get_participant_count(self) -> int:
        """
        Get current number of participants IN the meeting (admitted, not waiting).

        Google Meet badge jsname='ocqpFe' shows the participant count.
        Video elements are the most reliable indicator.

        Returns:
            int: Number of participants (at least 1 for the bot itself)
        """
        import re
        try:
            # PRIMARY: JavaScript multi-strategy count (fastest, most accurate)
            js_count = await self.page.evaluate("""() => {
                // Strategy 1: Count <video> elements (each participant streams video even if camera off)
                const videos = document.querySelectorAll('video');
                if (videos.length >= 2) return videos.length;

                // Strategy 2: participant count badge (jsname="ocqpFe" or "nav9Xe")
                for (const sel of ['[jsname="ocqpFe"]', '[jsname="nav9Xe"]']) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const txt = (el.innerText || el.textContent || '').trim();
                        const n = parseInt(txt);
                        if (!isNaN(n) && n >= 1) {
                            if (n >= 2) return n;
                        }
                    }
                }

                // Strategy 3: data-participant-id tiles
                const tiles = document.querySelectorAll('[data-participant-id]');
                if (tiles.length >= 1) return tiles.length;

                // Strategy 4: video elements (even 1 video means bot is there)
                if (videos.length >= 1) return videos.length;

                return 1;
            }""")
            if js_count and js_count > 0:
                logger.debug(f"Participant count (JS primary): {js_count}")
                return js_count

            # FALLBACK: aria-label based buttons
            people_selectors = [
                'button[aria-label*="participant" i]',
                'button[aria-label*="people" i]',
                'button[aria-label*="Show everyone" i]',
                'button[aria-label*="person" i]',
                'button[data-tooltip*="people" i]',
                'button[data-tooltip*="participant" i]',
            ]
            for sel in people_selectors:
                try:
                    btn = await self.page.query_selector(sel)
                    if btn:
                        aria = await btn.get_attribute('aria-label') or ''
                        tooltip = await btn.get_attribute('data-tooltip') or ''
                        text = await btn.inner_text() or ''
                        combined = f"{aria} {tooltip} {text}"
                        numbers = re.findall(r'\d+', combined)
                        if numbers:
                            count = int(numbers[0])
                            logger.debug(f"Participant count from '{sel}': {count} (text: '{combined[:60]}')") 
                            return count
                except Exception:
                    continue
            
            # Method 2: Count video tiles / participant elements
            tile_selectors = [
                'div[data-participant-id]',
                'div[data-self-name]',
                'div[data-requested-participant-id]',
            ]
            for sel in tile_selectors:
                tiles = await self.page.query_selector_all(sel)
                if tiles and len(tiles) > 0:
                    return len(tiles)
            
            # Method 3: JavaScript-based — multiple strategies
            js_count = await self.page.evaluate("""() => {
                // Strategy A: [data-participant-id] tiles
                let pids = document.querySelectorAll('[data-participant-id]');
                if (pids.length > 0) return pids.length;

                // Strategy B: Google Meet participant count badge (top-right "1"/"2" button)
                // jsname="ocqpFe" is the participant count badge in current Meet UI
                const badgeSelectors = [
                    '[jsname="ocqpFe"]',
                    '[jsname="nav9Xe"]',
                    '[data-count]',
                ];
                for (const sel of badgeSelectors) {
                    const badge = document.querySelector(sel);
                    if (badge) {
                        const text = (badge.innerText || badge.textContent || '').trim();
                        const num = parseInt(text);
                        if (!isNaN(num) && num > 0) return num;
                    }
                }

                // Strategy C: people/participant button aria-label numbers
                const btns = document.querySelectorAll('button');
                for (const b of btns) {
                    const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                    const tip  = (b.getAttribute('data-tooltip') || '').toLowerCase();
                    if (aria.includes('people') || aria.includes('participant') ||
                        aria.includes('everyone') || tip.includes('people')) {
                        const nums = (aria + ' ' + tip + ' ' + (b.innerText||'')).match(/\\d+/g);
                        if (nums) return parseInt(nums[0]);
                    }
                }

                // Strategy D: Count video elements (each participant has one)
                const videos = document.querySelectorAll('video');
                if (videos.length > 0) return videos.length;

                return 1;
            }""")
            if js_count and js_count > 0:
                logger.debug(f"Participant count from JS: {js_count}")
                return js_count

            # Default: assume at least 1 (the bot itself)
            return 1
            
        except Exception as e:
            logger.warning(f"Error getting participant count: {e}")
            return 1
    
    async def enable_microphone(self) -> bool:
        """
        Ensure microphone is enabled during the meeting.
        
        Returns:
            bool: True if microphone is enabled
        """
        try:
            logger.info("Checking microphone status...")
            
            # Find microphone button
            mic_button = await self.page.query_selector('button[aria-label*="microphone" i]')
            
            if not mic_button:
                logger.error("Could not find microphone button")
                return False
            
            aria_label = await mic_button.get_attribute('aria-label')
            
            # If button says "Turn on", click it
            if 'turn on' in aria_label.lower():
                logger.info("Enabling microphone...")
                await mic_button.click()
                await asyncio.sleep(1)
                logger.info("✅ Microphone enabled")
                return True
            else:
                logger.info("Microphone already enabled")
                return True
                
        except Exception as e:
            logger.error(f"Error enabling microphone: {e}")
            return False
    
    async def disable_microphone(self) -> bool:
        """
        Mute microphone during the meeting.
        
        Returns:
            bool: True if microphone is disabled
        """
        try:
            logger.info("Muting microphone...")
            
            mic_button = await self.page.query_selector('button[aria-label*="microphone" i]')
            
            if not mic_button:
                logger.error("Could not find microphone button")
                return False
            
            aria_label = await mic_button.get_attribute('aria-label')
            
            # If button says "Turn off", click it
            if 'turn off' in aria_label.lower():
                await mic_button.click()
                await asyncio.sleep(1)
                logger.info("✅ Microphone muted")
                return True
            else:
                logger.info("Microphone already muted")
                return True
                
        except Exception as e:
            logger.error(f"Error muting microphone: {e}")
            return False
    
    async def leave_meeting(self) -> bool:
        """
        Leave the current meeting.
        
        Returns:
            bool: True if successfully left
        """
        try:
            logger.info("Leaving meeting...")
            
            # Find leave button
            leave_selectors = [
                'button[aria-label*="Leave call" i]',
                'button[aria-label*="End call" i]',
                'button:has-text("Leave call")',
                'button:has-text("End call")',
            ]
            
            for selector in leave_selectors:
                try:
                    button = await self.page.wait_for_selector(selector, timeout=3000)
                    if button:
                        await button.click()
                        logger.info("✅ Left meeting")
                        self.is_in_meeting = False
                        return True
                except PlaywrightTimeout:
                    continue
            
            logger.error("Could not find leave button")
            return False
            
        except Exception as e:
            logger.error(f"Error leaving meeting: {e}")
            return False
    
    def _extract_meeting_code(self, meeting_url: str) -> str:
        """
        Extract meeting code from URL.
        
        Args:
            meeting_url: Full Google Meet URL
            
        Returns:
            str: Meeting code (e.g., 'abc-defg-hij')
        """
        # Extract code from URLs like:
        # https://meet.google.com/abc-defg-hij
        # https://meet.google.com/lookup/abc-defg-hij
        parts = meeting_url.rstrip('/').split('/')
        return parts[-1]


async def test_join_meeting():
    """
    Test joining a Google Meet meeting.
    """
    from meet_bot_launcher import GoogleMeetAuth
    import os
    
    # Get credentials
    email = os.getenv('MEET_BOT_EMAIL')
    password = os.getenv('MEET_BOT_PASSWORD')
    
    # Get meeting URL from user
    meeting_url = input("Enter Google Meet URL: ").strip()
    
    if not meeting_url or not meeting_url.startswith('https://meet.google.com'):
        logger.error("Invalid meeting URL")
        return
    
    # Authenticate
    auth = GoogleMeetAuth(email=email, password=password, headless=False)
    
    try:
        await auth.initialize()
        
        # Login (will use cached session)
        success = await auth.login()
        if not success:
            logger.error("Authentication failed")
            return
        
        # Navigate to meeting
        await auth.navigate_to_meet(meeting_url)
        
        # Create joiner and join meeting
        joiner = MeetBotJoiner(auth.get_page())
        
        join_success = await joiner.join_meeting(
            meeting_url=meeting_url,
            disable_camera=True,
            enable_microphone=True,
            bot_name="AI Interview Bot"
        )
        
        if join_success:
            logger.info("🎉 Successfully joined meeting!")
            
            # Wait for participants
            logger.info("Waiting for candidate to join...")
            await joiner.wait_for_participants(min_participants=2, timeout=120)
            
            # Stay in meeting for testing
            logger.info("Staying in meeting for 60 seconds...")
            await asyncio.sleep(60)
            
            # Leave meeting
            await joiner.leave_meeting()
        else:
            logger.error("Failed to join meeting")
    
    finally:
        await auth.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_join_meeting())
