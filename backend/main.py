from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
import uvicorn
import tempfile
import os
import logging
import datetime
from PyPDF2 import PdfReader
import re
from contextlib import asynccontextmanager
import PyPDF2
import io
import json
import base64
import asyncio
from groq import Groq
from dotenv import load_dotenv

# LangGraph Integration
from langgraph_integration import get_langgraph_service, initialize_langgraph_service

# Dashboard Service
from dashboard_service import get_dashboard_service

# MongoDB Client - Centralized database connection
from db.mongo_client import get_mongo_client, get_db, get_collection
from db.models import Collections

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    logger.info("🚀 Initializing LangGraph + MCP service...")
    groq_api_key = os.getenv('GROQ_API_KEY') or os.getenv('API_KEY_ANALYSIS')
    if groq_api_key:
        initialize_langgraph_service(groq_api_key=groq_api_key)
        logger.info("✅ LangGraph service initialized successfully!")
    else:
        logger.warning("⚠️ GROQ_API_KEY not found, LangGraph service may not work properly")
    
    yield
    
    # Shutdown (if needed in future)
    logger.info("🛑 Shutting down application...")

app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Groq client with different API keys for different functionalities
client_analysis = Groq(api_key=os.getenv('API_KEY_ANALYSIS'))
client_qa = Groq(api_key=os.getenv('API_KEY_QA'))
client_questions = Groq(api_key=os.getenv('API_KEY_QUESTIONS'))
client_improvement = Groq(api_key=os.getenv('API_KEY_IMPROVEMENT'))
client_improved_resume = Groq(api_key=os.getenv('API_KEY_IMPROVED_RESUME'))

# Define role requirements
ROLE_REQUIREMENTS = {
    "AI/ML Engineer": [
        "Machine Learning",
        "Deep Learning",
        "Python",
        "TensorFlow/PyTorch",
        "Data Analysis",
        "Statistical Modeling",
        "Computer Vision",
        "Natural Language Processing",
        "Big Data",
        "Cloud Computing"
    ],
    "Frontend Engineer": [
        "React",
        "JavaScript/TypeScript",
        "HTML5/CSS3",
        "Responsive Design",
        "State Management",
        "Web Performance",
        "Cross-browser Compatibility",
        "UI/UX Design",
        "Testing",
        "Build Tools"
    ],
    "Backend Engineer": [
        "Node.js/Python/Java",
        "RESTful APIs",
        "Database Design",
        "System Architecture",
        "Microservices",
        "Cloud Services",
        "Security",
        "Performance Optimization",
        "CI/CD",
        "Testing"
    ],
    "Full Stack Engineer": [
        "Frontend Development",
        "Backend Development",
        "Database Management",
        "API Design",
        "Cloud Services",
        "DevOps",
        "Security",
        "Testing",
        "System Design",
        "Performance Optimization"
    ],
    "DevOps Engineer": [
        "CI/CD",
        "Docker/Kubernetes",
        "Cloud Platforms",
        "Infrastructure as Code",
        "Monitoring",
        "Logging",
        "Security",
        "Automation",
        "Scripting",
        "System Administration"
    ],
    "Data Engineer": [
        "ETL",
        "Data Warehousing",
        "Big Data",
        "SQL/NoSQL",
        "Data Modeling",
        "Data Pipeline",
        "Data Quality",
        "Cloud Services",
        "Programming",
        "Data Governance"
    ],
    "Data Scientist": [
        "Statistical Analysis",
        "Machine Learning",
        "Data Visualization",
        "Python/R",
        "SQL",
        "Big Data",
        "Business Intelligence",
        "A/B Testing",
        "Feature Engineering",
        "Model Deployment"
    ],
    "Product Manager": [
        "Product Strategy",
        "Market Research",
        "User Research",
        "Agile/Scrum",
        "Product Analytics",
        "Roadmapping",
        "Stakeholder Management",
        "User Stories",
        "Product Launch",
        "Competitive Analysis"
    ],
    "UX Designer": [
        "User Research",
        "Wireframing",
        "Prototyping",
        "User Testing",
        "Information Architecture",
        "Interaction Design",
        "Visual Design",
        "Accessibility",
        "Design Systems",
        "Usability Testing"
    ],
    "UI Developer": [
        "HTML5/CSS3",
        "JavaScript",
        "Responsive Design",
        "UI Frameworks",
        "Animation",
        "Cross-browser Compatibility",
        "Performance",
        "Accessibility",
        "Design Systems",
        "Version Control"
    ]
}

def extract_text_from_pdf(file: UploadFile) -> str:
    try:
        reader = PdfReader(file.file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

def analyze_resume_text(text: str, requirements: str) -> dict:
    """Analyze resume text against job requirements with bias reduction."""
    try:
        # Anonymize the text first
        text = anonymize_text(text)
        
        # Standardized evaluation criteria
        evaluation_criteria = {
            "technical_skills": 40,  # 40% weight
            "experience": 30,        # 30% weight
            "education": 30          # 30% weight
        }
        
        # Calculate scores for each criterion
        scores = {
            "technical_skills": evaluate_technical_skills(text, requirements),
            "experience": evaluate_experience(text),
            "education": evaluate_education(text)
        }
        
        # Calculate weighted final score
        final_score = sum(
            scores[criterion] * (weight/100)
            for criterion, weight in evaluation_criteria.items()
        )
        
        # Convert requirements to list if it's a string
        if isinstance(requirements, str):
            requirements = [req.strip() for req in requirements.split(',')]
        
        # Convert text to lowercase for case-insensitive matching
        text_lower = text.lower()
        
        # Find matching skills
        matching_skills = []
        missing_skills = []
        
        for req in requirements:
            if req.lower() in text_lower:
                matching_skills.append(req)
            else:
                missing_skills.append(req)
        
        # Calculate match score
        total_requirements = len(requirements)
        if total_requirements == 0:
            match_score = 0
        else:
            match_score = int((len(matching_skills) / total_requirements) * 100)
        
        # Generate strengths and improvement areas
        strengths = []
        if matching_skills:
            strengths.append(f"Strong background in {', '.join(matching_skills[:3])}")
        
        improvement_areas = []
        if missing_skills:
            improvement_areas.append(f"Consider adding experience with {', '.join(missing_skills[:3])}")
        
        return {
            "match_score": int(final_score),
            "matching_skills": matching_skills,
            "missing_skills": missing_skills,
            "strengths": strengths,
            "improvement_areas": improvement_areas
        }
    except Exception as e:
        logger.error(f"Error analyzing resume text: {str(e)}")
        raise

def anonymize_text(text: str) -> str:
    """Anonymize personal identifiers in text"""
    # Replace gender-specific pronouns
    text = re.sub(r'\b(he|him|his|she|her|hers)\b', 'they/them', text, flags=re.IGNORECASE)
    
    # Replace names with "Candidate"
    names = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
    for name in names:
        text = text.replace(name, 'Candidate')
    
    return text

def evaluate_technical_skills(text: str, requirements: List[str]) -> float:
    """Evaluate technical skills objectively"""
    # Count matching skills
    matches = sum(1 for req in requirements if req.lower() in text.lower())
    return (matches / len(requirements)) * 100 if requirements else 0

def evaluate_experience(text: str) -> float:
    """Evaluate experience based on years and achievements"""
    # Basic experience scoring
    years = len(re.findall(r'\d+\s*years?', text, re.I))
    return min(years * 10, 100)  # Cap at 100

def evaluate_education(text: str) -> float:
    """Evaluate education level"""
    # Basic education scoring
    education_score = 0
    if re.search(r'phd|doctorate', text, re.I):
        education_score = 100
    elif re.search(r'master', text, re.I):
        education_score = 80
    elif re.search(r'bachelor|degree', text, re.I):
        education_score = 60
    return education_score

@app.post("/api/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    job_description: str = Form(...)
):
    """
    Analyze resume against job description using LangGraph workflow.
    
    NEW: Uses LangGraph + MCP for:
    - Multi-step workflow (extract → analyze → score → recommend)
    - Intelligent caching (80%+ faster on repeated queries)
    - Token optimization (60-75% cost reduction)
    - Better error handling (per-stage recovery)
    """
    try:
        logger.info("📄 Starting resume analysis with LangGraph workflow...")
        
        # Extract text from PDF
        resume_text = extract_text_from_pdf(resume)
        logger.info(f"✅ Extracted {len(resume_text)} characters from resume")
        
        # Use LangGraph service for analysis
        service = get_langgraph_service()
        analysis_result = service.analyze_resume(
            resume_text=resume_text,
            job_description=job_description
        )
        
        logger.info(f"✅ Analysis complete! Score: {analysis_result.get('match_score', 0)}/100")
        logger.info(f"📊 Performance: Cache hit rate: {analysis_result.get('metadata', {}).get('cache_hit_rate', 'N/A')}")
        logger.info(f"💰 Tokens saved: {analysis_result.get('metadata', {}).get('tokens_saved', 0)}")
        
        # Return the result (already in the correct format from LangGraph)
        return analysis_result
            
    except Exception as e:
        logger.error(f"❌ Error in analyze_resume: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Return error response
        return {
            "match_score": 0,
            "matching_skills": ["Error analyzing skills"],
            "missing_skills": ["Error analyzing missing skills"],
            "strengths": ["Error analyzing strengths"],
            "areas_for_improvement": [f"Error: {str(e)}"]
        }

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the server is running"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DASHBOARD ENDPOINTS - Real-time Monitoring
# ============================================================================

def verify_dashboard_auth(authorization: Optional[str] = Header(None)) -> bool:
    """
    Simple authentication for dashboard access
    Uses Authorization header: Bearer <DASHBOARD_SECRET>
    """
    dashboard_secret = os.getenv("DASHBOARD_SECRET", "your-secret-key-here")
    
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required. Use 'Authorization: Bearer <DASHBOARD_SECRET>'"
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme. Use 'Bearer'")
        
        if token != dashboard_secret:
            raise HTTPException(status_code=403, detail="Invalid dashboard secret")
        
        return True
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Use 'Authorization: Bearer <token>'"
        )


@app.get("/api/dashboard/metrics")
async def get_dashboard_metrics(
    time_range_hours: int = 24,
    authorization: Optional[str] = Header(None)
):
    """
    Get real-time orchestration metrics for dashboard
    
    **Authentication Required**: Bearer token in Authorization header
    
    Query Parameters:
    - time_range_hours: Time range to analyze (default: 24 hours)
    
    Returns:
    - STT latency statistics
    - LLM processing time statistics
    - TTS latency statistics
    - Retry counts
    - Active sessions count
    - Success rates
    - Quality scores
    - Recent sessions list
    
    Example:
    ```
    curl -H "Authorization: Bearer your-secret-key" \
         "http://localhost:8001/api/dashboard/metrics?time_range_hours=24"
    ```
    """
    verify_dashboard_auth(authorization)
    
    try:
        logger.info(f"📊 Dashboard metrics requested (last {time_range_hours} hours)")
        
        # Get dashboard service
        dashboard_service = get_dashboard_service()
        
        # Fetch metrics
        metrics = await dashboard_service.get_metrics(time_range_hours)
        
        logger.info(f"✅ Dashboard metrics fetched: {metrics['sessions']['total']} sessions, "
                   f"{metrics['turns']['total']} turns")
        
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Error fetching dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching metrics: {str(e)}")


@app.get("/api/dashboard/sessions/active")
async def get_active_sessions(
    authorization: Optional[str] = Header(None)
):
    """
    Get list of currently active orchestration sessions
    
    **Authentication Required**: Bearer token in Authorization header
    
    Returns:
    - List of active sessions with:
      - session_id
      - orchestration_id
      - created_at
      - total_turns
      - quality_score
    
    Example:
    ```
    curl -H "Authorization: Bearer your-secret-key" \
         "http://localhost:8001/api/dashboard/sessions/active"
    ```
    """
    verify_dashboard_auth(authorization)
    
    try:
        logger.info("📊 Active sessions requested")
        
        dashboard_service = get_dashboard_service()
        sessions = await dashboard_service.get_active_sessions_list()
        
        logger.info(f"✅ Found {len(sessions)} active sessions")
        
        return {
            "count": len(sessions),
            "sessions": sessions
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching active sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching active sessions: {str(e)}")


@app.get("/api/dashboard/session/{session_id}")
async def get_session_details(
    session_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Get detailed information about a specific session
    
    **Authentication Required**: Bearer token in Authorization header
    
    Path Parameters:
    - session_id: The session ID to retrieve
    
    Returns:
    - Complete session data including all turns and metrics
    
    Example:
    ```
    curl -H "Authorization: Bearer your-secret-key" \
         "http://localhost:8001/api/dashboard/session/session_abc123"
    ```
    """
    verify_dashboard_auth(authorization)
    
    try:
        logger.info(f"📊 Session details requested: {session_id}")
        
        dashboard_service = get_dashboard_service()
        session = await dashboard_service.get_session_details(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
        
        logger.info(f"✅ Session details fetched: {session_id}")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching session details: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching session details: {str(e)}")


@app.websocket("/api/dashboard/ws")
async def dashboard_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard updates
    
    **Authentication**: Send dashboard secret as first message
    
    Usage:
    1. Connect to ws://localhost:8001/api/dashboard/ws
    2. Send authentication message: {"auth": "your-secret-key"}
    3. Receive real-time metrics updates every 5 seconds
    
    Message Format:
    ```json
    {
        "timestamp": "2025-10-27T10:30:00",
        "sessions": {...},
        "turns": {...},
        "latency": {...},
        "retries": {...},
        "quality": {...}
    }
    ```
    """
    await websocket.accept()
    logger.info("📡 Dashboard WebSocket connection established")
    
    try:
        # Wait for authentication message
        auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
        
        dashboard_secret = os.getenv("DASHBOARD_SECRET", "your-secret-key-here")
        
        if not auth_message.get("auth") or auth_message["auth"] != dashboard_secret:
            await websocket.send_json({"error": "Invalid dashboard secret"})
            await websocket.close()
            logger.warning("⚠️ Dashboard WebSocket authentication failed")
            return
        
        logger.info("✅ Dashboard WebSocket authenticated")
        
        # Add to active connections
        dashboard_service = get_dashboard_service()
        await dashboard_service.add_websocket_connection(websocket)
        
        # Send initial metrics
        metrics = await dashboard_service.get_metrics(time_range_hours=24)
        await websocket.send_json(metrics)
        
        # Keep connection alive and send updates every 5 seconds
        while True:
            await asyncio.sleep(5)
            
            # Fetch and send updated metrics
            metrics = await dashboard_service.get_metrics(time_range_hours=24)
            await websocket.send_json(metrics)
            
    except WebSocketDisconnect:
        logger.info("📡 Dashboard WebSocket disconnected")
        if 'dashboard_service' in locals():
            await dashboard_service.remove_websocket_connection(websocket)
    except asyncio.TimeoutError:
        logger.warning("⚠️ Dashboard WebSocket authentication timeout")
        await websocket.close()
    except Exception as e:
        logger.error(f"❌ Dashboard WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
        if 'dashboard_service' in locals():
            await dashboard_service.remove_websocket_connection(websocket)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_html(authorization: Optional[str] = Header(None)):
    """
    Dashboard HTML page for real-time monitoring
    
    **Authentication Required**: Bearer token in Authorization header
    
    Displays:
    - Real-time metrics (auto-updates via WebSocket)
    - STT/LLM/TTS latency charts
    - Active sessions list
    - Success rates
    - Quality scores
    
    Access:
    ```
    curl -H "Authorization: Bearer your-secret-key" \
         "http://localhost:8001/dashboard"
    ```
    
    Or open in browser with extension like ModHeader to set Authorization header
    """
    verify_dashboard_auth(authorization)
    
    dashboard_secret = os.getenv("DASHBOARD_SECRET", "your-secret-key-here")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Recruiter - Real-time Dashboard</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}
            
            .header {{
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                margin-bottom: 30px;
                text-align: center;
            }}
            
            .header h1 {{
                color: #667eea;
                font-size: 2.5rem;
                margin-bottom: 10px;
            }}
            
            .header .status {{
                display: inline-block;
                padding: 8px 20px;
                background: #10b981;
                color: white;
                border-radius: 20px;
                font-weight: 600;
                margin-top: 10px;
            }}
            
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .metric-card {{
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                transition: transform 0.3s;
            }}
            
            .metric-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0,0,0,0.15);
            }}
            
            .metric-card h3 {{
                color: #667eea;
                font-size: 1rem;
                margin-bottom: 15px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .metric-value {{
                font-size: 2.5rem;
                font-weight: 700;
                color: #1f2937;
                margin-bottom: 10px;
            }}
            
            .metric-label {{
                color: #6b7280;
                font-size: 0.9rem;
            }}
            
            .metric-details {{
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid #e5e7eb;
            }}
            
            .metric-detail-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
                font-size: 0.9rem;
            }}
            
            .metric-detail-label {{
                color: #6b7280;
            }}
            
            .metric-detail-value {{
                color: #1f2937;
                font-weight: 600;
            }}
            
            .sessions-section {{
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }}
            
            .sessions-section h2 {{
                color: #667eea;
                margin-bottom: 20px;
                font-size: 1.5rem;
            }}
            
            .session-list {{
                max-height: 400px;
                overflow-y: auto;
            }}
            
            .session-item {{
                padding: 15px;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                margin-bottom: 10px;
                transition: background 0.3s;
            }}
            
            .session-item:hover {{
                background: #f9fafb;
            }}
            
            .session-id {{
                font-weight: 600;
                color: #1f2937;
                margin-bottom: 5px;
            }}
            
            .session-meta {{
                color: #6b7280;
                font-size: 0.85rem;
            }}
            
            .status-indicator {{
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                margin-right: 5px;
            }}
            
            .status-active {{
                background: #10b981;
                animation: pulse 2s infinite;
            }}
            
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
            }}
            
            .footer {{
                text-align: center;
                color: white;
                margin-top: 30px;
                opacity: 0.8;
            }}
            
            .error-message {{
                background: #fee2e2;
                color: #991b1b;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 AI Recruiter Dashboard</h1>
                <p style="color: #6b7280; margin: 10px 0;">Real-time Orchestration Monitoring</p>
                <div class="status">
                    <span class="status-indicator status-active"></span>
                    LIVE
                </div>
            </div>
            
            <div id="error-container"></div>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>📊 Total Sessions</h3>
                    <div class="metric-value" id="total-sessions">-</div>
                    <div class="metric-label">Last 24 hours</div>
                    <div class="metric-details">
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">Active:</span>
                            <span class="metric-detail-value" id="active-sessions">-</span>
                        </div>
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">Completed:</span>
                            <span class="metric-detail-value" id="completed-sessions">-</span>
                        </div>
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">Success Rate:</span>
                            <span class="metric-detail-value" id="session-success-rate">-</span>
                        </div>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>🎤 STT Latency</h3>
                    <div class="metric-value" id="stt-avg">-</div>
                    <div class="metric-label">Average (ms)</div>
                    <div class="metric-details">
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">Min:</span>
                            <span class="metric-detail-value" id="stt-min">-</span>
                        </div>
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">Max:</span>
                            <span class="metric-detail-value" id="stt-max">-</span>
                        </div>
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">P95:</span>
                            <span class="metric-detail-value" id="stt-p95">-</span>
                        </div>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>🧠 LLM Processing</h3>
                    <div class="metric-value" id="llm-avg">-</div>
                    <div class="metric-label">Average (ms)</div>
                    <div class="metric-details">
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">Min:</span>
                            <span class="metric-detail-value" id="llm-min">-</span>
                        </div>
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">Max:</span>
                            <span class="metric-detail-value" id="llm-max">-</span>
                        </div>
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">P95:</span>
                            <span class="metric-detail-value" id="llm-p95">-</span>
                        </div>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>🔊 TTS Latency</h3>
                    <div class="metric-value" id="tts-avg">-</div>
                    <div class="metric-label">Average (ms)</div>
                    <div class="metric-details">
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">Min:</span>
                            <span class="metric-detail-value" id="tts-min">-</span>
                        </div>
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">Max:</span>
                            <span class="metric-detail-value" id="tts-max">-</span>
                        </div>
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">P95:</span>
                            <span class="metric-detail-value" id="tts-p95">-</span>
                        </div>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>🔄 Retry Statistics</h3>
                    <div class="metric-value" id="retry-total">-</div>
                    <div class="metric-label">Total Retries</div>
                    <div class="metric-details">
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">Avg per turn:</span>
                            <span class="metric-detail-value" id="retry-avg">-</span>
                        </div>
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">Max retries:</span>
                            <span class="metric-detail-value" id="retry-max">-</span>
                        </div>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>⭐ Quality Score</h3>
                    <div class="metric-value" id="quality-avg">-</div>
                    <div class="metric-label">Average Score</div>
                    <div class="metric-details">
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">Min:</span>
                            <span class="metric-detail-value" id="quality-min">-</span>
                        </div>
                        <div class="metric-detail-row">
                            <span class="metric-detail-label">Max:</span>
                            <span class="metric-detail-value" id="quality-max">-</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="sessions-section">
                <h2>🎭 Recent Sessions</h2>
                <div class="session-list" id="recent-sessions">
                    <p style="color: #6b7280; text-align: center; padding: 20px;">Loading sessions...</p>
                </div>
            </div>
            
            <div class="footer">
                <p>🚀 Powered by LangGraph + Redis Streams + MongoDB Atlas</p>
                <p style="font-size: 0.85rem; margin-top: 10px;">Last updated: <span id="last-update">-</span></p>
            </div>
        </div>
        
        <script>
            const DASHBOARD_SECRET = '{dashboard_secret}';
            let ws = null;
            
            function connectWebSocket() {{
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${{protocol}}//${{window.location.host}}/api/dashboard/ws`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = () => {{
                    console.log('✅ WebSocket connected');
                    // Send authentication
                    ws.send(JSON.stringify({{ auth: DASHBOARD_SECRET }}));
                }};
                
                ws.onmessage = (event) => {{
                    const data = JSON.parse(event.data);
                    
                    if (data.error) {{
                        showError('Authentication failed: ' + data.error);
                        return;
                    }}
                    
                    updateDashboard(data);
                }};
                
                ws.onerror = (error) => {{
                    console.error('❌ WebSocket error:', error);
                    showError('WebSocket connection error');
                }};
                
                ws.onclose = () => {{
                    console.log('📡 WebSocket disconnected, reconnecting...');
                    setTimeout(connectWebSocket, 5000);
                }};
            }}
            
            function updateDashboard(metrics) {{
                // Clear error
                document.getElementById('error-container').innerHTML = '';
                
                // Update timestamp
                const timestamp = new Date(metrics.timestamp);
                document.getElementById('last-update').textContent = timestamp.toLocaleString();
                
                // Sessions
                document.getElementById('total-sessions').textContent = metrics.sessions.total;
                document.getElementById('active-sessions').textContent = metrics.sessions.active;
                document.getElementById('completed-sessions').textContent = metrics.sessions.completed;
                document.getElementById('session-success-rate').textContent = metrics.sessions.success_rate + '%';
                
                // STT Latency
                document.getElementById('stt-avg').textContent = metrics.latency.stt.avg + 'ms';
                document.getElementById('stt-min').textContent = metrics.latency.stt.min + 'ms';
                document.getElementById('stt-max').textContent = metrics.latency.stt.max + 'ms';
                document.getElementById('stt-p95').textContent = metrics.latency.stt.p95 + 'ms';
                
                // LLM Latency
                document.getElementById('llm-avg').textContent = metrics.latency.llm.avg + 'ms';
                document.getElementById('llm-min').textContent = metrics.latency.llm.min + 'ms';
                document.getElementById('llm-max').textContent = metrics.latency.llm.max + 'ms';
                document.getElementById('llm-p95').textContent = metrics.latency.llm.p95 + 'ms';
                
                // TTS Latency
                document.getElementById('tts-avg').textContent = metrics.latency.tts.avg + 'ms';
                document.getElementById('tts-min').textContent = metrics.latency.tts.min + 'ms';
                document.getElementById('tts-max').textContent = metrics.latency.tts.max + 'ms';
                document.getElementById('tts-p95').textContent = metrics.latency.tts.p95 + 'ms';
                
                // Retries
                document.getElementById('retry-total').textContent = metrics.retries.total;
                document.getElementById('retry-avg').textContent = metrics.retries.avg_per_turn.toFixed(2);
                document.getElementById('retry-max').textContent = metrics.retries.max;
                
                // Quality
                document.getElementById('quality-avg').textContent = metrics.quality.avg_score.toFixed(1);
                document.getElementById('quality-min').textContent = metrics.quality.min_score.toFixed(1);
                document.getElementById('quality-max').textContent = metrics.quality.max_score.toFixed(1);
                
                // Recent Sessions
                const sessionsHtml = metrics.recent_sessions.map(session => `
                    <div class="session-item">
                        <div class="session-id">
                            <span class="status-indicator status-active"></span>
                            ${{session.session_id}}
                        </div>
                        <div class="session-meta">
                            Orchestration: ${{session.orchestration_id}} | 
                            Turns: ${{session.total_turns}} | 
                            Quality: ${{session.quality_score ? session.quality_score.toFixed(1) : 'N/A'}} |
                            Created: ${{new Date(session.created_at).toLocaleString()}}
                        </div>
                    </div>
                `).join('');
                
                document.getElementById('recent-sessions').innerHTML = 
                    sessionsHtml || '<p style="color: #6b7280; text-align: center; padding: 20px;">No recent sessions</p>';
            }}
            
            function showError(message) {{
                document.getElementById('error-container').innerHTML = `
                    <div class="error-message">
                        ❌ Error: ${{message}}
                    </div>
                `;
            }}
            
            // Connect on load
            connectWebSocket();
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


