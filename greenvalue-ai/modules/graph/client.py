"""
Neo4j Client — Connection & Query Manager
Author: Erdinc Erdogan
Purpose: Manage Neo4j driver lifecycle, execute Cypher queries, and provide
         a clean interface for the property knowledge graph.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("greenvalue-graph")


@dataclass
class Neo4jConfig:
    """Neo4j connection configuration."""
    uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user: str = os.getenv("NEO4J_USER", "neo4j")
    password: str = os.getenv("NEO4J_PASSWORD", "greenvalue_secret")
    database: str = os.getenv("NEO4J_DATABASE", "neo4j")
    max_connection_pool_size: int = 50
    connection_timeout: int = 30  # seconds
    encrypted: bool = False

    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        return cls(
            uri=os.getenv("NEO4J_URI", cls.uri),
            user=os.getenv("NEO4J_USER", cls.user),
            password=os.getenv("NEO4J_PASSWORD", cls.password),
            database=os.getenv("NEO4J_DATABASE", cls.database),
        )


class Neo4jClient:
    """
    Neo4j database client with connection pooling and query helpers.

    Usage:
        client = Neo4jClient()
        client.connect()
        result = client.query("MATCH (n) RETURN n LIMIT 5")
        client.close()

    Context manager:
        with Neo4jClient() as client:
            result = client.query("MATCH (n) RETURN n LIMIT 5")
    """

    def __init__(self, config: Optional[Neo4jConfig] = None):
        self.config = config or Neo4jConfig.from_env()
        self._driver = None
        self._connected = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self) -> bool:
        """Establish connection to Neo4j."""
        if self._connected:
            return True

        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.user, self.config.password),
                max_connection_pool_size=self.config.max_connection_pool_size,
                connection_timeout=self.config.connection_timeout,
                encrypted=self.config.encrypted,
            )

            # Verify connectivity
            self._driver.verify_connectivity()
            self._connected = True

            server_info = self._driver.get_server_info()
            logger.info(
                f"✅ Connected to Neo4j {server_info.agent} "
                f"at {self.config.uri}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self._connected = False
            return False

    def close(self):
        """Close the Neo4j driver."""
        if self._driver:
            self._driver.close()
            self._driver = None
            self._connected = False
            logger.info("Neo4j connection closed")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def query(
        self,
        cypher: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict]:
        """
        Execute a Cypher query and return results as a list of dicts.

        Args:
            cypher: Cypher query string
            parameters: Query parameters
            database: Optional database name override

        Returns:
            List of result records as dicts
        """
        if not self._connected:
            self.connect()

        db = database or self.config.database

        try:
            with self._driver.session(database=db) as session:
                result = session.run(cypher, parameters or {})
                records = [dict(record) for record in result]
                return records
        except Exception as e:
            logger.error(f"Cypher query failed: {e}\nQuery: {cypher[:200]}")
            raise

    def write(
        self,
        cypher: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Dict:
        """
        Execute a Cypher write query in a transaction.

        Args:
            cypher: Cypher write query
            parameters: Query parameters
            database: Optional database name override

        Returns:
            Summary dict with counters
        """
        if not self._connected:
            self.connect()

        db = database or self.config.database

        try:
            with self._driver.session(database=db) as session:

                def _tx(tx):
                    result = tx.run(cypher, parameters or {})
                    summary = result.consume()
                    return {
                        "nodes_created": summary.counters.nodes_created,
                        "nodes_deleted": summary.counters.nodes_deleted,
                        "relationships_created": summary.counters.relationships_created,
                        "relationships_deleted": summary.counters.relationships_deleted,
                        "properties_set": summary.counters.properties_set,
                    }

                return session.execute_write(_tx)

        except Exception as e:
            logger.error(f"Cypher write failed: {e}\nQuery: {cypher[:200]}")
            raise

    def write_batch(
        self,
        queries: List[Dict[str, Any]],
        database: Optional[str] = None,
    ) -> Dict:
        """
        Execute multiple Cypher queries in a single transaction.

        Args:
            queries: List of {"cypher": str, "parameters": dict}
            database: Optional database name

        Returns:
            Aggregated summary
        """
        if not self._connected:
            self.connect()

        db = database or self.config.database
        total_summary = {
            "nodes_created": 0,
            "relationships_created": 0,
            "properties_set": 0,
            "queries_executed": 0,
        }

        try:
            with self._driver.session(database=db) as session:

                def _tx(tx):
                    for q in queries:
                        tx.run(q["cypher"], q.get("parameters", {}))

                session.execute_write(_tx)
                total_summary["queries_executed"] = len(queries)

            return total_summary

        except Exception as e:
            logger.error(f"Batch write failed: {e}")
            raise

    def health_check(self) -> Dict:
        """Check Neo4j health and return server info."""
        try:
            if not self._connected:
                self.connect()

            info = self._driver.get_server_info()
            # Count nodes and relationships
            stats = self.query(
                "MATCH (n) RETURN count(n) as nodes "
                "UNION ALL "
                "MATCH ()-[r]->() RETURN count(r) as nodes"
            )

            node_count = stats[0].get("nodes", 0) if stats else 0
            rel_count = stats[1].get("nodes", 0) if len(stats) > 1 else 0

            return {
                "status": "healthy",
                "server": info.agent,
                "address": str(info.address),
                "protocol_version": str(info.protocol_version),
                "database": self.config.database,
                "node_count": node_count,
                "relationship_count": rel_count,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
