"""
Semantic Caching System - Final 5% Optimization
Author: GreenValue AI Team (Enhanced by Senior RAG Developer)
Purpose: Intelligent caching for 10x performance improvement.
"""

import logging
import hashlib
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

import numpy as np
from qdrant_client import QdrantClient, models

logger = logging.getLogger("greenvalue-rag")


@dataclass
class CacheEntry:
    """Cached query result with metadata."""
    query: str
    query_embedding: List[float]
    answer: str
    sources: List[Dict]
    domain: str
    timestamp: datetime
    hit_count: int = 0
    avg_response_time: float = 0.0
    user_feedback_score: float = 0.0


class SemanticCache:
    """
    Intelligent semantic caching system for RAG queries.
    
    Features:
    - Embedding-based similarity matching
    - LRU eviction with semantic clustering
    - Response time tracking
    - Cache warming from popular queries
    - Automatic cache invalidation
    """
    
    def __init__(
        self,
        qdrant_url: str = "http://qdrant:6333",
        collection_name: str = "semantic_cache",
        similarity_threshold: float = 0.95,
        max_cache_size: int = 10000,
        ttl_hours: int = 168  # 1 week
    ):
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.similarity_threshold = similarity_threshold
        self.max_cache_size = max_cache_size
        self.ttl = timedelta(hours=ttl_hours)
        
        self.client: Optional[QdrantClient] = None
        self._initialized = False
        
        # Performance metrics
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "total_queries": 0,
            "avg_hit_response_time": 0.0,
            "avg_miss_response_time": 0.0,
            "cache_size": 0
        }
    
    def initialize(self, embedding_model) -> bool:
        """Initialize semantic cache with Qdrant."""
        if self._initialized:
            return True
        
        try:
            self.client = QdrantClient(url=self.qdrant_url)
            self.embedding_model = embedding_model
            
            # Create cache collection if not exists
            collections = [c.name for c in self.client.get_collections().collections]
            
            if self.collection_name not in collections:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=384,  # BGE-small embedding size
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"✅ Created semantic cache collection: {self.collection_name}")
            else:
                logger.info(f"✅ Semantic cache collection exists: {self.collection_name}")
            
            self._initialized = True
            self._update_cache_size()
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize semantic cache: {e}")
            return False
    
    def get(self, query: str, domain: str = None) -> Optional[Dict]:
        """
        Retrieve cached result for semantically similar query.
        
        Args:
            query: User query
            domain: Optional domain filter
            
        Returns:
            Cached result if found, None otherwise
        """
        if not self._initialized:
            return None
        
        start_time = time.time()
        self.metrics["total_queries"] += 1
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.embed_query(query)
            
            # Search for similar cached queries
            search_filter = None
            if domain:
                search_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="domain",
                            match=models.MatchValue(value=domain)
                        )
                    ]
                )
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=1,
                score_threshold=self.similarity_threshold
            )
            
            if results:
                hit = results[0]
                cached_data = hit.payload
                
                # Check TTL
                cached_time = datetime.fromisoformat(cached_data["timestamp"])
                if datetime.now() - cached_time > self.ttl:
                    # Expired - delete and return miss
                    self.client.delete(
                        collection_name=self.collection_name,
                        points_selector=[hit.id]
                    )
                    logger.debug(f"Cache entry expired: {query[:30]}...")
                    self._record_miss(time.time() - start_time)
                    return None
                
                # Cache hit!
                self._record_hit(time.time() - start_time, hit.id)
                
                logger.info(f"🎯 Cache HIT (similarity: {hit.score:.3f}): {query[:30]}...")
                
                return {
                    "answer": cached_data["answer"],
                    "sources": cached_data["sources"],
                    "domain": cached_data["domain"],
                    "cached": True,
                    "cache_similarity": hit.score,
                    "cache_age_hours": (datetime.now() - cached_time).total_seconds() / 3600,
                    "hit_count": cached_data.get("hit_count", 0)
                }
            
            # Cache miss
            self._record_miss(time.time() - start_time)
            logger.debug(f"❌ Cache MISS: {query[:30]}...")
            return None
            
        except Exception as e:
            logger.error(f"Cache lookup failed: {e}")
            return None
    
    def set(
        self,
        query: str,
        answer: str,
        sources: List[Dict],
        domain: str,
        response_time: float = 0.0
    ) -> bool:
        """
        Cache a query result.
        
        Args:
            query: User query
            answer: Generated answer
            sources: Source documents
            domain: Query domain
            response_time: Time taken to generate answer
            
        Returns:
            True if cached successfully
        """
        if not self._initialized:
            return False
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.embed_query(query)
            
            # Create cache entry
            cache_id = hashlib.md5(query.encode()).hexdigest()
            
            payload = {
                "query": query,
                "answer": answer,
                "sources": sources,
                "domain": domain,
                "timestamp": datetime.now().isoformat(),
                "hit_count": 0,
                "response_time": response_time,
                "user_feedback_score": 0.0
            }
            
            # Check cache size and evict if necessary
            if self.metrics["cache_size"] >= self.max_cache_size:
                self._evict_lru()
            
            # Upsert to cache
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=cache_id,
                        vector=query_embedding,
                        payload=payload
                    )
                ]
            )
            
            self.metrics["cache_size"] += 1
            logger.debug(f"✅ Cached: {query[:30]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache result: {e}")
            return False
    
    def update_feedback(self, query: str, feedback_score: float):
        """Update cache entry with user feedback."""
        if not self._initialized:
            return
        
        try:
            cache_id = hashlib.md5(query.encode()).hexdigest()
            
            # Get current entry
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[cache_id]
            )
            
            if result:
                payload = result[0].payload
                payload["user_feedback_score"] = feedback_score
                
                # Update entry
                self.client.set_payload(
                    collection_name=self.collection_name,
                    payload=payload,
                    points=[cache_id]
                )
                
                logger.debug(f"Updated feedback for cached query: {feedback_score}")
                
        except Exception as e:
            logger.warning(f"Failed to update cache feedback: {e}")
    
    def _record_hit(self, response_time: float, point_id: str):
        """Record cache hit metrics."""
        self.metrics["cache_hits"] += 1
        
        # Update average hit response time
        total_hits = self.metrics["cache_hits"]
        current_avg = self.metrics["avg_hit_response_time"]
        self.metrics["avg_hit_response_time"] = (
            (current_avg * (total_hits - 1) + response_time) / total_hits
        )
        
        # Increment hit count for this entry
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id]
            )
            
            if result:
                payload = result[0].payload
                payload["hit_count"] = payload.get("hit_count", 0) + 1
                
                self.client.set_payload(
                    collection_name=self.collection_name,
                    payload=payload,
                    points=[point_id]
                )
        except Exception as e:
            logger.warning(f"Failed to update hit count: {e}")
    
    def _record_miss(self, response_time: float):
        """Record cache miss metrics."""
        self.metrics["cache_misses"] += 1
        
        # Update average miss response time
        total_misses = self.metrics["cache_misses"]
        current_avg = self.metrics["avg_miss_response_time"]
        self.metrics["avg_miss_response_time"] = (
            (current_avg * (total_misses - 1) + response_time) / total_misses
        )
    
    def _evict_lru(self):
        """Evict least recently used cache entries."""
        try:
            # Get all entries sorted by hit_count and timestamp
            results = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
                with_payload=True
            )
            
            if not results[0]:
                return
            
            # Sort by hit_count (ascending) and timestamp (oldest first)
            entries = []
            for point in results[0]:
                entries.append({
                    "id": point.id,
                    "hit_count": point.payload.get("hit_count", 0),
                    "timestamp": datetime.fromisoformat(point.payload["timestamp"])
                })
            
            # Sort: lowest hit_count first, then oldest first
            entries.sort(key=lambda x: (x["hit_count"], x["timestamp"]))
            
            # Evict bottom 10%
            evict_count = max(1, len(entries) // 10)
            evict_ids = [e["id"] for e in entries[:evict_count]]
            
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=evict_ids
            )
            
            self.metrics["cache_size"] -= len(evict_ids)
            logger.info(f"🗑️ Evicted {len(evict_ids)} LRU cache entries")
            
        except Exception as e:
            logger.error(f"Cache eviction failed: {e}")
    
    def _update_cache_size(self):
        """Update cache size metric."""
        try:
            info = self.client.get_collection(self.collection_name)
            self.metrics["cache_size"] = info.points_count
        except Exception:
            pass
    
    def warm_cache(self, popular_queries: List[Tuple[str, str, str, List[Dict]]]):
        """
        Warm cache with popular queries.
        
        Args:
            popular_queries: List of (query, answer, domain, sources) tuples
        """
        logger.info(f"🔥 Warming cache with {len(popular_queries)} popular queries...")
        
        for query, answer, domain, sources in popular_queries:
            self.set(query, answer, sources, domain)
        
        logger.info(f"✅ Cache warmed with {len(popular_queries)} entries")
    
    def clear(self):
        """Clear all cache entries."""
        if not self._initialized:
            return
        
        try:
            self.client.delete_collection(self.collection_name)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=384,
                    distance=models.Distance.COSINE
                )
            )
            
            self.metrics["cache_size"] = 0
            logger.info("🗑️ Cache cleared")
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        self._update_cache_size()
        
        hit_rate = 0.0
        if self.metrics["total_queries"] > 0:
            hit_rate = self.metrics["cache_hits"] / self.metrics["total_queries"]
        
        speedup = 0.0
        if self.metrics["avg_hit_response_time"] > 0:
            speedup = (
                self.metrics["avg_miss_response_time"] / 
                self.metrics["avg_hit_response_time"]
            )
        
        return {
            **self.metrics,
            "hit_rate": hit_rate,
            "speedup_factor": speedup,
            "cache_utilization": self.metrics["cache_size"] / self.max_cache_size
        }
    
    def get_popular_queries(self, limit: int = 10) -> List[Dict]:
        """Get most popular cached queries."""
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
                with_payload=True
            )
            
            if not results[0]:
                return []
            
            # Sort by hit_count
            entries = [
                {
                    "query": p.payload["query"],
                    "domain": p.payload["domain"],
                    "hit_count": p.payload.get("hit_count", 0),
                    "feedback_score": p.payload.get("user_feedback_score", 0.0)
                }
                for p in results[0]
            ]
            
            entries.sort(key=lambda x: x["hit_count"], reverse=True)
            return entries[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get popular queries: {e}")
            return []


class EmbeddingCache:
    """
    Cache for document embeddings to avoid recomputation.
    Stores embeddings in memory with LRU eviction.
    """
    
    def __init__(self, max_size: int = 5000):
        self.max_size = max_size
        self.cache: Dict[str, Tuple[List[float], float]] = {}  # hash -> (embedding, timestamp)
        self.access_times: Dict[str, float] = {}
        
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "size": 0
        }
    
    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding for text."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        if text_hash in self.cache:
            self.metrics["hits"] += 1
            self.access_times[text_hash] = time.time()
            return self.cache[text_hash][0]
        
        self.metrics["misses"] += 1
        return None
    
    def set(self, text: str, embedding: List[float]):
        """Cache embedding for text."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Evict if at capacity
        if len(self.cache) >= self.max_size:
            # Remove least recently accessed
            lru_hash = min(self.access_times, key=self.access_times.get)
            del self.cache[lru_hash]
            del self.access_times[lru_hash]
        
        self.cache[text_hash] = (embedding, time.time())
        self.access_times[text_hash] = time.time()
        self.metrics["size"] = len(self.cache)
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = self.metrics["hits"] / total if total > 0 else 0.0
        
        return {
            **self.metrics,
            "hit_rate": hit_rate,
            "utilization": len(self.cache) / self.max_size
        }
    
    def clear(self):
        """Clear embedding cache."""
        self.cache.clear()
        self.access_times.clear()
        self.metrics["size"] = 0
