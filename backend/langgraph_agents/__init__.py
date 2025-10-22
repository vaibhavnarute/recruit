"""
LangGraph Package for AI Recruiter

This package contains LangGraph-based workflows for:
- Resume Analysis (multi-step evaluation)
- Q&A (context-aware answering)

Why LangGraph?
- Stateful workflows (maintain conversation context)
- Complex multi-step processes (not just one-shot prompts)
- Conditional branching (adapt based on results)
- Better error handling and retry logic
- Observable and debuggable execution
"""

from langgraph_agents.resume_analysis_agent import ResumeAnalysisAgent
from langgraph_agents.qa_agent import ResumeQAAgent

__all__ = [
    'ResumeAnalysisAgent',
    'ResumeQAAgent'
]
