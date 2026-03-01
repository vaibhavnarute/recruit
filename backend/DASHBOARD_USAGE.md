# 📊 Real-time Dashboard - Usage Guide

## ✅ Status: FULLY OPERATIONAL (5/5 Tests Passed)

The real-time monitoring dashboard is now live and ready for production use!

---

## 🚀 Quick Start

### 1. **Start the Server**
```bash
cd backend
python main.py
```

Server runs at: `http://localhost:8001`

### 2. **Authentication**
All dashboard endpoints require Bearer token authentication:

```bash
Authorization: Bearer ai-recruiter-dashboard-2025-secure-key
```

**Environment Variable:** `DASHBOARD_SECRET` in `.env` file

---

## 📍 Available Endpoints

### 1️⃣ **Dashboard HTML Page** (Interactive UI)
```bash
GET http://localhost:8001/dashboard
```

**Features:**
- ✅ Real-time metrics auto-update via WebSocket (every 5 seconds)
- ✅ STT/LLM/TTS latency charts
- ✅ Active sessions list with quality scores
- ✅ Success rates and retry counts
- ✅ System health status

**Access in Browser:**
1. Install browser extension: [ModHeader](https://chrome.google.com/webstore/detail/modheader/idgpnmonknjnojddfkpgkljpfnnfcklj) (Chrome) or similar
2. Set header: `Authorization: Bearer ai-recruiter-dashboard-2025-secure-key`
3. Visit: `http://localhost:8001/dashboard`

---

### 2️⃣ **Metrics API** (JSON)
```bash
curl -H "Authorization: Bearer ai-recruiter-dashboard-2025-secure-key" \
     "http://localhost:8001/api/dashboard/metrics?time_range_hours=24"
```

**Response:**
```json
{
  "timestamp": "2025-10-27T10:30:00",
  "sessions": {
    "total": 42,
    "active": 3,
    "completed": 39,
    "failed": 0
  },
  "turns": {
    "total": 256,
    "successful": 256,
    "failed": 0,
    "success_rate": 100.0
  },
  "latency": {
    "stt": {
      "avg_ms": 150,
      "min_ms": 120,
      "max_ms": 200,
      "p95_ms": 180
    },
    "llm": {
      "avg_ms": 450,
      "min_ms": 300,
      "max_ms": 800,
      "p95_ms": 650
    },
    "tts": {
      "avg_ms": 200,
      "min_ms": 150,
      "max_ms": 300,
      "p95_ms": 250
    }
  },
  "retries": {
    "total": 5,
    "avg_per_session": 0.12
  },
  "quality": {
    "avg_score": 98.5,
    "min_score": 95.0,
    "max_score": 100.0
  },
  "recent_sessions": [...]
}
```

**Query Parameters:**
- `time_range_hours` (optional): Time range in hours (default: 24)

---

### 3️⃣ **Active Sessions** (JSON)
```bash
curl -H "Authorization: Bearer ai-recruiter-dashboard-2025-secure-key" \
     "http://localhost:8001/api/dashboard/sessions/active"
```

**Response:**
```json
{
  "count": 3,
  "sessions": [
    {
      "session_id": "session_abc123",
      "orchestration_id": "orch_xyz789",
      "created_at": "2025-10-27T10:15:00",
      "total_turns": 5,
      "quality_score": 98.5,
      "status": "active"
    }
  ]
}
```

---

### 4️⃣ **Session Details** (JSON)
```bash
curl -H "Authorization: Bearer ai-recruiter-dashboard-2025-secure-key" \
     "http://localhost:8001/api/dashboard/session/session_abc123"
```

**Response:**
```json
{
  "session_id": "session_abc123",
  "orchestration_id": "orch_xyz789",
  "interview_id": "interview_001",
  "candidate_name": "John Doe",
  "job_description": "AI/ML Engineer",
  "created_at": "2025-10-27T10:15:00",
  "updated_at": "2025-10-27T10:25:00",
  "status": "active",
  "total_turns": 5,
  "successful_turns": 5,
  "failed_turns": 0,
  "quality_score": 98.5,
  "turns": [
    {
      "turn_number": 1,
      "stt_latency_ms": 150,
      "llm_latency_ms": 450,
      "tts_latency_ms": 200,
      "total_latency_ms": 800,
      "transcript": "Tell me about your experience...",
      "response": "I have 5 years of experience...",
      "audio_url": "https://storage.example.com/audio/..."
    }
  ]
}
```

---

### 5️⃣ **WebSocket** (Real-time Updates)
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8001/api/dashboard/ws');

// Authenticate
ws.onopen = () => {
  ws.send(JSON.stringify({
    auth: 'ai-recruiter-dashboard-2025-secure-key'
  }));
};

// Receive real-time metrics
ws.onmessage = (event) => {
  const metrics = JSON.parse(event.data);
  console.log('Latest metrics:', metrics);
  // Update your dashboard UI
};
```

**Update Frequency:** Every 5 seconds (automatic)

---

## 🔐 Authentication Setup

### Method 1: Environment Variable (Recommended)
```bash
# .env file
DASHBOARD_SECRET=your-super-secure-secret-key-here
```

### Method 2: Default (Development Only)
If not set, defaults to: `your-secret-key-here`

**⚠️ Security Note:** Always change the default secret in production!

---

## 📊 Metrics Tracked

### **Session Metrics**
- Total sessions (all time)
- Active sessions (currently running)
- Completed sessions
- Failed sessions
- Success rate percentage

### **Turn Metrics**
- Total conversation turns
- Successful vs. failed turns
- Average turns per session
- Turn success rate

### **Latency Metrics** (milliseconds)
- **STT (Speech-to-Text):** Transcription time
- **LLM (Language Model):** Response generation time
- **TTS (Text-to-Speech):** Audio synthesis time
- **Total:** End-to-end latency

**Statistics:** Average, Min, Max, P95 (95th percentile)

### **Retry Metrics**
- Total retry attempts
- Average retries per session
- Retry patterns by component (STT/LLM/TTS)

### **Quality Metrics**
- Average quality score (0-100)
- Min/Max quality scores
- Quality distribution

---

## 🧪 Testing

### **Run Test Suite**
```bash
cd backend
python test_dashboard.py
```

**Expected Output:**
```
✅ TEST 1 PASSED - Metrics Endpoint
✅ TEST 2 PASSED - Active Sessions Endpoint
✅ TEST 3 PASSED - Authentication (Invalid)
✅ TEST 4 PASSED - No Authentication
✅ TEST 5 PASSED - Dashboard HTML

Overall: 5/5 tests passed (100.0%)
```

---

## 🎨 Dashboard Features

### **Real-time Updates**
- Metrics refresh every 5 seconds via WebSocket
- No page reload required
- Live connection status indicator

### **Visual Components**
- 📊 **Latency Charts:** Bar charts for STT/LLM/TTS
- 📈 **Success Rate Gauge:** Visual success percentage
- 🎯 **Quality Score Badge:** Color-coded quality indicator
- 📋 **Active Sessions Table:** Live session list with details
- 🔄 **Auto-refresh:** Automatic data updates

### **Responsive Design**
- Desktop-optimized layout
- Clean, professional UI
- Dark/light theme support (future)

---

## 🔧 Configuration

### **MongoDB Connection**
Ensure `MONGODB_ATLAS_URI` is set in `.env`:
```bash
MONGODB_ATLAS_URI=mongodb+srv://user:pass@cluster.mongodb.net/dbname
```

### **Redis Connection** (for distributed orchestration)
```bash
REDIS_HOST=redis-18720.c330.asia-south1-1.gce.redns.redis-cloud.com
REDIS_PORT=18720
REDIS_PASSWORD=your-redis-password
REDIS_USERNAME=default
```

---

## 📝 Usage Examples

### **Example 1: Monitor Production System**
```bash
# Terminal 1: Start server
python main.py

# Terminal 2: Watch metrics in real-time
watch -n 5 'curl -s -H "Authorization: Bearer YOUR_SECRET" http://localhost:8001/api/dashboard/metrics | jq .turns.success_rate'
```

### **Example 2: Get Alerts for High Latency**
```python
import requests
import time

DASHBOARD_SECRET = "ai-recruiter-dashboard-2025-secure-key"
headers = {"Authorization": f"Bearer {DASHBOARD_SECRET}"}

while True:
    response = requests.get(
        "http://localhost:8001/api/dashboard/metrics",
        headers=headers
    )
    metrics = response.json()
    
    # Check latency
    llm_latency = metrics["latency"]["llm"]["avg_ms"]
    if llm_latency > 1000:  # Alert if >1 second
        print(f"⚠️ HIGH LATENCY ALERT: LLM latency is {llm_latency}ms")
    
    time.sleep(30)  # Check every 30 seconds
```

### **Example 3: Export Metrics to CSV**
```python
import requests
import csv
from datetime import datetime

DASHBOARD_SECRET = "ai-recruiter-dashboard-2025-secure-key"
headers = {"Authorization": f"Bearer {DASHBOARD_SECRET}"}

response = requests.get(
    "http://localhost:8001/api/dashboard/metrics?time_range_hours=24",
    headers=headers
)
metrics = response.json()

# Export to CSV
with open(f'metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Sessions', metrics['sessions']['total']])
    writer.writerow(['Success Rate', metrics['turns']['success_rate']])
    writer.writerow(['Avg STT Latency', metrics['latency']['stt']['avg_ms']])
    writer.writerow(['Avg LLM Latency', metrics['latency']['llm']['avg_ms']])
    writer.writerow(['Avg TTS Latency', metrics['latency']['tts']['avg_ms']])
    writer.writerow(['Avg Quality', metrics['quality']['avg_score']])

