"""Explicit local-demo knowledge ingestion CLI.

This module is intentionally inert on import. Mutating ingestion requires:

``python -m app.knowledge.ingest_demo --confirm-local-demo``
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence

from app.config import get_settings
from app.demo.knowledge_documents import DEMO_KNOWLEDGE_DOCUMENTS
from app.knowledge.embeddings import create_embedding_client
from app.knowledge.ingestion import (
    DEFAULT_KNOWLEDGE_COLLECTION_NAME,
    DemoKnowledgeIngestionService,
    KnowledgeIngestionSummary,
)
from app.storage import create_minio_storage_provider
from app.vectorstore import create_qdrant_vector_store


async def run_demo_knowledge_ingestion(
    *,
    dry_run: bool = False,
    collection_name: str = DEFAULT_KNOWLEDGE_COLLECTION_NAME,
) -> KnowledgeIngestionSummary:
    """Run local-demo knowledge ingestion with configured providers."""
    settings = get_settings()
    storage = create_minio_storage_provider()
    vector_store = create_qdrant_vector_store(str(settings.qdrant_url))
    embedding_client = create_embedding_client(settings.embedding_settings)

    try:
        service = DemoKnowledgeIngestionService(
            storage=storage,
            vector_store=vector_store,
            embedding_client=embedding_client,
            bucket_name=settings.minio_bucket_name,
            collection_name=collection_name,
        )
        return await service.ingest_documents(
            DEMO_KNOWLEDGE_DOCUMENTS,
            dry_run=dry_run,
        )
    finally:
        await storage.close()
        await vector_store.close()


def build_parser() -> argparse.ArgumentParser:
    """Build the local-demo knowledge ingestion CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python -m app.knowledge.ingest_demo",
        description="Ingest deterministic local-demo procurement knowledge.",
    )
    parser.add_argument(
        "--confirm-local-demo",
        action="store_true",
        help="Required for mutating local demo knowledge ingestion.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute documents, chunks, and embeddings summary without writes.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the ingestion summary as JSON.",
    )
    parser.add_argument(
        "--collection-name",
        default=DEFAULT_KNOWLEDGE_COLLECTION_NAME,
        help="Qdrant collection name for demo knowledge chunks.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the demo knowledge ingestion CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.dry_run and not args.confirm_local_demo:
        parser.error("mutating ingestion requires --confirm-local-demo")

    try:
        summary = asyncio.run(
            _run_cli(
                dry_run=args.dry_run,
                collection_name=args.collection_name,
            ),
        )
    except Exception as exc:  # pragma: no cover - bounded CLI failure path
        print(
            f"Demo knowledge ingestion failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    if args.json:
        print(summary.model_dump_json())
    else:
        _print_human_summary(summary)
    return 0


async def _run_cli(
    *,
    dry_run: bool,
    collection_name: str,
) -> KnowledgeIngestionSummary:
    return await run_demo_knowledge_ingestion(
        dry_run=dry_run,
        collection_name=collection_name,
    )


def _print_human_summary(summary: KnowledgeIngestionSummary) -> None:
    print(summary.demo_only_warning)
    print(f"Dry run: {summary.dry_run}")
    print(f"Committed: {summary.committed}")
    print(f"Collection: {summary.collection_name}")
    print(f"Embedding model: {summary.embedding_model}")
    print(f"Embedding dimensions: {summary.embedding_dimensions}")
    print("Documents:")
    print(f"  seen: {summary.documents_seen}")
    print(f"  object keys: {len(summary.object_keys)}")
    print("Chunks:")
    print(f"  seen: {summary.chunks_seen}")
    print(f"  vectors upserted: {summary.vectors_upserted}")
    print("Objects:")
    print(f"  created: {summary.objects_created}")
    print(f"  reused: {summary.objects_reused}")


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_parser", "main", "run_demo_knowledge_ingestion"]
