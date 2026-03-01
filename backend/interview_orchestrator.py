"""
Google Meet Interview Orchestrator - Complete End-to-End Interview Flow

This orchestrates the COMPLETE interview process in Google Meet:
1. Authenticate bot → Join meeting
2. Load interview questions from MongoDB
3. Play TTS questions through Meet audio
4. Record candidate answers via Meet audio
5. Transcribe with STT (Groq Whisper)
6. Analyze with LLM (Groq llama-3.3-70b)
7. Save results to MongoDB
8. Leave meeting when complete

Integrates:
- meet_bot_launcher.py (Authentication)
- meet_bot_joiner.py (Join meeting)
- meet_audio_integration.py (Audio I/O)
- TTSAgent (Question speech)
- AudioTranscriptionAgent (Answer STT)
- QAAgent (Answer analysis)
- InterviewRepository (Database)

Author: AI Recruiter Team
Created: February 2026
"""

import asyncio
import logging
import os
import json
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv

# Meet bot components
from meet_bot_launcher import GoogleMeetAuth
from meet_bot_joiner import MeetBotJoiner
from meet_audio_integration import MeetAudioIntegration

# LangGraph agents
from langgraph_agents.tts_agent import TTSAgent
from langgraph_agents.audio_transcription_agent import AudioTranscriptionAgent

# Groq for LLM analysis
from groq import Groq

# MongoDB
from repositories.interview_repository import InterviewRepository
from repositories.question_repository import QuestionRepository
from repositories.qa_repository import QARepository

# MCP components
from mcp.context_manager import MCPContextManager
from mcp.cache_manager import MCPCacheManager

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InterviewStage(Enum):
    """Interview stages"""
    INIT = "initializing"
    JOINING = "joining_meeting"
    GREETING = "greeting"
    QUESTIONING = "questioning"
    WAITING_ANSWER = "waiting_for_answer"
    ANALYZING = "analyzing_answer"
    COMPLETING = "completing"
    FINISHED = "finished"
    ERROR = "error"


