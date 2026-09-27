# Developer API Versioning

## Current version

The public developer API uses URL versioning:

- Base version: `v1`
- Discovery endpoint: `GET /v1`
- Chat endpoint: `POST /v1/chat`
- Response header: `X-API-Version: v1`

## Compatibility policy

Breaking request, response, authentication, or semantic changes require a new major URL version such as `/v2`.

Non-breaking additions may be introduced within an existing version.

The control-plane endpoints used by the web application, such as `/api-keys`, remain outside the public developer API version namespace.

## Authentication

Developer chat requests use an API key:

`X-API-Key: ak_live_...`

API key creation, revocation, expiry, usage reporting, and rate limiting remain handled by the existing authenticated management endpoints.

## Migration policy

When a new major version is introduced, the previous version remains available during an explicit compatibility window. A deprecation date should be documented before an older version is removed.
