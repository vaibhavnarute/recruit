"""
AI Question Generator LangGraph Agent

Purpose: Generate intelligent interview questions based on:
- Candidate's resume (skills, experience, projects)
- Job description (requirements, responsibilities)
- Previous answers (adaptive questioning)

Features:
- Technical questions (based on skills)
- Behavioral questions (based on experience)
- Scenario-based questions (based on job requirements)
- Adaptive follow-up questions
- Difficulty progression (easy → medium → hard)
"""

import logging
from typing import Dict, Any, List, TypedDict, Optional
from datetime import datetime
import uuid
import json

from langgraph.graph import StateGraph, END
from groq import Groq
import os
from dotenv import load_dotenv

# Import MCP components
from mcp.context_manager import MCPContextManager
from mcp.cache_manager import MCPCacheManager
from mcp.token_optimizer import TokenOptimizer

load_dotenv()
logger = logging.getLogger(__name__)


class QuestionGeneratorState(TypedDict):
    """State for question generation workflow"""
    # Input
    resume_data: Dict[str, Any]
    job_description: Dict[str, Any]
    candidate_id: str
    job_id: str
    interview_id: str
    threshold_percentage: float
    previous_answers: List[Dict[str, Any]]
    
    # Processing
    context_id: str
    candidate_score: float
    technical_skills: List[str]
    experience_years: int
    job_requirements: List[str]
    
    # Output
    questions: List[Dict[str, Any]]
    question_categories: Dict[str, int]
    
    # Error handling
    errors: List[Dict[str, Any]]
    success: bool
    step_logs: List[str]


