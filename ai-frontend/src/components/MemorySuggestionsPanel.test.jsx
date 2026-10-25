import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MemorySuggestionsPanel from "./MemorySuggestionsPanel";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key) => key }),
}));

describe("MemorySuggestionsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows evidence and lets the user explicitly save or dismiss a suggestion", () => {
    const suggestion = {
      content: "يفضل الشرح بالعربية مع أمثلة.",
      evidence: "أفضل الشرح بالعربية مع أمثلة.",
    };
    const onSave = vi.fn();
    const onDismiss = vi.fn();
    const onClose = vi.fn();

    render(
      <MemorySuggestionsPanel
        suggestions={[suggestion]}
        savingContent=""
        onSave={onSave}
        onDismiss={onDismiss}
        onClose={onClose}
      />
    );

    expect(screen.getByText(suggestion.content)).toBeInTheDocument();
    expect(screen.getByText(suggestion.evidence)).toBeInTheDocument();

    fireEvent.click(screen.getByText("memory.suggestSave"));
    expect(onSave).toHaveBeenCalledWith(suggestion);

    fireEvent.click(screen.getByText("memory.suggestDismiss"));
    expect(onDismiss).toHaveBeenCalledWith(suggestion);

    fireEvent.click(screen.getByText("memory.suggestClose"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("explains that no suitable suggestions were found", () => {
    render(
      <MemorySuggestionsPanel
        suggestions={[]}
        savingContent=""
        onSave={vi.fn()}
        onDismiss={vi.fn()}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText("memory.suggestNoResults")).toBeInTheDocument();
  });

  it("disables all suggestion actions while a memory is being saved", () => {
    render(
      <MemorySuggestionsPanel
        suggestions={[
          {
            content: "يفضل الشرح بالعربية.",
            evidence: "اشرح بالعربية.",
          },
        ]}
        savingContent="يفضل الشرح بالعربية."
        onSave={vi.fn()}
        onDismiss={vi.fn()}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText("memory.suggestSaving")).toBeDisabled();
    expect(screen.getByText("memory.suggestDismiss")).toBeDisabled();
  });
});
