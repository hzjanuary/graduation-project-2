"""Tests for Alembic migration configuration."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

import app.models  # noqa: F401
from app.db import Base

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PHASE_1_TABLES = {
    "users",
    "roles",
    "user_roles",
    "workflows",
    "workflow_events",
    "audit_logs",
}


def test_alembic_config_loads_initial_revision() -> None:
    """Alembic config should locate the initial migration head."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))

    assert config.get_main_option("script_location") == "alembic"

    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    script = ScriptDirectory.from_config(config)

    assert script.get_current_head() == "0001_create_phase_1_core_tables"


def test_alembic_target_metadata_includes_phase_1_tables() -> None:
    """Model registry imports should populate Base metadata for migrations."""
    assert PHASE_1_TABLES.issubset(Base.metadata.tables)
