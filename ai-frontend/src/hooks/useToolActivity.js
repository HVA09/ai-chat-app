import { useCallback } from "react";
import { useTranslation } from "react-i18next";

export default function useToolActivity({ setToolActivity }) {
  const { t } = useTranslation();

  const toolActivityLabel = useCallback(
    (name) => {
      const labels = {
        calculator: t("tools.activity.calculator"),
        web_search: t("tools.activity.webSearch"),
        analyze_data: t("tools.activity.dataAnalysis"),
        agent: t("tools.activity.agent"),
        python: t("tools.activity.python"),
      };
      return labels[name] || name;
    },
    [t]
  );

  const handleToolEvent = useCallback(
    (event) => {
      if (!event?.type) return;

      if (event.type === "runtime_start") {
        setToolActivity({
          name: "agent",
          phase: "running",
          message: t("tools.activity.runtimeStarting"),
        });
        return;
      }

      if (event.type === "runtime_round_start") {
        setToolActivity({
          name: "agent",
          phase: "running",
          message: t("tools.activity.round", { round: event.round ?? 1 }),
        });
        return;
      }

      if (event.type === "start") {
        setToolActivity({
          name: event.name || "agent",
          phase: "running",
          round: event.round,
          duration_ms: null,
        });
        return;
      }

      if (event.type === "result") {
        setToolActivity({
          name: event.name || "agent",
          phase: event.ok ? "done" : "error",
          round: event.round,
          duration_ms: event.duration_ms,
        });
        return;
      }

      if (event.type === "runtime_budget") {
        setToolActivity({
          name: "agent",
          phase: "warning",
          message: t("tools.activity.budget"),
        });
        return;
      }

      if (
        event.type === "runtime_security_block" ||
        event.type === "runtime_security_stop"
      ) {
        setToolActivity({
          name: "agent",
          phase: "error",
          message: t("tools.activity.securityStop"),
        });
        return;
      }

      if (event.type === "cancelled") {
        setToolActivity({
          name: event.name || "agent",
          phase: "cancelled",
          message: t("tools.activity.cancelled"),
        });
        return;
      }

      if (event.type === "runtime_complete") {
        setToolActivity({
          name: "agent",
          phase: event.status === "completed" ? "done" : "warning",
          message:
            event.status === "completed"
              ? t("tools.activity.completed")
              : t("tools.activity.stopped"),
        });
      }
    },
    [setToolActivity, t]
  );

  return { toolActivityLabel, handleToolEvent };
}
