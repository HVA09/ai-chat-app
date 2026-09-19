import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import AssistantEditor from "./AssistantEditor";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => ({
      "assistantEditor.createTitle": "Create assistant",
      "assistantEditor.editTitle": "Edit assistant",
      "assistantEditor.description": "Create a reusable assistant profile.",
      "assistantEditor.close": "Close",
      "assistantEditor.name": "Name",
      "assistantEditor.descriptionLabel": "Description",
      "assistantEditor.instructions": "Instructions",
      "assistantEditor.instructionsPlaceholder": "How should the assistant behave?",
      "assistantEditor.cancel": "Cancel",
      "assistantEditor.saving": "Saving...",
      "assistantEditor.save": "Save",
    }[key] ?? key),
  }),
}));

describe("AssistantEditor", () => {
  it("submits edited assistant data", () => {
    const onSave = vi.fn();
    render(
      <AssistantEditor
        assistant={{ id: 3, name: "Tutor", description: "A2", instructions: "Explain simply." }}
        onSave={onSave}
        onClose={() => {}}
      />
    );

    fireEvent.change(screen.getByDisplayValue("Tutor"), { target: { value: "English Tutor" } });
    fireEvent.change(screen.getByDisplayValue("Explain simply."), {
      target: { value: "Explain clearly with examples." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(onSave).toHaveBeenCalledWith({
      name: "English Tutor",
      description: "A2",
      instructions: "Explain clearly with examples.",
    });
  });
});
