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
import useTagManagement from "./hooks/useTagManagement";
import useConversationMetadata from "./hooks/useConversationMetadata";
import useMessageEditing from "./hooks/useMessageEditing";
import useConversationBulkActions from "./hooks/useConversationBulkActions";
import useConversationSelection from "./hooks/useConversationSelection";
import useConversationItemActions from "./hooks/useConversationItemActions";
import useConversationImport from "./hooks/useConversationImport";
import useConversationExport from "./hooks/useConversationExport";
import useToolActivity from "./hooks/useToolActivity";
import useStopGeneration from "./hooks/useStopGeneration";
import useConversationBranching from "./hooks/useConversationBranching";
import useImageAnalysis from "./hooks/useImageAnalysis";
import useChatAutoScroll from "./hooks/useChatAutoScroll";
import useMessageFeedback from "./hooks/useMessageFeedback";
import useAppendToLastMessage from "./hooks/useAppendToLastMessage";
import useConversationSharing from "./hooks/useConversationSharing";
import useWorkspaceConversationSharing from "./hooks/useWorkspaceConversationSharing";
import useDeleteMessage from "./hooks/useDeleteMessage";
import useRegenerateLastResponse from "./hooks/useRegenerateLastResponse";
import useRetryFailedGeneration from "./hooks/useRetryFailedGeneration";
import useEditMessageGeneration from "./hooks/useEditMessageGeneration";
import useSendMessageGeneration from "./hooks/useSendMessageGeneration";
import { analyzeImage, compareChatModels } from "./lib/chatApi";
import api, { restoreSession } from "./lib/api";


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
  deleteConversation,
  toggleArchiveConversation,
  toggleTrashConversation,
  summarizeConversation,
  generateConversationTitle,
} from "./lib/conversationsApi";
import useFolderManagement from "./hooks/useFolderManagement";
import useProjectManagement from "./hooks/useProjectManagement";
import useProjectMemberRoles from "./hooks/useProjectMemberRoles";
import useWorkspaceManagement from "./hooks/useWorkspaceManagement";

