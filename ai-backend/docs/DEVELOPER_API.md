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

## Webhooks

Developer webhooks are configured through the authenticated control-plane endpoints:

- `POST /webhooks` creates an endpoint and returns its signing secret once.
- `GET /webhooks` lists only the current user's endpoints.
- `PATCH /webhooks/{id}` updates the endpoint or rotates its secret.
- `DELETE /webhooks/{id}` removes an endpoint.
- `GET /webhooks/{id}/deliveries` lists recent delivery attempts.
- `POST /webhooks/{id}/test` queues a signed test event.

Supported events currently include:

- `api_key.created`
- `api_key.revoked`
- `webhook.test`

Each delivery includes `X-Webhook-Id`, `X-Webhook-Event`, `X-Webhook-Timestamp`, and `X-Webhook-Signature`.

The signature is HMAC-SHA256 over `{timestamp}.{raw_json_body}` and is prefixed with `sha256=`.

Webhook destinations are validated against SSRF-sensitive private, loopback, local, and internal addresses. Production endpoints must use HTTPS. Redirects are not followed.

Delivery is asynchronous through the existing Celery/Redis infrastructure, with persisted attempt history and bounded retries.
