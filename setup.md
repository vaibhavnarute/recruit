# Setup Guide (Share with Friend)

This file helps a new developer run the project from scratch.

Project root: `final_ai_rectruter`

---

## 1) Prerequisites

Install these first:
- Python **3.11**
- Node.js **18+**
- Git
- (Recommended) MongoDB Atlas account
- Groq API key
- Deepgram API key

---

## 2) Clone Project

```powershell
git clone https://github.com/vaibhavnarute/recruit.git
cd recruit
```

If your folder name is already `final_ai_rectruter`, just open that folder.

---

## 3) Create Python Virtual Environment (venv)

### Windows PowerShell

```powershell
python -m venv venv311
.\venv311\Scripts\Activate.ps1
```

If PowerShell blocks scripts:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv311\Scripts\Activate.ps1
```

### macOS/Linux

```bash
python3.11 -m venv venv311
source venv311/bin/activate
```

---

## 4) Install Python Requirements

From project root:

```powershell
pip install -r requirements-py311.txt
pip install -r backend/requirements.txt
```

Optional extra file (if needed for specific backend tests):

```powershell
pip install -r backend/fastapi_requirements.txt
```

---

## 5) Install Frontend Requirements

Root frontend:

```powershell
npm install
```

If using the separate frontend app in `talentstream-hr`:

```powershell
cd talentstream-hr
npm install
cd ..
```

---

## 6) Playwright Browser Setup (for Google Meet bot)

```powershell
playwright install chromium
```

---

## 7) Backend .env Setup (Important)

Inside `backend/`, you already have:
- `.env.example`
- `.env.template`

Create real env file:

```powershell
Copy-Item backend/.env.template backend/.env
```

You can also use `.env.example`, but `.env.template` is more complete.

Then open `backend/.env` and fill values.

---

## 8) What to Fill in `backend/.env`

Minimum required to run core flow:

```env
# LLM / STT
GROQ_API_KEY=your_groq_api_key_here

# MongoDB
MONGODB_URI=your_mongodb_connection_string
MONGO_URI=your_mongodb_connection_string
MONGO_DB_NAME=ai_recruiter

# Meet bot credentials
MEET_BOT_EMAIL=your_bot_email@gmail.com
MEET_BOT_PASSWORD=your_bot_password_here

# TTS
DEEPGRAM_API_KEY=your_deepgram_key
```

Recommended extra keys (already present in template):
- `API_KEY_ANALYSIS`
- `API_KEY_QA`
- `API_KEY_QUESTIONS`
- `API_KEY_IMPROVEMENT`
- `API_KEY_IMPROVED_RESUME`

If scheduling is used, also configure:
- `GOOGLE_CALENDAR_CREDENTIALS_PATH`
- `GOOGLE_CALENDAR_TOKEN_PATH`
- SMTP/Firebase values if needed

---

## 9) Note on `.env.example` vs `.env.template`

### `backend/.env.example`
Simple and short; mostly Meet bot + basic keys.

### `backend/.env.template`
Detailed and recommended; includes:
- Groq keys
- MongoDB configs
- Meet bot configs
- WebSocket/API ports
- Calendar/Firebase placeholders
- security/logging settings

Use `.env.template` as the main base file for new setup.

---

## 10) Run Backend

### Option A (Simple): run with Python directly

```powershell
cd backend
python main.py
```

### Option B (Dev): run with Uvicorn single worker

```powershell
cd backend
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Option C (Recommended for this project): 4 workers

```powershell
cd backend
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
```

### Option D (same as Option C via script)

```powershell
cd backend
.\start_4_workers.ps1
```

After starting backend, open:
- Swagger docs: `http://localhost:8001/docs`
- Health/API base: `http://localhost:8001`

---

## 11) Run Frontend

From root:

```powershell
npm run dev
```

If working with `talentstream-hr` frontend:

```powershell
cd talentstream-hr
npm run dev
```

---

## 12) First-Time Google Meet Bot Login

Run once to create saved session cookies:

```powershell
cd backend
python meet_bot_launcher.py
```

Login manually in opened browser (first time only).  
Session gets saved under `backend/meet_bot_sessions/`.

---

## 13) Quick Health Checks

Backend API check:

```powershell
Invoke-WebRequest http://localhost:8001/docs
```

Run end-to-end Meet interview test:

```powershell
cd backend
python test_complete_meet_interview.py
```

---

## 14) Common Errors

### `ModuleNotFoundError`
- venv not activated or requirements not installed.

### `401/invalid API key`
- Check `GROQ_API_KEY` / `DEEPGRAM_API_KEY` in `backend/.env`.

### MongoDB connection fails
- Verify `MONGODB_URI` and whitelist IP in Atlas.

### Meet bot login fails
- Verify `MEET_BOT_EMAIL` and `MEET_BOT_PASSWORD`.
- Use dedicated Google account.

### Playwright browser missing
- Run `playwright install chromium` again.

---

## 15) Share Checklist (Before sending to friend)

- [ ] `setup.md` included (this file)
- [ ] `backend/.env.template` included
- [ ] `backend/.env.example` included
- [ ] `backend/.env` **NOT** shared with secrets
- [ ] `google_credentials.json` and tokens handled securely
- [ ] README + setup commands verified on clean machine

---

If your friend follows this file in order, they should be able to run backend, frontend, and Meet bot locally.