# ============================================================
# GreenValue AI — Qdrant Collection Initialization
# Creates the property_embeddings collection for
# "Homes Like This" similarity search
# ============================================================

import asyncio
import logging
import sys

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PayloadSchemaType,
    TextIndexParams,
    TokenizerType,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qdrant-init")

# Configuration — can override with env vars
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "property_embeddings"

# YOLO11 feature extractor produces 512-dim embeddings
# (from the backbone's last pooling layer)
VECTOR_SIZE = 512


def init_collection():
    """Create the Qdrant collection with proper schema."""
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=30)

    # Check if collection already exists
    collections = client.get_collections().collections
    existing = [c.name for c in collections]

    if COLLECTION_NAME in existing:
        info = client.get_collection(COLLECTION_NAME)
        logger.info(
            f"Collection '{COLLECTION_NAME}' already exists "
            f"({info.points_count} points, {info.vectors_count} vectors)"
        )
        return

    # Create collection
    logger.info(f"Creating collection '{COLLECTION_NAME}' ...")

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
        # Optimizers config for dev (small dataset)
        optimizers_config={
            "indexing_threshold": 100,  # Start indexing after 100 vectors
        },
    )

    # Create payload indexes for filtered search
    # Property ID — exact match
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="property_id",
        field_schema=PayloadSchemaType.KEYWORD,
    )

    # City / region — exact match, used for geographic filtering
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="city",
        field_schema=PayloadSchemaType.KEYWORD,
    )

    # Energy label (A-G) — exact match
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="energy_label",
        field_schema=PayloadSchemaType.KEYWORD,
    )

    # Construction year — range queries ("<1960", "1960-1980" etc.)
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="building_year",
        field_schema=PayloadSchemaType.INTEGER,
    )

    # Overall U-Value — range queries
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="overall_u_value",
        field_schema=PayloadSchemaType.FLOAT,
    )

    # Address — full-text search
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="address",
        field_schema=TextIndexParams(
            type="text",
            tokenizer=TokenizerType.WORD,
            min_token_len=2,
            max_token_len=20,
            lowercase=True,
        ),
    )

    logger.info(f"Collection '{COLLECTION_NAME}' created with indexes.")

    # Verify
    info = client.get_collection(COLLECTION_NAME)
    logger.info(
        f"Verified: vectors={info.config.params.vectors.size}, "
        f"distance={info.config.params.vectors.distance}"
    )


if __name__ == "__main__":
    try:
        init_collection()
        logger.info("Qdrant initialization complete.")
    except Exception as e:
        logger.error(f"Qdrant initialization failed: {e}")
        sys.exit(1)
