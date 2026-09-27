"""Developer API versioning policy and helpers."""

DEVELOPER_API_VERSION = "v1"
DEVELOPER_API_PREFIX = f"/{DEVELOPER_API_VERSION}"
DEVELOPER_API_VERSION_HEADER = "X-API-Version"


def developer_api_version_metadata() -> dict[str, str]:
    return {
        "version": DEVELOPER_API_VERSION,
        "status": "stable",
        "policy": "Breaking changes require a new major URL version.",
    }
