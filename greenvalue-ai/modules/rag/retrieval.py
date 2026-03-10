"""
Retrieval Engine
Author: GreenValue AI Team
Purpose: Orchestrates hybrid search, reranking, and parent expansion.
"""

import logging
from typing import List, Optional

from langchain_core.documents import Document

from .config import RAGConfig
from .store import GreenValueDocumentStore
from .reranker import CrossEncoderReranker

logger = logging.getLogger("greenvalue-rag")

# Check for FlashRank availability
try:
    from flashrank import Ranker, RerankRequest
    FLASHRANK_AVAILABLE = True
except ImportError:
    FLASHRANK_AVAILABLE = False
    logger.warning("FlashRank not installed. Using cross-encoder only.")


class RetrievalEngine:
    """
    Multi-stage retrieval pipeline:
    1. Hybrid Search (Dense + Sparse)
    2. FlashRank Reranking
    3. Cross-Encoder Reranking
    4. Parent Document Expansion
    """
    
    def __init__(
        self,
        store: GreenValueDocumentStore,
        config: Optional[RAGConfig] = None
    ):
        self.store = store
        self.config = config or RAGConfig()
        
        # Initialize rerankers
        self.flashrank = None
        if FLASHRANK_AVAILABLE:
            try:
                self.flashrank = Ranker(model_name="ms-marco-MultiBERT-L-12")
                logger.info("✅ FlashRank reranker loaded")
            except Exception as e:
                logger.warning(f"FlashRank init failed: {e}")
        
        self.cross_encoder = CrossEncoderReranker()
    
    def retrieve(
        self,
        query: str,
        category: Optional[str] = None,
        book_ids: Optional[List[str]] = None,
        top_k: int = 10,
        use_rerank: bool = True,
        use_parent: bool = True
    ) -> List[Document]:
        """
        Full retrieval pipeline.
        
        Args:
            query: Search query
            category: Optional category filter
            book_ids: Optional list of book_ids to restrict retrieval
            top_k: Initial documents to retrieve
            use_rerank: Whether to apply reranking
            use_parent: Whether to expand to parent documents
            
        Returns:
            Retrieved and processed documents
        """
        logger.info(f"🔍 Query: {query[:50]}...")
        
        # Step 1: Hybrid Search
        retriever = self.store.get_retriever(
            category_filter=category,
            book_ids=book_ids,
            top_k=top_k
        )
        docs = retriever.invoke(query)
        logger.info(f"  → Retrieved {len(docs)} documents")
        
        if not docs:
            return []
        
        # Step 2: FlashRank Reranking
        if use_rerank and self.flashrank and len(docs) > 1:
            docs = self._flashrank_rerank(query, docs)
        
        # Step 3: Cross-Encoder Reranking
        if use_rerank and self.cross_encoder.is_available and len(docs) > 1:
            docs = self.cross_encoder.rerank(
                query, docs,
                top_k=self.config.top_k_rerank
            )
            logger.info(f"  → Cross-encoder reranked to {len(docs)} docs")
        
        # Step 4: Parent Expansion
        if use_parent:
            docs = self.store.expand_to_parents(docs)
            logger.info(f"  → Expanded to {len(docs)} parent documents")
        
        return docs
    
    def _flashrank_rerank(
        self,
        query: str,
        docs: List[Document],
        top_k: int = 5
    ) -> List[Document]:
        """Apply FlashRank reranking."""
        if not self.flashrank:
            return docs
        
        try:
            passages = [
                {"id": i, "text": doc.page_content}
                for i, doc in enumerate(docs)
            ]
            
            rerank_request = RerankRequest(query=query, passages=passages)
            rerank_results = self.flashrank.rerank(rerank_request)
            
            top_indices = [r["id"] for r in rerank_results[:top_k]]
            reranked = [docs[i] for i in top_indices]
            
            logger.info(f"  → FlashRank reranked to {len(reranked)} docs")
            return reranked
            
        except Exception as e:
            logger.warning(f"FlashRank reranking failed: {e}")
            return docs[:top_k]
    
    def similarity_search(
        self,
        query: str,
        k: int = 5
    ) -> List[Document]:
        """Simple similarity search without reranking."""

    def retrieve_for_books(
        self,
        query: str,
        book_ids: List[str],
        top_k: int = 8,
        use_rerank: bool = True,
        use_parent: bool = True,
    ) -> List[Document]:
        """
        Retrieve documents filtered to specific books (by book_id).

        This is the primary method used by the Chain-of-Thought engine
        to query individual expert books during the multi-step reasoning
        pipeline (Physics → Cost → Finance → Appraisal).

        Args:
            query: Search query
            book_ids: List of book_ids to restrict retrieval to
            top_k: Max documents to retrieve
            use_rerank: Whether to apply reranking stages
            use_parent: Whether to expand to parent documents

        Returns:
            List of relevant documents from the specified books
        """
        logger.info(f"📚 Book-filtered retrieval: {book_ids} | query: {query[:50]}...")
        return self.retrieve(
            query=query,
            book_ids=book_ids,
            top_k=top_k,
            use_rerank=use_rerank,
            use_parent=use_parent,
        )
        retriever = self.store.get_retriever(top_k=k)
        return retriever.invoke(query)
