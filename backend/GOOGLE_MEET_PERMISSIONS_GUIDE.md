# Google Meet Permissions & Security Configuration Guide

## 🔐 How Our Implementation Creates Legitimate Google Meet Rooms

### ✅ Current Implementation Status

Our system creates **100% LEGITIMATE** Google Meet rooms using the **Official Google Calendar API**.

**Method:** `create_interview_meeting()` in `services/google_calendar_service.py`

**How it works:**
```python
'conferenceData': {
    'createRequest': {
        'requestId': interview_id,
        'conferenceSolutionKey': {'type': 'hangoutsMeet'}  # ← Official API call
    }
}
```

**Result:**
- ✅ Real Google Meet room created on Google's infrastructure
- ✅ Official Meet URL: `https://meet.google.com/xxx-xxxx-xxx`
- ✅ Associated with Google Calendar event
- ✅ Compliant with Google's security policies
- ✅ Meet room persists as long as Calendar event exists

---

## 🎥 Camera & Microphone Permission Controls

### Important Note About Google Meet Permissions

**Google Meet's camera and microphone permissions are controlled at multiple levels:**

1. **Browser Level** (User's browser prompts for permission)
2. **Google Workspace Admin Level** (Organization-wide policies)
3. **Meet Room Host Level** (Host can mute participants)
4. **Individual User Level** (Users can control their own camera/mic)

### What We Can Control via API

| Feature | Can Control via API? | How to Control |
|---------|---------------------|----------------|
| **Create legitimate Meet room** | ✅ YES | `conferenceData.conferenceSolutionKey.type = 'hangoutsMeet'` |
| **Restrict who can join** | ✅ YES (partial) | `attendees` list + event visibility |
| **Prevent guests from inviting others** | ✅ YES | `guestsCanInviteOthers = False` |
| **Prevent guests from modifying event** | ✅ YES | `guestsCanModify = False` |
| **Force camera off for specific users** | ❌ NO | Must use Google Workspace Admin Console |
| **Force microphone off for specific users** | ❌ NO | Must use Google Workspace Admin Console |
| **Restrict recording** | ❌ NO | Must use Google Workspace Admin Console |
| **Control screen sharing** | ❌ NO | Must use Google Workspace Admin Console |

### What Our Current Implementation Does

```python
# ✅ Event-level security (configured via API)
'guestsCanModify': False,          # Only organizer can modify
'guestsCanInviteOthers': False,    # Can't invite additional people
'guestsCanSeeOtherGuests': True,   # Can see other attendees

# ✅ Attendee restrictions
'attendees': [
    {'email': candidate_email},    # Invited candidate
    {'email': hr_email}            # Invited HR
]
# Only these users can join directly; others must request access
```

---

## 🛡️ Google Meet Security Hierarchy

### 1. **Default Google Meet Behavior** (What happens automatically)

When someone joins a Meet created via our API:

**✅ Automatic Security Features:**
- Only invited attendees can join directly
- Non-invited users must "Ask to join" and wait for host approval
- First person to join becomes the host
- Host can mute all participants
- Host can remove participants
- Host can lock the meeting (no more joins)

**⚠️ Important Notes:**
- Camera/mic are ON by default when users join (browser permission required)
- Users control their own camera/mic (can turn on/off)
- Host can force mute participants but cannot force camera off via API

### 2. **Organization-Level Controls** (Google Workspace Admin Console)

For stricter controls, configure via **Google Workspace Admin Console** → **Apps** → **Google Meet**:

**Available Policies:**
- ✅ Disable camera for external users
- ✅ Disable microphone for external users  
- ✅ Require host to admit guests
- ✅ Restrict recording to domain users only
- ✅ Disable screen sharing for external participants
- ✅ Enable waiting room for all meetings
- ✅ Auto-mute participants on join

**Access Admin Console:**
1. Go to: https://admin.google.com
2. Navigate to: Apps → Google Workspace → Google Meet
3. Configure: Meeting settings → Security

---

## 🎯 Recommended Configuration for Interview System

### For Maximum Security & Control:

#### **Step 1: API-Level Settings** (Already Implemented ✅)

```python
# In google_calendar_service.py (already done)
'conferenceData': {
    'createRequest': {
        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
    }
},
'guestsCanModify': False,
'guestsCanInviteOthers': False,
```

#### **Step 2: Google Workspace Admin Settings** (Manual Configuration Required)

**Recommended Admin Console Settings:**

1. **Security Settings:**
   ```
   ✅ Quick access: OFF (requires host to admit)
   ✅ Host management: Only organizer and co-hosts can admit
   ✅ Auto-admit: Only users in your organization
   ```

2. **Recording Settings:**
   ```
   ✅ Recording: Only host can record
   ✅ Recording notification: Always show
   ✅ Recording consent: Required
   ```

3. **Screen Sharing:**
   ```
   ✅ Screen sharing: Host and co-hosts only
   ✅ External participants: View only
   ```

4. **Camera/Microphone:**
   ```
   ⚠️ Note: Cannot force camera/mic off via API
   ✅ Solution: Use bot to monitor and alert if unauthorized devices detected
   ```

#### **Step 3: Runtime Controls** (Can Implement via Bot)

For the Puppeteer bot implementation:

```javascript
// Bot can programmatically:
✅ Monitor who joins the meeting
✅ Check camera/mic status of participants
✅ Alert if unauthorized devices are enabled
✅ Request host to mute specific participants
✅ End meeting if security violation detected
```

---

## 🤖 Bot Implementation for Advanced Controls

### Option 1: Monitoring Bot (Read-Only)

```javascript
// Bot joins as participant and monitors
const bot = new MeetMonitorBot({
  meetLink: 'https://meet.google.com/xxx-xxxx-xxx',
  capabilities: {
    monitorAudio: true,      // Transcribe speech
    monitorVideo: false,     // Don't process video
    monitorParticipants: true, // Track who joins/leaves
    alertOnUnauthorized: true  // Alert if unknown user joins
  }
});
```

### Option 2: Control Bot (Host Powers)

```javascript
// Bot joins as HOST and has control
const bot = new MeetControlBot({
  meetLink: 'https://meet.google.com/xxx-xxxx-xxx',
  hostEmail: 'bot@company.com',  // Bot is organizer
  controls: {
    autoMuteOnJoin: true,        // Mute participants when they join
    requireHandRaise: true,       // Unmute only when hand raised
    disableVideoForGuests: false, // Cannot enforce via API
    endMeetingOn: 'last_leave'   // End when everyone leaves
  }
});
```

---

## 📋 Implementation Checklist

### Current Status: ✅ API-Level Security Implemented

- [x] Creates legitimate Google Meet rooms via official API
- [x] Restricts event modification (`guestsCanModify: false`)
- [x] Prevents guests from inviting others (`guestsCanInviteOthers: false`)
- [x] Only invited attendees can join directly
- [x] Comprehensive logging and validation

### To Enhance Security Further:

- [ ] **Configure Google Workspace Admin Console** (Manual)
  - [ ] Enable "Quick access: OFF" (requires host admission)
  - [ ] Set "Auto-admit: Organization users only"
  - [ ] Configure recording restrictions
  - [ ] Set screen sharing to "Host only"

- [ ] **Implement Monitoring Bot** (Future Enhancement)
  - [ ] Monitor participant audio/video status
  - [ ] Alert on unauthorized camera/mic usage
  - [ ] Transcribe and analyze conversation
  - [ ] Store meeting analytics

- [ ] **Add Host Controls** (Future Enhancement)
  - [ ] Bot joins as organizer with host powers
  - [ ] Programmatic mute/unmute capabilities
  - [ ] Participant admission control
  - [ ] Meeting lock/unlock

---

## 🔍 How to Verify Meet Link Legitimacy

### Test Any Generated Meet Link:

1. **Copy Meet link from API response:**
   ```
   https://meet.google.com/wjk-wang-kqd
   ```

2. **Verify format:**
   ```python
   assert meet_link.startswith('https://meet.google.com/')
   room_code = meet_link.split('/')[-1]  # "wjk-wang-kqd"
   assert len(room_code) >= 8  # Typical Google Meet room code length
   ```

3. **Test accessibility:**
   - Open link in browser (incognito mode)
   - Should see Google Meet interface
   - Should prompt for Google account (if not invited)
   - Should show "Ask to join" button (if not in attendees list)

4. **Verify in Google Calendar:**
   - Check Calendar event exists
   - Verify Meet link appears in event details
   - Confirm attendees are listed

### Validation Script:

Run `python test_meet_link.py` to create and verify a test Meet link.

---

## 📞 Support & Troubleshooting

### Common Issues:

**Issue:** "No Meet link generated"
- **Cause:** `conferenceDataVersion=1` not set
- **Solution:** Already fixed in our implementation ✅

**Issue:** "Unauthorized users joining"
- **Cause:** Google Workspace set to "Quick access: ON"
- **Solution:** Configure Admin Console to require host admission

**Issue:** "Cannot force camera off"
- **Cause:** Not supported via Calendar API
- **Solution:** Use Workspace admin policies or bot monitoring

**Issue:** "Meet link expired"
- **Cause:** Calendar event was deleted
- **Solution:** Meet link persists as long as Calendar event exists

---

## 🎯 Summary

### What We've Implemented:

✅ **100% Legitimate Google Meet rooms** via official Calendar API
✅ **Event-level security** (guest restrictions)
✅ **Attendee controls** (only invited users)
✅ **Comprehensive validation** (URL format, room code, conference ID)
✅ **Detailed logging** for audit trail

### What Requires Additional Configuration:

⚠️ **Camera/Mic restrictions** → Google Workspace Admin Console
⚠️ **Advanced host controls** → Bot implementation
⚠️ **Organization policies** → Admin Console settings

### Next Steps:

1. **Test current implementation**: Run `python test_interview_scheduling.py`
2. **Configure Workspace policies**: Set up Admin Console (if using Google Workspace)
3. **Plan bot implementation**: Design Puppeteer bot for monitoring
4. **Document usage**: Share Meet link security info with HR team

---

**Last Updated:** October 22, 2025
**Implementation Status:** ✅ Production Ready
**Security Level:** High (with recommended Admin Console configuration)