class QuestionGeneratorAgent:
    """
    LangGraph Agent for generating intelligent interview questions
    
    Workflow:
    1. Analyze resume and extract key information
    2. Parse job description and identify requirements
    3. Generate technical questions (based on skills)
    4. Generate behavioral questions (based on experience)
    5. Generate scenario questions (based on job requirements)
    6. Adapt questions based on previous answers (if any)
    7. Store questions in database
    """
    
    def __init__(self, technical_count: int = 5, behavioral_count: int = 3, scenario_count: int = 2):
        """
        Initialize Question Generator Agent
        
        Args:
            technical_count: Number of technical questions to generate (default: 5)
            behavioral_count: Number of behavioral questions to generate (default: 3)
            scenario_count: Number of scenario questions to generate (default: 2)
        """
        # Groq LLM for question generation
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.model = "llama-3.3-70b-versatile"  # Updated to supported model
        
        # Question count configuration
        self.technical_count = technical_count
        self.behavioral_count = behavioral_count
        self.scenario_count = scenario_count
        
        # MCP components
        self.context_manager = MCPContextManager(max_context_length=10000)
        self.cache_manager = MCPCacheManager(ttl_minutes=1440, max_cache_size=1000)
        self.token_optimizer = TokenOptimizer(max_input_tokens=10000, max_output_tokens=10000)
        
        # Build workflow
        self.workflow = self._build_workflow()
        
        logger.info("🤖 Question Generator Agent initialized")
        logger.info(f"📊 Using Groq LLM: {self.model}")
        logger.info(f"📋 Question Config: {technical_count} technical, {behavioral_count} behavioral, {scenario_count} scenario")
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow for question generation"""
        workflow = StateGraph(QuestionGeneratorState)
        
        # Add nodes
        workflow.add_node("analyze_resume", self.analyze_resume)
        workflow.add_node("parse_job_description", self.parse_job_description)
        workflow.add_node("generate_technical_questions", self.generate_technical_questions)
        workflow.add_node("generate_behavioral_questions", self.generate_behavioral_questions)
        workflow.add_node("generate_scenario_questions", self.generate_scenario_questions)
        workflow.add_node("adapt_questions", self.adapt_questions)
        workflow.add_node("handle_error", self.handle_error)
        
        # Define workflow
        workflow.set_entry_point("analyze_resume")
        
        workflow.add_conditional_edges(
            "analyze_resume",
            lambda s: "parse_job_description" if s["success"] else "handle_error",
            {
                "parse_job_description": "parse_job_description",
                "handle_error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "parse_job_description",
            lambda s: "generate_technical_questions" if s["success"] else "handle_error",
            {
                "generate_technical_questions": "generate_technical_questions",
                "handle_error": "handle_error"
            }
        )
        
        workflow.add_edge("generate_technical_questions", "generate_behavioral_questions")
        workflow.add_edge("generate_behavioral_questions", "generate_scenario_questions")
        workflow.add_edge("generate_scenario_questions", "adapt_questions")
        workflow.add_edge("adapt_questions", END)
        workflow.add_edge("handle_error", END)
        
        logger.info("✅ Question generation workflow built")
        return workflow.compile()
    
    def analyze_resume(self, state: QuestionGeneratorState) -> QuestionGeneratorState:
        """
        Node 1: Analyze candidate's resume
        
        Extracts:
        - Technical skills
        - Years of experience
        - Key projects
        - Education
        """
        logger.info("📋 STEP 1: Analyzing resume...")
        state["step_logs"].append(f"[{datetime.now().isoformat()}] Analyzing resume")
        
        try:
            resume_data = state["resume_data"]
            
            # Extract technical skills
            technical_skills = resume_data.get("skills", [])
            if isinstance(technical_skills, str):
                technical_skills = [s.strip() for s in technical_skills.split(",")]
            
            state["technical_skills"] = technical_skills
            
            # Calculate experience years
            experience = resume_data.get("experience", [])
            total_years = 0
            if isinstance(experience, list):
                for exp in experience:
                    years = exp.get("years", 0)
                    if isinstance(years, (int, float)):
                        total_years += years
            elif isinstance(experience, str):
                # Try to extract years from text
                import re
                years_match = re.findall(r'(\d+)\s*(?:year|yr)', experience.lower())
                if years_match:
                    total_years = sum(int(y) for y in years_match)
            
            state["experience_years"] = total_years or resume_data.get("total_experience", 0)
            
            # Get candidate score (from resume analysis)
            state["candidate_score"] = resume_data.get("match_percentage", 0.0)
            
            # Create MCP context
            state["context_id"] = self.context_manager.create_context_id(
                state["candidate_id"],
                state["interview_id"]
            )
            
            self.context_manager.add_message(
                state["context_id"],
                "system",
                f"Analyzing resume for {state['candidate_id']} - {len(technical_skills)} skills identified"
            )
            
            logger.info(f"✅ Resume analysis complete")
            logger.info(f"   Skills: {len(technical_skills)}")
            logger.info(f"   Experience: {state['experience_years']} years")
            logger.info(f"   Match Score: {state['candidate_score']}%")
            
            state["success"] = True
            state["step_logs"].append(f"[{datetime.now().isoformat()}] Resume analyzed successfully")
            
        except Exception as e:
            logger.error(f"❌ Resume analysis failed: {str(e)}")
            state["success"] = False
            state["errors"].append({
                "code": "RESUME_ANALYSIS_ERROR",
                "message": f"Failed to analyze resume: {str(e)}",
                "step": "analyze_resume"
            })
            state["step_logs"].append(f"[{datetime.now().isoformat()}] Resume analysis failed")
        
        return state
    
    def parse_job_description(self, state: QuestionGeneratorState) -> QuestionGeneratorState:
        """
        Node 2: Parse job description
        
        Extracts:
        - Required skills
        - Responsibilities
        - Qualifications
        - Experience requirements
        """
        logger.info("💼 STEP 2: Parsing job description...")
        state["step_logs"].append(f"[{datetime.now().isoformat()}] Parsing job description")
        
        try:
            job_desc = state["job_description"]
            
            # Extract requirements
            requirements = job_desc.get("requirements", [])
            if isinstance(requirements, str):
                requirements = [r.strip() for r in requirements.split("\n") if r.strip()]
            
            state["job_requirements"] = requirements
            
            logger.info(f"✅ Job description parsed")
            logger.info(f"   Requirements: {len(requirements)}")
            
            self.context_manager.add_message(
                state["context_id"],
                "system",
                f"Job description parsed: {len(requirements)} requirements identified"
            )
            
            state["success"] = True
            state["step_logs"].append(f"[{datetime.now().isoformat()}] Job description parsed")
            
        except Exception as e:
            logger.error(f"❌ Job description parsing failed: {str(e)}")
            state["success"] = False
            state["errors"].append({
                "code": "JOB_PARSE_ERROR",
                "message": f"Failed to parse job description: {str(e)}",
                "step": "parse_job_description"
            })
        
        return state
    
    def generate_technical_questions(self, state: QuestionGeneratorState) -> QuestionGeneratorState:
        """
        Node 3: Generate technical questions based on skills
        
        Question types:
        - Skill-specific (e.g., "Explain Python decorators")
        - Problem-solving (e.g., "How would you optimize this algorithm?")
        - Best practices (e.g., "What's your approach to code review?")
        """
        logger.info("🔧 STEP 3: Generating technical questions...")
        state["step_logs"].append(f"[{datetime.now().isoformat()}] Generating technical questions")
        
        try:
            skills = state["technical_skills"]
            job_reqs = state["job_requirements"]
            experience_years = state["experience_years"]
            
            # Determine difficulty level based on experience
            if experience_years < 2:
                difficulty = "junior"
            elif experience_years < 5:
                difficulty = "mid-level"
            else:
                difficulty = "senior"
            
            # Create prompt for LLM
            prompt = f"""Generate {self.technical_count} technical interview questions for a {difficulty} candidate.

