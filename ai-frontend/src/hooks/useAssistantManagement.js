import {
  listAssistants,
  listWorkspaceSharedAssistants,
  createAssistant,
  updateAssistant,
  deleteAssistant,
  shareAssistantWithWorkspace,
  unshareAssistantFromWorkspace,
} from "../lib/assistantsApi";
import { getErrorMessage } from "../lib/errors";

export default function useAssistantManagement({
  selectedWorkspaceId,
  selectedAssistantId,
  editingAssistantId,
  setAssistants,
  setSelectedAssistantId,
  setEditingAssistantId,
  setShowAssistantEditor,
  setToast,
  startNewChat,
  t,
}) {
  const refreshAssistants = async (workspaceId = selectedWorkspaceId) => {
    try {
      const owned = (await listAssistants()).map((assistant) => ({
        ...assistant,
        is_shared: false,
        can_edit: true,
      }));

      let shared = [];
      if (workspaceId !== null && workspaceId !== undefined) {
        shared = await listWorkspaceSharedAssistants(workspaceId);
      }

      const ownedById = new Map(owned.map((assistant) => [assistant.id, assistant]));
      for (const item of shared) {
        const existing = ownedById.get(item.id);
        if (existing) {
          ownedById.set(item.id, {
            ...existing,
            is_shared: true,
            shared_workspace_id: item.workspace_id,
            owner_email: item.owner_email,
            can_edit: true,
          });
        } else {
          ownedById.set(item.id, item);
        }
      }

      const merged = Array.from(ownedById.values());
      setAssistants(merged);

      if (
        selectedAssistantId !== null &&
        !merged.some((assistant) => assistant.id === selectedAssistantId)
      ) {
        setSelectedAssistantId(null);
      }
    } catch (err) {
      setToast({
        message: getErrorMessage(err, t("app.assistantLoadError")),
        type: "error",
      });
    }
  };

  const openCreateAssistantEditor = () => {
    setEditingAssistantId(null);
    setShowAssistantEditor(true);
  };

  const openEditAssistantEditor = (id) => {
    setEditingAssistantId(id);
    setShowAssistantEditor(true);
  };

  const handleToggleAssistantShare = async (assistant) => {
    if (selectedWorkspaceId === null || assistant.can_edit === false) return;

    try {
      if (assistant.is_shared) {
        await unshareAssistantFromWorkspace(assistant.id, selectedWorkspaceId);
        setToast({ message: t("app.assistantUnshared"), type: "success" });
      } else {
        await shareAssistantWithWorkspace(assistant.id, selectedWorkspaceId);
        setToast({ message: t("app.assistantShared"), type: "success" });
      }
      await refreshAssistants(selectedWorkspaceId);
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.assistantShareError"),
        type: "error",
      });
    }
  };

  const handleAssistantRestored = async (restored) => {
    try {
      await refreshAssistants(selectedWorkspaceId);
      setSelectedAssistantId(restored.id);
      setToast({ message: t("app.assistantVersionRestored"), type: "success" });
    } catch {
      setToast({ message: t("app.assistantUpdateError"), type: "error" });
    }
  };

  const handleSaveAssistant = async ({ name, description, instructions }) => {
    try {
      if (editingAssistantId === null) {
        const assistant = await createAssistant({ name, description, instructions });
        await refreshAssistants(selectedWorkspaceId);
        setSelectedAssistantId(assistant.id);
        setEditingAssistantId(assistant.id);
        startNewChat();
      } else {
        const assistant = await updateAssistant(editingAssistantId, {
          name,
          description,
          instructions,
        });
        await refreshAssistants(selectedWorkspaceId);
        if (selectedAssistantId === editingAssistantId) {
          setSelectedAssistantId(assistant.id);
        }
      }
    } catch (err) {
      setToast({
        message:
          err?.response?.data?.detail ||
          (editingAssistantId === null
            ? t("app.assistantCreateError")
            : t("app.assistantUpdateError")),
        type: "error",
      });
      throw err;
    }
  };

  const handleDeleteAssistant = async (id, name) => {
    if (!window.confirm(t("sidebar.assistantDeleteConfirm", { name }))) return;
    try {
      await deleteAssistant(id);
      if (id === selectedAssistantId) {
        setSelectedAssistantId(null);
        startNewChat();
      }
      await refreshAssistants(selectedWorkspaceId);
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.assistantDeleteError"),
        type: "error",
      });
    }
  };

  const handleSelectAssistant = (id) => {
    setSelectedAssistantId(id);
    startNewChat();
  };

  return {
    refreshAssistants,
    openCreateAssistantEditor,
    openEditAssistantEditor,
    handleToggleAssistantShare,
    handleAssistantRestored,
    handleSaveAssistant,
    handleDeleteAssistant,
    handleSelectAssistant,
  };
}
