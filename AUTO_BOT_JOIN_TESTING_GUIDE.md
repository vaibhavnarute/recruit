# Auto-Bot Join Testing Guide

## 🎯 Feature Overview
The Auto-Bot Join feature automatically triggers the AI meeting bot when a candidate clicks "Start Interview" in their email invitation. This eliminates the need for manual bot activation and creates a seamless interview experience.

## ✅ Implementation Complete

### Backend Changes
1. **New Database Fields** (in `interviews` collection):
   - `auto_start_bot`: boolean (default: true)
   - `auto_join_token`: string (32-byte URL-safe token)
   - `bot_join_status`: enum ('pending', 'triggered', 'joined', 'failed', 'not_applicable')
   - `candidate_joined_at`: timestamp
   - `bot_joined_at`: timestamp
   - `trigger_timestamp`: timestamp

2. **New API Endpoint**: `GET /api/meet/trigger/{interview_id}`
   - Validates security token from query parameters
   - Prevents duplicate clicks (checks bot_join_status)
   - Starts bot asynchronously
   - Returns HTML page with 10-second countdown
   - Redirects to Google Meet after delay

3. **Email Service Enhanced**:
   - Dynamic button generation (trigger URL vs direct Meet link)
   - New parameters: `auto_start_bot`, `auto_join_token`, `backend_url`
   - Backward compatible (works with existing interviews)

4. **Interview Scheduling Agent**:
   - Generates secure tokens using `secrets.token_urlsafe(32)`
   - Stores token in MongoDB
   - Passes token to email service

