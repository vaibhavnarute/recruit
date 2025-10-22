"""
Improved Resume Generation Agent with LangGraph + MCP Integration

This agent generates an improved version of a resume using:
- LangGraph workflow for structured generation
- MCP (Model Context Protocol) for efficient context management
- Multi-step process: extract → enhance → format → validate
"""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
import logging
import json

logger = logging.getLogger(__name__)


class ImprovedResumeState(TypedDict):
    """State for improved resume generation workflow"""
    resume_text: str
    target_role: str
    skills_to_highlight: List[str]
    
    # Processing results
    extracted_sections: Dict[str, str]
    enhanced_content: Dict[str, str]
    formatted_resume: str
    
    # Metadata
    tokens_used: int
    processing_time: float


class ImprovedResumeAgent:
    """
    LangGraph-based Improved Resume Generation Agent
    
    Workflow:
    1. extract_sections: Parse resume into structured sections
    2. enhance_content: Improve each section with strong language and metrics
    3. format_resume: Combine enhanced sections into professional format
    4. validate_output: Ensure quality and completeness
    """
    
    def __init__(self, groq_client, mcp_context_manager):
        """
        Initialize the Improved Resume Agent
        
        Args:
            groq_client: Groq API client for LLM calls
            mcp_context_manager: MCP context manager for optimization
        """
        self.groq_client = groq_client
        self.mcp_context = mcp_context_manager
        self.workflow = self._build_workflow()
        
        logger.info("✅ Improved Resume Agent initialized")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for resume improvement"""
        workflow = StateGraph(ImprovedResumeState)
        
        # Add nodes
        workflow.add_node("extract_sections", self._extract_sections)
        workflow.add_node("enhance_content", self._enhance_content)
        workflow.add_node("format_resume", self._format_resume)
        workflow.add_node("validate_output", self._validate_output)
        
        # Define edges
        workflow.set_entry_point("extract_sections")
        workflow.add_edge("extract_sections", "enhance_content")
        workflow.add_edge("enhance_content", "format_resume")
        workflow.add_edge("format_resume", "validate_output")
        workflow.add_edge("validate_output", END)
        
        return workflow.compile()
    
    def _extract_sections(self, state: ImprovedResumeState) -> ImprovedResumeState:
        """
        Node 1: Extract and structure resume sections
        
        Uses MCP to intelligently parse different resume sections
        """
        logger.info("📝 [Node 1/4] Extracting resume sections...")
        
        resume_text = state["resume_text"]
        
        # Simple section extraction (no MCP optimization needed here)
        # The LLM will extract sections directly from the resume
        
        prompt = f"""Extract the following sections from this resume:
- Summary/Objective
- Skills
- Work Experience
- Education
- Certifications (if present)
- Projects (if present)

Resume:
{resume_text[:8000]}

Return in JSON format:
{{
    "summary": "extracted summary text",
    "skills": "extracted skills text",
    "experience": "extracted experience text",
    "education": "extracted education text",
    "certifications": "extracted certifications text or empty",
    "projects": "extracted projects text or empty"
}}

Return only valid JSON."""

        response = self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        response_text = response.choices[0].message.content.strip()
        
        # Clean JSON response
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            response_text = '\n'.join(lines).strip()
        response_text = response_text.replace('```', '')
        
        try:
            sections = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse extracted sections: {e}")
            # Fallback: treat entire resume as one section
            sections = {
                "summary": "",
                "skills": "",
                "experience": resume_text,
                "education": "",
                "certifications": "",
                "projects": ""
            }
        
        state["extracted_sections"] = sections
        logger.info(f"✅ Extracted {len(sections)} resume sections")
        
        return state
    
    def _enhance_content(self, state: ImprovedResumeState) -> ImprovedResumeState:
        """
        Node 2: Enhance each section with strong action verbs and metrics
        
        Improves content while maintaining factual accuracy
        """
        logger.info("✨ [Node 2/4] Enhancing resume content...")
        
        sections = state["extracted_sections"]
        target_role = state["target_role"]
        skills = state["skills_to_highlight"]
        
        enhanced = {}
        
        # Enhance Professional Summary
        if sections.get("summary"):
            prompt = f"""Improve this professional summary for a {target_role} role:

