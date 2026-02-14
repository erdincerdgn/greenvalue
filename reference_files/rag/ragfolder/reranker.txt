"""
Cross-Encoder Document Reranker
Author: GreenValue AI Team
Purpose: Ultra-precise relevance scoring using cross-encoder models.
"""

import logging
from typing import List, Optional

from langchain_core.documents import Document

logger = logging.getLogger("greenvalue-rag")

# Check for sentence-transformers availability
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Cross-encoder reranking disabled.")


class CrossEncoderReranker:
    """
    Cross-encoder for precise document reranking.
    Uses ms-marco-MiniLM-L-6-v2 for fast inference.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self.available = False
        
        if CROSS_ENCODER_AVAILABLE:
            try:
                self.model = CrossEncoder(model_name)
                self.available = True
                logger.info(f"✅ Cross-encoder loaded: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to load cross-encoder: {e}")
    
    def rerank(
        self,
        query: str,
        docs: List[Document],
        top_k: int = 3
    ) -> List[Document]:
        """
        Rerank documents using cross-encoder scoring.
        
        Args:
            query: Search query
            docs: List of documents to rerank
            top_k: Number of top documents to return
            
        Returns:
            Top-k documents sorted by relevance
        """
        if not self.available or not docs:
            return docs[:top_k]
        
        # Create query-document pairs
        pairs = [[query, doc.page_content[:500]] for doc in docs]
        
        # Get cross-encoder scores
        scores = self.model.predict(pairs)
        
        # Sort by score
        scored_docs = list(zip(docs, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Add score to metadata
        result = []
        for doc, score in scored_docs[:top_k]:
            doc.metadata["cross_encoder_score"] = float(score)
            result.append(doc)
        
        logger.debug(f"Cross-encoder reranked {len(docs)} → {len(result)} docs")
        return result
    
    @property
    def is_available(self) -> bool:
        return self.available
