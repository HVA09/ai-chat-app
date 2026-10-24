import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { axiosMock } = vi.hoisted(() => {
  const client = {
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  };

  return {
    axiosMock: {
      create: vi.fn(() => client),
      post: vi.fn(),
    },
  };
});

vi.mock("axios", () => ({ default: axiosMock }));

import axios from "axios";
import { restoreSession } from "./api";

describe("restoreSession cold-start recovery", () => {
  beforeEach(() => {
    axios.post.mockReset();
    vi.useRealTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("retries a temporary 503 and restores the session once the backend is available", async () => {
    vi.useFakeTimers();
    axios.post
      .mockRejectedValueOnce({ response: { status: 503 } })
      .mockResolvedValueOnce({ data: { access_token: "test-access-token" } });

    const pending = restoreSession();
    await vi.advanceTimersByTimeAsync(1500);

    await expect(pending).resolves.toBe("test-access-token");
    expect(axios.post).toHaveBeenCalledTimes(2);
    expect(axios.post.mock.calls[0][2]).toMatchObject({
      timeout: 12000,
      withCredentials: true,
    });
  });

  it("does not retry a 401 because no saved session is a normal state", async () => {
    const unauthorized = { response: { status: 401 } };
    axios.post.mockRejectedValueOnce(unauthorized);

    await expect(restoreSession()).rejects.toBe(unauthorized);
    expect(axios.post).toHaveBeenCalledTimes(1);
  });

  it("shares an in-flight session restore rather than issuing concurrent refresh requests", async () => {
    let finishRequest;
    axios.post.mockImplementation(
      () =>
        new Promise((resolve) => {
          finishRequest = resolve;
        })
    );

    const first = restoreSession();
    const second = restoreSession();

    expect(second).toBe(first);
    expect(axios.post).toHaveBeenCalledTimes(1);

    finishRequest({ data: { access_token: "shared-test-token" } });
    await expect(first).resolves.toBe("shared-test-token");
  });
});