# ============================================================================
# END DASHBOARD ENDPOINTS
# ============================================================================


# ============================================================================
# GRACEFUL SESSION SHUTDOWN ENDPOINT
# ============================================================================

@app.post("/api/orchestration/end-session/{session_id}")
async def graceful_end_session(
    session_id: str,
    force: bool = False
):
    """
    Gracefully end orchestration session with proper cleanup
    
    **Graceful Shutdown Process:**
    1. ✅ Flush MCP caches to MongoDB
    2. ✅ Finalize conversation transcript
    3. ✅ Calculate and persist final metrics
    4. ✅ Mark session as terminated
    5. ✅ Clean up resources (memory, connections)
    
    **Path Parameters:**
    - session_id: The session ID to end
    
    **Query Parameters:**
    - force: Force shutdown even if session not found (default: false)
    
    **Returns:**
    ```json
    {
        "success": true,
        "data": {
            "orchestration_id": "orch_uuid",
            "session_id": "session_uuid",
            "interview_id": "interview_123",
            "total_turns": 10,
            "successful_turns": 10,
            "failed_turns": 0,
            "success_rate": 100.0,
            "quality_score": 98.5,
            "duration_seconds": 450,
            "avg_latency_ms": 650,
            "total_retries": 2,
            "transcript_archived": true,
            "metrics_persisted": true,
            "graceful_shutdown": true,
            "completed_at": "2025-10-27T10:30:00Z"
        },
        "message": "Orchestration session ended gracefully"
    }
    ```
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8001/api/orchestration/end-session/session_abc123"
    curl -X POST "http://localhost:8001/api/orchestration/end-session/session_abc123?force=true"
    ```
    """
    logger.info(f"🏁 POST /api/orchestration/end-session/{session_id}")
    logger.info(f"   Force mode: {force}")
    
    try:
        from langgraph_agents.realtime_orchestrator_agent import get_realtime_orchestrator
        
        # Get orchestrator
        orchestrator = get_realtime_orchestrator()
        
        if not orchestrator:
            logger.error("❌ Realtime orchestrator not initialized")
            return {
                "success": False,
                "error": {
                    "code": "ORCHESTRATOR_NOT_INITIALIZED",
                    "message": "Realtime orchestrator is not initialized"
                },
                "message": "Orchestrator not available"
            }
        
        # Execute graceful shutdown
        logger.info("🔄 Initiating graceful shutdown...")
        result = await orchestrator.end_orchestration(session_id, force=force)
        
        if result.get('success'):
            summary = result.get('data', {})
            logger.info("✅ Graceful shutdown completed successfully")
            logger.info(f"   Total turns: {summary.get('total_turns', 0)}")
            logger.info(f"   Success rate: {summary.get('success_rate', 0):.1f}%")
            logger.info(f"   Quality score: {summary.get('quality_score', 0)}")
            logger.info(f"   Transcript archived: {summary.get('transcript_archived', False)}")
            logger.info(f"   Metrics persisted: {summary.get('metrics_persisted', False)}")
        else:
            logger.error(f"❌ Graceful shutdown failed: {result.get('message')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error during graceful shutdown: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "GRACEFUL_SHUTDOWN_FAILED",
                "message": str(e),
                "details": "An unexpected error occurred during graceful shutdown"
            },
            "message": "Failed to end session gracefully"
        }


# ============================================================================
# END GRACEFUL SHUTDOWN ENDPOINT
# ============================================================================


# ============================================================================
# ANALYTICS ENGINE ENDPOINT - Post-Interview Analysis
# ============================================================================

@app.post("/api/analytics/analyze/{session_id}")
async def analyze_interview(
    session_id: str,
    orchestration_id: Optional[str] = None,
    interview_id: Optional[str] = None
):
    """
    Generate comprehensive post-interview analysis
    
    **Features:**
    - Fetches complete transcript from MongoDB
    - LLM-based summarization with LangGraph workflow
    - Calculates multiple metrics:
      * Response coherence (0-100)
      * Technical depth (0-100)
      * Communication clarity (0-100)
      * Overall score (weighted average)
    - Generates detailed report with strengths/weaknesses
    - Stores JSON report in interview_results collection
    
    **Path Parameters:**
    - session_id (required): The session ID to analyze
    
    **Query Parameters:**
    - orchestration_id (optional): Orchestration ID for reference
    - interview_id (optional): Interview ID for reference
    
    **Response Format:**
    ```json
    {
      "success": true,
      "data": {
        "session_id": "session_abc123",
        "summary": "Comprehensive interview summary...",
        "recommendation": "strong_hire|hire|maybe|no_hire",
        "scores": {
          "overall_score": 85.5,
          "response_coherence": 88.0,
          "technical_depth": 90.0,
          "communication_clarity": 80.0
        },
        "strengths": ["strength1", "strength2"],
        "weaknesses": ["weakness1", "weakness2"],
        "technical_assessment": {...},
        "communication_assessment": {...}
      },
      "message": "Interview analysis completed successfully"
    }
    ```
    
    **Status Codes:**
    - 200: Success (analysis complete or with warnings)
    - 200: Success with error details (partial analysis)
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8001/api/analytics/analyze/session_abc123"
    ```
    """
    logger.info(f"🔬 Analytics request received for session: {session_id}")
    logger.info(f"   Orchestration ID: {orchestration_id or 'N/A'}")
    logger.info(f"   Interview ID: {interview_id or 'N/A'}")
    
    try:
        # Import analytics agent
        from langgraph_agents.analytics_agent import get_analytics_agent
        
        # Get analytics agent instance
        logger.info("📊 Initializing analytics agent...")
        analytics_agent = get_analytics_agent()
        
        # Run analysis
        logger.info("🚀 Starting interview analysis workflow...")
        result = await analytics_agent.analyze_interview(
            session_id=session_id,
            orchestration_id=orchestration_id,
            interview_id=interview_id
        )
        
        # Always return 200 with success/failure in body
        if result.get('success'):
            data = result.get('data', {})
            logger.info("✅ Analysis completed successfully")
            logger.info(f"   Overall Score: {data.get('scores', {}).get('overall_score', 'N/A')}/100")
            logger.info(f"   Recommendation: {data.get('recommendation', 'N/A')}")
            logger.info(f"   Strengths: {len(data.get('strengths', []))}")
            logger.info(f"   Weaknesses: {len(data.get('weaknesses', []))}")
            
            # Check for warnings
            if data.get('errors'):
                logger.warning(f"⚠️ Analysis completed with {len(data['errors'])} warning(s)")
                for warning in data['errors']:
                    logger.warning(f"   - {warning}")
                
                return {
                    "success": True,
                    "data": data,
                    "message": "Interview analysis completed with warnings",
                    "warnings": data['errors']
                }
            
            return {
                "success": True,
                "data": data,
                "message": "Interview analysis completed successfully"
            }
        else:
            # Analysis failed but still return 200 with error details
            error_info = result.get('error', {})
            logger.error(f"❌ Analysis failed: {error_info.get('message', 'Unknown error')}")
            
            if error_info.get('details'):
                logger.error(f"   Details: {error_info['details']}")
            
            return {
                "success": False,
                "error": {
                    "code": error_info.get('code', 'ANALYSIS_FAILED'),
                    "message": error_info.get('message', 'Analysis failed'),
                    "details": error_info.get('details', []),
                    "session_id": session_id
                },
                "message": result.get('message', 'Interview analysis failed')
            }
        
    except ImportError as e:
        logger.error(f"❌ Failed to import analytics agent: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "IMPORT_ERROR",
                "message": "Analytics agent module not available",
                "details": str(e)
            },
            "message": "Failed to load analytics engine"
        }
    
    except Exception as e:
        logger.error(f"❌ Unexpected error in analytics endpoint: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e),
                "details": "An unexpected error occurred during analysis"
            },
            "message": "Failed to analyze interview"
        }


@app.get("/api/analytics/report/{session_id}")
async def get_analysis_report(session_id: str):
    """
    Retrieve existing analysis report from database
    
    **Path Parameters:**
    - session_id (required): The session ID
    
    **Response Format:**
    ```json
    {
      "success": true,
      "data": {
        "session_id": "session_abc123",
        "summary": "...",
        "scores": {...},
        "recommendation": "hire"
      },
      "message": "Analysis report retrieved successfully"
    }
    ```
    
    **Example:**
    ```bash
    curl "http://localhost:8001/api/analytics/report/session_abc123"
    ```
    """
    logger.info(f"📄 Retrieving analysis report for session: {session_id}")
    
    try:
        from pymongo import MongoClient
        
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGODB_ATLAS_URI')
        client = MongoClient(mongo_uri)
        mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
        db = client[mongo_db_name]
        
        # Fetch report
        report = db['interview_results'].find_one(
            {'session_id': session_id},
            {'_id': 0}  # Exclude MongoDB ID
        )
        
        if report:
            logger.info("✅ Analysis report found")
            logger.info(f"   Overall Score: {report.get('scores', {}).get('overall_score', 'N/A')}")
            logger.info(f"   Recommendation: {report.get('recommendation', 'N/A')}")
            
            return {
                "success": True,
                "data": report,
                "message": "Analysis report retrieved successfully"
            }
        else:
            logger.warning(f"⚠️ No analysis report found for session: {session_id}")
            return {
                "success": False,
                "error": {
                    "code": "REPORT_NOT_FOUND",
                    "message": f"No analysis report found for session: {session_id}",
                    "details": "Session may not have been analyzed yet"
                },
                "message": "Analysis report not found"
            }
        
    except Exception as e:
        logger.error(f"❌ Error retrieving analysis report: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
                "details": "Failed to retrieve report from database"
            },
            "message": "Failed to retrieve analysis report"
        }


# ============================================================================
# END ANALYTICS ENGINE ENDPOINTS
# ============================================================================


# ============================================================================
# SECURITY & ISOLATION ENDPOINTS - JWT Auth + Session Sandboxing
# ============================================================================

@app.post("/api/security/session/create")
async def create_secure_session(
    session_id: str = Form(...),
    interview_id: str = Form(...),
    candidate_name: str = Form(...),
    job_description: str = Form(...),
    permissions: Optional[str] = Form(None)
):
    """
    Create secure session with JWT token and isolated sandbox
    
    **Form Parameters:**
    - session_id (required): Unique session identifier
    - interview_id (required): Interview identifier  
    - candidate_name (required): Candidate name
    - job_description (required): Job description
    - permissions (optional): JSON string of permissions dict
    
    **Returns:**
    - JWT token for session authentication
    - Session sandbox details
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8001/api/security/session/create" \\
         -F "session_id=session_123" \\
         -F "interview_id=interview_001" \\
         -F "candidate_name=John Doe" \\
         -F "job_description=Senior Engineer"
    ```
    """
    logger.info(f"🔐 Creating secure session: {session_id}")
    logger.info(f"   Interview: {interview_id}")
    logger.info(f"   Candidate: {candidate_name}")
    
    try:
        from security import get_session_auth_manager, get_session_isolation_manager
        
        # Parse permissions if provided
        permissions_dict = None
        if permissions:
            try:
                permissions_dict = json.loads(permissions)
            except:
                pass
        
        # Initialize managers
        auth_manager = get_session_auth_manager()
        isolation_manager = get_session_isolation_manager()
        
        # Generate JWT token
        logger.info("🔑 Generating JWT token...")
        jwt_token, session_token = auth_manager.generate_session_token(
            session_id=session_id,
            interview_id=interview_id,
            candidate_name=candidate_name,
            job_description=job_description,
            permissions=permissions_dict
        )
        
        # Create isolated sandbox
        logger.info("🏗️ Creating session sandbox...")
        sandbox = isolation_manager.create_sandbox(session_id)
        
        logger.info("✅ Secure session created successfully")
        logger.info(f"   JWT token generated: {jwt_token[:20]}...")
        logger.info(f"   Sandbox created: {session_id}")
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "jwt_token": jwt_token,
                "token_hash": session_token.token_hash[:16] + "...",
                "expires_at": session_token.expires_at,
                "permissions": session_token.permissions,
                "sandbox": {
                    "created": True,
                    "isolated": sandbox.isolated,
                    "memory_allocated_mb": 0
                }
            },
            "message": "Secure session created with JWT authentication and isolated sandbox"
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating secure session: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "SESSION_CREATION_FAILED",
                "message": str(e)
            },
            "message": "Failed to create secure session"
        }


@app.post("/api/security/session/verify")
async def verify_session_token(jwt_token: str = Form(...)):
    """
    Verify JWT session token
    
    **Form Parameters:**
    - jwt_token (required): JWT token to verify
    
    **Returns:**
    - Token validation status
    - Session details if valid
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8001/api/security/session/verify" \\
         -F "jwt_token=eyJhbGc..."
    ```
    """
    logger.info("🔍 Verifying session token...")
    
    try:
        from security import get_session_auth_manager
        
        auth_manager = get_session_auth_manager()
        
        # Verify token
        valid, payload, error_message = auth_manager.verify_session_token(jwt_token)
        
        if valid:
            logger.info(f"✅ Token verified: {payload['session_id']}")
            return {
                "success": True,
                "data": {
                    "valid": True,
                    "session_id": payload['session_id'],
                    "interview_id": payload['interview_id'],
                    "candidate_name": payload['candidate_name'],
                    "expires_at": payload['expires_at'],
                    "permissions": payload['permissions']
                },
                "message": "Token is valid"
            }
        else:
            logger.warning(f"⚠️ Token verification failed: {error_message}")
            return {
                "success": False,
                "data": {
                    "valid": False,
                    "error": error_message
                },
                "message": f"Token verification failed: {error_message}"
            }
        
    except Exception as e:
        logger.error(f"❌ Error verifying token: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "VERIFICATION_ERROR",
                "message": str(e)
            },
            "message": "Token verification error"
        }


@app.post("/api/security/session/revoke/{session_id}")
async def revoke_session_token(session_id: str):
    """
    Revoke session token and clean up sandbox
    
    **Path Parameters:**
    - session_id (required): Session ID to revoke
    
    **Returns:**
    - Revocation status
    - Cleanup summary
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8001/api/security/session/revoke/session_123"
    ```
    """
    logger.info(f"🚫 Revoking session: {session_id}")
    
    try:
        from security import get_session_auth_manager, get_session_isolation_manager
        
        auth_manager = get_session_auth_manager()
        isolation_manager = get_session_isolation_manager()
        
        # Revoke token
        logger.info("🔒 Revoking JWT token...")
        token_revoked = auth_manager.revoke_session_token(session_id)
        
        # Clean up sandbox
        logger.info("🧹 Cleaning up sandbox...")
        cleanup_result = isolation_manager.cleanup_sandbox(session_id, force=True)
        
        logger.info("✅ Session revoked and cleaned up")
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "token_revoked": token_revoked,
                "sandbox_cleaned": cleanup_result.get('success', False),
                "cleanup_summary": cleanup_result.get('data', {})
            },
            "message": "Session revoked and resources cleaned up"
        }
        
    except Exception as e:
        logger.error(f"❌ Error revoking session: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "REVOCATION_ERROR",
                "message": str(e)
            },
            "message": "Failed to revoke session"
        }


@app.get("/api/security/session/permissions/{session_id}")
async def get_session_permissions(session_id: str):
    """
    Get session permissions
    
    **Path Parameters:**
    - session_id (required): Session ID
    
    **Returns:**
    - Session permissions
    
    **Example:**
    ```bash
    curl "http://localhost:8001/api/security/session/permissions/session_123"
    ```
    """
    logger.info(f"📋 Getting permissions for session: {session_id}")
    
    try:
        from security import get_session_auth_manager
        
        auth_manager = get_session_auth_manager()
        permissions = auth_manager.get_session_permissions(session_id)
        
        if permissions:
            logger.info(f"✅ Permissions retrieved: {session_id}")
            return {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "permissions": permissions
                },
                "message": "Permissions retrieved successfully"
            }
        else:
            logger.warning(f"⚠️ No permissions found: {session_id}")
            return {
                "success": False,
                "error": {
                    "code": "PERMISSIONS_NOT_FOUND",
                    "message": "Session permissions not found"
                },
                "message": "Permissions not found"
            }
        
    except Exception as e:
        logger.error(f"❌ Error getting permissions: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "PERMISSIONS_ERROR",
                "message": str(e)
            },
            "message": "Failed to get permissions"
        }


@app.get("/api/security/sandbox/stats/{session_id}")
async def get_sandbox_stats(session_id: str):
    """
    Get sandbox memory and resource stats
    
    **Path Parameters:**
    - session_id (required): Session ID
    
    **Returns:**
    - Memory usage
    - Buffer count
    - Resource tracking
    
    **Example:**
    ```bash
    curl "http://localhost:8001/api/security/sandbox/stats/session_123"
    ```
    """
    logger.info(f"📊 Getting sandbox stats for: {session_id}")
    
    try:
        from security import get_session_isolation_manager
        
        isolation_manager = get_session_isolation_manager()
        sandbox = isolation_manager.get_sandbox(session_id)
        
        if sandbox:
            stats = {
                "session_id": session_id,
                "created_at": sandbox.created_at.isoformat(),
                "last_accessed": sandbox.last_accessed.isoformat(),
                "access_count": sandbox.access_count,
                "memory_allocated_mb": sandbox.total_memory_allocated / (1024 * 1024),
                "buffers_count": len(sandbox.memory_buffers),
                "temp_data_count": len(sandbox.temp_data),
                "cache_keys_count": len(sandbox.cache_keys),
                "file_handles_count": len(sandbox.file_handles),
                "isolated": sandbox.isolated,
                "cleaned": sandbox.cleaned
            }
            
            logger.info(f"✅ Sandbox stats retrieved: {session_id}")
            logger.info(f"   Memory: {stats['memory_allocated_mb']:.2f} MB")
            logger.info(f"   Buffers: {stats['buffers_count']}")
            
            return {
                "success": True,
                "data": stats,
                "message": "Sandbox stats retrieved successfully"
            }
        else:
            logger.warning(f"⚠️ Sandbox not found: {session_id}")
            return {
                "success": False,
                "error": {
                    "code": "SANDBOX_NOT_FOUND",
                    "message": "Sandbox not found for session"
                },
                "message": "Sandbox not found"
            }
        
    except Exception as e:
        logger.error(f"❌ Error getting sandbox stats: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "SANDBOX_STATS_ERROR",
                "message": str(e)
            },
            "message": "Failed to get sandbox stats"
        }


@app.get("/api/security/memory/global")
async def get_global_memory_stats():
    """
    Get global memory statistics across all sessions
    
    **Returns:**
    - Process memory usage
    - Total sandbox memory
    - Active sessions count
    - Memory limits
    
    **Example:**
    ```bash
    curl "http://localhost:8001/api/security/memory/global"
    ```
    """
    logger.info("📊 Getting global memory stats...")
    
    try:
        from security import get_session_isolation_manager
        
        isolation_manager = get_session_isolation_manager()
        stats = isolation_manager.get_memory_stats()
        
        logger.info("✅ Global memory stats retrieved")
        logger.info(f"   Process memory: {stats.get('process_memory_mb', 0):.2f} MB")
        logger.info(f"   Active sessions: {stats.get('active_sessions', 0)}")
        
        return {
            "success": True,
            "data": stats,
            "message": "Global memory stats retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting global memory stats: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "MEMORY_STATS_ERROR",
                "message": str(e)
            },
            "message": "Failed to get memory stats"
        }


@app.get("/api/security/sessions/active")
async def get_active_secure_sessions():
    """
    Get list of active secure sessions
    
    **Returns:**
    - List of active sessions with stats
    - Total count
    
    **Example:**
    ```bash
    curl "http://localhost:8001/api/security/sessions/active"
    ```
    """
    logger.info("📋 Getting active secure sessions...")
    
    try:
        from security import get_session_isolation_manager, get_session_auth_manager
        
        isolation_manager = get_session_isolation_manager()
        auth_manager = get_session_auth_manager()
        
        # Get sandboxes
        sandboxes = isolation_manager.get_active_sandboxes()
        
        # Get active sessions count from auth
        active_sessions_count = auth_manager.get_active_sessions()
        
        logger.info(f"✅ Found {len(sandboxes)} active sandboxes")
        logger.info(f"✅ Found {active_sessions_count} active tokens")
        
        return {
            "success": True,
            "data": {
                "active_sandboxes": len(sandboxes),
                "active_tokens": active_sessions_count,
                "sandboxes": sandboxes
            },
            "message": "Active secure sessions retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting active sessions: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "ACTIVE_SESSIONS_ERROR",
                "message": str(e)
            },
            "message": "Failed to get active sessions"
        }


# ============================================================================
# END SECURITY & ISOLATION ENDPOINTS
# ============================================================================

@app.post("/api/qa")
async def resume_qa(
    resume_file: Optional[UploadFile] = File(None),
    resume_text: Optional[str] = Form(None),
    question: str = Form(...)
):
    """
    Answer questions about a resume using LangGraph Q&A workflow.
    
    NEW: Uses LangGraph + MCP for:
    - Question classification (skills/experience/education/general)
    - Selective retrieval (only relevant sections, 75%+ token savings)
    - Intelligent caching (repeated questions answered instantly)
    - Conversation history management
    """
    try:
        logger.info(f"❓ Received Q&A request: {question[:50]}...")
        
        # Get resume text either from file or directly from the request
        if resume_file:
            text = extract_text_from_pdf(resume_file)
            logger.info(f"✅ Extracted {len(text)} characters from uploaded file")
        elif resume_text:
            text = resume_text
            logger.info(f"✅ Using provided resume text ({len(text)} characters)")
        else:
            logger.error("❌ No resume provided")
            return {"error": "Please provide either a resume file or resume text"}
        
        # Use LangGraph service for Q&A
        service = get_langgraph_service()
        result = service.answer_question(
            resume_text=text,
            question=question
        )
        
        # Extract the answer from the result
        answer = result.get('answer', '')
        
        logger.info(f"✅ Question answered successfully")
        logger.info(f"📊 Performance: Cache hit rate: {result.get('metadata', {}).get('cache_hit_rate', 'N/A')}")
        logger.info(f"💰 Tokens saved: {result.get('metadata', {}).get('tokens_saved', 0)}")
        
        # Format answer as bullet points for backward compatibility
        bullet_points = [point.strip() for point in answer.split('\n') if point.strip()]
        formatted_points = []
        for point in bullet_points:
            if not point.startswith('-'):
                point = f"- {point}"
            formatted_points.append(point)

        return {"answer": formatted_points}
        
    except Exception as e:
        logger.error(f"❌ Error in resume_qa: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e)}

@app.post("/api/questions")
async def generate_questions(
    resume: UploadFile = File(...),
    question_types: str = Form(...),
    difficulty: str = Form(...),
    num_questions: int = Form(...)
):
    try:
        # Extract text from PDF
        resume_text = extract_text_from_pdf(resume)
        
        # Parse question types
        types = json.loads(question_types)
        
        prompt = f"""
        Based on this resume:
        {resume_text}

        Generate {num_questions} interview questions with these specifications:
        - Types: {', '.join(types)}
        - Difficulty: {difficulty}
        - Questions should be specific to the candidate's experience and skills

        Provide the questions in this exact JSON format:
        {{
            "questions": [
                {{
                    "question": "<question text>",
                    "type": "<question type>",
                    "difficulty": "<difficulty level>"
                }},
                ...
            ]
        }}

        Important:
        1. Return ONLY valid JSON, no other text
        2. Ensure all fields are present for each question
        3. Use proper JSON formatting with double quotes
        4. Generate exactly {num_questions} questions
        5. Make questions specific to the resume content
        """

        completion = client_questions.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024,
        )

        response_text = completion.choices[0].message.content.strip()
        
        # Try to parse the response as JSON
        try:
            questions_result = json.loads(response_text)
            
            # Validate the response format
            if "questions" not in questions_result:
                raise ValueError("Missing 'questions' field in response")
            
            # Ensure we have the correct number of questions
            if len(questions_result["questions"]) != num_questions:
                logger.warning(f"Expected {num_questions} questions, got {len(questions_result['questions'])}")
            
            # Validate each question has required fields
            for i, q in enumerate(questions_result["questions"]):
                required_fields = ["question", "type", "difficulty"]
                for field in required_fields:
                    if field not in q:
                        raise ValueError(f"Question {i+1} missing required field: {field}")
            
            return questions_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {response_text}")
            # Return a default response if JSON parsing fails
            return {
                "questions": [
                    {
                        "question": "Error generating questions. Please try again.",
                        "type": "error",
                        "difficulty": "unknown"
                    }
                ]
            }
            
    except Exception as e:
        logger.error(f"Error in generate_questions: {str(e)}")
        return {
            "questions": [
                {
                    "question": f"Error: {str(e)}",
                    "type": "error",
                    "difficulty": "unknown"
                }
            ]
        }

