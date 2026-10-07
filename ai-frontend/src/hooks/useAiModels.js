import { useCallback, useState } from "react";
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

  const refreshAiModels = useCallback(async () => {
    try {
      const data = await listAiModels();
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
      setToast({
        message: getErrorMessage(err, t("app.aiModelsLoadError")),
        type: "error",
      });
    }
  }, [setToast, t]);

  const resetAiModels = useCallback(() => {
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
