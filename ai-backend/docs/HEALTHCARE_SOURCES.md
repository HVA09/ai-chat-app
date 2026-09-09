# Healthcare data sources

The starter keeps public healthcare data sources configurable and isolated from application secrets. These integrations are intentionally not called automatically by the core chat path; add provider-specific adapters under `app/services/healthcare/` and enforce per-user rate limits before exposing them as API routes.

- ClinicalTrials.gov API v2
- RxNorm REST API
- PubMed / NCBI E-utilities
- openFDA API
- NPI Registry API
- Medicare Care Compare / CMS Provider Data Catalog
- DailyMed services API
- CMS Open Data
- CMS Coverage API
- OpenAI Platform (configured through `AI_*`)

For medical workflows, treat these as source data rather than medical advice. Always preserve source attribution, timestamp/cache metadata, and explicit disclaimers in the UI. CMS Coverage has endpoints where an accepted license-agreement token is required; keep such tokens server-side and never expose them to the browser.
