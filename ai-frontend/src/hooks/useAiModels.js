import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { listAiModels } from "../lib/chatApi";
import { getErrorMessage } from "../lib/errors";

/**
 * Owns the available AI model catalog and the user's active model.
 *
 * Selection stays compatible with existing conversation loading behavior:
 * keep the current model when it is still available, otherwise use the
 * backend-provided default model or the first available model.
 */
export default function useAiModels({ setToast }) {
  const { t } = useTranslation();
  const [aiModels, setAiModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const refreshRequestRef = useRef(0);

  const refreshAiModels = useCallback(async () => {
    const requestId = ++refreshRequestRef.current;
    try {
      const data = await listAiModels();
      // A newer request or logout/reset has made this response obsolete.
      if (requestId !== refreshRequestRef.current) return;

      const models = Array.isArray(data) ? data : data.models || [];
      setAiModels(models);

      const fallback =
        models.find((model) => model.is_default)?.id ||
        models[0]?.id ||
        "";

      setSelectedModel((current) =>
        current && models.some((model) => model.id === current)
          ? current
          : fallback
      );
    } catch (err) {
      // Do not surface failures from a stale request after reset or refresh.
      if (requestId !== refreshRequestRef.current) return;
      setToast({
        message: getErrorMessage(err, t("app.aiModelsLoadError")),
        type: "error",
      });
    }
  }, [setToast, t]);

  const resetAiModels = useCallback(() => {
    // Invalidate in-flight reads before clearing user-scoped UI state.
    refreshRequestRef.current += 1;
    setAiModels([]);
    setSelectedModel("");
  }, []);

  return {
    aiModels,
    selectedModel,
    setSelectedModel,
    refreshAiModels,
    resetAiModels,
  };
}
