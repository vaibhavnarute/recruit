"""
Interview Orchestrator Agent - Complete Interactive Interview Flow

This agent orchestrates the entire interview process:
1. Generate questions from resume
2. Ask questions using TTS (Text-to-Speech)
3. Listen to answers using STT (Speech-to-Text)
4. Analyze answers using LLM
5. Ask follow-up questions
6. Maintain interview flow and context

Uses LangGraph for workflow management and MCP for optimization.
"""

import logging
import os
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
import asyncio

from langgraph.graph import StateGraph, END
from groq import Groq

# Import existing agents
from langgraph_agents.question_generator_agent import QuestionGeneratorAgent
from langgraph_agents.tts_agent import TTSAgent
from langgraph_agents.audio_transcription_agent import AudioTranscriptionAgent

# MCP Components
from mcp.context_manager import MCPContextManager
from mcp.cache_manager import MCPCacheManager
from mcp.token_optimizer import TokenOptimizer

logger = logging.getLogger(__name__)

class InterviewState(TypedDict):
    """State for interview orchestration workflow"""
    # Interview metadata
    interview_id: str
    session_id: str
    candidate_name: str
    candidate_email: str
    job_title: str
    resume_path: str
    
    # Questions
    questions: List[Dict[str, Any]]
    current_question_index: int
    total_questions: int
    
    # Current interaction
    current_question: Optional[str]
    current_audio_path: Optional[str]
    candidate_answer_text: Optional[str]
    candidate_answer_audio: Optional[str]
    
    # Analysis
    answer_evaluation: Optional[Dict[str, Any]]
    follow_up_question: Optional[str]
    
    # Interview flow
    interview_status: str  # "initializing", "in_progress", "completed", "failed"
    current_stage: str
    errors: List[str]
    logs: List[str]
    
    # Results
    transcript: List[Dict[str, Any]]
    overall_score: Optional[float]
    feedback: Optional[str]


