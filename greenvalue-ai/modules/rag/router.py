"""
Enhanced Smart Router - Professional RAG Upgrade
Author: GreenValue AI Team (Enhanced by Senior RAG Developer)
Purpose: LLM-based semantic domain routing for PropTech queries.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from enum import Enum

from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger("greenvalue-rag")


class PropTechDomain(Enum):
    """PropTech domain categories for specialized routing."""
    VALUATION = "valuation"
    ENERGY = "energy"
    FINANCE = "finance"
    RETROFIT = "retrofit"
    SUSTAINABILITY = "sustainability"
    LEGAL = "legal"
    GENERAL = "general"


# ─── RAG Knowledge Library: 8-Book Expert Mapping ────────────

BOOK_LIBRARY = {
    "IVS-Jan-2025": {
        "book_id": "book_01_ivs",
        "title": "International Valuation Standards (IVS) January 2025",
        "filename_pattern": "ivs",
        "domains": [PropTechDomain.VALUATION, PropTechDomain.LEGAL],
        "authority": 1.0,         # Highest — official standard
        "expertise": "Official appraisal standard. Defines Market Value (IVS 104), "
                     "valuation approaches, scope of work, assumptions & limiting conditions.",
        "chain_role": "appraisal_expert",
        "chain_order": 4,         # Last in chain — provides legal basis
    },
    "Appraisal-of-Real-Estate-15th": {
        "book_id": "book_02_appraisal",
        "title": "The Appraisal of Real Estate, 15th Edition",
        "filename_pattern": "appraisal",
        "domains": [PropTechDomain.VALUATION],
        "authority": 0.95,
        "expertise": "Three fundamental U.S. valuation approaches: Cost, Sales Comparison, "
                     "Income. Comparable adjustment grids, depreciation, highest & best use.",
        "chain_role": "appraisal_expert",
        "chain_order": 4,
    },
    "Sustainable-Home-Refurbishment": {
        "book_id": "book_03_thermal",
        "title": "Sustainable Home Refurbishment",
        "filename_pattern": "sustainable.*home|refurbishment",
        "domains": [PropTechDomain.ENERGY],
        "authority": 0.90,
        "expertise": "Thermal physics, U-Value reduction strategies, energy labels (A–G), "
                     "heat loss calculations, building fabric performance.",
        "chain_role": "physics_expert",
        "chain_order": 1,         # First in chain — diagnoses the problem
    },
    "Green-Building-Illustrated": {
        "book_id": "book_04_architecture",
        "title": "Green Building Illustrated",
        "filename_pattern": "green.*building.*illustrated",
        "domains": [PropTechDomain.RETROFIT, PropTechDomain.SUSTAINABILITY],
        "authority": 0.85,
        "expertise": "Architectural integration of green technologies. Solar panel placement, "
                     "passive design, daylighting, structural feasibility.",
        "chain_role": "design_expert",
        "chain_order": 2,
    },
    "Sustainable-Construction": {
        "book_id": "book_05_materials",
        "title": "Sustainable Construction",
        "filename_pattern": "sustainable.*construction",
        "domains": [PropTechDomain.SUSTAINABILITY],
        "authority": 0.85,
        "expertise": "Materials science, life cycle analysis (LCA), carbon footprint, "
                     "embodied energy. Rock wool vs EPS vs aerogel comparisons.",
        "chain_role": "materials_expert",
        "chain_order": 2,
    },
    "Book-on-Flipping-Houses": {
        "book_id": "book_06_costs",
        "title": "The Book on Flipping Houses (J. Scott)",
        "filename_pattern": "flipping|j.*scott",
        "domains": [PropTechDomain.FINANCE, PropTechDomain.RETROFIT],
        "authority": 0.80,
        "expertise": "Construction/renovation cost estimation. Cost tables by component, "
                     "contractor budgeting, $/sqft benchmarks, rehab scope.",
        "chain_role": "cost_expert",
        "chain_order": 2,         # Second in chain — estimates cost
    },
    "What-Every-RE-Investor": {
        "book_id": "book_07_finance",
        "title": "What Every Real Estate Investor Needs to Know About Cash Flow",
        "filename_pattern": "investor|cash.*flow",
        "domains": [PropTechDomain.FINANCE],
        "authority": 0.85,
        "expertise": "Financial modeling: Cap Rate, NOI, DCF, IRR, NPV, Cash-on-Cash Return. "
                     "Converts energy savings into property value via income approach.",
        "chain_role": "finance_expert",
        "chain_order": 3,         # Third in chain — calculates ROI
    },
    "REALES": {
        "book_id": "book_08_glossary",
        "title": "REALES — Real Estate Fundamentals",
        "filename_pattern": "reales",
        "domains": [PropTechDomain.GENERAL],
        "authority": 0.70,
        "expertise": "General real estate reference. Glossary (Easement, Zoning, Liens), "
                     "basic concepts for consumer-facing explanations.",
        "chain_role": "reference",
        "chain_order": 99,        # Used on-demand, not in main chain
    },
}


def get_books_for_domain(domain: PropTechDomain) -> list:
    """Return book configs matching a domain, sorted by authority (highest first)."""
    matches = [
        book for book in BOOK_LIBRARY.values()
        if domain in book["domains"]
    ]
    return sorted(matches, key=lambda b: b["authority"], reverse=True)


def get_chain_of_thought_books() -> list:
    """Return the 4-step chain-of-thought book sequence."""
    chain = [
        book for book in BOOK_LIBRARY.values()
        if book["chain_order"] < 99
    ]
    return sorted(chain, key=lambda b: b["chain_order"])


def identify_book_from_filename(filename: str) -> dict | None:
    """Match a PDF filename to its book config using filename patterns."""
    import re as _re
    fn_lower = filename.lower()
    for book in BOOK_LIBRARY.values():
        if _re.search(book["filename_pattern"], fn_lower):
            return book
    return None


class QueryComplexity(Enum):
    """Query complexity levels for adaptive processing."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class LLMDomainRouter:
    """
    Fast local LLM-based domain router for PropTech queries.
    Uses llama3.2:1b for rapid semantic classification.
    """
    
    def __init__(self, ollama_host: str = "http://ollama:11434"):
        self.ollama_host = ollama_host
        self.llm = None
        self._initialized = False
        
        # Domain classification prompt
        self.domain_prompt = ChatPromptTemplate.from_template("""
You are a PropTech domain classifier. Analyze the query and classify it into ONE domain.

DOMAINS:
- valuation: Property appraisal, market value, IVS standards, pricing
- energy: Energy efficiency, thermal performance, U-values, consumption
- finance: ROI, costs, investment analysis, payback periods, budgets
- retrofit: Renovations, upgrades, improvements, construction work
- sustainability: Green building, carbon emissions, environmental impact
- legal: Regulations, compliance, standards, codes, legal requirements
- general: Other real estate topics not fitting above categories

QUERY: {query}

Respond with ONLY the domain name (lowercase, one word).
""")
        
        # Complexity assessment prompt
        self.complexity_prompt = ChatPromptTemplate.from_template("""
Assess the complexity of this PropTech query for RAG processing.

COMPLEXITY LEVELS:
- simple: Single concept, direct question (e.g., "What is U-value?")
- moderate: Multiple concepts, requires analysis (e.g., "Compare insulation costs vs energy savings")
- complex: Multi-domain, requires synthesis (e.g., "Create ROI analysis for sustainable retrofit considering legal compliance")

QUERY: {query}

Respond with ONLY: simple, moderate, or complex
""")
    
    def initialize(self) -> bool:
        """Initialize the LLM router."""
        if self._initialized:
            return True
        
        try:
            # Use fast llama3.2:3b for routing
            self.llm = OllamaLLM(
                model="llama3.2:3b",
                base_url=self.ollama_host,
                temperature=0.1  # Low temperature for consistent classification
            )
            
            # Test the connection
            test_response = self.llm.invoke("test")
            
            self._initialized = True
            logger.info("✅ LLM Domain Router initialized with llama3.2:3b")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM router: {e}")
            return False
    
    def classify_domain(self, query: str) -> PropTechDomain:
        """Classify query into PropTech domain using LLM."""
        if not self._initialized:
            if not self.initialize():
                return self._fallback_domain_classification(query)
        
        try:
            # Get LLM classification
            prompt = self.domain_prompt.format(query=query)
            response = self.llm.invoke(prompt).strip().lower()
            
            # Map response to enum
            domain_mapping = {
                "valuation": PropTechDomain.VALUATION,
                "energy": PropTechDomain.ENERGY,
                "finance": PropTechDomain.FINANCE,
                "retrofit": PropTechDomain.RETROFIT,
                "sustainability": PropTechDomain.SUSTAINABILITY,
                "legal": PropTechDomain.LEGAL,
                "general": PropTechDomain.GENERAL
            }
            
            domain = domain_mapping.get(response, PropTechDomain.GENERAL)
            logger.debug(f"LLM classified '{query[:30]}...' as {domain.value}")
            return domain
            
        except Exception as e:
            logger.warning(f"LLM domain classification failed: {e}")
            return self._fallback_domain_classification(query)
    
    def assess_complexity(self, query: str) -> QueryComplexity:
        """Assess query complexity using LLM."""
        if not self._initialized:
            if not self.initialize():
                return self._fallback_complexity_assessment(query)
        
        try:
            prompt = self.complexity_prompt.format(query=query)
            response = self.llm.invoke(prompt).strip().lower()
            
            complexity_mapping = {
                "simple": QueryComplexity.SIMPLE,
                "moderate": QueryComplexity.MODERATE,
                "complex": QueryComplexity.COMPLEX
            }
            
            complexity = complexity_mapping.get(response, QueryComplexity.MODERATE)
            logger.debug(f"LLM assessed complexity as {complexity.value}")
            return complexity
            
        except Exception as e:
            logger.warning(f"LLM complexity assessment failed: {e}")
            return self._fallback_complexity_assessment(query)
    
    def _fallback_domain_classification(self, query: str) -> PropTechDomain:
        """Fallback keyword-based domain classification."""
        query_lower = query.lower()
        
        # Domain keywords
        domain_keywords = {
            PropTechDomain.VALUATION: ['valuation', 'appraisal', 'market value', 'price', 'ivs', 'worth'],
            PropTechDomain.ENERGY: ['energy', 'efficiency', 'thermal', 'u-value', 'r-value', 'kwh', 'consumption'],
            PropTechDomain.FINANCE: ['roi', 'cost', 'investment', 'budget', 'payback', 'npv', 'irr', 'financial'],
            PropTechDomain.RETROFIT: ['renovation', 'retrofit', 'upgrade', 'improvement', 'construction', 'install'],
            PropTechDomain.SUSTAINABILITY: ['green', 'sustainable', 'carbon', 'emission', 'environmental', 'eco'],
            PropTechDomain.LEGAL: ['regulation', 'compliance', 'standard', 'code', 'law', 'legal', 'requirement']
        }
        
        # Score each domain
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            domain_scores[domain] = score
        
        # Return highest scoring domain or general
        best_domain = max(domain_scores, key=domain_scores.get)
        return best_domain if domain_scores[best_domain] > 0 else PropTechDomain.GENERAL
    
    def _fallback_complexity_assessment(self, query: str) -> QueryComplexity:
        """Fallback rule-based complexity assessment."""
        query_lower = query.lower()
        
        # Complexity indicators
        complex_indicators = ['compare', 'analyze', 'calculate', 'optimize', 'recommend', 'strategy']
        simple_indicators = ['what is', 'define', 'explain', 'how much', 'when']
        
        complex_score = sum(1 for indicator in complex_indicators if indicator in query_lower)
        simple_score = sum(1 for indicator in simple_indicators if indicator in query_lower)
        
        # Word count and question marks as additional indicators
        word_count = len(query.split())
        question_marks = query.count('?')
        
        if complex_score > 0 or word_count > 20:
            return QueryComplexity.COMPLEX
        elif simple_score > 0 or (word_count < 8 and question_marks == 1):
            return QueryComplexity.SIMPLE
        else:
            return QueryComplexity.MODERATE


