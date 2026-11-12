# Embeddings provider configuration

This page documents the independent Embeddings provider settings introduced by the isolated provider-configuration change.

## Backward-compatible mode

Leave these values empty:

```dotenv
EMBEDDING_PROVIDER=
EMBEDDING_API_KEY=
EMBEDDING_API_BASE_URL=
EMBEDDING_MODEL=
EMBEDDING_DIMENSIONS=768
```

The service follows `AI_PROVIDER` and uses the chat key/base URL only when doing so is safe. For an existing Gemini-compatible deployment that uses the official Google host in `AI_API_BASE_URL`, the embedding service resolves the native Gemini REST endpoint. The provider parser supports Gemini single-vector responses, Gemini batch responses, and OpenAI-compatible `data[].embedding` responses; the singular Gemini parser fix was already merged separately in PR #690 and is not a new change in this extraction.

## Independent provider mode

Set the following variables explicitly when Embeddings must use a provider separate from chat:

- `EMBEDDING_PROVIDER`: `gemini`, `openai`, or `openai-compatible`.
- `EMBEDDING_API_KEY`: the key for the Embeddings provider. Do not reuse a chat key for a different provider.
- `EMBEDDING_API_BASE_URL`: required for an independent OpenAI-compatible endpoint; for Gemini it must use the official Google Generative Language HTTPS hostname.
- `EMBEDDING_MODEL`: model name. Defaults are `gemini-embedding-001` for Gemini and `text-embedding-3-small` for OpenAI/OpenAI-compatible.
- `EMBEDDING_DIMENSIONS`: must match the current PostgreSQL `vector(768)` column.

Example — separate Gemini key while chat uses another provider:

```dotenv
EMBEDDING_PROVIDER=gemini
EMBEDDING_API_KEY=your_gemini_embedding_key
EMBEDDING_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSIONS=768
```

Example — OpenAI-compatible embedding endpoint:

```dotenv
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_API_KEY=your_embedding_provider_key
EMBEDDING_API_BASE_URL=https://your-provider.example/v1
EMBEDDING_MODEL=your-compatible-embedding-model
EMBEDDING_DIMENSIONS=768
```

## Safety and compatibility rules

- The service rejects unsupported provider names and obvious model/provider mismatches.
- A separate provider or endpoint requires an explicit Embeddings API key; the chat key is not forwarded to another provider/host.
- An explicitly configured Gemini endpoint must be HTTPS and use the exact official hostname `generativelanguage.googleapis.com`, with no embedded credentials, nonstandard port, query string, or fragment.
- OpenAI-compatible endpoints must be explicitly configured when they are independent of the chat provider.
- Embedding dimensions are checked against the currently stored vector schema. Do not change the dimension in production without a separate schema migration, backup/rollback plan, and full reindexing plan.
- Matching dimensions alone do not make embeddings compatible: changing the provider or embedding model changes the vector space. Existing file chunks must be fully re-embedded before queries use the new provider/model; otherwise retrieval quality can silently collapse even when every vector still has 768 values.
- In backward-compatible mode, `EMBEDDING_PROVIDER` follows `AI_PROVIDER`. Changing the chat provider can therefore also change the implicit Embeddings provider. Before changing `AI_PROVIDER`, explicitly pin `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, and its credentials to preserve the existing embedding space, or complete a separately reviewed full-reindex plan first.
- API keys are never written into source control. Put secrets only in the deployment's secret environment settings.
- This change does not alter Render/Supabase settings, migrate the production database, reindex existing files, or run live provider evaluations.
