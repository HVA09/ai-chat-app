"""Tests for the fail-closed Supabase staging restore target guard."""

from pathlib import Path
import sys

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[2] / ".github" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from validate_supabase_staging_target import (  # noqa: E402
    PRODUCTION_PROJECT_REF,
    RestoreTargetError,
    validate_staging_target,
)


STAGING_PROJECT_REF = "abcdefghijklmnopqrst"
VALID_STAGING_URL = (
    f"postgresql://postgres:staging-secret@db.{STAGING_PROJECT_REF}.supabase.co:"
    "5432/postgres?sslmode=require"
)


def test_accepts_matching_direct_staging_database_url():
    validate_staging_target(VALID_STAGING_URL, STAGING_PROJECT_REF)


def test_rejects_known_production_project_ref():
    production_url = (
        f"postgresql://postgres:secret@db.{PRODUCTION_PROJECT_REF}.supabase.co:"
        "5432/postgres?sslmode=require"
    )

    with pytest.raises(RestoreTargetError, match="production project"):
        validate_staging_target(production_url, PRODUCTION_PROJECT_REF)


def test_rejects_database_host_that_does_not_match_staging_ref():
    url = VALID_STAGING_URL.replace(
        f"db.{STAGING_PROJECT_REF}.supabase.co",
        f"db.{PRODUCTION_PROJECT_REF}.supabase.co",
    )

    with pytest.raises(RestoreTargetError, match="does not match"):
        validate_staging_target(url, STAGING_PROJECT_REF)


def test_rejects_pooler_or_non_direct_database_port():
    url = VALID_STAGING_URL.replace(":5432/", ":6543/")

    with pytest.raises(RestoreTargetError, match="port 5432"):
        validate_staging_target(url, STAGING_PROJECT_REF)


def test_rejects_database_url_without_tls_requirement():
    url = VALID_STAGING_URL.replace("sslmode=require", "sslmode=disable")

    with pytest.raises(RestoreTargetError, match="sslmode=require"):
        validate_staging_target(url, STAGING_PROJECT_REF)


def test_rejects_missing_or_malformed_project_ref():
    with pytest.raises(RestoreTargetError, match="20-character"):
        validate_staging_target(VALID_STAGING_URL, "not-a-project-ref")


def test_rejects_missing_database_url():
    with pytest.raises(RestoreTargetError, match="is missing"):
        validate_staging_target("", STAGING_PROJECT_REF)
