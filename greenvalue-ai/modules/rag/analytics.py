"""
Advanced Analytics Dashboard
Author: GreenValue AI Team
Purpose: RAG pipeline analytics, performance monitoring, and insights.
"""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("greenvalue-rag")


class AdvancedAnalyticsDashboard:
    """
    Analytics dashboard for RAG pipeline monitoring.

    Tracks:
        - Query performance metrics (latency, quality, cache hit rate)
        - Domain distribution (which domains are queried most)
        - Document utilization (which docs are retrieved most)
        - User engagement (query frequency, feedback rate)
        - System health (component status, error rates)
    """

    def __init__(self, learning_engine=None):
        self._learning_engine = learning_engine
        self._query_log: List[Dict] = []
        self._error_log: List[Dict] = []
        self._initialized = True

    def log_query(
        self,
        query: str,
        domain: str,
        response_time: float,
        quality: float,
        cached: bool = False,
        vision_enhanced: bool = False,
        tables_included: int = 0,
        documents_retrieved: int = 0,
    ):
        """Log a query for analytics."""
        entry = {
            "query": query[:100],
            "domain": domain,
            "response_time": response_time,
            "quality": quality,
            "cached": cached,
            "vision_enhanced": vision_enhanced,
            "tables_included": tables_included,
            "documents_retrieved": documents_retrieved,
            "timestamp": time.time(),
        }
        self._query_log.append(entry)

        # Keep last 10000 entries
        if len(self._query_log) > 10000:
            self._query_log = self._query_log[-10000:]

    def log_error(self, error_type: str, message: str, component: str = ""):
        """Log an error for analytics."""
        self._error_log.append({
            "type": error_type,
            "message": message[:200],
            "component": component,
            "timestamp": time.time(),
        })

    def get_dashboard_data(self) -> Dict:
        """Get complete dashboard data."""
        total_queries = len(self._query_log)
        if total_queries == 0:
            return {
                "total_queries": 0,
                "avg_response_time": 0,
                "avg_quality": 0,
                "cache_hit_rate": 0,
                "domain_distribution": {},
                "error_count": len(self._error_log),
            }

        # Calculate metrics
        avg_time = sum(q["response_time"] for q in self._query_log) / total_queries
        avg_quality = sum(q["quality"] for q in self._query_log) / total_queries
        cache_hits = sum(1 for q in self._query_log if q["cached"])
        cache_hit_rate = cache_hits / total_queries

        # Domain distribution
        domain_counts: Dict[str, int] = {}
        for q in self._query_log:
            d = q["domain"]
            domain_counts[d] = domain_counts.get(d, 0) + 1

        # Vision utilization
        vision_count = sum(1 for q in self._query_log if q["vision_enhanced"])
        table_count = sum(q["tables_included"] for q in self._query_log)

        return {
            "total_queries": total_queries,
            "avg_response_time": round(avg_time, 3),
            "avg_quality": round(avg_quality, 3),
            "cache_hit_rate": round(cache_hit_rate, 3),
            "domain_distribution": domain_counts,
            "vision_utilization": round(vision_count / total_queries, 3),
            "tables_per_query": round(table_count / total_queries, 2),
            "error_count": len(self._error_log),
            "recent_errors": self._error_log[-5:] if self._error_log else [],
        }

    def get_performance_summary(self) -> Dict:
        """Get a performance summary with trends."""
        data = self.get_dashboard_data()

        # Determine health status
        if data["avg_response_time"] < 2.0 and data["avg_quality"] > 0.8:
            health = "excellent"
        elif data["avg_response_time"] < 3.0 and data["avg_quality"] > 0.7:
            health = "good"
        elif data["avg_response_time"] < 5.0:
            health = "fair"
        else:
            health = "needs_attention"

        return {
            **data,
            "health": health,
            "learning_stats": (
                self._learning_engine.get_learning_stats()
                if self._learning_engine
                else {}
            ),
        }
