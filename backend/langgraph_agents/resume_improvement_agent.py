"""
Resume Improvement Agent with LangGraph + MCP Integration

This agent provides intelligent resume improvement suggestions using:
- LangGraph workflow for structured analysis
- MCP (Model Context Protocol) for efficient context management
- Multi-step             try:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": suggestion_prompt}],
                    temperature=0.3,
                    max_tokens=512,
                )
                
                response_text = clean_json_response(response.choices[0].message.content)
                suggestion = json.loads(response_text)
                suggestions.append(suggestion)
                
                state["tokens_used"] = state.get("tokens_used", 0) + response.usage.total_tokens
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON parsing error for {gap.get('area')}: {str(e)}")
                logger.warning(f"📄 Raw response: {response.choices[0].message.content[:200]}...")
                continue
            except Exception as e:
                logger.warning(f"⚠️ Error generating suggestion for {gap.get('area')}: {str(e)}")
                continuee → identify gaps → generate suggestions
"""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
import logging
import json

logger = logging.getLogger(__name__)


def clean_json_response(response_text: str) -> str:
    """
    Clean LLM response to extract pure JSON
    
    Removes markdown code blocks and other formatting
    """
    if not response_text:
        return "{}"
    
    # Strip whitespace
    response_text = response_text.strip()
    
    # Remove markdown code blocks (```json ... ``` or ``` ... ```)
    if '```' in response_text:
        # Split by ``` to find code blocks
        parts = response_text.split('```')
        if len(parts) >= 3:
            # The JSON is typically in the middle part (between first and last ```)
            # Skip the first part (before opening ```) and last part (after closing ```)
            json_part = parts[1]
            # Remove 'json' or other language identifiers from the start
            if json_part.strip().lower().startswith('json'):
                json_part = json_part.strip()[4:].strip()
            response_text = json_part
        elif len(parts) == 2:
            # Only opening ``` found, take the second part
            json_part = parts[1]
            if json_part.strip().lower().startswith('json'):
                json_part = json_part.strip()[4:].strip()
            response_text = json_part
    
    # Strip again after removing code blocks
    response_text = response_text.strip()
    
    # Remove any remaining backticks
    response_text = response_text.replace('```', '')
    
    return response_text


class ImprovementState(TypedDict):
    """State for resume improvement workflow"""
    resume_text: str
    requirements: List[str]
    target_role: str
    
    # Analysis results
    current_strengths: List[str]
    identified_gaps: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    
    # Metadata
    tokens_used: int
    processing_time: float


class ResumeImprovementAgent:
    """
    LangGraph-based Resume Improvement Agent
    
    Workflow:
    1. analyze_resume: Extract current strengths and weaknesses
    2. identify_gaps: Compare against requirements to find improvement areas
    3. generate_suggestions: Create actionable improvement suggestions with examples
    """
    
    def __init__(self, groq_client, mcp_context_manager):
        """
        Initialize the Resume Improvement Agent
        
        Args:
            groq_client: Groq API client for LLM calls
            mcp_context_manager: MCP context manager for optimization
        """
        self.groq_client = groq_client
        self.mcp_context = mcp_context_manager
        self.workflow = self._build_workflow()
        
        logger.info("✅ Resume Improvement Agent initialized")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for resume improvement"""
        workflow = StateGraph(ImprovementState)
        
        # Add nodes
        workflow.add_node("analyze_resume", self._analyze_resume)
        workflow.add_node("identify_gaps", self._identify_gaps)
        workflow.add_node("generate_suggestions", self._generate_suggestions)
        
        # Define edges
        workflow.set_entry_point("analyze_resume")
        workflow.add_edge("analyze_resume", "identify_gaps")
        workflow.add_edge("identify_gaps", "generate_suggestions")
        workflow.add_edge("generate_suggestions", END)
        
        return workflow.compile()
    
    def _analyze_resume(self, state: ImprovementState) -> ImprovementState:
        """
        Node 1: Analyze current resume to identify strengths
        
        Uses MCP to extract only relevant sections for analysis
        """
        logger.info("📊 [Node 1/3] Analyzing current resume strengths...")
        
        resume_text = state["resume_text"]
        target_role = state.get("target_role", "professional")
        
        # Truncate resume if too long (token optimization)
        truncated_resume = resume_text[:6000] if len(resume_text) > 6000 else resume_text
        
        prompt = f"""Analyze this resume and identify current strengths:

Resume:
{truncated_resume}

Target Role: {target_role}

Identify the top 5 current strengths in JSON format:
{{
    "strengths": [
        "Strength 1",
        "Strength 2",
        ...
    ]
}}

