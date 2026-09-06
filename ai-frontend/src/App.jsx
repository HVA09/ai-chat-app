import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Sidebar from "./components/Sidebar";
import ChatHeader from "./components/ChatHeader";
import ChatMessage from "./components/ChatMessage";
import ChatComposer from "./components/ChatComposer";
import AuthForm from "./components/AuthForm";
import Toast from "./components/Toast";
import useDirection from "./hooks/useDirection";
import { streamChatMessage } from "./lib/chatApi";
import api, { restoreSession } from "./lib/api";
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
import { listConversations, getConversation, renameConversation, deleteConversation } from "./lib/conversationsApi";
import { getCurrentUser } from "./lib/usersApi";
import { listNotifications, markNotificationRead, markAllNotificationsRead, buildNotificationsWebSocketUrl } from "./lib/notificationsApi";
import "./i18n";
function getWelcomeMessage(t) { return { role: "assistant", text: t("app.welcomeMessage"), time: t("app.now") }; }
function PageLoadingFallback() {
  return <div className="flex h-full items-center justify-center bg-slate-50"><p className="text-sm text-slate-400">...</p></div>;
}
function ModalLoadingFallback() {
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"><p className="text-sm text-white">...</p></div>;
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
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [showAccountSettings, setShowAccountSettings] = useState(false);
  const [showFiles, setShowFiles] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [showBilling, setShowBilling] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const bottomRef = useRef(null);
  const streamAbortRef = useRef(null);
  useDirection();
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);
  const empty = useMemo(() => messages.length === 0, [messages.length]);
  const logout = useCallback(async () => {
    try { await api.post("/auth/logout"); } catch {}
    setAuthed(false); setConversations([]); setConversationId(null); setMessages([getWelcomeMessage(t)]); setError(""); setCurrentUser(null); setShowAccountSettings(false); setShowFiles(false); setShowAdmin(false); setShowBilling(false); setNotifications([]);
  }, [t]);
  useEffect(() => { restoreSession().then(() => setAuthed(true)).catch(() => setAuthed(false)).finally(() => setSessionChecking(false)); }, []);
  useEffect(() => { const handleUnauthorized = () => { logout(); setToast({ message: t("app.sessionExpired"), type: "error" }); }; window.addEventListener("auth:unauthorized", handleUnauthorized); return () => window.removeEventListener("auth:unauthorized", handleUnauthorized); }, [logout, t]);
  const refreshConversations = async () => { setConversationsLoading(true); try { setConversations(await listConversations()); } catch {} finally { setConversationsLoading(false); } };
  const refreshCurrentUser = async () => { try { setCurrentUser(await getCurrentUser()); } catch {} };
  const refreshNotifications = async () => { try { setNotifications(await listNotifications()); } catch {} };
  useEffect(() => { if (authed) { refreshConversations(); refreshCurrentUser(); refreshNotifications(); } }, [authed]);
  useEffect(() => { if (!authed) return; const ws = new WebSocket(buildNotificationsWebSocketUrl()); ws.onmessage = (event) => { const notification = JSON.parse(event.data); setNotifications((prev) => [notification, ...prev]); setToast({ message: notification.title, type: "success" }); }; return () => ws.close(); }, [authed]);
  const switchLang = (nextLang) => { setLang(nextLang); i18n.changeLanguage(nextLang); };
  const startNewChat = () => { setConversationId(null); setMessages([getWelcomeMessage(t)]); setError(""); };
  const openConversation = async (id) => { setError(""); try { const data = await getConversation(id); setConversationId(data.id); setMessages(data.messages.map((m) => ({ role: m.role, text: m.content, time: new Date(m.created_at).toLocaleTimeString() }))); } catch { setError(t("app.conversationLoadError")); } };
  const handleRenameConversation = async (id, newTitle) => { try { await renameConversation(id, newTitle); await refreshConversations(); } catch { setToast({ message: t("app.renameConversationError"), type: "error" }); } };
  const handleDeleteConversation = async (id) => { try { await deleteConversation(id); if (id === conversationId) startNewChat(); await refreshConversations(); } catch { setToast({ message: t("app.deleteConversationError"), type: "error" }); } };
  const stopGeneration = () => { if (streamAbortRef.current) { streamAbortRef.current.abort(); streamAbortRef.current = null; } setLoading(false); };
  const sendMessage = async () => {
    const userText = input.trim(); if (!userText) return; setError(""); setMessages((prev) => [...prev, { role: "user", text: userText, time: new Date().toLocaleTimeString() }, { role: "assistant", text: "", time: new Date().toLocaleTimeString() }]); setInput(""); setLoading(true);
    const controller = new AbortController(); streamAbortRef.current = controller; const isNewConversation = !conversationId; let receivedFirstChunk = false;
    const appendToLastMessage = (chunk) => setMessages((prev) => { const next = [...prev]; const last = next[next.length - 1]; next[next.length - 1] = { ...last, text: last.text + chunk }; return next; });
    await streamChatMessage(userText, conversationId, { signal: controller.signal, onConversationId: (id) => setConversationId(id), onChunk: (chunk) => { if (!receivedFirstChunk) receivedFirstChunk = true; appendToLastMessage(chunk); }, onDone: () => { streamAbortRef.current = null; setLoading(false); if (isNewConversation) refreshConversations(); }, onError: (message) => { streamAbortRef.current = null; setLoading(false); setError(message); setMessages((prev) => { const last = prev[prev.length - 1]; if (last?.role === "assistant" && last.text === "") return prev.slice(0, -1); return prev; }); } });
  };
  const handleMarkNotificationRead = async (id) => { try { await markNotificationRead(id); setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))); } catch {} };
  const handleMarkAllNotificationsRead = async () => { try { await markAllNotificationsRead(); setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true }))); } catch {} };
  const path = normalizedPath;
  if (path === "/terms") return <Suspense fallback={<PageLoadingFallback />}><TermsPage /></Suspense>;
  if (path === "/privacy") return <Suspense fallback={<PageLoadingFallback />}><PrivacyPage /></Suspense>;
  if (path === "/pricing") return <Suspense fallback={<PageLoadingFallback />}><PricingPage /></Suspense>;
  if (path === "/verify-email") return <Suspense fallback={<PageLoadingFallback />}><VerifyEmailPage /></Suspense>;
  if (path === "/reset-password") return <Suspense fallback={<PageLoadingFallback />}><ResetPasswordPage /></Suspense>;
  if (path === "/billing/success") return <Suspense fallback={<PageLoadingFallback />}><BillingSuccessPage /></Suspense>;
  if (path === "/billing/cancel") return <Suspense fallback={<PageLoadingFallback />}><BillingCancelPage /></Suspense>;
  if (sessionChecking) return <PageLoadingFallback />;
  if (!authed) return <><AuthForm onAuthenticated={() => { setAuthed(true); setToast({ message: t("app.loginSuccess"), type: "success" }); }} /><Toast message={toast?.message} type={toast?.type} onDismiss={() => setToast(null)} /></>;
  return <div className="flex h-full bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100"><Sidebar conversations={conversations} onSelectConversation={openConversation} onNewChat={startNewChat} onRenameConversation={handleRenameConversation} onDeleteConversation={handleDeleteConversation} loading={conversationsLoading} /><main className="flex flex-1 flex-col"><ChatHeader lang={lang} setLang={switchLang} onLogout={logout} onOpenAccount={() => setShowAccountSettings(true)} onOpenFiles={() => setShowFiles(true)} onOpenAdmin={() => setShowAdmin(true)} onOpenBilling={() => setShowBilling(true)} isAdmin={currentUser?.role === "admin"} notifications={notifications} onMarkNotificationRead={handleMarkNotificationRead} onMarkAllNotificationsRead={handleMarkAllNotificationsRead} /><section className="flex flex-1 flex-col p-4"><div className="flex-1 space-y-4 overflow-y-auto rounded-3xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">{empty ? <div className="flex h-full flex-col items-center justify-center text-center text-slate-500"><h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{t("emptyTitle")}</h3><p className="mt-2 max-w-md">{t("emptyDesc")}</p></div> : messages.map((msg, index) => { const isPendingAssistantBubble = index === messages.length - 1 && msg.role === "assistant" && msg.text === "" && loading; if (isPendingAssistantBubble) return null; return <ChatMessage key={index} role={msg.role} text={msg.text} time={msg.time} />; })}{loading && <div className="flex justify-start"><div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">{t("typing")}</div></div>}<div ref={bottomRef} /></div>{error && <div className="mt-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}</section><ChatComposer value={input} setValue={setInput} onSend={sendMessage} onStop={stopGeneration} loading={loading} /></main><Toast message={toast?.message} type={toast?.type} onDismiss={() => setToast(null)} />{showAccountSettings && <Suspense fallback={<ModalLoadingFallback />}><AccountSettings user={currentUser} onClose={() => setShowAccountSettings(false)} onUserUpdated={refreshCurrentUser} onAccountDeleted={logout} /></Suspense>}{showFiles && <Suspense fallback={<ModalLoadingFallback />}><FilesPanel onClose={() => setShowFiles(false)} /></Suspense>}{showAdmin && <Suspense fallback={<ModalLoadingFallback />}><AdminDashboard currentUserId={currentUser?.id} onClose={() => setShowAdmin(false)} /></Suspense>}{showBilling && <Suspense fallback={<ModalLoadingFallback />}><BillingPanel onClose={() => setShowBilling(false)} /></Suspense>}</div>;
}
