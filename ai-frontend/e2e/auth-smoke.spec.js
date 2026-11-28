import { expect, test } from "@playwright/test";

async function openUnauthenticatedApp(page) {
  await page.route("http://localhost:8000/**", async (route) => {
    const url = new URL(route.request().url());
    const corsHeaders = {
      "access-control-allow-origin": "http://127.0.0.1:5173",
      "access-control-allow-credentials": "true",
      "access-control-allow-methods": "GET, POST, OPTIONS",
      "access-control-allow-headers": "Content-Type, Authorization",
    };

    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: corsHeaders });
      return;
    }

    if (url.pathname === "/auth/refresh") {
      await route.fulfill({
        status: 401,
        headers: corsHeaders,
        contentType: "application/json",
        body: JSON.stringify({ detail: "No active test session" }),
      });
      return;
    }

    if (url.pathname === "/auth/password-reset/request") {
      await route.fulfill({
        status: 200,
        headers: corsHeaders,
        contentType: "application/json",
        body: JSON.stringify({ detail: "If the account exists, a reset link will be sent." }),
      });
      return;
    }

    await route.fulfill({
      status: 404,
      headers: corsHeaders,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Unexpected API request in isolated browser test" }),
    });
  });

  await page.goto("/");
}

test("shows the login form and completes the password-recovery request flow", async ({ page }) => {
  await openUnauthenticatedApp(page);

  const email = page.locator('input[type="email"]');
  const password = page.locator('input[type="password"]');

  await expect(email).toBeVisible();
  await expect(password).toBeVisible();
  await expect(page.getByRole("button", { name: "دخول" })).toBeVisible();

  await page.getByRole("button", { name: "نسيت كلمة المرور؟" }).click();
  await expect(page.getByText("استرجاع كلمة المرور")).toBeVisible();
  await expect(password).toHaveCount(0);

  await email.fill("browser-test@example.invalid");
  await page.getByRole("button", { name: "أرسل رابط الاسترجاع" }).click();
  await expect(page.getByText("If the account exists, a reset link will be sent.")).toBeVisible();
});

test("keeps the login form usable on a narrow mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openUnauthenticatedApp(page);

  await expect(page.locator('input[type="email"]')).toBeVisible();
  await expect(page.locator('input[type="password"]')).toBeVisible();
  await expect(page.getByRole("button", { name: "دخول" })).toBeVisible();

  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
  }));

  expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport);
});
