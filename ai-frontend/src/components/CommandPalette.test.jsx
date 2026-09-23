import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, afterEach } from "vitest";
import CommandPalette from "./CommandPalette";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => ({
      "commandPalette.title": "لوحة الأوامر",
      "commandPalette.placeholder": "ابحث عن أمر...",
      "commandPalette.searchLabel": "البحث في الأوامر",
      "commandPalette.noResults": "لا توجد نتائج",
      "commandPalette.hint": "اختصار لوحة الأوامر",
    })[key] ?? key,
  }),
}));

const actions = [
  { id: "new", label: "محادثة جديدة", keywords: ["new", "chat"], onSelect: vi.fn() },
  { id: "files", label: "الملفات", keywords: ["files"], onSelect: vi.fn() },
];

afterEach(() => {
  vi.restoreAllMocks();
});

describe("CommandPalette", () => {
  it("لا يعرض اللوحة عندما تكون مغلقة", () => {
    render(<CommandPalette open={false} onClose={vi.fn()} actions={actions} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("يعرض الأوامر ويختار الأمر", async () => {
    const user = userEvent.setup();
    render(<CommandPalette open onClose={vi.fn()} actions={actions} />);

    await user.click(screen.getByRole("button", { name: "محادثة جديدة" }));

    expect(actions[0].onSelect).toHaveBeenCalled();
  });

  it("يبحث في الأوامر", async () => {
    const user = userEvent.setup();
    render(<CommandPalette open onClose={vi.fn()} actions={actions} />);

    await user.type(screen.getByRole("searchbox"), "files");

    expect(screen.getByRole("button", { name: "الملفات" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "محادثة جديدة" })).not.toBeInTheDocument();
  });

  it("يغلق عند Escape", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<CommandPalette open onClose={onClose} actions={actions} />);

    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalled();
  });
});
