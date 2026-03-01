"""
Real-time Dashboard Service
Monitors orchestration metrics and provides WebSocket updates
"""

import logging
import asyncio
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Real-time dashboard service for monitoring orchestration metrics
    
    Metrics Tracked:
    - STT Latency (Speech-to-Text)
    - LLM Processing Time
    - TTS Latency (Text-to-Speech)
    - Retry Counts
    - Active Sessions
    - Success Rates
    - Quality Scores
    """
    
    def __init__(self):
        """Initialize Dashboard Service"""
        self.mongo_uri = os.getenv("MONGODB_ATLAS_URI")
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.collection = None
        self._connected = False
        
        # WebSocket connections for live updates
        self.active_connections: List[Any] = []
        
    async def connect(self):
        """Connect to MongoDB"""
        if self._connected:
            return
            
        try:
            self.client = AsyncIOMotorClient(self.mongo_uri)
            self.db = self.client.get_database("ai_recruiter")
            self.collection = self.db.get_collection("orchestration_sessions")
            
            # Test connection
            await self.client.admin.command('ping')
            self._connected = True
            logger.info("✅ Dashboard Service connected to MongoDB")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("✅ Dashboard Service disconnected from MongoDB")
    
    async def get_metrics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """
        Get comprehensive metrics for dashboard
        
        Args:
            time_range_hours: Time range to analyze (default: 24 hours)
            
        Returns:
            Dictionary containing all metrics
        """
        if not self._connected:
            await self.connect()
        
        try:
            # Calculate time range
            time_threshold = datetime.utcnow() - timedelta(hours=time_range_hours)
            
            # Get all sessions in time range
            sessions_cursor = self.collection.find({
                "created_at": {"$gte": time_threshold}
            }).sort("created_at", DESCENDING)
            
            sessions = await sessions_cursor.to_list(length=None)
            
            # Calculate metrics
            metrics = await self._calculate_metrics(sessions, time_threshold)
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error fetching metrics: {e}")
            return self._get_empty_metrics()
    
    async def _calculate_metrics(self, sessions: List[Dict], time_threshold: datetime) -> Dict[str, Any]:
        """Calculate all dashboard metrics"""
        
        # Initialize counters
        total_sessions = len(sessions)
        active_sessions = 0
        completed_sessions = 0
        failed_sessions = 0
        
        total_turns = 0
        successful_turns = 0
        failed_turns = 0
        
        stt_latencies = []
        llm_latencies = []
        tts_latencies = []
        total_latencies = []
        
        retry_counts = []
        quality_scores = []
        
        # Recent sessions for timeline
        recent_sessions = []
        
        # Analyze each session
        for session in sessions:
            status = session.get("status", "unknown")
            
            if status == "active":
                active_sessions += 1
            elif status == "completed":
                completed_sessions += 1
            elif status == "failed":
                failed_sessions += 1
            
            # Process turns
            turns = session.get("turns", [])
            for turn in turns:
                total_turns += 1
                
                # Check success
                if turn.get("success", True):
                    successful_turns += 1
                else:
                    failed_turns += 1
                
                # Collect latencies
                stt_latency = turn.get("stt_latency_ms")
                if stt_latency is not None:
                    stt_latencies.append(stt_latency)
                
                llm_latency = turn.get("llm_latency_ms")
                if llm_latency is not None:
                    llm_latencies.append(llm_latency)
                
                tts_latency = turn.get("tts_latency_ms")
                if tts_latency is not None:
                    tts_latencies.append(tts_latency)
                
                total_latency = turn.get("total_latency_ms")
                if total_latency is not None:
                    total_latencies.append(total_latency)
                
                # Retry count
                retry_count = turn.get("retry_count", 0)
                retry_counts.append(retry_count)
            
            # Quality score
            quality_score = session.get("quality_score")
            if quality_score is not None:
                quality_scores.append(quality_score)
            
            # Add to recent sessions (limit to 10)
            if len(recent_sessions) < 10:
                recent_sessions.append({
                    "session_id": session.get("session_id"),
                    "orchestration_id": session.get("orchestration_id"),
                    "status": status,
                    "created_at": session.get("created_at"),
                    "total_turns": len(turns),
                    "quality_score": quality_score
                })
        
        # Calculate averages and statistics
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "time_range_hours": (datetime.utcnow() - time_threshold).total_seconds() / 3600,
            
            # Session metrics
            "sessions": {
                "total": total_sessions,
                "active": active_sessions,
                "completed": completed_sessions,
                "failed": failed_sessions,
                "success_rate": round(completed_sessions / total_sessions * 100, 2) if total_sessions > 0 else 0
            },
            
            # Turn metrics
            "turns": {
                "total": total_turns,
                "successful": successful_turns,
                "failed": failed_turns,
                "success_rate": round(successful_turns / total_turns * 100, 2) if total_turns > 0 else 0
            },
            
            # Latency metrics (in milliseconds)
            "latency": {
                "stt": {
                    "avg": round(sum(stt_latencies) / len(stt_latencies), 2) if stt_latencies else 0,
                    "min": min(stt_latencies) if stt_latencies else 0,
                    "max": max(stt_latencies) if stt_latencies else 0,
                    "p95": self._percentile(stt_latencies, 95) if stt_latencies else 0,
                    "samples": len(stt_latencies)
                },
                "llm": {
                    "avg": round(sum(llm_latencies) / len(llm_latencies), 2) if llm_latencies else 0,
                    "min": min(llm_latencies) if llm_latencies else 0,
                    "max": max(llm_latencies) if llm_latencies else 0,
                    "p95": self._percentile(llm_latencies, 95) if llm_latencies else 0,
                    "samples": len(llm_latencies)
                },
                "tts": {
                    "avg": round(sum(tts_latencies) / len(tts_latencies), 2) if tts_latencies else 0,
                    "min": min(tts_latencies) if tts_latencies else 0,
                    "max": max(tts_latencies) if tts_latencies else 0,
                    "p95": self._percentile(tts_latencies, 95) if tts_latencies else 0,
                    "samples": len(tts_latencies)
                },
                "total": {
                    "avg": round(sum(total_latencies) / len(total_latencies), 2) if total_latencies else 0,
                    "min": min(total_latencies) if total_latencies else 0,
                    "max": max(total_latencies) if total_latencies else 0,
                    "p95": self._percentile(total_latencies, 95) if total_latencies else 0,
                    "samples": len(total_latencies)
                }
            },
            
            # Retry metrics
            "retries": {
                "total": sum(retry_counts),
                "avg_per_turn": round(sum(retry_counts) / len(retry_counts), 2) if retry_counts else 0,
                "max": max(retry_counts) if retry_counts else 0
            },
            
            # Quality metrics
            "quality": {
                "avg_score": round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else 0,
                "min_score": min(quality_scores) if quality_scores else 0,
                "max_score": max(quality_scores) if quality_scores else 0
            },
            
            # Recent sessions
            "recent_sessions": recent_sessions
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a list"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return round(sorted_data[min(index, len(sorted_data) - 1)], 2)
    
    def _get_empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "time_range_hours": 0,
            "sessions": {
                "total": 0,
                "active": 0,
                "completed": 0,
                "failed": 0,
                "success_rate": 0
            },
            "turns": {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0
            },
            "latency": {
                "stt": {"avg": 0, "min": 0, "max": 0, "p95": 0, "samples": 0},
                "llm": {"avg": 0, "min": 0, "max": 0, "p95": 0, "samples": 0},
                "tts": {"avg": 0, "min": 0, "max": 0, "p95": 0, "samples": 0},
                "total": {"avg": 0, "min": 0, "max": 0, "p95": 0, "samples": 0}
            },
            "retries": {
                "total": 0,
                "avg_per_turn": 0,
                "max": 0
            },
            "quality": {
                "avg_score": 0,
                "min_score": 0,
                "max_score": 0
            },
            "recent_sessions": []
        }
    
    async def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific session"""
        if not self._connected:
            await self.connect()
        
        try:
            session = await self.collection.find_one({"session_id": session_id})
            return session
        except Exception as e:
            logger.error(f"❌ Error fetching session details: {e}")
            return None
    
    async def get_active_sessions_list(self) -> List[Dict[str, Any]]:
        """Get list of currently active sessions"""
        if not self._connected:
            await self.connect()
        
        try:
            sessions_cursor = self.collection.find({
                "status": "active"
            }).sort("created_at", DESCENDING)
            
            sessions = await sessions_cursor.to_list(length=100)
            
            return [
                {
                    "session_id": s.get("session_id"),
                    "orchestration_id": s.get("orchestration_id"),
                    "created_at": s.get("created_at"),
                    "total_turns": len(s.get("turns", [])),
                    "quality_score": s.get("quality_score", 0)
                }
                for s in sessions
            ]
        except Exception as e:
            logger.error(f"❌ Error fetching active sessions: {e}")
            return []
    
    # WebSocket connection management
    async def add_websocket_connection(self, websocket):
        """Add a WebSocket connection for live updates"""
        self.active_connections.append(websocket)
        logger.info(f"📡 WebSocket connected. Total connections: {len(self.active_connections)}")
    
    async def remove_websocket_connection(self, websocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"📡 WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast_metrics_update(self, metrics: Dict[str, Any]):
        """Broadcast metrics update to all connected WebSocket clients"""
        if not self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(metrics)
            except Exception as e:
                logger.warning(f"⚠️ Failed to send to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            await self.remove_websocket_connection(conn)


# Global dashboard service instance
_dashboard_service: Optional[DashboardService] = None


def get_dashboard_service() -> DashboardService:
    """Get or create dashboard service instance"""
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = DashboardService()
    return _dashboard_service
