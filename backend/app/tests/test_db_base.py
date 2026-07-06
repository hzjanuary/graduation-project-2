"""Tests for SQLAlchemy declarative base and model mixins."""

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class SampleModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Sample model for testing shared database mixins."""

    __tablename__ = "sample_models"

    name: Mapped[str] = mapped_column(String(100), nullable=False)


def test_base_metadata_has_stable_naming_convention() -> None:
    assert Base.metadata.naming_convention == {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }


def test_sample_model_uses_declarative_base_metadata() -> None:
    assert Base.metadata.tables["sample_models"] is SampleModel.__table__
    assert SampleModel.__tablename__ == "sample_models"


def test_uuid_primary_key_mixin_adds_typed_id_column() -> None:
    id_column = SampleModel.__table__.c.id

    assert id_column.primary_key is True
    assert id_column.nullable is False
    assert id_column.default is not None
    assert callable(id_column.default.arg)


def test_timestamp_mixin_adds_timezone_aware_timestamp_columns() -> None:
    created_at = SampleModel.__table__.c.created_at
    updated_at = SampleModel.__table__.c.updated_at

    assert created_at.default is not None
    assert callable(created_at.default.arg)
    assert created_at.nullable is False
    assert updated_at.nullable is False
    assert isinstance(created_at.type, DateTime)
    assert isinstance(updated_at.type, DateTime)
    assert created_at.type.timezone is True
    assert updated_at.type.timezone is True
    assert updated_at.onupdate is not None


def test_soft_delete_mixin_adds_nullable_deleted_at_column() -> None:
    deleted_at = SampleModel.__table__.c.deleted_at

    assert deleted_at.nullable is True
    assert isinstance(deleted_at.type, DateTime)
    assert deleted_at.type.timezone is True