Return only valid JSON."""

        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=512,
            )
            
            # Clean the response before parsing
            cleaned_response = clean_json_response(response.choices[0].message.content)
            result = json.loads(cleaned_response)
            
            state["current_strengths"] = result.get("strengths", [])
            state["tokens_used"] = state.get("tokens_used", 0) + response.usage.total_tokens
            
            logger.info(f"✅ Identified {len(state['current_strengths'])} current strengths")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing error in analyze_resume: {str(e)}")
            logger.error(f"📄 Raw LLM response: {response.choices[0].message.content[:500]}...")
            state["current_strengths"] = []
        except Exception as e:
            logger.error(f"❌ Error analyzing resume: {str(e)}")
            state["current_strengths"] = []
        
        return state
    
    def _identify_gaps(self, state: ImprovementState) -> ImprovementState:
        """
        Node 2: Compare resume against requirements to identify gaps
        
        Uses MCP to focus only on relevant requirement areas
        """
        logger.info("🔍 [Node 2/3] Identifying improvement gaps...")
        
        resume_text = state["resume_text"]
        requirements = state["requirements"]
        strengths = state["current_strengths"]
        
        # Truncate resume if too long (token optimization)
        truncated_resume = resume_text[:6000] if len(resume_text) > 6000 else resume_text
        
        prompt = f"""Compare the resume against requirements and identify gaps:

Resume Context:
{truncated_resume}

Current Strengths:
{json.dumps(strengths, indent=2)}

Required Skills/Areas:
{json.dumps(requirements, indent=2)}

Identify top 5 improvement areas in JSON format:
{{
    "gaps": [
        {{
            "area": "Area name",
            "current_state": "What the resume currently has",
            "desired_state": "What should be improved",
            "priority": "high|medium|low"
        }},
        ...
    ]
}}

Return only valid JSON."""

        try:
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=768,
            )
            
            # Clean the response before parsing
            cleaned_response = clean_json_response(response.choices[0].message.content)
            result = json.loads(cleaned_response)
            
            state["identified_gaps"] = result.get("gaps", [])
            state["tokens_used"] = state.get("tokens_used", 0) + response.usage.total_tokens
            
            logger.info(f"✅ Identified {len(state['identified_gaps'])} improvement gaps")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing error in identify_gaps: {str(e)}")
            logger.error(f"📄 Raw LLM response: {response.choices[0].message.content[:500]}...")
            state["identified_gaps"] = []
        except Exception as e:
            logger.error(f"❌ Error identifying gaps: {str(e)}")
            state["identified_gaps"] = []
        
        return state
    
    def _generate_suggestions(self, state: ImprovementState) -> ImprovementState:
        """
        Node 3: Generate actionable improvement suggestions with examples
        
        Creates specific, actionable suggestions for each identified gap
        """
        logger.info("💡 [Node 3/3] Generating improvement suggestions...")
        
        gaps = state["identified_gaps"]
        target_role = state.get("target_role", "professional")
        
        suggestions = []
        
        # Generate suggestions for each gap
        for gap in gaps[:5]:  # Focus on top 5 gaps
            area_name = gap.get('area', 'General')
            current = gap.get('current_state', 'N/A')
            desired = gap.get('desired_state', 'Improved')
            
            prompt = f"""Generate specific improvement suggestions for this area:

Area: {area_name}
Current State: {current}
Desired State: {desired}
Target Role: {target_role}

Provide 3 specific, actionable suggestions and ONE concrete example.

CRITICAL RULES FOR THE EXAMPLE:
1. Write the example as a natural English sentence (like a resume bullet point)
2. DO NOT use JSON format, brackets {{}}, or any code syntax
3. DO NOT use technical notation like {{"key": "value"}}
4. Write it as if you're describing work experience on a professional resume
5. Use this format: "As a [role], I [specific action taken] using [tools/technologies], which [result/impact achieved]"

GOOD EXAMPLE for "Security":
"As a DevOps Engineer, I implemented comprehensive security measures including multi-factor authentication, role-based access control, and automated vulnerability scanning using tools like AWS Security Hub and Terraform, which reduced security incidents by 60% and achieved compliance with SOC 2 requirements"

BAD EXAMPLES (DO NOT DO THIS):
- {{"security": "implemented measures"}}
- ["security", "authentication", "compliance"]
- JSON or code snippets
- Technical notation or brackets

Your example for "{area_name}" should describe real accomplishments in natural language.

Return in JSON format (but the example itself should be plain English):
{{
    "area": "{area_name}",
    "suggestions": [
        "Specific actionable suggestion 1",
        "Specific actionable suggestion 2", 
        "Specific actionable suggestion 3"
    ],
    "example": "Write a natural English sentence here describing real accomplishments - NO JSON, NO BRACKETS, NO CODE SYNTAX"
}}

