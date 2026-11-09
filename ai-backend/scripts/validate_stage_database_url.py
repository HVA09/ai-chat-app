"""Validate that DATABASE_URL identifies the approved Stage database.

This helper intentionally reads credentials only from the process environment.
It never prints the URI, username, hostname details, or password.
"""
from __future__ import annotations

import os
from urllib.parse import parse_qs, unquote, urlsplit


def main() -> None:
    raw = os.environ.get("DATABASE_URL", "").strip()
    if not raw:
        raise SystemExit(
            "Missing repository Actions secret STAGE_DATABASE_URL. "
            "Add the ai-chat-stage-db connection string in GitHub "
            "Settings > Secrets and variables > Actions, then re-run this job."
        )

    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise SystemExit(
            "DATABASE_URL is malformed; check the Stage connection URI format."
        ) from exc

    project_ref = "ihjuewvddqsesbrqqptj"
    direct_host = f"db.{project_ref}.supabase.co"
    pooler_host = "aws-0-us-east-2.pooler.supabase.com"
    username = unquote(parsed.username or "")
    database = unquote(parsed.path.lstrip("/"))
    sslmode = parse_qs(parsed.query).get("sslmode", [""])[0]

    if parsed.scheme != "postgresql+psycopg":
        raise SystemExit(
            "DATABASE_URL must use postgresql+psycopg:// so the pinned "
            "psycopg v3 driver is selected."
        )
    if port != 5432 or database != "postgres":
        raise SystemExit(
            "Only the Stage project's PostgreSQL database 'postgres' "
            "on port 5432 (direct or session pooler) is allowed."
        )
    if sslmode not in {"require", "verify-ca", "verify-full"}:
        raise SystemExit("DATABASE_URL must include sslmode=require (or stronger).")
    if parsed.password is None or parsed.password == "":
        raise SystemExit("DATABASE_URL must include the Stage database password.")

    direct_ok = parsed.hostname == direct_host and username == "postgres"
    pooler_ok = (
        parsed.hostname == pooler_host
        and username == f"postgres.{project_ref}"
    )
    if not (direct_ok or pooler_ok):
        raise SystemExit(
            "Refusing to connect: URL host/user do not identify the approved "
            "ai-chat-stage-db project. Production and other Supabase refs are rejected."
        )

    print("Stage database URL target validated; credentials were not printed.")


if __name__ == "__main__":
    main()
