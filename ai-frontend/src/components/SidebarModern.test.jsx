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

describe("SidebarModern conversation actions", () => {
  const sampleConversation = {
    id: 101,
    title: "Example conversation",
    folder_id: null,
    project_id: null,
    tags: [],
    is_pinned: false,
  };

  it("opens the action menu when the more button is tapped", () => {
    const { container } = renderSidebar({
      conversations: [sampleConversation],
      folders: [{ id: 23, name: "Folder Alpha" }],
      projects: [{ id: 34, name: "Project Alpha" }],
      tags: [{ id: 45, name: "Tag Alpha", color: "#123456" }],
    });

    fireEvent.click(screen.getByRole("button", { name: "header.more" }));

    expect(container.querySelector(".modern-conversation-item")).toHaveClass("menu-open");
    expect(container.querySelector(".modern-conversation-menu")).toBeInTheDocument();
  });

  it("closes the action menu on Escape and restores focus to its trigger", () => {
    renderSidebar({ conversations: [sampleConversation] });
    const trigger = screen.getByRole("button", { name: "header.more" });

    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("group", { name: "header.more" })).not.toBeInTheDocument();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(trigger).toHaveFocus();
  });

  it("closes the action menu when the user taps outside it", () => {
    renderSidebar({ conversations: [sampleConversation] });
    fireEvent.click(screen.getByRole("button", { name: "header.more" }));

    fireEvent.pointerDown(document.body);

    expect(screen.queryByRole("group", { name: "header.more" })).not.toBeInTheDocument();
  });

  it("passes selected folder and project values to their handlers", () => {
    const onMoveConversationToFolder = vi.fn();
    const onMoveConversationToProject = vi.fn();
    renderSidebar({
      conversations: [sampleConversation],
      folders: [{ id: 23, name: "Folder Alpha" }],
      projects: [{ id: 34, name: "Project Alpha" }],
      onMoveConversationToFolder,
      onMoveConversationToProject,
    });

    fireEvent.click(screen.getByRole("button", { name: "header.more" }));
    fireEvent.change(screen.getByRole("combobox", { name: "sidebar.moveFolderTitle" }), {
      target: { value: "23" },
    });
    expect(onMoveConversationToFolder).toHaveBeenCalledWith(101, "23");

    fireEvent.click(screen.getByRole("button", { name: "header.more" }));
    fireEvent.change(screen.getByRole("combobox", { name: "sidebar.moveProjectTitle" }), {
      target: { value: "34" },
    });
    expect(onMoveConversationToProject).toHaveBeenCalledWith(101, "34");
  });

  it("adds a conversation tag through the action menu", () => {
    const onSetConversationTags = vi.fn();
    const { container } = renderSidebar({
      conversations: [sampleConversation],
      tags: [{ id: 45, name: "Tag Alpha", color: "#123456" }],
      onSetConversationTags,
    });

    fireEvent.click(screen.getByRole("button", { name: "header.more" }));
    fireEvent.click(container.querySelector(".modern-conversation-tags summary"));
    fireEvent.click(screen.getByRole("checkbox", { name: "Tag Alpha" }));

    expect(onSetConversationTags).toHaveBeenCalledWith(101, [45]);
  });

  it("moves a conversation to trash from the regular list without permanent deletion", () => {
    const onToggleTrashConversation = vi.fn();
    const onDeleteConversation = vi.fn();
    const { container } = renderSidebar({
      conversations: [sampleConversation],
      onToggleTrashConversation,
      onDeleteConversation,
    });

    fireEvent.click(screen.getByRole("button", { name: "header.more" }));
    fireEvent.click(container.querySelector(".modern-conversation-menu .modern-menu-delete"));

    expect(onToggleTrashConversation).toHaveBeenCalledWith(101);
    expect(onDeleteConversation).not.toHaveBeenCalled();
  });

  it("does not permanently delete a trashed conversation when confirmation is cancelled", () => {
    const onDeleteConversation = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    renderSidebar({
      conversations: [sampleConversation],
      showTrash: true,
      onDeleteConversation,
    });

    fireEvent.click(screen.getByRole("button", { name: "header.more" }));
    fireEvent.click(screen.getByRole("button", { name: "sidebar.deleteTitle" }));

    expect(confirmSpy).toHaveBeenCalled();
    expect(onDeleteConversation).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("permanently deletes a trashed conversation only after confirmation", () => {
    const onDeleteConversation = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderSidebar({
      conversations: [sampleConversation],
      showTrash: true,
      onDeleteConversation,
    });

    fireEvent.click(screen.getByRole("button", { name: "header.more" }));
    fireEvent.click(screen.getByRole("button", { name: "sidebar.deleteTitle" }));

    expect(confirmSpy).toHaveBeenCalled();
    expect(onDeleteConversation).toHaveBeenCalledWith(101);
    confirmSpy.mockRestore();
  });

  it("closes the action menu without opening a conversation from the trash", () => {
    const onSelectConversation = vi.fn();
    const { container } = renderSidebar({
      conversations: [sampleConversation],
      showTrash: true,
      onSelectConversation,
    });

    fireEvent.click(screen.getByRole("button", { name: "header.more" }));
    fireEvent.click(screen.getByRole("button", { name: /Example conversation/ }));

    expect(onSelectConversation).not.toHaveBeenCalled();
    expect(container.querySelector(".modern-conversation-item")).not.toHaveClass("menu-open");
  });

  it("limits the action menu to permanent deletion while in the trash", () => {
    const { container } = renderSidebar({
      conversations: [sampleConversation],
      showTrash: true,
    });

    fireEvent.click(screen.getByRole("button", { name: "header.more" }));

    expect(container.querySelector(".modern-conversation-menu")).toBeInTheDocument();
    expect(container.querySelector(".modern-conversation-menu select")).toBeNull();
    expect(screen.getByRole("button", { name: "sidebar.deleteTitle" })).toBeInTheDocument();
  });
});

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