Original:
{sections["summary"]}

Skills to highlight: {', '.join(skills[:5])}

Create a compelling 3-4 sentence professional summary that:
- Highlights key achievements and years of experience
- Emphasizes relevant skills: {', '.join(skills[:3])}
- Uses strong, confident language
- Focuses on value proposition for {target_role}

Return only the improved summary, no other text."""

            try:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.6,
                    max_tokens=256,
                )
                
                enhanced["summary"] = response.choices[0].message.content.strip()
                state["tokens_used"] = state.get("tokens_used", 0) + response.usage.total_tokens
                
            except Exception as e:
                logger.warning(f"⚠️ Error enhancing summary: {str(e)}")
                enhanced["summary"] = sections.get("summary", "")
        
        # Enhance Skills Section
        if sections.get("skills"):
            prompt = f"""Organize and enhance this skills section for a {target_role} role:

Original:
{sections["skills"]}

Priority skills: {', '.join(skills)}

Create a categorized skills section that:
- Groups related skills together (Technical, Tools, Soft Skills)
- Prioritizes: {', '.join(skills[:5])}
- Uses industry-standard terminology
- Is ATS-friendly

Return only the improved skills section, no other text."""

            try:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                    max_tokens=384,
                )
                
                enhanced["skills"] = response.choices[0].message.content.strip()
                state["tokens_used"] = state.get("tokens_used", 0) + response.usage.total_tokens
                
            except Exception as e:
                logger.warning(f"⚠️ Error enhancing skills: {str(e)}")
                enhanced["skills"] = sections.get("skills", "")
        
        # Enhance Experience Section
        if sections.get("experience"):
            prompt = f"""Enhance this professional experience section for a {target_role} role:

Original:
{sections["experience"]}

Target role: {target_role}
Skills to emphasize: {', '.join(skills[:5])}

Improve each job entry by:
- Starting bullets with strong action verbs (Led, Developed, Implemented, etc.)
- Adding specific metrics and results where possible (e.g., "increased by 30%")
- Emphasizing achievements over responsibilities
- Highlighting experiences relevant to {target_role}
- Using STAR method (Situation, Task, Action, Result) where applicable

Return only the improved experience section, no other text."""

            try:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=1024,
                )
                
                enhanced["experience"] = response.choices[0].message.content.strip()
                state["tokens_used"] = state.get("tokens_used", 0) + response.usage.total_tokens
                
            except Exception as e:
                logger.warning(f"⚠️ Error enhancing experience: {str(e)}")
                enhanced["experience"] = sections.get("experience", "")
        
        # Keep other sections as-is but clean them up
        for section in ["education", "certifications", "projects"]:
            if sections.get(section):
                enhanced[section] = sections[section]
        
        state["enhanced_content"] = enhanced
        
        logger.info(f"✅ Enhanced {len(enhanced)} sections")
        logger.info(f"💰 Tokens used so far: {state.get('tokens_used', 0)}")
        
        return state
    
    def _format_resume(self, state: ImprovedResumeState) -> ImprovedResumeState:
        """
        Node 3: Format enhanced content into professional resume
        
        Combines all sections with proper formatting and structure
        """
        logger.info("📄 [Node 3/4] Formatting improved resume...")
        
        enhanced = state["enhanced_content"]
        target_role = state["target_role"]
        
        # Build certifications and projects sections separately to avoid f-string backslash issues
        certifications_section = ""
        if enhanced.get('certifications'):
            certifications_section = f"\nCertifications:\n{enhanced.get('certifications', '')}\n"
        
        projects_section = ""
        if enhanced.get('projects'):
            projects_section = f"\nProjects:\n{enhanced.get('projects', '')}\n"
        
        prompt = f"""Format these enhanced resume sections into a professional, ATS-friendly resume:

Professional Summary:
{enhanced.get('summary', '')}

Skills:
{enhanced.get('skills', '')}

Professional Experience:
{enhanced.get('experience', '')}

Education:
{enhanced.get('education', '')}
{certifications_section}{projects_section}
Target Role: {target_role}

