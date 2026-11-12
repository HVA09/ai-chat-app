"""Tests for the fail-closed Supabase staging restore destination guard."""

import hashlib
import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "restore_target_guard.py"
SPEC = importlib.util.spec_from_file_location("restore_target_guard_under_test", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
restore_target_guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(restore_target_guard)

STAGING_REF = "abcdefghijklmnopqrst"
PRODUCTION_REF = "wfhijmawoojcmfdgibxg"
ROOT_CA_CERT_PEM = "-----BEGIN CERTIFICATE-----\nYWJj\n-----END CERTIFICATE-----"
SSL_QUERY = "?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem"


def test_accepts_exact_direct_staging_project_host_with_tls():
    database_url = (
        f"postgresql://postgres:password@db.{STAGING_REF}.supabase.co:"
        "5432/postgres?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem"
    )

    assert restore_target_guard.validate_staging_target(
        database_url, STAGING_REF, PRODUCTION_REF, ROOT_CA_CERT_PEM
    ) == STAGING_REF


def test_accepts_session_pooler_url_only_when_username_contains_exact_staging_ref():
    database_url = (
        f"postgresql://postgres.{STAGING_REF}:password@"
        "aws-0-us-east-2.pooler.supabase.com:5432/postgres?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem"
    )

    assert restore_target_guard.validate_staging_target(
        database_url, STAGING_REF, PRODUCTION_REF, ROOT_CA_CERT_PEM
    ) == STAGING_REF


def test_rejects_known_production_project_even_when_url_is_direct():
    database_url = (
        f"postgresql://postgres:password@db.{PRODUCTION_REF}.supabase.co:"
        "5432/postgres?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem"
    )

    with pytest.raises(ValueError, match="production Supabase project"):
        restore_target_guard.validate_staging_target(
            database_url, STAGING_REF, PRODUCTION_REF, ROOT_CA_CERT_PEM
        )


def test_rejects_staging_allowlist_pointing_to_production():
    production_url = (
        f"postgresql://postgres:password@db.{PRODUCTION_REF}.supabase.co:"
        "5432/postgres?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem"
    )

    with pytest.raises(ValueError, match="must not equal the production"):
        restore_target_guard.validate_staging_target(
            production_url, PRODUCTION_REF, PRODUCTION_REF, ROOT_CA_CERT_PEM
        )


def test_rejects_url_for_a_different_non_production_project():
    other_ref = "zyxwvutsrqponmlkjihg"
    database_url = (
        f"postgresql://postgres:password@db.{other_ref}.supabase.co:"
        "5432/postgres?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem"
    )

    with pytest.raises(ValueError, match="does not match"):
        restore_target_guard.validate_staging_target(
            database_url, STAGING_REF, PRODUCTION_REF, ROOT_CA_CERT_PEM
        )


def test_rejects_unknown_pooler_username_without_project_ref():
    database_url = (
        "postgresql://postgres:password@aws-0-us-east-2.pooler.supabase.com:"
        "5432/postgres?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem"
    )

    with pytest.raises(ValueError, match="cannot prove"):
        restore_target_guard.validate_staging_target(
            database_url, STAGING_REF, PRODUCTION_REF, ROOT_CA_CERT_PEM
        )


@pytest.mark.parametrize(
    "database_url",
    [
        "",
        "https://db.abcdefghijklmnopqrst.supabase.co/postgres",
        "postgresql://postgres:password@db.not-a-project-ref.supabase.co:5432/postgres?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem",
    ],
)
def test_rejects_missing_or_unverifiable_database_urls(database_url):
    with pytest.raises(ValueError):
        restore_target_guard.validate_staging_target(
            database_url, STAGING_REF, PRODUCTION_REF, ROOT_CA_CERT_PEM
        )


def test_rejects_missing_or_invalid_staging_project_ref():
    database_url = (
        f"postgresql://postgres:password@db.{STAGING_REF}.supabase.co:"
        "5432/postgres?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem"
    )

    with pytest.raises(ValueError, match="missing or invalid"):
        restore_target_guard.validate_staging_target(
            database_url, "", PRODUCTION_REF, ROOT_CA_CERT_PEM
        )


@pytest.mark.parametrize(
    "url_suffix, error",
    [
        ("6543/postgres?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem", "port 5432"),
        ("5432/postgres?sslmode=disable&sslrootcert=/ca/supabase-root-ca.pem", "sslmode=verify-full"),
        ("5432/postgres?sslmode=verify-full", "only sslmode and sslrootcert"),
        ("5432/other?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem", "postgres database"),
    ],
)
def test_rejects_pooler_mode_wrong_database_or_unverified_tls(url_suffix, error):
    database_url = (
        f"postgresql://postgres.{STAGING_REF}:password@"
        f"aws-0-us-east-2.pooler.supabase.com:{url_suffix}"
    )

    with pytest.raises(ValueError, match=error):
        restore_target_guard.validate_staging_target(
            database_url, STAGING_REF, PRODUCTION_REF, ROOT_CA_CERT_PEM
        )


@pytest.mark.parametrize(
    "key",
    [
        "database/staging-sanitized/ai-chat-postgres-20261108T120000Z.dump",
        "database/staging-sanitized/staging_backup-v2.dump",
    ],
)
def test_accepts_single_sanitized_dump_filename_under_staging_prefix(key):
    assert restore_target_guard.is_safe_staging_backup_key(
        key, "database/staging-sanitized/"
    )


@pytest.mark.parametrize(
    "key",
    [
        "database/staging-sanitized/backup.dump\nSTAGING_BACKUP_KEY=attacker.dump",
        "database/staging-sanitized/backup.dump\rINJECTED=value",
        "database/staging-sanitized/backup.dump=INJECTED",
        "database/staging-sanitized/../production.dump",
        "database/staging-sanitized/nested/backup.dump",
        "database/production/backup.dump",
        None,
    ],
)
def test_rejects_unsafe_or_untrusted_staging_backup_object_keys(key):
    assert not restore_target_guard.is_safe_staging_backup_key(
        key, "database/staging-sanitized/"
    )


def test_rejects_untrusted_query_parameters_that_could_override_connection_routing():
    database_url = (
        f"postgresql://postgres:password@db.{STAGING_REF}.supabase.co:"
        "5432/postgres?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem"
        f"&host=db.{PRODUCTION_REF}.supabase.co"
    )

    with pytest.raises(ValueError, match="only sslmode and sslrootcert"):
        restore_target_guard.validate_staging_target(
            database_url, STAGING_REF, PRODUCTION_REF, ROOT_CA_CERT_PEM
        )


def test_rejects_unrecognized_supavisor_hostname_even_with_matching_username():
    database_url = (
        f"postgresql://postgres.{STAGING_REF}:password@evil.pooler.supabase.com:"
        "5432/postgres?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem"
    )

    with pytest.raises(ValueError, match="cannot prove"):
        restore_target_guard.validate_staging_target(
            database_url, STAGING_REF, PRODUCTION_REF, ROOT_CA_CERT_PEM
        )


@pytest.mark.parametrize(
    "certificate",
    [
        "",
        "not a certificate",
        "-----BEGIN CERTIFICATE-----\nnot-base64!!\n-----END CERTIFICATE-----",
    ],
)
def test_rejects_missing_or_malformed_supabase_root_ca(certificate):
    database_url = (
        f"postgresql://postgres:password@db.{STAGING_REF}.supabase.co:"
        "5432/postgres?sslmode=verify-full&sslrootcert=/ca/supabase-root-ca.pem"
    )

    with pytest.raises(ValueError, match=r"root CA|SUPABASE_STAGING_ROOT_CA_CERT_PEM"):
        restore_target_guard.validate_staging_target(
            database_url, STAGING_REF, PRODUCTION_REF, certificate
        )


def test_verifies_archive_against_pre_reviewed_sha256(tmp_path):
    archive = tmp_path / "staging.dump"
    payload = b"reviewed staging archive payload"
    archive.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()

    assert restore_target_guard.verify_sha256_file(archive, expected)
    assert not restore_target_guard.verify_sha256_file(archive, "0" * 64)


@pytest.mark.parametrize(
    "digest",
    [
        "",
        "0" * 63,
        "g" * 64,
        " " + "a" * 64,
        "a" * 65,
    ],
)
def test_rejects_invalid_reviewed_archive_sha256_input(tmp_path, digest):
    archive = tmp_path / "staging.dump"
    archive.write_bytes(b"reviewed staging archive payload")

    assert not restore_target_guard.verify_sha256_file(archive, digest)
