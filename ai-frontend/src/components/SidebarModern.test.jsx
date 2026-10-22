import { act, fireEvent, render, screen } from "@testing-library/react";
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

function renderSidebar(overrides = {}) {
  return render(
    <SidebarModern
      conversations={[]}
      onSelectConversation={vi.fn()}
      onNewChat={vi.fn()}
      {...overrides}
    />
  );
}

function openMobileLibrarySection(container, sectionName) {
  const sidebar = container.querySelector("aside.modern-sidebar");
  act(() => {
    window.dispatchEvent(new Event("app:open-sidebar"));
  });
  fireEvent.click(screen.getByRole("button", { name: sectionName }));
  expect(sidebar).toHaveClass("modern-sidebar-open");
  return sidebar;
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


  it("closes mobile navigation after selecting a project", () => {
    const onSelectProject = vi.fn();
    const { container } = renderSidebar({
      projects: [{ id: 12, name: "Project Alpha", owner_id: 99 }],
      onSelectProject,
    });
    const sidebar = openMobileLibrarySection(container, "sidebar.projectsTitle");

    fireEvent.click(screen.getByRole("button", { name: "Project Alpha" }));

    expect(onSelectProject).toHaveBeenCalledWith(12);
    expect(sidebar).not.toHaveClass("modern-sidebar-open");
  });

  it("closes mobile navigation after selecting a folder", () => {
    const onSelectFolder = vi.fn();
    const { container } = renderSidebar({
      folders: [{ id: 23, name: "Folder Alpha", color: "slate" }],
      onSelectFolder,
    });
    const sidebar = openMobileLibrarySection(container, "sidebar.foldersTitle");

    fireEvent.click(screen.getByRole("button", { name: "Folder Alpha" }));

    expect(onSelectFolder).toHaveBeenCalledWith(23);
    expect(sidebar).not.toHaveClass("modern-sidebar-open");
  });

  it("closes mobile navigation after selecting an assistant", () => {
    const onSelectAssistant = vi.fn();
    const { container } = renderSidebar({
      assistants: [{ id: 34, name: "Assistant Alpha" }],
      onSelectAssistant,
    });
    const sidebar = openMobileLibrarySection(container, "sidebar.assistantsTitle");

    fireEvent.click(screen.getByRole("button", { name: "Assistant Alpha" }));

    expect(onSelectAssistant).toHaveBeenCalledWith(34);
    expect(sidebar).not.toHaveClass("modern-sidebar-open");
  });

  it("closes mobile navigation after selecting a tag", () => {
    const onSelectTag = vi.fn();
    const { container } = renderSidebar({
      tags: [{ id: 45, name: "Tag Alpha", color: "#123456" }],
      onSelectTag,
    });
    const sidebar = openMobileLibrarySection(container, "sidebar.tagsTitle");

    fireEvent.click(screen.getByRole("button", { name: "Tag Alpha" }));

    expect(onSelectTag).toHaveBeenCalledWith(45);
    expect(sidebar).not.toHaveClass("modern-sidebar-open");
  });

  it("closes mobile navigation after opening a bookmarked conversation", () => {
    const onOpenBookmarkedMessage = vi.fn();
    const { container } = renderSidebar({
      bookmarkedMessages: [{ message_id: 56, conversation_title: "Bookmarked chat" }],
      onOpenBookmarkedMessage,
    });
    const sidebar = openMobileLibrarySection(container, "bookmarks.title");

    fireEvent.click(screen.getByRole("button", { name: "Bookmarked chat" }));

    expect(onOpenBookmarkedMessage).toHaveBeenCalledWith(
      expect.objectContaining({ message_id: 56 })
    );
    expect(sidebar).not.toHaveClass("modern-sidebar-open");
  });

  it("closes mobile navigation after using a saved prompt", () => {
    const onUseSavedPrompt = vi.fn();
    const { container } = renderSidebar({
      savedPrompts: [{ id: 67, name: "Translate prompt", content: "Translate this text" }],
      onUseSavedPrompt,
    });
    const sidebar = openMobileLibrarySection(container, "sidebar.savedPromptsTitle");

    fireEvent.click(screen.getByRole("button", { name: "Translate prompt" }));

    expect(onUseSavedPrompt).toHaveBeenCalledWith("Translate this text");
    expect(sidebar).not.toHaveClass("modern-sidebar-open");
  });

});
