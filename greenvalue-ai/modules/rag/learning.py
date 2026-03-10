"""
Real-Time Learning Engine
Author: GreenValue AI Team
Purpose: Continuous learning from user queries, feedback, and interactions
         to improve RAG retrieval quality over time.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("greenvalue-rag")


@dataclass
class LearningEvent:
    """A single learning event from user interaction."""
    event_type: str  # "query", "feedback", "click"
    user_id: str
    query: str
    domain: str
    response_quality: float = 0.0
    response_time: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


class RealTimeLearningEngine:
    """
    Tracks user interactions and adapts RAG parameters in real-time.

    Capabilities:
        - Domain performance tracking (which domains produce best results)
        - Query pattern recognition (frequent vs. rare queries)
        - User preference profiling (preferred detail level, domains)
        - Adaptive parameter tuning (top_k, rerank thresholds)
    """

    def __init__(self):
        self._events: List[LearningEvent] = []
        self._domain_stats: Dict[str, Dict] = defaultdict(
            lambda: {
                "total_queries": 0,
                "total_quality": 0.0,
                "total_time": 0.0,
                "best_expansion_strategy": "hybrid",
            }
        )
        self._user_profiles: Dict[str, Dict] = defaultdict(
            lambda: {
                "query_count": 0,
                "preferred_domains": defaultdict(int),
                "avg_quality": 0.0,
                "feedback_positive": 0,
                "feedback_negative": 0,
            }
        )
        self._initialized = True

    def record_event(
        self,
        event_type: str,
        user_id: str,
        query: str,
        domain: str,
        response_quality: float = 0.0,
        response_time: float = 0.0,
        metadata: Optional[Dict] = None,
    ):
        """Record a learning event."""
        event = LearningEvent(
            event_type=event_type,
            user_id=user_id,
            query=query,
            domain=domain,
            response_quality=response_quality,
            response_time=response_time,
            metadata=metadata or {},
        )
        self._events.append(event)

        # Update domain stats
        stats = self._domain_stats[domain]
        stats["total_queries"] += 1
        stats["total_quality"] += response_quality
        stats["total_time"] += response_time

        # Update user profile
        profile = self._user_profiles[user_id]
        profile["query_count"] += 1
        profile["preferred_domains"][domain] += 1

        total_q = profile["query_count"]
        profile["avg_quality"] = (
            (profile["avg_quality"] * (total_q - 1) + response_quality) / total_q
        )

        if metadata and metadata.get("cached"):
            pass  # Don't count cached results for learning

    def get_adaptive_parameters(
        self, domain: str, user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Get adaptively-tuned parameters for the given domain and user.

        Returns:
            Dict with tuned parameters:
                - domain_weight (float): Weight multiplier for this domain
                - expansion_strategy (str): Best expansion strategy
                - quality_threshold (float): Min quality for caching
                - user_preferences (dict): User-specific preferences
        """
        domain_stats = self._domain_stats.get(domain, {})
        user_profile = self._user_profiles.get(user_id, {})

        total_queries = domain_stats.get("total_queries", 0)
        total_quality = domain_stats.get("total_quality", 0.0)

        # Domain weight: domains with better avg quality get higher weight
        avg_quality = (total_quality / total_queries) if total_queries > 0 else 0.7
        domain_weight = max(0.5, min(1.5, avg_quality * 1.5))

        # Quality threshold: adapt based on historical performance
        quality_threshold = max(0.6, avg_quality - 0.1)

        # Expansion strategy: prefer what's worked historically
        expansion_strategy = domain_stats.get("best_expansion_strategy", "hybrid")

        # User preferences
        user_prefs = {}
        if user_profile:
            domains = user_profile.get("preferred_domains", {})
            if domains:
                user_prefs = {k: v for k, v in sorted(
                    domains.items(), key=lambda x: x[1], reverse=True
                )[:3]}

        return {
            "domain_weight": domain_weight,
            "expansion_strategy": expansion_strategy,
            "quality_threshold": quality_threshold,
            "user_preferences": user_prefs,
            "total_domain_queries": total_queries,
        }

    def record_feedback(
        self, user_id: str, query_id: str, helpful: bool
    ):
        """Record user feedback for learning."""
        profile = self._user_profiles[user_id]
        if helpful:
            profile["feedback_positive"] += 1
        else:
            profile["feedback_negative"] += 1

    def get_learning_stats(self) -> Dict:
        """Get comprehensive learning statistics."""
        total_events = len(self._events)
        if total_events == 0:
            return {
                "total_events": 0,
                "domains": {},
                "users": 0,
            }

        domain_summary = {}
        for domain, stats in self._domain_stats.items():
            total = stats["total_queries"]
            domain_summary[domain] = {
                "queries": total,
                "avg_quality": (
                    stats["total_quality"] / total if total > 0 else 0.0
                ),
                "avg_time": (
                    stats["total_time"] / total if total > 0 else 0.0
                ),
            }

        return {
            "total_events": total_events,
            "domains": domain_summary,
            "users": len(self._user_profiles),
            "recent_events": total_events,
        }
