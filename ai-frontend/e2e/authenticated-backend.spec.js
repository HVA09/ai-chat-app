import { expect, test } from "@playwright/test";

test("authenticates against the disposable backend, loads the account, and uploads a chat attachment", async ({ page, request }) => {
  const email = `playwright-${Date.now()}@example.com`;
  const password = "StrongPass123";

  const registration = await request.post("http://127.0.0.1:8000/auth/register", {
    data: { email, password },
  });
  expect(registration.status()).toBe(201);

  await page.goto("/");
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);

  const currentUserResponse = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/users/me" && response.status() === 200
  );
  const conversationsResponse = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/conversations" &&
    response.request().method() === "GET" &&
    response.status() === 200
  );
  await page.getByRole("button", { name: "دخول" }).click();
  await expect(currentUserResponse).resolves.toBeTruthy();
  const conversationList = await conversationsResponse;
  expect(await conversationList.json()).toEqual([]);

  await expect(page.getByPlaceholder("اكتب رسالتك هنا...")).toBeVisible();

  const uploadResponse = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/files/upload" && response.status() === 201
  );
  await page.locator('input[type="file"][accept=".txt,.csv,.pdf,.docx,.xlsx,image/*"]').setInputFiles({
    name: "playwright-attachment.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Disposable Playwright attachment test content."),
  });
  await expect(uploadResponse).resolves.toBeTruthy();
  await expect(page.getByText("playwright-attachment.txt")).toBeVisible();

  await page.route("**/chat/stream", async (route) => {
    expect(route.request().method()).toBe("POST");
    const payload = route.request().postDataJSON();
    expect(payload.message).toBe("Run the deterministic streaming check");

    await route.fulfill({
      status: 200,
      headers: { "content-type": "text/event-stream; charset=utf-8" },
      body: [
        "event: conversation",
        "data: 987654",
        "",
        "event: chunk",
        "data: Deterministic streaming response",
        "",
        "event: done",
        "data: [DONE]",
        "",
        "",
      ].join("\n"),
    });
  });
  await page.route("**/conversations/987654/generate-title", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ title: "Streaming check" }) });
  });

  const composer = page.getByPlaceholder("اكتب رسالتك هنا...");
  await composer.fill("Run the deterministic streaming check");
  const streamRequest = page.waitForRequest((request) =>
    new URL(request.url()).pathname === "/chat/stream"
  );
  await page.locator(".chat-send-button").click({ force: true });
  await expect(streamRequest).resolves.toBeTruthy();
  await expect(page.getByText("Deterministic streaming response")).toBeVisible({ timeout: 10000 });
});
