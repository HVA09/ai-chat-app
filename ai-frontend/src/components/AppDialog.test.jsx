import { fireEvent, render, screen } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import i18n from "../i18n";
import { AppDialogProvider, useAppDialog } from "./AppDialog";

function TestHarness() {
  const { confirm, prompt } = useAppDialog();

  return (
    <>
      <button onClick={async () => document.body.dataset.confirm = String(await confirm({ message: "Delete?" }))}>
        Confirm
      </button>
      <button onClick={async () => document.body.dataset.prompt = String(await prompt({ message: "Name?" }))}>
        Prompt
      </button>
    </>
  );
}

function renderHarness() {
  return render(
    <I18nextProvider i18n={i18n}>
      <AppDialogProvider>
        <TestHarness />
      </AppDialogProvider>
    </I18nextProvider>
  );
}

test("resolves confirm dialog", async () => {
  renderHarness();
  fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  fireEvent.click(screen.getAllByRole("button", { name: /تأكيد|Confirm/ })[1]);
  expect(document.body.dataset.confirm).toBe("true");
});

test("resolves prompt dialog from entered value", async () => {
  renderHarness();
  fireEvent.click(screen.getByRole("button", { name: "Prompt" }));
  const input = screen.getByRole("textbox");
  fireEvent.change(input, { target: { value: "Project Alpha" } });
  fireEvent.click(screen.getByRole("button", { name: /حفظ|Save/ }));
  expect(document.body.dataset.prompt).toBe("Project Alpha");
});
