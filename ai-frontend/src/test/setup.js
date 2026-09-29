import { expect } from "vitest";
import * as matchers from "@testing-library/jest-dom/matchers";

expect.extend(matchers);


/*
 * Component tests render children directly rather than through main.jsx.
 * Keep the production AppDialogProvider intact while emulating the old
 * browser-dialog contract used by legacy component tests.
 */
import { vi } from "vitest";

vi.mock("../components/AppDialog", async () => {
  const actual = await vi.importActual("../components/AppDialog");
  return {
    ...actual,
    useAppDialog: () => ({
      alert: async ({ message = "" } = {}) => {
        window.alert(message);
        return true;
      },
      confirm: async ({ message = "" } = {}) => window.confirm(message),
      prompt: async ({ message = "", defaultValue = "" } = {}) =>
        window.prompt(message, defaultValue),
    }),
  };
});
