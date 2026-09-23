import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

function shortcutLabel() {
  if (typeof navigator !== "undefined" && /Mac|iPhone|iPad|iPod/.test(navigator.platform)) {
    return "⌘K";
  }
  return "Ctrl K";
}

export default function CommandPalette({ open, onClose, actions = [] }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (!open) {
      setQuery("");
      return undefined;
    }

    const timer = window.setTimeout(() => inputRef.current?.focus(), 0);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  const filteredActions = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    if (!normalized) return actions;

    return actions.filter((action) => {
      const haystack = [
        action.label,
        ...(action.keywords || []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLocaleLowerCase();
      return haystack.includes(normalized);
    });
  }, [actions, query]);

  useEffect(() => {
    if (!open) return undefined;

    const onGlobalShortcut = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onClose();
      }
    };

    window.addEventListener("keydown", onGlobalShortcut);
    return () => window.removeEventListener("keydown", onGlobalShortcut);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center bg-slate-950/40 p-4 pt-[12vh] backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={t("commandPalette.title")}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900">
        <div className="border-b border-slate-200 p-3 dark:border-slate-700">
          <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 dark:border-slate-700 dark:bg-slate-800">
            <span className="text-sm text-slate-400">⌕</span>
            <input
              ref={inputRef}
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t("commandPalette.placeholder")}
              className="min-w-0 flex-1 bg-transparent py-3 text-sm outline-none"
              aria-label={t("commandPalette.searchLabel")}
            />
            <kbd className="rounded-md border border-slate-200 bg-white px-2 py-1 text-[10px] text-slate-400 dark:border-slate-700 dark:bg-slate-900">
              Esc
            </kbd>
          </div>
        </div>

        <div className="max-h-[55vh] overflow-y-auto p-2">
          {filteredActions.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-slate-400">
              {t("commandPalette.noResults")}
            </p>
          ) : (
            <div className="space-y-1">
              {filteredActions.map((action) => (
                <button
                  key={action.id}
                  type="button"
                  onClick={() => {
                    action.onSelect?.();
                    onClose();
                  }}
                  className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-start text-sm text-slate-700 transition hover:bg-slate-100 focus:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-300 dark:text-slate-200 dark:hover:bg-slate-800 dark:focus:bg-slate-800"
                >
                  <span className="w-7 shrink-0 text-center text-base text-slate-400" aria-hidden="true">
                    {action.icon || "•"}
                  </span>
                  <span className="min-w-0 flex-1 truncate">{action.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 px-3 py-2 text-[11px] text-slate-400 dark:border-slate-700">
          <span>{t("commandPalette.hint")}</span>
          <kbd className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 dark:border-slate-700 dark:bg-slate-800">
            {shortcutLabel()}
          </kbd>
        </div>
      </div>
    </div>
  );
}
