import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ScheduledTasksPanel from "./ScheduledTasksPanel";

const api = vi.hoisted(() => ({
  listScheduledTasks: vi.fn(),
  createScheduledTask: vi.fn(),
  updateScheduledTask: vi.fn(),
  deleteScheduledTask: vi.fn(),
  runScheduledTask: vi.fn(),
  listScheduledTaskRuns: vi.fn(),
}));

vi.mock("../lib/scheduledTasksApi", () => api);

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) =>
      ({
        "scheduledTasks.title": "المهام المجدولة",
        "scheduledTasks.description": "تشغيل تلقائي",
        "scheduledTasks.workspace": "مساحة العمل",
        "scheduledTasks.prompt": "المهمة",
        "scheduledTasks.promptPlaceholder": "اكتب المهمة",
        "scheduledTasks.frequency": "التكرار",
        "scheduledTasks.once": "مرة واحدة",
        "scheduledTasks.daily": "يومي",
        "scheduledTasks.weekly": "أسبوعي",
        "scheduledTasks.nextRun": "أول تنفيذ",
        "scheduledTasks.timezone": "المنطقة الزمنية",
        "scheduledTasks.create": "إنشاء المهمة",
        "scheduledTasks.saving": "جارٍ الحفظ...",
        "scheduledTasks.listTitle": "المهام الحالية",
        "scheduledTasks.refresh": "تحديث",
        "scheduledTasks.loading": "جارٍ التحميل...",
        "scheduledTasks.empty": "لا توجد مهام",
        "scheduledTasks.pause": "إيقاف",
        "scheduledTasks.resume": "استئناف",
        "scheduledTasks.delete": "حذف",
        "scheduledTasks.deleteConfirm": "حذف؟",
        "scheduledTasks.runNow": "تشغيل الآن",
        "scheduledTasks.running": "جارٍ التشغيل...",
        "scheduledTasks.history": "سجل التنفيذ",
        "scheduledTasks.hideHistory": "إخفاء السجل",
        "scheduledTasks.historyEmpty": "لا توجد عمليات تنفيذ بعد",
        "scheduledTasks.historyLoadError": "تعذر تحميل سجل التنفيذ",
        "scheduledTasks.runNowError": "تعذر تشغيل المهمة الآن",
        "scheduledTasks.retryError": "تعذر إعادة المحاولة",
        "scheduledTasks.retry": "إعادة المحاولة",
        "scheduledTasks.retrying": "جارٍ إعادة المحاولة...",
        "scheduledTasks.edit": "تعديل",
        "scheduledTasks.savingEdit": "جارٍ حفظ التعديل...",
        "scheduledTasks.saveEdit": "حفظ التعديل",
        "scheduledTasks.cancelEdit": "إلغاء",
        "scheduledTasks.editError": "تعذر تعديل المهمة المجدولة",
        "scheduledTasks.finishedAt": "انتهى: {{date}}",
        "scheduledTasks.conversationCreated": "تم إنشاء محادثة من هذا التنفيذ",
        "scheduledTasks.status.queued": "في الانتظار",
        "scheduledTasks.status.running": "جارٍ التنفيذ",
        "scheduledTasks.status.succeeded": "نجح",
        "scheduledTasks.status.failed": "فشل",
      })[key] ?? key,
  }),
}));

