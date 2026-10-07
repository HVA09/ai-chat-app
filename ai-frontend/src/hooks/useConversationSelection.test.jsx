import { renderHook, act } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useState } from "react";
import useConversationSelection from "./useConversationSelection";

function useTestSelection(initial = []) {
  const [selectedConversationIds, setSelectedConversationIds] = useState(initial);
  const selection = useConversationSelection({ setSelectedConversationIds });
  return { selectedConversationIds, ...selection };
}

describe("useConversationSelection", () => {
  it("toggles an individual conversation", () => {
    const { result } = renderHook(() => useTestSelection());

    act(() => result.current.toggleConversationSelection("a"));
    expect(result.current.selectedConversationIds).toEqual(["a"]);

    act(() => result.current.toggleConversationSelection("a"));
    expect(result.current.selectedConversationIds).toEqual([]);
  });

  it("selects and clears all visible conversations without duplicates", () => {
    const { result } = renderHook(() => useTestSelection(["a"]));

    act(() => result.current.toggleSelectAllVisibleConversations(["a", "b", "b"]));
    expect(result.current.selectedConversationIds).toEqual(["a", "b"]);

    act(() => result.current.toggleSelectAllVisibleConversations(["a", "b"]));
    expect(result.current.selectedConversationIds).toEqual([]);
  });

  it("keeps non-visible selections when clearing a visible selection set", () => {
    const { result } = renderHook(() => useTestSelection(["x", "a"]));

    act(() => result.current.toggleSelectAllVisibleConversations(["a", "b"]));
    expect(result.current.selectedConversationIds).toEqual(["x", "a", "b"]);

    act(() => result.current.toggleSelectAllVisibleConversations(["a", "b"]));
    expect(result.current.selectedConversationIds).toEqual(["x"]);
  });

  it("clears all selected conversations", () => {
    const { result } = renderHook(() => useTestSelection(["a", "b"]));

    act(() => result.current.clearSelectedConversations());
    expect(result.current.selectedConversationIds).toEqual([]);
  });
});
