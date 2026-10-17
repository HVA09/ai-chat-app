import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useCommandPaletteActions from "./useCommandPaletteActions";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => ({
      "commandPalette.actions.newChat": "محادثة جديدة",
      "commandPalette.actions.backToChats": "العودة للمحادثات",
      "commandPalette.actions.archived": "المؤرشفة",
      "commandPalette.actions.trash": "سلة المحذوفات",
      "commandPalette.actions.files": "الملفات",
      "commandPalette.actions.account": "الحساب",
      "commandPalette.actions.billing": "الاشتراك",
      "commandPalette.actions.newFolder": "مجلد جديد",
      "commandPalette.actions.newProject": "مشروع جديد",
      "commandPalette.actions.newAssistant": "مساعد جديد",
      "commandPalette.actions.scheduledTasks": "المهام المجدولة",
      "commandPalette.actions.admin": "الإدارة",
    }[key] ?? key),
  }),
}));

function createProps(overrides = {}) {
  return {
    startNewChat: vi.fn(),
    showArchivedConversations: false,
    setShowArchivedConversations: vi.fn(),
    showTrashConversations: false,
    setShowTrashConversations: vi.fn(),
    selectedFolderId: 5,
    selectedWorkspaceId: 8,
    selectedProjectId: 11,
    conversationSearch: "invoice",
    setSelectedFolderId: vi.fn(),
    setSelectedConversationIds: vi.fn(),
    refreshConversations: vi.fn(),
    setShowFiles: vi.fn(),
    setShowAccountSettings: vi.fn(),
    setShowBilling: vi.fn(),
    handleCreateFolder: vi.fn(),
    handleCreateProject: vi.fn(),
    openCreateAssistantEditor: vi.fn(),
    setShowScheduledTasks: vi.fn(),
    currentUserRole: "user",
    setShowAdmin: vi.fn(),
    ...overrides,
  };
}

describe("useCommandPaletteActions", () => {
  it("provides the standard actions and hides administration from non-admin users", () => {
    const { result } = renderHook(() => useCommandPaletteActions(createProps()));

    expect(result.current.map((action) => action.id)).toEqual([
      "new-chat",
      "archived",
      "trash",
      "files",
      "account",
      "billing",
      "new-folder",
      "new-project",
      "new-assistant",
      "scheduled-tasks",
    ]);
    expect(result.current.find((action) => action.id === "new-chat").label).toBe("محادثة جديدة");
  });

  it("includes the administration action only for administrators", () => {
    const props = createProps({ currentUserRole: "admin" });
    const { result } = renderHook(() => useCommandPaletteActions(props));
    const adminAction = result.current.find((action) => action.id === "admin");

    expect(adminAction).toBeDefined();
    adminAction.onSelect();
    expect(props.setShowAdmin).toHaveBeenCalledWith(true);
    expect(result.current.length).toBe(11);
  });

  it("switches to archived conversations with the existing filters", () => {
    const props = createProps({ showTrashConversations: true });
    const { result } = renderHook(() => useCommandPaletteActions(props));

    result.current.find((action) => action.id === "archived").onSelect();

    expect(props.setShowArchivedConversations).toHaveBeenCalledWith(true);
    expect(props.setShowTrashConversations).toHaveBeenCalledWith(false);
    expect(props.refreshConversations).toHaveBeenCalledWith(
      true,
      5,
      8,
      11,
      "invoice",
      false
    );
    expect(props.startNewChat).toHaveBeenCalledOnce();
  });

  it("switches to the trash view and clears folder and conversation selection", () => {
    const props = createProps({ showArchivedConversations: true });
    const { result } = renderHook(() => useCommandPaletteActions(props));

    result.current.find((action) => action.id === "trash").onSelect();

    expect(props.setShowTrashConversations).toHaveBeenCalledWith(true);
    expect(props.setShowArchivedConversations).toHaveBeenCalledWith(false);
    expect(props.setSelectedFolderId).toHaveBeenCalledWith(null);
    expect(props.setSelectedConversationIds).toHaveBeenCalledWith([]);
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false,
      null,
      8,
      null,
      "invoice",
      true
    );
    expect(props.startNewChat).toHaveBeenCalledOnce();
  });

  it("delegates navigation actions to their existing handlers", () => {
    const props = createProps();
    const { result } = renderHook(() => useCommandPaletteActions(props));

    result.current.find((action) => action.id === "files").onSelect();
    result.current.find((action) => action.id === "account").onSelect();
    result.current.find((action) => action.id === "billing").onSelect();
    result.current.find((action) => action.id === "new-folder").onSelect();
    result.current.find((action) => action.id === "new-project").onSelect();
    result.current.find((action) => action.id === "new-assistant").onSelect();
    result.current.find((action) => action.id === "scheduled-tasks").onSelect();

    expect(props.setShowFiles).toHaveBeenCalledWith(true);
    expect(props.setShowAccountSettings).toHaveBeenCalledWith(true);
    expect(props.setShowBilling).toHaveBeenCalledWith(true);
    expect(props.handleCreateFolder).toHaveBeenCalledOnce();
    expect(props.handleCreateProject).toHaveBeenCalledOnce();
    expect(props.openCreateAssistantEditor).toHaveBeenCalledOnce();
    expect(props.setShowScheduledTasks).toHaveBeenCalledWith(true);
  });
});