**Candidate Skills:** {', '.join(skills[:10])}
**Job Requirements:** {', '.join(job_reqs[:5])}
**Experience Level:** {experience_years} years

Generate questions that:
1. Test core technical knowledge
2. Assess problem-solving ability
3. Evaluate best practices understanding
4. Are appropriate for {difficulty} level
5. Relate to the job requirements

Return ONLY a JSON array of questions in this format:
[
  {{
    "question": "Question text here",
    "category": "technical",
    "difficulty": "easy|medium|hard",
    "topic": "specific topic/skill",
    "expected_answer_points": ["point 1", "point 2", "point 3"]
  }}
]
"""
            
            # Optimize prompt
            optimized_prompt, stats = self.token_optimizer.optimize_prompt(prompt)
            logger.info(f"📊 Prompt optimized: {stats.tokens_saved} tokens saved")
            
            # Call Groq LLM
            logger.info("🤖 Calling Groq LLM for technical questions...")
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert technical interviewer. Generate clear, relevant interview questions in valid JSON format."},
                    {"role": "user", "content": optimized_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            technical_questions = json.loads(response_text)
            
            # Add metadata
            for q in technical_questions:
                q["question_id"] = str(uuid.uuid4())
                q["created_at"] = datetime.utcnow().isoformat()
                q["interview_id"] = state["interview_id"]
            
            state["questions"] = technical_questions
            state["question_categories"] = {"technical": len(technical_questions)}
            
            logger.info(f"✅ Generated {len(technical_questions)} technical questions")
            state["step_logs"].append(f"[{datetime.now().isoformat()}] Technical questions generated")
            
        except Exception as e:
            logger.error(f"❌ Technical question generation failed: {str(e)}")
            # Continue with empty list (don't fail entire process)
            state["questions"] = []
            state["question_categories"] = {"technical": 0}
        
        return state
    
    def generate_behavioral_questions(self, state: QuestionGeneratorState) -> QuestionGeneratorState:
        """
        Node 4: Generate behavioral questions
        
        Based on:
        - Past experience
        - Leadership skills
        - Teamwork
        - Problem-solving approach
        """
        logger.info("👥 STEP 4: Generating behavioral questions...")
        state["step_logs"].append(f"[{datetime.now().isoformat()}] Generating behavioral questions")
        
        try:
            resume_data = state["resume_data"]
            experience_years = state["experience_years"]
            
            prompt = f"""Generate {self.behavioral_count} behavioral interview questions for a candidate with {experience_years} years of experience.