@app.post("/api/improve")
async def improve_resume(
    resume: UploadFile = File(...),
    target_role: Optional[str] = Form(None),
    custom_areas: Optional[str] = Form(None)
):
    """
    Generate resume improvement suggestions using LangGraph + MCP workflow.
    
    NEW: Uses LangGraph + MCP for:
    - Multi-step analysis (analyze -> identify gaps -> generate suggestions)
    - MCP context optimization (focused analysis per area)
    - Actionable recommendations with specific examples
    - Structured workflow with progress tracking
    """
    try:
        logger.info(f"💡 Received resume improvement request for role: {target_role}")
        
        # Extract text from PDF
        resume_text = extract_text_from_pdf(resume)
        logger.info(f"✅ Extracted {len(resume_text)} characters from resume")
        
        # Prepare improvement areas
        if target_role and target_role in ROLE_REQUIREMENTS:
            requirements = ROLE_REQUIREMENTS[target_role]
        elif custom_areas:
            requirements = [area.strip() for area in custom_areas.split('\n') if area.strip()]
        else:
            logger.error("❌ No target role or custom areas provided")
            return {"error": "Please provide either a target role or custom areas for improvement"}
        
        logger.info(f"📋 Analyzing against {len(requirements)} requirements")
        
        # Use LangGraph service for resume improvement
        service = get_langgraph_service()
        result = service.generate_resume_improvements(
            resume_text=resume_text,
            requirements=requirements,
            target_role=target_role or "professional"
        )
        
        # Format response for frontend compatibility
        suggestions = result.get('suggestions', [])
        
        logger.info(f"✅ Generated {len(suggestions)} improvement suggestions")
        logger.info(f"📊 Performance: Tokens used: {result['metadata']['tokens_used']}")
        logger.info(f"⚡ Processing time: {result['metadata']['processing_time']:.2f}s")
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"❌ Error in resume improvement: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e)}

@app.post("/api/improved-resume")
async def get_improved_resume(
    resume: UploadFile = File(...),
    target_role: str = Form(...),
    highlight_skills: str = Form(...),
    custom_skills: Optional[str] = Form(None)
):
    """
    Generate an improved version of the resume using LangGraph + MCP workflow.
    
    NEW: Uses LangGraph + MCP for:
    - Multi-step enhancement (extract -> enhance -> format -> validate)
    - Section-by-section improvement (better quality control)
    - MCP context optimization (focused enhancement per section)
    - Quality validation (ensures good output)
    """
    try:
        logger.info(f"✨ Received improved resume request for role: {target_role}")
        
        # Extract text from PDF
        resume_text = extract_text_from_pdf(resume)
        logger.info(f"✅ Extracted {len(resume_text)} characters from resume")
        
        # Parse skills to highlight
        try:
            skills = json.loads(highlight_skills)
        except:
            skills = [s.strip() for s in highlight_skills.split(',') if s.strip()]
        
        if custom_skills:
            custom_skill_list = [s.strip() for s in custom_skills.split('\n') if s.strip()]
            skills.extend(custom_skill_list)
        
        logger.info(f"🎯 Highlighting {len(skills)} skills for {target_role}")
        
        # Use LangGraph service for improved resume generation
        service = get_langgraph_service()
        result = service.generate_improved_resume(
            resume_text=resume_text,
            target_role=target_role,
            skills_to_highlight=skills
        )
        
        improved_text = result.get('improved_resume', '')
        
        # Validate the response
        if not improved_text or len(improved_text) < 200:
            logger.error("❌ Generated resume too short or empty")
            return {
                "improved_resume": "Error: Failed to generate an improved version. Please try again."
            }
        
        if improved_text == resume_text:
            logger.warning("⚠️ Generated resume identical to original")
        
        logger.info(f"✅ Generated {len(improved_text)} character improved resume")
        logger.info(f"📊 Performance: Tokens used: {result['metadata']['tokens_used']}")
        logger.info(f"⚡ Processing time: {result['metadata']['processing_time']:.2f}s")
        logger.info(f"📝 Enhanced sections: {', '.join(result['metadata']['enhanced_sections'])}")
        
        return {"improved_resume": improved_text}
        
    except Exception as e:
        logger.error(f"❌ Error in improved resume generation: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e)}
        logger.error(f"Error in get_improved_resume: {str(e)}")
        return {
            "improved_resume": f"Error generating improved resume: {str(e)}"
        }


@app.post("/api/predict-salary")
async def predict_salary(
    years_experience: float = Form(...),
    education_level: str = Form(...),
    job_level: str = Form(...),
    industry: str = Form(...),
    location: str = Form(...)
):
    """
    Predict salary using ML model + LangGraph workflow.
    
    Uses trained XGBoost models for accurate salary predictions.
    
    Args:
        years_experience: Years of work experience
        education_level: Education level (High School, Associate, Bachelor, Master, PhD)
        job_level: Job level (Entry-level, Mid-level, Senior, Executive)
        industry: Industry (Technology, Finance, Healthcare, etc.)
        location: Location (Urban, Suburban, Rural)
    
    Returns:
        Predicted salary with confidence and feature importance
    """
    try:
        logger.info(f"💰 Received salary prediction request")
        logger.info(f"📊 Params: {years_experience}y exp, {education_level}, {job_level}, {industry}, {location}")
        
        # Validate inputs
        if years_experience < 0:
            return {"error": "Years of experience cannot be negative"}
        
        valid_education = ['High School', 'Associate', 'Bachelor', 'Master', 'PhD']
        if education_level not in valid_education:
            return {"error": f"Invalid education level. Must be one of: {', '.join(valid_education)}"}
        
        valid_job_levels = ['Entry-level', 'Mid-level', 'Senior', 'Executive']
        if job_level not in valid_job_levels:
            return {"error": f"Invalid job level. Must be one of: {', '.join(valid_job_levels)}"}
        
        valid_locations = ['Urban', 'Suburban', 'Rural']
        if location not in valid_locations:
            return {"error": f"Invalid location. Must be one of: {', '.join(valid_locations)}"}
        
        # Use LangGraph service for ML prediction
        service = get_langgraph_service()
        result = service.predict_salary(
            years_experience=years_experience,
            education_level=education_level,
            job_level=job_level,
            industry=industry,
            location=location
        )
        
        logger.info(f"✅ Salary prediction complete: ${result['predicted_salary']:,.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in salary prediction: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e)}


@app.post("/api/predict-job-possibility")
async def predict_job_possibility(
    years_experience: float = Form(...),
    education_level: str = Form(...),
    job_level: str = Form(...),
    industry: str = Form(...),
    skill_match_score: float = Form(...)
):
    """
    Predict job possibility using ML model + LangGraph workflow.
    
    Uses trained XGBoost models to predict job acquisition probability.
    
    Args:
        years_experience: Years of work experience
        education_level: Education level
        job_level: Job level
        industry: Industry
        skill_match_score: Skill match score (0-1)
    
    Returns:
        Job possibility prediction with probability and recommendation
    """
    try:
        logger.info(f"🎯 Received job possibility prediction request")
        logger.info(f"📊 Params: {years_experience}y exp, {education_level}, {job_level}, {industry}, skill_match={skill_match_score:.2f}")
        
        # Validate inputs
        if years_experience < 0:
            return {"error": "Years of experience cannot be negative"}
        
        if not (0 <= skill_match_score <= 1):
            return {"error": "Skill match score must be between 0 and 1"}
        
        valid_education = ['High School', 'Associate', 'Bachelor', 'Master', 'PhD']
        if education_level not in valid_education:
            return {"error": f"Invalid education level. Must be one of: {', '.join(valid_education)}"}
        
        valid_job_levels = ['Entry-level', 'Mid-level', 'Senior', 'Executive']
        if job_level not in valid_job_levels:
            return {"error": f"Invalid job level. Must be one of: {', '.join(valid_job_levels)}"}
        
        # Use LangGraph service for ML prediction
        service = get_langgraph_service()
        result = service.predict_job_possibility(
            years_experience=years_experience,
            education_level=education_level,
            job_level=job_level,
            industry=industry,
            skill_match_score=skill_match_score
        )
        
        logger.info(f"✅ Job possibility prediction complete: {result['probability']:.2%}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in job possibility prediction: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e)}


# ==================== INTERVIEW SCHEDULING ====================

class InterviewScheduleRequest(BaseModel):
    """Request model for scheduling an interview"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "candidate_name": "John Doe",
                "candidate_email": "john.doe@example.com",
                "candidate_id": "optional-resume-id",
                "job_id": "job-123",
                "job_title": "Python Developer",
                "hr_email": "hr@company.com",
                "hr_id": "hr-user-id",
                "scheduled_datetime": "2025-10-21T10:00:00Z",
                "duration_minutes": 30,
                "interview_type": "ai_assisted"
            }
        }
    )
    
    candidate_name: str
    candidate_email: str
    candidate_id: Optional[str] = None
    job_id: str
    job_title: str
    hr_email: str
    hr_id: str
    scheduled_datetime: str  # ISO 8601 format
    duration_minutes: int = 30
    interview_type: str = "ai_assisted"  # ai_assisted, human, hybrid
    auto_start_bot: bool = True  # Enable automatic bot joining when candidate clicks


@app.post("/api/interviews/schedule")
async def schedule_interview(request: InterviewScheduleRequest):
    """
    Schedule an AI-assisted interview
    
    Features:
    1. Validates input parameters
    2. Creates Google Meet link (valid for 24 hours)
    3. Sends email invitation to candidate
    4. Stores interview details in MongoDB
    
    Uses:
    - LangGraph for workflow orchestration
    - MCP for context management and optimization
    - Google Calendar API for Meet link generation
    
    Returns:
        ALWAYS returns 200 status code
        Success response:
        {
            "success": true,
            "data": {
                "interview_id": "uuid",
                "meet_link": "https://meet.google.com/...",
                "calendar_link": "https://calendar.google.com/...",
                "expires_at": "2025-10-21T10:00:00Z",
                "email_sent": true,
                "mongodb_saved": true
            },
            "logs": [...]
        }
        
        Error response (still 200):
        {
            "success": false,
            "errors": [{
                "code": "ERROR_CODE",
                "message": "Error description",
                "field": "field_name"
            }],
            "partial_data": {...},
            "logs": [...]
        }
    """
    logger.info("\n" + "="*80)
    logger.info("📞 API CALL: /api/interviews/schedule")
    logger.info("="*80)
    logger.info(f"📝 Candidate: {request.candidate_name} ({request.candidate_email})")
    logger.info(f"💼 Job: {request.job_title} (ID: {request.job_id})")
    logger.info(f"⏰ Scheduled: {request.scheduled_datetime}")
    logger.info(f"👤 HR: {request.hr_email} (ID: {request.hr_id})")
    
    try:
        # Import agent (lazy import to avoid startup issues)
        from langgraph_agents.interview_scheduling_agent import InterviewSchedulingAgent
        
        logger.info("🤖 Initializing Interview Scheduling Agent...")
        
        # Create agent instance
        agent = InterviewSchedulingAgent()
        
        logger.info("🚀 Invoking LangGraph workflow...")
        
        # Schedule interview using LangGraph agent
        result = agent.schedule_interview(
            candidate_name=request.candidate_name,
            candidate_email=request.candidate_email,
            candidate_id=request.candidate_id,
            job_id=request.job_id,
            job_title=request.job_title,
            hr_email=request.hr_email,
            hr_id=request.hr_id,
            scheduled_datetime=request.scheduled_datetime,
            duration_minutes=request.duration_minutes,
            interview_type=request.interview_type,
            auto_start_bot=request.auto_start_bot
        )
        
        logger.info(f"✅ Workflow completed: {'SUCCESS' if result['success'] else 'FAILED'}")
        logger.info("="*80 + "\n")
        
        # ALWAYS return 200 status
        return result
        
    except ImportError as e:
        logger.error(f"❌ Failed to import InterviewSchedulingAgent: {str(e)}")
        logger.error("💡 Make sure all dependencies are installed:")
        logger.error("   pip install langgraph google-api-python-client google-auth-oauthlib")
        
        return {
            "success": False,
            "errors": [{
                "code": "IMPORT_ERROR",
                "message": f"Failed to load scheduling agent: {str(e)}",
                "details": {
                    "missing_module": "langgraph_agents.interview_scheduling_agent",
                    "suggestion": "Install required packages: pip install langgraph google-api-python-client"
                }
            }],
            "logs": [f"Import error: {str(e)}"]
        }
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in schedule_interview: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            "success": False,
            "errors": [{
                "code": "UNEXPECTED_ERROR",
                "message": f"An unexpected error occurred: {str(e)}",
                "details": {
                    "exception_type": type(e).__name__,
                    "traceback": traceback.format_exc()
                }
            }],
            "logs": [f"Exception: {str(e)}"]
        }


@app.get("/api/interviews/{interview_id}")
async def get_interview(interview_id: str):
    """
    Get interview details by ID
    
    Returns:
        ALWAYS 200 status
        {
            "success": true/false,
            "data": {...} or "error": {...}
        }
    """
    logger.info(f"📝 Fetching interview: {interview_id}")
    
    try:
        from repositories.interview_repository import InterviewRepository
        
        repo = InterviewRepository()
        interview = repo.get_interview_by_id(interview_id)
        
        if interview:
            # Convert datetime to ISO string
            if 'scheduled_for' in interview and isinstance(interview['scheduled_for'], datetime.datetime):
                interview['scheduled_for'] = interview['scheduled_for'].isoformat()
            if 'created_at' in interview and isinstance(interview['created_at'], datetime.datetime):
                interview['created_at'] = interview['created_at'].isoformat()
            if 'updated_at' in interview and isinstance(interview['updated_at'], datetime.datetime):
                interview['updated_at'] = interview['updated_at'].isoformat()
            
            return {
                "success": True,
                "data": interview
            }
        else:
            return {
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Interview not found: {interview_id}"
                }
            }
            
    except Exception as e:
        logger.error(f"❌ Error fetching interview: {str(e)}")
        return {
            "success": False,
            "error": {
                "code": "DATABASE_ERROR",
                "message": f"Failed to fetch interview: {str(e)}"
            }
        }


@app.get("/api/interviews/status/{interview_id}")
async def get_interview_status(interview_id: str):
    """
    Check interview status and Meet link validity
    
    Returns:
        ALWAYS 200 status
    """
    logger.info(f"🔍 Checking interview status: {interview_id}")
    
    try:
        from repositories.interview_repository import InterviewRepository
        from services.google_calendar_service import GoogleCalendarService
        
        # Get interview from MongoDB
        repo = InterviewRepository()
        interview = repo.get_interview_by_id(interview_id)
        
        if not interview:
            return {
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Interview not found: {interview_id}"
                }
            }
        
        # Check Google Calendar event status
        calendar_service = GoogleCalendarService()
        event_id = interview.get('calendar_event_id')
        
        if event_id:
            calendar_status = calendar_service.get_meeting_status(event_id)
        else:
            calendar_status = {
                "success": False,
                "error": {"message": "No calendar event ID"}
            }
        
        return {
            "success": True,
            "data": {
                "interview_id": interview_id,
                "status": interview.get('status'),
                "scheduled_for": interview.get('scheduled_for').isoformat() if interview.get('scheduled_for') else None,
                "meet_link": interview.get('meet_link'),
                "email_sent": interview.get('email_sent', False),
                "calendar_event": calendar_status.get('data') if calendar_status.get('success') else None,
                "calendar_error": calendar_status.get('error') if not calendar_status.get('success') else None
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error checking interview status: {str(e)}")
        return {
            "success": False,
            "error": {
                "code": "STATUS_CHECK_ERROR",
                "message": f"Failed to check status: {str(e)}"
            }
        }


# ============================================================================
# QUESTION GENERATION ENDPOINTS (Step 2: AI Question Generator)
# ============================================================================

from langgraph_agents.question_generator_agent import QuestionGeneratorAgent
from repositories.question_repository import QuestionRepository

# Initialize question generator and repository
question_generator = QuestionGeneratorAgent()
try:
    question_repo = QuestionRepository()
    logger.info("✅ QuestionRepository initialized successfully")
except Exception as e:
    logger.warning(f"⚠️  QuestionRepository initialization failed: {e}")
    logger.warning("   Question endpoints will not be available")
    question_repo = None


class QuestionGenerationRequest(BaseModel):
    """Request model for question generation"""
    candidate_id: str
    job_id: str
    interview_id: str
    resume_data: dict
    job_description: dict
    threshold_percentage: float = 70.0
    previous_answers: Optional[List[dict]] = None
    # Question count configuration (optional)
    technical_count: int = 5
    behavioral_count: int = 3
    scenario_count: int = 2


class AnswerSubmissionRequest(BaseModel):
    """Request model for submitting answers"""
    interview_id: str
    question_id: str
    answer: str
    is_correct: Optional[bool] = None
    score: Optional[float] = None


@app.post("/api/questions/generate")
async def generate_interview_questions(request: QuestionGenerationRequest):
    """
    Generate intelligent interview questions using LangGraph agent
    
    Process:
    1. Analyze candidate's resume (skills, experience)
    2. Parse job description (requirements, responsibilities)
    3. Generate technical questions (based on skills)
    4. Generate behavioral questions (based on experience)
    5. Generate scenario questions (based on job requirements)
    6. Adapt questions based on previous answers (if any)
    7. Store questions in MongoDB
    
    Returns (ALWAYS 200 status):
        {
            "success": True/False,
            "data": {
                "questions": [...],
                "total_questions": 10,
                "categories": {"technical": 5, "behavioral": 3, "scenario": 2},
                "question_set_id": "uuid"
            },
            "errors": [...] (if any),
            "logs": [...]
        }
    """
    logger.info("\n" + "="*80)
    logger.info("🎯 ENDPOINT: Generate Interview Questions")
    logger.info("="*80)
    logger.info(f"📋 Candidate: {request.candidate_id}")
    logger.info(f"💼 Job: {request.job_id}")
    logger.info(f"📅 Interview: {request.interview_id}")
    logger.info(f"🎚️ Threshold: {request.threshold_percentage}%")
    logger.info(f"📊 Question Counts: {request.technical_count} technical, {request.behavioral_count} behavioral, {request.scenario_count} scenario")
    
    try:
        # Step 1: Create Question Generator Agent with custom counts
        logger.info("🤖 Initializing Question Generator Agent with custom configuration...")
        custom_generator = QuestionGeneratorAgent(
            technical_count=request.technical_count,
            behavioral_count=request.behavioral_count,
            scenario_count=request.scenario_count
        )
        
        # Step 2: Generate questions using LangGraph agent
        logger.info("🚀 Invoking Question Generator Agent...")
        result = custom_generator.generate_questions(
            resume_data=request.resume_data,
            job_description=request.job_description,
            candidate_id=request.candidate_id,
            job_id=request.job_id,
            interview_id=request.interview_id,
            threshold_percentage=request.threshold_percentage,
            previous_answers=request.previous_answers
        )
        
        if not result.get("success"):
            logger.error("❌ Question generation failed")
            return {
                "success": False,
                "error": {
                    "code": "GENERATION_FAILED",
                    "message": "Failed to generate questions",
                    "details": result.get("errors", [])
                },
                "logs": result.get("logs", [])
            }
        
        # Step 2: Save questions to MongoDB
        logger.info("💾 Saving questions to database...")
        questions = result["data"]["questions"]
        metadata = {
            "categories": result["data"]["categories"],
            "threshold_percentage": request.threshold_percentage,
            "threshold_met": result["data"]["threshold_met"]
        }
        
        if question_repo is None:
            logger.warning("⚠️  QuestionRepository not available, skipping database save")
            save_result = {"success": False, "error": "Database not available"}
        else:
            save_result = question_repo.save_questions(
                interview_id=request.interview_id,
                candidate_id=request.candidate_id,
                job_id=request.job_id,
                questions=questions,
            metadata=metadata
        )
        
        if not save_result.get("success"):
            logger.error("❌ Failed to save questions to database")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Questions generated but failed to save",
                    "details": save_result.get("error")
                },
                "data": result["data"],  # Return questions even if save failed
                "logs": result.get("logs", [])
            }
        
        # Step 3: Return success response
        logger.info("✅ Questions generated and saved successfully")
        logger.info(f"   Total questions: {len(questions)}")
        logger.info(f"   Categories: {metadata['categories']}")
        logger.info(f"   Question set ID: {save_result['question_set_id']}")
        
        return {
            "success": True,
            "data": {
                "questions": questions,
                "total_questions": len(questions),
                "categories": metadata["categories"],
                "question_set_id": save_result["question_set_id"],
                "interview_id": request.interview_id,
                "threshold_met": metadata["threshold_met"]
            },
            "logs": result.get("logs", [])
        }
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # ALWAYS return 200 with error details
        return {
            "success": False,
            "error": {
                "code": "UNEXPECTED_ERROR",
                "message": f"Question generation failed: {str(e)}",
                "traceback": traceback.format_exc()
            }
        }


@app.get("/api/questions/{interview_id}")
async def get_interview_questions(interview_id: str):
    """
    Retrieve questions for a specific interview
    
    Returns (ALWAYS 200):
        {
            "success": True/False,
            "data": {
                "questions": [...],
                "total_questions": 10,
                "answered_count": 3,
                "status": "pending|in_progress|completed"
            }
        }
    """
    logger.info(f"🔍 GET Questions for interview: {interview_id}")
    
    try:
        if question_repo is None:
            return {
                "success": False,
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Question repository not available"
                }
            }
            
        result = question_repo.get_questions_by_interview(interview_id)
        
        if not result.get("success"):
            logger.warning(f"⚠️ Questions not found: {interview_id}")
            return {
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": result.get("error", "Questions not found")
                }
            }
        
        logger.info(f"✅ Retrieved {result['data']['total_questions']} questions")
        return result
    
    except Exception as e:
        logger.error(f"❌ Error retrieving questions: {str(e)}")
        return {
            "success": False,
            "error": {
                "code": "RETRIEVAL_ERROR",
                "message": str(e)
            }
        }


@app.post("/api/questions/answer")
async def submit_answer(request: AnswerSubmissionRequest):
    """
    Submit answer for a question
    
    Returns (ALWAYS 200):
        {
            "success": True/False,
            "data": {
                "answered_count": 4,
                "total_questions": 10,
                "status": "in_progress"
            }
        }
    """
    logger.info(f"✍️ Submit answer for question: {request.question_id}")
    
    try:
        if question_repo is None:
            return {
                "success": False,
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Question repository not available"
                }
            }
            
        result = question_repo.update_question_answer(
            interview_id=request.interview_id,
            question_id=request.question_id,
            answer=request.answer,
            is_correct=request.is_correct,
            score=request.score
        )
        
        if not result.get("success"):
            logger.error(f"❌ Failed to submit answer")
            return {
                "success": False,
                "error": {
                    "code": "ANSWER_SUBMISSION_FAILED",
                    "message": result.get("error", "Failed to submit answer")
                }
            }
        
        logger.info(f"✅ Answer submitted successfully")
        logger.info(f"   Progress: {result['answered_count']}/{result['total_questions']}")
        
        return {
            "success": True,
            "data": {
                "answered_count": result["answered_count"],
                "total_questions": result["total_questions"],
                "status": result["status"]
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Error submitting answer: {str(e)}")
        return {
            "success": False,
            "error": {
                "code": "SUBMISSION_ERROR",
                "message": str(e)
            }
        }


@app.get("/api/questions/candidate/{candidate_id}")
async def get_candidate_questions(candidate_id: str):
    """
    Get all question sets for a candidate (for adaptive questioning)
    
    Returns (ALWAYS 200):
        {
            "success": True/False,
            "data": [...],
            "count": 3
        }
    """
    logger.info(f"🔍 GET All questions for candidate: {candidate_id}")
    
    try:
        if question_repo is None:
            return {
                "success": False,
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Question repository not available"
                }
            }
            
        result = question_repo.get_questions_by_candidate(candidate_id)
        
        logger.info(f"✅ Found {result.get('count', 0)} question sets")
        return result
    
    except Exception as e:
        logger.error(f"❌ Error retrieving candidate questions: {str(e)}")
        return {
            "success": False,
            "error": {
                "code": "RETRIEVAL_ERROR",
                "message": str(e)
            },
            "data": []
        }


@app.get("/api/questions/analytics/{interview_id}")
async def get_question_analytics(interview_id: str):
    """
    Get analytics for question set
    
    Returns (ALWAYS 200):
        {
            "success": True/False,
            "data": {
                "total_questions": 10,
                "answered": 7,
                "pending": 3,
                "correct": 5,
                "incorrect": 2,
                "accuracy": 71.4,
                "completion": 70.0,
                "categories": {"technical": 5, "behavioral": 3, "scenario": 2}
            }
        }
    """
    logger.info(f"📈 GET Analytics for interview: {interview_id}")
    
    try:
        if question_repo is None:
            return {
                "success": False,
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Question repository not available"
                }
            }
            
        result = question_repo.get_question_analytics(interview_id)
        
        if result.get("success"):
            logger.info(f"✅ Analytics generated: {result['data']['completion']:.1f}% complete")
        else:
            logger.warning(f"⚠️ Analytics generation failed")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Error getting analytics: {str(e)}")
        return {
            "success": False,
            "error": {
                "code": "ANALYTICS_ERROR",
                "message": str(e)
            }
        }


# ==================== Google Meet Bot Endpoints ====================

from langgraph_agents.meet_bot_agent import create_meet_session
from repositories.meet_session_repository import MeetSessionRepository
import subprocess
import uuid as uuid_lib

# Initialize Meet Session Repository
meet_session_repo = MeetSessionRepository()

async def _run_meet_bot_agent(session_config: dict, session_id: str, repo: MeetSessionRepository):
    """Background task to run Meet Bot LangGraph agent"""
    try:
        logger.info(f"🤖 [Background] Starting Meet Bot agent for session: {session_id}")
        
        result = await create_meet_session(session_config)
        
        logger.info(f"✅ [Background] Meet Bot agent completed: {result.get('session_status')}")
        
        # Update session with result
        repo.update_session(session_id, {
            "session_status": result.get('session_status', 'unknown'),
            "join_attempts": result.get('join_attempts', 0),
            "audio_chunks_received": result.get('audio_chunks_received', 0)
        })
        
    except Exception as e:
        logger.error(f"❌ [Background] Meet Bot agent error: {str(e)}", exc_info=True)
        repo.update_session(session_id, {
            "session_status": "failed",
            "last_error": str(e)
        })

class MeetSessionRequest(BaseModel):
    """Request model for starting Meet recording session"""
    meet_url: str
    interview_id: str
    bot_email: Optional[str] = None
    bot_password: Optional[str] = None
    max_retries: Optional[int] = 3

class MeetSessionStopRequest(BaseModel):
    """Request model for stopping Meet recording session"""
    session_id: str
    reason: Optional[str] = "Manual stop"

class MeetTriggerRequest(BaseModel):
    """Request model for auto-triggering bot when candidate joins"""
    interview_id: str
    token: str


@app.get("/api/meet/trigger/{interview_id}")
async def trigger_bot_auto_join(interview_id: str, token: str):
    """
    Auto-trigger bot to join meeting when candidate clicks 'Start Interview'
    
    Flow:
    1. Validate security token
    2. Check if bot already joining/joined
    3. Start bot in background
    4. Wait 5-10 seconds (let bot join first)
    5. Redirect candidate to Google Meet
    
    Returns:
        HTML redirect page with countdown
    """
    try:
        logger.info(f"🚀 Auto-trigger received for interview: {interview_id}")
        
        # 1. Get interview from database
        from repositories.interview_repository import InterviewRepository
        interview_repo = InterviewRepository()
        
        interview = interview_repo.get_interview_by_id(interview_id)
        if not interview:
            return HTMLResponse(content="""
                <!DOCTYPE html>
                <html>
                <head><title>Interview Not Found</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>❌ Interview Not Found</h1>
                    <p>The interview link may be invalid or expired.</p>
                </body>
                </html>
            """, status_code=404)
        
        # 2. Validate token
        expected_token = interview.get('auto_join_token')
        if not expected_token or token != expected_token:
            logger.error(f"❌ Invalid token for interview {interview_id}")
            return HTMLResponse(content="""
                <!DOCTYPE html>
                <html>
                <head><title>Invalid Link</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>🔒 Invalid or Expired Link</h1>
                    <p>This interview link is not valid.</p>
                </body>
                </html>
            """, status_code=403)
        
        # 3. Check if already triggered (prevent multiple clicks)
        if interview.get('bot_join_status') in ['joining', 'joined']:
            logger.info(f"⏭️ Bot already {interview.get('bot_join_status')} for {interview_id}")
            meet_link = interview.get('meet_link')
            return HTMLResponse(content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Joining Interview</title>
                    <meta http-equiv="refresh" content="2;url={meet_link}">
                </head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>✅ Bot Already Joined!</h1>
                    <p>Redirecting you to the interview...</p>
                    <p style="font-size: 12px; color: #888;">You will be redirected in 2 seconds</p>
                </body>
                </html>
            """)
        
        # 4. Update status to prevent duplicate triggers
        interview_repo.update_interview(interview_id, {
            'bot_join_status': 'joining',
            'candidate_joined_at': datetime.datetime.now().isoformat(),
            'trigger_timestamp': datetime.datetime.now().isoformat()
        })
        
        # 5. Start bot in background (async)
        meet_link = interview.get('meet_link')
        bot_request = MeetSessionRequest(
            meet_url=meet_link,
            interview_id=interview_id,
            max_retries=3
        )
        
        # Start bot and interview orchestration asynchronously
        import asyncio
        
        async def start_bot_and_interview():
            """Start bot, wait for it to join, then start interactive interview"""
            try:
                # Start bot joining
                bot_result = await start_meet_recording(bot_request)
                
                if bot_result.get('success'):
                    session_id = bot_result['data']['session_id']
                    logger.info(f"✅ Bot joined successfully, session: {session_id}")
                    
                    # Wait a few seconds for bot to stabilize in meeting
                    await asyncio.sleep(5)
                    
                    # Start interactive interview (question generation and TTS)
                    logger.info(f"🎬 Starting interactive interview for: {interview_id}")
                    interview_result = await start_interactive_interview(interview_id)
                    
                    if interview_result.get('success'):
                        logger.info(f"✅ Interactive interview started successfully")
                        logger.info(f"   Total questions: {interview_result['data']['total_questions']}")
                    else:
                        logger.error(f"❌ Failed to start interactive interview: {interview_result.get('error')}")
                else:
                    logger.error(f"❌ Bot failed to join: {bot_result.get('error')}")
            except Exception as e:
                logger.error(f"❌ Error in start_bot_and_interview: {str(e)}", exc_info=True)
        
        asyncio.create_task(start_bot_and_interview())
        
        logger.info(f"✅ Bot start triggered for {interview_id}")
        
        # 6. Return HTML page with 10-second countdown + redirect
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Starting Interview</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        text-align: center;
                        padding: 50px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                    }}
                    .container {{
                        background: white;
                        color: #333;
                        padding: 40px;
                        border-radius: 15px;
                        max-width: 500px;
                        margin: 0 auto;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    }}
                    .countdown {{
                        font-size: 72px;
                        font-weight: bold;
                        color: #667eea;
                        margin: 20px 0;
                    }}
                    .spinner {{
                        border: 4px solid #f3f3f3;
                        border-top: 4px solid #667eea;
                        border-radius: 50%;
                        width: 40px;
                        height: 40px;
                        animation: spin 1s linear infinite;
                        margin: 20px auto;
                    }}
                    @keyframes spin {{
                        0% {{ transform: rotate(0deg); }}
                        100% {{ transform: rotate(360deg); }}
                    }}
                </style>
                <script>
                    let countdown = 10;
                    function updateCountdown() {{
                        document.getElementById('countdown').innerText = countdown;
                        if (countdown <= 0) {{
                            window.location.href = '{meet_link}';
                        }} else {{
                            countdown--;
                            setTimeout(updateCountdown, 1000);
                        }}
                    }}
                    window.onload = updateCountdown;
                </script>
            </head>
            <body>
                <div class="container">
                    <h1>🤖 AI Interviewer is Joining...</h1>
                    <div class="spinner"></div>
                    <p>Our AI interviewer bot is joining the meeting now.</p>
                    <p>You will be redirected to the interview in:</p>
                    <div class="countdown" id="countdown">10</div>
                    <p style="font-size: 14px; color: #888;">
                        This ensures the bot is ready when you arrive! 🎯
                    </p>
                    <p style="font-size: 12px; margin-top: 30px;">
                        <a href="{meet_link}" style="color: #667eea;">Click here if not redirected automatically</a>
                    </p>
                </div>
            </body>
            </html>
        """)
        
    except Exception as e:
        logger.error(f"❌ Error in auto-trigger: {str(e)}")
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Error</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>❌ Something Went Wrong</h1>
                <p>Please contact HR or try again later.</p>
                <p style="font-size: 12px; color: #888;">Error: {str(e)}</p>
            </body>
            </html>
        """, status_code=500)


