"""
Post-Interview Analytics Agent
Generates comprehensive analysis using LangGraph workflow
Analyzes transcripts and calculates metrics
"""

import json
import logging
import os
import sys
from typing import Dict, Any, List, TypedDict, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from groq import Groq
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnalyticsState(TypedDict):
    """State for analytics workflow"""
    # Input
    session_id: str
    orchestration_id: str
    interview_id: str
    
    # Transcript data
    transcript: List[Dict[str, Any]]
    candidate_name: str
    job_description: str
    total_turns: int
    
    # Analysis components
    summary: Optional[str]
    strengths: Optional[List[str]]
    weaknesses: Optional[List[str]]
    technical_assessment: Optional[Dict[str, Any]]
    communication_assessment: Optional[Dict[str, Any]]
    
    # Calculated metrics
    response_coherence_score: Optional[float]
    technical_depth_score: Optional[float]
    communication_clarity_score: Optional[float]
    overall_score: Optional[float]
    
    # Final report
    analysis_report: Optional[Dict[str, Any]]
    
    # Error handling
    errors: List[str]
    processing_status: str


class PostInterviewAnalyticsAgent:
    """
    Analytics agent for post-interview analysis
    
    Workflow:
    1. Fetch transcript from MongoDB
    2. Analyze with LLM (summary, strengths, weaknesses)
    3. Calculate coherence metrics
    4. Assess technical depth
    5. Evaluate communication clarity
    6. Generate final report
    7. Store in interview_results collection
    """
    
    def __init__(self, groq_api_key: Optional[str] = None):
        """Initialize Analytics Agent"""
        logger.info("🔬 Initializing PostInterviewAnalyticsAgent")
        
        # Groq client for LLM analysis
        self.groq_api_key = groq_api_key or os.getenv('GROQ_API_KEY')
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        self.client = Groq(api_key=self.groq_api_key)
        self.model = "llama-3.3-70b-versatile"
        
        # MongoDB connection
        mongo_uri = os.getenv('MONGODB_ATLAS_URI')
        if not mongo_uri:
            raise ValueError("MONGODB_ATLAS_URI not found in environment")
        
        self.mongo_client = MongoClient(mongo_uri)
        mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
        self.db = self.mongo_client[mongo_db_name]
        
        # Build workflow
        self.workflow = self._build_workflow()
        
        logger.info("✅ PostInterviewAnalyticsAgent initialized")
        logger.info(f"   Model: {self.model}")
        logger.info(f"   MongoDB: Connected")
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow for analytics"""
        workflow = StateGraph(AnalyticsState)
        
        # Add nodes
        workflow.add_node("fetch_transcript", self._fetch_transcript)
        workflow.add_node("generate_summary", self._generate_summary)
        workflow.add_node("analyze_technical_depth", self._analyze_technical_depth)
        workflow.add_node("analyze_communication", self._analyze_communication)
        workflow.add_node("calculate_metrics", self._calculate_metrics)
        workflow.add_node("generate_report", self._generate_report)
        workflow.add_node("store_report", self._store_report)
        workflow.add_node("handle_error", self._handle_error)
        
        # Define flow
        workflow.set_entry_point("fetch_transcript")
        
        workflow.add_conditional_edges(
            "fetch_transcript",
            lambda state: "error" if state.get("errors") else "continue",
            {
                "error": "handle_error",
                "continue": "generate_summary"
            }
        )
        
        workflow.add_edge("generate_summary", "analyze_technical_depth")
        workflow.add_edge("analyze_technical_depth", "analyze_communication")
        workflow.add_edge("analyze_communication", "calculate_metrics")
        workflow.add_edge("calculate_metrics", "generate_report")
        workflow.add_edge("generate_report", "store_report")
        workflow.add_edge("store_report", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    async def _fetch_transcript(self, state: AnalyticsState) -> AnalyticsState:
        """Fetch transcript from MongoDB"""
        logger.info(f"📥 Fetching transcript for session: {state['session_id']}")
        
        try:
            # Fetch from conversation_transcripts
            transcript_doc = self.db['conversation_transcripts'].find_one({
                'session_id': state['session_id']
            })
            
            if not transcript_doc:
                # Try fetching from orchestration_sessions
                session_doc = self.db['orchestration_sessions'].find_one({
                    'session_id': state['session_id']
                })
                
                if not session_doc:
                    error_msg = f"No transcript found for session: {state['session_id']}"
                    logger.error(f"❌ {error_msg}")
                    state['errors'].append(error_msg)
                    state['processing_status'] = 'failed'
                    return state
                
                # Extract turns from session
                turns = session_doc.get('turns', [])
                state['transcript'] = turns
                state['candidate_name'] = session_doc.get('candidate_name', 'Unknown')
                state['job_description'] = session_doc.get('job_description', 'Not specified')
                state['total_turns'] = len(turns)
            else:
                state['transcript'] = transcript_doc.get('transcript', [])
                state['candidate_name'] = transcript_doc.get('candidate_name', 'Unknown')
                state['job_description'] = transcript_doc.get('job_description', 'Not specified')
                state['total_turns'] = transcript_doc.get('total_turns', len(state['transcript']))
            
            if not state['transcript']:
                error_msg = "Transcript is empty"
                logger.error(f"❌ {error_msg}")
                state['errors'].append(error_msg)
                state['processing_status'] = 'failed'
                return state
            
            logger.info(f"✅ Transcript fetched: {state['total_turns']} turns")
            state['processing_status'] = 'analyzing'
            
            return state
            
        except Exception as e:
            error_msg = f"Error fetching transcript: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            state['errors'].append(error_msg)
            state['processing_status'] = 'failed'
            return state
    
    async def _generate_summary(self, state: AnalyticsState) -> AnalyticsState:
        """Generate interview summary using LLM"""
        logger.info("📝 Generating interview summary with LLM")
        
        try:
            # Build conversation text
            conversation_text = self._build_conversation_text(state['transcript'])
            
            # Create prompt
            prompt = f"""Analyze this interview transcript and provide a comprehensive summary.

