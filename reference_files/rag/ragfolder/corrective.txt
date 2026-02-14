"""
Corrective RAG (C-RAG) Implementation
Author: GreenValue AI Team
Purpose: Filter irrelevant documents using LLM-based relevance scoring.
"""

import logging
from typing import List, Optional, Tuple

from langchain_core.documents import Document

logger = logging.getLogger("greenvalue-rag")


class CorrectiveRAG:
    """
    Corrective RAG for relevance filtering.
    - LLM-based relevance scoring (0-100)
    - Dynamic threshold based on average scores
    - Web fallback for missing information
    """
    
    def __init__(self, llm):
        self.llm = llm
    
    def check_relevance(self, query: str, doc: Document) -> Tuple[bool, float]:
        """
        Check if document is relevant to query.
        
        Returns:
            Tuple of (is_relevant, score)
        """
        prompt = f"""Rate how relevant this document is to the question.
Only respond with a number from 0-100.

QUESTION: {query[:200]}
DOCUMENT: {doc.page_content[:300]}

RELEVANCE SCORE (0-100):"""

        try:
            response = self.llm.invoke(prompt)
            score = int(''.join(filter(str.isdigit, response[:5])))
            score = min(score, 100)
            return score >= 25, score
        except Exception as e:
            logger.warning(f"Relevance check failed: {e}")
            return True, 70  # Default to relevant on failure
    
    def filter_documents(
        self,
        query: str,
        docs: List[Document],
        min_score: int = 25
    ) -> List[Document]:
        """
        Filter irrelevant documents using dynamic threshold.
        
        Args:
            query: Search query
            docs: Documents to filter
            min_score: Minimum relevance score
            
        Returns:
            Filtered documents
        """
        if not docs:
            return docs
        
        # Score all documents
        scored_docs = []
        for doc in docs:
            is_relevant, score = self.check_relevance(query, doc)
            doc.metadata["relevance_score"] = score
            scored_docs.append((doc, score))
        
        # Calculate dynamic threshold
        avg_score = sum(s for _, s in scored_docs) / len(scored_docs)
        dynamic_threshold = max(min_score, avg_score * 0.6)
        
        logger.info(f"C-RAG threshold: {dynamic_threshold:.0f} (avg: {avg_score:.0f})")
        
        # Filter by threshold
        filtered = [doc for doc, score in scored_docs if score >= dynamic_threshold]
        
        # Fallback: return at least top 2 if all filtered out
        if not filtered and docs:
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            filtered = [doc for doc, _ in scored_docs[:2]]
            logger.warning("C-RAG fallback: returning top 2 documents")
        
        return filtered
    
    def web_search_fallback(self, query: str) -> str:
        """
        Web search fallback for missing information.
        Uses DuckDuckGo for privacy.
        """
        logger.info(f"🌐 Web fallback for: {query[:50]}...")
        
        try:
            import urllib.request
            import urllib.parse
            import re
            
            search_query = urllib.parse.quote(f"{query} real estate sustainability")
            url = f"https://html.duckduckgo.com/html/?q={search_query}"
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=5) as response:
                html = response.read().decode('utf-8')
            
            titles = re.findall(r'class="result__a"[^>]*>([^<]+)</a>', html)
            
            if titles:
                news = [f"• {title.strip()}" for title in titles[:3]]
                result = "\n".join(news)
                logger.info(f"Web fallback: found {len(news)} results")
                return f"\n🌐 WEB SEARCH RESULTS:\n{result}\n"
                
        except Exception as e:
            logger.warning(f"Web fallback failed: {e}")
        
        return ""