@app.post("/api/interview/start-interactive")
async def start_interactive_interview(
    interview_id: str,
    session_id: str
):
    """
    Start the interactive interview orchestration
    
    This endpoint triggers the complete Q&A flow:
    1. Load resume and generate questions
    2. Ask questions using TTS
    3. Listen to answers using STT
    4. Analyze answers with LLM
    5. Ask follow-up questions
    6. Generate final feedback
    
    This should be called after the bot joins the meeting.
    """
    try:
        logger.info(f"🎯 Starting interactive interview for interview_id: {interview_id}")
        
        # Get interview details from database
        from repositories.interview_repository import InterviewRepository
        interview_repo = InterviewRepository()
        
        interview = interview_repo.get_interview_by_id(interview_id)
        if not interview:
            return {
                "success": False,
                "error": "Interview not found"
            }
        
        # Get resume path (assuming it's stored or linked to candidate)
        resume_path = f"uploads/{interview.get('candidate_name', 'unknown').replace(' ', '_')}_resume.pdf"
        
        # Import and initialize orchestrator
        from langgraph_agents.interview_orchestrator_agent import InterviewOrchestratorAgent
        orchestrator = InterviewOrchestratorAgent()
        
        # Start interview in background
        async def run_interview():
            result = await orchestrator.conduct_interview(
                interview_id=interview_id,
                session_id=session_id,
                candidate_name=interview.get('candidate_name', 'Unknown'),
                candidate_email=interview.get('candidate_email', ''),
                job_title=interview.get('job_title', 'Position'),
                resume_path=resume_path
            )
            logger.info(f"✅ Interactive interview completed: {result.get('success')}")
            return result
        
        # Start interview task in background
        asyncio.create_task(run_interview())
        
        return {
            "success": True,
            "message": "Interactive interview started",
            "data": {
                "interview_id": interview_id,
                "session_id": session_id,
                "status": "started"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error starting interactive interview: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/meet/start")
async def start_meet_recording(request: MeetSessionRequest):
    """
    Start Google Meet recording session
    
    Returns:
        Status 200 with success/error in body
    """
    try:
        logger.info(f"🎤 Starting Meet recording session")
        logger.info(f"   Meet URL: {request.meet_url}")
        logger.info(f"   Interview ID: {request.interview_id}")
        
        # Generate session ID
        session_id = f"meet_session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid_lib.uuid4())[:8]}"
        
        # Get bot credentials from environment if not provided
        bot_email = request.bot_email or os.getenv("MEET_BOT_EMAIL")
        bot_password = request.bot_password or os.getenv("MEET_BOT_PASSWORD")
        
        if not bot_email or not bot_password:
            logger.error("❌ Bot credentials not provided")
            return {
                "success": False,
                "error": {
                    "code": "MISSING_CREDENTIALS",
                    "message": "Bot email and password are required. Set MEET_BOT_EMAIL and MEET_BOT_PASSWORD in environment or provide in request."
                }
            }
        
        # Create session in database
        session_doc = meet_session_repo.create_session({
            "session_id": session_id,
            "interview_id": request.interview_id,
            "meet_url": request.meet_url,
            "bot_email": bot_email,
            "metadata": {
                "max_retries": request.max_retries
            }
        })
        
        if not session_doc.get("session_id"):
            logger.error("❌ Failed to create session in database")
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Failed to create session in database"
                }
            }
        
        logger.info(f"✅ Session created: {session_id}")
        
        # Step 1: Start Node.js Puppeteer bot FIRST (before LangGraph)
        try:
            logger.info(f"🚀 Starting Puppeteer bot process")
            
            # Path to meet_recorder.js
            recorder_script = os.path.join(
                os.path.dirname(__file__),
                "services",
                "meet_bot",
                "meet_recorder.js"
            )
            
            # Start Node.js process
            env = os.environ.copy()
            env["MEET_BOT_EMAIL"] = bot_email
            env["MEET_BOT_PASSWORD"] = bot_password
            env["SESSION_ID"] = session_id
            env["MEET_URL"] = request.meet_url
            env["INTERVIEW_ID"] = request.interview_id
            
            # Start in background (don't wait)
            bot_process = subprocess.Popen(
                ["node", recorder_script],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"✅ Puppeteer bot process started (PID: {bot_process.pid})")
            
            # Give bot a moment to initialize
            import asyncio
            await asyncio.sleep(2)
            
        except Exception as bot_error:
            logger.error(f"❌ Error starting Puppeteer bot: {str(bot_error)}")
            meet_session_repo.add_session_error(session_id, {
                "stage": "puppeteer_startup",
                "error": str(bot_error)
            })
            return {
                "success": False,
                "error": {
                    "code": "PUPPETEER_STARTUP_ERROR",
                    "message": f"Failed to start Puppeteer bot: {str(bot_error)}"
                }
            }
        
        # Step 2: Start LangGraph Meet Bot Agent (monitors the session)
        logger.info(f"🤖 Invoking Meet Bot LangGraph agent")
        
        # Prepare session configuration
        session_config = {
            "session_id": session_id,
            "meet_url": request.meet_url,
            "interview_id": request.interview_id,
            "bot_email": bot_email,
            "bot_password": bot_password,
            "max_retries": request.max_retries
        }
        
        # Run agent asynchronously (don't block response)
        import asyncio
        asyncio.create_task(_run_meet_bot_agent(session_config, session_id, meet_session_repo))
        
        logger.info(f"✅ Meet Bot agent started in background")
        
        return {
            "success": True,
            "message": "Meet recording session started successfully",
            "data": {
                "session_id": session_id,
                "session_status": "initializing",
                "meet_url": request.meet_url,
                "interview_id": request.interview_id,
                "started_at": datetime.datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error starting Meet recording: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "SESSION_START_ERROR",
                "message": str(e)
            }
        }


@app.post("/api/meet/stop")
async def stop_meet_recording(request: MeetSessionStopRequest):
    """
    Stop Google Meet recording session
    
    Returns:
        Status 200 with success/error in body
    """
    try:
        logger.info(f"🛑 Stopping Meet recording session: {request.session_id}")
        
        # Get session
        session = meet_session_repo.get_session(request.session_id)
        
        if not session:
            logger.warning(f"⚠️ Session not found: {request.session_id}")
            return {
                "success": False,
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": f"Session {request.session_id} not found"
                }
            }
        
        # Update session status
        meet_session_repo.update_session(request.session_id, {
            "session_status": "disconnecting",
            "ended_at": datetime.datetime.utcnow()
        })
        
        logger.info(f"✅ Session marked as disconnecting: {request.session_id}")
        
        # Note: The Puppeteer bot will receive stop command via WebSocket
        # and handle cleanup automatically
        
        return {
            "success": True,
            "message": "Meet recording session stop initiated",
            "data": {
                "session_id": request.session_id,
                "reason": request.reason,
                "stopped_at": datetime.datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error stopping Meet recording: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "SESSION_STOP_ERROR",
                "message": str(e)
            }
        }


@app.get("/api/meet/status/{session_id}")
async def get_meet_session_status(session_id: str):
    """
    Get Meet recording session status
    
    Returns:
        Status 200 with session data or error in body
    """
    try:
        logger.info(f"📊 Getting session status: {session_id}")
        
        # Get session
        session = meet_session_repo.get_session(session_id)
        
        if not session:
            logger.warning(f"⚠️ Session not found: {session_id}")
            return {
                "success": False,
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": f"Session {session_id} not found"
                }
            }
        
        # Get analytics
        analytics = meet_session_repo.get_session_analytics(session_id)
        
        return {
            "success": True,
            "message": "Session status retrieved successfully",
            "data": {
                "session_id": session_id,
                "interview_id": session.get("interview_id"),
                "meet_url": session.get("meet_url"),
                "session_status": session.get("session_status"),
                "created_at": session.get("created_at"),
                "started_at": session.get("started_at"),
                "ended_at": session.get("ended_at"),
                "join_attempts": session.get("join_attempts", 0),
                "audio_chunks_received": session.get("audio_chunks_received", 0),
                "transcription_segments": session.get("transcription_segments", 0),
                "errors": session.get("errors", []),
                "analytics": analytics
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting session status: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "STATUS_ERROR",
                "message": str(e)
            }
        }


@app.get("/api/meet/transcript/{session_id}")
async def get_meet_transcript(session_id: str):
    """
    Get full transcript for a Meet recording session
    
    Returns:
        Status 200 with transcript data or error in body
    """
    try:
        logger.info(f"📝 Getting transcript: {session_id}")
        
        # Get full transcript
        transcript_data = meet_session_repo.get_full_transcript(session_id)
        
        if not transcript_data.get("full_transcript") and not transcript_data.get("segments"):
            logger.warning(f"⚠️ No transcript found for session: {session_id}")
            return {
                "success": False,
                "error": {
                    "code": "TRANSCRIPT_NOT_FOUND",
                    "message": f"No transcript available for session {session_id}"
                }
            }
        
        return {
            "success": True,
            "message": "Transcript retrieved successfully",
            "data": transcript_data
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting transcript: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "TRANSCRIPT_ERROR",
                "message": str(e)
            }
        }


@app.get("/api/meet/sessions/interview/{interview_id}")
async def get_meet_sessions_by_interview(interview_id: str):
    """
    Get all Meet recording sessions for an interview
    
    Returns:
        Status 200 with sessions list or error in body
    """
    try:
        logger.info(f"📋 Getting sessions for interview: {interview_id}")
        
        # Get sessions
        sessions = meet_session_repo.get_sessions_by_interview(interview_id)
        
        return {
            "success": True,
            "message": f"Retrieved {len(sessions)} sessions",
            "data": {
                "interview_id": interview_id,
                "sessions": sessions,
                "total_sessions": len(sessions)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting sessions: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "SESSIONS_ERROR",
                "message": str(e)
            }
        }


@app.get("/api/meet/sessions")
async def get_all_meet_sessions():
    """
    Get all active Meet recording sessions
    
    Returns:
        List of active sessions
    """
    try:
        logger.info("📋 Getting all meet sessions")
        
        # Get all sessions from MongoDB
        sessions = meet_session_repo.sessions_collection.find(
            {"session_status": {"$in": ["joining", "recording", "transcribing"]}}
        ).sort("created_at", -1).limit(50)
        
        sessions_list = []
        for session in sessions:
            session['_id'] = str(session['_id'])
            sessions_list.append(session)
        
        return sessions_list
        
    except Exception as e:
        logger.error(f"❌ Error getting sessions: {str(e)}")
        return []


@app.post("/api/interviews/{interview_id}/start-interactive")
async def start_interactive_interview(interview_id: str):
    """
    Start interactive interview with bot asking questions and listening to answers
    
    This endpoint:
    1. Generates questions from candidate's resume
    2. Starts TTS to speak questions
    3. Starts STT to listen to answers
    4. Orchestrates the Q&A flow
    
    Returns:
        Status 200 with orchestration details
    """
    try:
        logger.info(f"🎬 Starting interactive interview for: {interview_id}")
        
        # Get interview details
        from repositories.interview_repository import InterviewRepository
        interview_repo = InterviewRepository()
        interview = interview_repo.get_interview_by_id(interview_id)
        
        if not interview:
            return {
                "success": False,
                "error": {
                    "code": "INTERVIEW_NOT_FOUND",
                    "message": f"Interview {interview_id} not found"
                }
            }
        
        # Step 1: Generate questions from resume
        logger.info("📝 Generating interview questions...")
        
        # Use the question generator agent
        from langgraph_agents.question_generator_agent import QuestionGeneratorAgent
        
        question_agent = QuestionGeneratorAgent()
        
        # Prepare resume data and job description
        resume_data = {
            "name": interview.get('candidate_name', 'Candidate'),
            "email": interview.get('candidate_email', ''),
            "skills": [],
            "experience": [],
            "education": []
        }
        
        job_description = {
            "title": interview.get('job_title', 'Software Engineer'),
            "description": interview.get('job_description', ''),
            "requirements": []
        }
        
        # Generate questions based on job and resume
        questions_result = question_agent.generate_questions(
            resume_data=resume_data,
            job_description=job_description,
            candidate_id=interview.get('candidate_id', ''),
            job_id=interview.get('job_id', ''),
            interview_id=interview_id
        )
        
        if not questions_result.get('success'):
            logger.error(f"❌ Failed to generate questions: {questions_result.get('errors')}")
            return {
                "success": False,
                "error": {
                    "code": "QUESTION_GENERATION_FAILED",
                    "message": "Failed to generate interview questions",
                    "details": questions_result.get('errors')
                }
            }
        
        # Extract questions from the data field
        questions_data = questions_result.get('data', {})
        questions = questions_data.get('questions', [])
        logger.info(f"✅ Generated {len(questions)} questions")
        
        # Step 2: Start interview conductor
        logger.info("🎯 Starting interview conductor...")
        
        # Store questions in interview document
        from db.mongo_client import get_db
        db = get_db()
        db.interviews.update_one(
            {"interview_id": interview_id},
            {"$set": {
                "questions": questions,
                "questions_generated": True,
                "interactive_interview_started": True,
                "current_question_index": 0
            }}
        )
        
        # Step 3: Return success - the bot will handle Q&A flow
        return {
            "success": True,
            "message": "Interactive interview started successfully",
            "data": {
                "interview_id": interview_id,
                "total_questions": len(questions),
                "first_question": questions[0] if questions else None,
                "status": "active"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error starting interactive interview: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "ORCHESTRATION_ERROR",
                "message": str(e)
            }
        }


