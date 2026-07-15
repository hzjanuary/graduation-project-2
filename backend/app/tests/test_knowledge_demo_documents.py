"""Tests for deterministic demo knowledge document definitions."""

from __future__ import annotations

from app.demo.knowledge_documents import DEMO_KNOWLEDGE_DOCUMENTS
from app.knowledge.chunking import chunk_document, sha256_normalized_text
from app.knowledge.schemas import KnowledgeDocumentSourceType


def test_demo_knowledge_documents_cover_required_source_types() -> None:
    source_types = {
        document.metadata.source_type for document in DEMO_KNOWLEDGE_DOCUMENTS
    }

    assert {
        KnowledgeDocumentSourceType.POLICY,
        KnowledgeDocumentSourceType.CONTRACT,
        KnowledgeDocumentSourceType.SUPPLIER_PROFILE,
        KnowledgeDocumentSourceType.PRICING,
        KnowledgeDocumentSourceType.COMPLIANCE_CHECKLIST,
    }.issubset(source_types)


def test_demo_knowledge_documents_have_stable_safe_metadata() -> None:
    document_ids = [
        document.metadata.document_id for document in DEMO_KNOWLEDGE_DOCUMENTS
    ]
    object_keys = [
        document.metadata.object_storage_key for document in DEMO_KNOWLEDGE_DOCUMENTS
    ]

    assert len(document_ids) == len(set(document_ids))
    assert all(document_id.startswith("demo-kb-") for document_id in document_ids)
    assert all(key and key.startswith("demo/knowledge/") for key in object_keys)
    assert all(
        document.metadata.domain == "procurement"
        for document in DEMO_KNOWLEDGE_DOCUMENTS
    )
    assert all(
        document.metadata.attributes["demo_seed"] is True
        for document in DEMO_KNOWLEDGE_DOCUMENTS
    )


def test_demo_knowledge_checksums_and_chunks_are_deterministic() -> None:
    first_document = DEMO_KNOWLEDGE_DOCUMENTS[0]
    first_chunking = chunk_document(first_document)
    second_chunking = chunk_document(first_document)

    assert first_document.metadata.checksum == sha256_normalized_text(
        first_document.content
    )
    assert first_chunking == second_chunking
    assert first_chunking.chunks[0].metadata.chunk_id.startswith(
        f"kbchunk:{first_document.metadata.document_id}:0:"
    )
