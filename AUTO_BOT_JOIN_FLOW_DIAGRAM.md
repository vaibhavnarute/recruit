# Auto-Bot Join Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AUTO-BOT JOIN COMPLETE WORKFLOW                           │
└─────────────────────────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════════════╗
║ PHASE 1: INTERVIEW SCHEDULING (HR ACTION)                                  ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌──────────────┐
│   HR Opens   │
│  Assign Page │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Frontend: AssignInterviews.tsx     │
│  ─────────────────────────────────  │
│  ✓ Select batch & template          │
│  ✓ Checkbox: "Enable Auto-Bot Join" │
│    [✓] CHECKED (default)            │
│  ✓ Click "Assign Interview"         │
└─────────────┬───────────────────────┘
              │
              │ POST /api/interviews/schedule
              │ { auto_start_bot: true, ... }
              ▼
┌────────────────────────────────────────────────────┐
│  Backend: interview_scheduling_agent.py            │
│  ────────────────────────────────────────────────  │
│  1. Validate input ✓                               │
│  2. Create Google Meet link ✓                      │
│  3. GENERATE TOKEN:                                │
│     auto_join_token = secrets.token_urlsafe(32)    │
│     → "xYz123AbC456DeF789..." (43 chars)           │
│  4. Save to MongoDB:                               │
│     {                                              │
│       meet_link: "https://meet.google.com/abc",    │
│       auto_start_bot: true,                        │
│       auto_join_token: "xYz123...",                │
│       bot_join_status: "pending"                   │
│     }                                              │
└─────────────┬──────────────────────────────────────┘
              │
              │ Pass token to email service
              ▼
