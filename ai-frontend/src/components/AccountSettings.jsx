import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  requestEmailVerification,
  setupTwoFactor,
  enableTwoFactor,
  disableTwoFactor,
} from "../lib/authApi";
import { updateProfile, changePassword, deleteAccount } from "../lib/usersApi";
import { listMemories, createMemory, updateMemory, deleteMemory } from "../lib/memoriesApi";
import { listApiKeys, createApiKey, revokeApiKey, getApiKeyUsage } from "../lib/apiKeysApi";
import { getErrorMessage } from "../lib/errors";

function Section({ title, children }) {
  return (
    <div className="mb-4 rounded-2xl border border-slate-200 p-4">
      <p className="mb-2 text-sm font-medium text-slate-900">{title}</p>
      {children}
    </div>
  );
}

export default function AccountSettings({ user, onClose, onUserUpdated, onAccountDeleted }) {
  const { t } = useTranslation();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [fullName, setFullName] = useState(user?.full_name || "");
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar_url || "");

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const [deletePassword, setDeletePassword] = useState("");
  const [memories, setMemories] = useState([]);
  const [memoryDraft, setMemoryDraft] = useState("");
  const [apiKeys, setApiKeys] = useState([]);
  const [apiKeyName, setApiKeyName] = useState("");
  const [apiKeyDailyLimit, setApiKeyDailyLimit] = useState("");
  const [apiKeyExpiry, setApiKeyExpiry] = useState("");
  const [createdApiKeySecret, setCreatedApiKeySecret] = useState("");
  const [apiKeyUsage, setApiKeyUsage] = useState({});

  const [setupData, setSetupData] = useState(null);
  const [code, setCode] = useState("");

  const loadMemories = async () => {
    try {
      setMemories(await listMemories());
    } catch (err) {
      setError(getErrorMessage(err, t("account.memoryLoadError")));
    }
  };

  const loadApiKeys = async () => {
    try {
      const keys = await listApiKeys();
      setApiKeys(keys);
      const usageEntries = await Promise.all(
        keys.map(async (item) => {
          try {
            return [item.id, await getApiKeyUsage(item.id, 24)];
          } catch {
            return [item.id, null];
          }
        })
      );
      setApiKeyUsage(Object.fromEntries(usageEntries));
    } catch (err) {
      setError(getErrorMessage(err, t("account.apiKeysLoadError")));
    }
  };

  useEffect(() => {
    loadMemories();
    loadApiKeys();
  }, []);

  const runAction = async (action) => {
    setError("");
    setMessage("");
    setLoading(true);
    try {
      await action();
    } catch (err) {
      setError(getErrorMessage(err, t("account.genericError")));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateApiKey = () =>
    runAction(async () => {
      const name = apiKeyName.trim();
      if (!name) return;
      const created = await createApiKey(
        name,
        apiKeyDailyLimit ? Number(apiKeyDailyLimit) : null,
        apiKeyExpiry || null
      );
      setApiKeys((prev) => [created, ...prev]);
      setCreatedApiKeySecret(created.secret);
      setApiKeyName("");
      setApiKeyDailyLimit("");
      setApiKeyExpiry("");
      setMessage(t("account.apiKeyCreated"));
    });

  const handleRevokeApiKey = (item) =>
    runAction(async () => {
      if (item.revoked_at) return;
      if (!window.confirm(t("account.apiKeyRevokeConfirm", { name: item.name }))) return;
      await revokeApiKey(item.id);
      await loadApiKeys();
      setMessage(t("account.apiKeyRevoked"));
    });

  const handleCopyApiKey = async () => {
    if (!createdApiKeySecret) return;
    try {
      await navigator.clipboard.writeText(createdApiKeySecret);
      setMessage(t("account.apiKeyCopied"));
    } catch {
      setError(t("account.apiKeyCopyError"));
    }
  };

  const handleAddMemory = () =>
    runAction(async () => {
      await createMemory(memoryDraft);
      setMemoryDraft("");
      await loadMemories();
      setMessage(t("account.memorySaved"));
    });

  const handleEditMemory = (memory) =>
    runAction(async () => {
      const content = window.prompt(t("account.memoryEditPrompt"), memory.content);
      if (!content?.trim()) return;
      await updateMemory(memory.id, content.trim());
      await loadMemories();
      setMessage(t("account.memorySaved"));
    });

  const handleDeleteMemory = (memory) =>
    runAction(async () => {
      if (!window.confirm(t("account.memoryDeleteConfirm", { content: memory.content }))) return;
      await deleteMemory(memory.id);
      await loadMemories();
      setMessage(t("account.memoryDeleted"));
    });

  const handleSaveProfile = () =>
    runAction(async () => {
      await updateProfile({ full_name: fullName, avatar_url: avatarUrl });
      setMessage(t("account.profileSaved"));
      onUserUpdated();
    });

  const handleChangePassword = () =>
    runAction(async () => {
      await changePassword(currentPassword, newPassword);
      setMessage(t("account.passwordChanged"));
      setCurrentPassword("");
      setNewPassword("");
    });

  const handleDeleteAccount = () =>
    runAction(async () => {
      if (!window.confirm(t("account.confirmDeleteAccount"))) return;
      await deleteAccount(deletePassword);
      onAccountDeleted();
    });

  const handleResendVerification = () =>
    runAction(async () => {
      const data = await requestEmailVerification();
      setMessage(data.detail);
    });

  const handleStartSetup = () =>
    runAction(async () => {
      const data = await setupTwoFactor();
      setSetupData(data);
    });

  const handleEnable = () =>
    runAction(async () => {
      await enableTwoFactor(code);
      setMessage(t("account.twoFAEnabled"));
      setSetupData(null);
      setCode("");
      onUserUpdated();
    });

  const handleDisable = () =>
    runAction(async () => {
      await disableTwoFactor(code);
      setMessage(t("account.twoFADisabled"));
      setCode("");
      onUserUpdated();
    });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/30 p-4">
      <div className="my-8 w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">{t("account.title")}</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        <Section title={t("account.profileSection")}>
          <div className="space-y-2">
            <input
              type="text"
              placeholder={t("account.namePlaceholder")}
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
            />
            <input
              type="text"
              placeholder={t("account.avatarPlaceholder")}
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
            />
            {avatarUrl && (
              <img
                src={avatarUrl}
                alt={t("account.avatarAlt")}
                loading="lazy"
                className="h-14 w-14 rounded-full border border-slate-200 object-cover"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
            )}
            <button
              onClick={handleSaveProfile}
              disabled={loading}
              className="w-full rounded-xl bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {t("account.save")}
            </button>
          </div>
        </Section>

        <Section title={t("account.memorySection")}>
          <div className="space-y-2">
            <p className="text-xs text-slate-500">{t("account.memoryDescription")}</p>
            <textarea
              value={memoryDraft}
              onChange={(e) => setMemoryDraft(e.target.value)}
              maxLength={500}
              rows={3}
              placeholder={t("account.memoryPlaceholder")}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
            />
            <button
              onClick={handleAddMemory}
              disabled={loading || !memoryDraft.trim()}
              className="w-full rounded-xl bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {t("account.memoryAdd")}
            </button>
            {memories.length > 0 && (
              <div className="space-y-2 pt-2">
                {memories.map((memory) => (
                  <div key={memory.id} className="rounded-xl border border-slate-200 bg-white p-3">
                    <p className="whitespace-pre-wrap text-sm text-slate-700">{memory.content}</p>
                    <div className="mt-2 flex gap-2">
                      <button
                        onClick={() => handleEditMemory(memory)}
                        disabled={loading}
                        className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                      >
                        {t("account.memoryEdit")}
                      </button>
                      <button
                        onClick={() => handleDeleteMemory(memory)}
                        disabled={loading}
                        className="rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        {t("account.memoryDelete")}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Section>

        <Section title={t("account.apiKeysSection")}>
          <div className="space-y-3">
            <p className="text-xs text-slate-500">{t("account.apiKeysDescription")}</p>
            <div className="space-y-2">
              <input
                type="text"
                maxLength={100}
                placeholder={t("account.apiKeyNamePlaceholder")}
                value={apiKeyName}
                onChange={(e) => setApiKeyName(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
              />
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <input
                  type="number"
                  min="1"
                  max="10000"
                  placeholder={t("account.apiKeyDailyLimitPlaceholder")}
                  value={apiKeyDailyLimit}
                  onChange={(e) => setApiKeyDailyLimit(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
                />
                <input
                  type="date"
                  min={new Date().toISOString().slice(0, 10)}
                  aria-label={t("account.apiKeyExpiryPlaceholder")}
                  value={apiKeyExpiry}
                  onChange={(e) => setApiKeyExpiry(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
                />
              </div>
              <p className="text-xs text-slate-400">{t("account.apiKeyControlsHelp")}</p>
              <button
                onClick={handleCreateApiKey}
                disabled={loading || !apiKeyName.trim()}
                className="w-full rounded-xl bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {t("account.apiKeyCreate")}
              </button>
            </div>

            {createdApiKeySecret && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
                <p className="text-xs font-medium text-amber-900">{t("account.apiKeySecretTitle")}</p>
                <p className="mt-1 text-xs text-amber-800">{t("account.apiKeySecretDescription")}</p>
                <code className="mt-2 block break-all rounded-lg bg-white p-2 text-xs text-slate-800">{createdApiKeySecret}</code>
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    onClick={handleCopyApiKey}
                    className="rounded-lg border border-amber-300 px-3 py-1.5 text-xs text-amber-900 hover:bg-amber-100"
                  >
                    {t("account.apiKeyCopy")}
                  </button>
                  <button
                    type="button"
                    onClick={() => setCreatedApiKeySecret("")}
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50"
                  >
                    {t("account.apiKeyHide")}
                  </button>
                </div>
              </div>
            )}

            {apiKeys.length > 0 ? (
              <div className="space-y-2">
                {apiKeys.map((item) => (
                  <div key={item.id} className="rounded-xl border border-slate-200 bg-white p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-slate-800">{item.name}</p>
                        <p className="text-xs text-slate-400">{item.key_prefix}…</p>
                      </div>
                      {item.revoked_at ? (
                        <span className="text-xs text-slate-400">{t("account.apiKeyRevokedLabel")}</span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleRevokeApiKey(item)}
                          disabled={loading}
                          className="rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                        >
                          {t("account.apiKeyRevoke")}
                        </button>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      {item.last_used_at
                        ? t("account.apiKeyLastUsed", { date: new Date(item.last_used_at).toLocaleString() })
                        : t("account.apiKeyNeverUsed")}
                    </p>
                    {apiKeyUsage[item.id] && (
                      <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-500">
                        <span>{apiKeyUsage[item.id].used_requests} {t("account.apiKeyUsageRequests")}</span>
                        <span>{apiKeyUsage[item.id].input_tokens} {t("account.apiKeyUsageInputTokens")}</span>
                        <span>{apiKeyUsage[item.id].output_tokens} {t("account.apiKeyUsageOutputTokens")}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400">{t("account.apiKeyEmpty")}</p>
            )}
          </div>
        </Section>

        <Section title={t("account.changePasswordSection")}>
          <div className="space-y-2">
            <input
              type="password"
              placeholder={t("account.currentPasswordPlaceholder")}
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
            />
            <input
              type="password"
              minLength={8}
              placeholder={t("account.newPasswordPlaceholder")}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
            />
            <button
              onClick={handleChangePassword}
              disabled={loading || !currentPassword || newPassword.length < 8}
              className="w-full rounded-xl bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {t("account.change")}
            </button>
          </div>
        </Section>

        <Section title={t("account.emailSection")}>
          {user?.is_email_verified ? (
            <p className="text-sm text-emerald-700">{t("account.verified")}</p>
          ) : (
            <div>
              <p className="mb-2 text-sm text-slate-500">{t("account.notVerified")}</p>
              <button
                onClick={handleResendVerification}
                disabled={loading}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
              >
                {t("account.resendVerification")}
              </button>
            </div>
          )}
        </Section>

        <Section title={t("account.twoFASection")}>
          {user?.is_2fa_enabled ? (
            <div className="space-y-2">
              <p className="text-sm text-emerald-700">{t("account.twoFAEnabledBadge")}</p>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder={t("account.codeToDisablePlaceholder")}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-center outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
              />
              <button
                onClick={handleDisable}
                disabled={loading || code.length !== 6}
                className="w-full rounded-xl border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                {t("account.disable2FA")}
              </button>
            </div>
          ) : setupData ? (
            <div className="space-y-3">
              <img
                src={`data:image/png;base64,${setupData.qr_code_base64}`}
                alt={t("account.qrAlt")}
                className="mx-auto h-40 w-40 rounded-xl border border-slate-200"
              />
              <p className="break-all text-center text-xs text-slate-400">{setupData.secret}</p>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder={t("account.confirmCodePlaceholder")}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-center outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
              />
              <button
                onClick={handleEnable}
                disabled={loading || code.length !== 6}
                className="w-full rounded-xl bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {t("account.confirmAndEnable")}
              </button>
            </div>
          ) : (
            <button
              onClick={handleStartSetup}
              disabled={loading}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
            >
              {t("account.enable2FA")}
            </button>
          )}
        </Section>

        <div className="rounded-2xl border border-red-200 p-4">
          <p className="mb-2 text-sm font-medium text-red-700">{t("account.deleteAccountTitle")}</p>
          <p className="mb-2 text-xs text-slate-500">{t("account.deleteAccountWarning")}</p>
          <input
            type="password"
            placeholder={t("account.confirmPasswordPlaceholder")}
            value={deletePassword}
            onChange={(e) => setDeletePassword(e.target.value)}
            className="mb-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-red-400 focus:ring-2 focus:ring-red-400"
          />
          <button
            onClick={handleDeleteAccount}
            disabled={loading || !deletePassword}
            className="w-full rounded-xl bg-red-600 px-3 py-2 text-sm text-white hover:bg-red-700 disabled:opacity-50"
          >
            {t("account.deletePermanently")}
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}
        {message && (
          <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {message}
          </div>
        )}
      </div>
    </div>
  );
}
