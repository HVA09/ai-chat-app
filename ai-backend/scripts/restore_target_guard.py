#!/usr/bin/env python3
"""Fail-closed validation for the Supabase staging restore destination."""

from __future__ import annotations

import base64
import os
import re
import sys
from urllib.parse import parse_qs, unquote, urlsplit

PRODUCTION_SUPABASE_PROJECT_REF = "wfhijmawoojcmfdgibxg"
_PROJECT_REF = re.compile(r"^[a-z0-9]{20}$")

_STAGING_BACKUP_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*[.]dump$")


def is_safe_staging_backup_key(key: object, prefix: str) -> bool:
    """Reject S3 object keys that could inject lines into GITHUB_ENV.

    Only a single sanitized .dump filename directly beneath the configured
    staging prefix is accepted. Newlines, equals signs, separators, and nested
    paths are rejected before the key is written to the GitHub environment file.
    """
    if not isinstance(key, str) or not isinstance(prefix, str) or not prefix:
        return False
    if not key.startswith(prefix):
        return False
    filename = key[len(prefix):]
    return _STAGING_BACKUP_FILENAME.fullmatch(filename) is not None




def validate_root_ca_certificate(certificate_pem: str) -> None:
    """Require a well-formed PEM certificate without logging its contents."""
    if not certificate_pem or not certificate_pem.strip():
        raise ValueError("SUPABASE_STAGING_ROOT_CA_CERT_PEM is missing")
    pem = certificate_pem.strip()
    begin = "-----BEGIN CERTIFICATE-----"
    finish = "-----END CERTIFICATE-----"
    if not pem.startswith(begin) or not pem.endswith(finish):
        raise ValueError("Supabase root CA must be a PEM certificate")
    encoded = "".join(
        line.strip()
        for line in pem[len(begin):-len(finish)].splitlines()
        if line.strip()
    )
    try:
        der = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("Supabase root CA PEM encoding is invalid") from exc
    if not der:
        raise ValueError("Supabase root CA certificate is empty")


def extract_supabase_project_ref(database_url: str) -> str:
    """Extract and validate a direct or documented Supavisor session URL."""
    if not database_url or not database_url.strip():
        raise ValueError("staging database URL is missing")

    try:
        parsed = urlsplit(database_url.strip())
        port = parsed.port
        query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise ValueError("staging database URL is malformed") from exc

    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("staging database URL must use PostgreSQL")
    if not parsed.password:
        raise ValueError("staging database URL must contain a password")
    if port != 5432:
        raise ValueError("only direct/session PostgreSQL port 5432 is allowed")
    if parsed.path != "/postgres":
        raise ValueError("staging database URL must target the postgres database")
    if parsed.fragment:
        raise ValueError("URL fragments are not allowed")

    # Keep libpq routing and TLS configuration deterministic. In particular,
    # do not allow query parameters such as host/hostaddr to override the URL
    # hostname that was checked against the approved project reference.
    if set(query) != {"sslmode", "sslrootcert"}:
        raise ValueError(
            "staging database URL must contain only sslmode and sslrootcert parameters"
        )
    if query.get("sslmode") != ["verify-full"]:
        raise ValueError(
            "staging database URL must use sslmode=verify-full"
        )
    if query.get("sslrootcert") != ["/ca/supabase-root-ca.pem"]:
        raise ValueError(
            "staging database URL must use the mounted Supabase root CA certificate"
        )

    hostname = (parsed.hostname or "").lower()
    direct_match = re.fullmatch(r"db\.([a-z0-9]{20})\.supabase\.co", hostname)
    if direct_match and parsed.username == "postgres":
        return direct_match.group(1)

    # Supavisor session mode uses a region-specific shared hostname on port
    # 5432. Reject arbitrary subdomains even when they share the suffix.
    username = unquote(parsed.username or "")
    pooler_match = re.fullmatch(r"postgres\.([a-z0-9]{20})", username)
    session_pooler_host = re.fullmatch(
        r"aws-\d+-[a-z0-9-]+\.pooler\.supabase\.com",
        hostname,
    )
    if pooler_match and session_pooler_host:
        return pooler_match.group(1)

    raise ValueError(
        "cannot prove the Supabase project ref from this direct or session-pooler URL"
    )


def validate_staging_target(
    database_url: str,
    expected_project_ref: str,
    production_project_ref: str = PRODUCTION_SUPABASE_PROJECT_REF,
    root_ca_certificate_pem: str = "",
) -> str:
    """Return the validated staging ref or raise without exposing connection data."""
    expected = (expected_project_ref or "").strip().lower()
    production = (production_project_ref or "").strip().lower()

    if not _PROJECT_REF.fullmatch(expected):
        raise ValueError("SUPABASE_STAGING_PROJECT_REF is missing or invalid")
    if not _PROJECT_REF.fullmatch(production):
        raise ValueError("production project ref guard is missing or invalid")
    if expected == production:
        raise ValueError("staging project ref must not equal the production project ref")

    validate_root_ca_certificate(root_ca_certificate_pem)
    actual = extract_supabase_project_ref(database_url)
    if actual == production:
        raise ValueError("restore target resolves to the production Supabase project")
    if actual != expected:
        raise ValueError("database URL project ref does not match the approved staging project")

    return actual


def main() -> int:
    database_url = os.environ.get("SUPABASE_STAGING_DB_URL", "")
    expected_project_ref = os.environ.get("SUPABASE_STAGING_PROJECT_REF", "")

    try:
        project_ref = validate_staging_target(
            database_url,
            expected_project_ref,
            os.environ.get(
                "SUPABASE_PRODUCTION_PROJECT_REF",
                PRODUCTION_SUPABASE_PROJECT_REF,
            ),
            os.environ.get("SUPABASE_STAGING_ROOT_CA_CERT_PEM", ""),
        )
    except ValueError as exc:
        print(f"Restore target validation failed: {exc}", file=sys.stderr)
        return 1

    # A project ref is not a credential; never print the URL or username.
    print(f"Validated non-production Supabase staging project: {project_ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
