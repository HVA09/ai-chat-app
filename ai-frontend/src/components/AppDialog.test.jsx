import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
  delete document.body.dataset.confirm;
  renderHarness();
  fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

  const dialog = screen.getByRole("dialog");
  fireEvent.click(within(dialog).getByRole("button", { name: /تأكيد|Confirm/ }));

  await waitFor(() => expect(document.body.dataset.confirm).toBe("true"));
});

test("resolves prompt dialog from entered value", async () => {
  delete document.body.dataset.prompt;
  renderHarness();
  fireEvent.click(screen.getByRole("button", { name: "Prompt" }));

  const dialog = screen.getByRole("dialog");
  const input = within(dialog).getByRole("textbox");
  fireEvent.change(input, { target: { value: "Project Alpha" } });
  fireEvent.click(within(dialog).getByRole("button", { name: /حفظ|Save/ }));

  await waitFor(() => expect(document.body.dataset.prompt).toBe("Project Alpha"));
});
