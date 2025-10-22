"""
MCP Token Optimizer

Purpose: Optimize token usage in LLM calls
Why we need this:
- LLMs charge per token (input + output)
- Large contexts = slow responses + high costs
- Intelligent pruning can reduce costs by 50%+ without losing quality

How it works:
1. Analyze prompt structure
2. Remove redundant information
3. Compress verbose sections
4. Prioritize important context
5. Estimate token usage before calling LLM
"""

import logging
import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TokenStats:
    """
    Statistics about token usage
    
    Why: Monitor and optimize token consumption
    """
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    reduction_percent: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert TokenStats to dictionary for JSON serialization"""
        return {
            'original_tokens': self.original_tokens,
            'optimized_tokens': self.optimized_tokens,
            'tokens_saved': self.tokens_saved,
            'reduction_percent': self.reduction_percent
        }
    

class TokenOptimizer:
    """
    Optimizes prompts and contexts to reduce token usage
    
    Why we use this:
    - Cost savings: Fewer tokens = lower API costs
    - Speed: Less tokens = faster responses
    - Efficiency: Stay within context limits
    
    Key optimizations:
    1. Remove redundant whitespace
    2. Eliminate duplicate information
    3. Compress verbose instructions
    4. Smart truncation of long texts
    """
    
    # Token estimation (rough: 1 token ≈ 4 characters for English)
    CHARS_PER_TOKEN = 4
    
    def __init__(self, max_input_tokens: int = 4000, max_output_tokens: int = 1000):
        """
        Initialize token optimizer
        
        Args:
            max_input_tokens: Maximum tokens for input context
            max_output_tokens: Maximum tokens for LLM output
        """
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.total_tokens_saved = 0
        
        logger.info(f"🎯 Token Optimizer initialized "
                   f"(Max input: {max_input_tokens}, Max output: {max_output_tokens})")
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate number of tokens in text
        
        Why: Know cost before API call
        How: Use character-based approximation
        
        Note: This is a rough estimate. Actual tokenization depends on model.
        For production, use tiktoken library for exact counts.
        """
        # Remove extra whitespace
        cleaned_text = ' '.join(text.split())
        
        # Estimate tokens
        estimated_tokens = len(cleaned_text) // self.CHARS_PER_TOKEN
        
        logger.debug(f"📊 Estimated {estimated_tokens} tokens for text: {text[:50]}...")
        return estimated_tokens
    
    def optimize_prompt(self, prompt: str, aggressive: bool = False) -> Tuple[str, TokenStats]:
        """
        Optimize prompt to reduce token usage
        
        Why: Reduce costs and improve response speed
        How: Apply multiple optimization techniques
        
        Args:
            prompt: Original prompt
            aggressive: If True, apply more aggressive optimizations
        
        Returns:
            (optimized_prompt, stats)
        """
        original_tokens = self.estimate_tokens(prompt)
        logger.info(f"🔧 Optimizing prompt ({original_tokens} tokens)...")
        
        # Apply optimizations
        optimized = prompt
        
        # 1. Remove extra whitespace
        optimized = self._remove_extra_whitespace(optimized)
        
        # 2. Remove redundant phrases
        optimized = self._remove_redundant_phrases(optimized)
        
        # 3. Compress instructions
        optimized = self._compress_instructions(optimized)
        
        if aggressive:
            # 4. More aggressive compression
            optimized = self._aggressive_compression(optimized)
        
        # Calculate stats
        optimized_tokens = self.estimate_tokens(optimized)
        tokens_saved = original_tokens - optimized_tokens
        reduction_percent = (tokens_saved / original_tokens * 100) if original_tokens > 0 else 0
        
        stats = TokenStats(
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            tokens_saved=tokens_saved,
            reduction_percent=round(reduction_percent, 2)
        )
        
        self.total_tokens_saved += tokens_saved
        
        logger.info(f"✅ Optimization complete: {tokens_saved} tokens saved ({reduction_percent:.1f}% reduction)")
        logger.info(f"📈 Total tokens saved: {self.total_tokens_saved}")
        
        return optimized, stats
    
    def _remove_extra_whitespace(self, text: str) -> str:
        """
        Remove unnecessary whitespace
        
        Why: Whitespace counts as tokens!
        """
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Remove spaces around punctuation (careful not to break meaning)
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        
        logger.debug(f"🧹 Removed extra whitespace")
        return text
    
    def _remove_redundant_phrases(self, text: str) -> str:
        """
        Remove common redundant phrases
        
        Why: Some instructions are unnecessarily verbose
        """
        redundant_patterns = [
            (r'please\s+', ''),  # "please analyze" -> "analyze"
            (r'kindly\s+', ''),  # "kindly provide" -> "provide"
            (r'I would like you to\s+', ''),  # Direct instruction
            (r'Can you\s+', ''),  # "Can you analyze" -> "analyze"
            (r'Could you\s+', ''),
        ]
        
        original_length = len(text)
        
        for pattern, replacement in redundant_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        if len(text) < original_length:
            logger.debug(f"✂️ Removed redundant phrases (saved {original_length - len(text)} chars)")
        
        return text
    
    def _compress_instructions(self, text: str) -> str:
        """
        Compress common instruction patterns
        
        Why: Instructions can be more concise
        """
        compressions = [
            ('Based on the following', 'From:'),
            ('According to the information provided', 'From:'),
            ('Taking into consideration', 'Considering'),
            ('in order to', 'to'),
            ('for the purpose of', 'to'),
            ('due to the fact that', 'because'),
            ('at this point in time', 'now'),
            ('in the event that', 'if'),
        ]
        
        original_length = len(text)
        
        for verbose, concise in compressions:
            text = re.sub(verbose, concise, text, flags=re.IGNORECASE)
        
        if len(text) < original_length:
            logger.debug(f"📉 Compressed instructions (saved {original_length - len(text)} chars)")
        
        return text
    
    def _aggressive_compression(self, text: str) -> str:
        """
        Apply aggressive compression techniques
        
        Why: Maximum token savings (use carefully - may impact quality)
        How: Remove filler words, use abbreviations
        """
        # Remove filler words
        filler_words = [
            'basically', 'actually', 'literally', 'very', 'really', 
            'quite', 'somewhat', 'perhaps', 'maybe'
        ]
        
        pattern = r'\b(' + '|'.join(filler_words) + r')\b'
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove extra articles where safe
        # text = re.sub(r'\ba\s+', '', text)  # Commented: too aggressive
        
        logger.debug(f"⚡ Applied aggressive compression")
        return text
    
    def optimize_context(self, context: List[Dict[str, str]], 
                        max_messages: int = 10) -> List[Dict[str, str]]:
        """
        Optimize conversation context
        
        Why: Long conversations exceed token limits
        How: Keep most recent + most important messages
        
        Args:
            context: List of conversation messages
            max_messages: Maximum messages to keep
        
        Returns:
            Optimized context
        """
        if len(context) <= max_messages:
            return context
        
        logger.info(f"🔄 Optimizing context: {len(context)} -> {max_messages} messages")
        
        # Strategy: Keep first (system) + last N messages
        optimized = []
        
        # Keep system message if exists
        if context and context[0].get('role') == 'system':
            optimized.append(context[0])
            context = context[1:]
        
        # Keep most recent messages
        recent_count = max_messages - len(optimized)
        optimized.extend(context[-recent_count:])
        
        original_tokens = sum(self.estimate_tokens(msg.get('content', '')) for msg in context)
        optimized_tokens = sum(self.estimate_tokens(msg.get('content', '')) for msg in optimized)
        
        logger.info(f"✅ Context optimized: {original_tokens} -> {optimized_tokens} tokens")
        
        return optimized
    
    def truncate_text(self, text: str, max_tokens: int) -> str:
        """
        Intelligently truncate text to fit token limit
        
        Why: Some inputs are too long
        How: Truncate while preserving key information
        
        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
        
        Returns:
            Truncated text
        """
        current_tokens = self.estimate_tokens(text)
        
        if current_tokens <= max_tokens:
            return text
        
        logger.warning(f"⚠️ Text exceeds limit ({current_tokens} > {max_tokens} tokens), truncating...")
        
        # Calculate how many characters to keep
        max_chars = max_tokens * self.CHARS_PER_TOKEN
        
        # Truncate at sentence boundary if possible
        truncated = text[:max_chars]
        
        # Try to end at a sentence
        last_period = truncated.rfind('.')
        last_newline = truncated.rfind('\n')
        
        cut_point = max(last_period, last_newline)
        if cut_point > max_chars * 0.8:  # If we're within 80%, use it
            truncated = truncated[:cut_point + 1]
        
        truncated += "\n[... truncated for length ...]"
        
        new_tokens = self.estimate_tokens(truncated)
        logger.info(f"✂️ Truncated: {current_tokens} -> {new_tokens} tokens")
        
        return truncated
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get optimizer statistics
        
        Why: Monitor optimization effectiveness
        """
        stats = {
            'total_tokens_saved': self.total_tokens_saved,
            'max_input_tokens': self.max_input_tokens,
            'max_output_tokens': self.max_output_tokens,
        }
        
        logger.info(f"📊 Optimizer stats: {stats}")
        return stats


# Example usage demonstration
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create optimizer
    optimizer = TokenOptimizer(max_input_tokens=4000)
    
    # Example verbose prompt
    verbose_prompt = """
    Based on the following resume information provided below, please analyze and 
    tell me what are the candidate's technical skills in Python programming language.
    Can you also provide information about their experience level? I would like you to 
    be very detailed in your response.
    
    Resume:
    John Doe has worked with Python for 5 years. He knows Django and Flask.
    """
    
    print("Original prompt:")
    print(verbose_prompt)
    print(f"\nEstimated tokens: {optimizer.estimate_tokens(verbose_prompt)}")
    
    # Optimize
    optimized, stats = optimizer.optimize_prompt(verbose_prompt)
    
    print(f"\n{'='*50}")
    print("Optimized prompt:")
    print(optimized)
    print(f"\n📊 Stats:")
    print(f"  Original: {stats.original_tokens} tokens")
    print(f"  Optimized: {stats.optimized_tokens} tokens")
    print(f"  Saved: {stats.tokens_saved} tokens ({stats.reduction_percent}%)")
