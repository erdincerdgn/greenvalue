#!/usr/bin/env python3
"""
GreenValue AI — Book Ingestion Script (Phase 2A.1)

Ingests all 8 RAG Knowledge Library PDFs into Qdrant with book-aware
metadata tagging.  Each PDF is matched to its BOOK_LIBRARY entry so
that downstream retrieval can filter by book_id.

Usage:
    # From the project root (/app)
    python -m scripts.ingest_books                     # ingest all
    python -m scripts.ingest_books --force-recreate    # wipe + re-ingest
    python -m scripts.ingest_books --verify-only       # check existing collections
    python -m scripts.ingest_books --book book_01_ivs  # ingest a single book

Environment:
    - Qdrant must be running at QDRANT_URL (default: http://qdrant:6333)
    - Ollama must be running for embeddings
    - PDFs must exist under: infrastructure/qdrant/knowledge_base/books/
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.rag.config import RAGConfig
from modules.rag.store import GreenValueDocumentStore
from modules.rag.ingestion import EnhancedDocumentIngestionPipeline
from modules.rag.router import BOOK_LIBRARY, identify_book_from_filename

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("greenvalue-ingest")


# ── Helpers ──────────────────────────────────────────────────

def _book_id_to_filename_hint(book_id: str) -> str:
    """Return the filename_pattern for a book_id."""
    for book in BOOK_LIBRARY.values():
        if book["book_id"] == book_id:
            return book["filename_pattern"]
    return ""


def _find_pdf_for_book(directory: Path, book: dict) -> Path | None:
    """Find the PDF file that matches a book's filename pattern."""
    import re
    pattern = book["filename_pattern"]
    for pdf in sorted(directory.glob("*.pdf")) + sorted(directory.glob("*.PDF")):
        if re.search(pattern, pdf.name.lower()):
            return pdf
    return None


def verify_collections(config: RAGConfig, store: GreenValueDocumentStore) -> dict:
    """Verify Qdrant collections exist and report per-book stats."""
    store.initialize()
    stats = store.get_collection_stats()

    # Attempt to count points per book_id in child collection
    book_counts = {}
    try:
        from qdrant_client import models
        for book in BOOK_LIBRARY.values():
            book_id = book["book_id"]
            result = store.client.count(
                collection_name=config.child_collection,
                count_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.book_id",
                            match=models.MatchValue(value=book_id),
                        )
                    ]
                ),
            )
            book_counts[book_id] = result.count
    except Exception as e:
        logger.warning(f"Could not count per-book points: {e}")

    return {
        "collection_stats": stats,
        "book_counts": book_counts,
    }


def ingest_single_book(
    pipeline: EnhancedDocumentIngestionPipeline,
    directory: Path,
    book_id: str,
) -> dict:
    """Ingest a single book by book_id."""
    target_book = None
    for book in BOOK_LIBRARY.values():
        if book["book_id"] == book_id:
            target_book = book
            break

    if not target_book:
        return {"success": False, "error": f"Unknown book_id: {book_id}"}

    pdf_path = _find_pdf_for_book(directory, target_book)
    if not pdf_path:
        return {
            "success": False,
            "error": f"PDF not found for {book_id} (pattern: {target_book['filename_pattern']})",
        }

    logger.info(f"📚 Ingesting: {target_book['title']}")
    logger.info(f"   File: {pdf_path.name} ({pdf_path.stat().st_size / 1024 / 1024:.1f} MB)")

    result = pipeline.ingest_file(str(pdf_path))
    result["book_id"] = book_id
    result["book_title"] = target_book["title"]
    return result