┌────────────────────────────────────────────────────┐
│  Backend: email_service.py                         │
│  ────────────────────────────────────────────────  │
│  IF auto_start_bot AND token:                      │
│    button_link = /api/meet/trigger/{id}?token=...  │
│    button_text = "Start Interview"                 │
│    button_color = GREEN (#10b981)                  │
│    sub_text = "Bot will be ready"                  │
│  ELSE:                                             │
│    button_link = meet_link (direct)                │
│    button_text = "Join Interview"                  │
│    button_color = BLUE (#3b82f6)                   │
│  ───────────────────────────────────────────────   │
│  Send email via SMTP ✉️                            │
└─────────────┬──────────────────────────────────────┘
              │
              │ Email sent successfully
              ▼
        ┌─────────┐
        │ SUCCESS │
        └─────────┘

╔═══════════════════════════════════════════════════════════════════════════╗
║ PHASE 2: CANDIDATE RECEIVES EMAIL                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌────────────────────────────────────────────────────────────────────────┐
│  📧 CANDIDATE'S EMAIL INBOX                                             │
│  ─────────────────────────────────────────────────────────────────────  │
│  From: swarupkakade1810@gmail.com                                       │
│  Subject: Interview Invitation - Software Engineer                      │
│                                                                          │
│  Dear John,                                                             │
│                                                                          │
│  You have been scheduled for an interview:                              │
│  • Position: Software Engineer                                          │
│  • Time: February 1, 2025 at 2:00 PM                                    │
│                                                                          │
│  ┌────────────────────────────────────┐                                 │
│  │  🚀 START INTERVIEW (GREEN BUTTON)  │  ← Auto-Trigger URL            │
│  └────────────────────────────────────┘                                 │
│                                                                          │
│  The AI interviewer will be ready when you join                         │
│                                                                          │
│  Meeting Link: https://meet.google.com/abc-defg-hij                     │
└────────────────────────────────────────────────────────────────────────┘
             │
             │ Candidate clicks "Start Interview"
             ▼

╔═══════════════════════════════════════════════════════════════════════════╗
║ PHASE 3: TRIGGER BOT & COUNTDOWN (CANDIDATE CLICKS)                      ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌────────────────────────────────────────────────────┐
│  GET /api/meet/trigger/{interview_id}?token=xYz... │
└─────────────┬──────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────────────┐
│  Backend: main.py - trigger_bot() endpoint                    │
│  ──────────────────────────────────────────────────────────   │
│  VALIDATION CHECKS:                                           │
│  ✓ 1. Interview exists?                                       │
│  ✓ 2. Token matches database?                                 │
│       interview.auto_join_token == token                      │
│  ✓ 3. Not expired?                                            │
│       scheduled_time > now() - 24h                            │
│  ✓ 4. Not already triggered?                                  │
│       bot_join_status != "triggered"                          │
│  ────────────────────────────────────────────────────────     │
│  IF all checks pass:                                          │
│    1. Update database:                                        │
│       bot_join_status = "triggered"                           │
│       trigger_timestamp = now()                               │
│    2. START BOT ASYNC:                                        │
│       asyncio.create_task(start_bot(interview_id))            │
│    3. Return HTML countdown page                              │
│  ELSE:                                                        │
│    Return error (403/400/410)                                 │
└─────────────┬────────────────────────────────────────────────┘
              │
              │ Bot starting in background...
              │ Return HTML response
              ▼
┌─────────────────────────────────────────────────────────────┐
│  COUNTDOWN PAGE (Browser)                                    │
│  ───────────────────────────────────────────────────────────  │
│                                                              │
│         🎯 Preparing Your Interview                          │
│                                                              │
│      The AI interviewer is joining the meeting...            │
│                                                              │
│                     ⏱️ 10                                     │
│                  (countdown)                                 │
│                                                              │
│         ████████████░░░░░░░░  75%                            │
│              (progress bar)                                  │
│                                                              │
│  ───────────────────────────────────────────────────────────  │
│  JavaScript:                                                 │
│    setInterval(() => {                                       │
│      countdown--;                                            │
│      if (countdown === 0) {                                  │
│        window.location.href = meet_link;                     │
│      }                                                       │
│    }, 1000);                                                 │
└─────────────┬───────────────────────────────────────────────┘
              │
              │ 10 seconds elapse...
              │ (Bot joining in parallel)
              ▼

╔═══════════════════════════════════════════════════════════════════════════╗
║ PHASE 4: BOT JOINS GOOGLE MEET (BACKGROUND PROCESS)                      ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────┐
│  Backend: Async Bot Startup (Puppeteer)                  │
│  ────────────────────────────────────────────────────────  │
│  Timeline (parallel to countdown):                        │
│                                                           │
│  t=0s:  asyncio.create_task(start_bot())                  │
│  t=1s:  Launch headless Chrome                            │
│  t=2s:  Navigate to Google Meet URL                       │
│  t=3s:  Enter bot credentials                             │
│  t=5s:  Join meeting (click button)                       │
│  t=8s:  Bot visible in meeting ✓                          │
│                                                           │
│  Update database:                                         │
│    bot_join_status = "joined"                             │
│    bot_joined_at = now()                                  │
└─────────────┬────────────────────────────────────────────┘
              │
              │ Bot successfully joined at t=8s
              │ Countdown still running (10s total)
              ▼
        ┌──────────┐
        │ Bot Ready│
        └──────────┘

╔═══════════════════════════════════════════════════════════════════════════╗
║ PHASE 5: CANDIDATE REDIRECTS TO MEETING                                  ║
╚═══════════════════════════════════════════════════════════════════════════╝

              t=10s: Countdown reaches 0
              │
              ▼
┌─────────────────────────────────────────────┐
│  window.location.href = meet_link;          │
│  → https://meet.google.com/abc-defg-hij     │
└─────────────┬───────────────────────────────┘
              │
              │ Browser redirects
              ▼
┌─────────────────────────────────────────────────────────────┐
│  Google Meet Interface                                       │
│  ───────────────────────────────────────────────────────────  │
│                                                              │
│  👤 AI Recruiter Bot (already in meeting)                    │
│  ✓ Camera: On                                                │
│  ✓ Microphone: On                                            │
│  ✓ Waiting for candidate...                                  │
│                                                              │
│  ───────────────────────────────────────────────────────────  │
│                                                              │
│  [John Doe wants to join]                                    │
│  ┌──────────────┐                                            │
│  │ ADMIT        │  ← Bot auto-admits                         │
│  └──────────────┘                                            │
└─────────────┬───────────────────────────────────────────────┘
              │
              │ Candidate admitted
              ▼
┌─────────────────────────────────────────────────────────────┐
│  Active Interview                                            │
│  ───────────────────────────────────────────────────────────  │
│  👤 AI Recruiter Bot                                          │
│  👤 John Doe                                                  │
│                                                              │
│  Bot: "Hello John, welcome to your interview..."             │
│                                                              │
│  Update database:                                            │
│    candidate_joined_at = now()                               │
└─────────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════════════╗
║ TIMING DIAGRAM                                                            ║
╚═══════════════════════════════════════════════════════════════════════════╝

 t=0s                t=5s               t=8s                t=10s
  │                   │                  │                   │
  │ Candidate clicks  │                  │                   │
  │ "Start Interview" │                  │                   │
  │                   │                  │                   │
  ├─► Bot starts      │                  │                   │
  │   (async)         │                  │                   │
  │                   │                  │                   │
  ├─► Countdown       │                  │                   │
  │   page shown      │                  │                   │
  │                   │                  │                   │
  │   10 → 9 → 8 →... │ 5 → 4 → 3 →...   │ 2 → 1 → 0         │
  │                   │                  │                   │
  │   Bot launching   ├─► Bot joining    ├─► Bot in meeting  ├─► Redirect
  │                   │    Meet          │    ✓              │    candidate
  │                   │                  │                   │
  └───────────────────┴──────────────────┴───────────────────┴─────────►

  Result: Bot is ready BEFORE candidate joins (no race condition!)

╔═══════════════════════════════════════════════════════════════════════════╗
║ ERROR HANDLING & EDGE CASES                                               ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│ SCENARIO 1: Duplicate Click                                             │
│ ───────────────────────────────────────────────────────────────────────  │
│ Candidate clicks button twice:                                          │
│                                                                          │
│ First click:  bot_join_status = "pending" → "triggered" ✓               │
│               Bot starts, countdown shows                                │
│                                                                          │
│ Second click: bot_join_status = "triggered" already!                    │
│               → Return error HTML:                                       │
│               "Bot Already Started"                                      │
│               "The AI interviewer has already joined this meeting"       │
│               [Go to Meeting] button (no bot restart)                    │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ SCENARIO 2: Expired Token                                               │
│ ───────────────────────────────────────────────────────────────────────  │
│ Candidate clicks 25 hours after scheduled_time:                         │
│                                                                          │
│ Check: scheduled_time + 24h < now()                                      │
│        → Token expired ✗                                                 │
│                                                                          │
│ Return 410 Gone:                                                         │
│   "Link Expired"                                                         │
│   "This interview link has expired (>24 hours)"                          │
│   "Please contact support"                                               │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ SCENARIO 3: Invalid Token                                               │
│ ───────────────────────────────────────────────────────────────────────  │
│ Attacker modifies URL token parameter:                                  │
│   ?token=WRONG_TOKEN                                                     │
│                                                                          │
│ Check: interview.auto_join_token != token                                │
│        → Unauthorized ✗                                                  │
│                                                                          │
│ Return 403 Forbidden:                                                    │
│   "Invalid or expired token"                                             │
│   "Please use the link from your email"                                  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ SCENARIO 4: Bot Startup Failure                                         │
│ ───────────────────────────────────────────────────────────────────────  │
│ Puppeteer fails (network error, credentials invalid):                   │
│                                                                          │
│ Update database:                                                         │
│   bot_join_status = "failed"                                             │
│                                                                          │
│ Fallback options:                                                        │
│   1. Countdown still completes → candidate joins meeting                 │
│   2. HR notified via email/dashboard                                     │
│   3. HR can manually start bot from "Meeting Bot" page                   │
│   4. Interview proceeds (manual control)                                 │
└─────────────────────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════════════╗
║ DATABASE STATE TRANSITIONS                                                ║
╚═══════════════════════════════════════════════════════════════════════════╝

Initial (after scheduling):
┌─────────────────────────────────────────┐
│ auto_start_bot: true                    │
│ auto_join_token: "xYz123..."            │
│ bot_join_status: "pending"       ◄─┐    │
│ trigger_timestamp: null             │    │
│ bot_joined_at: null                 │    │
│ candidate_joined_at: null           │    │
└─────────────────────────────────────┘    │
                 │                         │
                 │ Candidate clicks        │
                 ▼                         │
After trigger:                             │
┌─────────────────────────────────────────┐│
│ bot_join_status: "triggered"     ◄─┐    ││
│ trigger_timestamp: 2025-02-01T14:00 │    ││
│ (other fields unchanged)           │    ││
└─────────────────────────────────────┘│   ││
                 │                     │   ││
                 │ Bot joins meeting   │   ││
                 ▼                     │   ││
After bot joins:                       │   ││
┌─────────────────────────────────────┐│  ││
│ bot_join_status: "joined"           ││  ││
│ bot_joined_at: 2025-02-01T14:00:08  ││  ││
└─────────────────────────────────────┘│  ││
                 │                     │  ││
                 │ Candidate joins     │  ││
                 ▼                     │  ││
After candidate joins:                 │  ││
┌─────────────────────────────────────┐│ ││
│ candidate_joined_at: 2025-02-01T14:00:10│││
└─────────────────────────────────────┘│││││
                                       │││││
If duplicate click: ───────────────────┘││││
If bot fails: ──────────────────────────┘│││
   bot_join_status: "failed"             ││
                                         ││
If manual mode (auto_start_bot=false): ──┘│
   bot_join_status: "not_applicable"      │
                                          │
Retry after duplicate click blocked ──────┘

╔═══════════════════════════════════════════════════════════════════════════╗
║ SECURITY LAYERS                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

Layer 1: Token Generation
┌────────────────────────────────────────┐
│ secrets.token_urlsafe(32)              │
│ → 256-bit entropy                      │
│ → Cryptographically secure             │
│ → 43 characters: "xYz123AbC..."        │
└────────────────────────────────────────┘

Layer 2: Token Validation
┌────────────────────────────────────────┐
│ interview_id + token BOTH required     │
│ Database lookup must match exactly     │
│ Case-sensitive comparison              │
└────────────────────────────────────────┘

Layer 3: One-Time Use
┌────────────────────────────────────────┐
│ bot_join_status state machine          │
│ "pending" → "triggered" (permanent)    │
│ Second click → error (no replay)       │
└────────────────────────────────────────┘

Layer 4: Expiration
┌────────────────────────────────────────┐
│ scheduled_time + 24 hours              │
│ After deadline → 410 Gone              │
│ Prevents long-term token reuse         │
└────────────────────────────────────────┘

Layer 5: Rate Limiting (TODO)
┌────────────────────────────────────────┐
│ 10 requests per minute per IP          │
│ Prevents brute force attacks           │
│ Monitor for suspicious patterns        │
└────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════════════╗
║ COMPARISON: BEFORE vs AFTER                                               ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────┬──────────────────────────────────────┐
│ BEFORE (Manual Bot Control)         │ AFTER (Auto-Bot Join)                │
├─────────────────────────────────────┼──────────────────────────────────────┤
│ 1. HR schedules interview            │ 1. HR schedules interview            │
│ 2. Email sent with Meet link         │ 2. Email sent with trigger link      │
│ 3. HR goes to "Meeting Bot" page     │ 3. [SKIPPED - Automatic]             │
│ 4. HR clicks "Start Bot" manually    │ 4. [SKIPPED - Automatic]             │
│ 5. HR monitors bot status            │ 5. [SKIPPED - Automatic]             │
│ 6. Candidate joins meeting           │ 6. Candidate clicks "Start Interview"│
│ 7. Bot may join late (race)          │ 7. Bot joins first (10s buffer)      │
│ 8. Interview starts                  │ 8. Candidate redirects after 10s     │
│                                      │ 9. Interview starts (seamless)       │
├─────────────────────────────────────┼──────────────────────────────────────┤
│ Pain Points:                         │ Benefits:                            │
│ • HR must remember to start bot      │ • Zero manual intervention           │
│ • Timing issues (too early/late)     │ • Perfect timing (on-demand)         │
│ • Manual process prone to errors     │ • Automated, reliable                │
│ • Bot may not be present when        │ • Bot always ready before candidate  │
│   candidate joins                    │                                      │
├─────────────────────────────────────┼──────────────────────────────────────┤
│ Use Case:                            │ Use Case:                            │
│ • Special interviews                 │ • Regular interviews (90%+ cases)    │
│ • Troubleshooting                    │ • Default behavior                   │
│ • Manual control needed              │ • Seamless candidate experience      │
└─────────────────────────────────────┴──────────────────────────────────────┘

Both modes coexist! HR can still use manual control as override.

═══════════════════════════════════════════════════════════════════════════

END OF FLOW DIAGRAM
Version: 1.0
Last Updated: 2025-02-01
```
