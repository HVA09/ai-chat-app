import { describe, expect, it, vi } from "vitest";
import { runSequentially } from "./runSequentially";

describe("runSequentially", () => {
  it("waits for each startup read before starting the next", async () => {
    const order = [];
    let resolveFirst;
    const first = vi.fn(() => {
      order.push("first:start");
      return new Promise((resolve) => {
        resolveFirst = () => {
          order.push("first:end");
          resolve();
        };
      });
    });
    const second = vi.fn(() => order.push("second"));
    const third = vi.fn(() => order.push("third"));

    const pending = runSequentially([first, second, third]);

    expect(order).toEqual(["first:start"]);
    expect(second).not.toHaveBeenCalled();

    resolveFirst();
    await pending;

    expect(order).toEqual(["first:start", "first:end", "second", "third"]);
  });

  it("stops before starting another read when the session is no longer active", async () => {
    let active = true;
    const second = vi.fn();
    await runSequentially(
      [
        async () => {
          active = false;
        },
        second,
      ],
      () => active
    );

    expect(second).not.toHaveBeenCalled();
  });

  it("propagates unexpected loader errors instead of silently skipping them", async () => {
    const failure = new Error("unexpected startup failure");
    const second = vi.fn();

    await expect(
      runSequentially([
        async () => {
          throw failure;
        },
        second,
      ])
    ).rejects.toBe(failure);

    expect(second).not.toHaveBeenCalled();
  });
});