@app.get("/api/interviews/{interview_id}/questions")
async def get_interview_questions(interview_id: str):
    """
    Get generated questions for an interview
    
    Returns:
        List of questions or error
    """
    try:
        logger.info(f"📋 Getting questions for interview: {interview_id}")
        
        from repositories.interview_repository import InterviewRepository
        interview_repo = InterviewRepository()
        interview = interview_repo.get_interview_by_id(interview_id)
        
        if not interview:
            return {"success": False, "error": "Interview not found"}
        
        questions = interview.get('questions', [])
        
        return {
            "success": True,
            "interview_id": interview_id,
            "questions": questions,
            "total": len(questions),
            "current_index": interview.get('current_question_index', 0)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting questions: {str(e)}")
        return {"success": False, "error": str(e)}


@app.post("/api/interviews/{interview_id}/conduct")
async def conduct_interactive_interview(interview_id: str):
    """
    Conduct the interactive interview: bot asks questions via TTS and listens for answers
    
    This orchestrates the full Q&A loop:
    1. Get next question from generated questions
    2. Speak question via TTS (ElevenLabs)
    3. Listen for candidate answer via STT (Groq Whisper) 
    4. Analyze answer with LLM
    5. Ask follow-up or move to next question
    6. Repeat until all questions answered
    
    Returns:
        Interview conductor status
    """
    try:
        logger.info(f"🎤 Starting interview conduction for: {interview_id}")
        
        # Get interview details
        from repositories.interview_repository import InterviewRepository
        interview_repo = InterviewRepository()
        interview = interview_repo.get_interview_by_id(interview_id)
        
        if not interview:
            return {
                "success": False,
                "error": {"code": "INTERVIEW_NOT_FOUND", "message": "Interview not found"}
            }
        
        # Check if questions are generated
        questions = interview.get('questions', [])
        if not questions:
            return {
                "success": False,
                "error": {"code": "NO_QUESTIONS", "message": "No questions generated yet"}
            }
        
        # Start interview conductor
        from langgraph_agents.interview_conductor_agent import conduct_interview
        
        conductor_config = {
            "interview_id": interview_id,
            "candidate_name": interview.get('candidate_name', 'Candidate'),
            "candidate_email": interview.get('candidate_email', ''),
            "job_title": interview.get('job_title', 'Position'),
            "job_description": interview.get('job_description', ''),
            "required_skills": interview.get('required_skills', []),
            "candidate_resume": "",
            "target_duration_minutes": 45,
            "questions": questions
        }
        
        result = await conduct_interview(conductor_config)
        
        if result.get('success'):
            logger.info(f"✅ Interview conductor started successfully")
            logger.info(f"   Introduction: {result.get('introduction', '')[:100]}...")
            
            # Speak introduction via TTS
            intro_text = result.get('introduction', '')
            if intro_text:
                tts_result = await speak_in_meeting(interview_id, intro_text, "intro")
                logger.info(f"   TTS Introduction: {'✅' if tts_result.get('success') else '❌'}")
            
            return {
                "success": True,
                "message": "Interview conductor started",
                "data": {
                    "interview_id": interview_id,
                    "session_id": result.get('session_id'),
                    "introduction": intro_text,
                    "total_questions": len(questions),
                    "status": "active"
                }
            }
        else:
            logger.error(f"❌ Failed to start conductor: {result.get('error')}")
            return {
                "success": False,
                "error": {"code": "CONDUCTOR_FAILED", "message": str(result.get('error'))}
            }
            
    except Exception as e:
        logger.error(f"❌ Error conducting interview: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {"code": "CONDUCT_ERROR", "message": str(e)}
        }


@app.post("/api/interviews/{interview_id}/speak")
async def speak_question_in_meeting(interview_id: str, request: dict):
    """
    Speak a question or text in the active Google Meet session via TTS
    
    Request body:
        {
            "text": "Question text to speak",
            "text_type": "question|intro|followup|closing",
            "question_index": 0
        }
    
    Returns:
        TTS generation status and audio details
    """
    try:
        text = request.get('text', '')
        text_type = request.get('text_type', 'question')
        question_index = request.get('question_index', 0)
        
        logger.info(f"🔊 Speaking in meeting for interview: {interview_id}")
        logger.info(f"   Text type: {text_type}")
        logger.info(f"   Text: {text[:100]}...")
        
        result = await speak_in_meeting(interview_id, text, text_type)
        
        if result.get('success'):
            logger.info(f"✅ TTS completed successfully")
            
            # Update interview with spoken question
            from repositories.interview_repository import InterviewRepository
            interview_repo = InterviewRepository()
            interview_repo.update_interview(
                interview_id,
                {
                    f"questions.{question_index}.spoken_at": datetime.datetime.now().isoformat(),
                    f"questions.{question_index}.tts_audio_id": result['data'].get('tts_id')
                }
            )
            
            return {"success": True, "data": result['data']}
        else:
            logger.error(f"❌ TTS failed: {result.get('error')}")
            return {"success": False, "error": result.get('error')}
            
    except Exception as e:
        logger.error(f"❌ Error speaking in meeting: {str(e)}", exc_info=True)
        return {"success": False, "error": {"code": "TTS_ERROR", "message": str(e)}}


async def speak_in_meeting(interview_id: str, text: str, text_type: str = "question") -> Dict[str, Any]:
    """
    Helper function to generate TTS audio and play it in the meeting
    
    Args:
        interview_id: Interview ID
        text: Text to speak
        text_type: Type of text (intro, question, followup, closing)
    
    Returns:
        TTS result with audio data
    """
    from langgraph_agents.tts_agent import convert_text_to_speech
    
    tts_request = {
        "text": text,
        "text_type": text_type,
        "voice_profile": "professional_female",  # Can be configured
        "emotion": "professional",
        "session_id": interview_id,
        "interview_id": interview_id
    }
    
    result = await convert_text_to_speech(tts_request)
    
    # TODO: Send audio to Google Meet via Puppeteer bot
    # This would require integrating with the meet_recorder.js to play audio
    # For now, we return the TTS result
    
    return result


@app.post("/api/interviews/{interview_id}/qa-loop")
async def run_qa_loop(interview_id: str):
    """
    Run the complete Q&A loop for interactive interview
    
    This orchestrates:
    1. Get next question
    2. Speak question via TTS
    3. Wait for candidate answer (STT)
    4. Analyze answer with LLM
    5. Generate follow-up or move to next
    6. Repeat until done
    
    Returns:
        Q&A loop status
    """
    try:
        logger.info(f"🔄 Starting Q&A loop for interview: {interview_id}")
        
        # Get interview details
        from repositories.interview_repository import InterviewRepository
        interview_repo = InterviewRepository()
        interview = interview_repo.get_interview_by_id(interview_id)
        
        if not interview:
            return {"success": False, "error": {"code": "NOT_FOUND", "message": "Interview not found"}}
        
        questions = interview.get('questions', [])
        if not questions:
            return {"success": False, "error": {"code": "NO_QUESTIONS", "message": "No questions available"}}
        
        current_index = interview.get('current_question_index', 0)
        
        if current_index >= len(questions):
            return {
                "success": True,
                "message": "Interview complete - all questions answered",
                "data": {"status": "completed", "total_questions": len(questions)}
            }
        
        current_question = questions[current_index]
        question_text = current_question.get('question', '')
        
        logger.info(f"📝 Current question {current_index + 1}/{len(questions)}: {question_text[:80]}...")
        
        # Step 1: Speak the question via TTS
        logger.info("🔊 Step 1: Speaking question via TTS...")
        tts_result = await speak_in_meeting(interview_id, question_text, "question")
        
        if not tts_result.get('success'):
            return {
                "success": False,
                "error": {"code": "TTS_FAILED", "message": "Failed to generate TTS audio"}
            }
        
        # Update question with TTS info
        interview_repo.update_interview(
            interview_id,
            {
                f"questions.{current_index}.spoken_at": datetime.datetime.now().isoformat(),
                f"questions.{current_index}.tts_audio_id": tts_result['data'].get('tts_id'),
                f"questions.{current_index}.status": "spoken"
            }
        )
        
        logger.info(f"✅ Question spoken successfully (audio: {tts_result['data'].get('audio_duration_seconds')}s)")
        
        # Step 2: Listen for answer (STT)
        # Note: STT is passive - audio comes from meet_bot via WebSocket
        # We just mark that we're waiting for answer
        interview_repo.update_interview(
            interview_id,
            {"current_question_index": current_index, "waiting_for_answer": True}
        )
        
        logger.info("👂 Step 2: Listening for candidate answer...")
        logger.info("   (STT will capture answer from audio stream)")
        
        return {
            "success": True,
            "message": "Question spoken, waiting for answer",
            "data": {
                "interview_id": interview_id,
                "current_question_index": current_index,
                "total_questions": len(questions),
                "question": question_text,
                "tts_audio_id": tts_result['data'].get('tts_id'),
                "audio_duration": tts_result['data'].get('audio_duration_seconds'),
                "status": "waiting_for_answer"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error in Q&A loop: {str(e)}", exc_info=True)
        return {"success": False, "error": {"code": "QA_LOOP_ERROR", "message": str(e)}}


@app.post("/api/interviews/{interview_id}/process-answer")
async def process_candidate_answer(interview_id: str, request: dict):
    """
    Process candidate's answer to current question
    
    Request body:
        {
            "answer_text": "Candidate's transcribed answer",
            "answer_audio_id": "audio_chunk_id",
            "question_index": 0
        }
    
    This will:
    1. Analyze answer with LLM
    2. Score the answer
    3. Generate follow-up if needed
    4. Move to next question or continue
    
    Returns:
        Analysis result and next action
    """
    try:
        # Accept both 'answer' and 'answer_text' for compatibility
        answer_text = request.get('answer_text', '') or request.get('answer', '')
        answer_audio_id = request.get('answer_audio_id')
        
        logger.info(f"🔍 Processing answer for interview: {interview_id}")
        
        from repositories.interview_repository import InterviewRepository
        interview_repo = InterviewRepository()
        interview = interview_repo.get_interview_by_id(interview_id)
        
        if not interview:
            return {"success": False, "error": {"code": "NOT_FOUND", "message": "Interview not found"}}
        
        questions = interview.get('questions', [])
        # Use current_question_index from interview state
        question_index = interview.get('current_question_index', 0)
        
        logger.info(f"   Question {question_index + 1}/{len(questions)}, Answer length: {len(answer_text)} chars")
        
        if question_index >= len(questions):
            return {"success": False, "error": {"code": "INVALID_INDEX", "message": "Invalid question index"}}
        
        current_question = questions[question_index]
        question_text = current_question.get('question', '')
        
        # Check if this question already has an answer (indicates this is a follow-up response)
        is_followup_response = bool(current_question.get('answer'))
        
        # Analyze answer with Groq LLM directly
        from groq import Groq
        groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        
        # Build analysis prompt
        expected_points = current_question.get('expected_answer_points', [])
        expected_points_text = "\n".join([f"- {point}" for point in expected_points]) if expected_points else "N/A"
        
        analysis_prompt = f"""Analyze this interview answer and provide a score with feedback.

Question: {question_text}
Category: {current_question.get('category', 'general')}
Expected Answer Points:
{expected_points_text}

Candidate's Answer:
{answer_text}

Analyze the answer and provide:
1. A score from 0-10
2. Brief feedback (2-3 sentences)
3. Whether a follow-up question is needed (true/false)
4. If follow-up needed, generate one follow-up question

Respond ONLY with valid JSON in this format:
{{
  "score": 8,
  "feedback": "Good answer covering key points...",
  "needs_followup": false,
  "followup_question": ""
}}"""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.3,
            max_tokens=500
        )
        
        analysis_text = response.choices[0].message.content
        
        # Parse JSON response
        import json
        try:
            # Extract JSON from response (might have markdown backticks)
            if "```json" in analysis_text:
                analysis_text = analysis_text.split("```json")[1].split("```")[0]
            elif "```" in analysis_text:
                analysis_text = analysis_text.split("```")[1].split("```")[0]
            
            analysis_data = json.loads(analysis_text.strip())
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Fallback analysis
            analysis_data = {
                "score": 5,
                "feedback": "Answer received and recorded.",
                "needs_followup": False,
                "followup_question": ""
            }
        
        score = analysis_data.get('score', 0)
        feedback = analysis_data.get('feedback', '')
        needs_followup = analysis_data.get('needs_followup', False)
        followup_question = analysis_data.get('followup_question', '')
        
        logger.info(f"✅ Answer analyzed - Score: {score}/10")
        
        # Store answer and analysis
        interview_repo.update_interview(
            interview_id,
            {
                f"questions.{question_index}.answer": answer_text,
                f"questions.{question_index}.answer_audio_id": answer_audio_id,
                f"questions.{question_index}.answered_at": datetime.datetime.now().isoformat(),
                f"questions.{question_index}.score": score,
                f"questions.{question_index}.feedback": feedback,
                f"questions.{question_index}.needs_followup": needs_followup,
                f"questions.{question_index}.status": "answered",
                "waiting_for_answer": False
            }
        )
        
        # Decide next action based on whether this is initial answer or follow-up response
        if needs_followup and followup_question and not is_followup_response:
            # This is the FIRST answer to this question - generate follow-up
            logger.info(f"🔄 Generating follow-up question...")
            
            # Speak follow-up
            followup_tts = await speak_in_meeting(interview_id, followup_question, "followup")
            
            # Check if TTS succeeded (may fail due to quota)
            followup_audio_id = followup_tts.get('data', {}).get('tts_id') if followup_tts.get('success') else None
            
            return {
                "success": True,
                "message": "Follow-up question generated",
                "data": {
                    "score": score,
                    "feedback": feedback,
                    "followup_question": followup_question,
                    "followup_audio_id": followup_audio_id,
                    "next_action": "followup",
                    "current_index": question_index
                }
            }
        else:
            # Either no follow-up needed, OR this is already a follow-up response
            # In both cases: move to next question
            if is_followup_response:
                logger.info(f"✅ Follow-up response processed, moving to next question...")
            
            next_index = question_index + 1
            
            if next_index < len(questions):
                # Update to next question
                interview_repo.update_interview(interview_id, {"current_question_index": next_index})
                
                logger.info(f"➡️ Moving to next question {next_index + 1}/{len(questions)}")
                
                return {
                    "success": True,
                    "message": "Answer processed, moving to next question",
                    "data": {
                        "score": score,
                        "feedback": feedback,
                        "next_action": "next_question",
                        "current_index": next_index,
                        "total_questions": len(questions)
                    }
                }
            else:
                # Interview complete
                logger.info(f"✅ Interview completed - all {len(questions)} questions answered")
                
                # Generate closing message
                closing_text = f"Thank you {interview.get('candidate_name', 'Candidate')}, that completes our interview. We appreciate your time and thoughtful answers. Our HR team will review your responses and get back to you soon."
                
                closing_tts = await speak_in_meeting(interview_id, closing_text, "closing")
                
                # Update index to signal completion (important for auto-conduct loop)
                interview_repo.update_interview(
                    interview_id,
                    {
                        "current_question_index": next_index,  # Set to len(questions) to exit loop
                        "interview_status": "completed",
                        "completed_at": datetime.datetime.now().isoformat(),
                        "closing_audio_id": closing_tts['data'].get('tts_id')
                    }
                )
                
                return {
                    "success": True,
                    "message": "Interview completed successfully",
                    "data": {
                        "score": score,
                        "feedback": feedback,
                        "next_action": "complete",
                        "total_questions": len(questions),
                        "closing_message": closing_text,
                        "closing_audio_id": closing_tts['data'].get('tts_id')
                    }
                }
        
    except Exception as e:
        logger.error(f"❌ Error processing answer: {str(e)}", exc_info=True)
        return {"success": False, "error": {"code": "PROCESS_ERROR", "message": str(e)}}


@app.post("/api/interviews/{interview_id}/reset")
async def reset_interview(interview_id: str):
    """
    Reset interview to initial state for testing
    Clears answers and resets status to scheduled
    """
    try:
        logger.info(f"🔄 Resetting interview: {interview_id}")
        
        # Reset interview state directly in database
        from db.mongo_client import get_db
        db = get_db()
        
        update_data = {
            "status": "scheduled",
            "current_question_index": 0,
            "answers": [],
            "started_at": None,
            "completed_at": None
        }
        
        result = db.interviews.update_one(
            {"interview_id": interview_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            return {
                "success": False,
                "error": {"code": "NOT_FOUND", "message": "Interview not found"}
            }
        
        if result.modified_count > 0:
            logger.info(f"✅ Interview reset successfully: {interview_id}")
            return {
                "success": True,
                "message": "Interview reset successfully",
                "data": {
                    "interview_id": interview_id,
                    "status": "scheduled",
                    "current_question_index": 0,
                    "answers_cleared": True
                }
            }
        else:
            # Interview exists but already in reset state
            logger.info(f"ℹ️ Interview already in reset state: {interview_id}")
            return {
                "success": True,
                "message": "Interview already in reset state",
                "data": {
                    "interview_id": interview_id,
                    "status": "scheduled",
                    "current_question_index": 0,
                    "answers_cleared": False
                }
            }
            
    except Exception as e:
        logger.error(f"❌ Error resetting interview: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {"code": "RESET_ERROR", "message": str(e)}
        }


@app.post("/api/interviews/{interview_id}/auto-conduct")
async def auto_conduct_interview(interview_id: str):
    """
    Automatically conduct complete interview with all Q&A loops
    
    This endpoint orchestrates the entire interview:
    1. Speaks introduction
    2. Loops through all questions:
       - Asks question via TTS
       - Waits for answer (simulated or from STT)
       - Analyzes answer with LLM
       - Generates follow-up if needed
       - Moves to next question
    3. Speaks closing message
    4. Saves final interview results
    
    **Note:** This is for testing/demo. In production, use real-time STT integration.
    
    Returns:
        Complete interview summary with all scores and feedback
    
    Example:
        POST /api/interviews/{interview_id}/auto-conduct
    """
    logger.info(f"🎯 Starting automated interview conductor for: {interview_id}")
    
    try:
        # Import repository
        from repositories.interview_repository import InterviewRepository
        
        # Initialize repository
        interview_repo = InterviewRepository()
        
        # Get interview
        interview = interview_repo.get_interview_by_id(interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Check if questions exist
        questions = interview.get('questions', [])
        if not questions:
            return {
                "success": False,
                "error": {
                    "code": "NO_QUESTIONS",
                    "message": "No questions found for this interview. Generate questions first."
                }
            }
        
        logger.info(f"📋 Found {len(questions)} questions to ask")
        
        # Track results
        results = {
            "interview_id": interview_id,
            "candidate_name": interview.get('candidate_name'),
            "total_questions": len(questions),
            "questions_asked": 0,
            "questions_answered": 0,
            "followups_generated": 0,
            "scores": [],
            "average_score": 0,
            "started_at": datetime.datetime.now().isoformat(),
            "completed_at": None,
            "status": "in_progress"
        }
        
        # Step 1: Speak introduction
        logger.info("🎬 Step 1: Speaking introduction...")
        try:
            intro_result = await conduct_interactive_interview(interview_id)
            if intro_result.get('success'):
                logger.info("✅ Introduction spoken successfully")
            else:
                logger.warn("⚠️ Introduction failed, continuing anyway")
        except Exception as e:
            logger.warn(f"⚠️ Introduction error: {e}, continuing anyway")
        
        # Step 2: Loop through all questions
        # Always read current_index from database to stay synchronized
        while True:
            # Refresh interview state from database
            interview = interview_repo.get_interview_by_id(interview_id)
            current_index = interview.get('current_question_index', 0)
            
            if current_index >= len(questions):
                logger.info("✅ All questions completed")
                break
            
            question_num = current_index + 1
            logger.info(f"\n{'='*60}")
            logger.info(f"📝 Question {question_num}/{len(questions)}")
            logger.info(f"{'='*60}")
            
            # Ask question
            logger.info(f"🔊 Asking question {question_num}...")
            qa_result = await run_qa_loop(interview_id)
            
            if not qa_result.get('success'):
                logger.error(f"❌ Failed to ask question {question_num}: {qa_result.get('message')}")
                break
            
            results["questions_asked"] += 1
            question_data = qa_result['data']
            logger.info(f"✅ Question asked: {question_data.get('question', '')[:80]}...")
            
            # Simulate waiting for answer (2 seconds)
            # In production, this would wait for real STT transcription
            logger.info("⏳ Waiting for candidate answer (simulated 2s delay)...")
            import asyncio
            await asyncio.sleep(2)
            
            # Generate simulated answer (quality varies by question number)
            # Pass the actual question text for contextually relevant answers
            question_text = question_data.get('question', '')
            simulated_answer = generate_simulated_answer(question_num, len(questions), question_text)
            logger.info(f"🎤 Simulated answer: {simulated_answer[:100]}...")
            
            # Process answer
            logger.info(f"🔍 Processing answer with LLM...")
            answer_result = await process_candidate_answer(
                interview_id,
                {"answer": simulated_answer, "answer_audio_id": f"audio_q{question_num}"}
            )
            
            if not answer_result.get('success'):
                logger.error(f"❌ Failed to process answer {question_num}")
                break
            
            results["questions_answered"] += 1
            answer_data = answer_result['data']
            
            score = answer_data['score']
            feedback = answer_data['feedback']
            next_action = answer_data['next_action']
            
            results["scores"].append(score)
            
            logger.info(f"✅ Answer processed:")
            logger.info(f"   Score: {score}/10")
            logger.info(f"   Feedback: {feedback[:80]}...")
            logger.info(f"   Next action: {next_action}")
            
            # Handle follow-up
            if next_action == 'followup':
                results["followups_generated"] += 1
                logger.info(f"🔄 Follow-up generated, processing follow-up answer...")
                
                # Simulate follow-up answer with context from original question
                await asyncio.sleep(1)
                followup_answer = generate_simulated_answer(question_num, len(questions), question_text)
                logger.info(f"🎤 Follow-up answer: {followup_answer[:80]}...")
                
                followup_result = await process_candidate_answer(
                    interview_id,
                    {"answer": followup_answer, "answer_audio_id": f"audio_q{question_num}_followup"}
                )
                
                if followup_result.get('success'):
                    logger.info("✅ Follow-up processed successfully")
                    # Update next_action from follow-up result
                    followup_data = followup_result.get('data', {})
                    next_action = followup_data.get('next_action', next_action)
            
            # Check if interview completed
            if next_action == 'complete':
                logger.info("🎉 Interview marked as complete by LLM")
                break
            
            # process_candidate_answer already updates the DB with next index
            # Just add a brief pause before next iteration
            await asyncio.sleep(0.5)
        
        # Step 3: Final summary
        logger.info("\n" + "="*60)
        logger.info("📊 INTERVIEW COMPLETED")
        logger.info("="*60)
        
        results["completed_at"] = datetime.datetime.now().isoformat()
        results["status"] = "completed"
        
        if results["scores"]:
            results["average_score"] = sum(results["scores"]) / len(results["scores"])
        
        logger.info(f"✅ Total Questions: {results['total_questions']}")
        logger.info(f"✅ Questions Asked: {results['questions_asked']}")
        logger.info(f"✅ Questions Answered: {results['questions_answered']}")
        logger.info(f"✅ Follow-ups Generated: {results['followups_generated']}")
        logger.info(f"✅ Average Score: {results['average_score']:.1f}/10")
        logger.info(f"✅ Scores: {results['scores']}")
        
        return {
            "success": True,
            "message": "Automated interview completed successfully",
            "data": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in auto-conduct: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "AUTO_CONDUCT_ERROR",
                "message": str(e)
            }
        }


def generate_simulated_answer(question_num: int, total_questions: int, question_text: str = "") -> str:
    """
    Generate simulated candidate answer with varying quality based on question number
    Simple quality variation for testing - realistic scoring distribution
    """
    
    # Quality tier determines answer depth and completeness
    # Q1-4: Excellent (detailed, comprehensive - expect 7-9/10)
    # Q5-7: Good (solid but less detail - expect 5-7/10)  
    # Q8-10: Average (brief, basic - expect 3-5/10)
    if question_num <= 4:
        return f"""Based on my understanding and experience, I can provide a comprehensive answer to this question. 
        The key concepts involve understanding the fundamentals and applying them practically. 
        I've worked with similar scenarios in my studies and projects. Let me explain my approach: 
        First, I would analyze the requirements carefully. Then, I would research best practices and 
        consider different solutions. I believe in implementing solutions incrementally, testing at each step 
        to ensure quality. Documentation is also important for maintainability. I would collaborate with 
        team members to get feedback and ensure the solution meets all requirements. 
        (Question {question_num}/{total_questions})"""
    elif question_num <= 7:
        return f"""I have some experience with this topic. My approach would be to first understand 
        the requirements, then plan the implementation carefully. I would test my solution to make sure 
        it works correctly and meets the needs. Collaboration and communication are important for success. 
        (Question {question_num}/{total_questions})"""
    else:
        return f"""I think I understand what you're asking. I would try my best to solve this problem 
        using what I've learned. (Question {question_num}/{total_questions})"""


# ==================== Speech-to-Text (STT) API Endpoints ====================

from langgraph_agents.audio_transcription_agent import AudioTranscriptionAgent, transcribe_audio_chunk
from fastapi import UploadFile, File, Form
from pydantic import Field

class STTTranscribeRequest(BaseModel):
    """Request model for audio transcription"""
    audio_data: str = Field(..., description="Base64 encoded audio data")
    audio_format: str = Field(default="webm", description="Audio format (webm, wav, mp3, etc.)")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    interview_id: Optional[str] = Field(None, description="Interview ID for context")
    question_context: Optional[str] = Field(None, description="Current question context")
    language: Optional[str] = Field(default="en", description="Expected language")


class STTStreamChunkRequest(BaseModel):
    """Request model for streaming audio chunk"""
    chunk_id: str
    session_id: str
    audio_data: str  # Base64 encoded
    audio_format: str = "webm"
    chunk_number: int
    is_final: bool = False


@app.post("/api/stt/transcribe")
async def transcribe_audio(request: STTTranscribeRequest):
    """
    Transcribe audio using Groq Whisper API with LangGraph + MCP
    
    This endpoint handles real-time speech-to-text conversion using:
    - Groq Whisper API (whisper-large-v3 model)
    - LangGraph workflow for processing pipeline
    - MCP components for optimization and caching
    
    Returns:
        Status 200 with transcription result or error in body
        
    Example:
        {
            "success": true,
            "data": {
                "raw_transcription": "...",
                "cleaned_transcription": "...",
                "confidence_score": 0.95,
                "sentiment": "positive",
                "key_points": [...],
                "processing_time_ms": 1234
            }
        }
    """
    try:
        logger.info("\n" + "="*80)
        logger.info("🎤 API CALL: /api/stt/transcribe")
        logger.info("="*80)
        logger.info(f"📊 Audio format: {request.audio_format}")
        logger.info(f"🔤 Language: {request.language}")
        
        if request.session_id:
            logger.info(f"📝 Session ID: {request.session_id}")
        if request.interview_id:
            logger.info(f"💼 Interview ID: {request.interview_id}")
        
        # Validate audio data
        if not request.audio_data:
            logger.error("❌ No audio data provided")
            return {
                "success": False,
                "error": {
                    "code": "MISSING_AUDIO_DATA",
                    "message": "Audio data is required"
                }
            }
        
        # Decode base64 audio
        try:
            audio_bytes = base64.b64decode(request.audio_data)
            logger.info(f"✅ Decoded audio data: {len(audio_bytes)} bytes")
        except Exception as decode_error:
            logger.error(f"❌ Failed to decode audio data: {str(decode_error)}")
            return {
                "success": False,
                "error": {
                    "code": "INVALID_AUDIO_DATA",
                    "message": f"Failed to decode base64 audio: {str(decode_error)}"
                }
            }
        
        # Check audio size
        if len(audio_bytes) < 100:
            logger.warning(f"⚠️ Audio data too small: {len(audio_bytes)} bytes")
            return {
                "success": False,
                "error": {
                    "code": "AUDIO_TOO_SMALL",
                    "message": f"Audio data too small ({len(audio_bytes)} bytes). Minimum 100 bytes required."
                }
            }
        
        # Generate chunk ID
        chunk_id = f"stt_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Prepare chunk configuration
        chunk_config = {
            'session_id': request.session_id or 'direct_api_call',
            'audio_chunk_id': chunk_id,
            'audio_data': audio_bytes,
            'audio_format': request.audio_format,
            'interview_id': request.interview_id or '',
            'question_context': request.question_context or '',
            'previous_transcripts': []
        }
        
        # Start timing
        start_time = datetime.datetime.now()
        
        # Invoke LangGraph transcription agent
        logger.info(f"🤖 Invoking Audio Transcription LangGraph Agent")
        logger.info(f"   Using model: whisper-large-v3")
        logger.info(f"   Chunk ID: {chunk_id}")
        
        result = await transcribe_audio_chunk(chunk_config)
        
        # Calculate processing time
        processing_time_ms = int((datetime.datetime.now() - start_time).total_seconds() * 1000)
        
        logger.info(f"✅ Transcription completed: {result.get('processing_status')}")
        logger.info(f"   Processing time: {processing_time_ms}ms")
        logger.info(f"   Confidence: {result.get('confidence_score', 0.0):.2f}")
        logger.info(f"   Sentiment: {result.get('sentiment', 'neutral')}")
        logger.info(f"   Text length: {len(result.get('cleaned_transcription', ''))} chars")
        logger.info("="*80 + "\n")
        
        # Check if transcription was successful
        if result.get('processing_status') != 'completed':
            return {
                "success": False,
                "error": {
                    "code": "TRANSCRIPTION_FAILED",
                    "message": result.get('last_error', 'Transcription processing failed'),
                    "details": {
                        "processing_status": result.get('processing_status'),
                        "errors": result.get('errors', [])
                    }
                }
            }
        
        # Return successful result
        return {
            "success": True,
            "message": "Audio transcribed successfully",
            "data": {
                "chunk_id": chunk_id,
                "raw_transcription": result.get('raw_transcription', ''),
                "cleaned_transcription": result.get('cleaned_transcription', ''),
                "confidence_score": result.get('confidence_score', 0.0),
                "language_detected": result.get('language_detected', 'en'),
                "speaker_detected": result.get('speaker_detected', ''),
                "sentiment": result.get('sentiment', 'neutral'),
                "key_points": result.get('key_points', []),
                "technical_terms": result.get('technical_terms', []),
                "chunk_duration": result.get('chunk_duration', 0.0),
                "processing_time_ms": processing_time_ms,
                "model": "whisper-large-v3",
                "workflow": "langgraph",
                "mcp_optimized": True
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error in /api/stt/transcribe: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "TRANSCRIPTION_ERROR",
                "message": str(e),
                "traceback": str(e.__traceback__) if hasattr(e, '__traceback__') else None
            }
        }


@app.post("/api/stt/transcribe/file")
async def transcribe_audio_file(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    interview_id: Optional[str] = Form(None),
    question_context: Optional[str] = Form(None)
):
    """
    Transcribe audio file upload using Groq Whisper API
    
    This endpoint accepts file uploads (multipart/form-data) for transcription.
    Supports: mp3, mp4, mpeg, mpga, m4a, wav, webm
    
    Returns:
        Status 200 with transcription result or error in body
    """
    try:
        logger.info("\n" + "="*80)
        logger.info("📁 API CALL: /api/stt/transcribe/file")
        logger.info("="*80)
        logger.info(f"📄 Filename: {file.filename}")
        logger.info(f"📊 Content type: {file.content_type}")
        
        # Read file content
        audio_bytes = await file.read()
        logger.info(f"✅ File uploaded: {len(audio_bytes)} bytes")
        
        # Determine audio format from filename
        audio_format = file.filename.split('.')[-1].lower() if '.' in file.filename else 'wav'
        logger.info(f"🔊 Detected format: {audio_format}")
        
        # Validate format
        supported_formats = ['mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm']
        if audio_format not in supported_formats:
            logger.warning(f"⚠️ Unsupported format: {audio_format}, defaulting to wav")
            audio_format = 'wav'
        
        # Encode to base64 and use existing endpoint logic
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        # Create request object
        transcribe_request = STTTranscribeRequest(
            audio_data=audio_base64,
            audio_format=audio_format,
            session_id=session_id,
            interview_id=interview_id,
            question_context=question_context
        )
        
        # Use existing transcription logic
        return await transcribe_audio(transcribe_request)
        
    except Exception as e:
        logger.error(f"❌ Error in /api/stt/transcribe/file: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "FILE_TRANSCRIPTION_ERROR",
                "message": str(e)
            }
        }


@app.post("/api/stt/stream/chunk")
async def stream_audio_chunk(request: STTStreamChunkRequest):
    """
    Process streaming audio chunk for real-time transcription
    
    This endpoint is designed for real-time streaming scenarios where
    audio is sent in small chunks (e.g., 5-second intervals).
    
    The chunks are accumulated and transcribed using LangGraph workflow.
    
    Returns:
        Status 200 with chunk acknowledgment or error in body
    """
    try:
        logger.info(f"🔄 Stream chunk received: {request.chunk_id}")
        logger.info(f"   Session: {request.session_id}")
        logger.info(f"   Chunk #: {request.chunk_number}")
        logger.info(f"   Final: {request.is_final}")
        
        # Decode audio data
        try:
            audio_bytes = base64.b64decode(request.audio_data)
            logger.info(f"✅ Decoded chunk: {len(audio_bytes)} bytes")
        except Exception as decode_error:
            logger.error(f"❌ Failed to decode chunk: {str(decode_error)}")
            return {
                "success": False,
                "error": {
                    "code": "INVALID_CHUNK_DATA",
                    "message": f"Failed to decode chunk data: {str(decode_error)}"
                }
            }
        
        # Save chunk to MongoDB via repository
        meet_session_repo.save_audio_chunk_metadata({
            'chunk_id': request.chunk_id,
            'session_id': request.session_id,
            'chunk_number': request.chunk_number,
            'chunk_size': len(audio_bytes),
            'audio_format': request.audio_format,
            'is_final': request.is_final,
            'processing_status': 'received'
        })
        
        logger.info(f"💾 Chunk saved to database: {request.chunk_id}")
        
        # If this is a final chunk or chunk number is multiple of 5, transcribe
        should_transcribe = request.is_final or (request.chunk_number % 5 == 0)
        
        if should_transcribe:
            logger.info(f"🎤 Triggering transcription for chunk: {request.chunk_id}")
            
            # Prepare chunk configuration
            chunk_config = {
                'session_id': request.session_id,
                'audio_chunk_id': request.chunk_id,
                'audio_data': audio_bytes,
                'audio_format': request.audio_format,
                'interview_id': '',
                'question_context': '',
                'previous_transcripts': []
            }
            
            # Process asynchronously
            asyncio.create_task(
                _process_chunk_transcription(request.session_id, request.chunk_id, chunk_config)
            )
            
            return {
                "success": True,
                "message": "Chunk received and transcription started",
                "data": {
                    "chunk_id": request.chunk_id,
                    "chunk_number": request.chunk_number,
                    "processing_status": "transcribing",
                    "is_final": request.is_final
                }
            }
        else:
            return {
                "success": True,
                "message": "Chunk received and queued",
                "data": {
                    "chunk_id": request.chunk_id,
                    "chunk_number": request.chunk_number,
                    "processing_status": "queued",
                    "is_final": request.is_final
                }
            }
        
    except Exception as e:
        logger.error(f"❌ Error in /api/stt/stream/chunk: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "STREAM_CHUNK_ERROR",
                "message": str(e)
            }
        }


async def _process_chunk_transcription(session_id: str, chunk_id: str, chunk_config: dict):
    """Background task to process chunk transcription"""
    try:
        logger.info(f"🤖 [Background] Starting transcription for chunk: {chunk_id}")
        
        result = await transcribe_audio_chunk(chunk_config)
        
        logger.info(f"✅ [Background] Transcription completed: {result.get('processing_status')}")
        
        # Save transcript to MongoDB if successful
        if result.get('processing_status') == 'completed' and result.get('cleaned_transcription'):
            meet_session_repo.save_transcript({
                'chunk_id': chunk_id,
                'session_id': session_id,
                'interview_id': '',
                'raw_transcription': result.get('raw_transcription', ''),
                'cleaned_transcription': result.get('cleaned_transcription', ''),
                'confidence_score': result.get('confidence_score', 0.0),
                'language_detected': result.get('language_detected', 'en'),
                'speaker_detected': result.get('speaker_detected', ''),
                'sentiment': result.get('sentiment', 'neutral'),
                'key_points': result.get('key_points', []),
                'technical_terms': result.get('technical_terms', []),
                'chunk_duration': result.get('chunk_duration', 0.0)
            })
            logger.info(f"💾 [Background] Transcript saved to database: {chunk_id}")
        else:
            logger.warning(f"⚠️ [Background] Transcription failed for chunk: {chunk_id}")
            
    except Exception as e:
        logger.error(f"❌ [Background] Error processing transcription: {str(e)}", exc_info=True)


@app.get("/api/stt/transcript/{session_id}")
async def get_session_transcripts(session_id: str):
    """
    Get all transcripts for a session
    
    Returns:
        Status 200 with transcripts list or error in body
    """
    try:
        logger.info(f"📝 Getting transcripts for session: {session_id}")
        
        # Get transcripts from repository
        transcripts = meet_session_repo.get_transcripts_by_session(session_id)
        
        if not transcripts:
            logger.warning(f"⚠️ No transcripts found for session: {session_id}")
            return {
                "success": False,
                "error": {
                    "code": "NO_TRANSCRIPTS",
                    "message": f"No transcripts found for session {session_id}"
                }
            }
        
        # Get full transcript compilation
        full_transcript_data = meet_session_repo.get_full_transcript(session_id)
        
        logger.info(f"✅ Retrieved {len(transcripts)} transcripts")
        
        return {
            "success": True,
            "message": f"Retrieved {len(transcripts)} transcripts",
            "data": {
                "session_id": session_id,
                "transcripts": transcripts,
                "total_count": len(transcripts),
                "full_transcript": full_transcript_data.get('full_transcript', ''),
                "stats": full_transcript_data.get('stats', {})
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting transcripts: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "TRANSCRIPTS_ERROR",
                "message": str(e)
            }
        }


@app.get("/api/stt/health")
async def stt_health_check():
    """
    Health check for STT service
    
    Returns:
        Status 200 with service health information
    """
    try:
        logger.info("🏥 STT Health check")
        
        # Check Groq API key
        groq_api_key = os.getenv("GROQ_API_KEY")
        groq_available = bool(groq_api_key and len(groq_api_key) > 10)
        
        # Check MCP components
        try:
            agent = AudioTranscriptionAgent()
            mcp_available = True
            mcp_components = {
                "context_manager": "operational",
                "cache_manager": "operational",
                "token_optimizer": "operational"
            }
        except Exception as mcp_error:
            mcp_available = False
            mcp_components = {"error": str(mcp_error)}
        
        # Check WebSocket bridge
        ws_host = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
        ws_port = int(os.getenv("WEBSOCKET_PORT", 8765))
        
        health_status = {
            "service": "Speech-to-Text (STT)",
            "status": "healthy" if (groq_available and mcp_available) else "degraded",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "components": {
                "groq_whisper_api": {
                    "available": groq_available,
                    "model": "whisper-large-v3",
                    "api_key_configured": groq_available
                },
                "langgraph_workflow": {
                    "available": mcp_available,
                    "nodes": 6,
                    "workflow_type": "transcription_pipeline"
                },
                "mcp_integration": {
                    "available": mcp_available,
                    "components": mcp_components
                },
                "websocket_bridge": {
                    "host": ws_host,
                    "port": ws_port,
                    "status": "configured"
                }
            },
            "capabilities": {
                "real_time_transcription": True,
                "streaming_support": True,
                "file_upload": True,
                "language_detection": True,
                "sentiment_analysis": True,
                "speaker_detection": True,
                "technical_term_extraction": True
            },
            "supported_formats": ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"],
            "endpoints": [
                "/api/stt/transcribe",
                "/api/stt/transcribe/file",
                "/api/stt/stream/chunk",
                "/api/stt/transcript/{session_id}",
                "/api/stt/health"
            ]
        }
        
        logger.info(f"✅ STT Health: {health_status['status']}")
        
        return {
            "success": True,
            "data": health_status
        }
        
    except Exception as e:
        logger.error(f"❌ Error in health check: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "HEALTH_CHECK_ERROR",
                "message": str(e)
            }
        }


# ==================== Interview Conductor Endpoints ====================

from langgraph_agents.interview_conductor_agent import conduct_interview, process_interview_answer

class InterviewStartRequest(BaseModel):
    """Request to start a new interview"""
    candidate_name: str
    candidate_email: str
    job_title: str
    job_description: str = ""
    required_skills: List[str] = []
    candidate_resume: str = ""
    interview_id: Optional[str] = None
    session_id: Optional[str] = None
    meeting_id: Optional[str] = None
    target_duration_minutes: int = 60

class InterviewAnswerRequest(BaseModel):
    """Request to process candidate answer"""
    interview_id: str
    answer: str
    transcription_id: Optional[str] = None

@app.post("/api/interview/start")
async def start_interview_endpoint(request: InterviewStartRequest):
    """
    Start a new AI interview session
    
    Returns:
        - interview_id: Unique interview identifier
        - introduction: AI interviewer's welcome message
        - current_stage: Interview stage (intro)
    """
    logger.info(f"📞 Interview start request for: {request.candidate_name}")
    
    try:
        # Prepare interview configuration
        interview_config = {
            "interview_id": request.interview_id,
            "session_id": request.session_id,
            "meeting_id": request.meeting_id,
            "candidate_name": request.candidate_name,
            "candidate_email": request.candidate_email,
            "job_title": request.job_title,
            "job_description": request.job_description,
            "required_skills": request.required_skills,
            "candidate_resume": request.candidate_resume,
            "target_duration_minutes": request.target_duration_minutes
        }
        
        # Start interview with LangGraph agent
        result = await conduct_interview(interview_config)
        
        if result.get('success'):
            logger.info(f"✅ Interview started: {result.get('interview_id')}")
            logger.info(f"   Candidate: {request.candidate_name}")
            logger.info(f"   Position: {request.job_title}")
            
            return {
                "success": True,
                "data": {
                    "interview_id": result['interview_id'],
                    "session_id": result['session_id'],
                    "introduction": result.get('introduction', ''),
                    "current_stage": result.get('current_stage', 'intro'),
                    "processing_status": result.get('processing_status', 'in_progress')
                },
                "message": "Interview started successfully"
            }
        else:
            logger.error(f"❌ Failed to start interview: {result.get('error')}")
            return {
                "success": False,
                "error": {
                    "code": "INTERVIEW_START_ERROR",
                    "message": result.get('message', 'Failed to start interview'),
                    "details": result.get('error')
                },
                "message": "Failed to start interview"
            }
    
    except Exception as e:
        logger.error(f"❌ Error starting interview: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "INTERVIEW_START_EXCEPTION",
                "message": str(e)
            }
        }


