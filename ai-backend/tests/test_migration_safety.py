"""Regression tests for security-sensitive Alembic downgrade behavior."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def test_harden_public_rls_downgrade_never_disables_rls(monkeypatch):
    migration_path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "0080_harden_public_rls.py"
    )
    spec = spec_from_file_location("migration_0080_harden_public_rls", migration_path)
    assert spec is not None and spec.loader is not None

    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)

    executed_statements = []
    monkeypatch.setattr(
        migration.op,
        "execute",
        lambda statement: executed_statements.append(str(statement)),
    )

    migration.downgrade()

    assert executed_statements == []
