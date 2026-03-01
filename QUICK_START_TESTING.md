# Quick Start Guide - Testing New Frontend Features

## 🚀 Quick Start (5 Minutes)

### Step 1: Start Backend (Terminal 1)
```powershell
cd c:\Users\Vaibhav\OneDrive\Desktop\Ai_recruiter\final_ai_rectruter\backend
python main.py
```
✅ Backend should start on `http://localhost:8001`

### Step 2: Start Frontend (Terminal 2)
```powershell
cd c:\Users\Vaibhav\OneDrive\Desktop\Ai_recruiter\final_ai_rectruter\talentstream-hr
npm run dev
```
✅ Frontend should start on `http://localhost:5173`

### Step 3: Test Dashboard
1. Open browser: `http://localhost:5173`
2. Navigate to Dashboard
3. Look for "Live" indicator (top-right) - should turn green when WebSocket connects
4. Watch metrics update in real-time (every 5 seconds)
5. Scroll down to see Latency Chart and Performance Radar Chart

**Expected Behavior**:
- Cards show: Total Sessions, Active Interviews, Completed Today, Avg Quality Score
- Green "Live" indicator with WiFi icon
- Charts update automatically
- No errors in browser console

---

## 🧪 Testing Each Feature

### Test 1: Real-time Dashboard WebSocket ⚡
**What it does**: Displays live interview metrics from backend

**How to test**:
1. Open Dashboard page
2. Check connection indicator (top-right):
   - 🟢 Green "Live" = Connected
   - 🔴 Grey "Offline" = Disconnected
3. Open browser DevTools (F12) → Network → WS tab
4. You should see WebSocket connection to `ws://localhost:8001/api/dashboard/ws`
5. Watch metrics update every 5 seconds

**Backend verification**:
```powershell
# Backend terminal should show:
INFO:     WebSocket connection accepted
INFO:     Dashboard metrics sent to client
```

**Troubleshooting**:
- If "Offline": Check backend is running
- If error message: Verify `.env` has correct `VITE_DASHBOARD_SECRET`
- If no data: Backend might not have any sessions yet

---

### Test 2: Meeting Bot Control 🤖
**What it does**: Starts AI bot to join Google Meet and conduct interviews

**How to test**:
1. Add `<MeetingBotControl />` to a page (or create `/meeting-bot` route)
2. Enter test data:
   - **Meeting Link**: `https://meet.google.com/xxx-yyyy-zzz` (use a real or test link)
   - **Interview ID**: `test_interview_001`
3. Click "Start Bot"
4. Watch status badge change to "JOINING" → "ACTIVE"
5. Live transcript should appear below
6. Click "Stop Bot" to end session

**API Test (without UI)**:
```powershell
# Test in PowerShell
$body = @{
    meeting_link = "https://meet.google.com/xxx-yyyy-zzz"
    interview_id = "test_001"
    bot_name = "AI Assistant"
    auto_transcribe = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/meet/start" -Method POST -Body $body -ContentType "application/json"
```

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "session_id": "unique_session_id",
    "bot_id": "bot_12345",
    "status": "joining",
    "join_time": "2024-12-20T10:30:00"
  }
}
```

---

### Test 3: Chart Visualizations 📊
**What it does**: Displays latency and performance metrics in visual charts

**How to test**:
1. Navigate to Dashboard
2. Scroll down to see two charts:
   - **Latency Chart** (line chart): Shows STT, LLM, TTS latency
   - **Performance Radar Chart**: Shows 5-dimensional performance view
3. Charts should update automatically with WebSocket data
4. Hover over data points to see tooltips

**Data verification**:
```typescript
// In browser console:
// The charts get data from useDashboardWebSocket hook
// You can check the data structure:
console.log(metrics.latency);
// Should output: { stt: {avg, min, max}, llm: {avg, min, max}, tts: {avg, min, max} }
```

**Expected Behavior**:
- Charts render without errors
- Tooltips show correct values
- Real-time updates reflect in chart animations

---

### Test 4: Interview Analytics Page 📈
**What it does**: Generates comprehensive interview analysis reports

**How to test**:

**Option A: Add Route** (Recommended)
Edit `src/App.tsx` or routing file:
```typescript
import InterviewAnalytics from '@/pages/InterviewAnalytics';

