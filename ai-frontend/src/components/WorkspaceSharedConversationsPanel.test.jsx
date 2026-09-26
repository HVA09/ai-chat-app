import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import WorkspaceSharedConversationsPanel from "./WorkspaceSharedConversationsPanel";

const listWorkspaceSharedConversations = vi.fn();
const duplicateWorkspaceSharedConversation = vi.fn();

vi.mock("../lib/workspaceConversationSharesApi", () => ({
  listWorkspaceSharedConversations: (...args) =>
    listWorkspaceSharedConversations(...args),
  duplicateWorkspaceSharedConversation: (...args) =>
    duplicateWorkspaceSharedConversation(...args),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) =>
      ({
        "workspaceSharing.title": "محادثات مساحة العمل المشتركة",
        "workspaceSharing.empty": "لا توجد محادثات مشتركة",
        "workspaceSharing.duplicateButton": "نسخ إلى محادثاتي",
      })[key] ?? key,
  }),
}));

describe("WorkspaceSharedConversationsPanel", () => {
  beforeEach(() => {
    listWorkspaceSharedConversations.mockReset();
    duplicateWorkspaceSharedConversation.mockReset();
  });

  it("يعرض المحادثات المشتركة ويسمح بنسخ واحدة منها", async () => {
    listWorkspaceSharedConversations.mockResolvedValue([
      {
        conversation_id: 42,
        workspace_id: 7,
        title: "بحث مشترك",
        updated_at: "2026-09-23T00:00:00Z",
        owner_email: "owner@example.com",
        shared_by_email: "owner@example.com",
        shared_at: "2026-09-23T00:00:00Z",
      },
    ]);
    duplicateWorkspaceSharedConversation.mockResolvedValue({ id: 99 });

    const onDuplicatedConversation = vi.fn();
    const user = userEvent.setup();

    render(
      <WorkspaceSharedConversationsPanel
        workspaceId={7}
        onOpenConversation={vi.fn()}
        onDuplicatedConversation={onDuplicatedConversation}
      />
    );

    expect(
      await screen.findByRole("button", { name: /بحث مشترك/ })
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "نسخ إلى محادثاتي" }));

    expect(duplicateWorkspaceSharedConversation).toHaveBeenCalledWith(7, 42);
    expect(onDuplicatedConversation).toHaveBeenCalledWith(99);
  });
  it("يستخدم Global Toast عند فشل تحميل المحادثات المشتركة", async () => {
    listWorkspaceSharedConversations.mockRejectedValue({
      response: { data: { detail: "فشل التحميل" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(
      <WorkspaceSharedConversationsPanel
        workspaceId={7}
        onOpenConversation={vi.fn()}
      />
    );

    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(dispatchSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "app:toast",
        detail: { message: "فشل التحميل", type: "error" },
      })
    );

    dispatchSpy.mockRestore();
  });

});