import useAssistantManagement from "./hooks/useAssistantManagement";
import useCurrentUser from "./hooks/useCurrentUser";
import useOnboarding from "./hooks/useOnboarding";
import useAppGlobalEvents from "./hooks/useAppGlobalEvents";
import useCommandPaletteActions from "./hooks/useCommandPaletteActions";
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
  const [sessionCheckSlow, setSessionCheckSlow] = useState(false);
  const [sessionCheckError, setSessionCheckError] = useState(false);
  const [sessionCheckAttempt, setSessionCheckAttempt] = useState(0);
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
  const folderRequestGenerationRef = useRef(0);
  const [selectedFolderId, setSelectedFolderId] = useState(null);
  const [projects, setProjects] = useState([]);
  const projectRequestGenerationRef = useRef(0);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [tags, setTags] = useState([]);
  const tagRequestGenerationRef = useRef(0);
  const [selectedTagId, setSelectedTagId] = useState(null);
  const [workspaces, setWorkspaces] = useState([]);
  const workspaceRequestGenerationRef = useRef(0);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(null);
  const [assistants, setAssistants] = useState([]);
  const assistantRequestGenerationRef = useRef(0);
  const [selectedAssistantId, setSelectedAssistantId] = useState(null);
  const [showAssistantEditor, setShowAssistantEditor] = useState(false);
  const [editingAssistantId, setEditingAssistantId] = useState(null);
  const [showProjectEditor, setShowProjectEditor] = useState(false);
  const [editingProjectId, setEditingProjectId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null); // { message, type }
  const { currentUser, refreshCurrentUser, resetCurrentUser } = useCurrentUser({
    setToast,
    t,
  });
  const { showOnboarding, closeOnboarding } = useOnboarding({
    authed,
    userId: currentUser?.id,
  });
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

  const projectMemberRoles = useProjectMemberRoles({
    projects,
    selectedProjectId,
    selectedWorkspaceId,
    currentUserId: currentUser?.id,
    workspaces,
  });

  const {
    notificationPreferences,
    setRealtimeToastsEnabled: handleNotificationToastsChanged,
    resetNotificationPreferences,
  } = useNotificationPreferences({
    authed,
    userId: currentUser?.id,
  });

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
  const { scrollContainerRef: chatScrollRef, handleScroll: handleChatScroll } =
    useChatAutoScroll({ conversationId, messages, loading });
  const conversationOpenRequestRef = useRef(0);
  const streamAbortRef = useRef(null);
  const autoSummaryInFlightRef = useRef(false);
  const autoSummaryLastMessageCountRef = useRef({});
  const messageCountRef = useRef(messages.length);
  const appendToLastMessage = useAppendToLastMessage({ setMessages });

  useDirection();

  useEffect(() => {
    messageCountRef.current = messages.length;
  }, [messages.length]);

  const empty = useMemo(() => messages.length === 0, [messages.length]);
  const { toolActivityLabel, handleToolEvent } = useToolActivity({ setToolActivity });

  const lastAssistantIndex = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (messages[index].role === "assistant") return index;
    }
    return -1;
  }, [messages]);

  const logout = useCallback(async () => {
    // Invalidate pending conversation opens and user-scoped list loads before waiting for logout.
    conversationOpenRequestRef.current += 1;
    folderRequestGenerationRef.current += 1;
    projectRequestGenerationRef.current += 1;
    assistantRequestGenerationRef.current += 1;
    tagRequestGenerationRef.current += 1;
    workspaceRequestGenerationRef.current += 1;
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
    resetCurrentUser();
    // Discard user-scoped overlays and filters so a subsequent login starts clean.
    setShowAssistantEditor(false);
    setEditingAssistantId(null);
    setShowProjectEditor(false);
    setEditingProjectId(null);
    setShowModelCompare(false);
    setCommandPaletteOpen(false);
    setShowArchivedConversations(false);
    setConversationSearch("");
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
    setSummaryLoading(false);
    autoSummaryLastMessageCountRef.current = {};
    messageCountRef.current = 1;
    resetNotifications();
  }, [resetCurrentUser, t]);

  useEffect(() => {
    let active = true;

    setSessionChecking(true);
    setSessionCheckSlow(false);
    setSessionCheckError(false);

    const slowTimer = window.setTimeout(() => {
      if (active) setSessionCheckSlow(true);
    }, 12000);

    restoreSession()
      .then(() => {
        if (active) setAuthed(true);
      })
      .catch((error) => {
        if (!active) return;
        setAuthed(false);
        // 401 is the normal "no saved session" case. Other errors mean the
        // API could not be reached, including Render's temporary cold-start page.
        setSessionCheckError(error.response?.status !== 401);
      })
      .finally(() => {
        if (!active) return;
        window.clearTimeout(slowTimer);
        setSessionChecking(false);
      });

    return () => {
      active = false;
      window.clearTimeout(slowTimer);
    };
  }, [sessionCheckAttempt]);



  useAppGlobalEvents({ logout, setCommandPaletteOpen, setToast, t });

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

  const handleOpenWorkspaceMembers = () => {
    if (selectedWorkspaceId !== null) setShowWorkspaceMembers(true);
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

  const handleUseSavedPrompt = (content) => {
    setInput(content);
    setEditingMessageIndex(null);
    setError("");
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




  const switchLang = (nextLang) => {
    setLang(nextLang);
    i18n.changeLanguage(nextLang);
  };

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
    autoGenerateTitles,
    autoGenerateSummaries,
    setAutoGenerateTitlesEnabled,
    setAutoGenerateSummariesEnabled,
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
    conversationOpenRequestRef,
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

  const { startNewChat } = useStartNewChat({
    t,
    messageCountRef,
    conversationOpenRequestRef,
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

  const {
    refreshAssistants,
    openCreateAssistantEditor,
    openEditAssistantEditor,
    handleToggleAssistantShare,
    handleAssistantRestored,
    handleSaveAssistant,
    handleDeleteAssistant,
    handleSelectAssistant,
  } = useAssistantManagement({
    selectedWorkspaceId,
    assistantRequestGenerationRef,
    selectedAssistantId,
    editingAssistantId,
    setAssistants,
    setSelectedAssistantId,
    setEditingAssistantId,
    setShowAssistantEditor,
    setToast,
    startNewChat,
    t,
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
    refreshProjects,
    handleSaveProject,
    handleDeleteProject,
    handleSelectProject,
    handleExportProject,
    handleImportProject,
    handleMoveConversationToProject,
  } = useProjectManagement({
    projects,
    selectedWorkspaceId,
    projectRequestGenerationRef,
    selectedProjectId,
    selectedFolderId,
    editingProjectId,
    showArchivedConversations,
    conversationId,
    setProjects,
    setSelectedProjectId,
    setSelectedFolderId,
    setSelectedAssistantId,
    setShowProjectEditor,
    setEditingProjectId,
    startNewChat,
    refreshConversations,
    setToast,
    t,
  });

  const {
    refreshTags,
    handleCreateTag,
    handleRenameTag,
    handleDeleteTag,
    handleSelectTag,
    handleSetConversationTags,
  } = useTagManagement({
    tagRequestGenerationRef,
    t,
    selectedTagId,
    setSelectedTagId,
    setTags,
    setSelectedConversationIds,
    startNewChat,
    refreshConversations,
    showArchivedConversations,
    selectedFolderId,
    selectedWorkspaceId,
    selectedProjectId,
    conversationSearch,
    showTrashConversations,
    setToast,
  });

  const { handleImportConversation } = useConversationImport({
    selectedWorkspaceId,
    t,
    setToast,
    setShowArchivedConversations,
    setShowTrashConversations,
    setConversationSearch,
    setSelectedTagId,
    setSelectedFolderId,
    setSelectedProjectId,
    setSelectedConversationIds,
    refreshConversations,
    openConversation,
  });

  const { handleExportConversation } = useConversationExport({
    conversationId,
    loading,
    setToast,
    t,
  });

  const { handleBranchConversation } = useConversationBranching({
    conversationId,
    conversationSearch,
    loading,
    openConversation,
    readOnlyConversation,
    refreshConversations,
    selectedFolderId,
    selectedProjectId,
    selectedTagId,
    selectedWorkspaceId,
    setToast,
    showArchivedConversations,
    showTrashConversations,
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
    refreshFolders,
    handleCreateFolder,
    handleRenameFolder,
    handleMoveFolder,
    handleDeleteFolder,
    handleSelectFolder,
  } = useFolderManagement({
    folderRequestGenerationRef,
    selectedWorkspaceId,
    selectedFolderId,
    selectedProjectId,
    showArchivedConversations,
    conversationId,
    setFolders,
    setSelectedFolderId,
    setSelectedProjectId,
    startNewChat,
    refreshConversations,
    maybeAutoSummarizeConversation,
    messageCountRef,
    setToast,
    t,
  });

  const {
    refreshWorkspaces,
    handleCreateWorkspace,
    handleRenameWorkspace,
    handleWorkspaceUpdated,
    handleWorkspaceQuotaUpdated,
    handleSelectWorkspace,
  } = useWorkspaceManagement({
    workspaces,
    selectedWorkspaceId,
    workspaceRequestGenerationRef,
    aiModels,
    showArchivedConversations,
    setWorkspaces,
    setSelectedWorkspaceId,
    setSelectedModel,
    setSelectedFolderId,
    setSelectedProjectId,
    startNewChat,
    refreshFolders,
    refreshProjects,
    refreshAssistants,
    refreshConversations,
    setToast,
    t,
  });

  const { handleAnalyzeImage } = useImageAnalysis({
    analyzeImage,
    conversationId,
    loading,
    readOnlyConversation,
    messageCountRef,
    setError,
    setShowFiles,
    setMessages,
    setConversationId,
    setLoading,
    refreshConversations,
    showArchivedConversations,
    selectedFolderId,
    selectedWorkspaceId,
    selectedProjectId,
    maybeAutoSummarizeConversation,
    setToast,
    t,
  });

  const { handleMessageFeedback } = useMessageFeedback({
    conversationId,
    loading,
    readOnlyConversation,
    messages,
    setMessages,
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
    handleDuplicateConversation,
    handleMoveConversationToFolder,
    handleRenameConversation,
    handleToggleArchiveConversation,
    handleTogglePinConversation,
    handleToggleTrashConversation,
  } = useConversationItemActions({
    conversationId,
    conversationSearch,
    openConversation,
    refreshConversations,
    selectedFolderId,
    selectedProjectId,
    selectedTagId,
    selectedWorkspaceId,
    setToast,
    showArchivedConversations,
    showTrashConversations,
    startNewChat,
    t,
  });

  const { handleShareConversation, handleManageConversationShares } =
    useConversationSharing({
      conversationId,
      loading,
      messages,
      setShowShareManager,
      setToast,
      t,
    });

  const { deleteMessage } = useDeleteMessage({
    conversationId,
    loading,
    editingMessageIndex,
    readOnlyConversation,
    setError,
    setMessages,
    refreshConversations,
    getWelcomeMessage,
    t,
    setToast,
  });

  const {
    handleOpenWorkspaceSharedConversation,
    handleDuplicatedWorkspaceConversation,
    handleToggleWorkspaceShare,
  } = useWorkspaceConversationSharing({
    conversationId,
    selectedWorkspaceId,
    workspaceShare,
    loading,
    readOnlyConversation,
    openConversation,
    setShowShareManager,
    setReadOnlyConversation,
    setShowWorkspaceComments,
    setWorkspaceShare,
    setSelectedWorkspaceId,
    setConversationId,
    setConversationSummary,
    setConversationSummaryUpdatedAt,
    setSelectedAssistantId,
    setSelectedFolderId,
    setSelectedProjectId,
    setSelectedModel,
    setMessages,
    setInput,
    setEditingMessageIndex,
    setError,
    setToast,
    t,
  });

  const { stopGeneration } = useStopGeneration({
    streamAbortRef,
    setLoading,
    setToolActivity,
  });

  const { editMessage } = useEditMessageGeneration({
    readOnlyConversation,
    editingMessageIndex,
    input,
    conversationId,
    userId: currentUser?.id,
    loading,
    messages,
    autoSummaryLastMessageCountRef,
    setError,
    setRetryableUserMessage,
    messageCountRef,
    setMessages,
    setInput,
    setEditingMessageIndex,
    setLoading,
    streamAbortRef,
    setConversationId,
    handleToolEvent,
    appendToLastMessage,
    setToolActivity,
    refreshConversations,
    showArchivedConversations,
    selectedFolderId,
    selectedWorkspaceId,
    selectedProjectId,
    maybeAutoSummarizeConversation,
  });

  const { sendMessage } = useSendMessageGeneration({
    readOnlyConversation,
    editingMessageIndex,
    editMessage,
    input,
    chatAttachments,
    userId: currentUser?.id,
    conversationId,
    selectedAssistantId,
    selectedWorkspaceId,
    selectedProjectId,
    selectedFolderId,
    selectedModel,
    handleToolEvent,
    appendToLastMessage,
    resetChatAttachments,
    setError,
    setRetryableUserMessage,
    setToolActivity,
    messageCountRef,
    setMessages,
    setInput,
    setLoading,
    streamAbortRef,
    setConversationId,
    setToast,
    setActiveConversationTitle,
    refreshConversations,
    showArchivedConversations,
    maybeAutoGenerateConversationTitle,
    maybeAutoSummarizeConversation,
    messages,
    t,
  });

  const { retryFailedGeneration } = useRetryFailedGeneration({
    readOnlyConversation,
    loading,
    retryableUserMessage,
    conversationId,
    selectedAssistantId,
    selectedModel,
    setError,
    setLoading,
    setRetryableUserMessage,
    messageCountRef,
    setMessages,
    streamAbortRef,
    setConversationId,
    appendToLastMessage,
    resetChatAttachments,
    setToast,
    setActiveConversationTitle,
    refreshConversations,
    showArchivedConversations,
    selectedFolderId,
    selectedWorkspaceId,
    selectedProjectId,
    conversationSearch,
    showTrashConversations,
    selectedTagId,
    maybeAutoGenerateConversationTitle,
    maybeAutoSummarizeConversation,
    t,
  });

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

  const commandPaletteActions = useCommandPaletteActions({
    startNewChat,
    showArchivedConversations,
    setShowArchivedConversations,
    showTrashConversations,
    setShowTrashConversations,
    selectedFolderId,
    selectedWorkspaceId,
    selectedProjectId,
    conversationSearch,
    setSelectedFolderId,
    setSelectedConversationIds,
    refreshConversations,
    setShowFiles,
    setShowAccountSettings,
    setShowBilling,
    handleCreateFolder,
    handleCreateProject,
    openCreateAssistantEditor,
    setShowScheduledTasks,
    currentUserRole: currentUser?.role,
    setShowAdmin,
  });


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

  if (sessionChecking) {
    const isArabic = document.documentElement.lang === "ar";
    return (
      <main className="app-startup-screen" role="status" aria-live="polite">
        <div className="app-startup-brand" aria-hidden="true">AI</div>
        <div className="app-startup-spinner" aria-hidden="true" />
        <h1>{t("appName")}</h1>
        <p>
          {sessionCheckSlow
            ? isArabic
              ? "الخادم يستيقظ الآن. قد يستغرق الاتصال الأول نحو دقيقة."
              : "The server is waking up. The first connection can take about a minute."
            : isArabic
              ? "جارٍ الاتصال بالخادم وتجهيز جلستك..."
              : "Connecting to the server and restoring your session..."}
        </p>
        {sessionCheckSlow ? (
          <p className="app-startup-hint">
            {isArabic
              ? "اترك الصفحة مفتوحة؛ سنعيد المحاولة تلقائيًا."
              : "Keep this page open; we are retrying automatically."}
          </p>
        ) : null}
      </main>
    );
  }

  if (!authed && sessionCheckError) {
    const isArabic = document.documentElement.lang === "ar";
    return (
      <main className="app-startup-screen" role="alert">
        <div className="app-startup-brand" aria-hidden="true">AI</div>
        <h1>
          {isArabic ? "تعذر الاتصال بالخادم" : "Could not connect to the server"}
        </h1>
        <p>
          {isArabic
            ? "لم يستجب الخادم بعد عدة محاولات. تحقق من اتصال الإنترنت ثم أعد المحاولة."
            : "The server did not respond after several attempts. Check your internet connection and retry."}
        </p>
        <button
          type="button"
          className="app-startup-retry"
          onClick={() => {
            setSessionChecking(true);
            setSessionCheckSlow(false);
            setSessionCheckError(false);
            setSessionCheckAttempt((attempt) => attempt + 1);
          }}
        >
          {isArabic ? "إعادة المحاولة" : "Try again"}
        </button>
      </main>
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
        onOpenSettings={() => setShowAccountSettings(true)}
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

          <div
            ref={chatScrollRef}
            onScroll={handleChatScroll}
            className="chat-surface mx-auto flex min-h-0 w-full max-w-4xl flex-1 flex-col space-y-3 overflow-y-auto rounded-3xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
          >
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

      <CommandPalette
        open={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        actions={commandPaletteActions}
      />


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
            onAutoGenerateTitlesChanged={setAutoGenerateTitlesEnabled}
            autoGenerateSummaries={autoGenerateSummaries}
            onAutoGenerateSummariesChanged={setAutoGenerateSummariesEnabled}
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