Candidate: {state['candidate_name']}
Position: {state['job_description']}
Total Turns: {state['total_turns']}

Transcript:
{conversation_text}

Provide analysis in JSON format:
{{
    "summary": "Overall interview summary (2-3 paragraphs)",
    "strengths": ["strength 1", "strength 2", "strength 3"],
    "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
    "key_insights": ["insight 1", "insight 2", "insight 3"],
    "recommendation": "hire|maybe|no_hire",
    "confidence_level": "high|medium|low"
}}

Focus on:
- Technical competency
- Communication skills
- Problem-solving approach
- Cultural fit indicators"""

            # Call LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert interview analyzer. Provide objective, detailed analysis in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # Parse response
            llm_response = response.choices[0].message.content
            
            # Extract JSON
            analysis = self._extract_json(llm_response)
            
            if analysis:
                state['summary'] = analysis.get('summary', '')
                state['strengths'] = analysis.get('strengths', [])
                state['weaknesses'] = analysis.get('weaknesses', [])
                
                logger.info("✅ Summary generated successfully")
                logger.info(f"   Strengths: {len(state['strengths'])}")
                logger.info(f"   Weaknesses: {len(state['weaknesses'])}")
            else:
                # Fallback parsing
                state['summary'] = llm_response[:500]
                state['strengths'] = []
                state['weaknesses'] = []
                logger.warning("⚠️ Could not parse JSON, using fallback")
            
            return state
            
        except Exception as e:
            error_msg = f"Error generating summary: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            state['errors'].append(error_msg)
            # Continue with partial analysis
            return state
    
    async def _analyze_technical_depth(self, state: AnalyticsState) -> AnalyticsState:
        """Analyze technical depth of responses"""
        logger.info("🔬 Analyzing technical depth")
        
        try:
            conversation_text = self._build_conversation_text(state['transcript'])
            
            prompt = f"""Analyze the technical depth of this interview for a {state['job_description']} position.

Transcript:
{conversation_text}

