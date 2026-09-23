import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

// لازم يطابق حد ChatRequest.message بالباكيند (Field max_length=4000) — بدونه المستخدم
// يقدر يبعت رسالة أطول من المسموح ويوصله خطأ 422 بدل ما نمنعه من الأساس
const MAX_MESSAGE_LENGTH = 4000;

export default function ChatComposer({
  value,
  setValue,
  onSend,
  onStop,
  loading,
  isEditing = false,
  onCancelEdit,
  onInsertCalculator,
  onInsertWebSearch,
  onInsertDataAnalysis,
  onInsertAgent,
  onInsertPython,
  onVoiceError,
  models = [],
  selectedModel = "",
  onSelectModel,
  attachments = [],
  onAttachFiles,
  onRemoveAttachment,
  attachmentUploading = false,
}) {
  const { t } = useTranslation();
  const recognitionRef = useRef(null);
  const textareaRef = useRef(null);
  const [commandMenuDismissed, setCommandMenuDismissed] = useState(false);
  const [commandIndex, setCommandIndex] = useState(0);
  const [isListening, setIsListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const nearLimit = value.length > MAX_MESSAGE_LENGTH - 200;
  const lang = document.documentElement.lang;
  const saveEditLabel = lang === "ar" ? "حفظ التعديل" : "Save edit";
  const cancelEditLabel = lang === "ar" ? "إلغاء" : "Cancel";

  const commands = useMemo(
    () => [
      { name: "calc", icon: "🧮", label: lang === "ar" ? "آلة حاسبة" : "Calculator" },
      { name: "search", icon: "🔎", label: lang === "ar" ? "بحث الويب" : "Web search" },
      { name: "analyze", icon: "📊", label: lang === "ar" ? "تحليل البيانات" : "Data analysis" },
      { name: "agent", icon: "🤖", label: lang === "ar" ? "وضع الوكيل" : "Agent mode" },
      { name: "python", icon: "🐍", label: lang === "ar" ? "بايثون آمن" : "Safe Python" },
    ],
    [lang]
  );

  const commandModeActive = value.startsWith("/") && !/\s/.test(value.slice(1));
  const commandQuery = commandModeActive ? value.slice(1).split(/\s/)[0] : "";
  const filteredCommands = useMemo(() => {
    if (!commandModeActive || commandMenuDismissed) return [];
    const query = commandQuery.toLocaleLowerCase();
    return commands.filter((command) => command.name.startsWith(query));
  }, [commandMenuDismissed, commandModeActive, commandQuery, commands]);

  useEffect(() => {
    setCommandIndex(0);
    setCommandMenuDismissed(false);
  }, [commandQuery]);

  const selectCommand = (command) => {
    setValue(`/${command.name} `);
    setCommandMenuDismissed(true);
    requestAnimationFrame(() => textareaRef.current?.focus());
  };


  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    setVoiceSupported(Boolean(SpeechRecognition));

    return () => {
      recognitionRef.current?.stop();
      recognitionRef.current = null;
    };
  }, []);

  const handleFileSelection = (event) => {
    const files = Array.from(event.target.files || []);
    if (files.length) onAttachFiles?.(files);
    event.target.value = "";
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragOver(false);
    const files = Array.from(event.dataTransfer.files || []);
    if (files.length) onAttachFiles?.(files);
  };

  const handlePaste = (event) => {
    if (loading || isEditing) return;
    const files = Array.from(event.clipboardData?.files || []);
    if (files.length) onAttachFiles?.(files);
  };

  const toggleVoiceInput = () => {
    if (!voiceSupported || loading || isEditing) return;

    if (isListening) {
      recognitionRef.current?.stop();
      return;
    }

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      onVoiceError?.(t("app.voiceNotSupported"));
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = lang === "ar" ? "ar-SA" : "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };
    recognition.onerror = () => {
      setIsListening(false);
      recognitionRef.current = null;
      onVoiceError?.(t("app.voiceError"));
    };
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript || "")
        .join(" ")
        .trim();
      if (transcript) {
        setValue((current) =>
          [current.trim(), transcript].filter(Boolean).join(" ")
        );
      }
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      recognitionRef.current = null;
      setIsListening(false);
      onVoiceError?.(t("app.voiceError"));
    }
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!value.trim() || loading || attachmentUploading) return;
        onSend();
      }}
      onDragOver={(e) => {
        e.preventDefault();
        if (!loading && !isEditing) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className="border-t border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
    >
      {isEditing && !loading ? (
        <div className="mb-2 flex items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
          <span>{lang === "ar" ? "تعديل الرسالة" : "Editing message"}</span>
          <button
            type="button"
            onClick={onCancelEdit}
            className="rounded-md px-2 py-1 font-medium hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-slate-800 dark:hover:text-slate-100"
          >
            {cancelEditLabel}
          </button>
        </div>
      ) : null}

      {attachments.length > 0 ? (
        <div className="mb-3 flex flex-wrap gap-2">
          {attachments.map((file) => (
            <div
              key={file.id}
              className="flex max-w-full items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            >
              <span aria-hidden="true">📎</span>
              <span className="max-w-56 truncate">{file.original_filename}</span>
              <button
                type="button"
                onClick={() => onRemoveAttachment?.(file.id)}
                disabled={loading}
                title={t("tools.removeAttachment")}
                aria-label={t("tools.removeAttachment")}
                className="rounded-md px-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700 disabled:opacity-50 dark:hover:bg-slate-700"
              >
                ✕
              </button>
            </div>
          ))}
          {attachmentUploading ? (
            <span className="self-center text-xs text-slate-400">{t("tools.uploadingAttachment")}</span>
          ) : null}
        </div>
      ) : null}

      {dragOver && !loading && !isEditing ? (
        <div className="mb-3 rounded-xl border border-dashed border-slate-400 bg-slate-50 px-3 py-2 text-center text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-300">
          {t("tools.dropFilesHere")}
        </div>
      ) : null}

      <div className="flex items-end gap-3">
        <div className="flex-1">
          <div className="relative">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => {
                setValue(e.target.value);
                setCommandMenuDismissed(false);
              }}
              onKeyDown={(event) => {
                if (!filteredCommands.length || loading || isEditing) return;

                if (event.key === "ArrowDown") {
                  event.preventDefault();
                  setCommandIndex((current) => (current + 1) % filteredCommands.length);
                } else if (event.key === "ArrowUp") {
                  event.preventDefault();
                  setCommandIndex((current) =>
                    current === 0 ? filteredCommands.length - 1 : current - 1
                  );
                } else if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  selectCommand(filteredCommands[commandIndex]);
                } else if (event.key === "Escape") {
                  event.preventDefault();
                  setCommandMenuDismissed(true);
                }
              }}
              onPaste={handlePaste}
            placeholder={t("placeholder")}
            rows={2}
            maxLength={MAX_MESSAGE_LENGTH}
            disabled={loading}
              className="min-h-[56px] w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            />
            {filteredCommands.length > 0 ? (
              <div
                role="listbox"
                aria-label={lang === "ar" ? "أوامر الدردشة" : "Chat commands"}
                className="absolute inset-x-0 bottom-full z-20 mb-2 overflow-hidden rounded-2xl border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-900"
              >
                {filteredCommands.map((command, index) => (
                  <button
                    key={command.name}
                    type="button"
                    role="option"
                    aria-selected={index === commandIndex}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => selectCommand(command)}
                    className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-start text-sm ${
                      index === commandIndex
                        ? "bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-100"
                        : "text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
                    }`}
                  >
                    <span aria-hidden="true">{command.icon}</span>
                    <span className="font-medium">/{command.name}</span>
                    <span className="text-xs text-slate-400">{command.label}</span>
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          {nearLimit && (
            <p className="mt-1 text-end text-xs text-slate-400">
              {value.length}/{MAX_MESSAGE_LENGTH}
            </p>
          )}
        </div>
        {!loading && !isEditing ? (
          <>
            <label
              className="cursor-pointer rounded-2xl border border-slate-200 bg-white px-3 py-3 text-lg hover:bg-slate-50 focus-within:ring-2 focus-within:ring-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
              title={t("tools.attachFiles")}
              aria-label={t("tools.attachFiles")}
            >
              📎
              <input
                type="file"
                multiple
                accept=".txt,.csv,.pdf,.docx,.xlsx,image/*"
                className="hidden"
                onChange={handleFileSelection}
                disabled={attachmentUploading}
              />
            </label>
            {models.length > 0 ? (
              <select
                value={selectedModel || ""}
                onChange={(event) => onSelectModel?.(event.target.value || null)}
                title={t("tools.modelSelector")}
                aria-label={t("tools.modelSelector")}
                className="max-w-[180px] rounded-2xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              >
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.label}
                  </option>
                ))}
              </select>
            ) : null}
            {voiceSupported ? (
              <button
                type="button"
                onClick={toggleVoiceInput}
                title={isListening ? t("tools.voiceStop") : t("tools.voiceInput")}
                aria-label={isListening ? t("tools.voiceStop") : t("tools.voiceInput")}
                aria-pressed={isListening}
                className={`rounded-2xl border px-3 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-slate-400 ${isListening ? "border-red-300 bg-red-50 text-red-700 hover:bg-red-100 dark:border-red-800 dark:bg-red-950 dark:text-red-300" : "border-slate-200 bg-white hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"}`}
              >
                {isListening ? "⏹️" : "🎙️"}
              </button>
            ) : null}
            <button
              type="button"
              onClick={onInsertCalculator}
              title={t("tools.calculator")}
              className="rounded-2xl border border-slate-200 bg-white px-3 py-3 text-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
            >
              🧮
            </button>
            <button
              type="button"
              onClick={onInsertWebSearch}
              title={t("tools.webSearch")}
              className="rounded-2xl border border-slate-200 bg-white px-3 py-3 text-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
            >
              🔎
            </button>
            <button
              type="button"
              onClick={onInsertAgent}
              title={t("tools.agent")}
              className="rounded-2xl border border-slate-200 bg-white px-3 py-3 text-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
            >
              🤖
            </button>
            <button
              type="button"
              onClick={onInsertPython}
              title={t("tools.python")}
              className="rounded-2xl border border-slate-200 bg-white px-3 py-3 text-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
            >
              🐍
            </button>
            <button
              type="button"
              onClick={onInsertDataAnalysis}
              title={t("tools.dataAnalysis")}
              className="rounded-2xl border border-slate-200 bg-white px-3 py-3 text-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
            >
              📊
            </button>
          </>
        ) : null}
        {loading ? (
          <button
            type="button"
            onClick={onStop}
            className="rounded-2xl border border-red-200 bg-red-50 px-5 py-3 text-red-700 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-400 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
          >
            {t("stop")}
          </button>
        ) : (
          <button
            type="submit"
            disabled={!value.trim()}
            className="rounded-2xl bg-slate-900 px-5 py-3 text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            {isEditing ? saveEditLabel : t("send")}
          </button>
        )}
      </div>
    </form>
  );
}
