import { afterEach, describe, expect, it } from "vitest";
import {
  clearChatDraft,
  loadChatDraft,
  saveChatDraft,
} from "./chatDrafts";

describe("chat drafts", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("saves and restores a draft per user and conversation", () => {
    saveChatDraft(7, 42, "رسالة غير مكتملة");
    expect(loadChatDraft(7, 42)).toBe("رسالة غير مكتملة");
    expect(loadChatDraft(8, 42)).toBe("");
    expect(loadChatDraft(7, 43)).toBe("");
  });

  it("keeps new-chat drafts separate from conversation drafts", () => {
    saveChatDraft(7, null, "مسودة جديدة");
    saveChatDraft(7, 42, "مسودة محادثة");
    expect(loadChatDraft(7, null)).toBe("مسودة جديدة");
    expect(loadChatDraft(7, 42)).toBe("مسودة محادثة");
  });

  it("clears blank drafts instead of storing them", () => {
    saveChatDraft(7, 42, "  ");
    expect(loadChatDraft(7, 42)).toBe("");
    saveChatDraft(7, 42, "hello");
    saveChatDraft(7, 42, "");
    expect(loadChatDraft(7, 42)).toBe("");
  });

  it("can clear one draft without affecting another conversation", () => {
    saveChatDraft(7, 41, "first");
    saveChatDraft(7, 42, "second");
    clearChatDraft(7, 41);
    expect(loadChatDraft(7, 41)).toBe("");
    expect(loadChatDraft(7, 42)).toBe("second");
  });
});
