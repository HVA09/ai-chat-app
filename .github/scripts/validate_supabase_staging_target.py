#!/usr/bin/env python3
"""Fail-closed validation for the Supabase staging restore destination.

This script intentionally accepts only a direct PostgreSQL connection URL for a
Supabase project whose ref matches SUPABASE_STAGING_PROJECT_REF. It refuses the
known production project and does not print the URL or credentials.
"""

from __future__ import annotations

import os
import re
import sys
from urllib.parse import parse_qs, urlsplit

PRODUCTION_PROJECT_REF = "wfhijmawoojcmfdgibxg"
PROJECT_REF_PATTERN = re.compile(r"^[a-z0-9]{20}$")


class RestoreTargetError(ValueError):
    """Raised when the restore destination is missing or unsafe."""


def validate_staging_target(database_url: str, staging_project_ref: str) -> None:
    """Validate an exact direct-connection target without exposing credentials."""
    if not staging_project_ref or not PROJECT_REF_PATTERN.fullmatch(staging_project_ref):
        raise RestoreTargetError("SUPABASE_STAGING_PROJECT_REF must be a 20-character project ref.")

    if staging_project_ref == PRODUCTION_PROJECT_REF:
        raise RestoreTargetError("The configured staging project ref is the production project.")

    if not database_url:
        raise RestoreTargetError("SUPABASE_STAGING_DB_URL is missing.")

    try:
        parsed = urlsplit(database_url)
        port = parsed.port
    except ValueError as exc:
        raise RestoreTargetError("The staging database URL is malformed.") from exc

    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RestoreTargetError("The staging target must use PostgreSQL.")
    if parsed.username != "postgres" or not parsed.password:
        raise RestoreTargetError("The staging target must use the project's direct postgres credentials.")
    if parsed.hostname != f"db.{staging_project_ref}.supabase.co":
        raise RestoreTargetError("The database URL host does not match the configured staging project ref.")
    if port != 5432:
        raise RestoreTargetError("Only the direct Supabase PostgreSQL port 5432 is allowed.")
    if parsed.path != "/postgres":
        raise RestoreTargetError("The staging database URL must target the postgres database.")
    if parsed.fragment:
        raise RestoreTargetError("URL fragments are not allowed in the staging database URL.")

    query = parse_qs(parsed.query, keep_blank_values=True)
    if query.get("sslmode") != ["require"]:
        raise RestoreTargetError("The staging database URL must require TLS with sslmode=require.")


def main() -> int:
    try:
        validate_staging_target(
            os.environ.get("SUPABASE_STAGING_DB_URL", ""),
            os.environ.get("SUPABASE_STAGING_PROJECT_REF", ""),
        )
    except RestoreTargetError as exc:
        print(f"Unsafe Supabase staging restore target: {exc}", file=sys.stderr)
        return 1

    print("Supabase staging restore destination validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
