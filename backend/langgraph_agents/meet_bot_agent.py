"""
Google Meet Bot LangGraph Agent
Manages Google Meet session lifecycle with Groq LLM orchestration
"""

import json
import logging
import asyncio
from typing import Dict, Any, TypedDict, List
from datetime import datetime
from langgraph.graph import StateGraph, END
from groq import Groq
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.context_manager import MCPContextManager
from mcp.cache_manager import MCPCacheManager
from mcp.token_optimizer import TokenOptimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MeetBotState(TypedDict):
    """State for Meet Bot workflow"""
    session_id: str
    meet_url: str
    interview_id: str
    bot_email: str
    bot_password: str
    
    # Session state
    session_status: str  # initializing, joining, recording, transcribing, disconnecting, completed, failed
    join_attempts: int
    max_retries: int
    
    # Audio & Transcription
    audio_chunks_received: int
    transcription_segments: List[Dict[str, Any]]
    current_speaker: str
    
    # Error handling
    errors: List[Dict[str, str]]
    last_error: str
    recovery_action: str
    
    # Timestamps
    started_at: str
    joined_at: str
    ended_at: str
    
    # LLM outputs
    join_strategy: str
    error_diagnosis: str
    recovery_plan: str
    session_summary: str


class MeetBotAgent:
    """
    LangGraph agent for managing Google Meet recording sessions
    
    Workflow:
    1. initialize_session: Validate inputs and prepare bot
    2. plan_join_strategy: Determine best approach to join meeting
    3. monitor_connection: Check connection health
    4. handle_audio_stream: Process incoming audio chunks
    5. diagnose_errors: Analyze failures and determine recovery
    6. finalize_session: Cleanup and summary
    """
    
    def __init__(self):
        """Initialize Meet Bot Agent with MCP components"""
        logger.info("Initializing MeetBotAgent")
        
        # Initialize Groq client
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"
        
        # Initialize MCP components
        self.context_manager = MCPContextManager(max_context_length=10000)
        self.cache_manager = MCPCacheManager(
            ttl_minutes=1440,  # 24 hours
            max_cache_size=1000
        )
        self.token_optimizer = TokenOptimizer(
            max_input_tokens=10000,
            max_output_tokens=10000
        )
        
        # Build workflow
        self.workflow = self._build_workflow()
        logger.info("MeetBotAgent initialized successfully")
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow"""
        workflow = StateGraph(MeetBotState)
        
        # Add nodes
        workflow.add_node("initialize_session", self.initialize_session)
        workflow.add_node("plan_join_strategy", self.plan_join_strategy)
        workflow.add_node("monitor_connection", self.monitor_connection)
        workflow.add_node("handle_audio_stream", self.handle_audio_stream)
        workflow.add_node("diagnose_errors", self.diagnose_errors)
        workflow.add_node("finalize_session", self.finalize_session)
        
        # Define edges
        workflow.set_entry_point("initialize_session")
        
        workflow.add_edge("initialize_session", "plan_join_strategy")
        workflow.add_edge("plan_join_strategy", "monitor_connection")
        
        # Conditional edges for monitoring
        workflow.add_conditional_edges(
            "monitor_connection",
            self._should_continue_monitoring,
            {
                "continue": "handle_audio_stream",
                "error": "diagnose_errors",
                "complete": "finalize_session"
            }
        )
        
        workflow.add_conditional_edges(
            "handle_audio_stream",
            self._should_continue_recording,
            {
                "continue": "monitor_connection",
                "error": "diagnose_errors",
                "complete": "finalize_session"
            }
        )
        
        workflow.add_conditional_edges(
            "diagnose_errors",
            self._should_retry,
            {
                "retry": "plan_join_strategy",
                "abort": "finalize_session"
            }
        )
        
        workflow.add_edge("finalize_session", END)
        
        return workflow.compile()
    
    def initialize_session(self, state: MeetBotState) -> MeetBotState:
        """Initialize Meet recording session"""
        logger.info(f"Initializing session: {state['session_id']}")
        
        try:
            # Validate required fields
            required_fields = ['meet_url', 'interview_id', 'bot_email']
            missing_fields = [f for f in required_fields if not state.get(f)]
            
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Initialize state
            state['session_status'] = 'initializing'
            state['join_attempts'] = 0
            state['max_retries'] = state.get('max_retries', 3)
            state['audio_chunks_received'] = 0
            state['transcription_segments'] = []
            state['errors'] = []
            state['started_at'] = datetime.utcnow().isoformat()
            
            logger.info(f"Session initialized: {state['session_id']}")
            logger.info(f"Meet URL: {state['meet_url']}")
            logger.info(f"Bot Email: {state['bot_email']}")
            
            return state
            
        except Exception as e:
            logger.error(f"Error initializing session: {str(e)}", exc_info=True)
            state['session_status'] = 'failed'
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'initialize_session',
                'error': str(e)
            })
            return state
    
    def plan_join_strategy(self, state: MeetBotState) -> MeetBotState:
        """Use LLM to plan optimal join strategy"""
        logger.info(f"Planning join strategy for session: {state['session_id']}")
        
        try:
            state['join_attempts'] += 1
            
            # Build context for LLM
            context = self.context_manager.build_context([
                f"Meet URL: {state['meet_url']}",
                f"Bot Email: {state['bot_email']}",
                f"Join Attempt: {state['join_attempts']}/{state['max_retries']}",
                f"Previous Errors: {state.get('last_error', 'None')}"
            ])
            
            # Check cache
            cache_key = f"join_strategy_{state['meet_url']}_{state['join_attempts']}"
            cached_strategy = self.cache_manager.get(cache_key)
            
            if cached_strategy:
                logger.info("Using cached join strategy")
                state['join_strategy'] = cached_strategy
                return state
            
            # Optimize prompt
            prompt = f"""You are a Google Meet automation expert. Analyze the following and provide a join strategy.

