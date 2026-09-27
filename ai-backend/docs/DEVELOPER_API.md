# Developer API Versioning

## Current version

The public developer API currently uses URL versioning with:

- Base version: `v1`
- Discovery endpoint: `GET /v1`
- Chat endpoint: `POST /v1/chat`
- Response header: `X-API-Version: v1`

## Compatibility policy

Versioned endpoints must remain backward-compatible within the same major URL version. A breaking request, response, authentication, or semantic change requires a new URL version such as `/v2`.

Non-breaking additions may be introduced inside an existing version.

The control-plane endpoints used by the web application, such as `/api-keys`, remain outside the public developer API version namespace. They are authenticated application-management endpoints.

## Authentication

Developer chat requests use the user's API key through:

`X-API-Key: ak_live_...`

API key creation, revocation, expiry, usage reporting, and rate limits are handled by the existing API key management endpoints.

## Migration policy

When a new major version is introduced, the previous version remains available during an explicit compatibility window. The project should document any deprecation date before removing an older version.

