"""
Embedding Manager for RAG Module
Author: GreenValue AI Team
Purpose: Manages dense and sparse embeddings for hybrid search.
"""

import logging
from typing import Optional

from .config import RAGConfig

logger = logging.getLogger("greenvalue-rag")


class EmbeddingManager:
    """
    Manages embedding models for hybrid search.
    - Dense: BAAI/bge-small-en-v1.5 (384 dimensions)
    - Sparse: BM25 for keyword matching
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self._dense_embeddings = None
        self._sparse_embeddings = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize embedding models lazily."""
        if self._initialized:
            return True
        
        try:
            from langchain_community.embeddings import FastEmbedEmbeddings
            from langchain_qdrant import FastEmbedSparse
            
            logger.info(f"Loading dense embeddings: {self.config.dense_model}")
            self._dense_embeddings = FastEmbedEmbeddings(
                model_name=self.config.dense_model
            )
            
            logger.info(f"Loading sparse embeddings: {self.config.sparse_model}")
            self._sparse_embeddings = FastEmbedSparse(
                model_name=self.config.sparse_model
            )
            
            self._initialized = True
            logger.info("✅ Embedding models loaded successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import embedding libraries: {e}")
            logger.error("Install with: pip install fastembed langchain-qdrant")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            return False
    
    @property
    def dense(self):
        """Get dense embedding model."""
        if not self._initialized:
            self.initialize()
        return self._dense_embeddings
    
    @property
    def sparse(self):
        """Get sparse embedding model."""
        if not self._initialized:
            self.initialize()
        return self._sparse_embeddings
    
    @property
    def is_ready(self) -> bool:
        """Check if embeddings are ready."""
        return self._initialized and self._dense_embeddings is not None
    
    def embed_query(self, text: str) -> list:
        """Generate dense embedding for a query."""
        if not self.is_ready:
            raise RuntimeError("Embeddings not initialized")
        return self._dense_embeddings.embed_query(text)
    
    def embed_documents(self, texts: list) -> list:
        """Generate dense embeddings for multiple documents."""
        if not self.is_ready:
            raise RuntimeError("Embeddings not initialized")
        return self._dense_embeddings.embed_documents(texts)
