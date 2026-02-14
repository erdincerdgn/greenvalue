"""
Advanced Query Expansion System - Final 5% Optimization
Author: GreenValue AI Team (Enhanced by Senior RAG Developer)
Purpose: PropTech-specific query expansion for better retrieval accuracy.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger("greenvalue-rag")


class ExpansionStrategy(Enum):
    """Query expansion strategies."""
    SYNONYM = "synonym"
    SEMANTIC = "semantic"
    DOMAIN_SPECIFIC = "domain_specific"
    CONTEXTUAL = "contextual"
    HYBRID = "hybrid"


@dataclass
class ExpandedQuery:
    """Expanded query with metadata."""
    original_query: str
    expanded_terms: List[str]
    domain_synonyms: List[str]
    semantic_variations: List[str]
    final_query: str
    expansion_strategy: ExpansionStrategy
    confidence_score: float


class PropTechQueryExpander:
    """
    Advanced query expansion system for PropTech domain.
    
    Features:
    - Domain-specific synonym expansion
    - Semantic query variations using LLM
    - Technical term normalization
    - Multi-language support preparation
    - Context-aware expansion
    """
    
    def __init__(self, ollama_host: str = "http://ollama:11434"):
        self.ollama_host = ollama_host
        self.llm = None
        self._initialized = False
        
        # PropTech domain knowledge base
        self.proptech_synonyms = {
            # Energy Efficiency Terms
            "energy efficiency": [
                "energy performance", "thermal efficiency", "energy rating",
                "energy consumption", "energy saving", "efficiency rating"
            ],
            "insulation": [
                "thermal insulation", "building insulation", "wall insulation",
                "roof insulation", "cavity insulation", "external insulation"
            ],
            "u-value": [
                "u value", "thermal transmittance", "heat transfer coefficient",
                "thermal conductivity", "insulation value"
            ],
            "r-value": [
                "r value", "thermal resistance", "insulation rating",
                "thermal performance", "resistance value"
            ],
            
            # Financial Terms
            "roi": [
                "return on investment", "investment return", "payback",
                "financial return", "profit margin", "investment yield"
            ],
            "payback period": [
                "payback time", "return period", "break-even period",
                "recovery time", "amortization period"
            ],
            "npv": [
                "net present value", "present value", "discounted value",
                "investment value", "financial value"
            ],
            "irr": [
                "internal rate of return", "rate of return", "yield rate",
                "discount rate", "return rate"
            ],
            
            # Property Valuation Terms
            "property valuation": [
                "property appraisal", "real estate valuation", "asset valuation",
                "property assessment", "market valuation", "property worth"
            ],
            "ivs": [
                "international valuation standards", "valuation standards",
                "appraisal standards", "valuation methodology"
            ],
            "market value": [
                "fair market value", "market price", "property value",
                "assessed value", "appraised value"
            ],
            
            # Retrofit & Construction Terms
            "retrofit": [
                "renovation", "refurbishment", "modernization", "upgrade",
                "improvement", "rehabilitation", "remodeling"
            ],
            "construction": [
                "building", "development", "erection", "assembly",
                "fabrication", "building work"
            ],
            "renovation": [
                "refurbishment", "restoration", "modernization", "upgrade",
                "improvement", "remodeling", "rehabilitation"
            ],
            
            # Sustainability Terms
            "sustainability": [
                "sustainable development", "green building", "eco-friendly",
                "environmental performance", "carbon neutral", "green design"
            ],
            "carbon footprint": [
                "carbon emissions", "co2 emissions", "greenhouse gas",
                "carbon impact", "environmental impact"
            ],
            "green building": [
                "sustainable building", "eco building", "environmental building",
                "leed building", "breeam building", "green construction"
            ],
            
            # Legal & Regulatory Terms
            "building regulations": [
                "building codes", "construction standards", "building standards",
                "regulatory requirements", "compliance standards"
            ],
            "compliance": [
                "regulatory compliance", "standard compliance", "code compliance",
                "legal compliance", "conformity"
            ],
            
            # Technical Terms
            "thermal bridge": [
                "thermal bridging", "cold bridge", "heat bridge",
                "thermal bypass", "thermal leak"
            ],
            "air leakage": [
                "air infiltration", "air permeability", "air tightness",
                "draft", "air seepage"
            ],
            "ventilation": [
                "air circulation", "air exchange", "mechanical ventilation",
                "natural ventilation", "hvac system"
            ]
        }
        
        # Technical abbreviations and their expansions
        self.technical_abbreviations = {
            "hvac": "heating ventilation air conditioning",
            "leed": "leadership in energy and environmental design",
            "breeam": "building research establishment environmental assessment method",
            "epc": "energy performance certificate",
            "ber": "building energy rating",
            "sap": "standard assessment procedure",
            "sbem": "simplified building energy model",
            "cop": "coefficient of performance",
            "eer": "energy efficiency ratio",
            "seer": "seasonal energy efficiency ratio",
            "hspf": "heating seasonal performance factor"
        }
        
        # Domain-specific query patterns
        self.query_patterns = {
            "cost_analysis": [
                r"cost.*(?:of|for|to)",
                r"price.*(?:of|for|to)",
                r"budget.*(?:for|to)",
                r"expense.*(?:of|for|to)"
            ],
            "roi_analysis": [
                r"roi.*(?:of|for|from)",
                r"return.*(?:on|from)",
                r"payback.*(?:period|time)",
                r"profit.*(?:from|of)"
            ],
            "energy_performance": [
                r"energy.*(?:efficiency|performance|rating)",
                r"thermal.*(?:performance|efficiency)",
                r"u.?value",
                r"r.?value"
            ],
            "regulatory": [
                r"regulation.*(?:for|of)",
                r"compliance.*(?:with|to)",
                r"standard.*(?:for|of)",
                r"code.*(?:for|of)"
            ]
        }
        
        # Semantic expansion prompt
        self.expansion_prompt = ChatPromptTemplate.from_template("""