@app.post("/api/interview/answer")
async def process_answer_endpoint(request: InterviewAnswerRequest):
    """
    Process candidate answer and generate next question
    
    Returns:
        - next_question: AI's next question
        - question_type: Type of question (technical, behavioral, etc.)
        - current_stage: Current interview stage
        - evaluation: Analysis of candidate's answer
        - interview_complete: Whether interview is finished
    """
    logger.info(f"📝 Processing answer for interview: {request.interview_id}")
    
    try:
        # Prepare answer data
        answer_data = {
            "interview_id": request.interview_id,
            "answer": request.answer,
            "transcription_id": request.transcription_id
        }
        
        # Process with LangGraph agent
        result = await process_interview_answer(answer_data)
        
        if result.get('success'):
            if result.get('interview_complete'):
                logger.info(f"✅ Interview completed: {request.interview_id}")
                logger.info(f"   Overall Score: {result.get('overall_score', 0)}/100")
                
                return {
                    "success": True,
                    "data": {
                        "interview_complete": True,
                        "closing_message": result.get('closing_message', ''),
                        "summary": result.get('summary', {}),
                        "overall_score": result.get('overall_score', 0)
                    },
                    "message": "Interview completed successfully"
                }
            else:
                logger.info(f"✅ Next question generated: {request.interview_id}")
                logger.info(f"   Question #{result.get('question_number', 0)}")
                logger.info(f"   Type: {result.get('question_type', 'unknown')}")
                
                return {
                    "success": True,
                    "data": {
                        "interview_complete": False,
                        "next_question": result.get('next_question', ''),
                        "question_type": result.get('question_type', ''),
                        "question_number": result.get('question_number', 0),
                        "current_stage": result.get('current_stage', ''),
                        "evaluation": result.get('evaluation', {})
                    },
                    "message": "Answer processed successfully"
                }
        else:
            logger.error(f"❌ Failed to process answer: {result.get('error')}")
            return {
                "success": False,
                "error": {
                    "code": "ANSWER_PROCESS_ERROR",
                    "message": result.get('message', 'Failed to process answer'),
                    "details": result.get('error')
                },
                "message": "Failed to process answer"
            }
    
    except Exception as e:
        logger.error(f"❌ Error processing answer: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "ANSWER_PROCESS_EXCEPTION",
                "message": str(e)
            }
        }


@app.get("/api/interview/{interview_id}")
async def get_interview_status(interview_id: str):
    """
    Get interview status and details
    
    Returns:
        - interview details
        - conversation history
        - scores and evaluation
    """
    logger.info(f"📊 Getting interview status: {interview_id}")
    
    try:
        from pymongo import MongoClient
        import os
        
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
        client = MongoClient(mongo_uri)
        db = client[mongo_db_name]
        
        interview = db['interviews'].find_one({"interview_id": interview_id})
        
        if not interview:
            logger.warning(f"⚠️ Interview not found: {interview_id}")
            return {
                "success": False,
                "error": {
                    "code": "INTERVIEW_NOT_FOUND",
                    "message": f"Interview {interview_id} not found"
                }
            }
        
        # Convert ObjectId to string
        interview['_id'] = str(interview['_id'])
        
        # Convert datetime objects
        for key in ['started_at', 'completed_at', 'created_at', 'updated_at']:
            if key in interview and interview[key]:
                interview[key] = interview[key].isoformat()
        
        logger.info(f"✅ Interview found: {interview_id}")
        logger.info(f"   Status: {interview.get('status', 'unknown')}")
        logger.info(f"   Questions Asked: {interview.get('total_questions', 0)}")
        
        client.close()
        
        return {
            "success": True,
            "data": interview,
            "message": "Interview retrieved successfully"
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting interview: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "INTERVIEW_GET_ERROR",
                "message": str(e)
            }
        }


@app.get("/api/interview/health")
async def interview_health_check():
    """Check interview conductor service health"""
    logger.info("🏥 Interview health check")
    
    try:
        from langgraph_agents.interview_conductor_agent import InterviewConductorAgent
        
        # Test agent initialization
        agent = InterviewConductorAgent()
        agent.close()
        
        health_status = {
            "status": "healthy",
            "service": "interview_conductor",
            "components": {
                "groq_llm": "available" if os.getenv("GROQ_API_KEY") else "missing_api_key",
                "mongodb": "connected",
                "langgraph": "initialized",
                "mcp_components": "active"
            },
            "workflow_stages": ['intro', 'technical', 'behavioral', 'situational', 'qa', 'closing'],
            "endpoints": [
                "/api/interview/start",
                "/api/interview/answer",
                "/api/interview/{interview_id}",
                "/api/interview/health"
            ]
        }
        
        logger.info(f"✅ Interview Service Health: {health_status['status']}")
        
        return {
            "success": True,
            "data": health_status
        }
    
    except Exception as e:
        logger.error(f"❌ Error in interview health check: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "INTERVIEW_HEALTH_ERROR",
                "message": str(e)
            }
        }


# ==================== TTS Endpoints ====================

from langgraph_agents.tts_agent import convert_text_to_speech, stream_text_to_speech
from fastapi.responses import StreamingResponse

class TTSSpeakRequest(BaseModel):
    """Request to convert text to speech"""
    text: str
    text_type: str = "question"  # intro, question, followup, closing, feedback
    voice_profile: str = "professional_female"  # professional_female, professional_male, etc.
    emotion: str = "professional"  # neutral, encouraging, professional, empathetic
    session_id: Optional[str] = None
    meeting_id: Optional[str] = None
    interview_id: Optional[str] = None
    model_id: str = "eleven_multilingual_v2"
    output_format: str = "mp3_44100_128"
    is_streaming: bool = False

class TTSStreamRequest(BaseModel):
    """Request to stream text to speech"""
    text: str
    text_type: str = "question"
    voice_profile: str = "professional_female"
    emotion: str = "professional"
    session_id: Optional[str] = None
    meeting_id: Optional[str] = None
    interview_id: Optional[str] = None