Context:
{context}

Provide a JSON response with:
1. "approach": Best approach to join (e.g., "direct_link", "retry_with_wait", "check_permissions")
2. "wait_time": Seconds to wait before joining (0-30)
3. "mic_state": Should mic be ON or OFF initially
4. "camera_state": Should camera be ON or OFF
5. "join_button_strategy": How to locate and click join button
6. "reasoning": Brief explanation

Response:"""
            
            optimized_prompt, stats = self.token_optimizer.optimize_prompt(prompt)
            
            # Call Groq LLM
            logger.info("Calling Groq LLM for join strategy")
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": optimized_prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            strategy_text = response.choices[0].message.content.strip()
            logger.info(f"LLM Response: {strategy_text}")
            
            # Parse JSON response
            try:
                # Extract JSON if wrapped in markdown
                if "```json" in strategy_text:
                    strategy_text = strategy_text.split("```json")[1].split("```")[0].strip()
                elif "```" in strategy_text:
                    strategy_text = strategy_text.split("```")[1].split("```")[0].strip()
                
                strategy = json.loads(strategy_text)
                state['join_strategy'] = json.dumps(strategy)
                
                # Cache the strategy
                self.cache_manager.set(cache_key, state['join_strategy'])
                
                logger.info(f"Join strategy planned: {strategy['approach']}")
                logger.info(f"Wait time: {strategy.get('wait_time', 0)}s")
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM JSON, using fallback strategy: {str(e)}")
                state['join_strategy'] = json.dumps({
                    "approach": "direct_link",
                    "wait_time": 2,
                    "mic_state": "ON",
                    "camera_state": "OFF",
                    "join_button_strategy": "wait_for_button",
                    "reasoning": "Fallback strategy due to parsing error"
                })
            
            state['session_status'] = 'joining'
            return state
            
        except Exception as e:
            logger.error(f"Error planning join strategy: {str(e)}", exc_info=True)
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'plan_join_strategy',
                'error': str(e)
            })
            # Use fallback strategy
            state['join_strategy'] = json.dumps({
                "approach": "direct_link",
                "wait_time": 2,
                "mic_state": "ON",
                "camera_state": "OFF",
                "join_button_strategy": "wait_for_button",
                "reasoning": "Fallback strategy due to error"
            })
            return state
    
    def monitor_connection(self, state: MeetBotState) -> MeetBotState:
        """Monitor Meet connection health"""
        logger.info(f"Monitoring connection for session: {state['session_id']} (status: {state['session_status']})")
        
        try:
            # Transition from joining to recording
            if state['session_status'] == 'joining':
                state['session_status'] = 'joined'
                state['joined_at'] = datetime.utcnow().isoformat()
                logger.info(f"✅ Successfully joined meeting: {state['session_id']}")
            
            # Check if we should complete
            if state.get('session_status') in ['completing', 'disconnecting', 'completed']:
                logger.info(f"Session is {state['session_status']}, moving to finalization")
            
            return state
            
        except Exception as e:
            logger.error(f"Error monitoring connection: {str(e)}", exc_info=True)
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'monitor_connection',
                'error': str(e)
            })
            return state
    
    def handle_audio_stream(self, state: MeetBotState) -> MeetBotState:
        """Process incoming audio stream - this is called in a loop by the workflow"""
        current_chunks = state.get('audio_chunks_received', 0)
        logger.info(f"Handling audio stream for session: {state['session_id']} (chunks: {current_chunks})")
        
        try:
            # NOTE: This function is called repeatedly by the workflow loop
            # Actual audio chunks are received via WebSocket and stored in MongoDB
            # We're just simulating the monitoring loop here
            
            # In production, this would check MongoDB for new audio chunks
            # For now, simulate receiving audio by incrementing counter
            state['audio_chunks_received'] = current_chunks + 1
            
            if state['audio_chunks_received'] % 5 == 0:
                logger.info(f"📊 Processed {state['audio_chunks_received']} audio chunks (workflow iterations)")
            
            # Update status to recording/transcribing
            if state['session_status'] == 'joined':
                state['session_status'] = 'recording'
            elif state['session_status'] == 'recording':
                state['session_status'] = 'transcribing'
            
            return state
            
        except Exception as e:
            logger.error(f"Error handling audio stream: {str(e)}", exc_info=True)
            state['last_error'] = str(e)
            state['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 'handle_audio_stream',
                'error': str(e)
            })
            return state
    
    def diagnose_errors(self, state: MeetBotState) -> MeetBotState:
        """Use LLM to diagnose errors and determine recovery"""
        logger.error(f"Diagnosing errors for session: {state['session_id']}")
        
        try:
            # Build error context
            errors_summary = "\n".join([
                f"{e['timestamp']}: {e['stage']} - {e['error']}"
                for e in state.get('errors', [])[-5:]  # Last 5 errors
            ])
            
            context = self.context_manager.build_context([
                f"Session ID: {state['session_id']}",
                f"Current Status: {state['session_status']}",
                f"Join Attempts: {state['join_attempts']}/{state['max_retries']}",
                f"Last Error: {state.get('last_error', 'None')}",
                f"Error History:\n{errors_summary}"
            ])
            
            prompt = f"""You are a debugging expert for Google Meet automation. Analyze these errors and provide recovery strategy.