class MeetInterviewOrchestrator:
    """
    Complete Google Meet interview orchestrator.
    
    Handles full interview lifecycle from joining Meet to saving results.
    """
    
    def __init__(self):
        """Initialize orchestrator with all components"""
        logger.info("🎯 Initializing Meet Interview Orchestrator")
        
        # Credentials
        self.bot_email = os.getenv('MEET_BOT_EMAIL')
        self.bot_password = os.getenv('MEET_BOT_PASSWORD')
        
        # Meet bot components
        self.auth: Optional[GoogleMeetAuth] = None
        self.joiner: Optional[MeetBotJoiner] = None
        self.audio: Optional[MeetAudioIntegration] = None
        
        # AI agents
        self.tts_agent = TTSAgent()
        self.stt_agent = AudioTranscriptionAgent()
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        
        # Repositories
        self.interview_repo = InterviewRepository()
        self.question_repo = QuestionRepository()
        self.qa_repo = QARepository()
        
        # MCP components
        self.context_manager = MCPContextManager()
        self.cache_manager = MCPCacheManager()
        
        # Interview state
        self.interview_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.qa_session_id: Optional[str] = None  # MongoDB QA session ObjectId
        self.stage = InterviewStage.INIT
        self.questions: List[Dict] = []
        self.current_question_index = 0
        self.qa_history: List[Dict] = []
        self.overall_score = 0.0
        
        logger.info("✅ Meet Interview Orchestrator initialized")
    
    async def conduct_interview(
        self,
        interview_id: str,
        meet_url: str,
        candidate_name: str,
        job_title: str,
        headless: bool = False
    ) -> Dict[str, Any]:
        """
        Conduct complete interview in Google Meet.
        
        Args:
            interview_id: Interview ID from database
            meet_url: Google Meet URL
            candidate_name: Candidate's name
            job_title: Position being interviewed for
            headless: Run browser in headless mode
            
        Returns:
            Dict with interview results
        """
        logger.info(f"🚀 Starting interview: {interview_id}")
        logger.info(f"   Candidate: {candidate_name}")
        logger.info(f"   Position: {job_title}")
        logger.info(f"   Meet URL: {meet_url}")
        
        try:
            self.interview_id = interview_id
            self.session_id = f"session_{interview_id}_{int(datetime.now().timestamp())}"
            
            # Step 1: Join Google Meet
            await self._join_meeting(meet_url, headless)
            
            # Step 2: Load interview questions
            await self._load_questions(job_title)
            
            # Step 3: Greet candidate
            await self._greet_candidate(candidate_name)
            
            # Step 4: Conduct Q&A loop
            await self._qa_loop()
            
            # Step 5: Closing & thank you
            await self._close_interview(candidate_name)
            
            # Step 6: Leave meeting
            await self._leave_meeting()
            
            # Step 7: Calculate final results
            results = await self._finalize_results()
            
            logger.info("✅ Interview completed successfully!")
            return results
            
        except Exception as e:
            logger.error(f"❌ Interview failed: {e}", exc_info=True)
            await self._handle_error(e)
            return {"success": False, "error": str(e)}
    
    async def _join_meeting(self, meet_url: str, headless: bool) -> None:
        """Step 1: Join Google Meet"""
        logger.info("📞 Step 1: Joining Google Meet...")
        self.stage = InterviewStage.JOINING
        
        # Initialize authentication
        self.auth = GoogleMeetAuth(
            email=self.bot_email,
            password=self.bot_password,
            headless=headless
        )
        
        await self.auth.initialize()
        
        # Login (uses cached session if available)
        login_success = await self.auth.login()
        if not login_success:
            raise Exception("Failed to authenticate with Google")
        
        # Join meeting (handles navigation internally)
        self.joiner = MeetBotJoiner(self.auth.get_page())
        join_success = await self.joiner.join_meeting(
            meeting_url=meet_url,
            disable_camera=True,
            enable_microphone=True,
            bot_name="AI Interview Bot"
        )
        
        if not join_success:
            raise Exception("Failed to join meeting")
        
        # Wait for candidate to join
        logger.info("⏳ Waiting for candidate to join...")
        candidate_joined = await self.joiner.wait_for_participants(min_participants=2, timeout=300)
        if not candidate_joined:
            raise Exception("Candidate did not join the meeting within 5 minutes. Interview cancelled.")
        
        # Initialize audio system
        self.audio = MeetAudioIntegration(self.auth.get_page())
        await self.audio.initialize()
        
        logger.info("✅ Successfully joined meeting and ready for interview")
    
    async def _load_questions(self, job_title: str) -> None:
        """Step 2: Load interview questions from database"""
        logger.info("📋 Step 2: Loading interview questions...")
        
        # Try to load questions from database by interview_id
        try:
            result = self.question_repo.get_questions_by_interview(self.interview_id)
            if result and result.get('questions'):
                self.questions = result['questions']
                logger.info(f"✅ Found {len(self.questions)} questions in database")
        except Exception as e:
            logger.warning(f"⚠️ Could not load questions from DB: {e}")
            self.questions = []
        
        if not self.questions:
            # Generate generic questions for the job title
            logger.warning(f"⚠️ No questions found for {job_title}, using generic ones")
            self.questions = [
                {"question_text": "Tell me about yourself and your background.", "type": "intro"},
                {"question_text": f"What interests you about this {job_title} position?", "type": "motivation"},
                {"question_text": f"Describe your relevant experience for {job_title}.", "type": "experience"},
                {"question_text": "What are your greatest strengths?", "type": "strengths"},
                {"question_text": "How do you handle challenges at work?", "type": "behavioral"},
            ]
        
        # Create QA session in database for storing Q&A pairs
        try:
            self.qa_session_id = self.qa_repo.create_session(
                interview_id=self.interview_id,
                session_type="interview"
            )
            logger.info(f"✅ QA session created: {self.qa_session_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not create QA session: {e}")
        
        logger.info(f"✅ Loaded {len(self.questions)} questions")
    
    async def _greet_candidate(self, candidate_name: str) -> None:
        """Step 3: Greet the candidate"""
        logger.info("👋 Step 3: Greeting candidate...")
        self.stage = InterviewStage.GREETING
        
        greeting = f"Hello {candidate_name}! Welcome to your AI interview. I'm your virtual interviewer today. We'll go through {len(self.questions)} questions. Please answer each question clearly. Let's begin!"
        
        # Generate TTS audio
        tts_result = await self.tts_agent.text_to_speech({
            "text": greeting,
            "voice_profile": "professional_female",
            "session_id": self.session_id
        })
        
        if tts_result.get('success'):
            # Play greeting through Meet - TTS returns base64 encoded audio
            audio_base64 = tts_result.get('data', {}).get('audio_base64', '')
            if audio_base64:
                audio_data = base64.b64decode(audio_base64)
                await self.audio.play_tts_audio(audio_data)
            
            # Wait for audio to finish + pause
            await asyncio.sleep(3)
        else:
            logger.warning(f"⚠️ TTS failed for greeting: {tts_result.get('error', {})}")
        
        logger.info("✅ Greeting complete")
    
    async def _qa_loop(self) -> None:
        """Step 4: Question & Answer loop"""
        logger.info("💬 Step 4: Starting Q&A loop...")
        self.stage = InterviewStage.QUESTIONING
        
        for idx, question in enumerate(self.questions):
            self.current_question_index = idx
            question_text = question.get('question_text', question.get('text', ''))
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Question {idx + 1}/{len(self.questions)}: {question_text}")
            logger.info(f"{'='*60}")
            
            # Ask question
            await self._ask_question(question_text)
            
            # Wait and record answer
            answer_text = await self._record_answer()
            
            # Analyze answer
            analysis = await self._analyze_answer(question_text, answer_text)
            
            # Save Q&A pair
            self.qa_history.append({
                "question": question_text,
                "answer": answer_text,
                "score": analysis.get('score', 0),
                "feedback": analysis.get('feedback', ''),
                "timestamp": datetime.now().isoformat()
            })
            
            # Save to database via QA session
            if self.qa_session_id:
                try:
                    self.qa_repo.add_question(
                        session_id=self.qa_session_id,
                        question=question_text,
                        answer=answer_text,
                        question_type=question.get('type', 'general'),
                        is_ai_generated=True
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Could not save Q&A to DB: {e}")
            
            logger.info(f"✅ Q&A #{idx + 1} completed (Score: {analysis.get('score', 0)}/10)")
        
        logger.info("✅ Q&A loop completed")
    
    async def _ask_question(self, question_text: str) -> None:
        """Ask a question via TTS"""
        logger.info(f"🔊 Asking question: {question_text[:50]}...")
        
        # Generate TTS
        tts_result = await self.tts_agent.text_to_speech({
            "text": question_text,
            "voice_profile": "professional_female",
            "session_id": self.session_id
        })
        
        if tts_result.get('success'):
            # Play through Meet - TTS returns base64 encoded audio
            audio_base64 = tts_result.get('data', {}).get('audio_base64', '')
            if audio_base64:
                audio_data = base64.b64decode(audio_base64)
                await self.audio.play_tts_audio(audio_data)
            
            # Wait for question to finish playing
            await asyncio.sleep(2)
        else:
            logger.warning(f"⚠️ TTS failed, skipping audio playback")
    
    async def _record_answer(self) -> str:
        """Record and transcribe candidate's answer"""
        logger.info("🎙️ Recording answer...")
        self.stage = InterviewStage.WAITING_ANSWER
        
        # Start recording
        await self.audio.start_recording_candidate()
        
        # Wait for silence (candidate finished speaking)
        await self.audio.wait_for_silence(duration=3.0, threshold=-40.0)
        
        # Stop recording and get audio chunks
        audio_chunks = await self.audio.stop_recording()
        
        if not audio_chunks:
            logger.warning("⚠️ No audio recorded")
            return "[No response]"
        
        # Combine audio chunks
        combined_audio = b''.join(audio_chunks)
        
        # Transcribe with STT
        logger.info("🔄 Transcribing answer...")
        try:
            stt_result = await self.stt_agent.transcribe_chunk({
                "audio_data": combined_audio,
                "session_id": self.session_id,
                "interview_id": self.interview_id,
                "audio_chunk_id": f"answer_{self.current_question_index}_{int(datetime.now().timestamp())}",
                "audio_format": "webm",
                "question_context": self.questions[self.current_question_index].get('question_text', '')
            })
            
            if stt_result.get('processing_status') == 'completed':
                answer_text = stt_result.get('cleaned_transcription') or stt_result.get('raw_transcription', '[Transcription failed]')
                logger.info(f"✅ Transcribed: {answer_text[:100]}...")
                return answer_text
            else:
                logger.error(f"❌ Transcription failed: {stt_result.get('last_error', 'unknown')}")
                return "[Transcription error]"
        except Exception as e:
            logger.error(f"❌ STT error: {e}")
            return "[Transcription error]"
    
    async def _analyze_answer(self, question: str, answer: str) -> Dict[str, Any]:
        """Analyze answer quality with LLM"""
        logger.info("🧠 Analyzing answer...")
        self.stage = InterviewStage.ANALYZING
        
        # Create analysis prompt
        prompt = f"""You are an expert interviewer analyzing a candidate's answer.

Question: {question}

Candidate's Answer: {answer}

Please provide:
1. Score (0-10): How well did they answer?
2. Feedback: Brief constructive feedback
3. Key points: What they did well
4. Improvements: What could be better

Format your response as JSON:
{{
    "score": <number 0-10>,
    "feedback": "<brief feedback>",
    "strengths": ["<point 1>", "<point 2>"],
    "improvements": ["<suggestion 1>", "<suggestion 2>"]
}}"""
        
        try:
            # Call Groq LLM
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse JSON response
            analysis_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_start = analysis_text.find('{')
            json_end = analysis_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(analysis_text[json_start:json_end])
            else:
                analysis = {"score": 5, "feedback": "Could not parse analysis"}
            
            logger.info(f"✅ Analysis complete (Score: {analysis.get('score', 0)}/10)")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
            return {"score": 0, "feedback": "Analysis error", "strengths": [], "improvements": []}
    
    async def _close_interview(self, candidate_name: str) -> None:
        """Step 5: Close the interview"""
        logger.info("👋 Step 5: Closing interview...")
        self.stage = InterviewStage.COMPLETING
        
        # Calculate overall score
        if self.qa_history:
            scores = [qa.get('score', 0) for qa in self.qa_history]
            self.overall_score = sum(scores) / len(scores)
        
        closing = f"Thank you {candidate_name}! We've completed all {len(self.questions)} questions. Your interview is now complete. We'll be in touch soon. Have a great day!"
        
        # Generate and play closing
        tts_result = await self.tts_agent.text_to_speech({
            "text": closing,
            "voice_profile": "professional_female",
            "session_id": self.session_id
        })
        
        if tts_result.get('success'):
            audio_base64 = tts_result.get('data', {}).get('audio_base64', '')
            if audio_base64:
                audio_data = base64.b64decode(audio_base64)
                await self.audio.play_tts_audio(audio_data)
            await asyncio.sleep(3)
        
        logger.info("✅ Closing message delivered")
    
    async def _leave_meeting(self) -> None:
        """Step 6: Leave Google Meet"""
        logger.info("🚪 Step 6: Leaving meeting...")
        
        if self.joiner:
            await self.joiner.leave_meeting()
        
        if self.auth:
            await self.auth.close()
        
        logger.info("✅ Left meeting successfully")
    
    async def _finalize_results(self) -> Dict[str, Any]:
        """Step 7: Calculate and save final results"""
        logger.info("📊 Step 7: Finalizing results...")
        self.stage = InterviewStage.FINISHED
        
        results = {
            "success": True,
            "interview_id": self.interview_id,
            "session_id": self.session_id,
            "total_questions": len(self.questions),
            "questions_answered": len(self.qa_history),
            "overall_score": round(self.overall_score, 2),
            "qa_history": self.qa_history,
            "completed_at": datetime.now().isoformat()
        }
        
        # Update interview in database
        self.interview_repo.update_interview(
            interview_id=self.interview_id,
            update_data={
                "status": "completed",
                "overall_score": self.overall_score,
                "qa_data": self.qa_history,
                "completed_at": datetime.utcnow()
            }
        )
        
        logger.info(f"✅ Results saved (Overall Score: {self.overall_score:.2f}/10)")
        return results
    
    async def _handle_error(self, error: Exception) -> None:
        """Handle errors and cleanup"""
        logger.error(f"❌ Error in interview: {error}")
        self.stage = InterviewStage.ERROR
        
        # Try to leave meeting gracefully
        try:
            if self.joiner:
                await self.joiner.leave_meeting()
            if self.auth:
                await self.auth.close()
        except:
            pass
        
        # Update database
        if self.interview_id:
            self.interview_repo.update_interview(
                interview_id=self.interview_id,
                update_data={
                    "status": "failed",
                    "error": str(error),
                    "failed_at": datetime.utcnow()
                }
            )


async def main():
    """
    Test the Meet Interview Orchestrator
    """
    # Get inputs
    interview_id = input("Interview ID: ").strip() or "test_interview_001"
    meet_url = input("Google Meet URL: ").strip()
    candidate_name = input("Candidate Name: ").strip() or "Test Candidate"
    job_title = input("Job Title: ").strip() or "Software Engineer"
    
    if not meet_url:
        print("❌ Meet URL is required")
        return
    
    # Create orchestrator
    orchestrator = MeetInterviewOrchestrator()
    
    # Conduct interview
    results = await orchestrator.conduct_interview(
        interview_id=interview_id,
        meet_url=meet_url,
        candidate_name=candidate_name,
        job_title=job_title,
        headless=False  # Set True for production
    )
    
    # Print results
    print("\n" + "="*60)
    print("📊 INTERVIEW RESULTS")
    print("="*60)
    print(f"Success: {results.get('success')}")
    print(f"Overall Score: {results.get('overall_score', 0)}/10")
    print(f"Questions: {results.get('total_questions', 0)}")
    print(f"Answers: {results.get('questions_answered', 0)}")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
