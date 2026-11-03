import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_database_url_is_required_without_env_file(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)
