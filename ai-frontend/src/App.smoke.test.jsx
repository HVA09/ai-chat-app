import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./lib/api", async () => {
  const actual = await vi.importActual("./lib/api");
  return {
    ...actual,
    restoreSession: vi.fn().mockRejectedValue(new Error("No active test session")),
  };
});

import App from "./App";

describe("App initial render", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("renders before session restoration without a temporal-dead-zone error", () => {
    expect(() => render(<App />)).not.toThrow();
  });
});