You are a PropTech domain expert. Expand the given query with relevant terms and variations.

QUERY: {query}
DOMAIN: {domain}

Generate 3-5 semantic variations of this query that would help find relevant PropTech information.
Focus on:
- Technical synonyms
- Alternative phrasings
- Related concepts
- Industry terminology

Return only the variations, one per line, without explanations.
""")
    
    def initialize(self) -> bool:
        """Initialize the query expander."""
        if self._initialized:
            return True
        
        try:
            # Use fast model for query expansion
            self.llm = OllamaLLM(
                model="llama3.2:1b",
                base_url=self.ollama_host,
                temperature=0.3  # Some creativity for variations
            )
            
            # Test connection
            test_response = self.llm.invoke("test")
            
            self._initialized = True
            logger.info("✅ PropTech Query Expander initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize query expander: {e}")
            return False
    
    def expand_query(
        self,
        query: str,
        domain: str = "general",
        strategy: ExpansionStrategy = ExpansionStrategy.HYBRID,
        max_expansions: int = 5
    ) -> ExpandedQuery:
        """
        Expand query using specified strategy.
        
        Args:
            query: Original user query
            domain: PropTech domain (energy, finance, valuation, etc.)
            strategy: Expansion strategy to use
            max_expansions: Maximum number of expansion terms
            
        Returns:
            ExpandedQuery with all expansion details
        """
        logger.debug(f"Expanding query: {query[:30]}... (domain: {domain})")
        
        # Normalize query
        normalized_query = self._normalize_query(query)
        
        # Apply expansion strategy
        if strategy == ExpansionStrategy.SYNONYM:
            expanded = self._synonym_expansion(normalized_query)
        elif strategy == ExpansionStrategy.SEMANTIC:
            expanded = self._semantic_expansion(normalized_query, domain)
        elif strategy == ExpansionStrategy.DOMAIN_SPECIFIC:
            expanded = self._domain_specific_expansion(normalized_query, domain)
        elif strategy == ExpansionStrategy.CONTEXTUAL:
            expanded = self._contextual_expansion(normalized_query, domain)
        else:  # HYBRID
            expanded = self._hybrid_expansion(normalized_query, domain)
        
        # Limit expansions
        expanded.expanded_terms = expanded.expanded_terms[:max_expansions]
        expanded.domain_synonyms = expanded.domain_synonyms[:max_expansions]
        expanded.semantic_variations = expanded.semantic_variations[:max_expansions]
        
        # Build final expanded query
        expanded.final_query = self._build_final_query(expanded)
        
        logger.debug(f"Query expanded: {len(expanded.expanded_terms)} terms added")
        return expanded
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query by expanding abbreviations and fixing common issues."""
        normalized = query.lower().strip()
        
        # Expand technical abbreviations
        for abbr, expansion in self.technical_abbreviations.items():
            # Match whole words only
            pattern = r'\b' + re.escape(abbr) + r'\b'
            normalized = re.sub(pattern, expansion, normalized, flags=re.IGNORECASE)
        
        # Fix common spacing issues
        normalized = re.sub(r'u-?value', 'u-value', normalized)
        normalized = re.sub(r'r-?value', 'r-value', normalized)
        normalized = re.sub(r'co2|co-2', 'carbon dioxide', normalized)
        
        return normalized
    
    def _synonym_expansion(self, query: str) -> ExpandedQuery:
        """Expand using domain synonym dictionary."""
        expanded_terms = []
        domain_synonyms = []
        
        query_lower = query.lower()
        
        # Find matching terms and their synonyms
        for term, synonyms in self.proptech_synonyms.items():
            if term in query_lower:
                domain_synonyms.extend(synonyms[:3])  # Top 3 synonyms
                expanded_terms.extend(synonyms[:2])   # Top 2 for expansion
        
        return ExpandedQuery(
            original_query=query,
            expanded_terms=list(set(expanded_terms)),
            domain_synonyms=list(set(domain_synonyms)),
            semantic_variations=[],
            final_query="",
            expansion_strategy=ExpansionStrategy.SYNONYM,
            confidence_score=0.8 if expanded_terms else 0.3
        )
    
    def _semantic_expansion(self, query: str, domain: str) -> ExpandedQuery:
        """Expand using LLM semantic understanding."""
        semantic_variations = []
        
        if not self._initialized:
            if not self.initialize():
                return self._fallback_expansion(query)
        
        try:
            prompt = self.expansion_prompt.format(query=query, domain=domain)
            response = self.llm.invoke(prompt)
            
            # Parse LLM response
            variations = [
                line.strip() 
                for line in response.split('\n') 
                if line.strip() and not line.startswith('#')
            ]
            
            semantic_variations = variations[:5]  # Top 5 variations
            
        except Exception as e:
            logger.warning(f"Semantic expansion failed: {e}")
            return self._fallback_expansion(query)
        
        return ExpandedQuery(
            original_query=query,
            expanded_terms=semantic_variations[:3],
            domain_synonyms=[],
            semantic_variations=semantic_variations,
            final_query="",
            expansion_strategy=ExpansionStrategy.SEMANTIC,
            confidence_score=0.9 if semantic_variations else 0.4
        )
    
    def _domain_specific_expansion(self, query: str, domain: str) -> ExpandedQuery:
        """Expand based on domain-specific patterns."""
        expanded_terms = []
        domain_synonyms = []
        
        # Detect query pattern
        query_type = self._detect_query_pattern(query)
        
        # Add domain-specific terms based on pattern
        if query_type == "cost_analysis":
            expanded_terms.extend([
                "budget", "expense", "investment", "financial analysis",
                "cost breakdown", "pricing"
            ])
        elif query_type == "roi_analysis":
            expanded_terms.extend([
                "return on investment", "payback period", "profit margin",
                "financial return", "investment yield"
            ])
        elif query_type == "energy_performance":
            expanded_terms.extend([
                "energy efficiency", "thermal performance", "energy rating",
                "consumption", "efficiency rating"
            ])
        elif query_type == "regulatory":
            expanded_terms.extend([
                "compliance", "standards", "regulations", "codes",
                "legal requirements"
            ])
        
        # Add domain-specific context
        if domain == "energy":
            domain_synonyms.extend([
                "thermal", "insulation", "efficiency", "consumption",
                "performance", "rating"
            ])
        elif domain == "finance":
            domain_synonyms.extend([
                "cost", "investment", "return", "profit", "budget", "value"
            ])
        elif domain == "valuation":
            domain_synonyms.extend([
                "appraisal", "assessment", "market value", "worth", "price"
            ])
        
        return ExpandedQuery(
            original_query=query,
            expanded_terms=list(set(expanded_terms)),
            domain_synonyms=list(set(domain_synonyms)),
            semantic_variations=[],
            final_query="",
            expansion_strategy=ExpansionStrategy.DOMAIN_SPECIFIC,
            confidence_score=0.7
        )
    
    def _contextual_expansion(self, query: str, domain: str) -> ExpandedQuery:
        """Expand based on contextual understanding."""
        # Combine synonym and domain-specific approaches
        synonym_result = self._synonym_expansion(query)
        domain_result = self._domain_specific_expansion(query, domain)
        
        # Merge results
        expanded_terms = list(set(
            synonym_result.expanded_terms + domain_result.expanded_terms
        ))
        domain_synonyms = list(set(
            synonym_result.domain_synonyms + domain_result.domain_synonyms
        ))
        
        return ExpandedQuery(
            original_query=query,
            expanded_terms=expanded_terms,
            domain_synonyms=domain_synonyms,
            semantic_variations=[],
            final_query="",
            expansion_strategy=ExpansionStrategy.CONTEXTUAL,
            confidence_score=(synonym_result.confidence_score + domain_result.confidence_score) / 2
        )
    
    def _hybrid_expansion(self, query: str, domain: str) -> ExpandedQuery:
        """Combine all expansion strategies for maximum coverage."""
        # Get results from all strategies
        synonym_result = self._synonym_expansion(query)
        semantic_result = self._semantic_expansion(query, domain)
        domain_result = self._domain_specific_expansion(query, domain)
        
        # Merge all results
        all_expanded = (
            synonym_result.expanded_terms + 
            semantic_result.expanded_terms + 
            domain_result.expanded_terms
        )
        
        all_synonyms = (
            synonym_result.domain_synonyms + 
            domain_result.domain_synonyms
        )
        
        # Remove duplicates and rank by relevance
        expanded_terms = list(set(all_expanded))
        domain_synonyms = list(set(all_synonyms))
        
        # Calculate confidence as weighted average
        confidence = (
            synonym_result.confidence_score * 0.3 +
            semantic_result.confidence_score * 0.4 +
            domain_result.confidence_score * 0.3
        )
        
        return ExpandedQuery(
            original_query=query,
            expanded_terms=expanded_terms,
            domain_synonyms=domain_synonyms,
            semantic_variations=semantic_result.semantic_variations,
            final_query="",
            expansion_strategy=ExpansionStrategy.HYBRID,
            confidence_score=confidence
        )
    
    def _detect_query_pattern(self, query: str) -> str:
        """Detect the type of query based on patterns."""
        query_lower = query.lower()
        
        for pattern_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return pattern_type
        
        return "general"
    
    def _build_final_query(self, expanded: ExpandedQuery) -> str:
        """Build the final expanded query string."""
        # Start with original query
        query_parts = [expanded.original_query]
        
        # Add most relevant expanded terms
        if expanded.expanded_terms:
            # Add top 3 expanded terms with OR logic
            top_terms = expanded.expanded_terms[:3]
            query_parts.extend(top_terms)
        
        # Join with OR logic for better retrieval
        final_query = " OR ".join(f'"{part}"' for part in query_parts)
        
        return final_query
    
    def _fallback_expansion(self, query: str) -> ExpandedQuery:
        """Fallback expansion when LLM is unavailable."""
        return ExpandedQuery(
            original_query=query,
            expanded_terms=[],
            domain_synonyms=[],
            semantic_variations=[],
            final_query=query,
            expansion_strategy=ExpansionStrategy.SYNONYM,
            confidence_score=0.2
        )
    
    def get_expansion_suggestions(self, query: str, domain: str = "general") -> List[str]:
        """Get expansion suggestions for UI display."""
        expanded = self.expand_query(query, domain, ExpansionStrategy.HYBRID)
        
        suggestions = []
        suggestions.extend(expanded.expanded_terms[:3])
        suggestions.extend(expanded.domain_synonyms[:2])
        
        return list(set(suggestions))[:5]
    
    def analyze_query_complexity(self, query: str) -> Dict:
        """Analyze query complexity for expansion strategy selection."""
        query_lower = query.lower()
        
        # Count technical terms
        technical_terms = sum(
            1 for term in self.proptech_synonyms.keys() 
            if term in query_lower
        )
        
        # Count abbreviations
        abbreviations = sum(
            1 for abbr in self.technical_abbreviations.keys()
            if abbr in query_lower
        )
        
        # Detect patterns
        patterns = [
            pattern_type for pattern_type, patterns in self.query_patterns.items()
            for pattern in patterns
            if re.search(pattern, query_lower)
        ]
        
        # Calculate complexity score
        complexity_score = (
            len(query.split()) * 0.1 +
            technical_terms * 0.3 +
            abbreviations * 0.2 +
            len(patterns) * 0.4
        )
        
        complexity_level = "simple"
        if complexity_score > 2.0:
            complexity_level = "complex"
        elif complexity_score > 1.0:
            complexity_level = "moderate"
        
        return {
            "complexity_level": complexity_level,
            "complexity_score": complexity_score,
            "technical_terms": technical_terms,
            "abbreviations": abbreviations,
            "detected_patterns": patterns,
            "recommended_strategy": (
                ExpansionStrategy.HYBRID if complexity_level == "complex"
                else ExpansionStrategy.CONTEXTUAL if complexity_level == "moderate"
                else ExpansionStrategy.SYNONYM
            )
        }


# Utility functions for integration
def expand_proptech_query(
    query: str,
    domain: str = "general",
    strategy: ExpansionStrategy = ExpansionStrategy.HYBRID
) -> str:
    """Convenience function for query expansion."""
    expander = PropTechQueryExpander()
    expander.initialize()
    
    expanded = expander.expand_query(query, domain, strategy)
    return expanded.final_query


def get_query_suggestions(query: str, domain: str = "general") -> List[str]:
    """Get expansion suggestions for autocomplete."""
    expander = PropTechQueryExpander()
    expander.initialize()
    
    return expander.get_expansion_suggestions(query, domain)
