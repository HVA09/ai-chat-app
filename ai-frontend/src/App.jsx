import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Sidebar from "./components/Sidebar";
import ChatHeader from "./components/ChatHeader";
import ChatMessage from "./components/ChatMessage";
import ChatComposer from "./components/ChatComposer";
import AssistantEditor from "./components/AssistantEditor";
import AuthForm from "./components/AuthForm";
import Toast from "./components/Toast";
import useDirection from "./hooks/useDirection";
import { streamChatMessage, streamRegenerateMessage, streamEditMessage, setMessageFeedback, analyzeImage, listAiModels } from "./lib/chatApi";
import { listBookmarkedMessages, toggleMessageBookmark } from "./lib/bookmarksApi";
import api, { restoreSession } from "./lib/api";
import { createConversationShare } from "./lib/sharedConversationsApi";
import {
  getConversationWorkspaceShare,
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
const BillingSuccessPage = lazy(() => import("./components/BillingSuccessPage"));
const BillingCancelPage = lazy(() => import("./components/BillingCancelPage"));
const TermsPage = lazy(() => import("./components/TermsPage"));
const PrivacyPage = lazy(() => import("./components/PrivacyPage"));
const PricingPage = lazy(() => import("./components/PricingPage"));
const SharedConversationPage = lazy(() => import("./components/SharedConversationPage"));
const WorkspaceMembersPanel = lazy(() => import("./components/WorkspaceMembersPanel"));
const WorkspaceInvitePage = lazy(() => import("./components/WorkspaceInvitePage"));
const ConversationShareManager = lazy(() => import("./components/ConversationShareManager"));
import {
  listConversations,
  getConversation,
  renameConversation,
  deleteConversation,
  togglePinConversation,
  toggleArchiveConversation,
  toggleTrashConversation,
  moveConversationToFolder,
  duplicateConversation,
  branchConversation,
  listConversationBranches,
  exportConversation,
  importConversation,
  summarizeConversation,
  generateConversationTitle,
} from "./lib/conversationsApi";
import {
  listFolders,
  createFolder,
  renameFolder,
  deleteFolder,
} from "./lib/foldersApi";
import {
  listProjects,
  createProject,
  updateProject,
  deleteProject,
  moveConversationToProject,
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
import {
  listSavedPrompts,
  createSavedPrompt,
  updateSavedPrompt,
  deleteSavedPrompt,
} from "./lib/savedPromptsApi";
import { getCurrentUser } from "./lib/usersApi";
import {
  listNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  buildNotificationsWebSocketUrl,
} from "./lib/notificationsApi";
import "./i18n";

// دالة بدل ثابت — لازم نستدعيها بعد ما يصير عندنا t() جوا المكوّن عشان رسالة
// الترحيب تتبدّل مع تبديل اللغة
function getWelcomeMessage(t) {
  return { role: "assistant", text: t("app.welcomeMessage"), time: t("app.now") };
}

function PageLoadingFallback() {
  if (sessionChecking) return <PageLoadingFallback />;

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
  const [conversations, setConversations] = useState([]);
  const [selectedConversationIds, setSelectedConversationIds] = useState([]);
  const [conversationSearch, setConversationSearch] = useState("");
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [conversationsLoadingMore, setConversationsLoadingMore] = useState(false);
  const [hasMoreConversations, setHasMoreConversations] = useState(false);
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
  const [savedPrompts, setSavedPrompts] = useState([]);
  const [bookmarkedMessages, setBookmarkedMessages] = useState([]);
  const [aiModels, setAiModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null); // { message, type }
  const [currentUser, setCurrentUser] = useState(null);
  const [showAccountSettings, setShowAccountSettings] = useState(false);
  const [showFiles, setShowFiles] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [showBilling, setShowBilling] = useState(false);
  const [showWorkspaceMembers, setShowWorkspaceMembers] = useState(false);
  const [showShareManager, setShowShareManager] = useState(false);
  const [workspaceShare, setWorkspaceShare] = useState(null);
  const [readOnlyConversation, setReadOnlyConversation] = useState(false);
  const [conversationSummary, setConversationSummary] = useState(null);
  const [conversationSummaryUpdatedAt, setConversationSummaryUpdatedAt] = useState(null);
  const [conversationBranches, setConversationBranches] = useState([]);
  const [parentConversationId, setParentConversationId] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [titleLoading, setTitleLoading] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [editingMessageIndex, setEditingMessageIndex] = useState(null);
  const bottomRef = useRef(null);
  const streamAbortRef = useRef(null);

  useDirection();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const empty = useMemo(() => messages.length === 0, [messages.length]);
  const lastAssistantIndex = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (messages[index].role === "assistant") return index;
    }
    return -1;
  }, [messages]);

  const logout = useCallback(async () => {
    try { await api.post("/auth/logout"); } catch { /* session may already be gone */ }
    setAuthed(false);
    setConversations([]);
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
    setSavedPrompts([]);
    setBookmarkedMessages([]);
    setAiModels([]);
    setSelectedModel("");
    setSelectedFolderId(null);
    setSelectedAssistantId(null);
    setConversationId(null);
    setParentConversationId(null);
    setConversationSummary(null);
    setConversationSummaryUpdatedAt(null);
    setMessages([getWelcomeMessage(t)]);
    setInput("");
    setEditingMessageIndex(null);
    setError("");
    setCurrentUser(null);
    setShowAccountSettings(false);
    setShowFiles(false);
    setShowAdmin(false);
    setShowBilling(false);
    setShowWorkspaceMembers(false);
    setShowShareManager(false);
    setWorkspaceShare(null);
    setReadOnlyConversation(false);
    setShowTrashConversations(false);
    setConversationSummary(null);
    setConversationSummaryUpdatedAt(null);
    setSummaryLoading(false);
    setNotifications([]);
  }, [t]);

  useEffect(() => {
    restoreSession().then(() => setAuthed(true)).catch(() => setAuthed(false)).finally(() => setSessionChecking(false));
  }, []);

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

  const refreshAiModels = async () => {
    try {
      const data = await listAiModels();
      const models = Array.isArray(data) ? data : data.models || [];
      setAiModels(models);
      const fallback = models.find((model) => model.is_default)?.id || models[0]?.id || "";
      setSelectedModel((current) =>
        current && models.some((model) => model.id === current) ? current : fallback
      );
    } catch {
      // فشل تحميل النماذج لا يمنع استخدام النموذج الافتراضي.
    }
  };

  const refreshConversations = async (
    includeArchived = showArchivedConversations,
    folderId = selectedFolderId,
    workspaceId = selectedWorkspaceId,
    projectId = selectedProjectId,
    search = conversationSearch,
    includeDeleted = showTrashConversations,
    tagId = selectedTagId,
    reset = true
  ) => {
    const pageSize = 50;
    if (reset) setConversationsLoading(true);
    else setConversationsLoadingMore(true);

    try {
      const list = await listConversations(
        includeArchived,
        folderId,
        workspaceId,
        projectId,
        search,
        includeDeleted,
        tagId,
        reset ? 0 : conversations.length,
        pageSize + 1
      );
      const page = list.slice(0, pageSize);

      if (reset) {
        setConversations(page);
      } else {
        setConversations((current) => {
          const existingIds = new Set(current.map((item) => item.id));
          return [...current, ...page.filter((item) => !existingIds.has(item.id))];
        });
      }

      setHasMoreConversations(list.length > pageSize);
    } catch {
      // فشل تحميل القائمة لا يوقف الشات نفسه — نتجاهله بصمت
    } finally {
      if (reset) setConversationsLoading(false);
      else setConversationsLoadingMore(false);
    }
  };

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
    } catch {
      setProjects([]);
      setSelectedProjectId(null);
    }
  };

  const loadMoreConversations = async () => {
    if (!hasMoreConversations || conversationsLoading || conversationsLoadingMore) return;
    await refreshConversations(
      showArchivedConversations,
      selectedFolderId,
      selectedWorkspaceId,
      selectedProjectId,
      conversationSearch,
      showTrashConversations,
      selectedTagId,
      false
    );
  };

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
    } catch {
      // فشل تحميل الوسوم لا يوقف الشات.
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
    try {
      const list = await listWorkspaces();
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
    } catch {
      // فشل تحميل مساحات العمل لا يوقف الشات.
    }
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
    } catch {
      // فشل تحميل المجلدات لا يوقف الشات.
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

  const handleRenameFolder = async (id, newName) => {
    try {
      await renameFolder(id, newName);
      await refreshFolders(selectedWorkspaceId);
      await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId);
    } catch {
      setToast({ message: t("app.folderRenameError"), type: "error" });
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

  const handleCreateProject = async () => {
    if (selectedWorkspaceId === null) return;
    const name = window.prompt(t("sidebar.projectCreatePrompt"));
    if (!name?.trim()) return;
    const description = window.prompt(t("sidebar.projectCreateDescriptionPrompt"), "");
    try {
      const project = await createProject(selectedWorkspaceId, name.trim(), description?.trim() || "");
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
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.projectCreateError"),
        type: "error",
      });
    }
  };

  const handleRenameProject = async (id, currentName, currentDescription) => {
    const name = window.prompt(t("sidebar.projectRenamePrompt"), currentName);
    if (!name?.trim()) return;
    const description = window.prompt(
      t("sidebar.projectEditDescriptionPrompt"),
      currentDescription || ""
    );
    try {
      await updateProject(id, name.trim(), description?.trim() || "");
      await refreshProjects(selectedWorkspaceId);
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId
      );
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.projectUpdateError"),
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
    setSelectedProjectId(id);
    setSelectedFolderId(null);
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

  const refreshBookmarkedMessages = async () => {
    try {
      setBookmarkedMessages(await listBookmarkedMessages());
    } catch {
      // فشل تحميل المحفوظات لا يوقف الشات.
    }
  };

  const refreshSavedPrompts = async () => {
    try {
      setSavedPrompts(await listSavedPrompts());
    } catch {
      // فشل تحميل الموجهات المحفوظة لا يوقف الشات.
    }
  };

  const handleCreateSavedPrompt = async () => {
    const name = window.prompt(t("sidebar.savedPromptCreateNamePrompt"));
    if (!name?.trim()) return;
    const content = window.prompt(t("sidebar.savedPromptCreateContentPrompt"));
    if (!content?.trim()) return;
    try {
      await createSavedPrompt(name.trim(), content.trim());
      await refreshSavedPrompts();
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.savedPromptCreateError"),
        type: "error",
      });
    }
  };

  const handleRenameSavedPrompt = async (id, currentName, currentContent) => {
    const name = window.prompt(
      t("sidebar.savedPromptRenameNamePrompt"),
      currentName
    );
    if (!name?.trim()) return;
    const content = window.prompt(
      t("sidebar.savedPromptRenameContentPrompt"),
      currentContent
    );
    if (!content?.trim()) return;
    try {
      await updateSavedPrompt(id, name.trim(), content.trim());
      await refreshSavedPrompts();
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.savedPromptUpdateError"),
        type: "error",
      });
    }
  };

  const handleDeleteSavedPrompt = async (id, name) => {
    if (!window.confirm(t("sidebar.savedPromptDeleteConfirm", { name }))) return;
    try {
      await deleteSavedPrompt(id);
      await refreshSavedPrompts();
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.savedPromptDeleteError"),
        type: "error",
      });
    }
  };

  const handleToggleMessageBookmark = async (index) => {
    if (!conversationId || loading || readOnlyConversation) return;
    try {
      const result = await toggleMessageBookmark(conversationId, index + 1);
      setMessages((prev) =>
        prev.map((message, messageIndex) =>
          messageIndex === index
            ? { ...message, isBookmarked: result.bookmarked }
            : message
        )
      );
      await refreshBookmarkedMessages();
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.bookmarkError"),
        type: "error",
      });
    }
  };

  const handleOpenBookmarkedMessage = async (item) => {
    await openConversation(item.conversation_id);
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
    } catch {
      // فشل تحميل المساعدين لا يوقف الشات.
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

  const handleSaveAssistant = async ({ name, description, instructions }) => {
    try {
      if (editingAssistantId === null) {
        const assistant = await createAssistant({ name, description, instructions });
        await refreshAssistants(selectedWorkspaceId);
        setSelectedAssistantId(assistant.id);
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
      setShowAssistantEditor(false);
      setEditingAssistantId(null);
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

  const toggleConversationSelection = (id) => {
    setSelectedConversationIds((prev) =>
      prev.includes(id) ? prev.filter((itemId) => itemId !== id) : [...prev, id]
    );
  };

  const toggleSelectAllVisibleConversations = (ids) => {
    setSelectedConversationIds((prev) => {
      const visible = new Set(ids);
      const allSelected = ids.length > 0 && ids.every((id) => prev.includes(id));
      if (allSelected) {
        return prev.filter((id) => !visible.has(id));
      }
      return Array.from(new Set([...prev, ...ids]));
    });
  };

  const clearSelectedConversations = () => setSelectedConversationIds([]);

  const handleBulkArchive = async () => {
    if (!selectedConversationIds.length) return;
    const results = await Promise.allSettled(
      selectedConversationIds.map((id) => toggleArchiveConversation(id))
    );
    const failed = results.filter((result) => result.status === "rejected").length;
    if (selectedConversationIds.includes(conversationId)) startNewChat();
    setSelectedConversationIds([]);
    await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId);
    if (failed) {
      setToast({
        message: t("app.bulkActionError", { count: failed }),
        type: "error",
      });
    }
  };

  const handleBulkDelete = async () => {
    if (!selectedConversationIds.length) return;
    const confirmed = window.confirm(
      t("sidebar.bulkDeleteConfirm", { count: selectedConversationIds.length })
    );
    if (!confirmed) return;

    const selectedIds = [...selectedConversationIds];
    const action = showTrashConversations ? deleteConversation : toggleTrashConversation;
    const results = await Promise.allSettled(
      selectedIds.map((id) => action(id))
    );
    const failed = results.filter((result) => result.status === "rejected").length;
    if (selectedIds.includes(conversationId)) startNewChat();
    setSelectedConversationIds([]);
    await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId);
    if (failed) {
      setToast({
        message: t("app.bulkActionError", { count: failed }),
        type: "error",
      });
    }
  };

  const handleBulkMoveToFolder = async (folderValue) => {
    if (!selectedConversationIds.length || folderValue === "") return;
    const folderId = folderValue === "__none__" ? null : Number(folderValue);
    const selectedIds = [...selectedConversationIds];
    const results = await Promise.allSettled(
      selectedIds.map((id) => moveConversationToFolder(id, folderId))
    );
    const failed = results.filter((result) => result.status === "rejected").length;
    if (selectedIds.includes(conversationId) && folderId !== selectedFolderId) {
      startNewChat();
    }
    setSelectedConversationIds([]);
    await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId);
    if (failed) {
      setToast({
        message: t("app.bulkActionError", { count: failed }),
        type: "error",
      });
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

  const refreshNotifications = async () => {
    try {
      setNotifications(await listNotifications());
    } catch {
      // فشل تحميل الإشعارات لا يوقف باقي التطبيق — نتجاهله بصمت
    }
  };

  useEffect(() => {
    if (authed) {
      refreshWorkspaces();
      refreshTags();
      refreshAssistants(selectedWorkspaceId);
      refreshSavedPrompts();
      refreshBookmarkedMessages();
      refreshCurrentUser();
      refreshNotifications();
    }
  }, [authed]);

  // اتصال WebSocket للإشعارات الفورية — يُفتح عند الدخول، ويُغلق عند الخروج
  useEffect(() => {
    if (!authed) return;

    const ws = new WebSocket(buildNotificationsWebSocketUrl());
    ws.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      setNotifications((prev) => [notification, ...prev]);
      setToast({ message: notification.title, type: "success" });
    };

    return () => ws.close();
  }, [authed]);

  const switchLang = (nextLang) => {
    setLang(nextLang);
    i18n.changeLanguage(nextLang);
  };

  const startNewChat = () => {
    setShowShareManager(false);
    setWorkspaceShare(null);
    setReadOnlyConversation(false);
    setSelectedConversationIds([]);
    setConversationId(null);
    setConversationBranches([]);
    setParentConversationId(null);
    setMessages([getWelcomeMessage(t)]);
    setInput("");
    setEditingMessageIndex(null);
    setError("");
  };

  const openConversation = async (id) => {
    setShowShareManager(false);
    setReadOnlyConversation(false);
    setSelectedConversationIds([]);
    setError("");
    setInput("");
    setEditingMessageIndex(null);
    try {
      const data = await getConversation(id);
      setConversationId(data.id);
      setParentConversationId(data.parent_conversation_id ?? null);
      try {
        setConversationBranches(await listConversationBranches(data.id));
      } catch {
        setConversationBranches([]);
      }
      setConversationSummary(data.summary ?? null);
      setConversationSummaryUpdatedAt(data.summary_updated_at ?? null);
      setSelectedAssistantId(data.assistant_id ?? null);
      setSelectedWorkspaceId(data.workspace_id ?? null);
      setSelectedFolderId(data.folder_id ?? null);
      setSelectedProjectId(data.project_id ?? null);
      setSelectedModel(
        data.ai_model ||
          aiModels.find((model) => model.is_default)?.id ||
          aiModels[0]?.id ||
          ""
      );
      try {
        setWorkspaceShare(await getConversationWorkspaceShare(data.id));
      } catch {
        setWorkspaceShare(null);
      }
      setMessages(
        data.messages.map((m) => ({
          role: m.role,
          text: m.content,
          time: new Date(m.created_at).toLocaleTimeString(),
          sources: m.sources ?? [],
          feedback: m.feedback ?? null,
          isBookmarked: m.is_bookmarked ?? false,
        }))
      );
    } catch {
      setError(t("app.conversationLoadError"));
    }
  };

  const handleOpenWorkspaceSharedConversation = async (workspaceId, sharedConversationId) => {
    try {
      const data = await getWorkspaceSharedConversation(
        Number(workspaceId),
        Number(sharedConversationId)
      );
      setShowShareManager(false);
      setReadOnlyConversation(true);
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
      await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId);
    } catch (err) {
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

  const handleGenerateConversationTitle = async () => {
    if (!conversationId || loading || titleLoading || readOnlyConversation) return;
    setTitleLoading(true);
    setError("");
    try {
      const result = await generateConversationTitle(conversationId);
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch,
        showTrashConversations,
        selectedTagId
      );
      setToast({ message: t("conversationTitle.generated"), type: "success" });
      return result;
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("conversationTitle.error"),
        type: "error",
      });
    } finally {
      setTitleLoading(false);
    }
  };

  const handleSummarizeConversation = async () => {
    if (!conversationId || loading || summaryLoading || readOnlyConversation) return;
    setSummaryLoading(true);
    setError("");
    try {
      const result = await summarizeConversation(conversationId);
      setConversationSummary(result.summary);
      setConversationSummaryUpdatedAt(result.summary_updated_at);
      setToast({ message: t("summary.saved"), type: "success" });
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("summary.error"),
        type: "error",
      });
    } finally {
      setSummaryLoading(false);
    }
  };

  const handleRenameConversation = async (id, newTitle) => {
    try {
      await renameConversation(id, newTitle);
      await refreshConversations();
    } catch {
      setToast({ message: t("app.renameConversationError"), type: "error" });
    }
  };

  const handleImportConversation = async (file) => {
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
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
      const share = await createConversationShare(conversationId, 7);
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

  const handleToggleTrashConversation = async (id) => {
    try {
      await toggleTrashConversation(id);
      if (id === conversationId) startNewChat();
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch,
        showTrashConversations
      );
    } catch {
      setToast({ message: t("app.trashConversationError"), type: "error" });
    }
  };

  const handleToggleArchiveConversation = async (id) => {
    try {
      const result = await toggleArchiveConversation(id);
      if (result.is_archived && id === conversationId) startNewChat();
      await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId);
    } catch {
      setToast({ message: t("app.archiveConversationError"), type: "error" });
    }
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

  const handleTogglePinConversation = async (id) => {
    try {
      await togglePinConversation(id);
      await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId);
    } catch {
      setToast({ message: t("app.pinConversationError"), type: "error" });
    }
  };

  const handleDeleteConversation = async (id) => {
    try {
      if (showTrashConversations) {
        await deleteConversation(id);
      } else {
        await toggleTrashConversation(id);
      }
      if (id === conversationId) startNewChat();
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch,
        showTrashConversations
      );
    } catch {
      setToast({
        message: showTrashConversations
          ? t("app.deleteConversationError")
          : t("app.trashConversationError"),
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
  };

  const cancelEditing = () => {
    setEditingMessageIndex(null);
    setInput("");
    setError("");
  };

  const startEditingMessage = (index) => {
    if (readOnlyConversation || loading || !conversationId || messages[index]?.role !== "user") return;
    setError("");
    setEditingMessageIndex(index);
    setInput(messages[index]?.text ?? "");
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
    setError("");
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
      onSources: (sources) => {
        setMessages((prev) => prev.map((message, index) =>
          index === targetIndex + 1 ? { ...message, sources } : message
        ));
      },
      onChunk: appendToLastMessage,
      onDone: () => {
        streamAbortRef.current = null;
        setLoading(false);
        refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId);
      },
      onError: (message) => {
        streamAbortRef.current = null;
        setLoading(false);
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
    if (!userText) return;

    setError("");
    setMessages((prev) => [
      ...prev,
      { role: "user", text: userText, time: new Date().toLocaleTimeString() },
      { role: "assistant", text: "", time: new Date().toLocaleTimeString(), feedback: null },
    ]);
    setInput("");
    setLoading(true);

    const controller = new AbortController();
    streamAbortRef.current = controller;

    const isNewConversation = !conversationId;
    let receivedFirstChunk = false;

    const appendToLastMessage = (chunk) => {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        next[next.length - 1] = { ...last, text: last.text + chunk };
        return next;
      });
    };

    await streamChatMessage(userText, conversationId, selectedAssistantId, {
      signal: controller.signal,
      workspaceId: selectedWorkspaceId,
      model: selectedModel || null,
      onConversationId: async (id) => {
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
      onDone: () => {
        streamAbortRef.current = null;
        setLoading(false);
        if (isNewConversation) {
          refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId);
        }
      },
      onError: (message) => {
        streamAbortRef.current = null;
        setLoading(false);
        setError(message);
        // نشيل فقاعة رد المساعد الفاضية لو ما وصل أي رد أصلًا
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && last.text === "") return prev.slice(0, -1);
          return prev;
        });
      },
    });
  };

  const regenerateLastResponse = async () => {
    if (readOnlyConversation || !conversationId || loading || lastAssistantIndex < 0) return;

    const targetIndex = lastAssistantIndex;
    const previousText = messages[targetIndex]?.text ?? "";
    setError("");
    setMessages((prev) =>
      prev.map((message, index) =>
        index === targetIndex ? { ...message, text: "", feedback: null } : message
      )
    );
    setLoading(true);

    const controller = new AbortController();
    streamAbortRef.current = controller;

    const appendToTargetMessage = (chunk) => {
      setMessages((prev) =>
        prev.map((message, index) =>
          index === targetIndex ? { ...message, text: message.text + chunk } : message
        )
      );
    };

    await streamRegenerateMessage(conversationId, {
      signal: controller.signal,
      onConversationId: (id) => setConversationId(id),
      onSources: (sources) => {
        setMessages((prev) => prev.map((message, index) =>
          index === targetIndex ? { ...message, sources } : message
        ));
      },
      onChunk: appendToTargetMessage,
      onDone: () => {
        streamAbortRef.current = null;
        setLoading(false);
        refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId);
      },
      onError: (message) => {
        streamAbortRef.current = null;
        setLoading(false);
        setError(message);
        setMessages((prev) =>
          prev.map((item, index) =>
            index === targetIndex ? { ...item, text: previousText } : item
          )
        );
      },
    });
  };

  const handleMarkNotificationRead = async (id) => {
    try {
      await markNotificationRead(id);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    } catch {
      // تجاهل بصمت — مو حرج
    }
  };

  const handleMarkAllNotificationsRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      // تجاهل بصمت — مو حرج
    }
  };

  const path = normalizedPath;
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
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <TermsPage />
      </Suspense>
    );
  }
  if (path === "/privacy") {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <PrivacyPage />
      </Suspense>
    );
  }
  if (path === "/pricing") {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <PricingPage />
      </Suspense>
    );
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
      </>
    );
  }

  return (
    <div className="flex h-full bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <Sidebar
        conversations={conversations}
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
        onMoveConversationToFolder={handleMoveConversationToFolder}
        projects={projects}
        selectedProjectId={selectedProjectId}
        onSelectProject={handleSelectProject}
        onCreateProject={handleCreateProject}
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
        onBulkMoveToFolder={handleBulkMoveToFolder}
        workspaces={workspaces}
        selectedWorkspaceId={selectedWorkspaceId}
        onSelectWorkspace={handleSelectWorkspace}
        onCreateWorkspace={handleCreateWorkspace}
        onRenameWorkspace={handleRenameWorkspace}
        onOpenWorkspaceMembers={handleOpenWorkspaceMembers}
        onOpenWorkspaceSharedConversation={handleOpenWorkspaceSharedConversation}
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
      <main className="flex flex-1 flex-col">
        <ChatHeader
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
          notifications={notifications}
          onMarkNotificationRead={handleMarkNotificationRead}
          onMarkAllNotificationsRead={handleMarkAllNotificationsRead}
        />

        <section className="flex flex-1 flex-col p-4">
          {conversationId && (conversationSummary || summaryLoading) ? (
            <div className="mb-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
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

          <div className="flex-1 space-y-4 overflow-y-auto rounded-3xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
            {empty ? (
              <div className="flex h-full flex-col items-center justify-center text-center text-slate-500">
                <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{t("emptyTitle")}</h3>
                <p className="mt-2 max-w-md">{t("emptyDesc")}</p>
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
                  {t("typing")}
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {error && (
            <div className="mt-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}
        </section>

        {readOnlyConversation ? (
          <div className="border-t border-slate-200 bg-white px-4 py-3 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
            {t("workspaceSharing.readOnly")}
          </div>
        ) : (
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
          models={aiModels}
          selectedModel={selectedModel}
          onSelectModel={setSelectedModel}
          />
        )}
      </main>

      <Toast message={toast?.message} type={toast?.type} onDismiss={() => setToast(null)} />

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
        />
      )}

      {showBilling && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <BillingPanel onClose={() => setShowBilling(false)} />
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
