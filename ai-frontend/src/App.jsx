import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Sidebar from "./components/Sidebar";
import ChatHeader from "./components/ChatHeader";
import ChatMessage from "./components/ChatMessage";
import ChatComposer from "./components/ChatComposer";
import AuthForm from "./components/AuthForm";
import Toast from "./components/Toast";
import useDirection from "./hooks/useDirection";
import { streamChatMessage, streamRegenerateMessage, streamEditMessage, setMessageFeedback, analyzeImage, listAiModels } from "./lib/chatApi";
import api, { restoreSession } from "./lib/api";
import { createConversationShare } from "./lib/sharedConversationsApi";

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
import {
  listConversations,
  getConversation,
  renameConversation,
  deleteConversation,
  togglePinConversation,
  toggleArchiveConversation,
  moveConversationToFolder,
  exportConversation,
} from "./lib/conversationsApi";
import {
  listFolders,
  createFolder,
  renameFolder,
  deleteFolder,
} from "./lib/foldersApi";
import {
  listWorkspaces,
  createWorkspace,
  renameWorkspace,
} from "./lib/workspacesApi";
import {
  listAssistants,
  createAssistant,
  updateAssistant,
  deleteAssistant,
} from "./lib/assistantsApi";
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
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [showArchivedConversations, setShowArchivedConversations] = useState(false);
  const [folders, setFolders] = useState([]);
  const [selectedFolderId, setSelectedFolderId] = useState(null);
  const [workspaces, setWorkspaces] = useState([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(null);
  const [assistants, setAssistants] = useState([]);
  const [selectedAssistantId, setSelectedAssistantId] = useState(null);
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
    setFolders([]);
    setWorkspaces([]);
    setSelectedWorkspaceId(null);
    setSelectedFolderId(null);
    setAssistants([]);
    setAiModels([]);
    setSelectedModel("");
    setSelectedFolderId(null);
    setSelectedAssistantId(null);
    setConversationId(null);
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
    workspaceId = selectedWorkspaceId
  ) => {
    setConversationsLoading(true);
    try {
      const list = await listConversations(includeArchived, folderId, workspaceId);
      setConversations(list);
    } catch {
      // فشل تحميل القائمة لا يوقف الشات نفسه — نتجاهله بصمت
    } finally {
      setConversationsLoading(false);
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
      setSelectedFolderId(null);
      await refreshConversations(showArchivedConversations, null, nextId);
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
      startNewChat();
      await refreshConversations(showArchivedConversations, null, workspace.id);
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

  const handleSelectWorkspace = async (id) => {
    const workspaceId = Number(id);
    if (!workspaceId || workspaceId === selectedWorkspaceId) return;
    setSelectedWorkspaceId(workspaceId);
    setSelectedFolderId(null);
    startNewChat();
    await refreshConversations(showArchivedConversations, null, workspaceId);
  };

  const refreshFolders = async () => {
    try {
      setFolders(await listFolders());
    } catch {
      // فشل تحميل المجلدات لا يوقف الشات.
    }
  };

  const handleCreateFolder = async () => {
    const name = window.prompt(t("sidebar.folderCreatePrompt"));
    if (!name?.trim()) return;
    try {
      const folder = await createFolder(name.trim());
      await refreshFolders();
      setSelectedFolderId(folder.id);
      startNewChat();
      await refreshConversations(showArchivedConversations, folder.id, selectedWorkspaceId);
    } catch {
      setToast({ message: t("app.folderCreateError"), type: "error" });
    }
  };

  const handleRenameFolder = async (id, newName) => {
    try {
      await renameFolder(id, newName);
      await refreshFolders();
      await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId);
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
      await refreshFolders();
      await refreshConversations(
        showArchivedConversations,
        wasSelected ? null : selectedFolderId,
        selectedWorkspaceId
      );
    } catch {
      setToast({ message: t("app.folderDeleteError"), type: "error" });
    }
  };

  const handleSelectFolder = async (id) => {
    setSelectedFolderId(id);
    startNewChat();
    await refreshConversations(showArchivedConversations, id, selectedWorkspaceId);
  };

  const refreshAssistants = async () => {
    try {
      setAssistants(await listAssistants());
    } catch {
      // فشل تحميل المساعدين لا يوقف الشات.
    }
  };

  const handleCreateAssistant = async () => {
    const name = window.prompt(t("sidebar.assistantCreateNamePrompt"));
    if (!name?.trim()) return;
    const instructions = window.prompt(t("sidebar.assistantCreateInstructionsPrompt"));
    if (!instructions?.trim()) return;
    const description = window.prompt(t("sidebar.assistantCreateDescriptionPrompt"));
    try {
      const assistant = await createAssistant({
        name: name.trim(),
        description: description?.trim() || null,
        instructions: instructions.trim(),
      });
      await refreshAssistants();
      setSelectedAssistantId(assistant.id);
      startNewChat();
    } catch (err) {
      setToast({
        message:
          err?.response?.data?.detail || t("app.assistantCreateError"),
        type: "error",
      });
    }
  };

  const handleRenameAssistant = async (id, currentName) => {
    const name = window.prompt(t("sidebar.assistantRenamePrompt"), currentName);
    if (!name?.trim() || name.trim() === currentName) return;
    try {
      await updateAssistant(id, { name: name.trim() });
      await refreshAssistants();
    } catch (err) {
      setToast({
        message:
          err?.response?.data?.detail || t("app.assistantRenameError"),
        type: "error",
      });
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
      await refreshAssistants();
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
      await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId);
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
      refreshFolders();
      refreshAssistants();
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
    setConversationId(null);
    setMessages([getWelcomeMessage(t)]);
    setInput("");
    setEditingMessageIndex(null);
    setError("");
  };

  const openConversation = async (id) => {
    setError("");
    setInput("");
    setEditingMessageIndex(null);
    try {
      const data = await getConversation(id);
      setConversationId(data.id);
      setSelectedAssistantId(data.assistant_id ?? null);
      setSelectedWorkspaceId(data.workspace_id ?? null);
      setSelectedFolderId(data.folder_id ?? null);
      setSelectedModel(
        data.ai_model ||
          aiModels.find((model) => model.is_default)?.id ||
          aiModels[0]?.id ||
          ""
      );
      setMessages(
        data.messages.map((m) => ({
          role: m.role,
          text: m.content,
          time: new Date(m.created_at).toLocaleTimeString(),
          sources: m.sources ?? [],
          feedback: m.feedback ?? null,
        }))
      );
    } catch {
      setError(t("app.conversationLoadError"));
    }
  };

  const handleAnalyzeImage = async (file, prompt) => {
    if (!conversationId || loading) return;
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
      await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId);
    } catch (err) {
      setMessages((prev) => prev.slice(0, -2));
      setToast({ message: t("app.imageAnalyzeError"), type: "error" });
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const handleMessageFeedback = async (index, rating) => {
    if (!conversationId || loading) return;

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

  const handleRenameConversation = async (id, newTitle) => {
    try {
      await renameConversation(id, newTitle);
      await refreshConversations();
    } catch {
      setToast({ message: t("app.renameConversationError"), type: "error" });
    }
  };

  const handleExportConversation = async () => {
    if (!conversationId || loading) return;
    try {
      await exportConversation(conversationId);
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

  const handleToggleArchiveConversation = async (id) => {
    try {
      const result = await toggleArchiveConversation(id);
      if (result.is_archived && id === conversationId) startNewChat();
      await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId);
    } catch {
      setToast({ message: t("app.archiveConversationError"), type: "error" });
    }
  };

  const handleTogglePinConversation = async (id) => {
    try {
      await togglePinConversation(id);
      await refreshConversations(showArchivedConversations, selectedFolderId);
    } catch {
      setToast({ message: t("app.pinConversationError"), type: "error" });
    }
  };

  const handleDeleteConversation = async (id) => {
    try {
      await deleteConversation(id);
      if (id === conversationId) startNewChat();
      await refreshConversations(showArchivedConversations, selectedFolderId);
    } catch {
      setToast({ message: t("app.deleteConversationError"), type: "error" });
    }
  };

  const deleteMessage = async (index) => {
    if (!conversationId || loading || editingMessageIndex !== null) return;

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
    if (loading || !conversationId || messages[index]?.role !== "user") return;
    setError("");
    setEditingMessageIndex(index);
    setInput(messages[index]?.text ?? "");
  };

  const editMessage = async () => {
    const targetIndex = editingMessageIndex;
    const editedText = input.trim();
    if (targetIndex === null || !conversationId || !editedText || loading) return;

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
        refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId);
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
      onConversationId: (id) => setConversationId(id),
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
          refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId);
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
    if (!conversationId || loading || lastAssistantIndex < 0) return;

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
        refreshConversations();
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
        onRenameConversation={handleRenameConversation}
        onDeleteConversation={handleDeleteConversation}
        onTogglePinConversation={handleTogglePinConversation}
        onToggleArchiveConversation={handleToggleArchiveConversation}
        assistants={assistants}
        selectedAssistantId={selectedAssistantId}
        onSelectAssistant={handleSelectAssistant}
        onCreateAssistant={handleCreateAssistant}
        onRenameAssistant={handleRenameAssistant}
        onDeleteAssistant={handleDeleteAssistant}
        folders={folders}
        selectedFolderId={selectedFolderId}
        onSelectFolder={handleSelectFolder}
        onCreateFolder={handleCreateFolder}
        onRenameFolder={handleRenameFolder}
        onDeleteFolder={handleDeleteFolder}
        onMoveConversationToFolder={handleMoveConversationToFolder}
        workspaces={workspaces}
        selectedWorkspaceId={selectedWorkspaceId}
        onSelectWorkspace={handleSelectWorkspace}
        onCreateWorkspace={handleCreateWorkspace}
        onRenameWorkspace={handleRenameWorkspace}
        onOpenWorkspaceMembers={handleOpenWorkspaceMembers}
        showArchived={showArchivedConversations}
        onShowArchived={(value) => {
          setShowArchivedConversations(value);
          refreshConversations(value, selectedFolderId, selectedWorkspaceId);
          if (value) startNewChat();
        }}
        loading={conversationsLoading}
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
          canShareConversation={conversationId !== null && !loading}
          onExportConversation={handleExportConversation}
          canExportConversation={conversationId !== null && !loading}
          isAdmin={currentUser?.role === "admin"}
          notifications={notifications}
          onMarkNotificationRead={handleMarkNotificationRead}
          onMarkAllNotificationsRead={handleMarkAllNotificationsRead}
        />

        <section className="flex flex-1 flex-col p-4">
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
                    canFeedback={
                      msg.role === "assistant" &&
                      !loading &&
                      editingMessageIndex === null &&
                      conversationId !== null
                    }
                    onFeedback={(rating) => handleMessageFeedback(index, rating)}
                    canEdit={
                      msg.role === "user" &&
                      !loading &&
                      editingMessageIndex === null &&
                      conversationId !== null
                    }
                    onEdit={() => startEditingMessage(index)}
                    canDelete={
                      !loading &&
                      editingMessageIndex === null &&
                      conversationId !== null
                    }
                    onDelete={() => deleteMessage(index)}
                    canRegenerate={
                      index === lastAssistantIndex &&
                      !loading &&
                      editingMessageIndex === null &&
                      conversationId !== null
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
      </main>

      <Toast message={toast?.message} type={toast?.type} onDismiss={() => setToast(null)} />

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
            onClose={() => setShowWorkspaceMembers(false)}
          />
        </Suspense>
      )}
    </div>
  );
}
