# ai-chat-saas — JavaScript SDK

JavaScript client for the AI Chat SaaS Developer API v1.

## Install

```bash
npm install ai-chat-saas
```

Requires Node.js 18+.

## Usage

```js
import { AIChatClient } from "ai-chat-saas";

const client = new AIChatClient("ak_live_...", {
  baseUrl: "https://your-api.example.com/v1",
});

const result = await client.chat("Explain recursion in simple terms.");
console.log(result.reply);
console.log(result.conversationId);
```

The SDK sends X-API-Key and uses the stable POST /v1/chat contract.

Errors expose statusCode, requestId, and retryAfter when provided by the API.

The SDK does not persist or log API keys.