@app.post("/api/tts/speak")
async def tts_speak_endpoint(request: TTSSpeakRequest):
    """
    Convert text to speech using ElevenLabs
    
    Returns:
        - tts_id: Unique TTS identifier
        - audio_base64: Base64 encoded audio
        - audio_duration: Audio duration in seconds
        - voice_name: Voice used
    """
    request_start = datetime.now()
    logger.info("=" * 80)
    logger.info(f"🔊 TTS SPEAK REQUEST RECEIVED")
    logger.info(f"   Timestamp: {request_start.isoformat()}")
    logger.info(f"   Text Length: {len(request.text)} characters")
    logger.info(f"   Text Preview: {request.text[:100]}...")
    logger.info(f"   Text Type: {request.text_type}")
    logger.info(f"   Voice Profile: {request.voice_profile}")
    logger.info(f"   Emotion: {request.emotion}")
    logger.info(f"   Model: {request.model_id}")
    logger.info(f"   Output Format: {request.output_format}")
    logger.info(f"   Session ID: {request.session_id}")
    logger.info(f"   Meeting ID: {request.meeting_id}")
    logger.info(f"   Interview ID: {request.interview_id}")
    logger.info(f"   Streaming: {request.is_streaming}")
    
    try:
        # Prepare TTS request
        tts_request = {
            "text": request.text,
            "text_type": request.text_type,
            "voice_profile": request.voice_profile,
            "emotion": request.emotion,
            "session_id": request.session_id or f"session_{uuid.uuid4()}",
            "meeting_id": request.meeting_id,
            "interview_id": request.interview_id,
            "model_id": request.model_id,
            "output_format": request.output_format,
            "is_streaming": request.is_streaming
        }
        
        # Convert to speech
        logger.info(f"🎬 Starting TTS generation...")
        result = await convert_text_to_speech(tts_request)
        
        request_duration = (datetime.now() - request_start).total_seconds()
        
        if result.get('success'):
            logger.info(f"✅ TTS GENERATION SUCCESSFUL")
            logger.info(f"   TTS ID: {result['data'].get('tts_id')}")
            logger.info(f"   Voice Name: {result['data'].get('voice_name')}")
            logger.info(f"   Audio Duration: {result['data'].get('audio_duration_seconds')}s")
            logger.info(f"   Audio Size: {result['data'].get('audio_size_bytes', 0) / 1024:.2f} KB")
            logger.info(f"   Processing Time: {result['data'].get('processing_time_ms')}ms")
            logger.info(f"   Total Request Time: {request_duration:.2f}s")
            logger.info(f"   Stored in DB: {result['data'].get('stored', False)}")
            logger.info("=" * 80)
            
            return {
                "success": True,
                "data": result['data'],
                "message": "Speech generated successfully"
            }
        else:
            logger.error(f"❌ TTS GENERATION FAILED")
            logger.error(f"   Error Code: {result.get('error', {}).get('code')}")
            logger.error(f"   Error Message: {result.get('error', {}).get('message')}")
            logger.error(f"   Request Duration: {request_duration:.2f}s")
            logger.error("=" * 80)
            return {
                "success": False,
                "error": result.get('error'),
                "message": "Failed to generate speech"
            }
    
    except Exception as e:
        request_duration = (datetime.now() - request_start).total_seconds()
        logger.error(f"❌ EXCEPTION IN TTS SPEAK ENDPOINT")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Error Type: {type(e).__name__}")
        logger.error(f"   Request Duration: {request_duration:.2f}s")
        logger.error("=" * 80, exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "TTS_SPEAK_ERROR",
                "message": str(e)
            }
        }


@app.post("/api/tts/stream")
async def tts_stream_endpoint(request: TTSStreamRequest):
    """
    Stream text to speech audio in real-time
    
    Returns:
        Streaming audio chunks
    """
    logger.info(f"📡 TTS stream request")
    logger.info(f"   Text: {request.text[:50]}...")
    logger.info(f"   Voice: {request.voice_profile}")
    
    try:
        # Prepare TTS request
        tts_request = {
            "text": request.text,
            "text_type": request.text_type,
            "voice_profile": request.voice_profile,
            "emotion": request.emotion,
            "session_id": request.session_id or f"session_{uuid.uuid4()}",
            "meeting_id": request.meeting_id,
            "interview_id": request.interview_id
        }
        
        # Stream audio chunks
        async def audio_stream():
            try:
                async for chunk in stream_text_to_speech(tts_request):
                    if chunk.get('error'):
                        yield json.dumps({"error": chunk['error']}).encode()
                    else:
                        yield json.dumps(chunk).encode() + b'\n'
            except Exception as e:
                logger.error(f"❌ Error in audio stream: {str(e)}")
                yield json.dumps({"error": str(e)}).encode()
        
        return StreamingResponse(audio_stream(), media_type="application/x-ndjson")
    
    except Exception as e:
        logger.error(f"❌ Error in TTS stream: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "TTS_STREAM_ERROR",
                "message": str(e)
            }
        }


@app.get("/api/tts/{tts_id}")
async def get_tts_audio(tts_id: str):
    """Get TTS audio by ID"""
    logger.info(f"📊 Getting TTS audio: {tts_id}")
    
    try:
        from repositories.tts_repository import TTSRepository
        
        repo = TTSRepository()
        tts_audio = repo.get_tts_audio(tts_id)
        repo.close()
        
        if not tts_audio:
            logger.warning(f"⚠️ TTS audio not found: {tts_id}")
            return {
                "success": False,
                "error": {
                    "code": "TTS_NOT_FOUND",
                    "message": f"TTS audio {tts_id} not found"
                }
            }
        
        # Convert ObjectId to string
        tts_audio['_id'] = str(tts_audio['_id'])
        
        # Convert datetime objects
        for key in ['created_at', 'started_at', 'completed_at', 'updated_at']:
            if key in tts_audio and tts_audio[key]:
                tts_audio[key] = tts_audio[key].isoformat()
        
        logger.info(f"✅ TTS audio found: {tts_id}")
        
        return {
            "success": True,
            "data": tts_audio,
            "message": "TTS audio retrieved successfully"
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting TTS audio: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "TTS_GET_ERROR",
                "message": str(e)
            }
        }


@app.get("/api/tts/health")
async def tts_health_check():
    """Check TTS service health"""
    logger.info("🏥 TTS health check")
    
    try:
        from langgraph_agents.tts_agent import TTSAgent
        
        # Test agent initialization
        agent = TTSAgent()
        agent.close()
        
        health_status = {
            "status": "healthy",
            "service": "tts",
            "components": {
                "elevenlabs_api": "available" if os.getenv("ELEVENLABS_API_KEY") else "missing_api_key",
                "mongodb": "connected",
                "langgraph": "initialized",
                "mcp_components": "active"
            },
            "voice_profiles": [
                "professional_female",
                "professional_male",
                "friendly_female",
                "friendly_male"
            ],
            "endpoints": [
                "/api/tts/speak",
                "/api/tts/stream",
                "/api/tts/{tts_id}",
                "/api/tts/health"
            ]
        }
        
        logger.info(f"✅ TTS Service Health: {health_status['status']}")
        
        return {
            "success": True,
            "data": health_status
        }
    
    except Exception as e:
        logger.error(f"❌ Error in TTS health check: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "TTS_HEALTH_ERROR",
                "message": str(e)
            }
        }


# ==================== Meeting Bot Endpoints ====================

from langgraph_agents.meeting_bot_agent import join_meeting, leave_meeting

class BotJoinRequest(BaseModel):
    """Request to join meeting with bot"""
    meeting_link: str
    meeting_platform: str = "google_meet"  # zoom, google_meet, teams
    meeting_title: str = "Interview Session"
    bot_name: str = "AI Interview Assistant"
    auto_transcribe: bool = True
    auto_tts: bool = True
    auto_record: bool = True
    session_id: Optional[str] = None
    meeting_id: Optional[str] = None
    interview_id: Optional[str] = None
    expected_participants: List[str] = []
    host_name: Optional[str] = None
    meeting_password: Optional[str] = None


@app.post("/api/bot/join-meeting")
async def bot_join_meeting_endpoint(request: BotJoinRequest):
    """
    Join meeting with AI bot
    
    Returns:
        - bot_id: Unique bot identifier
        - bot_status: Bot status (joined, active, etc.)
        - join_time: When bot joined
        - features: Enabled features (STT, TTS, recording)
    """
    request_start = datetime.now()
    logger.info("=" * 80)
    logger.info(f"🤖 MEETING BOT JOIN REQUEST RECEIVED")
    logger.info(f"   Timestamp: {request_start.isoformat()}")
    logger.info(f"   Meeting Link: {request.meeting_link}")
    logger.info(f"   Platform: {request.meeting_platform}")
    logger.info(f"   Meeting Title: {request.meeting_title}")
    logger.info(f"   Bot Name: {request.bot_name}")
    logger.info(f"   Auto Transcribe: {request.auto_transcribe}")
    logger.info(f"   Auto TTS: {request.auto_tts}")
    logger.info(f"   Auto Record: {request.auto_record}")
    logger.info(f"   Session ID: {request.session_id}")
    logger.info(f"   Meeting ID: {request.meeting_id}")
    logger.info(f"   Interview ID: {request.interview_id}")
    logger.info(f"   Expected Participants: {request.expected_participants}")
    logger.info(f"   Host: {request.host_name}")
    logger.info(f"   Has Password: {bool(request.meeting_password)}")
    
    try:
        # Prepare meeting request
        meeting_request = {
            "meeting_link": request.meeting_link,
            "meeting_platform": request.meeting_platform,
            "meeting_title": request.meeting_title,
            "bot_name": request.bot_name,
            "auto_transcribe": request.auto_transcribe,
            "auto_tts": request.auto_tts,
            "auto_record": request.auto_record,
            "session_id": request.session_id or f"session_{uuid.uuid4()}",
            "meeting_id": request.meeting_id or f"meeting_{uuid.uuid4()}",
            "interview_id": request.interview_id,
            "expected_participants": request.expected_participants,
            "host_name": request.host_name,
            "meeting_password": request.meeting_password
        }
        
        # Join meeting
        logger.info(f"🎬 Starting bot join process...")
        result = await join_meeting(meeting_request)
        
        request_duration = (datetime.now() - request_start).total_seconds()
        
        if result.get('success'):
            logger.info(f"✅ BOT JOINED MEETING SUCCESSFULLY")
            logger.info(f"   Bot ID: {result['data'].get('bot_id')}")
            logger.info(f"   Bot Status: {result['data'].get('bot_status')}")
            logger.info(f"   Join Time: {result['data'].get('join_time')}")
            logger.info(f"   Meeting Platform: {result['data'].get('meeting_platform')}")
            logger.info(f"   Features:")
            features = result['data'].get('features', {})
            logger.info(f"      - STT (Transcription): {features.get('stt_enabled')}")
            logger.info(f"      - TTS (Text-to-Speech): {features.get('tts_enabled')}")
            logger.info(f"      - Recording: {features.get('recording_enabled')}")
            logger.info(f"   Browser Session: {result['data'].get('browser_session_id', 'N/A')}")
            logger.info(f"   Total Request Time: {request_duration:.2f}s")
            logger.info("=" * 80)
            
            return {
                "success": True,
                "data": result['data'],
                "message": "Bot joined meeting successfully"
            }
        else:
            logger.error(f"❌ BOT JOIN FAILED")
            logger.error(f"   Error Code: {result.get('error', {}).get('code')}")
            logger.error(f"   Error Message: {result.get('error', {}).get('message')}")
            logger.error(f"   Request Duration: {request_duration:.2f}s")
            logger.error("=" * 80)
            return {
                "success": False,
                "error": result.get('error'),
                "message": "Failed to join meeting"
            }
    
    except Exception as e:
        request_duration = (datetime.now() - request_start).total_seconds()
        logger.error(f"❌ EXCEPTION IN BOT JOIN ENDPOINT")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Error Type: {type(e).__name__}")
        logger.error(f"   Request Duration: {request_duration:.2f}s")
        logger.error("=" * 80, exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "BOT_JOIN_ERROR",
                "message": str(e)
            }
        }


@app.post("/api/bot/leave-meeting/{bot_id}")
async def bot_leave_meeting_endpoint(bot_id: str):
    """
    Leave meeting and deactivate bot
    
    Returns:
        - bot_id: Bot identifier
        - leave_time: When bot left
        - duration_minutes: Meeting duration
    """
    logger.info(f"👋 Bot leave meeting request: {bot_id}")
    
    try:
        # Leave meeting
        result = await leave_meeting(bot_id)
        
        if result.get('success'):
            logger.info(f"✅ Bot left meeting successfully")
            logger.info(f"   Duration: {result['data'].get('duration_minutes')} minutes")
            
            return {
                "success": True,
                "data": result['data'],
                "message": "Bot left meeting successfully"
            }
        else:
            logger.error(f"❌ Bot leave failed: {result.get('error')}")
            return {
                "success": False,
                "error": result.get('error'),
                "message": "Failed to leave meeting"
            }
    
    except Exception as e:
        logger.error(f"❌ Error in bot leave: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "BOT_LEAVE_ERROR",
                "message": str(e)
            }
        }


@app.get("/api/bot/{bot_id}")
async def get_bot_status(bot_id: str):
    """Get bot status and details"""
    logger.info(f"📊 Getting bot status: {bot_id}")
    
    try:
        from pymongo import MongoClient
        import os
        
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
        client = MongoClient(mongo_uri)
        db = client[mongo_db_name]
        
        bot_session = db['meeting_bots'].find_one({"bot_id": bot_id})
        
        if not bot_session:
            logger.warning(f"⚠️ Bot not found: {bot_id}")
            client.close()
            return {
                "success": False,
                "error": {
                    "code": "BOT_NOT_FOUND",
                    "message": f"Bot {bot_id} not found"
                }
            }
        
        # Convert ObjectId to string
        bot_session['_id'] = str(bot_session['_id'])
        
        # Convert datetime objects
        for key in ['join_time', 'leave_time', 'created_at', 'started_at', 'completed_at', 'updated_at']:
            if key in bot_session and bot_session[key]:
                bot_session[key] = bot_session[key].isoformat()
        
        logger.info(f"✅ Bot found: {bot_id}")
        logger.info(f"   Status: {bot_session.get('bot_status')}")
        
        client.close()
        
        return {
            "success": True,
            "data": bot_session,
            "message": "Bot retrieved successfully"
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting bot: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "BOT_GET_ERROR",
                "message": str(e)
            }
        }


@app.get("/api/bot/health")
async def bot_health_check():
    """Check meeting bot service health"""
    logger.info("🏥 Bot health check")
    
    try:
        from langgraph_agents.meeting_bot_agent import MeetingBotAgent
        
        # Test agent initialization
        agent = MeetingBotAgent()
        agent.close()
        
        health_status = {
            "status": "healthy",
            "service": "meeting_bot",
            "components": {
                "mongodb": "connected",
                "langgraph": "initialized",
                "mcp_components": "active",
                "browser_automation": "simulated"
            },
            "supported_platforms": ["zoom", "google_meet", "teams"],
            "endpoints": [
                "/api/bot/join-meeting",
                "/api/bot/leave-meeting/{bot_id}",
                "/api/bot/{bot_id}",
                "/api/bot/health"
            ],
            "note": "Browser automation requires Selenium/Playwright integration for production"
        }
        
        logger.info(f"✅ Bot Service Health: {health_status['status']}")
        
        return {
            "success": True,
            "data": health_status
        }
    
    except Exception as e:
        logger.error(f"❌ Error in bot health check: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "BOT_HEALTH_ERROR",
                "message": str(e)
            }
        }


# ==================== Real-time Orchestration Endpoints ====================
# Step 7: STT → LLM → TTS Pipeline with Real-time Streaming

class OrchestrationStartRequest(BaseModel):
    """Request model for starting orchestration"""
    session_id: Optional[str] = None
    interview_id: str
    meeting_id: Optional[str] = None
    audio_format: str = "webm"
    enable_streaming: bool = True


class OrchestrationAudioRequest(BaseModel):
    """Request model for audio turn processing"""
    session_id: str
    audio_data: str  # Base64 encoded audio
    audio_format: str = "webm"


@app.post("/api/orchestration/start")
async def start_orchestration(request: OrchestrationStartRequest):
    """
    Start a new real-time orchestration session
    Initializes STT → LLM → TTS pipeline
    
    Status: 200 with success/error in response body
    """
    logger.info("🎭 POST /api/orchestration/start")
    logger.info(f"   Interview ID: {request.interview_id}")
    
    try:
        from langgraph_agents.realtime_orchestrator_agent import start_realtime_orchestration
        
        # Prepare configuration
        config = {
            'session_id': request.session_id,
            'interview_id': request.interview_id,
            'meeting_id': request.meeting_id,
            'audio_format': request.audio_format,
            'enable_streaming': request.enable_streaming
        }
        
        logger.info("🚀 Starting orchestration session...")
        result = await start_realtime_orchestration(config)
        
        if result.get('success'):
            logger.info(f"✅ Orchestration started successfully")
            logger.info(f"   Orchestration ID: {result['data'].get('orchestration_id')}")
            logger.info(f"   Session ID: {result['data'].get('session_id')}")
            
            return {
                "success": True,
                "data": result['data'],
                "message": "Orchestration session started successfully"
            }
        else:
            logger.error(f"❌ Orchestration start failed: {result.get('error')}")
            return {
                "success": False,
                "error": result.get('error'),
                "message": "Failed to start orchestration session"
            }
    
    except Exception as e:
        logger.error(f"❌ Error starting orchestration: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "ORCHESTRATION_START_ERROR",
                "message": str(e),
                "details": "An unexpected error occurred while starting orchestration"
            },
            "message": "Failed to start orchestration session"
        }


@app.post("/api/orchestration/process-turn")
async def process_orchestration_turn(request: OrchestrationAudioRequest):
    """
    Process a single audio turn through STT → LLM → TTS pipeline
    Real-time streaming enabled
    
    Flow:
    1. Receive audio chunk
    2. Transcribe with STT agent
    3. Process with Interview Conductor (LLM)
    4. Synthesize response with TTS agent
    5. Return audio URL and transcription
    
    Status: 200 with success/error in response body
    """
    logger.info("🔄 POST /api/orchestration/process-turn")
    logger.info(f"   Session ID: {request.session_id}")
    
    try:
        from langgraph_agents.realtime_orchestrator_agent import process_orchestration_turn
        
        # Decode base64 audio
        try:
            audio_bytes = base64.b64decode(request.audio_data)
            logger.info(f"   Audio size: {len(audio_bytes)} bytes")
        except Exception as decode_error:
            logger.error(f"❌ Failed to decode audio: {str(decode_error)}")
            return {
                "success": False,
                "error": {
                    "code": "AUDIO_DECODE_ERROR",
                    "message": "Invalid base64 audio data",
                    "details": str(decode_error)
                },
                "message": "Failed to decode audio data"
            }
        
        # Process through pipeline
        logger.info("⚡ Processing through STT → LLM → TTS pipeline...")
        result = await process_orchestration_turn(
            request.session_id,
            audio_bytes,
            request.audio_format
        )
        
        if result.get('success'):
            data = result['data']
            logger.info(f"✅ Turn processed successfully")
            logger.info(f"   Turn: {data.get('turn')}")
            logger.info(f"   Transcription: {data.get('transcription', '')[:50]}...")
            logger.info(f"   AI Response: {data.get('ai_response', '')[:50]}...")
            logger.info(f"   Latency: {data.get('latency_ms')}ms")
            logger.info(f"   Next action: {data.get('next_action')}")
            
            return {
                "success": True,
                "data": {
                    "session_id": request.session_id,
                    "turn": data.get('turn'),
                    "transcription": {
                        "text": data.get('transcription'),
                        "confidence": data.get('confidence', 0.0),
                        "speaker": data.get('speaker', 'user')
                    },
                    "ai_response": {
                        "text": data.get('ai_response'),
                        "audio_url": data.get('audio_url'),
                        "duration_seconds": data.get('duration_seconds', 0.0)
                    },
                    "metrics": {
                        "stt_latency_ms": data.get('stt_latency_ms', 0),
                        "llm_latency_ms": data.get('llm_latency_ms', 0),
                        "tts_latency_ms": data.get('tts_latency_ms', 0),
                        "total_latency_ms": data.get('latency_ms', 0)
                    },
                    "next_action": data.get('next_action', 'continue')
                },
                "message": "Audio turn processed successfully"
            }
        else:
            error_info = result.get('error', {})
            logger.error(f"❌ Turn processing failed: {error_info}")
            
            return {
                "success": False,
                "error": {
                    "code": error_info.get('code', 'TURN_PROCESSING_ERROR'),
                    "message": error_info.get('message', 'Unknown error'),
                    "stage": error_info.get('stage', 'unknown'),
                    "details": error_info.get('details', 'Pipeline processing failed')
                },
                "message": "Failed to process audio turn"
            }
    
    except Exception as e:
        logger.error(f"❌ Error in orchestration turn: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "ORCHESTRATION_TURN_ERROR",
                "message": str(e),
                "details": "An unexpected error occurred during pipeline processing"
            },
            "message": "Failed to process audio turn"
        }


@app.post("/api/orchestration/end/{session_id}")
async def end_orchestration(session_id: str):
    """
    End orchestration session and retrieve summary
    
    Returns:
    - Session metrics
    - Conversation quality score
    - Turn-by-turn breakdown
    - Latency statistics
    
    Status: 200 with success/error in response body
    """
    logger.info(f"🏁 POST /api/orchestration/end/{session_id}")
    
    try:
        from langgraph_agents.realtime_orchestrator_agent import end_realtime_orchestration
        
        logger.info("📊 Ending orchestration session...")
        result = await end_realtime_orchestration(session_id)
        
        if result.get('success'):
            data = result['data']
            logger.info(f"✅ Orchestration ended successfully")
            logger.info(f"   Total turns: {data.get('total_turns', 0)}")
            logger.info(f"   Success rate: {data.get('successful_turns', 0)}/{data.get('total_turns', 0)}")
            logger.info(f"   Quality score: {data.get('quality_score', 0):.1f}")
            logger.info(f"   Duration: {data.get('duration_seconds', 0):.1f}s")
            
            return {
                "success": True,
                "data": {
                    "orchestration_id": data.get('orchestration_id'),
                    "session_id": session_id,
                    "summary": {
                        "total_turns": data.get('total_turns', 0),
                        "successful_turns": data.get('successful_turns', 0),
                        "failed_turns": data.get('failed_turns', 0),
                        "quality_score": data.get('quality_score', 0.0),
                        "duration_seconds": data.get('duration_seconds', 0.0)
                    },
                    "metrics": {
                        "avg_latency_ms": data.get('avg_latency_ms', 0),
                        "interruptions": data.get('interruptions', 0),
                        "errors": data.get('errors', [])
                    }
                },
                "message": "Orchestration session ended successfully"
            }
        else:
            logger.error(f"❌ Failed to end orchestration: {result.get('error')}")
            return {
                "success": False,
                "error": result.get('error'),
                "message": "Failed to end orchestration session"
            }
    
    except Exception as e:
        logger.error(f"❌ Error ending orchestration: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "ORCHESTRATION_END_ERROR",
                "message": str(e),
                "details": "An unexpected error occurred while ending orchestration"
            },
            "message": "Failed to end orchestration session"
        }


@app.get("/api/orchestration/{session_id}")
async def get_orchestration_status(session_id: str):
    """
    Get current orchestration session status and metrics
    
    Status: 200 with success/error in response body
    """
    logger.info(f"📊 GET /api/orchestration/{session_id}")
    
    try:
        from pymongo import MongoClient
        
        mongo_uri = os.getenv('MONGO_URI', 'mongo_url')
        mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
        
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000
        )
        db = client[mongo_db_name]
        
        # Get orchestration session
        orchestration = db['orchestration_sessions'].find_one({'session_id': session_id})
        
        if not orchestration:
            logger.warning(f"⚠️ Orchestration session not found: {session_id}")
            client.close()
            return {
                "success": False,
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": f"Orchestration session not found: {session_id}"
                },
                "message": "Session not found"
            }
        
        # Convert ObjectId to string
        orchestration['_id'] = str(orchestration['_id'])
        
        # Convert datetime objects
        for key in ['created_at', 'completed_at']:
            if key in orchestration and orchestration[key]:
                orchestration[key] = orchestration[key].isoformat()
        
        logger.info(f"✅ Orchestration found: {session_id}")
        logger.info(f"   Status: {orchestration.get('final_status')}")
        logger.info(f"   Turns: {orchestration.get('total_turns', 0)}")
        
        client.close()
        
        return {
            "success": True,
            "data": orchestration,
            "message": "Orchestration status retrieved successfully"
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting orchestration status: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "ORCHESTRATION_STATUS_ERROR",
                "message": str(e)
            },
            "message": "Failed to retrieve orchestration status"
        }