Provide technical assessment in JSON format:
{{
    "technical_depth_score": 0-100,
    "technical_areas_covered": ["area1", "area2", "area3"],
    "technical_strengths": ["strength1", "strength2"],
    "technical_gaps": ["gap1", "gap2"],
    "complexity_level": "basic|intermediate|advanced|expert",
    "practical_experience": "none|limited|moderate|extensive"
}}

Evaluate:
- Depth of technical knowledge
- Practical experience demonstrated
- Problem-solving approaches
- Technical terminology usage"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a technical interviewer expert. Provide objective technical assessment."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            llm_response = response.choices[0].message.content
            assessment = self._extract_json(llm_response)
            
            if assessment:
                state['technical_assessment'] = assessment
                state['technical_depth_score'] = float(assessment.get('technical_depth_score', 50))
                logger.info(f"✅ Technical analysis complete: {state['technical_depth_score']}/100")
            else:
                # Default score based on turn count
                state['technical_depth_score'] = min(50 + (state['total_turns'] * 2), 100)
                state['technical_assessment'] = {
                    'technical_depth_score': state['technical_depth_score'],
                    'note': 'Analysis incomplete, using heuristic'
                }
                logger.warning("⚠️ Could not parse technical assessment, using heuristic")
            
            return state
            
        except Exception as e:
            error_msg = f"Error analyzing technical depth: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            state['errors'].append(error_msg)
            state['technical_depth_score'] = 50.0  # Default
            return state
    
    async def _analyze_communication(self, state: AnalyticsState) -> AnalyticsState:
        """Analyze communication clarity"""
        logger.info("💬 Analyzing communication clarity")
        
        try:
            conversation_text = self._build_conversation_text(state['transcript'])
            
            prompt = f"""Analyze the communication skills in this interview.

Transcript:
{conversation_text}

Provide communication assessment in JSON format:
{{
    "communication_clarity_score": 0-100,
    "response_coherence_score": 0-100,
    "articulation_quality": "poor|fair|good|excellent",
    "listening_skills": "poor|fair|good|excellent",
    "conciseness": "poor|fair|good|excellent",
    "engagement_level": "low|moderate|high",
    "communication_strengths": ["strength1", "strength2"],
    "communication_areas_for_improvement": ["area1", "area2"]
}}

Evaluate:
- Clarity of explanations
- Coherence of responses
- Active listening demonstrated
- Conciseness vs verbosity
- Engagement and enthusiasm"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a communication skills expert. Provide objective assessment."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            llm_response = response.choices[0].message.content
            assessment = self._extract_json(llm_response)
            
            if assessment:
                state['communication_assessment'] = assessment
                state['communication_clarity_score'] = float(assessment.get('communication_clarity_score', 50))
                state['response_coherence_score'] = float(assessment.get('response_coherence_score', 50))
                logger.info(f"✅ Communication analysis complete:")
                logger.info(f"   Clarity: {state['communication_clarity_score']}/100")
                logger.info(f"   Coherence: {state['response_coherence_score']}/100")
            else:
                # Default scores
                state['communication_clarity_score'] = 60.0
                state['response_coherence_score'] = 60.0
                state['communication_assessment'] = {
                    'communication_clarity_score': 60.0,
                    'response_coherence_score': 60.0,
                    'note': 'Analysis incomplete, using default'
                }
                logger.warning("⚠️ Could not parse communication assessment, using default")
            
            return state
            
        except Exception as e:
            error_msg = f"Error analyzing communication: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            state['errors'].append(error_msg)
            state['communication_clarity_score'] = 50.0  # Default
            state['response_coherence_score'] = 50.0  # Default
            return state
    
    async def _calculate_metrics(self, state: AnalyticsState) -> AnalyticsState:
        """Calculate final metrics"""
        logger.info("📊 Calculating final metrics")
        
        try:
            # Ensure all scores exist
            coherence = state.get('response_coherence_score', 50.0)
            technical = state.get('technical_depth_score', 50.0)
            communication = state.get('communication_clarity_score', 50.0)
            
            # Calculate overall score (weighted average)
            weights = {
                'technical': 0.45,
                'communication': 0.30,
                'coherence': 0.25
            }
            
            overall = (
                technical * weights['technical'] +
                communication * weights['communication'] +
                coherence * weights['coherence']
            )
            
            state['overall_score'] = round(overall, 2)
            
            logger.info(f"✅ Metrics calculated:")
            logger.info(f"   Response Coherence: {coherence}/100")
            logger.info(f"   Technical Depth: {technical}/100")
            logger.info(f"   Communication Clarity: {communication}/100")
            logger.info(f"   Overall Score: {state['overall_score']}/100")
            
            return state
            
        except Exception as e:
            error_msg = f"Error calculating metrics: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            state['errors'].append(error_msg)
            state['overall_score'] = 50.0  # Default
            return state
    
    async def _generate_report(self, state: AnalyticsState) -> AnalyticsState:
        """Generate final analysis report"""
        logger.info("📋 Generating final analysis report")
        
        try:
            # Determine recommendation
            overall = state.get('overall_score', 0)
            if overall >= 80:
                recommendation = "strong_hire"
                recommendation_text = "Strong Hire - Candidate demonstrates excellent skills"
            elif overall >= 65:
                recommendation = "hire"
                recommendation_text = "Hire - Candidate meets requirements with good potential"
            elif overall >= 50:
                recommendation = "maybe"
                recommendation_text = "Maybe - Candidate shows potential but has areas to improve"
            else:
                recommendation = "no_hire"
                recommendation_text = "No Hire - Candidate does not meet minimum requirements"
            
            # Build comprehensive report
            report = {
                # Identification
                'session_id': state['session_id'],
                'orchestration_id': state['orchestration_id'],
                'interview_id': state['interview_id'],
                'candidate_name': state['candidate_name'],
                'job_description': state['job_description'],
                
                # Summary
                'summary': state.get('summary', 'Summary not available'),
                'recommendation': recommendation,
                'recommendation_text': recommendation_text,
                
                # Scores
                'scores': {
                    'overall_score': state.get('overall_score', 0),
                    'response_coherence': state.get('response_coherence_score', 0),
                    'technical_depth': state.get('technical_depth_score', 0),
                    'communication_clarity': state.get('communication_clarity_score', 0)
                },
                
                # Detailed Assessments
                'strengths': state.get('strengths', []),
                'weaknesses': state.get('weaknesses', []),
                'technical_assessment': state.get('technical_assessment', {}),
                'communication_assessment': state.get('communication_assessment', {}),
                
                # Metadata
                'total_turns': state['total_turns'],
                'analyzed_at': datetime.utcnow().isoformat(),
                'analysis_version': '1.0.0',
                'model_used': self.model,
                
                # Processing Info
                'errors': state.get('errors', []),
                'processing_status': 'completed' if not state.get('errors') else 'completed_with_warnings'
            }
            
            state['analysis_report'] = report
            state['processing_status'] = 'completed'
            
            logger.info("✅ Analysis report generated")
            logger.info(f"   Recommendation: {recommendation}")
            logger.info(f"   Overall Score: {state['overall_score']}/100")
            
            return state
            
        except Exception as e:
            error_msg = f"Error generating report: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            state['errors'].append(error_msg)
            state['processing_status'] = 'failed'
            return state
    
    async def _store_report(self, state: AnalyticsState) -> AnalyticsState:
        """Store analysis report in MongoDB"""
        logger.info(f"💾 Storing analysis report for session: {state['session_id']}")
        
        try:
            if not state.get('analysis_report'):
                raise ValueError("No analysis report to store")
            
            # Store in interview_results collection
            result = self.db['interview_results'].update_one(
                {'session_id': state['session_id']},
                {'$set': state['analysis_report']},
                upsert=True
            )
            
            if result.modified_count > 0 or result.upserted_id:
                logger.info("✅ Analysis report stored successfully")
                logger.info(f"   Collection: interview_results")
                logger.info(f"   Session: {state['session_id']}")
            
            return state
            
        except Exception as e:
            error_msg = f"Error storing report: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            state['errors'].append(error_msg)
            return state
    
    async def _handle_error(self, state: AnalyticsState) -> AnalyticsState:
        """Handle errors in workflow"""
        logger.error(f"❌ Analytics workflow failed for session: {state['session_id']}")
        logger.error(f"   Errors: {state.get('errors', [])}")
        
        state['processing_status'] = 'failed'
        
        # Store partial report if possible
        if state.get('session_id'):
            try:
                error_report = {
                    'session_id': state['session_id'],
                    'orchestration_id': state.get('orchestration_id'),
                    'interview_id': state.get('interview_id'),
                    'processing_status': 'failed',
                    'errors': state.get('errors', []),
                    'analyzed_at': datetime.utcnow().isoformat()
                }
                
                self.db['interview_results'].update_one(
                    {'session_id': state['session_id']},
                    {'$set': error_report},
                    upsert=True
                )
                
                logger.info("✅ Error report stored")
                
            except Exception as e:
                logger.error(f"❌ Could not store error report: {e}")
        
        return state
    
    def _build_conversation_text(self, transcript: List[Dict[str, Any]]) -> str:
        """Build readable conversation text from transcript"""
        conversation = []
        
        for turn in transcript:
            turn_num = turn.get('turn', turn.get('turn_number', '?'))
            speaker = turn.get('speaker', 'unknown')
            text = turn.get('text', turn.get('transcript', ''))
            
            if text:
                conversation.append(f"Turn {turn_num} ({speaker}): {text}")
        
        return "\n".join(conversation) if conversation else "No conversation data available"
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response"""
        try:
            # Try direct parse
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON in text
            start = text.find('{')
            end = text.rfind('}')
            
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start:end+1])
                except json.JSONDecodeError:
                    pass
            
            logger.warning("⚠️ Could not extract JSON from LLM response")
            return None
    
    async def analyze_interview(
        self,
        session_id: str,
        orchestration_id: Optional[str] = None,
        interview_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run complete analytics workflow
        
        Args:
            session_id: Session to analyze
            orchestration_id: Optional orchestration ID
            interview_id: Optional interview ID
            
        Returns:
            Analysis report
        """
        logger.info(f"🚀 Starting interview analysis for session: {session_id}")
        
        # Initialize state
        initial_state: AnalyticsState = {
            'session_id': session_id,
            'orchestration_id': orchestration_id or f'orch_{session_id}',
            'interview_id': interview_id or f'interview_{session_id}',
            'transcript': [],
            'candidate_name': '',
            'job_description': '',
            'total_turns': 0,
            'summary': None,
            'strengths': None,
            'weaknesses': None,
            'technical_assessment': None,
            'communication_assessment': None,
            'response_coherence_score': None,
            'technical_depth_score': None,
            'communication_clarity_score': None,
            'overall_score': None,
            'analysis_report': None,
            'errors': [],
            'processing_status': 'initializing'
        }
        
        # Run workflow
        try:
            final_state = await self.workflow.ainvoke(initial_state)
            
            if final_state.get('analysis_report'):
                logger.info("✅ Interview analysis completed successfully")
                return {
                    'success': True,
                    'data': final_state['analysis_report'],
                    'message': 'Interview analysis completed successfully'
                }
            else:
                logger.error("❌ Analysis failed to generate report")
                return {
                    'success': False,
                    'error': {
                        'code': 'ANALYSIS_FAILED',
                        'message': 'Failed to generate analysis report',
                        'details': final_state.get('errors', [])
                    },
                    'message': 'Interview analysis failed'
                }
                
        except Exception as e:
            logger.error(f"❌ Analysis workflow error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': {
                    'code': 'WORKFLOW_ERROR',
                    'message': str(e)
                },
                'message': 'Interview analysis workflow failed'
            }
    
    def close(self):
        """Close MongoDB connection"""
        try:
            self.mongo_client.close()
            logger.info("✅ MongoDB connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing MongoDB: {e}")


# Singleton instance
_analytics_agent_instance: Optional[PostInterviewAnalyticsAgent] = None


def get_analytics_agent() -> PostInterviewAnalyticsAgent:
    """Get singleton analytics agent instance"""
    global _analytics_agent_instance
    
    if _analytics_agent_instance is None:
        _analytics_agent_instance = PostInterviewAnalyticsAgent()
    
    return _analytics_agent_instance
