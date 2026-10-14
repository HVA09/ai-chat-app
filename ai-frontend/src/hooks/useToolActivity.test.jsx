import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useToolActivity from "./useToolActivity";

const { mockT } = vi.hoisted(() => ({
  mockT: vi.fn((key) => key),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: mockT }),
}));

function renderToolActivity() {
  const setToolActivity = vi.fn();
  const hook = renderHook(() => useToolActivity({ setToolActivity }));
  return { ...hook, setToolActivity };
}

describe("useToolActivity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("ignores missing or unknown event types", () => {
    const { result, setToolActivity } = renderToolActivity();

    act(() => {
      result.current.handleToolEvent(null);
      result.current.handleToolEvent({});
      result.current.handleToolEvent({ type: "not_supported" });
    });

    expect(setToolActivity).not.toHaveBeenCalled();
  });

  it("maps runtime start and round events to running activity", () => {
    const { result, setToolActivity } = renderToolActivity();

    act(() => result.current.handleToolEvent({ type: "runtime_start" }));
    expect(setToolActivity).toHaveBeenLastCalledWith({
      name: "agent",
      phase: "running",
      message: "tools.activity.runtimeStarting",
    });

    act(() => result.current.handleToolEvent({ type: "runtime_round_start", round: 3 }));
    expect(setToolActivity).toHaveBeenLastCalledWith({
      name: "agent",
      phase: "running",
      message: "tools.activity.round",
    });
    expect(mockT).toHaveBeenCalledWith("tools.activity.round", { round: 3 });

    act(() => result.current.handleToolEvent({ type: "runtime_round_start" }));
    expect(mockT).toHaveBeenLastCalledWith("tools.activity.round", { round: 1 });
  });

  it("preserves tool start, success, and failure activity details", () => {
    const { result, setToolActivity } = renderToolActivity();

    act(() => result.current.handleToolEvent({ type: "start", name: "python", round: 2 }));
    expect(setToolActivity).toHaveBeenLastCalledWith({
      name: "python",
      phase: "running",
      round: 2,
      duration_ms: null,
    });

    act(() => result.current.handleToolEvent({
      type: "result",
      name: "python",
      ok: true,
      round: 2,
      duration_ms: 125,
    }));
    expect(setToolActivity).toHaveBeenLastCalledWith({
      name: "python",
      phase: "done",
      round: 2,
      duration_ms: 125,
    });

    act(() => result.current.handleToolEvent({
      type: "result",
      ok: false,
      round: 4,
      duration_ms: 800,
    }));
    expect(setToolActivity).toHaveBeenLastCalledWith({
      name: "agent",
      phase: "error",
      round: 4,
      duration_ms: 800,
    });
  });

  it("maps budget and security events to warning or error states", () => {
    const { result, setToolActivity } = renderToolActivity();

    act(() => result.current.handleToolEvent({ type: "runtime_budget" }));
    expect(setToolActivity).toHaveBeenLastCalledWith({
      name: "agent",
      phase: "warning",
      message: "tools.activity.budget",
    });

    for (const type of ["runtime_security_block", "runtime_security_stop"]) {
      act(() => result.current.handleToolEvent({ type }));
      expect(setToolActivity).toHaveBeenLastCalledWith({
        name: "agent",
        phase: "error",
        message: "tools.activity.securityStop",
      });
    }
  });

  it("preserves cancellation and runtime completion states", () => {
    const { result, setToolActivity } = renderToolActivity();

    act(() => result.current.handleToolEvent({ type: "cancelled", name: "python" }));
    expect(setToolActivity).toHaveBeenLastCalledWith({
      name: "python",
      phase: "cancelled",
      message: "tools.activity.cancelled",
    });

    act(() => result.current.handleToolEvent({ type: "runtime_complete", status: "completed" }));
    expect(setToolActivity).toHaveBeenLastCalledWith({
      name: "agent",
      phase: "done",
      message: "tools.activity.completed",
    });

    act(() => result.current.handleToolEvent({ type: "runtime_complete", status: "stopped" }));
    expect(setToolActivity).toHaveBeenLastCalledWith({
      name: "agent",
      phase: "warning",
      message: "tools.activity.stopped",
    });
  });

  it("localizes known tool names and preserves unknown names", () => {
    const { result } = renderToolActivity();

    expect(result.current.toolActivityLabel("calculator")).toBe("tools.activity.calculator");
    expect(result.current.toolActivityLabel("web_search")).toBe("tools.activity.webSearch");
    expect(result.current.toolActivityLabel("analyze_data")).toBe("tools.activity.dataAnalysis");
    expect(result.current.toolActivityLabel("agent")).toBe("tools.activity.agent");
    expect(result.current.toolActivityLabel("python")).toBe("tools.activity.python");
    expect(result.current.toolActivityLabel("custom_tool")).toBe("custom_tool");
  });
});
