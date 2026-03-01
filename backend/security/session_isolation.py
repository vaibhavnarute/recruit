"""
Session Isolation & Memory Sandboxing
Prevents data overlap between parallel sessions
"""

import logging
import psutil
import os
import gc
import weakref
from typing import Dict, Any, Optional, Set, List
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class SessionSandbox:
    """
    Per-session memory sandbox
    
    Tracks and isolates:
    - Memory buffers
    - Temporary data
    - Cache entries
    - File handles
    - Network connections
    """
    session_id: str
    created_at: datetime
    
    # Memory tracking
    memory_buffers: Dict[str, Any] = field(default_factory=dict)
    temp_data: Dict[str, Any] = field(default_factory=dict)
    cache_keys: Set[str] = field(default_factory=set)
    
    # Resource tracking
    file_handles: List[Any] = field(default_factory=list)
    open_connections: Set[str] = field(default_factory=set)
    
    # Metadata
    total_memory_allocated: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    
    # Status
    isolated: bool = True
    cleaned: bool = False


class SessionIsolationManager:
    """
    Manages session isolation and memory sandboxing
    
    Features:
    - Per-session memory isolation
    - Automatic buffer cleanup
    - Resource leak prevention
    - Cross-session data protection
    - Memory usage tracking
    """
    
    def __init__(self):
        """Initialize Session Isolation Manager"""
        logger.info("🔒 Initializing SessionIsolationManager")
        
        # Session sandboxes
        self.sandboxes: Dict[str, SessionSandbox] = {}
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Memory limits (MB)
        self.max_session_memory_mb = int(os.getenv("MAX_SESSION_MEMORY_MB", "100"))
        self.max_total_memory_mb = int(os.getenv("MAX_TOTAL_MEMORY_MB", "1000"))
        
        # Session limits
        self.max_active_sessions = int(os.getenv("MAX_ACTIVE_SESSIONS", "50"))
        
        # Weak references for automatic cleanup
        self.weak_refs: Dict[str, weakref.ref] = {}
        
        logger.info("✅ SessionIsolationManager initialized")
        logger.info(f"   Max session memory: {self.max_session_memory_mb} MB")
        logger.info(f"   Max total memory: {self.max_total_memory_mb} MB")
        logger.info(f"   Max active sessions: {self.max_active_sessions}")
    
    def create_sandbox(self, session_id: str) -> SessionSandbox:
        """
        Create isolated sandbox for session
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionSandbox instance
        """
        with self.lock:
            try:
                logger.info(f"🏗️ Creating sandbox for session: {session_id}")
                
                # Check if already exists
                if session_id in self.sandboxes:
                    logger.warning(f"⚠️ Sandbox already exists: {session_id}")
                    return self.sandboxes[session_id]
                
                # Check session limit
                if len(self.sandboxes) >= self.max_active_sessions:
                    logger.warning(f"⚠️ Max active sessions reached: {self.max_active_sessions}")
                    # Cleanup oldest sandbox
                    self._cleanup_oldest_sandbox()
                
                # Create new sandbox
                sandbox = SessionSandbox(
                    session_id=session_id,
                    created_at=datetime.utcnow()
                )
                
                # Store sandbox
                self.sandboxes[session_id] = sandbox
                
                # Create weak reference for automatic cleanup
                def cleanup_callback(ref):
                    logger.info(f"🗑️ Weak reference cleanup triggered: {session_id}")
                    self.cleanup_sandbox(session_id, force=True)
                
                self.weak_refs[session_id] = weakref.ref(sandbox, cleanup_callback)
                
                logger.info(f"✅ Sandbox created: {session_id}")
                logger.info(f"   Active sandboxes: {len(self.sandboxes)}")
                
                return sandbox
                
            except Exception as e:
                logger.error(f"❌ Error creating sandbox: {e}", exc_info=True)
                raise
    
    def get_sandbox(self, session_id: str) -> Optional[SessionSandbox]:
        """
        Get sandbox for session
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionSandbox or None
        """
        sandbox = self.sandboxes.get(session_id)
        if sandbox:
            sandbox.last_accessed = datetime.utcnow()
            sandbox.access_count += 1
        return sandbox
    
    def allocate_buffer(self, session_id: str, buffer_name: str, data: Any) -> bool:
        """
        Allocate memory buffer for session
        
        Args:
            session_id: Session identifier
            buffer_name: Buffer identifier
            data: Data to store
            
        Returns:
            Success status
        """
        with self.lock:
            try:
                logger.debug(f"💾 Allocating buffer '{buffer_name}' for session: {session_id}")
                
                sandbox = self.get_sandbox(session_id)
                if not sandbox:
                    logger.error(f"❌ Sandbox not found: {session_id}")
                    return False
                
                # Estimate memory size
                data_size = len(str(data).encode('utf-8'))
                
                # Check memory limit
                if (sandbox.total_memory_allocated + data_size) > (self.max_session_memory_mb * 1024 * 1024):
                    logger.warning(f"⚠️ Session memory limit exceeded: {session_id}")
                    return False
                
                # Store buffer
                sandbox.memory_buffers[buffer_name] = data
                sandbox.total_memory_allocated += data_size
                
                logger.debug(f"✅ Buffer allocated: {buffer_name} ({data_size} bytes)")
                logger.debug(f"   Total memory: {sandbox.total_memory_allocated / 1024:.2f} KB")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Error allocating buffer: {e}", exc_info=True)
                return False
    
    def get_buffer(self, session_id: str, buffer_name: str) -> Optional[Any]:
        """
        Get buffer data from session sandbox
        
        Args:
            session_id: Session identifier
            buffer_name: Buffer identifier
            
        Returns:
            Buffer data or None
        """
        sandbox = self.get_sandbox(session_id)
        if sandbox:
            return sandbox.memory_buffers.get(buffer_name)
        return None
    
    def clear_buffer(self, session_id: str, buffer_name: str) -> bool:
        """
        Clear specific buffer
        
        Args:
            session_id: Session identifier
            buffer_name: Buffer identifier
            
        Returns:
            Success status
        """
        with self.lock:
            try:
                logger.debug(f"🗑️ Clearing buffer '{buffer_name}' for session: {session_id}")
                
                sandbox = self.get_sandbox(session_id)
                if not sandbox or buffer_name not in sandbox.memory_buffers:
                    return False
                
                # Get buffer size
                data = sandbox.memory_buffers[buffer_name]
                data_size = len(str(data).encode('utf-8'))
                
                # Remove buffer
                del sandbox.memory_buffers[buffer_name]
                sandbox.total_memory_allocated -= data_size
                
                # Force garbage collection
                del data
                gc.collect()
                
                logger.debug(f"✅ Buffer cleared: {buffer_name} ({data_size} bytes freed)")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Error clearing buffer: {e}", exc_info=True)
                return False
    
    def store_temp_data(self, session_id: str, key: str, value: Any) -> bool:
        """
        Store temporary data in session sandbox
        
        Args:
            session_id: Session identifier
            key: Data key
            value: Data value
            
        Returns:
            Success status
        """
        sandbox = self.get_sandbox(session_id)
        if sandbox:
            sandbox.temp_data[key] = value
            logger.debug(f"💾 Temp data stored: {session_id}.{key}")
            return True
        return False
    
    def get_temp_data(self, session_id: str, key: str) -> Optional[Any]:
        """Get temporary data from session sandbox"""
        sandbox = self.get_sandbox(session_id)
        if sandbox:
            return sandbox.temp_data.get(key)
        return None
    
    def cleanup_sandbox(self, session_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Clean up session sandbox and free resources
        
        Args:
            session_id: Session identifier
            force: Force cleanup even if errors occur
            
        Returns:
            Cleanup summary
        """
        with self.lock:
            try:
                logger.info(f"🧹 Cleaning up sandbox: {session_id}")
                
                sandbox = self.sandboxes.get(session_id)
                if not sandbox:
                    logger.warning(f"⚠️ Sandbox not found: {session_id}")
                    return {"success": False, "message": "Sandbox not found"}
                
                cleanup_summary = {
                    "session_id": session_id,
                    "buffers_cleared": 0,
                    "temp_data_cleared": 0,
                    "memory_freed_mb": 0,
                    "file_handles_closed": 0,
                    "connections_closed": 0
                }
                
                # Clear memory buffers
                buffers_count = len(sandbox.memory_buffers)
                memory_freed = sandbox.total_memory_allocated
                sandbox.memory_buffers.clear()
                cleanup_summary["buffers_cleared"] = buffers_count
                cleanup_summary["memory_freed_mb"] = memory_freed / (1024 * 1024)
                
                # Clear temp data
                temp_data_count = len(sandbox.temp_data)
                sandbox.temp_data.clear()
                cleanup_summary["temp_data_cleared"] = temp_data_count
                
                # Clear cache keys
                sandbox.cache_keys.clear()
                
                # Close file handles
                for fh in sandbox.file_handles:
                    try:
                        if hasattr(fh, 'close'):
                            fh.close()
                        cleanup_summary["file_handles_closed"] += 1
                    except:
                        pass
                sandbox.file_handles.clear()
                
                # Clear connections
                cleanup_summary["connections_closed"] = len(sandbox.open_connections)
                sandbox.open_connections.clear()
                
                # Mark as cleaned
                sandbox.cleaned = True
                sandbox.total_memory_allocated = 0
                
                # Remove from tracking
                del self.sandboxes[session_id]
                if session_id in self.weak_refs:
                    del self.weak_refs[session_id]
                
                # Force garbage collection
                gc.collect()
                
                logger.info(f"✅ Sandbox cleaned up: {session_id}")
                logger.info(f"   Buffers cleared: {cleanup_summary['buffers_cleared']}")
                logger.info(f"   Memory freed: {cleanup_summary['memory_freed_mb']:.2f} MB")
                logger.info(f"   Active sandboxes: {len(self.sandboxes)}")
                
                return {
                    "success": True,
                    "data": cleanup_summary,
                    "message": "Sandbox cleaned up successfully"
                }
                
            except Exception as e:
                logger.error(f"❌ Error cleaning up sandbox: {e}", exc_info=True)
                if force:
                    # Force removal
                    if session_id in self.sandboxes:
                        del self.sandboxes[session_id]
                    if session_id in self.weak_refs:
                        del self.weak_refs[session_id]
                    gc.collect()
                return {
                    "success": False,
                    "error": str(e),
                    "message": "Sandbox cleanup failed"
                }
    
    def _cleanup_oldest_sandbox(self):
        """Clean up the oldest accessed sandbox"""
        if not self.sandboxes:
            return
        
        # Find oldest accessed sandbox
        oldest_session = min(
            self.sandboxes.items(),
            key=lambda x: x[1].last_accessed
        )[0]
        
        logger.info(f"🗑️ Cleaning up oldest sandbox: {oldest_session}")
        self.cleanup_sandbox(oldest_session, force=True)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics
        
        Returns:
            Memory usage statistics
        """
        try:
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info().rss / (1024 * 1024)  # MB
            
            total_sandbox_memory = sum(
                s.total_memory_allocated for s in self.sandboxes.values()
            ) / (1024 * 1024)  # MB
            
            return {
                "process_memory_mb": round(process_memory, 2),
                "sandbox_memory_mb": round(total_sandbox_memory, 2),
                "active_sessions": len(self.sandboxes),
                "max_sessions": self.max_active_sessions,
                "per_session_limit_mb": self.max_session_memory_mb,
                "total_limit_mb": self.max_total_memory_mb
            }
        except Exception as e:
            logger.error(f"❌ Error getting memory stats: {e}")
            return {}
    
    def verify_isolation(self, session_id: str) -> bool:
        """
        Verify session isolation
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if properly isolated
        """
        sandbox = self.get_sandbox(session_id)
        if not sandbox:
            return False
        
        # Check if buffers are isolated (no shared references)
        for buffer_name, buffer_data in sandbox.memory_buffers.items():
            # Check if buffer is referenced by other sessions
            for other_sid, other_sandbox in self.sandboxes.items():
                if other_sid != session_id:
                    if buffer_name in other_sandbox.memory_buffers:
                        if id(buffer_data) == id(other_sandbox.memory_buffers[buffer_name]):
                            logger.error(f"❌ Isolation violation: {session_id} shares buffer with {other_sid}")
                            return False
        
        return True
    
    def get_active_sandboxes(self) -> List[Dict[str, Any]]:
        """Get list of active sandboxes"""
        return [
            {
                "session_id": sid,
                "created_at": sandbox.created_at.isoformat(),
                "memory_allocated_mb": sandbox.total_memory_allocated / (1024 * 1024),
                "buffers_count": len(sandbox.memory_buffers),
                "access_count": sandbox.access_count,
                "isolated": sandbox.isolated
            }
            for sid, sandbox in self.sandboxes.items()
        ]


# Singleton instance
_session_isolation_manager: Optional[SessionIsolationManager] = None


def get_session_isolation_manager() -> SessionIsolationManager:
    """Get singleton SessionIsolationManager instance"""
    global _session_isolation_manager
    if _session_isolation_manager is None:
        _session_isolation_manager = SessionIsolationManager()
    return _session_isolation_manager
