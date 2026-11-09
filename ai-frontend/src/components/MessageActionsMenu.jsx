import { useEffect, useId, useRef, useState } from "react";
import "./MessageActionsMenu.css";

export default function MessageActionsMenu({ hasActions, label, panelLabel, children }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const restoreFocusRef = useRef(false);

  const closeMenu = (restoreFocus = false) => {
    if (restoreFocus) restoreFocusRef.current = true;
    setOpen(false);
  };

  useEffect(() => {
    if (!open) {
      if (restoreFocusRef.current) {
        restoreFocusRef.current = false;
        triggerRef.current?.focus();
      }
      return undefined;
    }

    const handlePointerDown = (event) => {
      if (!rootRef.current?.contains(event.target)) closeMenu();
    };
    const handleKeyDown = (event) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      closeMenu(true);
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  if (!hasActions) return null;

  return (
    <div ref={rootRef} className="chat-message-actions-menu">
      <button
        ref={triggerRef}
        type="button"
        className="chat-message-actions-trigger"
        aria-label={label}
        title={label}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((current) => !current)}
      >
        <span aria-hidden="true">⋯</span>
      </button>
      {open ? (
        <div
          id={panelId}
          className="chat-message-actions chat-message-actions-panel flex min-w-0 max-w-full flex-wrap items-center gap-1"
          role="group"
          aria-label={panelLabel}
          onClickCapture={() => closeMenu(true)}
        >
          {children}
        </div>
      ) : null}
    </div>
  );
}