**Context:**
- Experience: {experience_years} years
- Resume highlights: {json.dumps(resume_data.get('summary', 'Not provided'))}

Generate questions that assess:
1. Leadership and teamwork
2. Problem-solving approach
3. Conflict resolution
4. Adaptability and learning

Return ONLY a JSON array:
[
  {{
    "question": "Question text here",
    "category": "behavioral",
    "difficulty": "medium",
    "topic": "leadership|teamwork|problem-solving|adaptability",
    "expected_answer_points": ["point 1", "point 2"]
  }}
]
"""
            
            # Call LLM
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert HR interviewer. Generate insightful behavioral questions in valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            response_text = response.choices[0].message.content.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            behavioral_questions = json.loads(response_text)
            
            # Add metadata
            for q in behavioral_questions:
                q["question_id"] = str(uuid.uuid4())
                q["created_at"] = datetime.utcnow().isoformat()
                q["interview_id"] = state["interview_id"]
            
            state["questions"].extend(behavioral_questions)
            state["question_categories"]["behavioral"] = len(behavioral_questions)
            
            logger.info(f"✅ Generated {len(behavioral_questions)} behavioral questions")
            state["step_logs"].append(f"[{datetime.now().isoformat()}] Behavioral questions generated")
            
        except Exception as e:
            logger.error(f"❌ Behavioral question generation failed: {str(e)}")
            state["question_categories"]["behavioral"] = 0
        
        return state
    
    def generate_scenario_questions(self, state: QuestionGeneratorState) -> QuestionGeneratorState:
        """
        Node 5: Generate scenario-based questions
        
        Real-world situations based on job requirements
        """
        logger.info("🎯 STEP 5: Generating scenario questions...")
        state["step_logs"].append(f"[{datetime.now().isoformat()}] Generating scenario questions")
        
        try:
            job_desc = state["job_description"]
            job_title = job_desc.get("title", "this position")
            responsibilities = job_desc.get("responsibilities", [])
            
            prompt = f"""Generate {self.scenario_count} scenario-based interview questions for a {job_title}.

**Job Responsibilities:**
{json.dumps(responsibilities[:5])}

Create realistic scenarios that test:
1. Decision-making under pressure
2. Technical problem-solving in real situations
3. Stakeholder management
4. Resource optimization

