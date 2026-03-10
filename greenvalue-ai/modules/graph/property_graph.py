"""
Property Knowledge Graph — Neo4j-Backed Domain Graph
Author: GreenValue AI Team
Purpose: Store and query property relationships, economic cause-effect chains,
         renovation impacts, and document-concept links in Neo4j.

Replaces the in-memory KnowledgeGraph/PropertyGraph with a persistent,
queryable graph database for production use.
"""

import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document

from .client import Neo4jClient, Neo4jConfig
from .schema import GraphSchema

logger = logging.getLogger("greenvalue-graph")


class PropertyKnowledgeGraph:
    """
    Neo4j-backed property knowledge graph for GreenValue AI.

    Provides:
        - Property ↔ Component ↔ Material relationships
        - Economic cause-effect chains (insulation → energy_efficiency → value)
        - Renovation impact analysis with ripple effects
        - Document ↔ Concept links for RAG graph retrieval
        - Similar property discovery via graph traversal
    """

    def __init__(self, config: Optional[Neo4jConfig] = None):
        self.config = config or Neo4jConfig.from_env()
        self.client = Neo4jClient(self.config)
        self.schema = GraphSchema(self.client)
        self._initialized = False

    def initialize(self, seed: bool = True) -> bool:
        """Connect to Neo4j and initialize schema."""
        if self._initialized:
            return True

        try:
            if not self.client.connect():
                logger.error("Cannot connect to Neo4j")
                return False

            if seed:
                self.schema.initialize()

            self._initialized = True
            logger.info("✅ PropertyKnowledgeGraph initialized")
            return True

        except Exception as e:
            logger.error(f"PropertyKnowledgeGraph init failed: {e}", exc_info=True)
            return False

    def close(self):
        """Close Neo4j connection."""
        self.client.close()
        self._initialized = False

    # ── Property Operations ───────────────────────────────────

    def upsert_property(
        self,
        property_id: str,
        title: str,
        address: str,
        city: str = "",
        building_year: int = 0,
        building_type: str = "",
        floor_area: float = 0.0,
        energy_label: str = "",
        overall_u_value: float = 0.0,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Create or update a property node."""
        params = {
            "property_id": property_id,
            "title": title,
            "address": address,
            "city": city,
            "building_year": building_year,
            "building_type": building_type,
            "floor_area": floor_area,
            "energy_label": energy_label,
            "overall_u_value": overall_u_value,
            "metadata": metadata or {},
        }

        result = self.client.write(
            """
            MERGE (p:Property {property_id: $property_id})
            SET p.title = $title,
                p.address = $address,
                p.city = $city,
                p.building_year = $building_year,
                p.building_type = $building_type,
                p.floor_area = $floor_area,
                p.overall_u_value = $overall_u_value,
                p.updated_at = datetime()
            WITH p
            FOREACH (_ IN CASE WHEN $energy_label <> '' THEN [1] ELSE [] END |
                MERGE (e:EnergyLabel {label: $energy_label})
                MERGE (p)-[:HAS_ENERGY_LABEL]->(e)
            )
            RETURN p.property_id as id
            """,
            params,
        )

        logger.info(f"Property upserted: {property_id}")
        return result

    def add_component(
        self,
        property_id: str,
        component_type: str,
        condition: str = "unknown",
        u_value: float = 0.0,
        area: float = 0.0,
        material: str = "",
        confidence: float = 0.0,
    ) -> Dict:
        """Add a building component (from YOLO detection) to a property."""
        component_id = f"{property_id}_{component_type}_{uuid.uuid4().hex[:8]}"

        result = self.client.write(
            """
            MATCH (p:Property {property_id: $property_id})
            CREATE (c:BuildingComponent {
                component_id: $component_id,
                type: $component_type,
                condition: $condition,
                u_value: $u_value,
                area: $area,
                confidence: $confidence,
                detected_at: datetime()
            })
            CREATE (p)-[:HAS_COMPONENT]->(c)
            WITH c
            FOREACH (_ IN CASE WHEN $material <> '' THEN [1] ELSE [] END |
                MERGE (m:Material {name: $material})
                MERGE (c)-[:MADE_OF]->(m)
            )
            RETURN c.component_id as id
            """,
            {
                "property_id": property_id,
                "component_id": component_id,
                "component_type": component_type,
                "condition": condition,
                "u_value": u_value,
                "area": area,
                "material": material,
                "confidence": confidence,
            },
        )

        return result

    def add_analysis_results(
        self,
        property_id: str,
        detections: List[Dict],
        overall_u_value: float = 0.0,
        energy_label: str = "",
    ) -> Dict:
        """
        Store a complete YOLO + physics analysis in the graph.

        Args:
            property_id: Property UUID
            detections: List of detection dicts from the pipeline
            overall_u_value: Calculated overall U-value
            energy_label: Assigned energy label (A-G)
        """
        # Update property
        self.client.write(
            """
            MATCH (p:Property {property_id: $property_id})
            SET p.overall_u_value = $u_value,
                p.last_analysis = datetime()
            WITH p
            FOREACH (_ IN CASE WHEN $label <> '' THEN [1] ELSE [] END |
                MERGE (e:EnergyLabel {label: $label})
                MERGE (p)-[:HAS_ENERGY_LABEL]->(e)
            )
            """,
            {"property_id": property_id, "u_value": overall_u_value, "label": energy_label},
        )

        # Add each detected component
        for det in detections:
            self.add_component(
                property_id=property_id,
                component_type=det.get("class", "unknown"),
                condition=det.get("condition", "unknown"),
                u_value=det.get("u_value", 0.0),
                area=det.get("area", 0.0),
                confidence=det.get("confidence", 0.0),
            )

        # Link to renovation concepts if components are in poor/critical condition
        for det in detections:
            if det.get("condition") in ("poor", "critical"):
                comp_type = det.get("class", "unknown")
                self.client.write(
                    """
                    MATCH (p:Property {property_id: $property_id})
                    MATCH (p)-[:HAS_COMPONENT]->(c:BuildingComponent {type: $comp_type})
                    WHERE c.condition IN ['poor', 'critical']
                    WITH c, $comp_type as ct
                    MERGE (r:Renovation {
                        renovation_id: ct + '_upgrade',
                        name: ct + ' upgrade',
                        type: ct
                    })
                    MERGE (c)-[:NEEDS_RENOVATION]->(r)
                    MERGE (r)-[:IMPROVES]->(c)
                    """,
                    {"property_id": property_id, "comp_type": comp_type},
                )

        return {
            "property_id": property_id,
            "components_added": len(detections),
            "energy_label": energy_label,
        }

    # ── Graph Retrieval for RAG ───────────────────────────────

    def get_graph_context(self, query: str) -> str:
        """
        Extract relevant graph context for a RAG query.
        Replaces the in-memory KnowledgeGraph.get_graph_context().

        Finds matching concepts and traverses 1-2 hops to discover
        related cause-effect chains.
        """
        if not self._initialized:
            return ""

        try:
            # Search concepts matching query terms (strip punctuation + stop words)
            _stop = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all',
                     'can', 'had', 'her', 'was', 'one', 'our', 'out', 'has',
                     'have', 'been', 'from', 'this', 'that', 'with', 'what',
                     'how', 'why', 'when', 'where', 'which', 'does', 'will',
                     'about', 'would', 'could', 'should', 'their', 'there'}
            words = [w for w in re.findall(r'\w+', query.lower())
                     if len(w) > 2 and w not in _stop][:10]
            logger.debug(f"Graph context words: {words}")

            results = self.client.query(
                """
                MATCH (c:Concept)
                WHERE ANY(word IN $words WHERE c.name CONTAINS word)
                OPTIONAL MATCH (c)-[r]-(t)
                WHERE t:Concept OR t:Material
                RETURN c.name as source, type(r) as relation,
                       t.name as target, r.weight as weight
                LIMIT 30
                """,
                {"words": words},
            )

            if not results:
                # Try fulltext search
                results = self.client.query(
                    """
                    CALL db.index.fulltext.queryNodes('concept_search', $query)
                    YIELD node, score
                    WITH node as c
                    OPTIONAL MATCH (c)-[r]-(t)
                    WHERE t:Concept OR t:Material
                    RETURN c.name as source, type(r) as relation,
                           t.name as target, r.weight as weight
                    LIMIT 30
                    """,
                    {"query": query},
                )

            if not results:
                logger.debug(f"No graph context for words: {words}")
                return ""

            # Format context
            ctx_lines = ["\n🕸️ PROPERTY RELATIONSHIPS (Neo4j):"]
            seen = set()

            for rec in results:
                source = rec.get("source", "")
                relation = rec.get("relation", "")
                target = rec.get("target", "")
                weight = rec.get("weight", 0.0)

                if not target or not relation:
                    continue

                key = (source, relation, target)
                if key in seen:
                    continue
                seen.add(key)

                source_fmt = source.replace("_", " ").title()
                target_fmt = target.replace("_", " ").title()
                conf = int(weight * 100) if weight else 0
                ctx_lines.append(
                    f"  • {source_fmt} → {relation.lower()} → {target_fmt} ({conf}%)"
                )

            return "\n".join(ctx_lines) + "\n" if len(ctx_lines) > 1 else ""

        except Exception as e:
            logger.warning(f"Graph context retrieval failed: {e}")
            return ""

    def get_ripple_effects(self, improvement: str) -> str:
        """
        Analyze ripple effects of a property improvement using graph traversal.

        Traverses 1-3 hops from the improvement concept to find all
        downstream impacts.
        """
        if not self._initialized:
            return ""

        try:
            # Split improvement into words for flexible matching
            # e.g. "insulation_upgrade" -> ["insulation", "upgrade"]
            words = [w for w in improvement.lower().replace("_", " ").replace("-", " ").split() if len(w) > 2]
            if not words:
                words = [improvement.lower()]

            results = self.client.query(
                """
                MATCH (start:Concept)
                WHERE start.name CONTAINS $improvement
                   OR start.description CONTAINS $improvement
                   OR ANY(word IN $words WHERE start.name CONTAINS word)
                MATCH path = (start)-[*1..3]->(end:Concept)
                UNWIND relationships(path) as r
                WITH startNode(r) as s, type(r) as rel, endNode(r) as t, r.weight as w
                RETURN DISTINCT s.name as source, rel as relation,
                       t.name as target, w as weight
                ORDER BY w DESC
                LIMIT 15
                """,
                {"improvement": improvement.lower(), "words": words},
            )

            if not results:
                return ""

            lines = ["\n📊 PREDICTED RIPPLE EFFECTS (Neo4j graph):"]
            for rec in results:
                source = rec["source"].replace("_", " ").title()
                target = rec["target"].replace("_", " ").title()
                relation = rec["relation"].lower()
                weight = rec.get("weight", 0.0)

                direction = "📈" if relation in ("increases", "improves") else "📉"
                lines.append(
                    f"  {direction} {source} → {relation} → {target} ({int(weight * 100)}%)"
                )

            return "\n".join(lines) + "\n"

        except Exception as e:
            logger.warning(f"Ripple effect analysis failed: {e}")
            return ""

    def get_related_factors(self, component: str) -> str:
        """Get factors related to a building component from the graph."""
        if not self._initialized:
            return ""

        try:
            results = self.client.query(
                """
                MATCH (c:Concept)
                WHERE c.name CONTAINS $component
                MATCH (c)-[r]-(related:Concept)
                RETURN related.name as factor, type(r) as relation
                LIMIT 10
                """,
                {"component": component.lower()},
            )

            if not results:
                return ""

            factors = [r["factor"].replace("_", " ").title() for r in results]
            return f"\n🔗 Related factors for {component}: {', '.join(factors)}\n"

        except Exception as e:
            logger.warning(f"Related factors query failed: {e}")
            return ""

    # ── Document-Concept Linking ──────────────────────────────

    def link_document_to_concepts(
        self,
        document_id: str,
        title: str,
        category: str,
        concepts: List[str],
        content_preview: str = "",
    ) -> Dict:
        """
        Link an ingested document to relevant concepts in the graph.

        Used during RAG ingestion to build document-concept relationships
        for graph-enhanced retrieval.
        """
        # Create document node
        self.client.write(
            """
            MERGE (d:Document {document_id: $doc_id})
            SET d.title = $title,
                d.category = $category,
                d.content_preview = $preview,
                d.ingested_at = datetime()
            """,
            {
                "doc_id": document_id,
                "title": title,
                "category": category,
                "preview": content_preview[:500],
            },
        )

        # Link to concepts
        for concept_name in concepts:
            self.client.write(
                """
                MATCH (d:Document {document_id: $doc_id})
                MERGE (c:Concept {name: $concept})
                MERGE (d)-[:REFERENCES]->(c)
                """,
                {"doc_id": document_id, "concept": concept_name.lower()},
            )

        return {"document_id": document_id, "concepts_linked": len(concepts)}

    def find_documents_for_query(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Find relevant documents using graph traversal.
        Useful for graph-enhanced RAG retrieval.
        """
        if not self._initialized:
            return []

        try:
            results = self.client.query(
                """
                CALL db.index.fulltext.queryNodes('concept_search', $query)
                YIELD node, score
                WITH node as concept, score
                MATCH (d:Document)-[:REFERENCES]->(concept)
                RETURN DISTINCT d.document_id as document_id,
                       d.title as title,
                       d.category as category,
                       collect(concept.name) as matching_concepts,
                       max(score) as relevance
                ORDER BY relevance DESC
                LIMIT $limit
                """,
                {"query": query, "limit": limit},
            )
            return results

        except Exception as e:
            logger.warning(f"Document graph search failed: {e}")
            return []

    # ── Similar Properties ────────────────────────────────────

    def find_similar_properties(
        self,
        property_id: str,
        limit: int = 5,
    ) -> List[Dict]:
        """
        Find properties similar to a given property based on shared
        graph characteristics (same energy label, similar components,
        same city, etc.).
        """
        if not self._initialized:
            return []

        try:
            results = self.client.query(
                """
                MATCH (p:Property {property_id: $property_id})
                OPTIONAL MATCH (p)-[:HAS_ENERGY_LABEL]->(e:EnergyLabel)
                OPTIONAL MATCH (p)-[:HAS_COMPONENT]->(c:BuildingComponent)
                WITH p, e, collect(c.type) as comp_types

                // Find properties with same energy label
                OPTIONAL MATCH (similar:Property)-[:HAS_ENERGY_LABEL]->(e)
                WHERE similar.property_id <> $property_id

                // Calculate similarity score
                OPTIONAL MATCH (similar)-[:HAS_COMPONENT]->(sc:BuildingComponent)
                WHERE sc.type IN comp_types
                WITH similar, count(sc) as shared_components,
                     CASE WHEN e IS NOT NULL THEN 1 ELSE 0 END as shared_label,
                     CASE WHEN similar.city = p.city THEN 1 ELSE 0 END as same_city
                WHERE similar IS NOT NULL

                RETURN similar.property_id as property_id,
                       similar.title as title,
                       similar.city as city,
                       similar.overall_u_value as u_value,
                       shared_components + shared_label + same_city as similarity_score
                ORDER BY similarity_score DESC
                LIMIT $limit
                """,
                {"property_id": property_id, "limit": limit},
            )
            return results

        except Exception as e:
            logger.warning(f"Similar properties query failed: {e}")
            return []

    # ── Statistics ────────────────────────────────────────────

    def get_stats(self) -> Dict:
        """Get graph database statistics."""
        if not self._initialized:
            return {"status": "not_initialized"}

        try:
            counts = self.client.query(
                """
                CALL { MATCH (p:Property) RETURN count(p) AS properties }
                CALL { MATCH (c:BuildingComponent) RETURN count(c) AS components }
                CALL { MATCH (m:Material) RETURN count(m) AS materials }
                CALL { MATCH (con:Concept) RETURN count(con) AS concepts }
                CALL { MATCH (d:Document) RETURN count(d) AS documents }
                CALL { MATCH ()-[r]->() RETURN count(r) AS relationships }
                RETURN properties, components, materials, concepts, documents, relationships
                """
            )

            if counts:
                return {
                    "status": "connected",
                    **counts[0],
                }
            return {"status": "connected", "empty": True}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def health_check(self) -> Dict:
        """Health check for the graph database."""
        return self.client.health_check()
