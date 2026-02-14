"""
RAG Module Configuration
Author: GreenValue AI Team
Purpose: Centralized configuration for RAG pipeline components.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class RAGConfig:
    """Configuration settings for the RAG module."""
    
    # Service URLs
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    unstructured_url: str = os.getenv(
        "UNSTRUCTURED_API_URL", 
        "http://localhost:8000/general/v0/general"
    )
    
    # Collection names
    child_collection: str = "greenvalue_child"
    parent_collection: str = "greenvalue_parent"
    
    # Embedding settings
    dense_model: str = "BAAI/bge-small-en-v1.5"
    sparse_model: str = "Qdrant/bm25"
    dense_vector_size: int = 384
    
    # Chunk settings
    child_chunk_size: int = 400
    child_chunk_overlap: int = 50
    parent_chunk_size: int = 1500
    parent_chunk_overlap: int = 200
    
    # LLM settings
    llm_model: str = os.getenv("RAG_LLM_MODEL", "llama3.2:3b")
    
    # Retrieval settings
    top_k_initial: int = 10
    top_k_rerank: int = 3
    min_relevance_score: int = 25
    
    @property
    def chunk_overlap(self) -> int:
        """Alias for child_chunk_overlap (used by ingestion pipeline)."""
        return self.child_chunk_overlap
    
    # Paths
    knowledge_base_path: str = os.getenv(
        "KNOWLEDGE_BASE_PATH",
        "/app/infrastructure/qdrant/knowledge_base/books"
    )
    memory_db_path: str = os.getenv(
        "MEMORY_DB_PATH",
        "/app/data/user_memory.db"
    )
    
    @classmethod
    def from_env(cls) -> "RAGConfig":
        """Create config from environment variables."""
        return cls(
            qdrant_url=os.getenv("QDRANT_URL", cls.qdrant_url),
            ollama_host=os.getenv("OLLAMA_HOST", cls.ollama_host),
            unstructured_url=os.getenv("UNSTRUCTURED_API_URL", cls.unstructured_url),
            knowledge_base_path=os.getenv("KNOWLEDGE_BASE_PATH", cls.knowledge_base_path),
            memory_db_path=os.getenv("MEMORY_DB_PATH", cls.memory_db_path),
        )


# Document categories for GreenValue domain
CATEGORIES = [
    "Real Estate",
    "Sustainability",
    "Energy Efficiency",
    "Finance",
    "Valuation",
    "General",
]

# Query types for semantic routing
class QueryType:
    VALUATION = "valuation"
    SUSTAINABILITY = "sustainability"
    ENERGY = "energy"
    GENERAL = "general"

# Query complexity levels
class QueryComplexity:
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