5. **Environment Configuration**:
   - Added `BACKEND_URL` to `.env` (default: http://localhost:8001)

### Frontend Changes
1. **AssignInterviews Component**:
   - Added "Enable Auto-Bot Join" checkbox (default: checked)
   - User can opt-out for specific interviews
   - State: `autoBotJoin` (boolean)

## 🧪 Testing Checklist

### Prerequisites
- [ ] Backend running on port 8001
- [ ] Frontend running on port 8080
- [ ] MongoDB connection active
- [ ] SMTP credentials configured in `.env`
- [ ] Google Meet bot credentials configured
- [ ] Node.js server running (for Puppeteer)

### Test Scenarios

#### **Scenario 1: Happy Path - Auto-Join Enabled**
1. **Schedule Interview**:
   - Go to "Assign Interviews" page
   - Select batch and template
   - Ensure "Enable Auto-Bot Join" is **checked**
   - Click "Assign Interview to Batch"

2. **Verify Database**:
   ```bash
   # Check interview record in MongoDB
   db.interviews.findOne({}, { auto_start_bot: 1, auto_join_token: 1, bot_join_status: 1 })
   ```
   - ✅ `auto_start_bot` should be `true`
   - ✅ `auto_join_token` should exist (32-char string)
   - ✅ `bot_join_status` should be `'pending'`

3. **Check Email**:
   - Open candidate's email inbox
   - Verify email contains:
     - Green "Start Interview" button
     - Text: "Click below to join your scheduled interview"
     - Small text: "The AI interviewer will be ready when you join"
   - Button URL should be: `http://localhost:8001/api/meet/trigger/{interview_id}?token={auto_join_token}`

4. **Click Trigger Button**:
   - Click "Start Interview" in email
   - Should see countdown page:
     - "Preparing Your Interview"
     - "The AI interviewer is joining the meeting..."
     - 10-second countdown timer
     - Progress bar animation
   - After 10 seconds, automatically redirects to Google Meet

5. **Verify Bot Started**:
   - Check backend logs for bot startup
   - Check database:
     ```bash
     db.interviews.findOne({}, { bot_join_status: 1, bot_joined_at: 1, trigger_timestamp: 1 })
     ```
   - ✅ `bot_join_status` should be `'triggered'` → `'joined'`
   - ✅ `trigger_timestamp` should exist
   - ✅ `bot_joined_at` should exist

6. **Verify Interview**:
   - Bot should be visible in Google Meet
   - Candidate joins after redirect
   - Interview proceeds normally

#### **Scenario 2: Auto-Join Disabled (Manual Mode)**
1. **Schedule Interview**:
   - Go to "Assign Interviews" page
   - **Uncheck** "Enable Auto-Bot Join"
   - Click "Assign Interview"

2. **Check Database**:
   ```bash
   db.interviews.findOne({}, { auto_start_bot: 1, bot_join_status: 1 })
   ```
   - ✅ `auto_start_bot` should be `false`
   - ✅ `bot_join_status` should be `'not_applicable'`
   - ✅ `auto_join_token` should NOT exist

3. **Check Email**:
   - Email should contain:
     - Blue "Join Interview" button
     - Direct link to Google Meet (no trigger)
     - Text: "Click below to join your scheduled interview"

4. **Manual Bot Control**:
   - HR must go to "Meeting Bot" page
   - Click "Start Bot" manually
   - Bot joins meeting

#### **Scenario 3: Duplicate Click Prevention**
1. **First Click**:
   - Click "Start Interview" in email
   - Countdown page loads
   - Bot starts

2. **Second Click** (before countdown finishes):
   - Open email again
   - Click "Start Interview" again
   - Should see error message:
     - "Bot Already Started"
     - "The AI interviewer has already joined this meeting"
     - Link to Google Meet (no bot restart)

3. **Verify Database**:
   - Only ONE `trigger_timestamp` exists
   - Bot not started twice

#### **Scenario 4: Token Expiration**
1. **Schedule Interview**:
   - Create interview with auto-join enabled
   - Get `auto_join_token` from database

2. **Wait 25 Hours** (or manually change `scheduled_time` in DB to past):
   ```bash
   db.interviews.updateOne(
     { _id: ObjectId("...") },
     { $set: { scheduled_time: new Date(Date.now() - 25 * 60 * 60 * 1000) } }
   )
   ```

3. **Click Button**:
   - Click "Start Interview"
   - Should see error:
     - "Link Expired"
     - "This interview link has expired"
     - Contact support message

#### **Scenario 5: Invalid Token**
1. **Modify URL**:
   - Get trigger URL from email
   - Change token parameter: `?token=INVALID_TOKEN`
   - Click modified link

2. **Verify Error**:
   - Should see 403 error or "Invalid Token" message
   - Bot does NOT start

#### **Scenario 6: Race Condition (10-Second Delay)**
1. **Candidate Clicks Button**:
   - Countdown starts
   - Bot begins joining (takes ~5-8 seconds)

2. **Verify Timing**:
   - Candidate waits 10 seconds (countdown)
   - Bot finishes joining during this time
   - Candidate redirects to meeting
   - Bot already present in meeting

3. **Check Logs**:
   - Bot join timestamp < redirect timestamp
   - No "bot not present" errors

#### **Scenario 7: Backward Compatibility**
1. **Check Existing Interviews**:
   ```bash
   # Old interviews without auto_start_bot field
   db.interviews.find({ auto_start_bot: { $exists: false } }).count()
   ```

2. **Email Behavior**:
   - Old interviews should send direct Meet links (no trigger)
   - Email template handles missing `auto_start_bot` field

3. **API Behavior**:
   - `/api/meet/trigger` returns error for interviews without token
   - Manual bot control still works

## 🐛 Common Issues & Troubleshooting

### Issue 1: Email Not Received
**Symptoms**: Candidate doesn't receive email after scheduling

**Checks**:
```bash
# Verify SMTP credentials in .env
cat backend/.env | grep SMTP

# Check backend logs for email errors
# Look for "Email sent successfully" or error messages
```

**Solutions**:
- Verify SMTP credentials
- Check spam folder
- Enable "Less secure app access" for Gmail
- Use app-specific password if 2FA enabled

### Issue 2: Bot Doesn't Start
**Symptoms**: Countdown finishes, but bot not in meeting

**Checks**:
```bash
# Check bot join status
db.interviews.findOne({}, { bot_join_status: 1, bot_joined_at: 1 })

# Check backend logs for Puppeteer errors
# Look for "Bot started successfully" or errors
```

**Solutions**:
- Verify Node.js server running
- Check Google Meet credentials in `.env`
- Ensure Puppeteer installed: `npm install puppeteer`
- Check firewall/network restrictions

### Issue 3: Countdown Page Shows Wrong Time
**Symptoms**: Countdown stuck at 10 seconds or goes negative

**Cause**: JavaScript disabled or browser compatibility

**Solution**:
- Test in modern browser (Chrome, Firefox, Edge)
- Check browser console for JS errors
- Fallback: Page auto-redirects after 12 seconds (no JS required)

### Issue 4: Token Not Generated
**Symptoms**: Email sent without trigger link

**Checks**:
```bash
# Check interview record
db.interviews.findOne({}, { auto_join_token: 1, auto_start_bot: 1 })

# Check backend logs for token generation
```

**Solutions**:
- Ensure `secrets` module imported in interview_scheduling_agent.py
- Check `auto_start_bot` parameter passed to scheduling API
- Verify database write permissions

### Issue 5: Redirect Doesn't Work
**Symptoms**: Countdown finishes, but no redirect to Meet

**Checks**:
- Open browser console
- Check for error: "Redirect blocked by browser"
- Verify Meet URL in interview record

**Solutions**:
- Allow pop-ups for localhost:8001
- Check Meet link format: `https://meet.google.com/abc-defg-hij`
- Clear browser cache

## 📊 Monitoring & Metrics

### Database Queries

**Check Auto-Join Success Rate**:
```javascript
// MongoDB
db.interviews.aggregate([
  { $match: { auto_start_bot: true } },
  { $group: {
    _id: "$bot_join_status",
    count: { $sum: 1 }
  }}
])
```

**Average Bot Join Time**:
```javascript
db.interviews.aggregate([
  { $match: { bot_joined_at: { $exists: true } } },
  { $project: {
    joinDelay: { $subtract: ["$bot_joined_at", "$trigger_timestamp"] }
  }},
  { $group: {
    _id: null,
    avgDelay: { $avg: "$joinDelay" }
  }}
])
```

**Failed Auto-Joins**:
```javascript
db.interviews.find({ 
  auto_start_bot: true,
  bot_join_status: "failed"
})
```

### Backend Logs
```bash
# Watch logs in real-time
tail -f backend/logs/app.log | grep -i "trigger"

# Count successful triggers
grep "Bot triggered successfully" backend/logs/app.log | wc -l

# Find errors
grep -i "error" backend/logs/app.log | grep -i "trigger"
```

## 🚀 Production Deployment

### Environment Variables
1. **Update `.env`**:
   ```bash
   BACKEND_URL=https://your-production-domain.com
   ```

2. **SMTP Settings**:
   - Use production email service (SendGrid, AWS SES)
   - Update SMTP credentials

3. **Security**:
   - Generate new `JWT_SECRET_KEY`
   - Use HTTPS for all URLs
   - Enable rate limiting on trigger endpoint

### Database Indexes
```javascript
// Add index for fast token lookups
db.interviews.createIndex({ auto_join_token: 1 })

// Index for status queries
db.interviews.createIndex({ bot_join_status: 1, scheduled_time: -1 })

// TTL index to auto-delete old tokens (optional)
db.interviews.createIndex(
  { scheduled_time: 1 },
  { expireAfterSeconds: 604800 } // 7 days
)
```

### Performance Optimization
1. **Bot Startup**:
   - Pre-warm Puppeteer instance
   - Use connection pooling
   - Implement retry logic

2. **Email Delivery**:
   - Queue emails (Celery, RabbitMQ)
   - Batch processing for multiple candidates
   - Send time optimization

3. **Token Storage**:
   - Consider Redis for token caching
   - Implement token cleanup job

## 📝 API Documentation

### Endpoint: Create Interview (Updated)
**POST** `/api/interviews/schedule`

**Request Body**:
```json
{
  "candidate_email": "candidate@example.com",
  "candidate_name": "John Doe",
  "job_title": "Software Engineer",
  "scheduled_time": "2025-02-01T14:00:00Z",
  "auto_start_bot": true,  // NEW: Enable auto-join
  "interview_type": "technical"
}
```

**Response**:
```json
{
  "interview_id": "507f1f77bcf86cd799439011",
  "meet_link": "https://meet.google.com/abc-defg-hij",
  "auto_join_token": "xYz123...",  // NEW
  "status": "scheduled"
}
```

### Endpoint: Trigger Bot (NEW)
**GET** `/api/meet/trigger/{interview_id}?token={auto_join_token}`

**Success Response** (HTML):
- 200 OK
- HTML countdown page
- Auto-redirects to Meet after 10 seconds

**Error Responses**:
- 403 Forbidden: Invalid token
- 400 Bad Request: Bot already started
- 410 Gone: Link expired
- 404 Not Found: Interview not found

## 🔒 Security Considerations

1. **Token Generation**:
   - Uses `secrets.token_urlsafe(32)` (256-bit entropy)
   - Cryptographically secure random tokens
   - One-time use enforced by status tracking

2. **Token Validation**:
   - Must match database record
   - Interview ID + token both required
   - Case-sensitive comparison

3. **Expiration**:
   - Tokens expire 24 hours after scheduled time
   - Prevents replay attacks
   - Database query checks scheduled_time

4. **Rate Limiting** (TODO for production):
   - Limit trigger requests per IP
   - Implement CAPTCHA for suspicious activity
   - Monitor for token enumeration attempts

5. **Logging**:
   - All trigger attempts logged
   - Include IP, timestamp, success/failure
   - Alert on unusual patterns

## 📈 Success Metrics

**KPIs to Track**:
- Auto-join success rate (target: >95%)
- Average bot join time (target: <8 seconds)
- Token expiration rate (should be low)
- Duplicate click attempts (monitor for UX issues)
- Failed joins (root cause analysis)

**User Experience**:
- Candidate satisfaction with seamless joining
- Reduction in "bot not present" support tickets
- Time saved for HR (no manual bot activation)

## 🎓 User Training

### For HR/Recruiters
1. **Default Behavior**: Auto-join is enabled by default
2. **When to Disable**: 
   - Special interviews requiring manual control
   - Testing purposes
   - Troubleshooting bot issues
3. **Manual Override**: Can still start bot manually from "Meeting Bot" page

### For Candidates
1. **Email Instructions**: Clear CTA "Start Interview"
2. **Countdown Explanation**: Wait 10 seconds for bot to join
3. **Troubleshooting**: Contact support if stuck on countdown

## ✨ Future Enhancements

1. **WebSocket Updates**: Real-time bot status in admin dashboard
2. **Retry Logic**: Auto-retry if bot fails to join
3. **Multi-Bot Support**: Handle high concurrency
4. **Analytics Dashboard**: Visualize success metrics
5. **Email Templates**: Multiple languages, customization
6. **SMS Notifications**: Backup reminder 5 minutes before interview
7. **Calendar Integration**: iCal/Outlook invites with trigger link

---

## 🚦 Quick Start Testing

```bash
# 1. Start backend
cd backend
source venv311/Scripts/activate  # Windows
python main.py

# 2. Start frontend
cd talentstream-hr
npm run dev

# 3. Open browser
# - Frontend: http://localhost:8080
# - Backend: http://localhost:8001

# 4. Schedule test interview
# - Go to "Assign Interviews"
# - Keep "Enable Auto-Bot Join" checked
# - Submit

# 5. Check email & click "Start Interview"
# - Watch countdown
# - Verify redirect to Meet
# - Bot should be in meeting

# 6. Verify in database
mongosh "mongo_url" -u <user> -p <pass>
use resumate
db.interviews.find().sort({_id:-1}).limit(1).pretty()
```

---

**Version**: 1.0  
**Last Updated**: 2025-02-01  
**Status**: Implementation Complete ✅  
**Next Steps**: End-to-End Testing 🧪
