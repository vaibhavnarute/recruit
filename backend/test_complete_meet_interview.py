"""
Complete Google Meet Interview - End-to-End Test
================================================
Flow:
  1. Bot authenticates & creates meeting as HOST
  2. Candidate joins via browser → bot auto-admits
  3. Interview runs: TTS questions → STT answers → LLM analysis → MongoDB save

All output is logged to both console AND a timestamped log file.
"""

import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# ── Logging setup (FIRST, before any imports that log) ────────────────────
log_file = f"interview_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger("TEST")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from meet_bot_launcher import GoogleMeetAuth
from meet_bot_joiner import MeetBotJoiner
from meet_audio_integration import MeetAudioIntegration
from interview_orchestrator import MeetInterviewOrchestrator

load_dotenv()

SEP = "=" * 70


# ═══════════════════════════════════════════════════════════════════════════
# STEP 1 — Create Meeting as HOST
# ═══════════════════════════════════════════════════════════════════════════

async def create_test_meeting() -> Optional[Dict[str, Any]]:
    """Authenticate bot, create meeting, auto-join. Returns auth + metadata."""
    print(f"\n{SEP}")
    print("📅 STEP 1: Bot Creates Google Meet as Host")
    print(SEP)

    candidate_name = input("Candidate Name (default: Test Candidate): ").strip() or "Test Candidate"
    job_title      = input("Job Title     (default: Software Engineer): ").strip() or "Software Engineer"

    bot_email    = os.getenv("MEET_BOT_EMAIL")
    bot_password = os.getenv("MEET_BOT_PASSWORD")

    if not bot_email or not bot_password:
        logger.error("❌ MEET_BOT_EMAIL / MEET_BOT_PASSWORD not set in .env")
        return None

    logger.info(f"Bot account : {bot_email} | Candidate: {candidate_name} | Role: {job_title}")

    auth = GoogleMeetAuth(email=bot_email, password=bot_password, headless=False)

    try:
        logger.info("Initializing browser with WebRTC interceptor...")
        await auth.initialize()

        logger.info("Logging in (using saved session if available)...")
        if not await auth.login():

            logger.error("❌ Bot login failed — check credentials in .env")
            return None

        logger.info("Creating Google Meet...")
        meet_link = await auth.create_meeting_as_host()
        if not meet_link:
            logger.error("❌ Could not create meeting URL")
            return None

        logger.info(f"✅ Meeting created: {meet_link}")
        print(f"\n   ✅ Meeting ready: {meet_link}")
        print(f"   🤖 Host: {bot_email}")
        print(f"   👤 Candidate: {candidate_name} ({job_title})")

        return {
            "meet_link": meet_link,
            "candidate_name": candidate_name,
            "job_title": job_title,
            "auth": auth,
        }

    except Exception:
        logger.error("❌ Meeting creation failed", exc_info=True)
        try:
            await auth.close()
        except Exception:
            pass
        return None


# ═══════════════════════════════════════════════════════════════════════════
# STEP 2 — Auto-Admit Loop (background task)
# ═══════════════════════════════════════════════════════════════════════════

async def run_auto_admit_loop(page, stop_event: asyncio.Event) -> None:
    """
    Runs every 1 second until stop_event is set.

    KEY LOGIC:
    - Every second: bring browser to front + look for Admit buttons
    - If a trusted Playwright click on an Admit button succeeds → candidate IS
      being admitted. We trust it immediately and set stop_event.
    - Do NOT rely on _get_participant_count() to decide if candidate joined —
      it often returns 1 even when candidate is in the meeting (because the bot
      has camera OFF → only 1 video element visible, badge timing issues, etc.)
    """
    joiner = MeetBotJoiner(page)
    joiner.is_in_meeting = True
    cycle = 0
    total_admitted = 0
    consecutive_errors = 0

    logger.info("🔓 Auto-admit loop STARTED")
    print("\n   🔓 Auto-admit ACTIVE — waiting for candidate to click 'Ask to join'...")
    print(f"   📄 Full log file: {log_file}")
    print()

    # Bring browser to foreground once at start
    try:
        await page.bring_to_front()
        await asyncio.sleep(0.5)
    except Exception:
        pass
    logger.info("Bot browser brought to foreground. Watching for Admit toast...")

    while not stop_event.is_set():
        cycle += 1
        try:
            # ── Page health check ─────────────────────────────────────────
            current_url = page.url
            if 'meet.google.com' not in current_url:
                logger.error(f"[cycle={cycle}] ❌ Bot left Google Meet! URL: {current_url}")
                print(f"\n   ❌ ERROR: Bot browser left Meet! ({current_url})")
                break

            # ── Bring bot browser to FOREGROUND every cycle ───────────────
            try:
                await page.bring_to_front()
            except Exception:
                pass

            # ── Try to admit ───────────────────────────────────────────────
            admitted = await joiner._auto_admit_participants()

            if admitted > 0:
                total_admitted += admitted
                msg = f"[cycle={cycle}] ✅ ADMITTED {admitted} participant(s)! (total={total_admitted})"
                logger.info(msg)
                print(f"\n   🔓 {msg}")

                # CRITICAL: Trust the Playwright admit click. If we clicked Admit,
                # the candidate IS joining. Wait 6s for them to fully connect,
                # then signal interview to start. Do NOT wait for count check.
                logger.info("⏳ Waiting 6s for candidate to fully connect after admit...")
                await asyncio.sleep(6)

                logger.info("✅ Candidate admitted & connected — starting interview!")
                print(f"\n   ✅ Candidate admitted! Starting interview...")
                stop_event.set()
                return
            else:
                logger.debug(f"[cycle={cycle}] No admit buttons found — watching...")

            # ── Status print every 5 cycles ───────────────────────────────
            if cycle % 5 == 1:
                print(
                    f"   👀 [cycle {cycle:04d}] Watching for 'Ask to join' toast... "
                    f"| url={current_url.split('/')[-1]}   ",
                    end="\r",
                )
                logger.info(f"[cycle={cycle}] Watching for admit toast | url={current_url.split('/')[-1]}")

            # ── Periodic screenshot (every 30 cycles = ~30 sec) ─────────────
            if cycle % 30 == 1:
                try:
                    ss = f"admit_diag_cycle{cycle:04d}_{datetime.now().strftime('%H%M%S')}.png"
                    await page.screenshot(path=ss)
                    logger.info(f"[cycle={cycle}] 📸 Diagnostic screenshot: {ss}")
                except Exception:
                    pass

            consecutive_errors = 0

        except asyncio.CancelledError:
            logger.info("Auto-admit loop cancelled")
            return
        except Exception as exc:
            consecutive_errors += 1
            logger.error(
                f"[cycle={cycle}] Auto-admit ERROR #{consecutive_errors}: "
                f"{type(exc).__name__}: {exc}",
                exc_info=True,
            )
            if consecutive_errors >= 5:
                print(f"\n   ⚠️ Auto-admit errored {consecutive_errors} times: {type(exc).__name__}: {exc}")
                print(f"      Check: {log_file}")

        await asyncio.sleep(1)


