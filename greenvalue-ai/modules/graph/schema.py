"""
Neo4j Graph Schema — Constraints, Indexes, and Initialization
Author: GreenValue AI Team
Purpose: Define and enforce the property knowledge graph schema.

Node Types:
  - Property        : A real estate property
  - BuildingComponent : A physical component (window, roof, facade, etc.)
  - Material        : Construction material (brick, glass wool, EPS, etc.)
  - EnergyLabel     : Energy efficiency label (A+, A, B, ..., G)
  - Renovation      : A renovation/retrofit action
  - Document        : An ingested knowledge-base document
  - Concept         : A domain concept (insulation, energy_efficiency, etc.)
  - Regulation      : Building regulation or standard

Relationship Types:
  - HAS_COMPONENT      : Property → BuildingComponent
  - MADE_OF            : BuildingComponent → Material
  - HAS_ENERGY_LABEL   : Property → EnergyLabel
  - NEEDS_RENOVATION   : BuildingComponent → Renovation
  - IMPROVES           : Renovation → BuildingComponent
  - AFFECTS            : Concept → Concept  (cause-effect)
  - INCREASES          : Concept → Concept  (positive impact)
  - DECREASES          : Concept → Concept  (negative impact)
  - REFERENCES         : Document → Concept
  - COMPLIES_WITH      : Property → Regulation
  - SIMILAR_TO         : Property → Property (embedding similarity)
"""

import logging
from typing import Dict, List

from .client import Neo4jClient

logger = logging.getLogger("greenvalue-graph")