// Add route:
<Route path="/analytics" element={<InterviewAnalytics />} />
```

**Option B: Direct API Test**
```powershell
# Analyze an interview
$body = @{
    interview_id = "test_interview_001"
    include_resume_match = $true
    include_communication_analysis = $true
    include_technical_depth = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/analytics/analyze" -Method POST -Body $body -ContentType "application/json"
```

**UI Test Steps**:
1. Navigate to `/analytics`
2. Enter Interview ID: `test_interview_001`
3. Click "Analyze"
4. Wait for report to load (2-5 seconds)
5. View comprehensive report:
   - Candidate info card
   - Overall score (large circular display)
   - Hiring recommendation badge
   - Score breakdown radar chart
   - Strengths (green checkmarks)
   - Weaknesses (yellow X icons)
   - Detailed analysis sections
   - Recommendations list
6. Click "Export PDF" to download report

**Expected Report Sections**:
- ✅ Candidate Info (Name, Position, Date, Duration)
- ✅ Overall Score (0-100)
- ✅ Hiring Recommendation (Strongly Recommend / Recommend / Consider / Not Recommended)
- ✅ Score Breakdown Chart (Technical, Communication, Problem Solving, Resume Match, Overall)
- ✅ Strengths List
- ✅ Weaknesses List
- ✅ Detailed Analysis (4 sections)
- ✅ Recommendations List

---

### Test 5: PDF Export Functionality 📄
**What it does**: Exports interview analysis report as PDF

**How to test**:
1. Generate a report (follow Test 4 steps)
2. Click "Export PDF" button
3. Browser should trigger download
4. Check Downloads folder for file named: `interview_report_<CandidateName>_<Date>.pdf`

**API Test**:
```powershell
# Download PDF directly
Invoke-WebRequest -Uri "http://localhost:8001/api/analytics/export/test_interview_001/pdf" -OutFile "report.pdf"
```

**Expected Behavior**:
- Button shows loading spinner during export
- PDF downloads automatically
- File opens in PDF viewer
- Report contains all data from UI

---

## 🔍 Debugging Checklist

### WebSocket Not Connecting?
1. ✅ Backend running on port 8001?
2. ✅ `.env` file has correct `VITE_WS_URL=ws://localhost:8001`?
3. ✅ `VITE_DASHBOARD_SECRET` matches backend config?
4. ✅ Check browser console for WebSocket errors
5. ✅ Firewall blocking WebSocket connections?

### API Calls Failing?
1. ✅ Backend running?
2. ✅ `.env` file has correct `VITE_API_URL=http://localhost:8001`?
3. ✅ CORS enabled on backend?
4. ✅ Check Network tab in DevTools for 404/500 errors
5. ✅ Backend logs show requests?

### Charts Not Rendering?
1. ✅ `chart.js` and `react-chartjs-2` installed?
2. ✅ Browser console shows chart registration errors?
3. ✅ Data structure matches expected format?
4. ✅ Try refreshing page (Ctrl+F5)

### PDF Export Not Working?
1. ✅ Backend has PDF generation dependencies?
2. ✅ Check backend logs for PDF creation errors
3. ✅ Browser blocking downloads?
4. ✅ Popup blocker active?

---

## 📊 Sample Test Data

### Create Test Interview Session
```powershell
# In backend directory
python -c "
from main import app, db_manager
import asyncio

async def create_test_session():
    session_data = {
        'interview_id': 'test_interview_001',
        'candidate_name': 'John Doe',
        'position': 'Senior Python Developer',
        'status': 'completed',
        'turns': 15,
        'quality_score': 92.5,
        'latency_avg': 350,
        'transcript': [
            {'speaker': 'AI', 'text': 'Hello! Tell me about yourself.', 'timestamp': '2024-12-20T10:00:00'},
            {'speaker': 'Candidate', 'text': 'I have 5 years of Python experience...', 'timestamp': '2024-12-20T10:00:30'}
        ]
    }
    await db_manager.create_interview_session(session_data)
    print('Test session created!')

asyncio.run(create_test_session())
"
```

---

## 🎯 Success Criteria

Your implementation is working correctly if:

- ✅ **Dashboard**: Shows live metrics with green "Live" indicator
- ✅ **WebSocket**: Reconnects automatically if disconnected
- ✅ **Charts**: Render without errors and update in real-time
- ✅ **Meeting Bot**: Can start, shows status, displays transcript
- ✅ **Analytics**: Generates reports with all sections
- ✅ **PDF Export**: Downloads report successfully
- ✅ **No Errors**: Browser console is clean (no red errors)
- ✅ **Responsive**: Works on different screen sizes

---

## 🚨 Common Issues & Solutions

### Issue 1: "WebSocket connection failed"
**Solution**: 
```powershell
# Check backend WebSocket endpoint
curl -v --no-buffer --http1.1 --include --header "Connection: Upgrade" --header "Upgrade: websocket" --header "Sec-WebSocket-Key: test" --header "Sec-WebSocket-Version: 13" http://localhost:8001/api/dashboard/ws?secret=your_secret
```

### Issue 2: "Cannot read property 'total' of undefined"
**Solution**: Backend not sending data yet. Wait 5 seconds or check backend logs.

### Issue 3: "CORS error"
**Solution**: Add CORS middleware in `backend/main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue 4: Charts not updating
**Solution**: Check WebSocket is connected. If offline, charts show last known data.

---

## 📸 Expected Screenshots

### 1. Dashboard with Live Data
- Top: 4 metric cards (Sessions, Active, Completed, Score)
- Green "Live" indicator
- Below: Latency line chart + Performance radar chart

### 2. Meeting Bot Control
- Input fields for Meeting Link and Interview ID
- "Start Bot" button (blue)
- Status badge showing "ACTIVE"
- Live transcript section with speaker labels and timestamps

### 3. Interview Analytics
- Search bar with Interview ID
- Report cards (Candidate Info, Overall Score, Recommendation)
- Large radar chart with 5 dimensions
- Strengths/Weaknesses lists with icons
- Detailed analysis sections

### 4. PDF Export
- Clicking "Export PDF" → Browser downloads file
- PDF contains all report data in formatted layout

---

## ⏱️ Performance Benchmarks

Expected loading times:
- Dashboard initial load: <1 second
- WebSocket connection: <500ms
- Chart rendering: <200ms
- Meeting bot start: 2-5 seconds (waiting for Google Meet)
- Analytics report generation: 3-10 seconds (AI processing)
- PDF export: 1-3 seconds

---

## 🎉 Ready to Test!

You now have a complete guide to test all 5 new frontend features. Start with the backend, then frontend, and test each feature systematically.

**Estimated Total Testing Time**: 15-20 minutes

Good luck! 🚀