class EnhancedSemanticRouter:
    """
    Enhanced semantic router with LLM-based domain classification.
    Combines fast LLM routing with adaptive strategy selection.
    """
    
    def __init__(self, ollama_host: str = "http://ollama:11434"):
        self.domain_router = LLMDomainRouter(ollama_host)
        
        # Domain-specific retrieval strategies (book-aware)
        self.domain_strategies = {
            PropTechDomain.VALUATION: {
                "top_k": 8,
                "use_rerank": True,
                "use_parent": True,
                "category_filter": "valuation",
                "priority_metadata": ["ivs", "appraisal", "market"],
                "preferred_books": ["book_01_ivs", "book_02_appraisal"],
                "authority_boost": 1.3,  # Boost IVS/Appraisal chunks
            },
            PropTechDomain.ENERGY: {
                "top_k": 6,
                "use_rerank": True,
                "use_parent": False,  # Energy data often in tables
                "category_filter": "energy",
                "priority_metadata": ["u_values", "energy_consumption", "thermal"],
                "preferred_books": ["book_03_thermal"],
                "authority_boost": 1.2,
            },
            PropTechDomain.FINANCE: {
                "top_k": 10,
                "use_rerank": True,
                "use_parent": True,
                "category_filter": "finance",
                "priority_metadata": ["roi_indicators", "currencies", "contains_roi_analysis"],
                "preferred_books": ["book_06_costs", "book_07_finance"],
                "authority_boost": 1.2,
            },
            PropTechDomain.RETROFIT: {
                "top_k": 7,
                "use_rerank": True,
                "use_parent": True,
                "category_filter": "retrofit",
                "priority_metadata": ["renovation", "construction", "improvement"],
                "preferred_books": ["book_04_architecture", "book_06_costs"],
                "authority_boost": 1.1,
            },
            PropTechDomain.SUSTAINABILITY: {
                "top_k": 6,
                "use_rerank": True,
                "use_parent": False,
                "category_filter": "sustainability",
                "priority_metadata": ["co2_emissions", "green", "environmental"],
                "preferred_books": ["book_04_architecture", "book_05_materials"],
                "authority_boost": 1.1,
            },
            PropTechDomain.LEGAL: {
                "top_k": 5,
                "use_rerank": False,  # Legal text is usually precise
                "use_parent": True,
                "category_filter": "legal",
                "priority_metadata": ["regulation", "compliance", "standard"],
                "preferred_books": ["book_01_ivs"],
                "authority_boost": 1.5,  # Strong boost for IVS in legal
            },
            PropTechDomain.GENERAL: {
                "top_k": 8,
                "use_rerank": True,
                "use_parent": True,
                "category_filter": None,
                "priority_metadata": [],
                "preferred_books": ["book_08_glossary"],
                "authority_boost": 1.0,
            }
        }
        
        # Complexity-based adjustments
        self.complexity_adjustments = {
            QueryComplexity.SIMPLE: {"top_k_multiplier": 0.7, "use_crag": False},
            QueryComplexity.MODERATE: {"top_k_multiplier": 1.0, "use_crag": True},
            QueryComplexity.COMPLEX: {"top_k_multiplier": 1.5, "use_crag": True}
        }
    
    def route_query(self, query: str) -> Dict:
        """
        Route query using LLM-based domain classification.
        
        Returns:
            Dict with routing strategy and parameters
        """
        # Classify domain and complexity
        domain = self.domain_router.classify_domain(query)
        complexity = self.domain_router.assess_complexity(query)
        
        # Get base strategy for domain
        base_strategy = self.domain_strategies[domain].copy()
        
        # Apply complexity adjustments
        complexity_adj = self.complexity_adjustments[complexity]
        
        # Adjust top_k based on complexity
        base_strategy["top_k"] = int(
            base_strategy["top_k"] * complexity_adj["top_k_multiplier"]
        )
        
        # Add complexity-specific settings
        base_strategy.update({
            "domain": domain.value,
            "complexity": complexity.value,
            "use_crag": complexity_adj["use_crag"],
            "query_type": self._get_query_type(query, domain),
            "description": f"{domain.value.title()} query with {complexity.value} complexity"
        })
        
        logger.info(f"🧠 Routed to {domain.value} domain ({complexity.value})")
        return base_strategy
    
    def _get_query_type(self, query: str, domain: PropTechDomain) -> str:
        """Determine specific query type within domain."""
        query_lower = query.lower()
        
        # Domain-specific query types
        if domain == PropTechDomain.FINANCE:
            if any(word in query_lower for word in ['roi', 'return', 'payback']):
                return "roi_analysis"
            elif any(word in query_lower for word in ['cost', 'budget', 'price']):
                return "cost_analysis"
            else:
                return "financial_query"
        
        elif domain == PropTechDomain.ENERGY:
            if any(word in query_lower for word in ['u-value', 'thermal', 'insulation']):
                return "thermal_analysis"
            elif any(word in query_lower for word in ['consumption', 'kwh', 'usage']):
                return "energy_consumption"
            else:
                return "energy_efficiency"
        
        elif domain == PropTechDomain.VALUATION:
            if any(word in query_lower for word in ['market', 'price', 'worth']):
                return "market_valuation"
            elif any(word in query_lower for word in ['ivs', 'standard', 'method']):
                return "valuation_method"
            else:
                return "property_valuation"
        
        else:
            return f"{domain.value}_query"
    
    def get_domain_context(self, domain: PropTechDomain) -> str:
        """Get domain-specific context for LLM prompts, referencing the book library."""
        domain_contexts = {
            PropTechDomain.VALUATION: """
Focus on property valuation methodologies per IVS-2025 standards and The Appraisal of Real Estate (15th Ed.).
Apply the three valuation approaches: Cost Approach, Sales Comparison Approach, and Income Approach.
Cite IVS 104 (Market Value) and IVS 101/102 (Scope of Work, Assumptions) where applicable.
Reference comparable sales adjustments, depreciation, and highest & best use analysis.
""",
            PropTechDomain.ENERGY: """
Focus on energy efficiency per Sustainable Home Refurbishment reference.
Apply building physics: U-values, R-values, thermal bridging, heat loss calculations.
Reference energy performance certificates (A through G) and EU/national energy standards.
Provide specific insulation strategies and quantified energy savings in kWh/year.
""",
            PropTechDomain.FINANCE: """
Focus on financial analysis per What Every Real Estate Investor Needs to Know About Cash Flow
and The Book on Flipping Houses (J. Scott) for cost estimation.
Apply Cap Rate, NOI, DCF, IRR, NPV, and Cash-on-Cash Return formulas.
Convert energy savings into property value via Income Approach: Value = NOI / Cap Rate.
Include specific cost estimates in $/sqft from renovation cost tables.
""",
            PropTechDomain.RETROFIT: """
Focus on renovation strategies per Green Building Illustrated and The Book on Flipping Houses.
Provide architectural integration guidance for green technologies (solar, insulation, HVAC).
Include structural feasibility warnings and cost estimates per component.
Reference passive design principles, daylighting, and building envelope improvements.
""",
            PropTechDomain.SUSTAINABILITY: """
Focus on environmental impact per Sustainable Construction and Green Building Illustrated.
Apply life cycle analysis (LCA), embodied energy calculations, and carbon footprint metrics.
Compare materials: rock wool vs EPS vs aerogel vs cellulose with specific thermal conductivity values.
Reference LEED, BREEAM, and green building certification requirements.
""",
            PropTechDomain.LEGAL: """
Focus on regulatory compliance per International Valuation Standards (IVS) January 2025.
Reference IVS 101 (Scope of Work), IVS 102 (Investigations), IVS 104 (Bases of Value).
Include assumptions, limiting conditions, and disclaimer language per IVS requirements.
This domain has the highest authority weight — all legal citations must be precise.
""",
            PropTechDomain.GENERAL: """
Provide comprehensive real estate analysis referencing REALES fundamentals.
Explain basic real estate concepts (Easement, Zoning, Liens, Title) in consumer-friendly language.
Reference specialized books when the query touches valuation, energy, finance, or sustainability.
""",
        }
        
        return domain_contexts.get(domain, "")


# Convenience functions for backward compatibility
def classify_query(query: str) -> str:
    """Legacy function for query classification."""
    router = EnhancedSemanticRouter()
    result = router.route_query(query)
    return result["query_type"]


def route_query(query: str) -> Dict:
    """Main routing function."""
    router = EnhancedSemanticRouter()
    return router.route_query(query)


class AdaptiveRAGStrategy:
    """
    Enhanced adaptive RAG with LLM-based routing.
    Replaces the previous keyword-based approach.
    """
    
    @staticmethod
    def route(query: str) -> Dict:
        """Route query using enhanced semantic router."""
        router = EnhancedSemanticRouter()
        return router.route_query(query)
    
    @staticmethod
    def get_strategy_description(strategy: Dict) -> str:
        """Get human-readable strategy description."""
        domain = strategy.get("domain", "general")
        complexity = strategy.get("complexity", "moderate")
        top_k = strategy.get("top_k", 5)
        
        return f"Domain: {domain.title()}, Complexity: {complexity}, Retrieving: {top_k} documents"
