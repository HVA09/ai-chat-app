import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useAppGlobalEvents from "./useAppGlobalEvents";

describe("useAppGlobalEvents", () => {
  let logout;
  let setCommandPaletteOpen;
  let setToast;
  let t;

  beforeEach(() => {
    logout = vi.fn();
    setCommandPaletteOpen = vi.fn();
    setToast = vi.fn();
    t = (key) => `translated:${key}`;
  });

  function mount() {
    return renderHook(() =>
      useAppGlobalEvents({
        logout,
        setCommandPaletteOpen,
        setToast,
        t,
      })
    );
  }

  it("logs out and explains an unauthorized session", () => {
    mount();

    act(() => {
      window.dispatchEvent(new Event("auth:unauthorized"));
    });

    expect(logout).toHaveBeenCalledTimes(1);
    expect(setToast).toHaveBeenCalledWith({
      message: "translated:app.sessionExpired",
      type: "error",
    });
  });

  it("toggles the command palette for Ctrl+K and Meta+K", () => {
    mount();

    const ctrlEvent = new KeyboardEvent("keydown", {
      key: "k",
      ctrlKey: true,
      cancelable: true,
    });
    const metaEvent = new KeyboardEvent("keydown", {
      key: "K",
      metaKey: true,
      cancelable: true,
    });

    act(() => {
      window.dispatchEvent(ctrlEvent);
      window.dispatchEvent(metaEvent);
    });

    expect(ctrlEvent.defaultPrevented).toBe(true);
    expect(metaEvent.defaultPrevented).toBe(true);
    expect(setCommandPaletteOpen).toHaveBeenCalledTimes(2);

    const updater = setCommandPaletteOpen.mock.calls[0][0];
    expect(updater(false)).toBe(true);
    expect(updater(true)).toBe(false);
  });

  it("forwards global toast events and defaults the type to error", () => {
    mount();

    act(() => {
      window.dispatchEvent(
        new CustomEvent("app:toast", {
          detail: { message: "File upload failed", type: "warning" },
        })
      );
      window.dispatchEvent(
        new CustomEvent("app:toast", {
          detail: { message: "Fallback toast" },
        })
      );
      window.dispatchEvent(new CustomEvent("app:toast", { detail: {} }));
    });

    expect(setToast).toHaveBeenNthCalledWith(1, {
      message: "File upload failed",
      type: "warning",
    });
    expect(setToast).toHaveBeenNthCalledWith(2, {
      message: "Fallback toast",
      type: "error",
    });
    expect(setToast).toHaveBeenCalledTimes(2);
  });

  it("removes global listeners on unmount", () => {
    const { unmount } = mount();
    unmount();

    act(() => {
      window.dispatchEvent(new Event("auth:unauthorized"));
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }));
      window.dispatchEvent(
        new CustomEvent("app:toast", { detail: { message: "After unmount" } })
      );
    });

    expect(logout).not.toHaveBeenCalled();
    expect(setCommandPaletteOpen).not.toHaveBeenCalled();
    expect(setToast).not.toHaveBeenCalled();
  });
});
