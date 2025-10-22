"""
MCP Context Manager

Purpose: Optimizes context handling for LLM interactions
Why we need this:
- Reduces token usage by intelligently summarizing/compressing context
- Maintains conversation state efficiently
- Implements sliding window for long conversations
- Prioritizes important context over verbose details

How it works:
1. Tracks conversation history
2. Compresses old messages when context gets too large
3. Maintains semantic coherence while reducing tokens
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ContextWindow:
    """
    Represents a sliding window of conversation context
    
    Why: We can't send unlimited history to LLM (token limits)
    How: Keep recent messages + compressed summary of old ones
    """
    messages: List[Dict[str, Any]] = field(default_factory=list)
    max_messages: int = 10  # Keep last 10 messages
    summary: Optional[str] = None
    total_tokens_saved: int = 0
    

class MCPContextManager:
    """
    Main context manager for MCP protocol
    
    Why we use this:
    - Prevents hitting token limits
    - Speeds up LLM responses (less tokens = faster)
    - Maintains conversation coherence
    - Reduces API costs
    """
    
    def __init__(self, max_context_length: int = 4000):
        """
        Initialize context manager
        
        Args:
            max_context_length: Maximum tokens to keep in context
        """
        self.max_context_length = max_context_length
        self.context_windows: Dict[str, ContextWindow] = {}
        
        logger.info(f"🔧 MCP Context Manager initialized with max length: {max_context_length}")
    
    def create_context_id(self, user_id: str, session_id: str) -> str:
        """
        Create unique context ID for tracking conversations
        
        Why: Multiple users/sessions need separate contexts
        """
        context_string = f"{user_id}:{session_id}:{datetime.now().date()}"
        context_id = hashlib.md5(context_string.encode()).hexdigest()
        
        logger.debug(f"📝 Created context ID: {context_id} for user: {user_id}")
        return context_id
    
    def add_message(self, context_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """
        Add message to context window with intelligent compression
        
        Why: Track conversation history efficiently
        How: Add new message, compress old ones if needed
        
        Args:
            context_id: Unique context identifier
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata (tokens, timestamp, etc.)
        """
        if context_id not in self.context_windows:
            self.context_windows[context_id] = ContextWindow()
            logger.info(f"🆕 Created new context window for ID: {context_id}")
        
        window = self.context_windows[context_id]
        
        # Add message
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        window.messages.append(message)
        
        logger.debug(f"➕ Added {role} message to context {context_id}: {content[:50]}...")
        
        # Compress if needed
        if len(window.messages) > window.max_messages:
            self._compress_context(context_id)
    
    def _compress_context(self, context_id: str):
        """
        Compress old messages to save tokens
        
        Why: Keep context under token limit
        How: Summarize old messages, keep recent ones
        
        This is the KEY optimization that MCP provides!
        """
        window = self.context_windows[context_id]
        
        if len(window.messages) <= window.max_messages:
            return
        
        # Calculate how many to compress
        messages_to_compress = len(window.messages) - window.max_messages
        old_messages = window.messages[:messages_to_compress]
        
        # Simple compression: keep only key information
        compressed_summary = self._create_summary(old_messages)
        
        # Estimate tokens saved (rough estimate: 1 token ~= 4 characters)
        original_tokens = sum(len(msg['content']) // 4 for msg in old_messages)
        compressed_tokens = len(compressed_summary) // 4
        tokens_saved = original_tokens - compressed_tokens
        
        window.total_tokens_saved += tokens_saved
        window.summary = compressed_summary
        window.messages = window.messages[messages_to_compress:]
        
        logger.info(f"🗜️ Compressed {messages_to_compress} messages in context {context_id}")
        logger.info(f"💰 Tokens saved: {tokens_saved} (Total saved: {window.total_tokens_saved})")
    
    def _create_summary(self, messages: List[Dict[str, Any]]) -> str:
        """
        Create concise summary of old messages
        
        Why: Maintain context while reducing tokens
        How: Extract key points from conversation
        """
        # Simple summarization (in production, you might use an LLM for this)
        summary_parts = []
        
        for msg in messages:
            role = msg['role']
            content = msg['content']
            # Keep first 100 chars of each message
            snippet = content[:100] + "..." if len(content) > 100 else content
            summary_parts.append(f"{role}: {snippet}")
        
        summary = " | ".join(summary_parts)
        logger.debug(f"📋 Created summary: {summary[:100]}...")
        return summary
    
    def build_context(self, context_items: List[str]) -> str:
        """
        Build formatted context string from list of items
        
        Why: Format context information for LLM prompts
        How: Join items with newlines and optimize length
        
        Args:
            context_items: List of context strings to combine
            
        Returns:
            Formatted context string
        """
        if not context_items:
            return ""
        
        # Join items with newlines
        context = "\n".join(context_items)
        
        # Optimize if too long
        if len(context) > self.max_context_length:
            # Truncate and add ellipsis
            context = context[:self.max_context_length - 3] + "..."
            logger.warning(f"⚠️ Context truncated to {self.max_context_length} chars")
        
        logger.debug(f"🔨 Built context: {len(context)} chars")
        return context
    
    def get_context(self, context_id: str) -> List[Dict[str, Any]]:
        """
        Get optimized context for LLM
        
        Why: Retrieve conversation history efficiently
        Returns: Messages + summary if available
        """
        if context_id not in self.context_windows:
            logger.warning(f"⚠️ Context ID {context_id} not found, returning empty context")
            return []
        
        window = self.context_windows[context_id]
        
        # Build context: summary (if exists) + recent messages
        context = []
        
        if window.summary:
            context.append({
                'role': 'system',
                'content': f"Previous conversation summary: {window.summary}"
            })
            logger.debug(f"📦 Including compressed summary in context")
        
        context.extend(window.messages)
        
        logger.info(f"📤 Retrieved context for {context_id}: {len(context)} messages "
                   f"(saved {window.total_tokens_saved} tokens)")
        
        return context
    
    def clear_context(self, context_id: str):
        """
        Clear context for a session
        
        Why: Clean up after conversation ends
        """
        if context_id in self.context_windows:
            del self.context_windows[context_id]
            logger.info(f"🗑️ Cleared context for ID: {context_id}")
    
    def get_stats(self, context_id: str) -> Dict[str, Any]:
        """
        Get statistics about context usage
        
        Why: Monitor efficiency and optimization
        """
        if context_id not in self.context_windows:
            return {"error": "Context not found"}
        
        window = self.context_windows[context_id]
        
        stats = {
            'total_messages': len(window.messages),
            'has_summary': window.summary is not None,
            'total_tokens_saved': window.total_tokens_saved,
            'compression_ratio': self._calculate_compression_ratio(window)
        }
        
        logger.debug(f"📊 Context stats for {context_id}: {stats}")
        return stats
    
    def _calculate_compression_ratio(self, window: ContextWindow) -> float:
        """
        Calculate how much compression was achieved
        
        Returns: Ratio (e.g., 0.3 means 30% of original size)
        """
        if not window.summary:
            return 1.0
        
        # Rough estimate
        current_size = len(window.summary) + sum(len(msg['content']) for msg in window.messages)
        # Assume we would have had max_messages * 2 without compression
        original_size = window.max_messages * 2 * 500  # Assume 500 chars per message
        
        ratio = current_size / original_size if original_size > 0 else 1.0
        return round(ratio, 2)


# Example usage demonstration
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create context manager
    mcp = MCPContextManager(max_context_length=4000)
    
    # Simulate a conversation
    context_id = mcp.create_context_id("user123", "session456")
    
    # Add messages
    for i in range(15):
        mcp.add_message(context_id, "user", f"This is user message {i} " * 10)
        mcp.add_message(context_id, "assistant", f"This is assistant response {i} " * 10)
    
    # Get optimized context
    context = mcp.get_context(context_id)
    print(f"\n📊 Final context size: {len(context)} messages")
    
    # Get stats
    stats = mcp.get_stats(context_id)
    print(f"📈 Statistics: {stats}")