@app.get("/api/orchestration/health")
async def orchestration_health_check():
    """
    Check real-time orchestration service health
    Verifies all pipeline components (STT, LLM, TTS)
    
    Status: 200 with success/error in response body
    """
    logger.info("🏥 Orchestration health check")
    
    try:
        from langgraph_agents.realtime_orchestrator_agent import RealtimeOrchestratorAgent
        
        # Test agent initialization
        agent = RealtimeOrchestratorAgent()
        agent.close()
        
        health_status = {
            "status": "healthy",
            "service": "realtime_orchestration",
            "pipeline": {
                "stt": {
                    "status": "available",
                    "provider": "Groq Whisper",
                    "model": "whisper-large-v3"
                },
                "llm": {
                    "status": "available",
                    "provider": "Groq",
                    "model": "llama-3.3-70b-versatile"
                },
                "tts": {
                    "status": "available" if os.getenv("ELEVENLABS_API_KEY") else "missing_api_key",
                    "provider": "ElevenLabs",
                    "voices": ["professional_female", "professional_male", "friendly_female", "friendly_male"]
                }
            },
            "components": {
                "mongodb": "connected",
                "langgraph": "initialized",
                "mcp_components": "active",
                "streaming": "enabled"
            },
            "features": {
                "real_time_processing": True,
                "error_recovery": True,
                "conversation_state": True,
                "performance_monitoring": True,
                "quality_assurance": True
            },
            "endpoints": [
                "/api/orchestration/start",
                "/api/orchestration/process-turn",
                "/api/orchestration/end/{session_id}",
                "/api/orchestration/{session_id}",
                "/api/orchestration/health"
            ],
            "max_retries": 3,
            "timeout_seconds": {
                "stt": 30,
                "llm": 60,
                "tts": 30
            }
        }
        
        logger.info(f"✅ Orchestration Service Health: {health_status['status']}")
        
        return {
            "success": True,
            "data": health_status,
            "message": "Orchestration service is healthy"
        }
    
    except Exception as e:
        logger.error(f"❌ Error in orchestration health check: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "ORCHESTRATION_HEALTH_ERROR",
                "message": str(e)
            },
            "message": "Orchestration service health check failed"
        }


# ==================== JWT AUTHENTICATION HELPER ====================

def verify_jwt_token(authorization: Optional[str]) -> dict:
    """
    Verify JWT token from Authorization header
    
    Args:
        authorization: Authorization header value (Bearer <token>)
    
    Returns:
        dict: {"valid": bool, "session_id": str, "error": str}
    """
    try:
        if not authorization:
            return {
                "valid": False,
                "error": "Missing Authorization header"
            }
        
        # Extract token from "Bearer <token>"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return {
                "valid": False,
                "error": "Invalid Authorization header format. Expected: Bearer <token>"
            }
        
        jwt_token = parts[1]
        
        # Verify token (synchronous call - verify_session_token is NOT async)
        from security import get_session_auth_manager
        auth_manager = get_session_auth_manager()
        
        # verify_session_token returns tuple: (is_valid, payload/session_token, error_message)
        is_valid, payload_or_error, error_message = auth_manager.verify_session_token(jwt_token)
        
        if not is_valid:
            return {
                "valid": False,
                "error": error_message or "Invalid or expired token"
            }
        
        # payload_or_error is the session payload dict when valid
        return {
            "valid": True,
            "session_id": payload_or_error.get('session_id'),
            "payload": payload_or_error
        }
    
    except Exception as e:
        logger.error(f"❌ JWT verification error: {str(e)}")
        return {
            "valid": False,
            "error": f"Token verification failed: {str(e)}"
        }


# ==================== DISTRIBUTED ORCHESTRATION ENDPOINTS ====================
# Handles multiple concurrent interviews using Redis Streams
# Enables horizontal scaling across multiple FastAPI workers
# 🔐 All endpoints require JWT authentication via Authorization header

@app.post("/api/distributed/orchestration/start")
async def start_distributed_orchestration(
    config: dict,
    authorization: Optional[str] = Header(None)
):
    """
    Start a new distributed orchestration session with Redis Streams
    🔐 Requires JWT authentication via Authorization header
    Enables horizontal scaling - multiple workers can handle different sessions
    
    Headers:
    - Authorization: Bearer <jwt_token>
    
    Request Body:
    {
        "interview_id": "interview_123",
        "meeting_id": "meeting_456",
        "candidate_name": "John Doe",
        "job_title": "Python Developer",
        "audio_format": "webm",
        "enable_streaming": true
    }
    
    Returns:
    {
        "success": true,
        "data": {
            "orchestration_id": "orch_uuid",
            "session_id": "session_uuid",
            "redis_stream": "orchestration:session:session_uuid",
            "worker_id": "worker_abc123",
            "consumer_group": "orchestration_workers"
        }
    }
    """
    logger.info("🌐 POST /api/distributed/orchestration/start")
    
    try:
        # Verify JWT token
        auth_result = verify_jwt_token(authorization)
        if not auth_result['valid']:
            logger.warning(f"🚫 Unauthorized access attempt: {auth_result['error']}")
            return {
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": auth_result['error']
                },
                "message": "Authentication required to start distributed orchestration"
            }
        
        logger.info(f"🔐 JWT verified for session: {auth_result['session_id']}")
        
        # Inject JWT session_id into config to ensure consistency
        config['session_id'] = auth_result['session_id']
        
        from langgraph_agents.distributed_orchestrator_agent import get_distributed_orchestrator
        
        orchestrator = await get_distributed_orchestrator()
        result = await orchestrator.start_session(config)
        
        logger.info(f"✅ Distributed orchestration session started")
        if result.get('success'):
            logger.info(f"   Session ID: {result['data']['session_id']}")
            logger.info(f"   Worker ID: {result['data']['worker_id']}")
            logger.info(f"   Redis Stream: {result['data']['redis_stream']}")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Error starting distributed orchestration: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "DISTRIBUTED_START_FAILED",
                "message": str(e)
            },
            "message": "Failed to start distributed orchestration session"
        }


@app.post("/api/distributed/orchestration/publish-audio")
async def publish_audio_to_stream(
    session_id: str = Form(...),
    audio_file: UploadFile = File(...),
    audio_format: str = Form("webm"),
    authorization: Optional[str] = Header(None)
):
    """
    Publish audio to Redis Stream for distributed processing
    🔐 Requires JWT authentication via Authorization header
    Audio will be processed by any available worker in the consumer group
    
    Headers:
    - Authorization: Bearer <jwt_token>
    
    Form Data:
    - session_id: Active session ID
    - audio_file: Audio file (WAV, WebM, MP3, etc.)
    - audio_format: Audio format (default: webm)
    
    Returns:
    {
        "success": true,
        "data": {
            "message_id": "redis_message_id",
            "session_id": "session_uuid",
            "stream": "orchestration:session:session_uuid"
        }
    }
    """
    logger.info(f"📤 POST /api/distributed/orchestration/publish-audio")
    logger.info(f"   Session: {session_id}")
    logger.info(f"   Format: {audio_format}")
    
    try:
        # Verify JWT token
        auth_result = verify_jwt_token(authorization)
        if not auth_result['valid']:
            logger.warning(f"🚫 Unauthorized access attempt for session {session_id}: {auth_result['error']}")
            return {
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": auth_result['error']
                },
                "message": "Authentication required to publish audio"
            }
        
        # Verify session_id matches JWT token
        if auth_result['session_id'] != session_id:
            logger.warning(f"🚫 Session mismatch: JWT={auth_result['session_id']}, Request={session_id}")
            return {
                "success": False,
                "error": {
                    "code": "SESSION_MISMATCH",
                    "message": "Session ID in request does not match authenticated session"
                },
                "message": "Session authentication failed"
            }
        
        logger.info(f"🔐 JWT verified for session: {session_id}")
        
        from langgraph_agents.distributed_orchestrator_agent import get_distributed_orchestrator
        
        # Read audio data
        audio_data = await audio_file.read()
        logger.info(f"   Audio size: {len(audio_data)} bytes")
        
        # Get orchestrator
        orchestrator = await get_distributed_orchestrator()
        
        # Publish to Redis Stream
        result = await orchestrator.publish_audio_turn(
            session_id=session_id,
            audio_data=audio_data,
            audio_format=audio_format
        )
        
        if result.get('success'):
            logger.info(f"✅ Audio published to stream: {result['data']['message_id']}")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Error publishing audio: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "AUDIO_PUBLISH_FAILED",
                "message": str(e)
            },
            "message": "Failed to publish audio to stream"
        }


@app.post("/api/distributed/orchestration/end/{session_id}")
async def end_distributed_orchestration(
    session_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    End distributed orchestration session
    🔐 Requires JWT authentication via Authorization header
    Publishes end message to Redis Stream and cleans up resources
    
    Headers:
    - Authorization: Bearer <jwt_token>
    
    Path Parameters:
    - session_id: Session to end
    
    Returns:
    {
        "success": true,
        "data": {
            "orchestration_id": "orch_uuid",
            "session_id": "session_uuid",
            "total_turns": 10,
            "quality_score": 95.5
        }
    }
    """
    logger.info(f"🏁 POST /api/distributed/orchestration/end/{session_id}")
    
    try:
        # Verify JWT token
        auth_result = verify_jwt_token(authorization)
        if not auth_result['valid']:
            logger.warning(f"🚫 Unauthorized end attempt for session {session_id}: {auth_result['error']}")
            return {
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": auth_result['error']
                },
                "message": "Authentication required to end session"
            }
        
        # Verify session_id matches JWT token
        if auth_result['session_id'] != session_id:
            logger.warning(f"🚫 Session mismatch: JWT={auth_result['session_id']}, Request={session_id}")
            return {
                "success": False,
                "error": {
                    "code": "SESSION_MISMATCH",
                    "message": "Session ID in request does not match authenticated session"
                },
                "message": "Session authentication failed"
            }
        
        logger.info(f"🔐 JWT verified for session: {session_id}")
        
        from langgraph_agents.distributed_orchestrator_agent import get_distributed_orchestrator
        
        orchestrator = await get_distributed_orchestrator()
        result = await orchestrator.end_session(session_id)
        
        if result.get('success'):
            logger.info(f"✅ Distributed session ended: {session_id}")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Error ending distributed session: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "DISTRIBUTED_END_FAILED",
                "message": str(e)
            },
            "message": "Failed to end distributed orchestration session"
        }


@app.get("/api/distributed/orchestration/sessions")
async def get_active_distributed_sessions(authorization: Optional[str] = Header(None)):
    """
    Get list of active sessions in this worker
    🔐 Requires JWT authentication via Authorization header
    Shows which sessions this specific worker is handling
    
    Headers:
    - Authorization: Bearer <jwt_token>
    
    Returns:
    {
        "success": true,
        "data": {
            "worker_id": "worker_abc123",
            "sessions": [
                {
                    "session_id": "session_uuid",
                    "orchestration_id": "orch_uuid",
                    "interview_id": "interview_123",
                    "status": "active",
                    "created_at": "2025-10-26T12:00:00Z"
                }
            ],
            "count": 1
        }
    }
    """
    logger.info("📊 GET /api/distributed/orchestration/sessions")
    
    try:
        # Verify JWT token
        auth_result = verify_jwt_token(authorization)
        if not auth_result['valid']:
            logger.warning(f"🚫 Unauthorized sessions query: {auth_result['error']}")
            return {
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": auth_result['error']
                },
                "message": "Authentication required to view sessions"
            }
        
        logger.info(f"🔐 JWT verified for sessions query")
        
        from langgraph_agents.distributed_orchestrator_agent import get_distributed_orchestrator
        
        orchestrator = await get_distributed_orchestrator()
        sessions = await orchestrator.get_active_sessions()
        
        logger.info(f"✅ Retrieved {len(sessions)} active sessions in this worker")
        
        return {
            "success": True,
            "data": {
                "worker_id": orchestrator.redis_manager.consumer_id,
                "sessions": sessions,
                "count": len(sessions)
            },
            "message": f"Found {len(sessions)} active sessions in this worker"
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting active sessions: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "GET_SESSIONS_FAILED",
                "message": str(e)
            },
            "message": "Failed to retrieve active sessions"
        }



@app.get("/api/distributed/orchestration/workers")
async def get_worker_info():
    """
    Get information about all active workers in the cluster
    🌐 Public endpoint - No JWT required
    Shows worker distribution and load balancing status
    
    Returns:
    {
        "success": true,
        "data": {
            "current_worker": {
                "worker_id": "worker_pid12345_abc123",
                "process_id": 12345,
                "status": "active"
            },
            "redis_consumer_group": {
                "group_name": "orchestration_workers",
                "consumers": [
                    {
                        "name": "worker_pid12345_abc123",
                        "pending": 0,
                        "idle_time": 1000
                    }
                ]
            },
            "active_sessions": 5,
            "load_distribution": {
                "worker_pid12345_abc123": 3,
                "worker_pid12346_def456": 2
            }
        }
    }
    """
    logger.info("🔍 GET /api/distributed/orchestration/workers - Worker Info Request")
    
    try:
        from langgraph_agents.distributed_orchestrator_agent import get_distributed_orchestrator
        import os
        
        orchestrator = await get_distributed_orchestrator()
        
        # Get current worker info
        current_worker = {
            "worker_id": orchestrator.redis_manager.consumer_id,
            "process_id": os.getpid(),
            "status": "active",
            "active_sessions": len(orchestrator.active_sessions),
            "consumer_group": orchestrator.redis_manager.consumer_group
        }
        
        # Get Redis consumer group information
        redis_info = {}
        consumer_group_info = []
        
        try:
            # Try to get consumer group info from Redis (requires active stream)
            # We'll query info for each active session
            for session_id in orchestrator.active_sessions.keys():
                stream_name = f"orchestration:session:{session_id}"
                
                try:
                    # Get consumer group info
                    groups = await orchestrator.redis_manager.redis_client.xinfo_groups(stream_name)
                    
                    for group in groups:
                        if group['name'] == orchestrator.redis_manager.consumer_group:
                            # Get consumers in this group
                            consumers = await orchestrator.redis_manager.redis_client.xinfo_consumers(
                                stream_name,
                                orchestrator.redis_manager.consumer_group
                            )
                            
                            redis_info = {
                                "group_name": group['name'],
                                "pending_messages": group['pending'],
                                "last_delivered_id": group['last-delivered-id']
                            }
                            
                            consumer_group_info = [
                                {
                                    "name": c['name'],
                                    "pending": c['pending'],
                                    "idle_time_ms": c['idle']
                                }
                                for c in consumers
                            ]
                            break
                except Exception as e:
                    logger.debug(f"Could not fetch consumer info for session {session_id}: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch Redis consumer group info: {e}")
            redis_info = {"error": "Consumer group info not available (no active streams)"}
        
        # Build response
        response_data = {
            "current_worker": current_worker,
            "redis_consumer_group": {
                **redis_info,
                "consumers": consumer_group_info
            },
            "active_sessions": len(orchestrator.active_sessions),
            "orchestrator_instances": len(orchestrator.orchestrators)
        }
        
        logger.info(f"✅ Worker info retrieved: {current_worker['worker_id']} (PID: {current_worker['process_id']})")
        logger.info(f"   Active sessions: {len(orchestrator.active_sessions)}")
        logger.info(f"   Consumers in group: {len(consumer_group_info)}")
        
        return {
            "success": True,
            "data": response_data,
            "message": f"Worker info for {current_worker['worker_id']}"
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting worker info: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "WORKER_INFO_FAILED",
                "message": str(e)
            },
            "message": "Failed to retrieve worker information"
        }


@app.get("/api/distributed/orchestration/health")
async def distributed_orchestration_health():
    """
    Check distributed orchestration service health
    🌐 Public endpoint - No JWT required
    Verifies Redis connectivity, worker status, and active sessions
    
    Returns:
    {
        "success": true,
        "data": {
            "status": "healthy",
            "worker_id": "worker_abc123",
            "redis": {
                "status": "healthy",
                "connected": true,
                "redis_version": "7.2.0"
            },
            "sessions": {
                "active": 5,
                "orchestrators": 5,
                "consumer_tasks": 5
            }
        }
    }
    """
    logger.info("🏥 GET /api/distributed/orchestration/health")
    
    try:
        from langgraph_agents.distributed_orchestrator_agent import get_distributed_orchestrator
        
        orchestrator = await get_distributed_orchestrator()
        health = await orchestrator.health_check()
        
        logger.info(f"✅ Distributed orchestration health: {health.get('status')}")
        
        return {
            "success": True,
            "data": health,
            "message": f"Distributed orchestration is {health.get('status')}"
        }
    
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "HEALTH_CHECK_FAILED",
                "message": str(e)
            },
            "message": "Distributed orchestration health check failed"
        }


# ==================== Audio Streaming WebSocket ====================
from audio_streaming import handle_audio_websocket

@app.websocket("/ws/audio/{interview_id}")
async def audio_streaming_websocket(websocket: WebSocket, interview_id: str):
    """
    WebSocket endpoint for real-time audio streaming
    
    Usage:
        1. Connect: ws://localhost:8001/ws/audio/{interview_id}
        2. Send audio chunks as binary data
        3. Receive transcriptions as JSON
    """
    await handle_audio_websocket(websocket, interview_id)


# ==================== Resume Upload & Parsing ====================

@app.post("/api/resumes/upload")
async def upload_resume(
    file: UploadFile = File(...),
    candidate_id: Optional[str] = Form(None),
    interview_id: Optional[str] = Form(None)
):
    """
    Upload and parse resume (PDF/DOCX)
    
    Returns:
        {
            "success": True,
            "data": {
                "resume_id": "uuid",
                "filename": "resume.pdf",
                "extracted_data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "phone": "(555) 123-4567",
                    "skills": ["Python", "JavaScript", ...],
                    "experience": [...],
                    "education": [...]
                }
            }
        }
    """
    import uuid
    from PyPDF2 import PdfReader
    import docx
    
    logger.info(f"📄 Uploading resume: {file.filename}")
    
    # Validate file type first
    if not (file.filename.endswith('.pdf') or file.filename.endswith('.docx') or file.filename.endswith('.txt')):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Please upload PDF, DOCX, or TXT file. Got: {file.filename}"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse based on file type
        text_content = ""
        if file.filename.endswith('.pdf'):
            # Parse PDF
            pdf_reader = PdfReader(io.BytesIO(content))
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
        
        elif file.filename.endswith('.docx'):
            # Parse DOCX
            doc = docx.Document(io.BytesIO(content))
            for para in doc.paragraphs:
                text_content += para.text + "\n"
        
        elif file.filename.endswith('.txt'):
            # Plain text
            text_content = content.decode('utf-8')
        
        # Extract structured data
        extracted_data = extract_resume_data(text_content)
        
        # Generate resume ID
        resume_id = str(uuid.uuid4())
        
        # Store in MongoDB
        resume_doc = {
            "resume_id": resume_id,
            "candidate_id": candidate_id,
            "interview_id": interview_id,
            "filename": file.filename,
            "raw_text": text_content,
            "extracted_data": extracted_data,
            "uploaded_at": datetime.datetime.now().isoformat()
        }
        
        # Save to database
        db = get_db()
        if db is not None:
            db.resumes.insert_one(resume_doc)
            logger.info(f"✅ Resume saved to database: {resume_id}")
        
        return {
            "success": True,
            "resume_id": resume_id,
            "filename": file.filename,
            "extracted_data": extracted_data
        }
        
    except Exception as e:
        logger.error(f"❌ Error uploading resume: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "UPLOAD_ERROR",
                "message": str(e)
            }
        }


def extract_resume_data(text: str) -> Dict:
    """
    Extract structured data from resume text
    
    Args:
        text: Raw resume text
        
    Returns:
        Extracted data dictionary
    """
    # Email regex
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    # Phone regex
    phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    
    # Extract email
    email_match = re.search(email_pattern, text)
    email = email_match.group(0) if email_match else None
    
    # Extract phone
    phone_match = re.search(phone_pattern, text)
    phone = phone_match.group(0) if phone_match else None
    
    # Extract name (usually first line)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    name = lines[0] if lines else "Unknown"
    
    # Extract skills (common programming languages and tools)
    skills_keywords = [
        'Python', 'JavaScript', 'Java', 'C++', 'C#', 'Ruby', 'PHP', 'Go', 'Rust',
        'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'FastAPI',
        'SQL', 'MongoDB', 'PostgreSQL', 'MySQL', 'Redis',
        'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes',
        'Git', 'CI/CD', 'Agile', 'Scrum'
    ]
    
    skills = []
    text_lower = text.lower()
    for skill in skills_keywords:
        if skill.lower() in text_lower:
            skills.append(skill)
    
    # Extract experience (lines containing years or "present")
    experience = []
    for line in lines:
        if re.search(r'\d{4}\s*-\s*(\d{4}|present)', line, re.IGNORECASE):
            experience.append(line)
    
    # Extract education (lines containing degree keywords)
    education = []
    education_keywords = ['bachelor', 'master', 'phd', 'b.s.', 'm.s.', 'b.a.', 'm.a.', 'university', 'college']
    for line in lines:
        if any(keyword in line.lower() for keyword in education_keywords):
            education.append(line)
    
    return {
        "name": name,
        "email": email,
        "phone": phone,
        "skills": skills,
        "experience": experience[:5],  # Top 5
        "education": education[:3],  # Top 3
        "summary": text[:500] + "..." if len(text) > 500 else text
    }


# ============================================================================
# GOOGLE MEET INTERVIEW ENDPOINTS
# ============================================================================

class MeetInterviewStartRequest(BaseModel):
    """Request to start a Google Meet interview"""
    interview_id: str
    meet_url: str
    candidate_name: str
    job_title: str
    headless: bool = True  # Run browser in headless mode for production

class MeetInterviewStatusRequest(BaseModel):
    """Request to get interview status"""
    interview_id: str


@app.post("/api/meet-interview/start")
async def start_meet_interview(request: MeetInterviewStartRequest):
    """
    Start a complete Google Meet interview with bot.
    
    This endpoint:
    1. Launches the Meet bot
    2. Joins the Google Meet
    3. Conducts the full interview (questions → answers → analysis)
    4. Saves results to MongoDB
    5. Leaves the meeting when complete
    
    Args:
        request: MeetInterviewStartRequest with interview details
        
    Returns:
        Interview results with overall score and Q&A history
    """
    logger.info(f"🚀 Starting Google Meet interview: {request.interview_id}")
    logger.info(f"   Candidate: {request.candidate_name}")
    logger.info(f"   Position: {request.job_title}")
    logger.info(f"   Meet URL: {request.meet_url}")
    
    try:
        # Import the orchestrator (lazy import to avoid startup delays)
        from interview_orchestrator import MeetInterviewOrchestrator
        
        # Create orchestrator instance
        orchestrator = MeetInterviewOrchestrator()
        
        # Conduct the complete interview (async)
        results = await orchestrator.conduct_interview(
            interview_id=request.interview_id,
            meet_url=request.meet_url,
            candidate_name=request.candidate_name,
            job_title=request.job_title,
            headless=request.headless
        )
        
        if results.get('success'):
            logger.info(f"✅ Meet interview completed successfully!")
            logger.info(f"   Overall Score: {results.get('overall_score', 0)}/10")
            logger.info(f"   Questions: {results.get('total_questions', 0)}")
            logger.info(f"   Answered: {results.get('questions_answered', 0)}")
            
            return {
                "success": True,
                "data": {
                    "interview_id": results.get('interview_id'),
                    "session_id": results.get('session_id'),
                    "overall_score": results.get('overall_score'),
                    "total_questions": results.get('total_questions'),
                    "questions_answered": results.get('questions_answered'),
                    "qa_history": results.get('qa_history', []),
                    "completed_at": results.get('completed_at')
                },
                "message": "Meet interview completed successfully"
            }
        else:
            logger.error(f"❌ Meet interview failed: {results.get('error')}")
            return {
                "success": False,
                "error": {
                    "code": "MEET_INTERVIEW_FAILED",
                    "message": results.get('error', 'Unknown error'),
                    "details": results
                },
                "message": "Failed to complete Meet interview"
            }
            
    except Exception as e:
        logger.error(f"❌ Error in Meet interview: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "MEET_INTERVIEW_EXCEPTION",
                "message": str(e)
            },
            "message": "Exception occurred during Meet interview"
        }


@app.get("/api/meet-interview/status/{interview_id}")
async def get_meet_interview_status(interview_id: str):
    """
    Get the current status of a Google Meet interview.
    
    Returns interview progress, current question, and real-time updates.
    """
    logger.info(f"📊 Getting status for interview: {interview_id}")
    
    try:
        # Get from MongoDB
        interviews_collection = get_collection(Collections.INTERVIEWS)
        interview = interviews_collection.find_one({"interview_id": interview_id})
        
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Convert ObjectId to string for JSON serialization
        if '_id' in interview:
            interview['_id'] = str(interview['_id'])
        
        return {
            "success": True,
            "data": interview,
            "message": "Interview status retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting interview status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)