import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";

const DialogContext = createContext(null);

function DialogShell({ title, children, onClose, actions }) {
  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center bg-black/40 p-2 sm:items-center sm:p-4"
      onMouseDown={(event) => {
        if (event.currentTarget === event.target) onClose();
      }}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="app-dialog-title"
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-4 shadow-2xl dark:border-slate-700 dark:bg-slate-900 sm:rounded-3xl sm:p-5"
      >
        <h2 id="app-dialog-title" className="text-base font-semibold text-slate-900 dark:text-slate-100">
          {title}
        </h2>
        <div className="mt-3">{children}</div>
        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          {actions}
        </div>
      </div>
    </div>,
    document.body
  );
}

function AppDialogHost({ request, resolve }) {
  const { t } = useTranslation();
  const inputRef = useRef(null);
  const [value, setValue] = useState(request.defaultValue || "");

  useEffect(() => {
    inputRef.current?.focus();
    if (request.defaultValue) inputRef.current?.select();
  }, [request.defaultValue]);

  const close = useCallback(() => resolve(request.cancelValue ?? null), [request.cancelValue, resolve]);
  const submit = useCallback(() => {
    if (request.kind === "confirm") resolve(true);
    else resolve(value.trim() || null);
  }, [request.kind, resolve, value]);

  const title =
    request.title ||
    (request.kind === "confirm" ? t("common.confirmTitle") : t("common.inputTitle"));

  return (
    <DialogShell
      title={title}
      onClose={close}
      actions={
        <>
          <button
            type="button"
            onClick={close}
            className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            {request.cancelLabel || t("common.cancel")}
          </button>
          <button
            type="button"
            onClick={submit}
            className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            {request.confirmLabel ||
              (request.kind === "confirm" ? t("common.confirm") : t("common.save"))}
          </button>
        </>
      }
    >
      <p className="whitespace-pre-wrap text-sm leading-6 text-slate-600 dark:text-slate-300">
        {request.message}
      </p>
      {request.kind === "prompt" && (
        <input
          ref={inputRef}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
          placeholder={request.placeholder || ""}
          maxLength={request.maxLength || 255}
          className="mt-4 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
      )}
    </DialogShell>
  );
}

export function AppDialogProvider({ children }) {
  const [request, setRequest] = useState(null);
  const resolverRef = useRef(null);

  const close = useCallback((value) => {
    const resolve = resolverRef.current;
    resolverRef.current = null;
    setRequest(null);
    resolve?.(value);
  }, []);

  const confirm = useCallback((options = {}) => {
    return new Promise((resolve) => {
      resolverRef.current = resolve;
      setRequest({ kind: "confirm", ...options });
    });
  }, []);

  const prompt = useCallback((options = {}) => {
    return new Promise((resolve) => {
      resolverRef.current = resolve;
      setRequest({ kind: "prompt", ...options });
    });
  }, []);

  return (
    <DialogContext.Provider value={{ confirm, prompt }}>
      {children}
      {request ? <AppDialogHost request={request} resolve={close} /> : null}
    </DialogContext.Provider>
  );
}

export function useAppDialog() {
  const context = useContext(DialogContext);
  if (!context) {
    throw new Error("useAppDialog must be used inside AppDialogProvider");
  }
  return context;
}