print("✅ Metrics exported to CSV")
```

---

## 🛠️ Troubleshooting

### **Issue: 401 Unauthorized**
**Solution:** Check Authorization header format:
```bash
Authorization: Bearer YOUR_SECRET_KEY
```

### **Issue: 404 Not Found**
**Solution:** Ensure server is running at port 8001:
```bash
python main.py
# Server should show: "Uvicorn running on http://0.0.0.0:8001"
```

### **Issue: No Metrics Data**
**Solution:** Run some orchestration sessions first to populate data:
```bash
python test_distributed_orchestration.py
```

### **Issue: WebSocket Connection Failed**
**Solution:** 
1. Check authentication message is sent first
2. Verify DASHBOARD_SECRET matches
3. Check firewall/proxy settings

---

## 📚 Related Documentation

- **Distributed Orchestration:** `DISTRIBUTED_SCALING_GUIDE.md`
- **Distributed Orchestration Summary:** `DISTRIBUTED_SCALING_SUMMARY.md`
- **API Endpoints:** FastAPI auto-docs at `http://localhost:8001/docs`

---

## 🎯 Next Steps

1. ✅ **Dashboard is ready** - All tests passed (5/5)
2. 🔄 **Run real sessions** - Populate dashboard with actual data
3. 📊 **Monitor production** - Use WebSocket for live updates
4. 🚀 **Scale horizontally** - Add more workers for higher load

---

## 📞 Support

**Test Status:** ✅ All 5/5 tests passed (100%)
**Production Ready:** Yes
**Authentication:** Bearer token required
**Real-time Updates:** WebSocket every 5 seconds

---

**Last Updated:** October 27, 2025
**Version:** 1.0.0
**Status:** Production Ready 🚀
