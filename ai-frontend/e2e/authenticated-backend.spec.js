import { expect, test } from "@playwright/test";

test("authenticates against the disposable backend and loads the account", async ({ page, request }) => {
  const email = `playwright-${Date.now()}@example.invalid`;
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
  await page.getByRole("button", { name: "دخول" }).click();
  await expect(currentUserResponse).resolves.toBeTruthy();

  await expect(page.getByPlaceholder("اكتب رسالتك هنا...")).toBeVisible();
});
