"""
GreenValue Document Store
Author: GreenValue AI Team
Purpose: Qdrant-based vector store with parent-document retrieval pattern.
"""

import logging
import uuid
from typing import Dict, List, Optional

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, SparseVectorParams, VectorParams
from langchain_core.documents import Document

from .config import RAGConfig
from .embeddings import EmbeddingManager

logger = logging.getLogger("greenvalue-rag")


class GreenValueDocumentStore:
    """
    Vector store with parent-document retrieval.
    - Child chunks (400 char): For precise search matching
    - Parent chunks (1500 char): For rich LLM context
    """
    
    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        embedding_manager: Optional[EmbeddingManager] = None
    ):
        self.config = config or RAGConfig()
        self.embeddings = embedding_manager or EmbeddingManager(self.config)
        self.client: Optional[QdrantClient] = None
        self.parent_docs: Dict[str, Document] = {}
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize Qdrant client and collections."""
        if self._initialized:
            return True
        
        try:
            logger.info(f"Connecting to Qdrant at {self.config.qdrant_url}")
            self.client = QdrantClient(url=self.config.qdrant_url)
            
            # Initialize embeddings
            if not self.embeddings.initialize():
                logger.error("Failed to initialize embeddings")
                return False
            
            self._initialized = True
            logger.info("✅ Document store initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize document store: {e}")
            return False
    
    def setup_collections(self, force_recreate: bool = False) -> bool:
        """Create or verify Qdrant collections."""
        if not self._initialized:
            self.initialize()
        
        collections = [
            self.config.child_collection,
            self.config.parent_collection
        ]
        
        for coll_name in collections:
            exists = self._collection_exists(coll_name)
            
            if exists and not force_recreate:
                logger.info(f"✅ Collection exists: {coll_name}")
                continue
            
            if exists:
                self.client.delete_collection(coll_name)
                logger.info(f"🗑️ Deleted collection: {coll_name}")
            
            self.client.create_collection(
                collection_name=coll_name,
                vectors_config={
                    "dense": VectorParams(
                        size=self.config.dense_vector_size,
                        distance=Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(
                        index=models.SparseIndexParams(on_disk=False)
                    )
                }
            )
            logger.info(f"✅ Created collection: {coll_name}")
        
        return True
    
    def _collection_exists(self, name: str) -> bool:
        """Check if collection exists in Qdrant."""
        try:
            self.client.get_collection(name)
            return True
        except Exception:
            return False
    
    def get_collection_stats(self) -> Dict:
        """Get statistics for all collections."""
        stats = {}
        for coll_name in [self.config.child_collection, self.config.parent_collection]:
            try:
                info = self.client.get_collection(coll_name)
                stats[coll_name] = {
                    "points_count": info.points_count,
                    "status": info.status.value if hasattr(info.status, 'value') else str(info.status),
                }
            except Exception as e:
                stats[coll_name] = {"error": str(e)}
        return stats
    
    def add_documents(
        self,
        documents: List[Document],
        collection: str = None,
        batch_size: int = 50
    ) -> int:
        """Add documents to a collection."""
        if not self._initialized:
            self.initialize()
        
        collection = collection or self.config.child_collection
        
        from langchain_qdrant import QdrantVectorStore, RetrievalMode
        
        vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=collection,
            embedding=self.embeddings.dense,
            sparse_embedding=self.embeddings.sparse,
            retrieval_mode=RetrievalMode.HYBRID,
            vector_name="dense",
            sparse_vector_name="sparse",
        )
        
        total_added = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            vector_store.add_documents(documents=batch)
            total_added += len(batch)
            logger.debug(f"Added batch {i//batch_size + 1}: {len(batch)} documents")
        
        return total_added
    
    def get_retriever(
        self,
        category_filter: Optional[str] = None,
        top_k: int = 10
    ):
        """Get a retriever with optional category filtering."""
        if not self._initialized:
            self.initialize()
        
        from langchain_qdrant import QdrantVectorStore, RetrievalMode
        
        vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.config.child_collection,
            embedding=self.embeddings.dense,
            sparse_embedding=self.embeddings.sparse,
            retrieval_mode=RetrievalMode.HYBRID,
            vector_name="dense",
            sparse_vector_name="sparse",
        )
        
        search_kwargs = {"k": top_k}
        
        if category_filter:
            search_kwargs["filter"] = models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.category",
                        match=models.MatchValue(value=category_filter)
                    )
                ]
            )
            logger.info(f"🏷️ Category filter: {category_filter}")
        
        return vector_store.as_retriever(search_kwargs=search_kwargs)
    
    def get_parent_document(self, parent_id: str) -> Optional[Document]:
        """Retrieve parent document by ID."""
        # First check in-memory cache
        if parent_id in self.parent_docs:
            return self.parent_docs[parent_id]
        
        # Query from Qdrant
        try:
            results = self.client.scroll(
                collection_name=self.config.parent_collection,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.parent_id",
                            match=models.MatchValue(value=parent_id)
                        )
                    ]
                ),
                limit=1,
                with_payload=True
            )
            
            if results[0]:
                point = results[0][0]
                return Document(
                    page_content=point.payload.get("page_content", ""),
                    metadata=point.payload.get("metadata", {})
                )
        except Exception as e:
            logger.warning(f"Failed to retrieve parent document: {e}")
        
        return None
    
    def expand_to_parents(self, docs: List[Document]) -> List[Document]:
        """Expand child documents to their parent documents."""
        expanded = []
        seen_parents = set()
        
        for doc in docs:
            parent_id = doc.metadata.get("parent_id")
            
            if parent_id and parent_id not in seen_parents:
                parent_doc = self.get_parent_document(parent_id)
                if parent_doc:
                    expanded.append(parent_doc)
                    seen_parents.add(parent_id)
                else:
                    expanded.append(doc)
            elif parent_id not in seen_parents:
                expanded.append(doc)
        
        return expanded if expanded else docs
