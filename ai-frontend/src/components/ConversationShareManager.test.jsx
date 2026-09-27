import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import ConversationShareManager from "./ConversationShareManager";

const listConversationShares = vi.fn();
const revokeConversationShare = vi.fn();

vi.mock("../lib/sharedConversationsApi", () => ({
  listConversationShares: (...args) => listConversationShares(...args),
  revokeConversationShare: (...args) => revokeConversationShare(...args),
}));

vi.mock("../lib/errors", () => ({
  getErrorMessage: vi.fn((error, fallback) => error?.response?.data?.detail || fallback),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key, vars) => ({
      "sharing.managementTitle": "إدارة روابط المشاركة",
      "sharing.managementHint": "إدارة الروابط",
      "sharing.managementLoading": "جارٍ التحميل",
      "sharing.managementLoadError": "تعذر التحميل",
      "sharing.managementUpdated": "تم التحديث",
      "sharing.noActiveLinks": "لا توجد روابط",
      "sharing.activeLink": "رابط فعّال",
      "sharing.passwordProtected": "محمي بكلمة مرور",
      "sharing.expiredLink": "رابط منتهي",
      "sharing.createdAt": `أُنشئ: ${vars?.date ?? ""}`,
      "sharing.expiresAt": `ينتهي: ${vars?.date ?? ""}`,
      "sharing.accessCount": `المشاهدات: ${vars?.count ?? 0}`,
      "sharing.lastAccessedAt": `آخر مشاهدة: ${vars?.date ?? ""}`,
      "sharing.never": "بدون انتهاء",
      "sharing.revoking": "جارٍ الإلغاء",
      "sharing.revoke": "إلغاء الرابط",
      "sharing.revokeConfirm": "إلغاء الرابط؟",
      "sharing.revokeError": "تعذر الإلغاء",
    })[key] ?? key,
  }),
}));

describe("ConversationShareManager", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("يعرض الروابط الموجودة ويسمح بإلغائها", async () => {
    listConversationShares.mockResolvedValue([
      {
        id: 10,
        created_at: "2026-09-20T10:00:00Z",
        expires_at: null,
        is_expired: false,
        password_protected: true,
        access_count: 3,
        last_accessed_at: "2026-09-21T12:00:00Z",
      },
    ]);
    revokeConversationShare.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    const user = userEvent.setup();
    render(
      <ConversationShareManager
        conversationId={7}
        onClose={vi.fn()}
      />
    );

    expect(await screen.findByText("رابط فعّال")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "إلغاء الرابط" }));

    expect(revokeConversationShare).toHaveBeenCalledWith(7, 10);
  });

  it("يعرض الحالة المنتهية الصلاحية", async () => {
    listConversationShares.mockResolvedValue([
      {
        id: 11,
        created_at: "2026-09-19T10:00:00Z",
        expires_at: "2026-09-19T12:00:00Z",
        is_expired: true,
      },
    ]);

    render(
      <ConversationShareManager
        conversationId={8}
        onClose={vi.fn()}
      />
    );

    expect(await screen.findByText("رابط منتهي")).toBeInTheDocument();
  });

  it("يستخدم Global Toast عند فشل تحميل روابط المشاركة", async () => {
    listConversationShares.mockRejectedValueOnce({
      response: { data: { detail: "Access denied" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(
      <ConversationShareManager
        conversationId={7}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Access denied" &&
            event.detail?.type === "error"
        )
      ).toBe(true);
    });

    expect(screen.queryByText("Access denied")).not.toBeInTheDocument();
  });

  it("يستخدم Global Toast عند فشل إلغاء رابط المشاركة", async () => {
    listConversationShares.mockResolvedValueOnce([
      {
        id: 10,
        created_at: "2026-09-20T10:00:00Z",
        expires_at: null,
        is_expired: false,
        password_protected: false,
        access_count: 0,
        last_accessed_at: null,
      },
    ]);
    revokeConversationShare.mockRejectedValueOnce({
      response: { data: { detail: "Revoke denied" } },
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    const user = userEvent.setup();

    render(
      <ConversationShareManager
        conversationId={7}
        onClose={vi.fn()}
      />
    );

    await user.click(await screen.findByRole("button", { name: "إلغاء الرابط" }));

    await waitFor(() => {
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Revoke denied" &&
            event.detail?.type === "error"
        )
      ).toBe(true);
    });

    expect(screen.queryByText("Revoke denied")).not.toBeInTheDocument();
  });
});