Return ONLY a JSON array:
[
  {{
    "question": "Scenario description and question",
    "category": "scenario",
    "difficulty": "medium",
    "topic": "decision-making|problem-solving|stakeholder-management",
    "expected_answer_points": ["approach 1", "consideration 2"]
  }}
]
"""
            
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert interviewer. Create realistic, job-specific scenarios in valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1500
            )
            
            response_text = response.choices[0].message.content.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            scenario_questions = json.loads(response_text)
            
            for q in scenario_questions:
                q["question_id"] = str(uuid.uuid4())
                q["created_at"] = datetime.utcnow().isoformat()
                q["interview_id"] = state["interview_id"]
            
            state["questions"].extend(scenario_questions)
            state["question_categories"]["scenario"] = len(scenario_questions)
            
            logger.info(f"✅ Generated {len(scenario_questions)} scenario questions")
            state["step_logs"].append(f"[{datetime.now().isoformat()}] Scenario questions generated")
            
        except Exception as e:
            logger.error(f"❌ Scenario question generation failed: {str(e)}")
            state["question_categories"]["scenario"] = 0
        
        return state
    
    def adapt_questions(self, state: QuestionGeneratorState) -> QuestionGeneratorState:
        """
        Node 6: Adapt questions based on previous answers (if any)
        
        If candidate has answered questions before:
        - Generate follow-up questions
        - Adjust difficulty based on performance
        - Deep-dive into weak areas
        """
        logger.info("🔄 STEP 6: Adapting questions based on context...")
        state["step_logs"].append(f"[{datetime.now().isoformat()}] Adapting questions")
        
        try:
            previous_answers = state.get("previous_answers", [])
            
            if previous_answers:
                logger.info(f"📊 Found {len(previous_answers)} previous answers - generating follow-ups")
                
                # Analyze previous performance
                correct_answers = sum(1 for ans in previous_answers if ans.get("is_correct", False))
                performance_ratio = correct_answers / len(previous_answers) if previous_answers else 0.5
                
                # Adjust difficulty
                if performance_ratio > 0.7:
                    logger.info("📈 High performance - increasing difficulty")
                    # Filter for harder questions
                    state["questions"] = [q for q in state["questions"] if q.get("difficulty") != "easy"]
                elif performance_ratio < 0.4:
                    logger.info("📉 Low performance - focusing on fundamentals")
                    # Keep easier questions
                    state["questions"] = [q for q in state["questions"] if q.get("difficulty") != "hard"]
                
                # Generate follow-up question based on last answer
                if previous_answers:
                    last_answer = previous_answers[-1]
                    follow_up_prompt = f"""Based on the candidate's previous answer, generate 1 follow-up question.

**Previous Question:** {last_answer.get('question', '')}
**Candidate's Answer:** {last_answer.get('answer', '')}

Generate a deeper follow-up question that:
1. Probes for more details
2. Tests understanding of implications
3. Explores edge cases or alternatives

