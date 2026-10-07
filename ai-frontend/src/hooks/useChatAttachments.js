import { useCallback, useState } from "react";
import { uploadFile, deleteFile } from "../lib/filesApi";
import { getErrorMessage } from "../lib/errors";

const MAX_ATTACHMENTS = 10;
const MAX_FILE_BYTES = 10 * 1024 * 1024;

export default function useChatAttachments({
  conversationId,
  selectedWorkspaceId,
  selectedProjectId,
  loading,
  readOnlyConversation,
  editingMessageIndex,
  setToast,
  t,
}) {
  const [chatAttachments, setChatAttachments] = useState([]);
  const [chatAttachmentUploading, setChatAttachmentUploading] = useState(false);

  const handleAttachFiles = useCallback(
    async (files) => {
      if (
        readOnlyConversation ||
        loading ||
        editingMessageIndex !== null ||
        chatAttachmentUploading
      ) {
        return;
      }

      const selectedFiles = Array.from(files || []).filter(Boolean);
      if (!selectedFiles.length) return;

      const remainingSlots = MAX_ATTACHMENTS - chatAttachments.length;
      if (remainingSlots <= 0) {
        setToast({ message: t("app.tooManyAttachments"), type: "error" });
        return;
      }

      const filesToUpload = selectedFiles.slice(0, remainingSlots);
      if (filesToUpload.length < selectedFiles.length) {
        setToast({ message: t("app.attachmentLimitReached"), type: "error" });
      }

      const oversized = filesToUpload.filter((file) => file.size > MAX_FILE_BYTES);
      const validFiles = filesToUpload.filter((file) => file.size <= MAX_FILE_BYTES);

      if (oversized.length) {
        setToast({
          message: t("app.attachmentTooLarge", { count: oversized.length }),
          type: "error",
        });
      }
      if (!validFiles.length) return;

      setChatAttachmentUploading(true);
      let uploadedAny = false;
      let failed = 0;

      try {
        for (const file of validFiles) {
          try {
            const result = await uploadFile(
              file,
              undefined,
              conversationId,
              selectedWorkspaceId,
              selectedProjectId
            );
            uploadedAny = true;
            setChatAttachments((current) => [
              ...current,
              {
                id: result.id,
                original_filename: result.original_filename,
                content_type: result.content_type,
                size_bytes: result.size_bytes,
              },
            ]);
          } catch (err) {
            failed += 1;
            setToast({
              message: getErrorMessage(
                err,
                t("app.attachmentUploadErrorForFile", { name: file.name })
              ),
              type: "error",
            });
          }
        }
      } finally {
        setChatAttachmentUploading(false);
      }

      if (uploadedAny && failed === 0 && oversized.length === 0) {
        setToast({ message: t("app.attachmentsReady"), type: "success" });
      }
    },
    [
      chatAttachmentUploading,
      chatAttachments.length,
      conversationId,
      editingMessageIndex,
      loading,
      readOnlyConversation,
      selectedProjectId,
      selectedWorkspaceId,
      setToast,
      t,
    ]
  );

  const handleRemoveAttachment = useCallback(
    async (fileId) => {
      if (loading) return;

      const attachment = chatAttachments.find((file) => file.id === fileId);
      setChatAttachments((current) => current.filter((file) => file.id !== fileId));

      try {
        await deleteFile(fileId);
      } catch (err) {
        if (attachment) {
          setChatAttachments((current) =>
            current.some((file) => file.id === fileId)
              ? current
              : [...current, attachment]
          );
        }
        setToast({
          message: getErrorMessage(err, t("app.attachmentRemoveError")),
          type: "error",
        });
      }
    },
    [chatAttachments, loading, setToast, t]
  );

  const resetChatAttachments = useCallback(() => {
    setChatAttachments([]);
    setChatAttachmentUploading(false);
  }, []);

  return {
    chatAttachments,
    chatAttachmentUploading,
    handleAttachFiles,
    handleRemoveAttachment,
    resetChatAttachments,
  };
}