describe("ScheduledTasksPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.retryScheduledTaskRun = vi.fn().mockResolvedValue({
      id: 10,
      scheduled_task_id: 1,
      workspace_id: 7,
      prompt: "لخص الأخبار",
      status: "queued",
      started_at: null,
      finished_at: null,
      conversation_id: null,
      error: null,
      created_at: "2026-09-21T10:00:00Z",
    });
    api.listScheduledTasks.mockResolvedValue([]);
    api.listScheduledTaskRuns.mockResolvedValue([]);
    api.runScheduledTask.mockResolvedValue({
      id: 5,
      scheduled_task_id: 1,
      workspace_id: 7,
      prompt: "لخص الأخبار",
      status: "queued",
      started_at: null,
      finished_at: null,
      conversation_id: null,
      error: null,
      created_at: "2026-09-21T10:00:00Z",
    });
    api.createScheduledTask.mockResolvedValue({
      id: 1,
      workspace_id: 7,
      prompt: "لخص الأخبار",
      schedule_type: "once",
      next_run_at: "2026-09-22T10:00:00Z",
      weekday: null,
      is_active: true,
      last_run_at: null,
      last_error: null,
      created_at: "2026-09-21T10:00:00Z",
    });
  });

  it("ينشئ مهمة في مساحة العمل المحددة", async () => {
    const user = userEvent.setup();
    render(
      <ScheduledTasksPanel
        workspaces={[{ id: 7, name: "عمل" }]}
        selectedWorkspaceId={7}
        onClose={vi.fn()}
      />
    );

    await user.type(screen.getByPlaceholderText("اكتب المهمة"), "لخص الأخبار");
    await user.click(screen.getByRole("button", { name: "إنشاء المهمة" }));

    await waitFor(() =>
      expect(api.createScheduledTask).toHaveBeenCalledWith(
        expect.objectContaining({
          workspace_id: 7,
          prompt: "لخص الأخبار",
          schedule_type: "once",
          timezone_name: expect.any(String),
        })
      )
    );
  });

  it("يعرض زر إعادة المحاولة للتنفيذ الفاشل", async () => {
    const user = userEvent.setup();
    api.listScheduledTasks.mockResolvedValue([
      {
        id: 1,
        workspace_id: 7,
        prompt: "لخص الأخبار",
        schedule_type: "once",
        next_run_at: "2026-09-22T10:00:00Z",
        is_active: true,
        last_run_at: null,
        last_error: "تعذر الاتصال بالمزوّد",
      },
    ]);
    api.listScheduledTaskRuns.mockResolvedValue([
      {
        id: 9,
        scheduled_task_id: 1,
        workspace_id: 7,
        prompt: "لخص الأخبار",
        status: "failed",
        started_at: "2026-09-21T10:00:00Z",
        finished_at: "2026-09-21T10:00:05Z",
        conversation_id: null,
        error: "تعذر الاتصال بالمزوّد",
        created_at: "2026-09-21T10:00:00Z",
      },
    ]);

    render(
      <ScheduledTasksPanel
        workspaces={[{ id: 7, name: "عمل" }]}
        selectedWorkspaceId={7}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => expect(screen.getByText("لخص الأخبار")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "سجل التنفيذ" }));
    await waitFor(() => expect(screen.getByText("فشل")).toBeInTheDocument());

    expect(screen.getByRole("button", { name: "إعادة المحاولة" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "إعادة المحاولة" }));
    await waitFor(() => expect(api.retryScheduledTaskRun).toHaveBeenCalledWith(1, 9));
  });

  it("يعدل مهمة مجدولة", async () => {
    const user = userEvent.setup();
    api.listScheduledTasks.mockResolvedValue([
      {
        id: 1,
        workspace_id: 7,
        prompt: "المهمة القديمة",
        schedule_type: "once",
        next_run_at: "2026-09-22T10:00:00Z",
        is_active: true,
        last_run_at: null,
        last_error: null,
        timezone_name: "Africa/Tripoli",
      },
    ]);
    api.updateScheduledTask.mockResolvedValue({
      id: 1,
      workspace_id: 7,
      prompt: "المهمة الجديدة",
      schedule_type: "daily",
      next_run_at: "2026-09-23T10:00:00Z",
      weekday: null,
      is_active: true,
      last_run_at: null,
      last_error: null,
    });

    render(
      <ScheduledTasksPanel
        workspaces={[{ id: 7, name: "عمل" }]}
        selectedWorkspaceId={7}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => expect(screen.getByText("المهمة القديمة")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "تعديل" }));
    const promptField = screen.getByDisplayValue("المهمة القديمة");
    await user.clear(promptField);
    await user.type(promptField, "المهمة الجديدة");
    await user.click(screen.getByRole("button", { name: "حفظ التعديل" }));

    await waitFor(() =>
      expect(api.updateScheduledTask).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          prompt: "المهمة الجديدة",
          schedule_type: "once",
        })
      )
    );
  });

  it("يشغّل المهمة الآن ويحمّل سجل التنفيذ", async () => {
    const user = userEvent.setup();
    api.listScheduledTasks.mockResolvedValue([
      {
        id: 1,
        workspace_id: 7,
        prompt: "لخص الأخبار",
        schedule_type: "once",
        next_run_at: "2026-09-22T10:00:00Z",
        is_active: true,
        last_run_at: null,
        last_error: null,
      },
    ]);
    api.listScheduledTaskRuns.mockResolvedValue([
      {
        id: 5,
        scheduled_task_id: 1,
        workspace_id: 7,
        prompt: "لخص الأخبار",
        status: "succeeded",
        started_at: "2026-09-21T10:00:00Z",
        finished_at: "2026-09-21T10:00:02Z",
        conversation_id: 44,
        error: null,
        created_at: "2026-09-21T10:00:00Z",
      },
    ]);

    render(
      <ScheduledTasksPanel
        workspaces={[{ id: 7, name: "عمل" }]}
        selectedWorkspaceId={7}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => expect(screen.getByText("لخص الأخبار")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "تشغيل الآن" }));

    await waitFor(() => expect(api.runScheduledTask).toHaveBeenCalledWith(1));
    await waitFor(() => expect(screen.getByRole("button", { name: "إخفاء السجل" })).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("نجح")).toBeInTheDocument());
    expect(screen.getByText("تم إنشاء محادثة من هذا التنفيذ")).toBeInTheDocument();
  });
});