Context:
{context}

Provide a JSON response with:
1. "diagnosis": What went wrong
2. "severity": "low", "medium", "high", or "critical"
3. "is_recoverable": true/false
4. "recovery_action": Specific action to take (e.g., "retry_with_delay", "check_credentials", "abort")
5. "recommended_delay": Seconds to wait before retry (0-60)
6. "reasoning": Brief explanation

Response:"""
            
            optimized_prompt, stats = self.token_optimizer.optimize_prompt(prompt)
            
            logger.info("Calling Groq LLM for error diagnosis")
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": optimized_prompt}],
                temperature=0.2,
                max_tokens=1000
            )
            
            diagnosis_text = response.choices[0].message.content.strip()
            logger.info(f"LLM Diagnosis: {diagnosis_text}")
            
            # Parse JSON response
            try:
                if "```json" in diagnosis_text:
                    diagnosis_text = diagnosis_text.split("```json")[1].split("```")[0].strip()
                elif "```" in diagnosis_text:
                    diagnosis_text = diagnosis_text.split("```")[1].split("```")[0].strip()
                
                diagnosis = json.loads(diagnosis_text)
                state['error_diagnosis'] = json.dumps(diagnosis)
                
                # Normalize recovery action to 'retry' or 'abort'
                raw_action = diagnosis.get('recovery_action', 'abort')
                if 'retry' in raw_action.lower():
                    normalized_action = 'retry'
                elif 'abort' in raw_action.lower() or not diagnosis.get('is_recoverable', False):
                    normalized_action = 'abort'
                else:
                    # Default to retry if recoverable, abort otherwise
                    normalized_action = 'retry' if diagnosis.get('is_recoverable', False) else 'abort'
                
                state['recovery_action'] = normalized_action
                
                logger.info(f"Error diagnosis: {diagnosis['diagnosis']}")
                logger.info(f"Severity: {diagnosis['severity']}")
                logger.info(f"Recovery action: {state['recovery_action']}")
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse diagnosis JSON: {str(e)}")
                state['recovery_action'] = 'abort' if state['join_attempts'] >= state['max_retries'] else 'retry'
            
            return state
            
        except Exception as e:
            logger.error(f"Error during diagnosis: {str(e)}", exc_info=True)
            state['recovery_action'] = 'abort'
            return state
    
    def finalize_session(self, state: MeetBotState) -> MeetBotState:
        """Finalize session and generate summary"""
        logger.info(f"Finalizing session: {state['session_id']}")
        
        try:
            state['ended_at'] = datetime.utcnow().isoformat()
            
            # Generate session summary with LLM
            context = self.context_manager.build_context([
                f"Session ID: {state['session_id']}",
                f"Duration: {state.get('started_at', 'N/A')} to {state['ended_at']}",
                f"Audio Chunks: {state.get('audio_chunks_received', 0)}",
                f"Transcription Segments: {len(state.get('transcription_segments', []))}",
                f"Errors Encountered: {len(state.get('errors', []))}",
                f"Final Status: {state['session_status']}"
            ])
            
            prompt = f"""Generate a brief session summary for this Google Meet recording session.