def ingest_all_books(
    pipeline: EnhancedDocumentIngestionPipeline,
    config: RAGConfig,
    force_recreate: bool = False,
) -> dict:
    """Ingest all 8 RAG Knowledge Library books."""
    directory = Path(config.knowledge_base_path)

    if not directory.exists():
        return {"success": False, "error": f"Directory not found: {directory}"}

    # Setup collections
    if not pipeline.store.setup_collections(force_recreate=force_recreate):
        return {"success": False, "error": "Failed to setup Qdrant collections"}

    start = time.time()
    results = []
    total_chunks = 0
    total_tables = 0

    # Iterate books in chain_order so dependencies ingest first
    ordered_books = sorted(BOOK_LIBRARY.values(), key=lambda b: b["chain_order"])

    for book in ordered_books:
        book_id = book["book_id"]
        pdf_path = _find_pdf_for_book(directory, book)

        if not pdf_path:
            logger.warning(f"⚠️  PDF not found for {book_id} ({book['title']})")
            results.append({
                "book_id": book_id,
                "success": False,
                "error": "PDF not found",
            })
            continue

        logger.info(f"\n{'='*60}")
        logger.info(f"📚 [{book['chain_role']}] {book['title']}")
        logger.info(f"   File: {pdf_path.name} ({pdf_path.stat().st_size / 1024 / 1024:.1f} MB)")
        logger.info(f"   Domains: {[d.value for d in book['domains']]}")

        result = pipeline.ingest_file(str(pdf_path))
        result["book_id"] = book_id
        result["book_title"] = book["title"]
        result["chain_role"] = book["chain_role"]
        results.append(result)

        if result.get("success"):
            total_chunks += result.get("child_docs", 0)
            total_tables += result.get("tables_extracted", 0)

    elapsed = time.time() - start
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    summary = {
        "success": True,
        "total_books": len(BOOK_LIBRARY),
        "ingested": len(successful),
        "failed": len(failed),
        "total_chunks": total_chunks,
        "total_tables": total_tables,
        "elapsed_seconds": round(elapsed, 1),
        "results": results,
    }

    logger.info(f"\n{'='*60}")
    logger.info(f"🎯 Book Ingestion Complete")
    logger.info(f"   Books: {len(successful)}/{len(BOOK_LIBRARY)}")
    logger.info(f"   Chunks: {total_chunks:,}")
    logger.info(f"   Tables: {total_tables:,}")
    logger.info(f"   Time: {elapsed:.1f}s")

    if failed:
        logger.warning(f"   ⚠️  Failed: {[r['book_id'] for r in failed]}")

    return summary


# ── CLI ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="GreenValue AI — Book Ingestion (Phase 2A.1)"
    )
    parser.add_argument(
        "--force-recreate", action="store_true",
        help="Wipe and recreate Qdrant collections before ingesting",
    )
    parser.add_argument(
        "--verify-only", action="store_true",
        help="Only verify existing collections (do not ingest)",
    )
    parser.add_argument(
        "--book", type=str, default=None,
        help="Ingest a single book by book_id (e.g. book_01_ivs)",
    )
    parser.add_argument(
        "--output-json", type=str, default=None,
        help="Write results to a JSON file",
    )
    args = parser.parse_args()

    config = RAGConfig()
    store = GreenValueDocumentStore(config)
    store.initialize()

    if args.verify_only:
        logger.info("🔍 Verify-only mode — checking Qdrant collections")
        result = verify_collections(config, store)
        print(json.dumps(result, indent=2, default=str))
        return

    pipeline = EnhancedDocumentIngestionPipeline(config, store)

    if args.book:
        directory = Path(config.knowledge_base_path)
        result = ingest_single_book(pipeline, directory, args.book)
    else:
        result = ingest_all_books(pipeline, config, force_recreate=args.force_recreate)

    # Print summary
    print(json.dumps(result, indent=2, default=str))

    # Verify after ingestion
    logger.info("\n📊 Post-ingestion verification:")
    verify_result = verify_collections(config, store)
    for book_id, count in verify_result.get("book_counts", {}).items():
        status = "✅" if count > 0 else "❌"
        logger.info(f"   {status} {book_id}: {count} chunks")

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump({"ingestion": result, "verification": verify_result}, f, indent=2, default=str)
        logger.info(f"📄 Results written to {args.output_json}")


if __name__ == "__main__":
    main()