Create a polished, professional resume that:
- Uses clear section headers
- Has consistent formatting throughout
- Is easy to read and scan
- Is optimized for ATS systems
- Emphasizes relevance to {target_role}
- Uses bullet points effectively
- Maintains professional tone

Return only the complete formatted resume, no other text or explanations."""

        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2048,
            )
            
            state["formatted_resume"] = response.choices[0].message.content.strip()
            state["tokens_used"] = state.get("tokens_used", 0) + response.usage.total_tokens
            
            logger.info("✅ Resume formatted successfully")
            
        except Exception as e:
            logger.error(f"❌ Error formatting resume: {str(e)}")
            # Fallback: concatenate sections
            formatted = "\n\n".join([
                "PROFESSIONAL SUMMARY",
                enhanced.get('summary', ''),
                "\nSKILLS",
                enhanced.get('skills', ''),
                "\nPROFESSIONAL EXPERIENCE",
                enhanced.get('experience', ''),
                "\nEDUCATION",
                enhanced.get('education', ''),
            ])
            if enhanced.get('certifications'):
                formatted += f"\n\nCERTIFICATIONS\n{enhanced['certifications']}"
            if enhanced.get('projects'):
                formatted += f"\n\nPROJECTS\n{enhanced['projects']}"
            
            state["formatted_resume"] = formatted
        
        return state
    
    def _validate_output(self, state: ImprovedResumeState) -> ImprovedResumeState:
        """
        Node 4: Validate the improved resume quality
        
        Ensures the output is complete and high quality
        """
        logger.info("✔️ [Node 4/4] Validating improved resume...")
        
        formatted = state["formatted_resume"]
        original = state["resume_text"]
        
        # Basic validation checks
        if not formatted or len(formatted) < 200:
            logger.warning("⚠️ Generated resume too short, using enhanced sections")
            enhanced = state["enhanced_content"]
            formatted = "\n\n".join([
                f"PROFESSIONAL SUMMARY\n{enhanced.get('summary', '')}",
                f"\nSKILLS\n{enhanced.get('skills', '')}",
                f"\nPROFESSIONAL EXPERIENCE\n{enhanced.get('experience', '')}",
                f"\nEDUCATION\n{enhanced.get('education', '')}",
            ])
            state["formatted_resume"] = formatted
        
        if formatted == original:
            logger.warning("⚠️ Improved resume identical to original")
        
        logger.info(f"✅ Resume validated successfully")
        logger.info(f"📊 Final resume length: {len(formatted)} characters")
        logger.info(f"💰 Total tokens used: {state.get('tokens_used', 0)}")
        
        return state
    
    def generate_improved_resume(
        self,
        resume_text: str,
        target_role: str,
        skills_to_highlight: List[str]
    ) -> Dict[str, Any]:
        """
        Generate an improved version of the resume
        
        Args:
            resume_text: Original resume text
            target_role: Target job role
            skills_to_highlight: Skills to emphasize
        
        Returns:
            Dictionary with improved resume and metadata
        """
        logger.info(f"🚀 Starting Improved Resume workflow for role: {target_role}")
        
        import time
        start_time = time.time()
        
        # Initialize state
        initial_state = ImprovedResumeState(
            resume_text=resume_text,
            target_role=target_role,
            skills_to_highlight=skills_to_highlight,
            extracted_sections={},
            enhanced_content={},
            formatted_resume="",
            tokens_used=0,
            processing_time=0.0
        )
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)
        
        processing_time = time.time() - start_time
        final_state["processing_time"] = processing_time
        
        logger.info(f"✅ Improved Resume workflow completed in {processing_time:.2f}s")
        logger.info(f"📊 Generated {len(final_state['formatted_resume'])} character resume")
        logger.info(f"💰 Tokens used: {final_state['tokens_used']}")
        
        return {
            "improved_resume": final_state["formatted_resume"],
            "metadata": {
                "extracted_sections": list(final_state["extracted_sections"].keys()),
                "enhanced_sections": list(final_state["enhanced_content"].keys()),
                "tokens_used": final_state["tokens_used"],
                "processing_time": processing_time,
                "target_role": target_role,
                "resume_length": len(final_state["formatted_resume"])
            }
        }
