import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import SidebarModern from "./components/SidebarModern";
import CommandPalette from "./components/CommandPalette";
import ChatHeaderModern from "./components/ChatHeaderModern";
import ChatMessage from "./components/ChatMessage";
import ChatComposer from "./components/ChatComposer";
import ModelCompareDialog from "./components/ModelCompareDialog";
import WorkspaceConversationCommentsPanel from "./components/WorkspaceConversationCommentsPanel";
import AssistantEditor from "./components/AssistantEditor";
import ProjectEditor from "./components/ProjectEditor";
import OnboardingModal from "./components/OnboardingModal";
import AuthForm from "./components/AuthForm";
import Toast from "./components/Toast";
import useDirection from "./hooks/useDirection";
import useSavedPrompts from "./hooks/useSavedPrompts";
import useNotifications from "./hooks/useNotifications";
import useBookmarks from "./hooks/useBookmarks";
import useMemories from "./hooks/useMemories";
import useAiModels from "./hooks/useAiModels";
import useNotificationPreferences from "./hooks/useNotificationPreferences";
import useConversationPreferences from "./hooks/useConversationPreferences";
import useChatDraft from "./hooks/useChatDraft";
import useChatAttachments from "./hooks/useChatAttachments";
import useConversationList from "./hooks/useConversationList";
import useOpenConversation from "./hooks/useOpenConversation";
import useStartNewChat from "./hooks/useStartNewChat";
import useRegenerateLastResponse from "./hooks/useRegenerateLastResponse";
import useConversationMetadata from "./hooks/useConversationMetadata";
import useMessageEditing from "./hooks/useMessageEditing";
import useConversationBulkActions from "./hooks/useConversationBulkActions";
import useConversationSelection from "./hooks/useConversationSelection";
import useConversationItemActions from "./hooks/useConversationItemActions";
import { streamChatMessage, streamEditMessage, setMessageFeedback, analyzeImage, compareChatModels } from "./lib/chatApi";
import api, { restoreSession } from "./lib/api";
import { createConversationShare } from "./lib/sharedConversationsApi";
import {
  shareConversationWithWorkspace,
  unshareConversationFromWorkspace,
  getWorkspaceSharedConversation,
} from "./lib/workspaceConversationSharesApi";

// مُحمَّلة عند الحاجة فقط (lazy) — كل وحدة تصير ملف منفصل (code splitting)،
// يقلّل حجم الحزمة الأولى اللي يحمّلها أي زائر
const VerifyEmailPage = lazy(() => import("./components/VerifyEmailPage"));
const ResetPasswordPage = lazy(() => import("./components/ResetPasswordPage"));
const AccountSettings = lazy(() => import("./components/AccountSettings"));
const FilesPanel = lazy(() => import("./components/FilesPanel"));
const AdminDashboard = lazy(() => import("./components/AdminDashboard"));
const BillingPanel = lazy(() => import("./components/BillingPanel"));
const ScheduledTasksPanel = lazy(() => import("./components/ScheduledTasksPanel"));
const BillingSuccessPage = lazy(() => import("./components/BillingSuccessPage"));
const BillingCancelPage = lazy(() => import("./components/BillingCancelPage"));
import TermsPage from "./components/TermsPage";
import PrivacyPage from "./components/PrivacyPage";
import PricingPage from "./components/PricingPage";
const PublicAssistantPage = lazy(() => import("./components/PublicAssistantPage"));

const SharedConversationPage = lazy(() => import("./components/SharedConversationPage"));
const WorkspaceMembersPanel = lazy(() => import("./components/WorkspaceMembersPanel"));
const WorkspaceInvitePage = lazy(() => import("./components/WorkspaceInvitePage"));
const ConversationShareManager = lazy(() => import("./components/ConversationShareManager"));
import {
  getConversation,
  deleteConversation,
  toggleArchiveConversation,
  toggleTrashConversation,
  moveConversationToFolder,
  duplicateConversation,
  branchConversation,
  exportConversation,
  importConversation,
  importConversations,
  summarizeConversation,
  generateConversationTitle,
} from "./lib/conversationsApi";
import {
  listFolders,
  createFolder,
  renameFolder,
  deleteFolder,
  moveFolder,
} from "./lib/foldersApi";
import {
  listProjects,
  createProject,
  updateProject,
  deleteProject,
  moveConversationToProject,
  exportProject,
  importProject,
} from "./lib/projectsApi";
import {
  listWorkspaces,
  createWorkspace,
  renameWorkspace,
} from "./lib/workspacesApi";
import {
  listAssistants,
  listWorkspaceSharedAssistants,
  createAssistant,
  updateAssistant,
  deleteAssistant,
  shareAssistantWithWorkspace,
  unshareAssistantFromWorkspace,
} from "./lib/assistantsApi";
import {
  listTags,
  createTag,
  updateTag,
  deleteTag,
  setConversationTags,
} from "./lib/tagsApi";
import { getErrorMessage } from "./lib/errors";
import { clearChatDraft } from "./lib/chatDrafts";
import { getCurrentUser } from "./lib/usersApi";
import { listProjectMembers } from "./lib/projectMembersApi";
import "./i18n";

// دالة بدل ثابت — لازم نستدعيها بعد ما يصير عندنا t() جوا المكوّن عشان رسالة
// الترحيب تتبدّل مع تبديل اللغة
function getWelcomeMessage(t) {
  return { role: "assistant", text: t("app.welcomeMessage"), time: t("app.now") };
}

function PageLoadingFallback() {
  return (
    <div className="flex h-full items-center justify-center bg-slate-50">
      <p className="text-sm text-slate-400">...</p>
    </div>
  );
}

function ModalLoadingFallback() {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <p className="text-sm text-white">...</p>
    </div>
  );
}

