import test from "node:test";
import assert from "node:assert/strict";

import {
  AIChatClient,
  AuthenticationError,
  RateLimitError,
} from "../src/index.js";


test("maps a successful chat response", async () => {
  let request;

  const fetchImpl = async (url, options) => {
    request = { url, options };
    return new Response(
      JSON.stringify({
        conversation_id: 7,
        reply: "Hi!",
        model: "gpt-4o-mini",
      }),
      {
        status: 200,
        headers: {
          "content-type": "application/json",
          "X-API-Version": "v1",
          "X-Request-ID": "req-123",
        },
      },
    );
  };

  const client = new AIChatClient("ak_live_test", {
    baseUrl: "https://api.example.com/v1",
    fetchImpl,
  });
  const result = await client.chat("hello", { model: "gpt-4o-mini" });

  assert.equal(request.url, "https://api.example.com/v1/chat");
  assert.equal(request.options.headers["X-API-Key"], "ak_live_test");
  assert.deepEqual(JSON.parse(request.options.body), {
    message: "hello",
    model: "gpt-4o-mini",
  });
  assert.equal(result.conversationId, 7);
  assert.equal(result.reply, "Hi!");
});


test("maps authentication errors", async () => {
  const fetchImpl = async () =>
    new Response(JSON.stringify({ detail: "Invalid API key" }), {
      status: 401,
      headers: {
        "content-type": "application/json",
        "X-Request-ID": "req-auth",
      },
    });

  const client = new AIChatClient("bad", {
    baseUrl: "https://api.example.com/v1",
    fetchImpl,
  });

  await assert.rejects(
    () => client.chat("hello"),
    (error) => {
      assert.ok(error instanceof AuthenticationError);
      assert.equal(error.statusCode, 401);
      assert.equal(error.requestId, "req-auth");
      return true;
    },
  );
});


test("maps rate limit errors", async () => {
  const fetchImpl = async () =>
    new Response(JSON.stringify({ detail: "Too many requests" }), {
      status: 429,
      headers: {
        "content-type": "application/json",
        "Retry-After": "30",
      },
    });

  const client = new AIChatClient("ak_live_test", {
    baseUrl: "https://api.example.com/v1",
    fetchImpl,
  });

  await assert.rejects(
    () => client.chat("hello"),
    (error) => {
      assert.ok(error instanceof RateLimitError);
      assert.equal(error.statusCode, 429);
      assert.equal(error.retryAfter, "30");
      return true;
    },
  );
});
