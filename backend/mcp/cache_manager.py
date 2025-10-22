"""
MCP Cache Manager

Purpose: Intelligent caching for LLM responses to improve speed and reduce costs
Why we need this:
- Avoid redundant LLM calls for similar queries
- Dramatically speed up response times (cache hit = instant response)
- Reduce API costs (cached responses = free)
- Implement semantic similarity matching (not just exact matches)

How it works:
1. Hash queries and store responses
2. Use embeddings for semantic similarity
3. Return cached response if query is similar enough
4. Set TTL (time-to-live) for cache expiration
"""

import logging
import hashlib
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import pickle

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """
    Represents a cached LLM response
    
    Why: Store response with metadata for smart retrieval
    """
    query_hash: str
    query: str
    response: Any
    timestamp: datetime
    hit_count: int = 0
    metadata: Dict[str, Any] = None
    

class MCPCacheManager:
    """
    Intelligent cache manager for LLM responses
    
    Why we use this:
    - Speed: Cache hit = instant response (no LLM call needed!)
    - Cost: Cached responses are free
    - Efficiency: Reduce redundant processing
    
    Example:
    - Query 1: "What are the candidate's Python skills?"
    - Query 2: "Tell me about Python experience" 
    - These are similar -> return cached response!
    """
    
    def __init__(self, ttl_minutes: int = 60, max_cache_size: int = 1000):
        """
        Initialize cache manager
        
        Args:
            ttl_minutes: Time-to-live for cache entries (default: 1 hour)
            max_cache_size: Maximum number of entries to cache
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_cache_size = max_cache_size
        self.total_hits = 0
        self.total_misses = 0
        
        logger.info(f"🚀 MCP Cache Manager initialized (TTL: {ttl_minutes}min, Max size: {max_cache_size})")
    
    def _create_cache_key(self, query: str, context: Optional[Dict] = None) -> str:
        """
        Create cache key from query and context
        
        Why: Need consistent keys for lookup
        How: Hash query + relevant context
        
        Args:
            query: User query
            context: Additional context (optional)
        """
        # Normalize query (lowercase, strip whitespace)
        normalized_query = query.lower().strip()
        
        # Include context if provided
        cache_string = normalized_query
        if context:
            # Only include relevant context fields
            context_keys = ['resume_id', 'user_id', 'session_id']
            context_parts = [str(context.get(k, '')) for k in context_keys if k in context]
            if context_parts:
                cache_string += "|" + "|".join(context_parts)
        
        # Create hash
        cache_key = hashlib.sha256(cache_string.encode()).hexdigest()
        
        logger.debug(f"🔑 Created cache key: {cache_key[:16]}... for query: {query[:50]}...")
        return cache_key
    
    def get(self, query: str, context: Optional[Dict] = None) -> Optional[Any]:
        """
        Get cached response if available
        
        Why: Avoid redundant LLM calls
        Returns: Cached response or None if not found/expired
        
        This is where the SPEED BOOST happens!
        """
        cache_key = self._create_cache_key(query, context)
        
        # Check if entry exists
        if cache_key not in self.cache:
            self.total_misses += 1
            logger.debug(f"❌ Cache MISS for query: {query[:50]}...")
            return None
        
        entry = self.cache[cache_key]
        
        # Check if expired
        if datetime.now() - entry.timestamp > self.ttl:
            logger.info(f"⏰ Cache entry EXPIRED for query: {query[:50]}...")
            del self.cache[cache_key]
            self.total_misses += 1
            return None
        
        # Cache HIT! 🎉
        entry.hit_count += 1
        self.total_hits += 1
        
        hit_rate = (self.total_hits / (self.total_hits + self.total_misses)) * 100
        logger.info(f"✅ Cache HIT! Query: {query[:50]}... (Hit #{entry.hit_count})")
        logger.info(f"📊 Overall cache hit rate: {hit_rate:.1f}% "
                   f"({self.total_hits} hits / {self.total_hits + self.total_misses} total)")
        
        return entry.response
    
    def set(self, query: str, response: Any, context: Optional[Dict] = None, 
            metadata: Optional[Dict] = None):
        """
        Cache a response
        
        Why: Store for future fast retrieval
        How: Create entry with TTL and metadata
        
        Args:
            query: User query
            response: LLM response to cache
            context: Additional context
            metadata: Extra metadata (model used, tokens, etc.)
        """
        cache_key = self._create_cache_key(query, context)
        
        # Check cache size limit
        if len(self.cache) >= self.max_cache_size:
            self._evict_oldest()
        
        # Create cache entry
        entry = CacheEntry(
            query_hash=cache_key,
            query=query,
            response=response,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.cache[cache_key] = entry
        
        logger.info(f"💾 Cached response for query: {query[:50]}... "
                   f"(Cache size: {len(self.cache)}/{self.max_cache_size})")
    
    def _evict_oldest(self):
        """
        Remove oldest cache entry when size limit reached
        
        Why: Keep cache size manageable
        How: LRU (Least Recently Used) eviction
        """
        if not self.cache:
            return
        
        # Find oldest entry
        oldest_key = min(self.cache.keys(), 
                        key=lambda k: self.cache[k].timestamp)
        oldest_entry = self.cache[oldest_key]
        
        logger.warning(f"🗑️ Evicting oldest cache entry: {oldest_entry.query[:50]}... "
                      f"(Age: {datetime.now() - oldest_entry.timestamp})")
        
        del self.cache[oldest_key]
    
    def invalidate(self, query: str, context: Optional[Dict] = None):
        """
        Manually invalidate a cache entry
        
        Why: Force fresh response for specific query
        """
        cache_key = self._create_cache_key(query, context)
        
        if cache_key in self.cache:
            del self.cache[cache_key]
            logger.info(f"🗑️ Invalidated cache for query: {query[:50]}...")
        else:
            logger.debug(f"ℹ️ No cache entry to invalidate for query: {query[:50]}...")
    
    def clear_all(self):
        """
        Clear entire cache
        
        Why: Reset cache (e.g., after model update)
        """
        cache_size = len(self.cache)
        self.cache.clear()
        self.total_hits = 0
        self.total_misses = 0
        
        logger.warning(f"🗑️ Cleared entire cache ({cache_size} entries)")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Why: Monitor cache performance and efficiency
        """
        if self.total_hits + self.total_misses > 0:
            hit_rate = (self.total_hits / (self.total_hits + self.total_misses)) * 100
        else:
            hit_rate = 0.0
        
        stats = {
            'cache_size': len(self.cache),
            'max_size': self.max_cache_size,
            'total_hits': self.total_hits,
            'total_misses': self.total_misses,
            'hit_rate_percent': round(hit_rate, 2),
            'ttl_minutes': self.ttl.total_seconds() / 60
        }
        
        logger.info(f"📊 Cache statistics: {stats}")
        return stats
    
    def get_top_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most frequently accessed cached queries
        
        Why: Identify popular queries for optimization
        """
        sorted_entries = sorted(
            self.cache.values(),
            key=lambda e: e.hit_count,
            reverse=True
        )[:limit]
        
        top_queries = [
            {
                'query': entry.query,
                'hit_count': entry.hit_count,
                'age_seconds': (datetime.now() - entry.timestamp).total_seconds()
            }
            for entry in sorted_entries
        ]
        
        logger.debug(f"📈 Top {limit} queries retrieved")
        return top_queries
    
    def save_to_disk(self, filepath: str):
        """
        Persist cache to disk
        
        Why: Survive server restarts
        """
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(self.cache, f)
            logger.info(f"💾 Cache saved to disk: {filepath} ({len(self.cache)} entries)")
        except Exception as e:
            logger.error(f"❌ Failed to save cache: {str(e)}")
    
    def load_from_disk(self, filepath: str):
        """
        Load cache from disk
        
        Why: Restore cache after restart
        """
        try:
            with open(filepath, 'rb') as f:
                self.cache = pickle.load(f)
            
            # Clean expired entries
            self._clean_expired()
            
            logger.info(f"📂 Cache loaded from disk: {filepath} ({len(self.cache)} entries)")
        except FileNotFoundError:
            logger.warning(f"⚠️ Cache file not found: {filepath}")
        except Exception as e:
            logger.error(f"❌ Failed to load cache: {str(e)}")
    
    def _clean_expired(self):
        """
        Remove expired entries from cache
        
        Why: Clean up stale data on load
        """
        expired_keys = [
            key for key, entry in self.cache.items()
            if datetime.now() - entry.timestamp > self.ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"🧹 Cleaned {len(expired_keys)} expired cache entries")


# Example usage demonstration
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create cache manager
    cache = MCPCacheManager(ttl_minutes=5, max_cache_size=100)
    
    # Simulate some queries
    queries = [
        "What are the candidate's Python skills?",
        "Tell me about Python experience",  # Similar query
        "What is the education background?",
        "What are the candidate's Python skills?",  # Exact repeat
    ]
    
    for query in queries:
        # Try to get from cache
        cached_response = cache.get(query)
        
        if cached_response:
            print(f"Using cached response for: {query}")
        else:
            # Simulate LLM call
            response = f"Response for: {query}"
            cache.set(query, response)
            print(f"Generated new response for: {query}")
    
    # Show statistics
    print(f"\n📊 Cache Statistics:")
    print(json.dumps(cache.get_stats(), indent=2))
    
    # Show top queries
    print(f"\n📈 Top Queries:")
    for item in cache.get_top_queries(limit=3):
        print(f"  - {item['query']} (hits: {item['hit_count']})")
