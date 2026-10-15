import { useCallback } from "react";

export default function useStopGeneration({
  streamAbortRef,
  setLoading,
  setToolActivity,
}) {
  const stopGeneration = useCallback(() => {
    if (streamAbortRef.current) {
      streamAbortRef.current.abort();
      streamAbortRef.current = null;
    }

    setLoading(false);
    setToolActivity(null);
  }, [setLoading, setToolActivity, streamAbortRef]);

  return { stopGeneration };
}