Context:
{context}

Provide a JSON response with:
1. "success": true/false
2. "summary": Brief description of what happened
3. "metrics": Key metrics (duration, audio_chunks, transcripts)
4. "issues": Any problems encountered
5. "recommendations": Suggestions for future sessions

Response:"""
            
            optimized_prompt, stats = self.token_optimizer.optimize_prompt(prompt)
            
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": optimized_prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            summary_text = response.choices[0].message.content.strip()
            
            try:
                if "```json" in summary_text:
                    summary_text = summary_text.split("```json")[1].split("```")[0].strip()
                elif "```" in summary_text:
                    summary_text = summary_text.split("```")[1].split("```")[0].strip()
                
                summary = json.loads(summary_text)
                state['session_summary'] = json.dumps(summary)
                
            except json.JSONDecodeError:
                state['session_summary'] = json.dumps({
                    "success": state['session_status'] == 'completed',
                    "summary": "Session ended",
                    "metrics": {
                        "audio_chunks": state.get('audio_chunks_received', 0),
                        "errors": len(state.get('errors', []))
                    }
                })
            
            # Set final status
            if state['session_status'] not in ['completed', 'failed']:
                state['session_status'] = 'completed'
            
            logger.info(f"Session finalized: {state['session_id']}")
            logger.info(f"Final status: {state['session_status']}")
            logger.info(f"Audio chunks processed: {state.get('audio_chunks_received', 0)}")
            
            return state
            
        except Exception as e:
            logger.error(f"Error finalizing session: {str(e)}", exc_info=True)
            state['session_status'] = 'failed'
            state['last_error'] = str(e)
            return state
    
    # Conditional edge functions
    
    def _should_continue_monitoring(self, state: MeetBotState) -> str:
        """Determine next step after monitoring"""
        status = state.get('session_status', '')
        audio_chunks = state.get('audio_chunks_received', 0)
        
        # Check if we've reached the chunk limit (for testing)
        if audio_chunks >= 10:
            logger.info(f"Chunk limit reached ({audio_chunks}/10), completing session")
            state['session_status'] = 'completing'
            return "complete"
        
        if status == 'failed' or state.get('last_error'):
            return "error"
        elif status in ['disconnecting', 'completing', 'completed']:
            return "complete"
        elif status in ['recording', 'transcribing', 'joined']:
            return "continue"
        else:
            return "continue"
    
    def _should_continue_recording(self, state: MeetBotState) -> str:
        """Determine if recording should continue"""
        status = state.get('session_status', '')
        audio_chunks = state.get('audio_chunks_received', 0)
        
        # Check chunk limit first
        if audio_chunks >= 10:
            logger.info(f"Processed {audio_chunks} audio chunks, marking for completion")
            state['session_status'] = 'completing'
            return "complete"
        elif state.get('last_error'):
            logger.warning(f"Error detected during recording: {state.get('last_error')}")
            return "error"
        elif status in ['disconnecting', 'completing', 'completed']:
            return "complete"
        else:
            return "continue"
    
    def _should_retry(self, state: MeetBotState) -> str:
        """Determine if error recovery should retry"""
        recovery_action = state.get('recovery_action', 'abort')
        join_attempts = state.get('join_attempts', 0)
        max_retries = state.get('max_retries', 3)
        
        if recovery_action == 'retry' and join_attempts < max_retries:
            logger.info(f"Retrying join (attempt {join_attempts + 1}/{max_retries})")
            return "retry"
        else:
            logger.warning("Max retries reached or abort requested")
            state['session_status'] = 'failed'
            return "abort"
    
    async def run_session(self, session_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a complete Meet recording session
        
        Args:
            session_config: Configuration with meet_url, interview_id, bot_email, etc.
            
        Returns:
            Final state dictionary
        """
        logger.info(f"Starting Meet recording session")
        logger.info(f"Configuration: {json.dumps({k: v for k, v in session_config.items() if k != 'bot_password'})}")
        
        try:
            # Initialize state
            initial_state = MeetBotState(
                session_id=session_config.get('session_id', f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"),
                meet_url=session_config['meet_url'],
                interview_id=session_config['interview_id'],
                bot_email=session_config['bot_email'],
                bot_password=session_config.get('bot_password', ''),
                session_status='pending',
                join_attempts=0,
                max_retries=session_config.get('max_retries', 3),
                audio_chunks_received=0,
                transcription_segments=[],
                current_speaker='',
                errors=[],
                last_error='',
                recovery_action='',
                started_at='',
                joined_at='',
                ended_at='',
                join_strategy='',
                error_diagnosis='',
                recovery_plan='',
                session_summary=''
            )
            
            # Run workflow with increased recursion limit
            logger.info("Invoking LangGraph workflow")
            final_state = self.workflow.invoke(
                initial_state,
                config={"recursion_limit": 50}  # Increase from default 25 to 50
            )
            
            logger.info(f"Workflow completed: {final_state['session_status']}")
            
            return dict(final_state)
            
        except Exception as e:
            logger.error(f"Fatal error in run_session: {str(e)}", exc_info=True)
            return {
                'session_id': session_config.get('session_id', 'unknown'),
                'session_status': 'failed',
                'last_error': str(e),
                'errors': [{'timestamp': datetime.utcnow().isoformat(), 'error': str(e)}]
            }
    
    def update_session_state(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update running session state (for external events like audio chunks, disconnections)
        
        Args:
            session_id: Session identifier
            updates: State updates dictionary
            
        Returns:
            Updated state
        """
        logger.info(f"Updating session state: {session_id}")
        logger.debug(f"Updates: {json.dumps(updates)}")
        
        # This would interact with a state store in production
        # For now, just return the updates
        return {
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat(),
            'updates': updates
        }


# Module-level function for easy import
async def create_meet_session(session_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to create and run a Meet session
    
    Args:
        session_config: Session configuration
        
    Returns:
        Session result
    """
    agent = MeetBotAgent()
    return await agent.run_session(session_config)


if __name__ == "__main__":
    # Test the agent
    import asyncio
    
    test_config = {
        'session_id': 'test_session_001',
        'meet_url': 'https://meet.google.com/abc-defg-hij',
        'interview_id': 'interview_001',
        'bot_email': 'bot@example.com',
        'bot_password': 'test_password',
        'max_retries': 2
    }
    
    result = asyncio.run(create_meet_session(test_config))
    print(json.dumps(result, indent=2))
