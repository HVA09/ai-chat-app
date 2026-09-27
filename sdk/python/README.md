# ai-chat-saas — Python SDK

Python client for the AI Chat SaaS Developer API v1.

## Install

```bash
pip install ai-chat-saas
```

## Usage

```python
from ai_chat_saas import AIChatClient

with AIChatClient(
    "ak_live_...",
    base_url="https://your-api.example.com/v1",
) as client:
    result = client.chat(
        "Explain recursion in simple terms.",
        model="gpt-4o-mini",
    )

print(result.reply)
print(result.conversation_id)
```

The SDK sends X-API-Key and uses the stable POST /v1/chat contract.

## Errors

AuthenticationError, ValidationError, RateLimitError, and APIError expose status_code, request_id, and retry_after when the API provides them.

The SDK does not store or log API keys.