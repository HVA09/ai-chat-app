import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SidebarModern from "./SidebarModern";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key) => key }),
}));

vi.mock("./ui/Icon", () => ({
  default: () => <span aria-hidden="true" />,
}));

vi.mock("./WorkspaceSharedConversationsPanel", () => ({
  default: () => null,
}));

function renderSidebar() {
  return render(
    <SidebarModern
      conversations={[]}
      onSelectConversation={vi.fn()}
      onNewChat={vi.fn()}
    />
  );
}

describe("SidebarModern mobile navigation", () => {
  it("opens and closes in response to the global navigation events", () => {
    const { container } = renderSidebar();
    const sidebar = container.querySelector("aside.modern-sidebar");

    expect(sidebar).not.toHaveClass("modern-sidebar-open");

    act(() => {
      window.dispatchEvent(new Event("app:open-sidebar"));
    });
    expect(sidebar).toHaveClass("modern-sidebar-open");

    act(() => {
      window.dispatchEvent(new Event("app:close-sidebar"));
    });
    expect(sidebar).not.toHaveClass("modern-sidebar-open");
  });

  it("uses the translated label for both mobile close controls", () => {
    const { container } = renderSidebar();

    act(() => {
      window.dispatchEvent(new Event("app:open-sidebar"));
    });

    expect(
      container.querySelectorAll('button[aria-label="sidebar.closeNavigation"]')
    ).toHaveLength(2);
  });

});
