"""
GreenValue RAG Pipeline
Author: GreenValue AI Team
Purpose: Main orchestrator combining all RAG components.
"""

import logging
from typing import Dict, List, Optional

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import OllamaLLM

from .config import RAGConfig
from .embeddings import EmbeddingManager
from .store import GreenValueDocumentStore
from .ingestion import EnhancedDocumentIngestionPipeline
from .retrieval import RetrievalEngine
from .corrective import CorrectiveRAG
from .router import EnhancedSemanticRouter, AdaptiveRAGStrategy
from .graph import KnowledgeGraph, PropertyGraph
from .memory import SQLiteMemory

logger = logging.getLogger("greenvalue-rag")


# Prompt template for GreenValue domain
GREENVALUE_PROMPT = """You are an expert real estate advisor specializing in property valuation and sustainability.
Use the following context to answer the question accurately.

CONTEXT:
{context}

{graph_context}
{user_context}

QUESTION: {question}

IMPORTANT:
- Base your answer on the provided context
- Provide specific recommendations when applicable
- Mention energy efficiency implications
- If uncertain, acknowledge limitations

ANSWER:"""


class GreenValueRAG:
    """
    Main RAG orchestrator for GreenValue AI.
    
    Pipeline:
    1. Semantic Routing (classify query)
    2. Adaptive Strategy (select RAG depth)
    3. Hybrid Search (dense + sparse)
    4. FlashRank Reranking
    5. C-RAG Filtering (optional)
    6. Cross-Encoder Reranking (optional)
    7. Parent Expansion
    8. LLM Generation
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self._initialized = False
        
        # Components (lazy loaded)
        self._embeddings = None
        self._store = None
        self._retrieval = None
        self._ingestion = None
        self._crag = None
        self._memory = None
        self._llm = None
        self._graph = None
        self._property_graph = None
    
    def initialize(self) -> bool:
        """Initialize all RAG components."""
        if self._initialized:
            return True
        
        try:
            logger.info("🚀 Initializing GreenValue RAG...")
            
            # Core components
            self._embeddings = EmbeddingManager(self.config)
            self._store = GreenValueDocumentStore(self.config, self._embeddings)
            self._retrieval = RetrievalEngine(self._store, self.config)
            self._ingestion = EnhancedDocumentIngestionPipeline(self.config, self._store)
            
            # Initialize store
            if not self._store.initialize():
                logger.error("Failed to initialize document store")
                return False
            
            # LLM
            self._llm = OllamaLLM(
                model=self.config.llm_model,
                base_url=self.config.ollama_host
            )
            
            # Enhancement components
            self._crag = CorrectiveRAG(self._llm)
            self._memory = SQLiteMemory(self.config.memory_db_path)
            self._graph = KnowledgeGraph()
            self._property_graph = PropertyGraph(self._llm)
            
            self._initialized = True
            logger.info("✅ GreenValue RAG initialized")
            return True
            
        except Exception as e:
            logger.error(f"RAG initialization failed: {e}")
            return False
    
    def build_knowledge_base(self, force_recreate: bool = False) -> Dict:
        """Build knowledge base from PDF files."""
        if not self._initialized:
            self.initialize()
        
        return self._ingestion.ingest_directory(
            directory=self.config.knowledge_base_path,
            force_recreate=force_recreate
        )
    
    def ingest_document(self, file_path: str) -> Dict:
        """Ingest a single document."""
        if not self._initialized:
            self.initialize()
        
        return self._ingestion.ingest_file(file_path)
    
    def query(
        self,
        question: str,
        category: Optional[str] = None,
        user_id: str = "default",
        use_adaptive: bool = True
    ) -> Dict:
        """
        Execute full RAG query pipeline.
        
        Args:
            question: User question
            category: Optional category filter
            user_id: User ID for personalization
            use_adaptive: Whether to use adaptive strategy
            
        Returns:
            Dict with answer, sources, and metadata
        """
        if not self._initialized:
            self.initialize()
        
        logger.info(f"🔍 Query: {question[:50]}...")
        
        # Step 1: Route query
        route = AdaptiveRAGStrategy.route(question) if use_adaptive else {
            "query_type": EnhancedSemanticRouter.classify(question),
            "complexity": "moderate",
            "use_crag": True,
            "use_cross_encoder": False,
            "top_k": 5,
            "use_parent": True,
        }
        
        logger.info(f"  → Route: {route['query_type']} ({route['description']})")
        
        # Step 2: Log query
        query_id = self._memory.log_query(
            user_id, question, route["query_type"], category
        )
        
        # Step 3: Retrieve documents
        docs = self._retrieval.retrieve(
            query=question,
            category=category,
            top_k=route["top_k"],
            use_rerank=True,
            use_parent=route["use_parent"]
        )
        
        # Step 4: C-RAG filtering (if enabled)
        if route.get("use_crag") and self._crag:
            docs = self._crag.filter_documents(question, docs)
            logger.info(f"  → C-RAG filtered to {len(docs)} docs")
        
        # Step 5: Build context
        context = self._build_context(docs)
        
        # Graph context (optional - may not be available if no graph DB)
        graph_context = ""
        try:
            if self._graph:
                graph_context = self._graph.get_graph_context(question)
        except Exception as e:
            logger.debug(f"Graph context unavailable: {e}")
        
        user_context = self._memory.get_personalization_context(user_id)
        
        # Step 6: Generate response
        response = self._generate(question, context, graph_context, user_context)
        
        return {
            "answer": response,
            "query_id": query_id,
            "sources": [
                {
                    "content": doc.page_content[:200],
                    "category": doc.metadata.get("category"),
                    "source_file": doc.metadata.get("source_file"),
                }
                for doc in docs[:3]
            ],
            "route": route,
        }
    
    def _build_context(self, docs: List[Document]) -> str:
        """Build context string from documents."""
        if not docs:
            return "No relevant documents found."
        
        return "\n\n---\n\n".join([
            f"[{doc.metadata.get('category', 'Unknown')}] {doc.page_content}"
            for doc in docs
        ])
    
    def _generate(
        self,
        question: str,
        context: str,
        graph_context: str = "",
        user_context: str = ""
    ) -> str:
        """Generate response using LLM."""
        prompt = ChatPromptTemplate.from_template(GREENVALUE_PROMPT)
        
        chain = (
            {
                "context": lambda x: context,
                "graph_context": lambda x: graph_context,
                "user_context": lambda x: user_context,
                "question": RunnablePassthrough()
            }
            | prompt
            | self._llm
            | StrOutputParser()
        )
        
        return chain.invoke(question)
    
    def add_feedback(self, query_id: int, helpful: bool, feedback_text: str = None):
        """Add feedback for a query."""
        self._memory.add_feedback(query_id, helpful, feedback_text)
    
    def get_status(self) -> Dict:
        """Get RAG system status."""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        return {
            "status": "ready",
            "collections": self._store.get_collection_stats(),
            "embeddings_ready": self._embeddings.is_ready,
            "config": {
                "llm_model": self.config.llm_model,
                "dense_model": self.config.dense_model,
                "child_collection": self.config.child_collection,
                "parent_collection": self.config.parent_collection,
            }
        }


# Convenience function
def create_rag(config: Optional[RAGConfig] = None) -> GreenValueRAG:
    """Create and initialize a GreenValue RAG instance."""
    rag = GreenValueRAG(config)
    rag.initialize()
    return rag