# ═══════════════════════════════════════════════════════════════════════════
# STEP 3 — Run Interview
# ═══════════════════════════════════════════════════════════════════════════

async def run_interview(
    auth: GoogleMeetAuth,
    interview_id: str,
    meet_url: str,
    candidate_name: str,
    job_title: str,
) -> Dict[str, Any]:
    """Run the full interview on the EXISTING browser session."""
    print(f"\n{SEP}")
    print("🎤 STEP 3: Running Interview")
    print(SEP)

    try:
        orchestrator = MeetInterviewOrchestrator()
        orchestrator.interview_id = interview_id
        orchestrator.session_id = f"session_{interview_id}_{int(datetime.now().timestamp())}"
        orchestrator.auth = auth

        page = auth.get_page()
        orchestrator.joiner = MeetBotJoiner(page)
        orchestrator.joiner.is_in_meeting = True

        # ── Verify bot is in meeting ────────────────────────────────────────
        is_in = await orchestrator.joiner._verify_in_meeting()
        logger.info(f"Bot in-meeting verification: {is_in}")
        print(f"   🤖 Bot in meeting: {'✅ YES' if is_in else '⚠️ uncertain (continuing anyway)'}")

        # ── Log WebRTC state (critical for TTS to reach candidate) ─────────
        pc_info = await page.evaluate("""
            () => ({
                peerConnections: (window._botPeerConnections || []).length,
                remoteStream: !!(window._botRemoteStream),
                remoteStreamTracks: window._botRemoteStream ? window._botRemoteStream.getTracks().length : 0
            })
        """)
        logger.info(f"WebRTC state: {pc_info}")
        print(f"   📡 WebRTC peer connections: {pc_info.get('peerConnections', 0)}")
        print(f"   🎙️  Remote audio stream captured: {'✅ YES' if pc_info.get('remoteStream') else '❌ NO (candidate audio may not be recorded)'}")

        if pc_info.get('peerConnections', 0) == 0:
            logger.warning("⚠️ No RTCPeerConnections captured — TTS may not reach candidate via Meet mic")

        # ── Initialize audio ────────────────────────────────────────────────
        orchestrator.audio = MeetAudioIntegration(page)
        audio_ok = await orchestrator.audio.initialize()
        logger.info(f"Audio initialized: {audio_ok}")
        print(f"   🎵 Audio system: {'✅ Ready' if audio_ok else '❌ Failed (will attempt anyway)'}")

        # ── Ensure microphone is ON ─────────────────────────────────────────
        try:
            mic_btn = await page.query_selector('button[aria-label*="microphone" i]')
            if mic_btn:
                aria = await mic_btn.get_attribute('aria-label') or ''
                logger.info(f"Mic button aria-label: '{aria}'")
                if 'turn on' in aria.lower():
                    logger.warning("🎤 Microphone was MUTED — enabling now!")
                    await mic_btn.click()
                    await asyncio.sleep(1)
                    print("   🎤 Microphone was muted — re-enabled ✅")
                else:
                    print(f"   🎤 Microphone: ON ✅")
            else:
                logger.warning("Could not find microphone button")
        except Exception as e:
            logger.warning(f"Mic check error: {e}")

        # ── Load questions ──────────────────────────────────────────────────
        print(f"\n   📋 Loading interview questions for: {job_title}")
        await orchestrator._load_questions(job_title)
        logger.info(f"Loaded {len(orchestrator.questions)} questions")
        print(f"   ✅ {len(orchestrator.questions)} questions ready")
        for i, q in enumerate(orchestrator.questions, 1):
            logger.info(f"  Q{i}: {q.get('question_text', q.get('text', ''))[:100]}")

        # ── Greet candidate ─────────────────────────────────────────────────
        print(f"\n   👋 Greeting: {candidate_name}")
        await orchestrator._greet_candidate(candidate_name)
        print("   ✅ Greeting delivered")

        # ── Q&A loop ────────────────────────────────────────────────────────
        print(f"\n   💬 Starting {len(orchestrator.questions)}-question interview...")
        await orchestrator._qa_loop()
        print("   ✅ All questions done")

        # ── Closing ─────────────────────────────────────────────────────────
        print("\n   👏 Closing interview...")
        await orchestrator._close_interview(candidate_name)

        # ── Leave meeting ───────────────────────────────────────────────────
        print("\n   🚪 Leaving meeting...")
        await orchestrator._leave_meeting()

        # ── Finalize ────────────────────────────────────────────────────────
        results = await orchestrator._finalize_results()
        logger.info(f"Interview complete. Score: {results.get('overall_score')}")
        return results

    except Exception:
        logger.error("❌ Interview failed", exc_info=True)
        print(f"\n   ❌ Interview error — full details in: {log_file}")
        traceback.print_exc()
        return {"success": False, "error": traceback.format_exc()}


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

