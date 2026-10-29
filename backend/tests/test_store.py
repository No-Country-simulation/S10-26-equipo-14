
from app.models.store import Store


def test_store_has_expected_columns():
    expected = {
        "id",
        "name",
        "base_url",
        "country",
        "is_active",
        "created_at",
    }

    assert set(Store.__table__.columns.keys()) == expected


def test_store_required_fields_are_not_nullable():
    table = Store.__table__

    for field in ("id", "name", "base_url", "is_active", "created_at"):
        assert table.columns[field].nullable is False


def test_store_has_defaults_for_active_and_created_at():
    table = Store.__table__

    assert table.columns["is_active"].default.arg is True
    assert table.columns["is_active"].server_default is not None
    assert table.columns["created_at"].server_default is not None
