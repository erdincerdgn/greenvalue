"""
Knowledge Graph for Real Estate Domain
Author: GreenValue AI Team
Purpose: Model relationships between property factors, sustainability, and value.
"""

import logging
import re
from typing import Dict, List, Tuple

from langchain_core.documents import Document

logger = logging.getLogger("greenvalue-rag")


class KnowledgeGraph:
    """
    Knowledge graph for real estate economic relationships.
    Models cause-effect relationships for property valuation.
    """
    
    # Relation weights: (source, relation, target) -> confidence
    RELATIONS = {
        # Energy efficiency impacts
        ("good_insulation", "increases", "energy_efficiency"): 0.9,
        ("energy_efficiency", "increases", "property_value"): 0.8,
        ("solar_panels", "reduces", "energy_costs"): 0.85,
        ("old_windows", "decreases", "energy_efficiency"): 0.7,
        
        # Sustainability impacts
        ("leed_certification", "increases", "property_value"): 0.75,
        ("green_building", "attracts", "eco_buyers"): 0.8,
        ("carbon_neutral", "increases", "marketability"): 0.7,
        
        # Market factors
        ("location", "affects", "property_value"): 0.95,
        ("renovation", "increases", "property_value"): 0.7,
        ("building_age", "affects", "maintenance_costs"): 0.8,
        
        # Energy labels
        ("energy_label_a", "indicates", "high_efficiency"): 0.9,
        ("energy_label_g", "indicates", "low_efficiency"): 0.9,
        ("high_u_value", "indicates", "poor_insulation"): 0.85,
    }
    
    # Concept mapping for query parsing
    CONCEPT_MAPPING = {
        "insulation": "good_insulation",
        "solar": "solar_panels",
        "windows": "old_windows",
        "leed": "leed_certification",
        "green": "green_building",
        "carbon": "carbon_neutral",
        "location": "location",
        "renovation": "renovation",
        "age": "building_age",
        "u-value": "high_u_value",
        "energy label": "energy_label_a",
    }
    
    @classmethod
    def get_graph_context(cls, query: str) -> str:
        """
        Extract relevant graph context from query.
        
        Returns formatted string with economic relationships.
        """
        q = query.lower()
        
        # Find matching concepts
        found_concepts = [
            concept for keyword, concept in cls.CONCEPT_MAPPING.items()
            if keyword in q
        ]
        
        if not found_concepts:
            return ""
        
        # Find relevant relations
        relations = [
            (source, rel, target, conf)
            for (source, rel, target), conf in cls.RELATIONS.items()
            if source in found_concepts or target in found_concepts
        ]
        
        if not relations:
            return ""
        
        # Format output
        ctx = "\n🕸️ PROPERTY RELATIONSHIPS:\n"
        for source, rel, target, conf in relations:
            source_fmt = source.replace("_", " ").title()
            target_fmt = target.replace("_", " ").title()
            ctx += f"  • {source_fmt} → {rel} → {target_fmt} ({int(conf*100)}%)\n"
        
        return ctx


class PropertyGraph:
    """
    Property-specific graph for ripple effect analysis.
    Models how changes in one factor affect related factors.
    """
    
    # Property factors and their related factors
    FACTOR_RELATIONS = {
        "insulation": ["u_value", "heating_costs", "comfort", "energy_label"],
        "windows": ["u_value", "natural_light", "noise", "heating_costs"],
        "roof": ["insulation", "solar_potential", "leaks", "value"],
        "hvac": ["energy_costs", "comfort", "maintenance", "air_quality"],
        "solar": ["energy_costs", "carbon_footprint", "value", "independence"],
    }
    
    # Ripple effects of improvements
    RIPPLE_EFFECTS = {
        "insulation_upgrade": {
            "u_value": -0.3,          # Lower U-value (better)
            "heating_costs": -0.25,   # Lower costs
            "property_value": 0.05,   # Slight increase
            "energy_label": 0.15,     # Better label
        },
        "solar_installation": {
            "energy_costs": -0.4,
            "carbon_footprint": -0.5,
            "property_value": 0.08,
            "independence": 0.6,
        },
        "window_replacement": {
            "u_value": -0.2,
            "heating_costs": -0.15,
            "comfort": 0.3,
            "noise_reduction": 0.4,
        },
        "energy_label_improvement": {
            "property_value": 0.1,
            "marketability": 0.2,
            "buyer_interest": 0.25,
        },
    }
    
    def __init__(self, llm=None):
        self.llm = llm
        self.extracted_relations = {}
    
    def extract_relations_from_doc(self, doc: Document) -> List[Tuple[str, str, str]]:
        """Extract causal relations from document text."""
        relations = []
        content = doc.page_content.lower()
        
        patterns = [
            (r"(\w+) increases? (\w+)", "increases"),
            (r"(\w+) decreases? (\w+)", "decreases"),
            (r"(\w+) affects? (\w+)", "affects"),
            (r"(\w+) leads? to (\w+)", "leads_to"),
            (r"(\w+) improves? (\w+)", "improves"),
            (r"(\w+) reduces? (\w+)", "reduces"),
        ]
        
        for pattern, relation in patterns:
            matches = re.findall(pattern, content)
            for source, target in matches[:5]:  # Limit matches
                relations.append((source, relation, target))
        
        return relations
    
    def get_ripple_effects(self, improvement: str) -> str:
        """
        Get ripple effects for a property improvement.
        
        Args:
            improvement: Type of improvement (e.g., "insulation_upgrade")
            
        Returns:
            Formatted string with predicted effects
        """
        improvement_key = improvement.lower().replace(" ", "_")
        
        # Try to match improvement
        effects = None
        for key, impacts in self.RIPPLE_EFFECTS.items():
            if improvement_key in key or key in improvement_key:
                effects = impacts
                break
        
        if not effects:
            return ""
        
        lines = ["\n📊 PREDICTED EFFECTS:"]
        for factor, change in effects.items():
            direction = "📈" if change > 0 else "📉"
            factor_fmt = factor.replace("_", " ").title()
            lines.append(f"  {direction} {factor_fmt}: {change:+.0%}")
        
        return "\n".join(lines) + "\n"
    
    def get_related_factors(self, component: str) -> str:
        """Get factors related to a building component."""
        component_key = component.lower()
        
        for key, factors in self.FACTOR_RELATIONS.items():
            if key in component_key or component_key in key:
                factors_fmt = ", ".join(f.replace("_", " ").title() for f in factors)
                return f"\n🔗 Related factors for {component}: {factors_fmt}\n"
        
        return ""