Return ONLY a JSON object:
{{
  "question": "Follow-up question text",
  "category": "follow-up",
  "difficulty": "medium",
  "topic": "deep-dive",
  "parent_question_id": "{last_answer.get('question_id', '')}",
  "expected_answer_points": ["point 1", "point 2"]
}}
"""
                    
                    try:
                        response = self.groq_client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": "You are an expert interviewer. Generate insightful follow-up questions in valid JSON format."},
                                {"role": "user", "content": follow_up_prompt}
                            ],
                            temperature=0.7,
                            max_tokens=500
                        )
                        
                        response_text = response.choices[0].message.content.strip()
                        if "```json" in response_text:
                            response_text = response_text.split("```json")[1].split("```")[0].strip()
                        elif "```" in response_text:
                            response_text = response_text.split("```")[1].split("```")[0].strip()
                        
                        follow_up_q = json.loads(response_text)
                        follow_up_q["question_id"] = str(uuid.uuid4())
                        follow_up_q["created_at"] = datetime.utcnow().isoformat()
                        follow_up_q["interview_id"] = state["interview_id"]
                        
                        state["questions"].append(follow_up_q)
                        state["question_categories"]["follow-up"] = 1
                        
                        logger.info("✅ Generated adaptive follow-up question")
                    except Exception as e:
                        logger.warning(f"⚠️ Follow-up question generation failed: {str(e)}")
            
            else:
                logger.info("ℹ️ No previous answers - using default question set")
            
            state["success"] = True
            state["step_logs"].append(f"[{datetime.now().isoformat()}] Questions adapted successfully")
            
            # Log summary
            logger.info(f"📊 Total questions generated: {len(state['questions'])}")
            logger.info(f"   Categories: {state['question_categories']}")
            
        except Exception as e:
            logger.error(f"❌ Question adaptation failed: {str(e)}")
            # Don't fail - use unadapted questions
            state["success"] = True
        
        return state
    
    def handle_error(self, state: QuestionGeneratorState) -> QuestionGeneratorState:
        """Error handler node"""
        logger.error(f"⚠️ ERROR HANDLER invoked")
        logger.error(f"📝 Errors: {state['errors']}")
        
        state["success"] = False
        state["step_logs"].append(f"[{datetime.now().isoformat()}] Error handler invoked")
        
        return state
    
    def generate_questions(
        self,
        resume_data: Dict[str, Any],
        job_description: Dict[str, Any],
        candidate_id: str,
        job_id: str,
        interview_id: str,
        threshold_percentage: float = 70.0,
        previous_answers: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for question generation
        
        Returns (ALWAYS 200 status):
        {
            "success": True/False,
            "data": {
                "questions": [...],
                "total_questions": 10,
                "categories": {"technical": 5, "behavioral": 3, "scenario": 2},
                "interview_id": "uuid"
            },
            "errors": [...],
            "logs": [...]
        }
        """
        logger.info("\n" + "="*80)
        logger.info("🎬 STARTING: AI Question Generation")
        logger.info("="*80)
        
        initial_state: QuestionGeneratorState = {
            "resume_data": resume_data,
            "job_description": job_description,
            "candidate_id": candidate_id,
            "job_id": job_id,
            "interview_id": interview_id,
            "threshold_percentage": threshold_percentage,
            "previous_answers": previous_answers or [],
            "context_id": "",
            "candidate_score": 0.0,
            "technical_skills": [],
            "experience_years": 0,
            "job_requirements": [],
            "questions": [],
            "question_categories": {},
            "errors": [],
            "success": True,
            "step_logs": []
        }
        
        try:
            logger.info("🚀 Invoking LangGraph workflow...")
            final_state = self.workflow.invoke(initial_state)
            
            logger.info("\n" + "="*80)
            logger.info(f"✅ WORKFLOW COMPLETED: {'SUCCESS' if final_state['success'] else 'FAILED'}")
            logger.info("="*80 + "\n")
            
            if final_state["success"]:
                return {
                    "success": True,
                    "data": {
                        "questions": final_state["questions"],
                        "total_questions": len(final_state["questions"]),
                        "categories": final_state["question_categories"],
                        "interview_id": interview_id,
                        "candidate_id": candidate_id,
                        "job_id": job_id,
                        "threshold_met": final_state["candidate_score"] >= threshold_percentage
                    },
                    "logs": final_state["step_logs"]
                }
            else:
                return {
                    "success": False,
                    "errors": final_state["errors"],
                    "logs": final_state["step_logs"]
                }
        
        except Exception as e:
            logger.error(f"❌ Workflow execution failed: {str(e)}")
            import traceback
            return {
                "success": False,
                "errors": [{
                    "code": "WORKFLOW_ERROR",
                    "message": f"Question generation failed: {str(e)}",
                    "traceback": traceback.format_exc()
                }],
                "logs": ["Workflow crashed unexpectedly"]
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test data
    test_resume = {
        "skills": ["Python", "Machine Learning", "TensorFlow", "PyTorch", "SQL"],
        "experience": [{"title": "ML Engineer", "years": 3}],
        "total_experience": 3,
        "match_percentage": 85.0,
        "summary": "Experienced ML engineer with 3 years in production systems"
    }
    
    test_job_desc = {
        "title": "Senior Machine Learning Engineer",
        "requirements": [
            "5+ years Python experience",
            "Deep learning expertise",
            "Production ML systems",
            "Team leadership"
        ],
        "responsibilities": [
            "Design and implement ML models",
            "Optimize model performance",
            "Lead technical initiatives"
        ]
    }
    
    agent = QuestionGeneratorAgent()
    result = agent.generate_questions(
        resume_data=test_resume,
        job_description=test_job_desc,
        candidate_id="test-candidate-123",
        job_id="test-job-456",
        interview_id="test-interview-789",
        threshold_percentage=70.0
    )
    
    print("\n" + "="*80)
    print("RESULT:")
    print("="*80)
    print(json.dumps(result, indent=2))