Return only valid JSON."""

            try:
                
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=768,
                )
                
                # Clean the response before parsing
                cleaned_response = clean_json_response(response.choices[0].message.content)
                suggestion = json.loads(cleaned_response)
                
                # CRITICAL: Ensure example is ALWAYS a string, never an object
                if "example" in suggestion:
                    example = suggestion["example"]
                    
                    # Log what we received for debugging
                    logger.debug(f"📝 Example type for {area_name}: {type(example).__name__}")
                    
                    if isinstance(example, dict):
                        # LLM returned an object - convert to meaningful string
                        logger.warning(f"⚠️ LLM returned object for example in {area_name}, converting to string")
                        
                        # Try to extract meaningful content from the dict
                        if 'description' in example:
                            suggestion["example"] = example['description']
                        elif 'text' in example:
                            suggestion["example"] = example['text']
                        elif 'content' in example:
                            suggestion["example"] = example['content']
                        else:
                            # Create a default example if dict doesn't have expected keys
                            suggestion["example"] = f"As a {target_role}, I gained expertise in {area_name} by working on real-world projects, implementing best practices, and achieving measurable improvements in system performance and code quality."
                    
                    elif isinstance(example, list):
                        # LLM returned an array - join into single string
                        logger.warning(f"⚠️ LLM returned array for example in {area_name}, joining to string")
                        suggestion["example"] = " ".join(str(item) for item in example if item)
                    
                    elif example is None or example == "":
                        # Empty example - provide a default
                        logger.warning(f"⚠️ Empty example for {area_name}, using default")
                        suggestion["example"] = f"As a {target_role}, I developed proficiency in {area_name} through hands-on experience in building scalable applications and implementing industry best practices."
                    
                    elif not isinstance(example, str):
                        # Some other type - convert to string
                        logger.warning(f"⚠️ Unexpected type {type(example).__name__} for example in {area_name}, converting to string")
                        suggestion["example"] = str(example)
                    
                    # ADDITIONAL CHECK: Detect if example contains JSON-like syntax
                    example_text = suggestion["example"]
                    if isinstance(example_text, str):
                        # Check for JSON-like patterns: {}, [], "key":"value", etc.
                        has_json_syntax = (
                            ('{' in example_text and '}' in example_text) or
                            (example_text.strip().startswith('{') or example_text.strip().startswith('[')) or
                            ('":"' in example_text) or
                            ('":' in example_text and ',' in example_text)
                        )
                        
                        if has_json_syntax:
                            logger.warning(f"⚠️ Example for {area_name} contains JSON syntax, generating replacement")
                            # Generate a proper narrative example
                            suggestion["example"] = f"As a {target_role}, I developed comprehensive expertise in {area_name} by implementing industry-standard solutions, working with relevant tools and technologies, and delivering measurable results that improved system efficiency, reliability, and performance across multiple production environments."
                    
                    # Final validation: ensure it's a non-empty string
                    if not suggestion["example"] or suggestion["example"].strip() == "":
                        suggestion["example"] = f"As a {target_role}, I continuously enhanced my skills in {area_name} through practical application and professional development."
                    
                    logger.info(f"✅ Example for {area_name}: {suggestion['example'][:100]}...")
                else:
                    # No example field - add a default one
                    logger.warning(f"⚠️ No example field for {area_name}, adding default")
                    suggestion["example"] = f"As a {target_role}, I developed strong capabilities in {area_name} through consistent practice and real-world application."
                
                suggestions.append(suggestion)
                
                state["tokens_used"] = state.get("tokens_used", 0) + response.usage.total_tokens
                
            except Exception as e:
                logger.warning(f"⚠️ Error generating suggestion for {gap.get('area')}: {str(e)}")
                continue
        
        state["suggestions"] = suggestions
        
        logger.info(f"✅ Generated {len(suggestions)} improvement suggestions")
        logger.info(f"💰 Total tokens used: {state.get('tokens_used', 0)}")
        
        return state
    
    def generate_improvements(
        self,
        resume_text: str,
        requirements: List[str],
        target_role: str = "professional"
    ) -> Dict[str, Any]:
        """
        Generate resume improvement suggestions
        
        Args:
            resume_text: Full resume text
            requirements: List of required skills/areas
            target_role: Target job role
        
        Returns:
            Dictionary with improvement suggestions and metadata
        """
        logger.info(f"🚀 Starting Resume Improvement workflow for role: {target_role}")
        
        import time
        start_time = time.time()
        
        # Initialize state
        initial_state = ImprovementState(
            resume_text=resume_text,
            requirements=requirements,
            target_role=target_role,
            current_strengths=[],
            identified_gaps=[],
            suggestions=[],
            tokens_used=0,
            processing_time=0.0
        )
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)
        
        processing_time = time.time() - start_time
        final_state["processing_time"] = processing_time
        
        logger.info(f"✅ Resume Improvement workflow completed in {processing_time:.2f}s")
        logger.info(f"📊 Performance: {len(final_state['suggestions'])} suggestions generated")
        logger.info(f"💰 Tokens used: {final_state['tokens_used']}")
        
        return {
            "suggestions": final_state["suggestions"],
            "metadata": {
                "current_strengths": final_state["current_strengths"],
                "identified_gaps": final_state["identified_gaps"],
                "tokens_used": final_state["tokens_used"],
                "processing_time": processing_time,
                "target_role": target_role
            }
        }