export default function App() {
  const { i18n, t } = useTranslation();
  const [authed, setAuthed] = useState(false);
  const [sessionChecking, setSessionChecking] = useState(true);
  const normalizedPath = window.location.pathname.replace(/\/+$/, "") || "/";
  const [lang, setLang] = useState("ar");
  const [messages, setMessages] = useState(() => [getWelcomeMessage(t)]);
  const [conversationId, setConversationId] = useState(null);
  const [activeConversationTitle, setActiveConversationTitle] = useState("");
  const [selectedConversationIds, setSelectedConversationIds] = useState([]);
  const [conversationSearch, setConversationSearch] = useState("");
  const [showArchivedConversations, setShowArchivedConversations] = useState(false);
  const [showTrashConversations, setShowTrashConversations] = useState(false);
  const [folders, setFolders] = useState([]);
  const [selectedFolderId, setSelectedFolderId] = useState(null);
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [tags, setTags] = useState([]);
  const [selectedTagId, setSelectedTagId] = useState(null);
  const [workspaces, setWorkspaces] = useState([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(null);
  const [assistants, setAssistants] = useState([]);
  const [selectedAssistantId, setSelectedAssistantId] = useState(null);
  const [showAssistantEditor, setShowAssistantEditor] = useState(false);
  const [editingAssistantId, setEditingAssistantId] = useState(null);
  const [showProjectEditor, setShowProjectEditor] = useState(false);
  const [editingProjectId, setEditingProjectId] = useState(null);
  const [projectMemberRoles, setProjectMemberRoles] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null); // { message, type }
  const [currentUser, setCurrentUser] = useState(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showAccountSettings, setShowAccountSettings] = useState(false);
  const [showModelCompare, setShowModelCompare] = useState(false);
  const [showFiles, setShowFiles] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [showBilling, setShowBilling] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [showScheduledTasks, setShowScheduledTasks] = useState(false);
  const [showWorkspaceMembers, setShowWorkspaceMembers] = useState(false);
  const [showShareManager, setShowShareManager] = useState(false);
  const [workspaceShare, setWorkspaceShare] = useState(null);
  const [readOnlyConversation, setReadOnlyConversation] = useState(false);
  const [showWorkspaceComments, setShowWorkspaceComments] = useState(false);
  const [conversationSummary, setConversationSummary] = useState(null);
  const [conversationSummaryUpdatedAt, setConversationSummaryUpdatedAt] = useState(null);
  const [conversationBranches, setConversationBranches] = useState([]);
  const [parentConversationId, setParentConversationId] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [titleLoading, setTitleLoading] = useState(false);
  const {
    savedPrompts,
    resetSavedPrompts,
    refreshSavedPrompts,
    handleCreateSavedPrompt,
    handleRenameSavedPrompt,
    handleDeleteSavedPrompt,
  } = useSavedPrompts({ setToast });

  useEffect(() => {
    const project = projects.find(
      (item) => Number(item.id) === Number(selectedProjectId)
    );
    const workspaceRole = workspaces.find(
      (workspace) => workspace.id === selectedWorkspaceId
    )?.role;

    if (!project || currentUser?.id == null) return;

    if (
      Number(project.owner_id) === Number(currentUser.id) ||
      ["owner", "admin"].includes(workspaceRole)
    ) {
      setProjectMemberRoles((current) => ({
        ...current,
        [project.id]: "manager",
      }));
      return;
    }

    let cancelled = false;
    listProjectMembers(project.id)
      .then((members) => {
        if (cancelled) return;
        const membership = members.find(
          (member) => Number(member.user_id) === Number(currentUser.id)
        );
        setProjectMemberRoles((current) => ({
          ...current,
          [project.id]: membership?.role ?? null,
        }));
      })
      .catch(() => {
        if (!cancelled) {
          setProjectMemberRoles((current) => ({
            ...current,
            [project.id]: null,
          }));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [projects, selectedProjectId, selectedWorkspaceId, currentUser?.id, workspaces]);

  const {
    notifications,
    resetNotifications,
    refreshNotifications,
    handleMarkNotificationRead,
    handleMarkAllNotificationsRead,
  } = useNotifications({
    authed,
    notificationPreferences,
    setToast,
  });

  const [editingMessageIndex, setEditingMessageIndex] = useState(null);
  const [retryableUserMessage, setRetryableUserMessage] = useState(null);
  const [toolActivity, setToolActivity] = useState(null);
  const bottomRef = useRef(null);
  const streamAbortRef = useRef(null);
  const autoSummaryInFlightRef = useRef(false);
  const autoSummaryLastMessageCountRef = useRef({});
  const messageCountRef = useRef(messages.length);

  useDirection();
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    messageCountRef.current = messages.length;
  }, [messages.length]);

  const empty = useMemo(() => messages.length === 0, [messages.length]);
  const toolActivityLabel = (name) => {
    const labels = {
      calculator: t("tools.activity.calculator"),
      web_search: t("tools.activity.webSearch"),
      analyze_data: t("tools.activity.dataAnalysis"),
      agent: t("tools.activity.agent"),
      python: t("tools.activity.python"),
    };
    return labels[name] || name;
  };

  const handleToolEvent = useCallback(
    (event) => {
      if (!event?.type) return;

      if (event.type === "runtime_start") {
        setToolActivity({
          name: "agent",
          phase: "running",
          message: t("tools.activity.runtimeStarting"),
        });
        return;
      }

      if (event.type === "runtime_round_start") {
        setToolActivity({
          name: "agent",
          phase: "running",
          message: t("tools.activity.round", { round: event.round ?? 1 }),
        });
        return;
      }

      if (event.type === "start") {
        setToolActivity({
          name: event.name || "agent",
          phase: "running",
          round: event.round,
          duration_ms: null,
        });
        return;
      }

      if (event.type === "result") {
        setToolActivity({
          name: event.name || "agent",
          phase: event.ok ? "done" : "error",
          round: event.round,
          duration_ms: event.duration_ms,
        });
        return;
      }

      if (event.type === "runtime_budget") {
        setToolActivity({
          name: "agent",
          phase: "warning",
          message: t("tools.activity.budget"),
        });
        return;
      }

      if (event.type === "runtime_security_block" || event.type === "runtime_security_stop") {
        setToolActivity({
          name: "agent",
          phase: "error",
          message: t("tools.activity.securityStop"),
        });
        return;
      }

      if (event.type === "cancelled") {
        setToolActivity({
          name: event.name || "agent",
          phase: "cancelled",
          message: t("tools.activity.cancelled"),
        });
        return;
      }

      if (event.type === "runtime_complete") {
        setToolActivity({
          name: "agent",
          phase: event.status === "completed" ? "done" : "warning",
          message:
            event.status === "completed"
              ? t("tools.activity.completed")
              : t("tools.activity.stopped"),
        });
      }
    },
    [t]
  );

  const lastAssistantIndex = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (messages[index].role === "assistant") return index;
    }
    return -1;
  }, [messages]);

  const logout = useCallback(async () => {
    try { await api.post("/auth/logout"); } catch { /* session may already be gone */ }
    setAuthed(false);
    resetConversations();
    setSelectedConversationIds([]);
    setFolders([]);
    setProjects([]);
    setWorkspaces([]);
    setSelectedWorkspaceId(null);
    setSelectedFolderId(null);
    setSelectedProjectId(null);
    setTags([]);
    setSelectedTagId(null);
    setAssistants([]);
    resetSavedPrompts();
    resetBookmarks();
    resetMemories();
    resetAiModels();
    resetNotificationPreferences();
    resetConversationPreferences();
    setSelectedFolderId(null);
    setSelectedAssistantId(null);
    setConversationId(null);
    setParentConversationId(null);
    setConversationSummary(null);
    setConversationSummaryUpdatedAt(null);
    setMessages([getWelcomeMessage(t)]);
    resetChatDraft();
    resetChatAttachments();
    setEditingMessageIndex(null);
    setRetryableUserMessage(null);
    setError("");
    setCurrentUser(null);
    setShowAccountSettings(false);
    setShowFiles(false);
    setShowAdmin(false);
    setShowBilling(false);
    setShowScheduledTasks(false);
    setShowWorkspaceMembers(false);
    setShowShareManager(false);
    setWorkspaceShare(null);
    setReadOnlyConversation(false);
    setShowWorkspaceComments(false);
    setShowTrashConversations(false);
    setConversationSummary(null);
    setConversationSummaryUpdatedAt(null);
    setSummaryLoading(false);
    autoSummaryLastMessageCountRef.current = {};
    messageCountRef.current = 1;
    resetNotifications();
  }, [t]);

  useEffect(() => {
    restoreSession().then(() => setAuthed(true)).catch(() => setAuthed(false)).finally(() => setSessionChecking(false));
  }, []);

  useEffect(() => {
    if (!authed || !currentUser?.id || typeof window === "undefined") return;
    const key = `ai-chat-onboarding:${currentUser.id}`;
    if (window.localStorage.getItem(key) !== "done") {
      setShowOnboarding(true);
    }
  }, [authed, currentUser?.id]);

  const closeOnboarding = useCallback(() => {
    if (currentUser?.id && typeof window !== "undefined") {
      window.localStorage.setItem(`ai-chat-onboarding:${currentUser.id}`, "done");
    }
    setShowOnboarding(false);
  }, [currentUser?.id]);

  // لو أي طلب بأي مكان بالتطبيق رجع 401 (مو بس إرسال رسالة)، نسجّل خروج
  // ونوضّح السبب — قبل كذا كان يصير خروج صامت بدون تفسير
  useEffect(() => {
    const handleUnauthorized = () => {
      logout();
      setToast({ message: t("app.sessionExpired"), type: "error" });
    };
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, [logout, t]);

  const refreshProjects = async (workspaceId = selectedWorkspaceId) => {
    if (workspaceId === null || workspaceId === undefined) {
      setProjects([]);
      setSelectedProjectId(null);
      return;
    }
    try {
      const list = await listProjects(workspaceId);
      setProjects(list);
      setSelectedProjectId((current) =>
        current && list.some((project) => project.id === current) ? current : null
      );
    } catch (err) {
      setProjects([]);
      setSelectedProjectId(null);
      setToast({
        message: getErrorMessage(err, t("app.projectLoadError")),
        type: "error",
      });
    }
  };

  useEffect(() => {
    const handleCommandShortcut = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandPaletteOpen((current) => !current);
      }
    };
    window.addEventListener("keydown", handleCommandShortcut);
    return () => window.removeEventListener("keydown", handleCommandShortcut);
  }, []);

  useEffect(() => {
    if (!authed) return;
    const timer = window.setTimeout(() => {
      refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch
      );
    }, 300);
    return () => window.clearTimeout(timer);
  }, [conversationSearch, authed]);

  const refreshTags = async () => {
    try {
      setTags(await listTags());
    } catch (err) {
      setToast({
        message: getErrorMessage(err, t("app.tagsLoadError")),
        type: "error",
      });
    }
  };

  const handleCreateTag = async () => {
    const name = window.prompt(t("sidebar.tagCreatePrompt"));
    if (!name?.trim()) return;
    try {
      const tag = await createTag(name.trim());
      await refreshTags();
      setSelectedTagId(tag.id);
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch,
        showTrashConversations,
        tag.id
      );
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.tagCreateError"),
        type: "error",
      });
    }
  };

  const handleRenameTag = async (id, currentName, currentColor) => {
    const name = window.prompt(t("sidebar.tagRenamePrompt"), currentName);
    if (!name?.trim()) return;
    try {
      await updateTag(id, name.trim(), currentColor);
      await refreshTags();
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.tagRenameError"),
        type: "error",
      });
    }
  };

  const handleDeleteTag = async (id, name) => {
    if (!window.confirm(t("sidebar.tagDeleteConfirm", { name }))) return;
    const wasSelected = id === selectedTagId;
    try {
      await deleteTag(id);
      if (wasSelected) setSelectedTagId(null);
      await refreshTags();
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch,
        showTrashConversations,
        wasSelected ? null : selectedTagId
      );
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.tagDeleteError"),
        type: "error",
      });
    }
  };

  const handleSelectTag = async (id) => {
    const tagId = id === null || id === undefined ? null : Number(id);
    setSelectedTagId(tagId);
    setSelectedConversationIds([]);
    startNewChat();
    await refreshConversations(
      showArchivedConversations,
      selectedFolderId,
      selectedWorkspaceId,
      selectedProjectId,
      conversationSearch,
      showTrashConversations,
      tagId
    );
  };

  const handleSetConversationTags = async (id, tagIds) => {
    try {
      await setConversationTags(id, tagIds);
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch,
        showTrashConversations,
        selectedTagId
      );
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.conversationTagError"),
        type: "error",
      });
    }
  };

  const refreshWorkspaces = async () => {
    let list;
    try {
      list = await listWorkspaces();
    } catch (err) {
      setToast({
        message: getErrorMessage(err, t("app.workspacesLoadError")),
        type: "error",
      });
      return;
    }

    setWorkspaces(list);
    const nextId =
      selectedWorkspaceId && list.some((workspace) => workspace.id === selectedWorkspaceId)
        ? selectedWorkspaceId
        : list[0]?.id ?? null;
    setSelectedWorkspaceId(nextId);
    const selectedWorkspace = list.find((workspace) => workspace.id === nextId);
    setSelectedModel(
      selectedWorkspace?.default_ai_model ||
        aiModels.find((model) => model.is_default)?.id ||
        aiModels[0]?.id ||
        ""
    );
    setSelectedFolderId(null);
    setSelectedProjectId(null);
    await refreshFolders(nextId);
    await refreshProjects(nextId);
    await refreshAssistants(nextId);
    await refreshConversations(showArchivedConversations, null, nextId, null);
  };

  const handleCreateWorkspace = async () => {
    const name = window.prompt(t("sidebar.workspaceCreatePrompt"));
    if (!name?.trim()) return;
    try {
      const workspace = await createWorkspace(name.trim());
      const nextList = [...workspaces, workspace];
      setWorkspaces(nextList);
      setSelectedWorkspaceId(workspace.id);
      setSelectedFolderId(null);
      setSelectedProjectId(null);
      startNewChat();
      await refreshFolders(workspace.id);
      await refreshProjects(workspace.id);
      await refreshAssistants(workspace.id);
      await refreshConversations(showArchivedConversations, null, workspace.id, null);
    } catch {
      setToast({ message: t("app.workspaceCreateError"), type: "error" });
    }
  };

  const handleRenameWorkspace = async () => {
    if (selectedWorkspaceId === null) return;
    const current = workspaces.find((workspace) => workspace.id === selectedWorkspaceId);
    const name = window.prompt(
      t("sidebar.workspaceRenamePrompt"),
      current?.name || ""
    );
    if (!name?.trim()) return;
    try {
      const updated = await renameWorkspace(selectedWorkspaceId, name.trim());
      setWorkspaces((prev) =>
        prev.map((workspace) => (workspace.id === updated.id ? updated : workspace))
      );
    } catch {
      setToast({ message: t("app.workspaceRenameError"), type: "error" });
    }
  };

  const handleOpenWorkspaceMembers = () => {
    if (selectedWorkspaceId !== null) setShowWorkspaceMembers(true);
  };

  const handleWorkspaceUpdated = (updated) => {
    setWorkspaces((prev) =>
      prev.map((workspace) =>
        workspace.id === updated.id ? { ...workspace, ...updated } : workspace
      )
    );
    if (updated.id === selectedWorkspaceId && updated.default_ai_model) {
      setSelectedModel(updated.default_ai_model);
    }
    setToast({ message: t("app.workspaceModelUpdated"), type: "success" });
  };

  const handleWorkspaceQuotaUpdated = (updated) => {
    setWorkspaces((prev) =>
      prev.map((workspace) =>
        workspace.id === updated.id ? { ...workspace, ...updated } : workspace
      )
    );
    setToast({ message: t("app.workspaceQuotaUpdated"), type: "success" });
  };

  const handleSelectWorkspace = async (id) => {
    const workspaceId = Number(id);
    if (!workspaceId || workspaceId === selectedWorkspaceId) return;
    const workspace = workspaces.find((item) => item.id === workspaceId);
    setSelectedWorkspaceId(workspaceId);
    setSelectedFolderId(null);
    setSelectedProjectId(null);
    setSelectedModel(
      workspace?.default_ai_model ||
        aiModels.find((model) => model.is_default)?.id ||
        aiModels[0]?.id ||
        ""
    );
    startNewChat();
    await refreshFolders(workspaceId);
    await refreshProjects(workspaceId);
    await refreshAssistants(workspaceId);
    await refreshConversations(showArchivedConversations, null, workspaceId, null);
  };

  const refreshFolders = async (workspaceId = selectedWorkspaceId) => {
    try {
      setFolders(await listFolders(workspaceId));
    } catch (err) {
      setToast({
        message: getErrorMessage(err, t("app.foldersLoadError")),
        type: "error",
      });
    }
  };

  const handleCreateFolder = async () => {
    const name = window.prompt(t("sidebar.folderCreatePrompt"));
    if (!name?.trim()) return;
    try {
      const folder = await createFolder(name.trim(), selectedWorkspaceId);
      await refreshFolders(selectedWorkspaceId);
      setSelectedFolderId(folder.id);
      startNewChat();
      await refreshConversations(showArchivedConversations, folder.id, selectedWorkspaceId, null);
    } catch {
      setToast({ message: t("app.folderCreateError"), type: "error" });
    }
  };

  const handleRenameFolder = async (id, newName, color = null) => {
    try {
      await renameFolder(id, newName, color);
      await refreshFolders(selectedWorkspaceId);
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId
      );
      void maybeAutoSummarizeConversation(
        conversationId,
        messageCountRef.current
      );
    } catch {
      setToast({ message: t("app.folderRenameError"), type: "error" });
    }
  };

  const handleMoveFolder = async (id, direction) => {
    try {
      await moveFolder(id, direction);
      await refreshFolders(selectedWorkspaceId);
    } catch {
      setToast({ message: t("app.folderReorderError"), type: "error" });
    }
  };

  const handleDeleteFolder = async (id) => {
    const wasSelected = id === selectedFolderId;
    try {
      await deleteFolder(id);
      if (wasSelected) {
        setSelectedFolderId(null);
        startNewChat();
      }
      await refreshFolders(selectedWorkspaceId);
      await refreshConversations(
        showArchivedConversations,
        wasSelected ? null : selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId
      );
    } catch {
      setToast({ message: t("app.folderDeleteError"), type: "error" });
    }
  };

  const handleSelectFolder = async (id) => {
    setSelectedFolderId(id);
    setSelectedProjectId(null);
    startNewChat();
    await refreshConversations(showArchivedConversations, id, selectedWorkspaceId, null);
  };

  const handleCreateProject = () => {
    if (selectedWorkspaceId === null) return;
    setEditingProjectId(null);
    setShowProjectEditor(true);
  };

  const handleRenameProject = (id) => {
    setEditingProjectId(id);
    setShowProjectEditor(true);
  };

  const handleSaveProject = async ({ name, description, instructions, assistant_id }) => {
    try {
      if (editingProjectId === null) {
        if (selectedWorkspaceId === null) return;
        const project = await createProject(
          selectedWorkspaceId,
          name,
          description || "",
          instructions || "",
          assistant_id ?? null
        );
        await refreshProjects(selectedWorkspaceId);
        setSelectedProjectId(project.id);
        setSelectedFolderId(null);
        startNewChat();
        await refreshConversations(
          showArchivedConversations,
          null,
          selectedWorkspaceId,
          project.id
        );
      } else {
        const project = await updateProject(
          editingProjectId,
          name,
          description || "",
          instructions || "",
          assistant_id ?? null
        );
        await refreshProjects(selectedWorkspaceId);
        if (selectedProjectId === editingProjectId) {
          setSelectedProjectId(project.id);
        }
        await refreshConversations(
          showArchivedConversations,
          selectedFolderId,
          selectedWorkspaceId,
          selectedProjectId
        );
      }
      setShowProjectEditor(false);
      setEditingProjectId(null);
    } catch (err) {
      setToast({
        message:
          err?.response?.data?.detail ||
          (editingProjectId === null
            ? t("app.projectCreateError")
            : t("app.projectUpdateError")),
        type: "error",
      });
      throw err;
    }
  };

  const handleExportProject = async (projectId) => {
    try {
      const project = projects.find((item) => item.id === Number(projectId));
      const blob = await exportProject(Number(projectId));
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `project-${projectId}-${(project?.name || "export").replace(/[^a-zA-Z0-9_-]+/g, "-")}.zip`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setToast({ message: t("app.projectExportSuccess"), type: "success" });
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.projectExportError"),
        type: "error",
      });
    }
  };

  const handleImportProject = async (file) => {
    if (!selectedWorkspaceId || !file) return;
    try {
      let result;
      try {
        result = await importProject(selectedWorkspaceId, file, "fail");
      } catch (err) {
        if (err?.response?.status !== 409) throw err;
        const rename = window.confirm(t("app.projectImportRenameConfirm"));
        if (!rename) return;
        result = await importProject(selectedWorkspaceId, file, "rename");
      }
      await refreshProjects(selectedWorkspaceId);
      setSelectedProjectId(result.project_id);
      setSelectedFolderId(null);
      startNewChat();
      await refreshConversations(
        showArchivedConversations,
        null,
        selectedWorkspaceId,
        result.project_id
      );
      setToast({
        message: t("app.projectImportSuccess", { name: result.name }),
        type: "success",
      });
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.projectImportError"),
        type: "error",
      });
    }
  };

  const handleDeleteProject = async (id, name) => {
    if (!window.confirm(t("sidebar.projectDeleteConfirm", { name }))) return;
    const wasSelected = id === selectedProjectId;
    try {
      await deleteProject(id);
      if (wasSelected) {
        setSelectedProjectId(null);
        startNewChat();
      }
      await refreshProjects(selectedWorkspaceId);
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        wasSelected ? null : selectedProjectId
      );
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.projectDeleteError"),
        type: "error",
      });
    }
  };

  const handleSelectProject = async (id) => {
    const project = id === null ? null : projects.find((item) => item.id === Number(id));
    setSelectedProjectId(id);
    setSelectedFolderId(null);
    setSelectedAssistantId(project?.assistant_id ?? null);
    startNewChat();
    await refreshConversations(
      showArchivedConversations,
      null,
      selectedWorkspaceId,
      id
    );
  };

  const handleMoveConversationToProject = async (id, projectId) => {
    const normalizedProjectId = projectId === "" ? null : Number(projectId);
    try {
      const result = await moveConversationToProject(id, normalizedProjectId);
      if (
        id === conversationId &&
        selectedProjectId !== null &&
        result.project_id !== selectedProjectId
      ) {
        startNewChat();
      }
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId
      );
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.conversationMoveError"),
        type: "error",
      });
    }
  };

  const handleUseSavedPrompt = (content) => {
    setInput(content);
    setEditingMessageIndex(null);
    setError("");
  };

  const refreshAssistants = async (workspaceId = selectedWorkspaceId) => {
    try {
      const owned = (await listAssistants()).map((assistant) => ({
        ...assistant,
        is_shared: false,
        can_edit: true,
      }));

      let shared = [];
      if (workspaceId !== null && workspaceId !== undefined) {
        shared = await listWorkspaceSharedAssistants(workspaceId);
      }

      const ownedById = new Map(owned.map((assistant) => [assistant.id, assistant]));
      for (const item of shared) {
        const existing = ownedById.get(item.id);
        if (existing) {
          ownedById.set(item.id, {
            ...existing,
            is_shared: true,
            shared_workspace_id: item.workspace_id,
            owner_email: item.owner_email,
            can_edit: true,
          });
        } else {
          ownedById.set(item.id, item);
        }
      }

      const merged = Array.from(ownedById.values());
      setAssistants(merged);

      if (
        selectedAssistantId !== null &&
        !merged.some((assistant) => assistant.id === selectedAssistantId)
      ) {
        setSelectedAssistantId(null);
      }
    } catch (err) {
      setToast({
        message: getErrorMessage(err, t("app.assistantLoadError")),
        type: "error",
      });
    }
  };

  const openCreateAssistantEditor = () => {
    setEditingAssistantId(null);
    setShowAssistantEditor(true);
  };

  const openEditAssistantEditor = (id) => {
    setEditingAssistantId(id);
    setShowAssistantEditor(true);
  };

  const handleToggleAssistantShare = async (assistant) => {
    if (selectedWorkspaceId === null || assistant.can_edit === false) return;

    try {
      if (assistant.is_shared) {
        await unshareAssistantFromWorkspace(
          assistant.id,
          selectedWorkspaceId
        );
        setToast({ message: t("app.assistantUnshared"), type: "success" });
      } else {
        await shareAssistantWithWorkspace(
          assistant.id,
          selectedWorkspaceId
        );
        setToast({ message: t("app.assistantShared"), type: "success" });
      }
      await refreshAssistants(selectedWorkspaceId);
    } catch (err) {
      setToast({
        message:
          err?.response?.data?.detail || t("app.assistantShareError"),
        type: "error",
      });
    }
  };

  const handleAssistantRestored = async (restored) => {
    try {
      await refreshAssistants(selectedWorkspaceId);
      setSelectedAssistantId(restored.id);
      setToast({ message: t("app.assistantVersionRestored"), type: "success" });
    } catch {
      setToast({ message: t("app.assistantUpdateError"), type: "error" });
    }
  };

  const handleSaveAssistant = async ({ name, description, instructions }) => {
    try {
      if (editingAssistantId === null) {
        const assistant = await createAssistant({ name, description, instructions });
        await refreshAssistants(selectedWorkspaceId);
        setSelectedAssistantId(assistant.id);
        setEditingAssistantId(assistant.id);
        startNewChat();
      } else {
        const assistant = await updateAssistant(editingAssistantId, {
          name,
          description,
          instructions,
        });
        await refreshAssistants(selectedWorkspaceId);
        if (selectedAssistantId === editingAssistantId) {
          setSelectedAssistantId(assistant.id);
        }
      }
    } catch (err) {
      setToast({
        message:
          err?.response?.data?.detail ||
          (editingAssistantId === null
            ? t("app.assistantCreateError")
            : t("app.assistantUpdateError")),
        type: "error",
      });
      throw err;
    }
  };

  const handleDeleteAssistant = async (id, name) => {
    if (!window.confirm(t("sidebar.assistantDeleteConfirm", { name }))) return;
    try {
      await deleteAssistant(id);
      if (id === selectedAssistantId) {
        setSelectedAssistantId(null);
        startNewChat();
      }
      await refreshAssistants(selectedWorkspaceId);
    } catch (err) {
      setToast({
        message:
          err?.response?.data?.detail || t("app.assistantDeleteError"),
        type: "error",
      });
    }
  };

  const handleSelectAssistant = (id) => {
    setSelectedAssistantId(id);
    startNewChat();
  };

  const handleMoveConversationToFolder = async (id, folderId) => {
    const normalizedFolderId = folderId === "" ? null : Number(folderId);
    try {
      const result = await moveConversationToFolder(id, normalizedFolderId);
      if (
        id === conversationId &&
        selectedFolderId !== null &&
        result.folder_id !== selectedFolderId
      ) {
        startNewChat();
      }
      await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId);
    } catch {
      setToast({ message: t("app.conversationMoveError"), type: "error" });
    }
  };

  const refreshCurrentUser = async () => {
    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
    } catch {
      // تجاهل بصمت — لوحة الحساب تبقى غير محدّثة لو فشل التحميل فقط
    }
  };


  useEffect(() => {
    if (authed) {
      refreshWorkspaces();
      refreshTags();
      refreshAssistants(selectedWorkspaceId);
      refreshSavedPrompts();
      refreshAiModels();
      refreshCurrentUser();
    }
  }, [authed]);

  useEffect(() => {
    const handleAppToast = (event) => {
      if (event.detail?.message) {
        setToast({
          message: event.detail.message,
          type: event.detail.type || "error",
        });
      }
    };
    window.addEventListener("app:toast", handleAppToast);
    return () => window.removeEventListener("app:toast", handleAppToast);
  }, []);


  const switchLang = (nextLang) => {
    setLang(nextLang);
    i18n.changeLanguage(nextLang);
  };

  const {
    bookmarkedMessages,
    handleToggleMessageBookmark,
    handleOpenBookmarkedMessage,
    resetBookmarks,
  } = useBookmarks({
    authed,
    conversationId,
    loading,
    readOnlyConversation,
    setMessages,
    setToast,
    openConversation,
  });

  const {
    memories,
    handleToggleMessageMemory,
    resetMemories,
  } = useMemories({
    authed,
    messages,
    loading,
    readOnlyConversation,
    editingMessageIndex,
    setToast,
  });

  const {
    aiModels,
    selectedModel,
    setSelectedModel,
    refreshAiModels,
    resetAiModels,
  } = useAiModels({ setToast });

  const {
    notificationPreferences,
    setRealtimeToastsEnabled: handleNotificationToastsChanged,
    resetNotificationPreferences,
  } = useNotificationPreferences({
    authed,
    userId: currentUser?.id,
  });

  const {
    autoGenerateTitles,
    autoGenerateSummaries,
    resetConversationPreferences,
  } = useConversationPreferences();

  const { input, setInput, resetChatDraft } = useChatDraft({
    authed,
    userId: currentUser?.id,
    conversationId,
  });

  const {
    chatAttachments,
    chatAttachmentUploading,
    handleAttachFiles,
    handleRemoveAttachment,
    resetChatAttachments,
  } = useChatAttachments({
    conversationId,
    selectedWorkspaceId,
    selectedProjectId,
    loading,
    readOnlyConversation,
    editingMessageIndex,
    setToast,
    t,
  });

  const { openConversation } = useOpenConversation({
    aiModels,
    setConversationId,
    setActiveConversationTitle,
    setParentConversationId,
    setConversationBranches,
    setConversationSummary,
    setConversationSummaryUpdatedAt,
    setSelectedAssistantId,
    setSelectedWorkspaceId,
    setSelectedFolderId,
    setSelectedProjectId,
    setSelectedModel,
    setWorkspaceShare,
    setMessages,
    setSelectedConversationIds,
    setShowShareManager,
    setReadOnlyConversation,
    setShowWorkspaceComments,
    setError,
    setToast,
    setInput,
    resetChatAttachments,
    setEditingMessageIndex,
    setRetryableUserMessage,
    messageCountRef,
    autoSummaryLastMessageCountRef,
    t,
  });

  const { startNewChat } = useStartNewChat({
    t,
    messageCountRef,
    resetChatAttachments,
    setToolActivity,
    setShowShareManager,
    setWorkspaceShare,
    setReadOnlyConversation,
    setShowWorkspaceComments,
    setSelectedConversationIds,
    setConversationId,
    setConversationBranches,
    setParentConversationId,
    setMessages,
    setInput,
    setEditingMessageIndex,
    setError,
    getWelcomeMessage,
  });
  const { startEditingMessage, cancelEditing } = useMessageEditing({
    readOnlyConversation,
    loading,
    conversationId,
    messages,
    resetChatAttachments,
    setError,
    setRetryableUserMessage,
    setEditingMessageIndex,
    setInput,
  });


  const {
    toggleConversationSelection,
    toggleSelectAllVisibleConversations,
    clearSelectedConversations,
  } = useConversationSelection({ setSelectedConversationIds });

  const {
    conversations,
    conversationsLoading,
    conversationsLoadingMore,
    hasMoreConversations,
    refreshConversations,
    loadMoreConversations,
    resetConversations,
  } = useConversationList({
    filters: {
      showArchivedConversations,
      showTrashConversations,
      selectedFolderId,
      selectedWorkspaceId,
      selectedProjectId,
      selectedTagId,
      conversationSearch,
    },
    setToast,
    t,
  });


  const {
    handleGenerateConversationTitle,
    maybeAutoGenerateConversationTitle,
    maybeAutoSummarizeConversation,
    handleSummarizeConversation,
  } = useConversationMetadata({
    conversationId,
    loading,
    titleLoading,
    summaryLoading,
    readOnlyConversation,
    autoGenerateTitles,
    autoGenerateSummaries,
    conversationSearch,
    showArchivedConversations,
    showTrashConversations,
    selectedFolderId,
    selectedWorkspaceId,
    selectedProjectId,
    selectedTagId,
    messageCountRef,
    autoSummaryLastMessageCountRef,
    autoSummaryInFlightRef,
    refreshConversations,
    setConversationSummary,
    setConversationSummaryUpdatedAt,
    setSummaryLoading,
    setTitleLoading,
    setError,
    setToast,
    t,
  });

  const {
    handleBulkArchive,
    handleBulkDelete,
    handleBulkExport,
    handleBulkMoveToFolder,
  } = useConversationBulkActions({
    selectedConversationIds,
    conversationId,
    showArchivedConversations,
    showTrashConversations,
    selectedFolderId,
    selectedWorkspaceId,
    selectedProjectId,
    refreshConversations,
    setSelectedConversationIds,
    startNewChat,
    setToast,
    t,
  });

  const {
    handleDeleteConversation,
    handleRenameConversation,
    handleToggleArchiveConversation,
    handleTogglePinConversation,
    handleToggleTrashConversation,
  } = useConversationItemActions({
    conversationId,
    conversationSearch,
    refreshConversations,
    selectedFolderId,
    selectedProjectId,
    selectedWorkspaceId,
    setToast,
    showArchivedConversations,
    showTrashConversations,
    startNewChat,
    t,
  });

  const handleOpenWorkspaceSharedConversation = async (workspaceId, sharedConversationId) => {
    try {
      const data = await getWorkspaceSharedConversation(
        Number(workspaceId),
        Number(sharedConversationId)
      );
      setShowShareManager(false);
      setReadOnlyConversation(true);
      setShowWorkspaceComments(true);
      setWorkspaceShare(null);
      setSelectedWorkspaceId(Number(workspaceId));
      setConversationId(data.conversation_id);
      setConversationSummary(null);
      setConversationSummaryUpdatedAt(null);
      setSelectedAssistantId(null);
      setSelectedFolderId(null);
      setSelectedProjectId(null);
      setSelectedModel("");
      setMessages(
        data.messages.map((message) => ({
          role: message.role,
          text: message.content,
          time: new Date(message.created_at).toLocaleTimeString(),
          sources: message.sources ?? [],
          feedback: null,
          isBookmarked: false,
        }))
      );
      setInput("");
      setEditingMessageIndex(null);
      setError("");
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("workspaceSharing.loadError"),
        type: "error",
      });
    }
  };

  const handleDuplicatedWorkspaceConversation = async (id) => {
    if (!id) {
      setToast({ message: t("workspaceSharing.duplicateError"), type: "error" });
      return;
    }
    try {
      await openConversation(id);
      setReadOnlyConversation(false);
      setToast({ message: t("workspaceSharing.duplicated"), type: "success" });
    } catch {
      setToast({ message: t("workspaceSharing.duplicateError"), type: "error" });
    }
  };

  const handleToggleWorkspaceShare = async () => {
    if (!conversationId || !selectedWorkspaceId || loading || readOnlyConversation) return;
    try {
      if (workspaceShare) {
        await unshareConversationFromWorkspace(conversationId);
        setWorkspaceShare(null);
        setToast({ message: t("workspaceSharing.unshared"), type: "success" });
      } else {
        const share = await shareConversationWithWorkspace(conversationId);
        setWorkspaceShare(share);
        setToast({ message: t("workspaceSharing.shared"), type: "success" });
      }
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("workspaceSharing.updateError"),
        type: "error",
      });
    }
  };

  const handleAnalyzeImage = async (file, prompt) => {
    if (!conversationId || loading || readOnlyConversation) return;
    setError("");
    setShowFiles(false);

    const imageMessageCount = messageCountRef.current + 2;
    messageCountRef.current = imageMessageCount;
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        text: "[صورة: " + file.original_filename + "] " + prompt,
        time: new Date().toLocaleTimeString(),
      },
      {
        role: "assistant",
        text: "",
        time: new Date().toLocaleTimeString(),
      },
    ]);
    setLoading(true);

    try {
      const result = await analyzeImage(conversationId, file.id, prompt);
      setConversationId(result.conversation_id);
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          ...next[next.length - 1],
          text: result.reply,
        };
        return next;
      });
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId
      );
      void maybeAutoSummarizeConversation(
        conversationId,
        imageMessageCount
      );
    } catch (err) {
      messageCountRef.current = Math.max(0, messageCountRef.current - 2);
      setMessages((prev) => prev.slice(0, -2));
      setToast({ message: t("app.imageAnalyzeError"), type: "error" });
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const handleMessageFeedback = async (index, rating) => {
    if (!conversationId || loading || readOnlyConversation) return;

    const nextRating = rating === messages[index]?.feedback ? null : rating;
    const previousRating = messages[index]?.feedback ?? null;

    setMessages((prev) =>
      prev.map((message, messageIndex) =>
        messageIndex === index ? { ...message, feedback: nextRating } : message
      )
    );

    try {
      await setMessageFeedback(conversationId, index + 1, nextRating);
    } catch {
      setMessages((prev) =>
        prev.map((message, messageIndex) =>
          messageIndex === index ? { ...message, feedback: previousRating } : message
        )
      );
      setToast({ message: t("app.feedbackError"), type: "error" });
    }
  };

  const handleImportConversation = async (file) => {
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      setToast({ message: t("importConversationTooLarge"), type: "error" });
      return;
    }
    if (selectedWorkspaceId === null || selectedWorkspaceId === undefined) {
      setToast({ message: t("importConversationError"), type: "error" });
      return;
    }

    try {
      const text = await file.text();
      let payload;
      try {
        payload = JSON.parse(text);
      } catch {
        setToast({ message: t("importConversationInvalidFile"), type: "error" });
        return;
      }

      if (
        payload &&
        typeof payload === "object" &&
        Array.isArray(payload.conversations)
      ) {
        if (payload.version !== 1 || payload.conversations.length === 0) {
          setToast({ message: t("importConversationInvalidFile"), type: "error" });
          return;
        }

        const imported = await importConversations(selectedWorkspaceId, payload);
        setShowArchivedConversations(false);
        setShowTrashConversations(false);
        setConversationSearch("");
        setSelectedTagId(null);
        setSelectedFolderId(null);
        setSelectedProjectId(null);
        setSelectedConversationIds([]);

        await refreshConversations(
          false,
          null,
          selectedWorkspaceId,
          null,
          "",
          false,
          null
        );

        const firstId = imported.conversation_ids?.[0];
        if (firstId) {
          await openConversation(firstId);
        }
        setToast({
          message: t("bulkImportSuccess", { count: imported.imported_count }),
          type: "success",
        });
        return;
      }

      if (
        !payload ||
        typeof payload !== "object" ||
        !Array.isArray(payload.messages) ||
        payload.messages.length === 0
      ) {
        setToast({ message: t("importConversationInvalidFile"), type: "error" });
        return;
      }

      const imported = await importConversation(selectedWorkspaceId, {
        title: payload.title || "Imported conversation",
        messages: payload.messages,
        folder_id: payload.folder_id ?? null,
        project_id: payload.project_id ?? null,
        assistant_id: payload.assistant_id ?? null,
        ai_model: payload.ai_model ?? null,
      });

      setShowArchivedConversations(false);
      setShowTrashConversations(false);
      setConversationSearch("");
      setSelectedTagId(null);
      setSelectedFolderId(imported.folder_id ?? null);
      setSelectedProjectId(imported.project_id ?? null);

      await refreshConversations(
        false,
        imported.folder_id ?? null,
        selectedWorkspaceId,
        imported.project_id ?? null,
        "",
        false,
        null
      );
      await openConversation(imported.id);
      setToast({ message: t("importConversationSuccess"), type: "success" });
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("importConversationError"),
        type: "error",
      });
    }
  };

  const handleExportConversation = async (format = "markdown") => {
    if (!conversationId || loading) return;
    try {
      await exportConversation(conversationId, format);
      setToast({ message: t("exportConversationSuccess"), type: "success" });
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("exportConversationError"),
        type: "error",
      });
    }
  };

  const handleShareConversation = async () => {
    if (!conversationId) return;
    try {
      const protect = window.confirm(t("sharing.protectConfirm"));
      let password = null;

      if (protect) {
        password = window.prompt(t("sharing.passwordPrompt"));
        if (password === null) return;
        password = password.trim();
        if (password.length < 8) {
          setToast({ message: t("sharing.passwordTooShort"), type: "error" });
          return;
        }
      }

      const share = await createConversationShare(conversationId, 7, password);
      if (navigator.share) {
        try {
          await navigator.share({
            title: messages[0]?.text || t("appName"),
            url: share.url,
          });
          setToast({ message: t("sharing.sharedSuccess"), type: "success" });
          return;
        } catch (err) {
          if (err?.name === "AbortError") return;
        }
      }

      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(share.url);
        setToast({ message: t("sharing.linkCopied"), type: "success" });
        return;
      }

      window.prompt(t("sharing.copyPrompt"), share.url);
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("sharing.createError"),
        type: "error",
      });
    }
  };

  const handleManageConversationShares = () => {
    if (!conversationId || loading) return;
    setShowShareManager(true);
  };



  const handleBranchConversation = async (messageIndex) => {
    if (!conversationId || loading || readOnlyConversation) return;
    try {
      const branch = await branchConversation(conversationId, messageIndex + 1);
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch,
        showTrashConversations,
        selectedTagId
      );
      await openConversation(branch.id);
      setToast({ message: t("app.branchConversationSuccess"), type: "success" });
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.branchConversationError"),
        type: "error",
      });
    }
  };

  const handleDuplicateConversation = async (id) => {
    try {
      const duplicate = await duplicateConversation(id);
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch,
        showTrashConversations,
        selectedTagId
      );
      await openConversation(duplicate.id);
      setToast({ message: t("app.duplicateConversationSuccess"), type: "success" });
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.duplicateConversationError"),
        type: "error",
      });
    }
  };



  const deleteMessage = async (index) => {
    if (!conversationId || loading || editingMessageIndex !== null || readOnlyConversation) return;

    const isArabic = document.documentElement.lang === "ar";
    const confirmed = window.confirm(
      isArabic
        ? "حذف هذه الرسالة؟ إذا كانت رسالة مستخدم فسيُحذف رد المساعد المرتبط بها أيضًا."
        : "Delete this message? For a user message, its linked assistant reply will also be deleted."
    );
    if (!confirmed) return;

    setError("");
    try {
      await api.delete(`/chat/${conversationId}/messages/${index + 1}`);
      const data = await getConversation(conversationId);
      setMessages(
        data.messages.length
          ? data.messages.map((m) => ({
              role: m.role,
              text: m.content,
              time: new Date(m.created_at).toLocaleTimeString(),
              sources: m.sources ?? [],
            }))
          : [getWelcomeMessage(t)]
      );
      await refreshConversations();
    } catch (err) {
      if (err?.response?.status === 401) return;
      setToast({
        message:
          err?.response?.data?.detail ||
          (isArabic ? "تعذر حذف الرسالة" : "Couldn't delete the message"),
        type: "error",
      });
    }
  };

  const stopGeneration = () => {
    if (streamAbortRef.current) {
      streamAbortRef.current.abort();
      streamAbortRef.current = null;
    }
    setLoading(false);
    setToolActivity(null);
  };

  const editMessage = async () => {
    const targetIndex = editingMessageIndex;
    const editedText = input.trim();
    if (readOnlyConversation || targetIndex === null || !conversationId || !editedText || loading) return;

    const userMessageIndex = messages
      .slice(0, targetIndex + 1)
      .filter((message) => message.role === "user").length;
    if (!userMessageIndex) return;

    const previousMessages = messages;
    autoSummaryLastMessageCountRef.current[conversationId] = 0;
    setError("");
    setRetryableUserMessage(null);
    messageCountRef.current = targetIndex + 2;
    clearChatDraft(currentUser?.id, conversationId);
    setMessages((prev) => [
      ...prev.slice(0, targetIndex + 1).map((message, index) =>
        index === targetIndex ? { ...message, text: editedText } : message
      ),
      { role: "assistant", text: "", time: new Date().toLocaleTimeString(), sources: [] },
    ]);
    setInput("");
    setEditingMessageIndex(null);
    setLoading(true);

    const controller = new AbortController();
    streamAbortRef.current = controller;

    const appendToLastMessage = (chunk) => {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        next[next.length - 1] = { ...last, text: last.text + chunk };
        return next;
      });
    };

    await streamEditMessage(conversationId, userMessageIndex, editedText, {
      signal: controller.signal,
      onConversationId: (id) => setConversationId(id),
      onToolEvent: handleToolEvent,
      onSources: (sources) => {
        setMessages((prev) => prev.map((message, index) =>
          index === targetIndex + 1 ? { ...message, sources } : message
        ));
      },
      onChunk: appendToLastMessage,
      onDone: () => {
        streamAbortRef.current = null;
        setLoading(false);
        refreshConversations(
          showArchivedConversations,
          selectedFolderId,
          selectedWorkspaceId,
          selectedProjectId
        );
        autoSummaryLastMessageCountRef.current[conversationId] = 0;
        void maybeAutoSummarizeConversation(
          conversationId,
          messageCountRef.current
        );
      },
      onError: (message) => {
        streamAbortRef.current = null;
        setLoading(false);
        setToolActivity(null);
        setError(message);
        setMessages(previousMessages);
        setInput(editedText);
        setEditingMessageIndex(targetIndex);
      },
    });
  };

  const sendMessage = async () => {
    if (readOnlyConversation) return;
    if (editingMessageIndex !== null) {
      await editMessage();
      return;
    }

    const userText = input.trim();
    const fileIds = chatAttachments.map((file) => file.id);
    if (!userText && fileIds.length === 0) return;
    const submittedText =
      userText ||
      (document.documentElement.lang === "ar" ? "أرسل لي الملف المرفق وحلله." : "Please analyze the attached file.");
    clearChatDraft(currentUser?.id, conversationId);
    setError("");
    setRetryableUserMessage(null);
    setToolActivity(null);
    messageCountRef.current += 2;
    setMessages((prev) => [
      ...prev,
      { role: "user", text: submittedText, time: new Date().toLocaleTimeString() },
      { role: "assistant", text: "", time: new Date().toLocaleTimeString(), feedback: null },
    ]);
    setInput("");
    setLoading(true);

    const controller = new AbortController();
    streamAbortRef.current = controller;

    const isNewConversation = !conversationId;
    let createdConversationId = conversationId;
    let receivedFirstChunk = false;

    const appendToLastMessage = (chunk) => {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        next[next.length - 1] = { ...last, text: last.text + chunk };
        return next;
      });
    };

    await streamChatMessage(submittedText, conversationId, selectedAssistantId, {
      signal: controller.signal,
      workspaceId: selectedWorkspaceId,
      projectId: selectedProjectId,
      model: selectedModel || null,
      fileIds,
      onToolEvent: handleToolEvent,
      onConversationId: async (id) => {
        createdConversationId = id;
        setConversationId(id);
        if (isNewConversation && selectedProjectId !== null) {
          try {
            await moveConversationToProject(id, selectedProjectId);
          } catch {
            setToast({ message: t("app.conversationMoveError"), type: "error" });
          }
        } else if (isNewConversation && selectedFolderId !== null) {
          try {
            await moveConversationToFolder(id, selectedFolderId);
          } catch {
            setToast({ message: t("app.conversationMoveError"), type: "error" });
          }
        }
      },
      onSources: (sources) => {
        setMessages((prev) => prev.map((message, index) =>
          index === messages.length + 1 ? { ...message, sources } : message
        ));
      },
      onChunk: (chunk) => {
        if (!receivedFirstChunk) {
          receivedFirstChunk = true;
          // نبقي loading=true أثناء البث عشان زر الإيقاف يظهر
        }
        appendToLastMessage(chunk);
      },
      onDone: async () => {
        streamAbortRef.current = null;
        setLoading(false);
        setRetryableUserMessage(null);
        resetChatAttachments();
        if (isNewConversation) {
          setActiveConversationTitle(submittedText.slice(0, 50));
          refreshConversations(
            showArchivedConversations,
            selectedFolderId,
            selectedWorkspaceId,
            selectedProjectId
          );
          await maybeAutoGenerateConversationTitle(createdConversationId);
        }
        void maybeAutoSummarizeConversation(
          createdConversationId,
          messageCountRef.current
        );
      },
      onError: (message) => {
        streamAbortRef.current = null;
        setLoading(false);
        setError(message);
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && last.text === "") {
            const next = prev.slice(0, -1);
            messageCountRef.current = next.length;
            return next;
          }
          messageCountRef.current = prev.length;
          return prev;
        });
        const failedConversationId = createdConversationId || conversationId;
        if (failedConversationId) {
          setRetryableUserMessage({
            conversationId: failedConversationId,
            text: submittedText,
          });
        }
      },
    });
  };

  const retryFailedGeneration = async () => {
    if (
      readOnlyConversation ||
      loading ||
      !retryableUserMessage ||
      !conversationId ||
      retryableUserMessage.conversationId !== conversationId
    ) {
      return;
    }

    setError("");
    setLoading(true);
    setRetryableUserMessage(null);
    messageCountRef.current += 1;
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        text: "",
        time: new Date().toLocaleTimeString(),
        feedback: null,
        sources: [],
      },
    ]);

    const controller = new AbortController();
    streamAbortRef.current = controller;
    const targetConversationId = conversationId;

    const appendToLastMessage = (chunk) => {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        next[next.length - 1] = { ...last, text: last.text + chunk };
        return next;
      });
    };

    await streamRegenerateMessage(targetConversationId, {
      signal: controller.signal,
      onConversationId: (id) => setConversationId(id),
      onSources: (sources) => {
        setMessages((prev) => prev.map((message, index) =>
          index === prev.length - 1 && message.role === "assistant"
            ? { ...message, sources }
            : message
        ));
      },
      onChunk: appendToLastMessage,
      onDone: () => {
        streamAbortRef.current = null;
        setLoading(false);
        refreshConversations(
          showArchivedConversations,
          selectedFolderId,
          selectedWorkspaceId,
          selectedProjectId,
          conversationSearch,
          showTrashConversations,
          selectedTagId
        );
        void maybeAutoSummarizeConversation(
          targetConversationId,
          messageCountRef.current
        );
      },
      onError: (message) => {
        streamAbortRef.current = null;
        setLoading(false);
        setError(message);
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && last.text === "") {
            const next = prev.slice(0, -1);
            messageCountRef.current = next.length;
            return next;
          }
          messageCountRef.current = prev.length;
          return prev;
        });
        setRetryableUserMessage({
          conversationId: targetConversationId,
          text: retryableUserMessage.text,
        });
      },
    });
  };

  const { regenerateLastResponse } = useRegenerateLastResponse({
    readOnlyConversation,
    conversationId,
    loading,
    lastAssistantIndex,
    messages,
    autoSummaryLastMessageCountRef,
    streamAbortRef,
    messageCountRef,
    setRetryableUserMessage,
    setError,
    setMessages,
    setLoading,
    setConversationId,
    refreshConversations,
    showArchivedConversations,
    selectedFolderId,
    selectedWorkspaceId,
    selectedProjectId,
    maybeAutoSummarizeConversation,
  });

  const commandPaletteActions = [
    {
      id: "new-chat",
      label: t("commandPalette.actions.newChat"),
      keywords: ["new", "chat", "محادثة"],
      icon: "＋",
      onSelect: startNewChat,
    },
    {
      id: "archived",
      label: showArchivedConversations
        ? t("commandPalette.actions.backToChats")
        : t("commandPalette.actions.archived"),
      keywords: ["archive", "archived", "أرشيف", "المؤرشفة"],
      icon: "▱",
      onSelect: () => {
        const next = !showArchivedConversations;
        setShowArchivedConversations(next);
        setShowTrashConversations(false);
        refreshConversations(
          next,
          selectedFolderId,
          selectedWorkspaceId,
          selectedProjectId,
          conversationSearch,
          false
        );
        if (next) startNewChat();
      },
    },
    {
      id: "trash",
      label: showTrashConversations
        ? t("commandPalette.actions.backToChats")
        : t("commandPalette.actions.trash"),
      keywords: ["trash", "deleted", "سلة", "محذوفة"],
      icon: "🗑",
      onSelect: () => {
        const next = !showTrashConversations;
        setShowTrashConversations(next);
        setShowArchivedConversations(false);
        setSelectedFolderId(null);
        setSelectedConversationIds([]);
        if (next) startNewChat();
        refreshConversations(
          false,
          next ? null : selectedFolderId,
          selectedWorkspaceId,
          next ? null : selectedProjectId,
          conversationSearch,
          next
        );
      },
    },
    {
      id: "files",
      label: t("commandPalette.actions.files"),
      keywords: ["files", "pdf", "ملفات"],
      icon: "📎",
      onSelect: () => setShowFiles(true),
    },
    {
      id: "account",
      label: t("commandPalette.actions.account"),
      keywords: ["account", "profile", "حساب"],
      icon: "👤",
      onSelect: () => setShowAccountSettings(true),
    },
    {
      id: "billing",
      label: t("commandPalette.actions.billing"),
      keywords: ["billing", "subscription", "اشتراك"],
      icon: "💳",
      onSelect: () => setShowBilling(true),
    },
    {
      id: "new-folder",
      label: t("commandPalette.actions.newFolder"),
      keywords: ["folder", "folders", "مجلد"],
      icon: "📁",
      onSelect: handleCreateFolder,
    },
    {
      id: "new-project",
      label: t("commandPalette.actions.newProject"),
      keywords: ["project", "projects", "مشروع"],
      icon: "🗂",
      onSelect: handleCreateProject,
    },
    {
      id: "new-assistant",
      label: t("commandPalette.actions.newAssistant"),
      keywords: ["assistant", "مساعد"],
      icon: "🤖",
      onSelect: openCreateAssistantEditor,
    },
    {
      id: "scheduled-tasks",
      label: t("commandPalette.actions.scheduledTasks"),
      keywords: ["schedule", "task", "مهام", "مجدولة"],
      icon: "⏰",
      onSelect: () => setShowScheduledTasks(true),
    },
    ...(currentUser?.role === "admin"
      ? [{
          id: "admin",
          label: t("commandPalette.actions.admin"),
          keywords: ["admin", "dashboard", "إدارة"],
          icon: "⚙",
          onSelect: () => setShowAdmin(true),
        }]
      : []),
  ];


  const path = normalizedPath;
  if (path.startsWith("/public-assistant/")) {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <PublicAssistantPage />
      </Suspense>
    );
  }
  if (path === "/workspace-invite") {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <WorkspaceInvitePage />
      </Suspense>
    );
  }
  if (path.startsWith("/share/")) {
    return (
      <Suspense fallback={<ModalLoadingFallback />}>
        <SharedConversationPage />
      </Suspense>
    );
  }
  if (path === "/terms") {
    return <TermsPage />;
  }
  if (path === "/privacy") {
    return <PrivacyPage />;
  }
  if (path === "/pricing") {
    return <PricingPage />;
  }
  if (path === "/verify-email") {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <VerifyEmailPage />
      </Suspense>
    );
  }
  if (path === "/reset-password") {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <ResetPasswordPage />
      </Suspense>
    );
  }
  if (path === "/billing/success") {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <BillingSuccessPage />
      </Suspense>
    );
  }
  if (path === "/billing/cancel") {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <BillingCancelPage />
      </Suspense>
    );
  }

  if (!authed) {
    return (
      <>
        <AuthForm
          onAuthenticated={() => {
            setAuthed(true);
            setToast({ message: t("app.loginSuccess"), type: "success" });
          }}
        />
        <Toast message={toast?.message} type={toast?.type} onDismiss={() => setToast(null)} />
      <CommandPalette
        open={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        actions={commandPaletteActions}
      />
      </>
    );
  }

  return (
    <div className="app-shell flex h-full bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <SidebarModern
        conversations={conversations}
        selectedConversationId={conversationId}
        onSelectConversation={openConversation}
        onNewChat={startNewChat}
        onImportConversation={handleImportConversation}
        onRenameConversation={handleRenameConversation}
        onDeleteConversation={handleDeleteConversation}
        onTogglePinConversation={handleTogglePinConversation}
        onDuplicateConversation={handleDuplicateConversation}
        onToggleArchiveConversation={handleToggleArchiveConversation}
        onToggleTrashConversation={handleToggleTrashConversation}
        showTrash={showTrashConversations}
        assistants={assistants}
        selectedAssistantId={selectedAssistantId}
        onSelectAssistant={handleSelectAssistant}
        onCreateAssistant={openCreateAssistantEditor}
        onEditAssistant={openEditAssistantEditor}
        onDeleteAssistant={handleDeleteAssistant}
        onToggleShareAssistant={handleToggleAssistantShare}
        bookmarkedMessages={bookmarkedMessages}
        onOpenBookmarkedMessage={handleOpenBookmarkedMessage}
        savedPrompts={savedPrompts}
        onCreateSavedPrompt={handleCreateSavedPrompt}
        onRenameSavedPrompt={handleRenameSavedPrompt}
        onDeleteSavedPrompt={handleDeleteSavedPrompt}
        onUseSavedPrompt={handleUseSavedPrompt}
        folders={folders}
        selectedFolderId={selectedFolderId}
        selectedWorkspaceId={selectedWorkspaceId}
        selectedWorkspaceRole={
          workspaces.find((workspace) => workspace.id === selectedWorkspaceId)?.role || "member"
        }
        onSelectFolder={handleSelectFolder}
        onCreateFolder={handleCreateFolder}
        onRenameFolder={handleRenameFolder}
        onDeleteFolder={handleDeleteFolder}
        onMoveFolder={handleMoveFolder}
        onMoveConversationToFolder={handleMoveConversationToFolder}
        projects={projects}
        currentUserId={currentUser?.id}
        selectedProjectId={selectedProjectId}
        onSelectProject={handleSelectProject}
        onCreateProject={handleCreateProject}
        onImportProject={handleImportProject}
        onExportProject={handleExportProject}
        onRenameProject={handleRenameProject}
        onDeleteProject={handleDeleteProject}
        onMoveConversationToProject={handleMoveConversationToProject}
        tags={tags}
        selectedTagId={selectedTagId}
        onSelectTag={handleSelectTag}
        onCreateTag={handleCreateTag}
        onRenameTag={handleRenameTag}
        onDeleteTag={handleDeleteTag}
        onSetConversationTags={handleSetConversationTags}
        selectedConversationIds={selectedConversationIds}
        onToggleConversationSelection={toggleConversationSelection}
        onToggleSelectAllVisible={toggleSelectAllVisibleConversations}
        onClearSelectedConversations={clearSelectedConversations}
        onBulkArchive={handleBulkArchive}
        onBulkDelete={handleBulkDelete}
        onBulkExport={handleBulkExport}
        onBulkMoveToFolder={handleBulkMoveToFolder}
        workspaces={workspaces}
        onSelectWorkspace={handleSelectWorkspace}
        onCreateWorkspace={handleCreateWorkspace}
        onRenameWorkspace={handleRenameWorkspace}
        onOpenWorkspaceMembers={handleOpenWorkspaceMembers}
        onOpenScheduledTasks={() => setShowScheduledTasks(true)}
        onOpenWorkspaceSharedConversation={handleOpenWorkspaceSharedConversation}
        onDuplicatedWorkspaceConversation={handleDuplicatedWorkspaceConversation}
        searchValue={conversationSearch}
        onSearchChange={setConversationSearch}
        showArchived={showArchivedConversations}
        onShowArchived={(value) => {
          setShowArchivedConversations(value);
          if (value) setShowTrashConversations(false);
          refreshConversations(value, selectedFolderId, selectedWorkspaceId, selectedProjectId, conversationSearch, false);
          if (value) startNewChat();
        }}
        onShowTrash={(value) => {
          setShowTrashConversations(value);
          if (value) setShowArchivedConversations(false);
          if (value) {
            setSelectedFolderId(null);
            setSelectedConversationIds([]);
            startNewChat();
          }
          refreshConversations(false, value ? null : selectedFolderId, selectedWorkspaceId, value ? null : selectedProjectId, conversationSearch, value);
        }}
        loading={conversationsLoading}
        loadingMore={conversationsLoadingMore}
        hasMore={hasMoreConversations}
        onLoadMore={loadMoreConversations}
      />
      <main className="app-main flex flex-1 flex-col">
        <ChatHeaderModern
          conversationTitle={conversations.find((item) => Number(item.id) === Number(conversationId))?.title || ""}
          lang={lang}
          setLang={switchLang}
          onLogout={logout}
          onOpenAccount={() => setShowAccountSettings(true)}
          onOpenFiles={() => setShowFiles(true)}
          onOpenAdmin={() => setShowAdmin(true)}
          onOpenBilling={() => setShowBilling(true)}
          onShareConversation={handleShareConversation}
          canShareConversation={conversationId !== null && !loading && !readOnlyConversation}
          onManageShares={handleManageConversationShares}
          canManageShares={conversationId !== null && !loading && !readOnlyConversation}
          onToggleWorkspaceShare={handleToggleWorkspaceShare}
          canShareWithWorkspace={conversationId !== null && selectedWorkspaceId !== null && !loading && !readOnlyConversation}
          workspaceShareActive={Boolean(workspaceShare)}
          onExportConversation={handleExportConversation}
          canExportConversation={conversationId !== null && !loading && !readOnlyConversation}
          onSummarizeConversation={handleSummarizeConversation}
          canSummarizeConversation={conversationId !== null && !loading}
          summaryLoading={summaryLoading}
          onGenerateConversationTitle={handleGenerateConversationTitle}
          canGenerateConversationTitle={conversationId !== null && !loading && !readOnlyConversation}
          titleLoading={titleLoading}
          conversationBranches={conversationBranches}
          onOpenConversationBranch={openConversation}
          parentConversationId={parentConversationId}
          onOpenParentConversation={openConversation}
          isAdmin={currentUser?.role === "admin"}
          projectName={projects.find((project) => Number(project.id) === Number(selectedProjectId))?.name || ""}
          canEditProject={(() => {
            const project = projects.find(
              (item) => Number(item.id) === Number(selectedProjectId)
            );
            const workspaceRole = workspaces.find(
              (workspace) => workspace.id === selectedWorkspaceId
            )?.role;
            return Boolean(
              project &&
              (
                Number(project.owner_id) === Number(currentUser?.id) ||
                ["owner", "admin"].includes(workspaceRole) ||
                ["editor", "manager"].includes(projectMemberRoles[project.id])
              )
            );
          })()}
          onEditProject={() => {
            if (selectedProjectId !== null) handleRenameProject(selectedProjectId);
          }}
          notifications={notifications}
          onMarkNotificationRead={handleMarkNotificationRead}
          onMarkAllNotificationsRead={handleMarkAllNotificationsRead}
        />

        <section className="chat-stage flex flex-1 flex-col p-3 sm:p-4">
          {conversationId &&
          selectedWorkspaceId !== null &&
          (workspaceShare || readOnlyConversation) ? (
            <div className="mb-3">
              <button
                type="button"
                onClick={() => setShowWorkspaceComments((current) => !current)}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                {showWorkspaceComments
                  ? t("workspaceComments.hide")
                  : t("workspaceComments.button")}
              </button>
              {showWorkspaceComments ? (
                <div className="mt-2">
                  <WorkspaceConversationCommentsPanel
                    workspaceId={selectedWorkspaceId}
                    conversationId={conversationId}
                  />
                </div>
              ) : null}
            </div>
          ) : null}
          {conversationId && (conversationSummary || summaryLoading) ? (
            <div className="chat-summary mb-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {t("summary.title")}
                  </h3>
                  {conversationSummaryUpdatedAt ? (
                    <p className="mt-1 text-xs text-slate-400">
                      {t("summary.updatedAt", {
                        date: new Date(conversationSummaryUpdatedAt).toLocaleString(),
                      })}
                    </p>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={handleSummarizeConversation}
                  disabled={loading || summaryLoading}
                  className="rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  {summaryLoading ? t("summary.loading") : t("summary.refresh")}
                </button>
              </div>
              <div className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700 dark:text-slate-200">
                {summaryLoading && !conversationSummary ? t("summary.loading") : conversationSummary}
              </div>
            </div>
          ) : null}

          <div className="chat-surface mx-auto flex w-full max-w-4xl flex-1 space-y-3 overflow-y-auto rounded-3xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
            {empty ? (
              <div className="empty-state flex h-full flex-col items-center justify-center px-4 text-center">
                <div className="mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-slate-900 text-xs font-extrabold tracking-[0.12em] text-white shadow-lg dark:bg-slate-100 dark:text-slate-900">AI</div>
                <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{t("emptyTitle")}</h3>
                <p className="mt-2 max-w-lg text-sm leading-6 text-slate-500 dark:text-slate-400">{t("emptyDesc")}</p>
                <div className="mt-6 grid w-full max-w-xl grid-cols-1 gap-2 sm:grid-cols-2">
                  {[
                    { label: document.documentElement.lang === "ar" ? "اشرح لي شيئًا" : "Explain something", value: document.documentElement.lang === "ar" ? "اشرح لي موضوعًا بطريقة بسيطة مع أمثلة." : "Explain a topic simply with examples." },
                    { label: document.documentElement.lang === "ar" ? "حلل ملفًا" : "Analyze a file", value: document.documentElement.lang === "ar" ? "سأرفع ملفًا. ساعدني في تحليله واستخراج أهم النقاط." : "I will upload a file. Help me analyze it and extract the key points." },
                    { label: document.documentElement.lang === "ar" ? "اكتب كودًا" : "Write code", value: document.documentElement.lang === "ar" ? "اكتب لي مثالًا برمجيًا وفسّر الكود خطوة بخطوة." : "Write a coding example and explain it step by step." },
                    { label: document.documentElement.lang === "ar" ? "ساعدني على التعلم" : "Help me learn", value: document.documentElement.lang === "ar" ? "أنشئ لي خطة تعلم عملية لهذا الموضوع." : "Create a practical learning plan for this topic." },
                  ].map((prompt) => (
                    <button
                      key={prompt.label}
                      type="button"
                      onClick={() => setInput(prompt.value)}
                      className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-start text-sm font-medium text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-slate-600 dark:hover:bg-slate-800"
                    >
                      {prompt.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, index) => {
                const isPendingAssistantBubble =
                  index === messages.length - 1 &&
                  msg.role === "assistant" &&
                  msg.text === "" &&
                  loading;
                if (isPendingAssistantBubble) return null;
                return (
                  <ChatMessage
                    key={index}
                    role={msg.role}
                    text={msg.text}
                    time={msg.time}
                    sources={msg.sources}
                    feedback={msg.feedback ?? null}
                    isBookmarked={msg.isBookmarked ?? false}
                    onToggleBookmark={() => handleToggleMessageBookmark(index)}
                    canRemember={
                      msg.role === "user" &&
                      !loading &&
                      editingMessageIndex === null &&
                      conversationId !== null &&
                      !readOnlyConversation
                    }
                    isRemembered={msg.role === "user" && memories.some((memory) => memory.content === msg.text)}
                    onToggleRemember={() => handleToggleMessageMemory(index)}
                    canFeedback={
                      msg.role === "assistant" &&
                      !loading &&
                      editingMessageIndex === null &&
                      conversationId !== null &&
                      !readOnlyConversation
                    }
                    onFeedback={(rating) => handleMessageFeedback(index, rating)}
                    canEdit={
                      msg.role === "user" &&
                      !loading &&
                      editingMessageIndex === null &&
                      conversationId !== null &&
                      !readOnlyConversation
                    }
                    onEdit={() => startEditingMessage(index)}
                    canDelete={
                      !loading &&
                      editingMessageIndex === null &&
                      conversationId !== null &&
                      !readOnlyConversation
                    }
                    onDelete={() => deleteMessage(index)}
                    canBranch={
                      !loading &&
                      editingMessageIndex === null &&
                      conversationId !== null &&
                      !readOnlyConversation
                    }
                    onBranch={() => handleBranchConversation(index)}
                    canRegenerate={
                      index === lastAssistantIndex &&
                      !loading &&
                      editingMessageIndex === null &&
                      conversationId !== null &&
                      !readOnlyConversation
                    }
                    onRegenerate={regenerateLastResponse}
                  />
                );
              })
            )}

            {loading && (
              <div className="flex justify-start">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
                  {toolActivity ? (
                    <span className="inline-flex items-center gap-2">
                      <span
                        aria-hidden="true"
                        className={toolActivity.phase === "running" ? "animate-pulse" : ""}
                      >
                        {toolActivity.phase === "error" || toolActivity.phase === "warning"
                          ? "⚠️"
                          : toolActivity.phase === "done"
                            ? "✓"
                            : toolActivity.phase === "cancelled"
                              ? "⏹️"
                              : "⚙️"}
                      </span>
                      <span>
                        {toolActivity.message
                          ? toolActivity.message
                          : toolActivity.phase === "running"
                            ? t("tools.activity.running", { tool: toolActivityLabel(toolActivity.name) })
                            : toolActivity.phase === "done"
                              ? t("tools.activity.done", {
                                  tool: toolActivityLabel(toolActivity.name),
                                  duration: toolActivity.duration_ms ?? 0,
                                })
                              : t("tools.activity.error", { tool: toolActivityLabel(toolActivity.name) })}
                      </span>
                    </span>
                  ) : (
                    t("typing")
                  )}
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {error && (
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <span>{error}</span>
              {retryableUserMessage?.conversationId === conversationId &&
              !loading &&
              !readOnlyConversation ? (
                <button
                  type="button"
                  onClick={retryFailedGeneration}
                  className="rounded-xl border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-300 dark:border-red-800 dark:bg-slate-900 dark:text-red-300 dark:hover:bg-red-950"
                >
                  {t("app.retryLastMessage")}
                </button>
              ) : null}
            </div>
          )}
        </section>

        {readOnlyConversation ? (
          <div className="readonly-bar border-t border-slate-200 bg-white px-4 py-3 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
            {t("workspaceSharing.readOnly")}
          </div>
        ) : (
          <div className="composer-stage mx-auto w-full max-w-4xl">
          <ChatComposer
            value={input}
          setValue={setInput}
          onInsertCalculator={() =>
            setInput((current) =>
              current.trim() ? `/calc ${current.trim()}` : "/calc "
            )
          }
          onInsertWebSearch={() =>
            setInput((current) =>
              current.trim() ? `/search ${current.trim()}` : "/search "
            )
          }
          onInsertDataAnalysis={() =>
            setInput((current) =>
              current.trim() ? `/analyze ${current.trim()}` : "/analyze "
            )
          }
          onInsertAgent={() =>
            setInput((current) =>
              current.trim() ? `/agent ${current.trim()}` : "/agent "
            )
          }
          onInsertPython={() =>
            setInput((current) =>
              current.trim() ? `/python ${current.trim()}` : "/python "
            )
          }
          onSend={sendMessage}
          onStop={stopGeneration}
          loading={loading}
          isEditing={editingMessageIndex !== null}
          onCancelEdit={cancelEditing}
          onVoiceError={(message) => setToast({ message, type: "error" })}
          attachments={chatAttachments}
          onAttachFiles={handleAttachFiles}
          onRemoveAttachment={handleRemoveAttachment}
          onCompareModels={() => setShowModelCompare(true)}
          attachmentUploading={chatAttachmentUploading}
          models={aiModels}
          selectedModel={selectedModel}
          onSelectModel={setSelectedModel}
          />
          </div>
        )}
      </main>

      <Toast message={toast?.message} type={toast?.type} onDismiss={() => setToast(null)} />

      {showOnboarding ? (
        <OnboardingModal
          onClose={closeOnboarding}
          onNewChat={() => {
            startNewChat();
            closeOnboarding();
          }}
          onOpenFiles={() => {
            setShowFiles(true);
            closeOnboarding();
          }}
          onOpenAccount={() => {
            setShowAccountSettings(true);
            closeOnboarding();
          }}
        />
      ) : null}

      {showShareManager && conversationId && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <ConversationShareManager
            conversationId={conversationId}
            onClose={() => setShowShareManager(false)}
            onChanged={() => setToast({ message: t("sharing.managementUpdated"), type: "success" })}
          />
        </Suspense>
      )}

      {showAccountSettings && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <AccountSettings
            user={currentUser}
            notificationToastsEnabled={notificationPreferences.realtimeToasts}
            onNotificationToastsChanged={handleNotificationToastsChanged}
            autoGenerateTitles={autoGenerateTitles}
            onAutoGenerateTitlesChanged={setAutoGenerateTitles}
            autoGenerateSummaries={autoGenerateSummaries}
            onAutoGenerateSummariesChanged={setAutoGenerateSummaries}
            onClose={() => setShowAccountSettings(false)}
            onUserUpdated={refreshCurrentUser}
            onAccountDeleted={logout}
          />
        </Suspense>
      )}

      {showFiles && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <FilesPanel
            conversationId={conversationId}
            workspaceId={selectedWorkspaceId}
            projectId={selectedProjectId}
            onAnalyzeImage={handleAnalyzeImage}
            onClose={() => setShowFiles(false)}
          />
        </Suspense>
      )}

      {showAdmin && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <AdminDashboard currentUserId={currentUser?.id} onClose={() => setShowAdmin(false)} />
        </Suspense>
      )}

      {showAssistantEditor && (
        <AssistantEditor
          assistant={
            editingAssistantId === null
              ? null
              : assistants.find((assistant) => assistant.id === editingAssistantId) || null
          }
          onClose={() => {
            setShowAssistantEditor(false);
            setEditingAssistantId(null);
          }}
          onSave={handleSaveAssistant}
          onRestored={handleAssistantRestored}
        />
      )}

      {showProjectEditor && (
        <ProjectEditor
          assistants={assistants}
          project={
            editingProjectId === null
              ? null
              : projects.find((project) => project.id === editingProjectId) || null
          }
          onClose={() => {
            setShowProjectEditor(false);
            setEditingProjectId(null);
          }}
          onSave={handleSaveProject}
          onExport={editingProjectId === null ? null : handleExportProject}
          currentUserId={currentUser?.id}
          workspaceRole={
            workspaces.find((workspace) => workspace.id === selectedWorkspaceId)?.role ||
            "member"
          }
        />
      )}

      {showModelCompare && (
        <ModelCompareDialog
          models={aiModels}
          initialPrompt={input}
          conversationId={conversationId}
          workspaceId={selectedWorkspaceId}
          projectId={selectedProjectId}
          assistantId={selectedAssistantId}
          onClose={() => setShowModelCompare(false)}
        />
      )}

      {showBilling && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <BillingPanel onClose={() => setShowBilling(false)} />
        </Suspense>
      )}

      {showScheduledTasks && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <ScheduledTasksPanel
            workspaces={workspaces}
            selectedWorkspaceId={selectedWorkspaceId}
            onClose={() => setShowScheduledTasks(false)}
          />
        </Suspense>
      )}

      {showWorkspaceMembers && selectedWorkspaceId !== null && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <WorkspaceMembersPanel
            workspaceId={selectedWorkspaceId}
            workspaceName={
              workspaces.find((workspace) => workspace.id === selectedWorkspaceId)?.name || ""
            }
            workspaceRole={
              workspaces.find((workspace) => workspace.id === selectedWorkspaceId)?.role || "member"
            }
            defaultAiModel={
              workspaces.find((workspace) => workspace.id === selectedWorkspaceId)?.default_ai_model || ""
            }
            dailyAiRequestLimit={
              workspaces.find((workspace) => workspace.id === selectedWorkspaceId)?.daily_ai_request_limit ?? null
            }
            availableModels={aiModels}
            onWorkspaceUpdated={handleWorkspaceUpdated}
            onQuotaUpdated={handleWorkspaceQuotaUpdated}
            onClose={() => setShowWorkspaceMembers(false)}
          />
        </Suspense>
      )}
    </div>
  );
}