class GraphSchema:
    """
    Manages the Neo4j graph schema: constraints, indexes, and seed data.
    """

    # Node label constraints (unique properties)
    CONSTRAINTS = [
        ("Property", "property_id"),
        ("BuildingComponent", "component_id"),
        ("Material", "name"),
        ("EnergyLabel", "label"),
        ("Renovation", "renovation_id"),
        ("Document", "document_id"),
        ("Concept", "name"),
        ("Regulation", "code"),
    ]

    # Full-text search indexes
    FULLTEXT_INDEXES = [
        {
            "name": "property_search",
            "labels": ["Property"],
            "properties": ["title", "address", "city"],
        },
        {
            "name": "document_search",
            "labels": ["Document"],
            "properties": ["title", "content_preview"],
        },
        {
            "name": "concept_search",
            "labels": ["Concept"],
            "properties": ["name", "description"],
        },
    ]

    # Seed data: core PropTech concepts and relationships
    SEED_CONCEPTS = [
        # Energy efficiency chain
        ("good_insulation", "Building with high-quality insulation materials"),
        ("poor_insulation", "Building with degraded or missing insulation"),
        ("energy_efficiency", "Overall energy performance of a building"),
        ("energy_costs", "Annual energy expenditure for heating/cooling"),
        ("property_value", "Market value of the property"),
        ("comfort", "Indoor thermal comfort level"),
        ("heating_demand", "Annual heating energy requirement (kWh/m²)"),
        ("cooling_demand", "Annual cooling energy requirement (kWh/m²)"),
        ("carbon_footprint", "CO₂ emissions from building operations"),
        ("marketability", "Ease of selling/renting the property"),

        # Components
        ("windows", "Window systems and glazing"),
        ("facade", "External wall system"),
        ("roof", "Roof structure and insulation"),
        ("hvac_system", "Heating, ventilation, and air conditioning"),
        ("solar_panels", "Photovoltaic or thermal solar installations"),

        # Certifications
        ("leed_certification", "LEED green building certification"),
        ("breeam_certification", "BREEAM sustainability assessment"),
        ("energy_label_a", "Energy performance certificate: A class"),
        ("energy_label_g", "Energy performance certificate: G class"),

        # Financial
        ("renovation_cost", "Total cost of renovation works"),
        ("payback_period", "Time to recoup renovation investment"),
        ("roi", "Return on investment from improvements"),
        ("government_subsidies", "Available grants and tax incentives"),
    ]

    SEED_RELATIONSHIPS = [
        # Insulation impacts
        ("good_insulation", "INCREASES", "energy_efficiency", 0.9),
        ("good_insulation", "DECREASES", "heating_demand", 0.85),
        ("good_insulation", "DECREASES", "energy_costs", 0.8),
        ("good_insulation", "INCREASES", "comfort", 0.75),
        ("good_insulation", "INCREASES", "property_value", 0.7),
        ("poor_insulation", "DECREASES", "energy_efficiency", 0.85),
        ("poor_insulation", "INCREASES", "heating_demand", 0.8),
        ("poor_insulation", "INCREASES", "energy_costs", 0.8),

        # Energy efficiency chain
        ("energy_efficiency", "INCREASES", "property_value", 0.8),
        ("energy_efficiency", "DECREASES", "energy_costs", 0.85),
        ("energy_efficiency", "DECREASES", "carbon_footprint", 0.75),
        ("energy_efficiency", "INCREASES", "marketability", 0.7),

        # Component impacts
        ("windows", "AFFECTS", "energy_efficiency", 0.7),
        ("windows", "AFFECTS", "comfort", 0.6),
        ("facade", "AFFECTS", "energy_efficiency", 0.8),
        ("roof", "AFFECTS", "energy_efficiency", 0.75),
        ("hvac_system", "AFFECTS", "energy_costs", 0.85),
        ("hvac_system", "AFFECTS", "comfort", 0.8),

        # Solar impacts
        ("solar_panels", "DECREASES", "energy_costs", 0.7),
        ("solar_panels", "DECREASES", "carbon_footprint", 0.6),
        ("solar_panels", "INCREASES", "property_value", 0.5),

        # Certification impacts
        ("leed_certification", "INCREASES", "property_value", 0.75),
        ("leed_certification", "INCREASES", "marketability", 0.8),
        ("breeam_certification", "INCREASES", "property_value", 0.7),
        ("energy_label_a", "INCREASES", "property_value", 0.65),
        ("energy_label_a", "INCREASES", "marketability", 0.7),
        ("energy_label_g", "DECREASES", "property_value", 0.5),
        ("energy_label_g", "DECREASES", "marketability", 0.6),

        # Financial chain
        ("renovation_cost", "AFFECTS", "payback_period", 0.9),
        ("energy_costs", "AFFECTS", "payback_period", 0.85),
        ("government_subsidies", "DECREASES", "renovation_cost", 0.6),
        ("government_subsidies", "DECREASES", "payback_period", 0.5),
        ("roi", "INCREASES", "marketability", 0.5),
    ]

    # Material thermal properties for the graph
    SEED_MATERIALS = [
        ("EPS Insulation", 0.035, "Expanded Polystyrene foam board"),
        ("XPS Insulation", 0.030, "Extruded Polystyrene foam"),
        ("Glass Wool", 0.040, "Mineral glass fiber insulation"),
        ("Rock Wool", 0.038, "Stone mineral fiber insulation"),
        ("Polyurethane Foam", 0.025, "PUR/PIR spray or board insulation"),
        ("Cellulose", 0.040, "Recycled cellulose fiber insulation"),
        ("Brick", 0.800, "Standard clay brick"),
        ("Concrete", 1.400, "Reinforced concrete"),
        ("Timber", 0.130, "Structural timber"),
        ("Double Glazing", 1.100, "Standard double-pane window"),
        ("Triple Glazing", 0.700, "High-performance triple-pane window"),
        ("Steel", 50.0, "Structural steel"),
        ("Aerogel", 0.015, "Ultra-high-performance aerogel insulation"),
    ]

    def __init__(self, client: Neo4jClient):
        self.client = client

    def initialize(self, force_reset: bool = False) -> Dict:
        """
        Initialize the complete graph schema.

        Args:
            force_reset: If True, delete all data and recreate

        Returns:
            Summary of initialization
        """
        result = {
            "constraints_created": 0,
            "indexes_created": 0,
            "concepts_seeded": 0,
            "relationships_seeded": 0,
            "materials_seeded": 0,
        }

        try:
            if force_reset:
                logger.warning("🗑️ Resetting Neo4j graph database...")
                self.client.write("MATCH (n) DETACH DELETE n")

            # Create constraints
            for label, prop in self.CONSTRAINTS:
                try:
                    self.client.write(
                        f"CREATE CONSTRAINT IF NOT EXISTS "
                        f"FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
                    )
                    result["constraints_created"] += 1
                except Exception as e:
                    logger.debug(f"Constraint {label}.{prop}: {e}")

            # Create fulltext indexes
            for idx in self.FULLTEXT_INDEXES:
                try:
                    labels = "|".join(idx["labels"])
                    props = ", ".join(f"n.{p}" for p in idx["properties"])
                    self.client.write(
                        f'CREATE FULLTEXT INDEX {idx["name"]} IF NOT EXISTS '
                        f"FOR (n:{labels}) ON EACH [{props}]"
                    )
                    result["indexes_created"] += 1
                except Exception as e:
                    logger.debug(f"Index {idx['name']}: {e}")

            # Seed concepts
            for name, description in self.SEED_CONCEPTS:
                self.client.write(
                    "MERGE (c:Concept {name: $name}) "
                    "SET c.description = $description, c.updated_at = datetime()",
                    {"name": name, "description": description},
                )
                result["concepts_seeded"] += 1

            # Seed relationships
            for source, rel_type, target, weight in self.SEED_RELATIONSHIPS:
                self.client.write(
                    f"MATCH (a:Concept {{name: $source}}) "
                    f"MATCH (b:Concept {{name: $target}}) "
                    f"MERGE (a)-[r:{rel_type}]->(b) "
                    f"SET r.weight = $weight, r.updated_at = datetime()",
                    {"source": source, "target": target, "weight": weight},
                )
                result["relationships_seeded"] += 1

            # Seed materials
            for name, conductivity, description in self.SEED_MATERIALS:
                self.client.write(
                    "MERGE (m:Material {name: $name}) "
                    "SET m.thermal_conductivity = $conductivity, "
                    "    m.description = $description, "
                    "    m.unit = 'W/mK', "
                    "    m.updated_at = datetime()",
                    {
                        "name": name,
                        "conductivity": conductivity,
                        "description": description,
                    },
                )
                result["materials_seeded"] += 1

            logger.info(
                f"✅ Neo4j schema initialized: "
                f"{result['constraints_created']} constraints, "
                f"{result['indexes_created']} indexes, "
                f"{result['concepts_seeded']} concepts, "
                f"{result['relationships_seeded']} relationships, "
                f"{result['materials_seeded']} materials"
            )
            return result

        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            raise
