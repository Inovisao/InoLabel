import { useEffect } from "react";
import { api } from "../../shared/api/client";
import { useAnnotationStore } from "../annotate/store";
import { useSessionStore } from "../../shared/session/store";
import { useAutolabelingStore } from "./store";
import type { LabelingRun, Proposal } from "./types";

export function useAutolabeling() {
  const sessionId = useSessionStore((s) => s.sessionId);
  const mode = useSessionStore((s) => s.mode);
  useEffect(() => {
    useAutolabelingStore.getState().reset(sessionId);
    if (mode !== "detection" || !sessionId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const runs = await api.get<LabelingRun[]>("/autolabeling/runs");
        if (cancelled) return;
        const selected = useAutolabelingStore.getState().runId;
        const runId = selected && runs.some((r) => r.id === selected) ? selected : runs[0]?.id ?? null;
        useAutolabelingStore.setState({ runs, runId });
        if (runId) {
          const filter = useAutolabelingStore.getState();
          const frameIndex = useAnnotationStore.getState().frame?.index;
          const query = new URLSearchParams({ offset: String(filter.offset), limit: "100" });
          if (filter.onlyCurrent && frameIndex != null) query.set("frame_index", String(frameIndex));
          const result = await api.get<{ proposals: Proposal[]; total: number }>(`/autolabeling/runs/${runId}/proposals?${query}`);
          const current = useAutolabelingStore.getState();
          if (!cancelled && current.runId === runId && current.offset === filter.offset &&
              current.onlyCurrent === filter.onlyCurrent && useAnnotationStore.getState().frame?.index === frameIndex) {
            useAutolabelingStore.setState({ proposals: result.proposals, total: result.total });
          }
        }
      } catch (e) {
        if (!cancelled) useAutolabelingStore.setState({ error: (e as Error).message });
      } finally {
        if (!cancelled) timer = setTimeout(refresh, 1500);
      }
    };
    void refresh();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [sessionId, mode]);
}
