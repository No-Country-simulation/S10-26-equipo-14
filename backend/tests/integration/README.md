# PostgreSQL integration tests

Integration tests use only `PRICESCOPE_TEST_DATABASE_URL`; they never fall back to `DATABASE_URL` or the root `.env` value. The test fixture rejects non-PostgreSQL URLs, hosts outside loopback, and any database name other than `pricescope_test`.

Local test database provisioned for this workspace:

```text
postgresql+psycopg://postgres@127.0.0.1/pricescope_test
```

Run the full suite, including PostgreSQL integration tests, from PowerShell:

```powershell
$env:PRICESCOPE_TEST_DATABASE_URL = 'postgresql+psycopg://postgres@127.0.0.1/pricescope_test'
python -m pytest -q
Remove-Item Env:PRICESCOPE_TEST_DATABASE_URL
```

The integration fixture checks the database name and current schema before migration, accepts only an empty database, the known `cb0deba93496` state, the prior `4db267e3b121` schema, or the current `d8f31a9c0e42` test schema, then runs Alembic and `alembic check`. It does not drop tables or databases. Test data is rolled back after each test.

Without `PRICESCOPE_TEST_DATABASE_URL`, PostgreSQL tests are skipped. Unit/API tests use SQLite in memory and force `DATABASE_URL=sqlite://` in the test process.