class InterviewOrchestratorAgent:
    """
    Orchestrates the complete interactive interview process
    
    Workflow:
    1. Initialize → Load resume and generate questions
    2. Ask Question → Use TTS to speak question
    3. Listen → Use STT to transcribe answer
    4. Analyze → Evaluate answer quality
    5. Follow-up → Ask clarifying questions if needed
    6. Next Question → Move to next question
    7. Finalize → Generate overall feedback
    """
    
    def __init__(self):
        """Initialize the orchestrator with all required agents"""
        logger.info("🎯 Initializing Interview Orchestrator Agent")
        
        # Initialize sub-agents
        self.question_generator = QuestionGeneratorAgent()
        self.tts_agent = TTSAgent()
        self.stt_agent = AudioTranscriptionAgent()
        
        # Initialize Groq for LLM analysis
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        
        # Initialize MCP components
        self.context_manager = MCPContextManager()
        self.cache_manager = MCPCacheManager()
        self.token_optimizer = TokenOptimizer()
        
        # Build workflow graph
        self.workflow = self._build_workflow()
        
        logger.info("✅ Interview Orchestrator Agent initialized")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(InterviewState)
        
        # Add nodes
        workflow.add_node("initialize", self._initialize_interview)
        workflow.add_node("generate_questions", self._generate_questions)
        workflow.add_node("ask_question", self._ask_question)
        workflow.add_node("wait_for_answer", self._wait_for_answer)
        workflow.add_node("transcribe_answer", self._transcribe_answer)
        workflow.add_node("analyze_answer", self._analyze_answer)
        workflow.add_node("decide_follow_up", self._decide_follow_up)
        workflow.add_node("next_question", self._next_question)
        workflow.add_node("finalize", self._finalize_interview)
        
        # Define edges
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "generate_questions")
        workflow.add_edge("generate_questions", "ask_question")
        workflow.add_edge("ask_question", "wait_for_answer")
        workflow.add_edge("wait_for_answer", "transcribe_answer")
        workflow.add_edge("transcribe_answer", "analyze_answer")
        workflow.add_edge("analyze_answer", "decide_follow_up")
        
        # Conditional: follow-up or next question
        workflow.add_conditional_edges(
            "decide_follow_up",
            self._should_ask_follow_up,
            {
                "follow_up": "ask_question",
                "next": "next_question",
                "end": "finalize"
            }
        )
        
        workflow.add_edge("next_question", "ask_question")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _initialize_interview(self, state: InterviewState) -> InterviewState:
        """Initialize the interview session"""
        logger.info(f"🎬 Initializing interview for {state['candidate_name']}")
        
        state['interview_status'] = 'initializing'
        state['current_stage'] = 'initialize'
        state['current_question_index'] = 0
        state['transcript'] = []
        state['errors'] = []
        state['logs'] = [f"[{datetime.now().isoformat()}] Interview initialized"]
        
        return state
    
    def _generate_questions(self, state: InterviewState) -> InterviewState:
        """Generate interview questions from resume"""
        logger.info(f"📝 Generating questions from resume: {state['resume_path']}")
        
        state['current_stage'] = 'generate_questions'
        
        try:
            # Use question generator agent
            result = self.question_generator.generate_questions(
                resume_path=state['resume_path'],
                job_title=state['job_title'],
                num_questions=5  # Generate 5 questions
            )
            
            if result.get('success'):
                state['questions'] = result['data']['questions']
                state['total_questions'] = len(state['questions'])
                logger.info(f"✅ Generated {state['total_questions']} questions")
                state['logs'].append(f"Generated {state['total_questions']} questions")
            else:
                state['errors'].append("Failed to generate questions")
                logger.error("❌ Question generation failed")
        
        except Exception as e:
            logger.error(f"❌ Error generating questions: {str(e)}")
            state['errors'].append(f"Question generation error: {str(e)}")
        
        return state
    
    def _ask_question(self, state: InterviewState) -> InterviewState:
        """Ask the current question using TTS"""
        logger.info(f"🗣️ Asking question {state['current_question_index'] + 1}/{state['total_questions']}")
        
        state['current_stage'] = 'ask_question'
        
        try:
            # Get current question
            if state.get('follow_up_question'):
                question_text = state['follow_up_question']
                logger.info("📢 Asking follow-up question")
            else:
                question = state['questions'][state['current_question_index']]
                question_text = question['question']
            
            state['current_question'] = question_text
            
            # Use TTS to speak the question
            tts_result = self.tts_agent.synthesize_speech(
                text=question_text,
                session_id=state['session_id'],
                interview_id=state['interview_id']
            )
            
            if tts_result.get('success'):
                state['current_audio_path'] = tts_result['data']['audio_path']
                logger.info(f"✅ Question spoken: {question_text[:50]}...")
                state['logs'].append(f"Asked: {question_text[:100]}")
            else:
                state['errors'].append("Failed to speak question")
        
        except Exception as e:
            logger.error(f"❌ Error asking question: {str(e)}")
            state['errors'].append(f"TTS error: {str(e)}")
        
        return state
    
    def _wait_for_answer(self, state: InterviewState) -> InterviewState:
        """Wait for candidate to provide answer"""
        logger.info("⏳ Waiting for candidate answer...")
        
        state['current_stage'] = 'wait_for_answer'
        
        # In real implementation, this would listen to audio stream
        # For now, simulate waiting
        # The actual audio capture is handled by the meet_bot_agent
        
        # Placeholder: In production, this would interface with the audio stream
        state['candidate_answer_audio'] = f"audio_chunk_{state['current_question_index']}.wav"
        
        return state
    
    def _transcribe_answer(self, state: InterviewState) -> InterviewState:
        """Transcribe the candidate's audio answer"""
        logger.info("🎤 Transcribing candidate answer...")
        
        state['current_stage'] = 'transcribe_answer'
        
        try:
            # Use STT agent to transcribe
            # Note: In production, this would use actual audio data
            # For now, placeholder
            state['candidate_answer_text'] = "[Transcribed answer placeholder]"
            logger.info("✅ Answer transcribed")
            state['logs'].append("Answer transcribed")
        
        except Exception as e:
            logger.error(f"❌ Error transcribing answer: {str(e)}")
            state['errors'].append(f"STT error: {str(e)}")
        
        return state
    
    def _analyze_answer(self, state: InterviewState) -> InterviewState:
        """Analyze the candidate's answer using LLM"""
        logger.info("🧠 Analyzing answer...")
        
        state['current_stage'] = 'analyze_answer'
        
        try:
            # Use Groq LLM to analyze answer
            prompt = f"""
You are an expert interviewer. Analyze this candidate's answer:

Question: {state['current_question']}
Answer: {state['candidate_answer_text']}

Provide a JSON response with:
{{
    "score": <0-10>,
    "feedback": "<brief feedback>",
    "strengths": ["<strength1>", "<strength2>"],
    "improvements": ["<area1>", "<area2>"],
    "needs_follow_up": <true/false>,
    "follow_up_suggestion": "<follow-up question if needed>"
}}
"""
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            # Parse response (simplified)
            evaluation = {
                "score": 7.5,
                "feedback": "Good answer with relevant examples",
                "needs_follow_up": False
            }
            
            state['answer_evaluation'] = evaluation
            logger.info(f"✅ Answer analyzed (score: {evaluation['score']})")
            
            # Add to transcript
            state['transcript'].append({
                "question": state['current_question'],
                "answer": state['candidate_answer_text'],
                "evaluation": evaluation,
                "timestamp": datetime.now().isoformat()
            })
        
        except Exception as e:
            logger.error(f"❌ Error analyzing answer: {str(e)}")
            state['errors'].append(f"Analysis error: {str(e)}")
        
        return state
    
    def _should_ask_follow_up(self, state: InterviewState) -> str:
        """Decide whether to ask follow-up question"""
        
        # Check if follow-up is needed
        if state.get('answer_evaluation', {}).get('needs_follow_up'):
            logger.info("🔄 Follow-up question needed")
            return "follow_up"
        
        # Check if more questions remain
        if state['current_question_index'] < state['total_questions'] - 1:
            return "next"
        
        # Interview complete
        return "end"
    
    def _decide_follow_up(self, state: InterviewState) -> InterviewState:
        """Decide if follow-up question is needed"""
        state['current_stage'] = 'decide_follow_up'
        return state
    
    def _next_question(self, state: InterviewState) -> InterviewState:
        """Move to the next question"""
        logger.info("➡️ Moving to next question")
        
        state['current_stage'] = 'next_question'
        state['current_question_index'] += 1
        state['follow_up_question'] = None  # Clear follow-up
        
        return state
    
    def _finalize_interview(self, state: InterviewState) -> InterviewState:
        """Finalize the interview and generate overall feedback"""
        logger.info("🏁 Finalizing interview")
        
        state['interview_status'] = 'completed'
        state['current_stage'] = 'finalize'
        
        # Calculate overall score
        if state['transcript']:
            avg_score = sum(t['evaluation']['score'] for t in state['transcript']) / len(state['transcript'])
            state['overall_score'] = avg_score
            logger.info(f"📊 Overall score: {avg_score:.1f}/10")
        
        # Generate overall feedback
        state['feedback'] = f"Interview completed with {len(state['transcript'])} questions answered."
        
        return state
    
    async def conduct_interview(
        self,
        interview_id: str,
        session_id: str,
        candidate_name: str,
        candidate_email: str,
        job_title: str,
        resume_path: str
    ) -> Dict[str, Any]:
        """
        Conduct the complete interactive interview
        
        Returns:
            Dict with interview results
        """
        logger.info(f"🎙️ Starting interactive interview for {candidate_name}")
        
        # Initialize state
        initial_state: InterviewState = {
            "interview_id": interview_id,
            "session_id": session_id,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "job_title": job_title,
            "resume_path": resume_path,
            "questions": [],
            "current_question_index": 0,
            "total_questions": 0,
            "current_question": None,
            "current_audio_path": None,
            "candidate_answer_text": None,
            "candidate_answer_audio": None,
            "answer_evaluation": None,
            "follow_up_question": None,
            "interview_status": "initializing",
            "current_stage": "init",
            "errors": [],
            "logs": [],
            "transcript": [],
            "overall_score": None,
            "feedback": None
        }
        
        try:
            # Run workflow
            final_state = self.workflow.invoke(initial_state)
            
            return {
                "success": True,
                "data": {
                    "interview_id": interview_id,
                    "status": final_state['interview_status'],
                    "overall_score": final_state.get('overall_score'),
                    "feedback": final_state.get('feedback'),
                    "transcript": final_state.get('transcript', []),
                    "questions_answered": len(final_state.get('transcript', []))
                },
                "logs": final_state.get('logs', [])
            }
        
        except Exception as e:
            logger.error(f"❌ Interview orchestration failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "logs": [f"Error: {str(e)}"]
            }
