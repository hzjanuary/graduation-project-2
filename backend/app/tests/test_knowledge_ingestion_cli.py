"""Tests for the explicit demo knowledge ingestion CLI."""

from __future__ import annotations

from typing import Any

import pytest

from app.knowledge.ingest_demo import main
from app.knowledge.ingestion import KnowledgeIngestionSummary


def _summary(*, dry_run: bool) -> KnowledgeIngestionSummary:
    return KnowledgeIngestionSummary(
        dry_run=dry_run,
        committed=not dry_run,
        collection_name="test_demo_knowledge",
        embedding_model="fake-hash-embedding",
        embedding_dimensions=64,
        documents_seen=5,
        chunks_seen=5,
        objects_created=5 if not dry_run else 0,
        objects_reused=0,
        vectors_upserted=5 if not dry_run else 0,
        document_ids=("demo-kb-procurement-policy",),
        object_keys=("demo/knowledge/demo-kb-procurement-policy.txt",),
        chunk_ids=("kbchunk:demo-kb-procurement-policy:0:abc123",),
    )


def test_cli_refuses_mutating_ingestion_without_confirmation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([])

    assert exc_info.value.code == 2
    assert "--confirm-local-demo" in capsys.readouterr().err


def test_cli_allows_dry_run_without_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_run_cli(*, dry_run: bool, collection_name: str) -> Any:
        assert collection_name == "test_demo_knowledge"
        return _summary(dry_run=dry_run)

    monkeypatch.setattr("app.knowledge.ingest_demo._run_cli", fake_run_cli)

    exit_code = main(
        ["--dry-run", "--json", "--collection-name", "test_demo_knowledge"]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"dry_run":true' in output
    assert '"committed":false' in output


def test_cli_json_output_with_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_run_cli(*, dry_run: bool, collection_name: str) -> Any:
        assert dry_run is False
        assert collection_name == "demo_procurement_knowledge"
        return _summary(dry_run=dry_run)

    monkeypatch.setattr("app.knowledge.ingest_demo._run_cli", fake_run_cli)

    exit_code = main(["--confirm-local-demo", "--json"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"committed":true' in output
    assert "api_key" not in output.lower()
    assert "raw_prompt" not in output.lower()


def test_cli_import_does_not_auto_run() -> None:
    import app.knowledge.ingest_demo as ingest_demo_module

    assert callable(ingest_demo_module.main)