async def main():
    print("\n" + "🤖" * 35)
    print("   AI RECRUITER — GOOGLE MEET INTERVIEW BOT")
    print("🤖" * 35)
    print(f"\n📄 Full log → {log_file}\n")

    # Step 1
    meeting_info = await create_test_meeting()
    if not meeting_info:
        print("❌ Could not create meeting. Exiting.")
        return

    meet_link      = meeting_info["meet_link"]
    auth           = meeting_info["auth"]
    candidate_name = meeting_info["candidate_name"]
    job_title      = meeting_info["job_title"]
    interview_id   = f"interview_{int(datetime.now().timestamp())}"

    # Step 2
    print(f"\n{SEP}")
    print("📌 STEP 2: Waiting for Candidate to Join")
    print(SEP)
    print(f"\n   🔗 Meeting URL : {meet_link}")
    print(f"   ➡️  Open in YOUR browser → click 'Ask to join'")
    print(f"   🔓  Bot auto-admits — no manual approval needed")
    print(f"   🎤  Turn ON your microphone!")
    print(f"\n   ⏳  Auto-admit ACTIVE. Interview starts AUTOMATICALLY when you join.\n")

    page = auth.get_page()
    stop_admit = asyncio.Event()
    admit_task = asyncio.create_task(run_auto_admit_loop(page, stop_admit))

    try:
        await asyncio.wait_for(stop_admit.wait(), timeout=300)
    except asyncio.TimeoutError:
        logger.error("❌ TIMEOUT: No candidate joined within 5 minutes")
        print("\n❌ Timeout — no candidate joined in 5 minutes. Exiting.")
        admit_task.cancel()
        try:
            await admit_task
        except asyncio.CancelledError:
            pass
        await auth.close()
        return

    admit_task.cancel()
    try:
        await admit_task
    except asyncio.CancelledError:
        pass

    logger.info("Candidate joined. Waiting 4s before starting interview...")
    print("\n   ⏳ Settling for 4 seconds...")
    await asyncio.sleep(4)

    # Step 3
    results = await run_interview(
        auth=auth,
        interview_id=interview_id,
        meet_url=meet_link,
        candidate_name=candidate_name,
        job_title=job_title,
    )

    # Results
    print(f"\n{SEP}")
    print("📊 FINAL RESULTS")
    print(SEP)
    if results.get("success"):
        print(f"✅ Status      : SUCCESS")
        print(f"📌 Interview ID: {results.get('interview_id')}")
        print(f"⭐ Score       : {results.get('overall_score', 0):.1f} / 10")
        print(f"❓ Questions   : {results.get('total_questions', 0)}")
        print(f"✅ Answered    : {results.get('questions_answered', 0)}")
        print(f"🕐 Completed   : {results.get('completed_at')}")
        for i, qa in enumerate(results.get("qa_history", []), 1):
            print(f"\n  Q{i}: {qa.get('question', '')[:100]}")
            print(f"  A{i}: {qa.get('answer',   '')[:100]}")
            print(f"  Score: {qa.get('score', 0)}/10 | {qa.get('feedback', '')[:100]}")
    else:
        print(f"❌ Status: FAILED")
        print(f"Error: {str(results.get('error', 'Unknown'))[:500]}")

    print(f"\n{SEP}")
    print(f"✅ Done! Full log → {log_file}")
    print(SEP)


if __name__ == "__main__":
    asyncio.run(main())
