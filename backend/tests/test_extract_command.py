from sqlalchemy.engine import make_url

from app.commands import extract_prices


def test_cli_refuses_remote_database_before_opening_a_session(monkeypatch, capsys):
    monkeypatch.setattr(
        extract_prices.engine,
        "url",
        make_url("postgresql://db.example.invalid/pricescope"),
    )

    assert extract_prices._is_local_database() is False
    assert extract_prices.main(["--store-id", "1"]) == 2
    assert "Refusado" in capsys.readouterr().err
